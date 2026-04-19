#!/bin/bash
# Setup script for Hostinger VPS Ubuntu 22.04/24.04

set -e

PROJECT_DIR="/var/www/executive_appointments"
DOMAIN="your-domain.com"

echo "=== Updating system ==="
sudo apt update && sudo apt upgrade -y

echo "=== Installing dependencies ==="
sudo apt install -y python3 python3-pip python3-venv nginx sqlite3

echo "=== Creating project directory ==="
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR

# NOTE: Upload your project files to $PROJECT_DIR first

echo "=== Creating virtual environment ==="
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Creating .env file ==="
cp .env.example .env
nano .env  # Edit this file with your settings

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Creating log directories ==="
sudo mkdir -p /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/gunicorn

echo "=== Setting up systemd service ==="
sudo cp deploy/systemd.service /etc/systemd/system/executive_appointments.service
sudo systemctl daemon-reload
sudo systemctl enable executive_appointments
sudo systemctl start executive_appointments

echo "=== Setting up Nginx ==="
sudo cp deploy/nginx.conf /etc/nginx/sites-available/executive_appointments
sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/executive_appointments
sudo ln -sf /etc/nginx/sites-available/executive_appointments /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

echo "=== Setting permissions ==="
sudo chown -R www-data:www-data $PROJECT_DIR
sudo chmod -R 755 $PROJECT_DIR

echo "=== Done! ==="
echo "App running at: http://$DOMAIN"
