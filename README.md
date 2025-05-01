# Keg Tap Manager System

This project creates a complete Keg Tap management system using a Raspberry Pi as a server and ESP32 S3 devices to display and monitor each tap. The system includes a web interface for managing beers and tap configurations.

## System Components

1. **Raspberry Pi Server**
   - Web interface for managing beers and taps
   - SQLite database for storing beer definitions and tap states
   - API endpoints for ESP32 communication

2. **ESP32 S3 Devices (one per tap)**
   - 240x240 display to show beer information
   - Flow sensor monitoring to track beer consumption
   - WiFi connectivity to communicate with the Raspberry Pi server

## Hardware Requirements

### Raspberry Pi
- Raspberry Pi (any model with network capability)
- SD card with Raspberry Pi OS
- Network connection (WiFi or Ethernet)

### ESP32 S3 (per tap)
- ESP32 S3 board with 240x240 display
- GREDIA 1/4" Water Flow Sensor (0.3-6L/min)
- Power supply for ESP32

## Installation

### Raspberry Pi Setup

1. Clone or download this repository to your Raspberry Pi:

```bash
git clone <repository-url> ~/keg_tap_server
cd ~/keg_tap_server
```

2. Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

3. The setup script will:
   - Install necessary dependencies
   - Create a Python virtual environment
   - Set up the directory structure
   - Create a systemd service for auto-starting the application
   - Display the IP address to access the web interface

4. Access the web interface at `http://<raspberry-pi-ip>:5000`

### ESP32 S3 Setup

1. Install required tools:
   - [esptool](https://github.com/espressif/esptool) for flashing the ESP32
   - [ampy](https://github.com/scientifichackers/ampy) for file transfer

2. Flash MicroPython to your ESP32 S3:

```bash
esptool.py --chip esp32s3 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32s3 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0 esp32s3-20230426-v1.20.0.bin
```

3. Edit the `main.py` file to configure your WiFi and Raspberry Pi settings:

```python
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
SERVER_URL = "http://192.168.1.100:5000"  # Replace with your Raspberry Pi IP
TAP_ID = "tap_1"  # Unique ID for each tap device
```

4. Install the required libraries on your ESP32 S3:
   - GC9A01 display driver
   - MicroPython urequests library

5. Upload the files to your ESP32 S3:

```bash
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put main.py
# Upload any additional libraries
```

6. Connect the hardware:
   - Display to appropriate pins (configured in main.py)
   - Flow sensor to GPIO4 (configurable in main.py)

7. Reset your ESP32 S3, and it should start automatically

## Usage

### Web Interface

1. **Home Page**
   - Overview of all taps and beers

2. **Beer Management**
   - Add new beers with name, ABV, and image
   - View existing beers

3. **Tap Management**
   - Add new taps with unique IDs
   - Configure taps with beer selection, volume, and flow rate
   - Edit existing tap configurations

### ESP32 S3 Display

Each ESP32 S3 device will:
1. Show the current beer information on its display
2. Monitor flow sensor to detect when beer is being poured
3. Report pouring events to the Raspberry Pi server
4. Update the displayed information automatically

## Troubleshooting

### Raspberry Pi Server

- Check service status: `sudo systemctl status beer-tap-manager.service`
- View logs: `sudo journalctl -u beer-tap-manager.service`
- Manually restart: `sudo systemctl restart beer-tap-manager.service`

### ESP32 S3 Devices

- Connect to the ESP32 S3 serial console to view debug messages
- Check WiFi connectivity
- Ensure the Raspberry Pi server is accessible from the ESP32

## Flow Sensor Calibration

The flow rate (milliliters per second) can be adjusted in the tap configuration. To calibrate:

1. Pour a known volume of liquid
2. Note the reported poured volume
3. Adjust the flow rate in the tap settings accordingly

## System Architecture Diagram

```
┌───────────────────────┐                ┌───────────────────────┐
│                       │                │                       │
│   Raspberry Pi        │◄───────────────┤   ESP32 S3 (tap_1)    │
│   - Web Server        │    HTTP API    │   - Display           │
│   - Database          │                │   - Flow Sensor       │
│   - API               │────────────────►│                       │
│                       │                │                       │
└───────────────────────┘                └───────────────────────┘
          ▲                                        ▲
          │                                        │
          │                               ┌────────┴──────────┐
          │                               │                   │
          │                               │  Flow Sensor      │
          │                               │                   │
          │                               └───────────────────┘
          │
          │                              ┌───────────────────────┐
          │                              │                       │
          └──────────────────────────────┤   ESP32 S3 (tap_2)    │
                            HTTP API     │   - Display           │
                                         │   - Flow Sensor       │
                                         │                       │
                                         └───────────────────────┘
```

## Future Enhancements

- User authentication for the web interface
- Multiple user roles (admin, bartender)
- Keg tracking and change alerts
- Temperature monitoring
- Web-based dashboard for real-time status
- Analytics for consumption patterns