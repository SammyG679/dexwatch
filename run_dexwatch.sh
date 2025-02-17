#!/bin/bash
cd /home/sam/projects/my_code/dexwatch-main
source venv/bin/activate
python main.py >> /var/log/dexwatch/pipeline.log 2>&1
