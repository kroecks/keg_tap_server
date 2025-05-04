#!/bin/bash
# setup.sh - Setup script for Keg Tap Manager on Raspberry Pi

echo "Setting up Keg Tap Manager on Raspberry Pi..."

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system dependencies
echo "Installing dependencies..."
sudo apt install -y python3-pip python3-venv python3-dev

# Create project directory
mkdir -p ~/keg_tap_server
cd ~/keg_tap_server

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install flask werkzeug Pillow

# Create directory structure
mkdir -p static/beer_images
mkdir -p templates

# Create a default beer image
if [ ! -f static/beer_images/default.jpg ]; then
    echo "Creating default beer image..."
    # Create a simple colored image
    cat > static/beer_images/default.jpg << EOF
    # This is a placeholder for a default beer image
    # Download a default beer image from the internet or create one
EOF
    echo "Note: You should replace the default.jpg with an actual image"
fi

# Create a simple startup script
cat > start.sh << EOF
#!/bin/bash
cd ~/keg_tap_server
source venv/bin/activate
python app.py
EOF

# Make startup script executable
chmod +x start.sh

# Create systemd service to run at startup
echo "Creating systemd service for auto-start..."
sudo tee /etc/systemd/system/keg_tap_server.service > /dev/null << EOF
[Unit]
Description=Keg Tap Manager
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/keg_tap_server
ExecStart=/home/$USER/keg_tap_server/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable keg_tap_server.service
sudo systemctl start keg_tap_server.service

# Display IP address for user to access the web interface
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo ""
echo "Keg Tap Manager setup complete!"
echo "You can access the web interface at: http://$IP_ADDRESS:5000"
echo ""
echo "To check service status: sudo systemctl status keg_tap_server.service"
echo "To manually start the service: sudo systemctl start keg_tap_server.service"
echo "To manually stop the service: sudo systemctl stop keg_tap_server.service"
echo "To view logs: sudo journalctl -u keg_tap_server.service"