#!/bin/bash
cd /home/sam/projects/my_code/dexwatch-main
source venv/bin/activate
python export_data.py >> /var/log/dexwatch/export.log 2>&1
