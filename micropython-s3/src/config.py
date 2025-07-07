# config.py - Configuration settings for ESP32 Keg Tap Monitor

# WiFi Configuration
WIFI_SSID = "Nexus"
WIFI_PASSWORD = "thescaryd00r"

# Server Configuration
SERVER_URL = "http://beerpi.kenandmidi.com:5000"  # Replace with your Raspberry Pi IP
TAP_ID = "tap_1"  # Can be modified for each device

# Display Configuration
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

# Flow Sensor Configuration
FLOW_SENSOR_PIN = 4  # GPIO4 for flow sensor input
FLOW_DETECTION_THRESHOLD = 5  # Number of pulses to detect as active flow
FLOW_TIMEOUT = 2000  # milliseconds without pulses to consider flow stopped

# LED Configuration
STATUS_LED_PIN = 33
LED_COUNT = 8

# Status LED colors (for startup sequence)
STATUS_RED = (255, 0, 0)      # No WiFi
STATUS_YELLOW = (255, 255, 0)  # WiFi connected, loading tap data
STATUS_GREEN = (0, 255, 0)     # Tap data loaded successfully

# Keg level colors
KEG_FULL = (0, 255, 0)        # Green for full levels
KEG_MEDIUM = (255, 255, 0)    # Yellow for medium levels
KEG_LOW = (255, 0, 0)         # Red for low levels
KEG_EMPTY = (0, 0, 0)         # Off for empty

# Battery Configuration
BATTERY_ADC_PIN = 1  # GPIO1 - battery voltage measurement pin per wiki
BATTERY_MIN_VOLTAGE = 3.2  # Minimum safe voltage (adjust based on your battery)
BATTERY_MAX_VOLTAGE = 4.2  # Maximum voltage for LiPo battery (adjust if different)
# Voltage divider: 200K + 100K resistors, so divider ratio is (200K+100K)/100K = 3.0

# Image Configuration
IMAGE_DIR = "/images"
USE_SERVER_RESIZE = True  # Set to False if your server doesn't support this feature