#!/bin/bash
# Teledown Oracle Cloud Auto-Deploy Script
set -e

echo "============================================="
echo "   Teledown Oracle Cloud Automated Setup     "
echo "============================================="
echo ""

# 1. Update and Install Docker + Git
echo "[1/4] Installing Docker and system packages..."
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose git iptables-persistent

# 2. Open OS Firewall Port 8000
echo "[2/4] Opening network port 8000 in OS firewall..."
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save

# 3. Download Code
echo "[3/4] Downloading Teledown application..."
cd /home/ubuntu
if [ -d "teledown" ]; then
    sudo rm -rf teledown
fi
git clone https://github.com/cherrylw1/teledown.git
cd teledown

# 4. Prompt for Config
echo ""
echo "[4/4] Connection Configuration:"
echo "---------------------------------------------"
read -p "Enter your Telegram API ID: " api_id
read -p "Enter your Telegram API HASH: " api_hash
read -p "Set a Security Password (for your phone): " access_token
echo "---------------------------------------------"

# Write configuration
sudo mkdir -p backend
cat <<EOF | sudo tee backend/.env > /dev/null
TELEGRAM_API_ID=${api_id}
TELEGRAM_API_HASH=${api_hash}
ACCESS_TOKEN=${access_token}
EOF

# Start Docker containers
echo ""
echo "Starting Teledown server..."
sudo docker-compose up -d

echo ""
echo "---------------------------------------------"
echo "Connecting to Telegram Login screen..."
echo "Enter your Telegram phone number when prompted."
echo "Detaching key command: Press Ctrl+P, then Ctrl+Q."
echo "---------------------------------------------"
echo ""
sleep 2

sudo docker attach teledown_app
