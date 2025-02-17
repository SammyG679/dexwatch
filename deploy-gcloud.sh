#!/bin/bash

# Variables
PROJECT_ID="g-labs-451213"
INSTANCE_NAME="dexwatch-server"
ZONE="us-central1-a"
MACHINE_TYPE="e2-small"
BUCKET_NAME="g-labs-451213-dexwatch-exports"

echo "Starting deployment for project: $PROJECT_ID"

# Create VM instance
echo "Creating VM instance..."
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --network-interface=network-tier=PREMIUM,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=$PROJECT_ID-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/debian-cloud/global/images/debian-11-bullseye-v20240111,mode=rw,size=20,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-standard \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=purpose=dexwatch

# Create startup script
cat << 'EOF' > startup-script.sh
#!/bin/bash

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y python3-pip python3-venv git redis-server curl wget gnupg2

# Install ArangoDB
curl -OL https://download.arangodb.com/arangodb311/DEBIAN/Release.key
apt-key add Release.key
echo 'deb https://download.arangodb.com/arangodb311/DEBIAN/ /' | tee /etc/apt/sources.list.d/arangodb.list
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y arangodb3

# Configure ArangoDB
cat > /etc/arangodb3/arangod.conf << CONF
[server]
endpoint = tcp://0.0.0.0:8529
authentication = true

[database]
directory = /var/lib/arangodb3

[javascript]
v8-contexts = 1
CONF

# Start services
systemctl start redis-server
systemctl enable redis-server
systemctl start arangodb3
systemctl enable arangodb3

# Clone repository
cd /opt
git clone https://github.com/yourusername/dexwatch.git dexwatch
cd dexwatch

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup database
arangosh --server.endpoint tcp://127.0.0.1:8529 --server.username root --server.password root << ARANGO
db._createDatabase("jeettech");
db._useDatabase("jeettech");
require("@arangodb/users").save("jeettech", "jeettech_password");
require("@arangodb/users").grantDatabase("jeettech", "jeettech", "rw");
ARANGO

# Create .env file
cat > .env << ENV
ARANGO_USER=jeettech
ARANGO_PASS=jeettech_password
ENV

# Setup log directory
mkdir -p /var/log/dexwatch
chmod 777 /var/log/dexwatch

# Setup cron jobs
(crontab -l 2>/dev/null; echo "*/1 * * * * cd /opt/dexwatch && source venv/bin/activate && python main.py >> /var/log/dexwatch/pipeline.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 * * * * cd /opt/dexwatch && source venv/bin/activate && python export_data.py >> /var/log/dexwatch/export.log 2>&1") | crontab -

EOF

# Upload startup script to VM
gcloud compute scp startup-script.sh $INSTANCE_NAME:~/startup-script.sh --zone=$ZONE

# Execute startup script on VM
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="chmod +x ~/startup-script.sh && sudo ~/startup-script.sh"

echo "Deployment complete! Please verify the services are running correctly."
