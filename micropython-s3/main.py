# main.py for ESP32 S3 with 240x240 display for Keg Tap monitoring
import gc
import network
import urequests as requests
import time
import json
import os
from machine import Pin, SPI, Timer, freq
import gc9a01

# Set CPU frequency to 240MHz for better performance
freq(240000000)

# Configuration
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
SERVER_URL = "http://192.168.1.100:5000"  # Replace with your Raspberry Pi IP
TAP_ID = "tap_1"  # Can be modified for each device

# Flow sensor pin and settings
FLOW_SENSOR_PIN = 4  # GPIO4 for flow sensor input
flow_pin = Pin(FLOW_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
flow_count = 0
flow_start_time = 0
flow_active = False
FLOW_DETECTION_THRESHOLD = 5  # Number of pulses to detect as active flow
FLOW_TIMEOUT = 2000  # milliseconds without pulses to consider flow stopped

# Initialize display
tft = None
last_image = None
current_beer = None

# Directory for storing images
IMAGE_DIR = "/images"
try:
    os.mkdir(IMAGE_DIR)
except:
    pass  # Directory already exists

def init_display():
    global tft
    try:
        # Initialize display
        tft = gc9a01.GC9A01(
            SPI(2, baudrate=80000000, polarity=0, sck=Pin(10), mosi=Pin(11)),
            240,
            240,
            reset=Pin(14, Pin.OUT),
            cs=Pin(9, Pin.OUT),
            dc=Pin(8, Pin.OUT),
            backlight=Pin(2, Pin.OUT),
            rotation=0)

        # Enable display and clear screen
        tft.init()
        tft.fill(0)  # Clear screen with black
        display_message("Connecting...")
        return True
    except Exception as e:
        print("Display initialization error:", e)
        return False

def display_message(message, y_pos=120):
    """Display a centered message on the screen"""
    if tft:
        tft.fill(0)  # Clear the screen
        tft.text(message, 120 - len(message) * 4, y_pos, gc9a01.WHITE)

def connect_wifi():
    display_message("Connecting to WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait for connection with timeout
        max_wait = 20
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            print("Waiting for connection...")
            time.sleep(1)

        if wlan.isconnected():
            print("Connected to WiFi")
            ip = wlan.ifconfig()[0]
            print(f"IP: {ip}")
            display_message(f"Connected: {ip}", 100)
            time.sleep(2)
            return True
        else:
            print("Failed to connect to WiFi")
            display_message("WiFi Failed!", 100)
            time.sleep(2)
            return False
    else:
        print("Already connected to WiFi")
        ip = wlan.ifconfig()[0]
        print(f"IP: {ip}")
        return True

def fetch_tap_info():
    """Fetch tap information from the server"""
    global current_beer

    try:
        display_message("Fetching tap info...")
        response = requests.get(f"{SERVER_URL}/api/tap/{TAP_ID}")

        if response.status_code == 200:
            data = response.json()
            current_beer = data
            print("Tap info:", data)

            # Download the beer image if it exists
            if data['image_path']:
                download_beer_image()

            display_tap_info()
            return True
        else:
            print(f"Error fetching tap info: {response.status_code}")
            display_message(f"Error: {response.status_code}")
            time.sleep(2)
            return False
    except Exception as e:
        print("Error fetching tap info:", e)
        display_message("Connection Error")
        time.sleep(2)
        return False

def download_beer_image():
    """Download the beer image from the server"""
    global last_image

    try:
        image_path = f"{IMAGE_DIR}/{TAP_ID}.jpg"

        # Delete existing image if exists
        try:
            os.remove(image_path)
        except:
            pass

        # Download new image
        response = requests.get(f"{SERVER_URL}/api/tap/{TAP_ID}/image")

        if response.status_code == 200:
            with open(image_path, 'wb') as f:
                f.write(response.content)
            print(f"Image downloaded to {image_path}")
            last_image = image_path
            return True
        else:
            print(f"Error downloading image: {response.status_code}")
            return False
    except Exception as e:
        print("Error downloading image:", e)
        return False

def display_tap_info():
    """Display the current tap information and beer image"""
    global tft, current_beer, last_image

    if not tft or not current_beer:
        return

    # Clear the screen
    tft.fill(0)

    # Display beer image if available
    if last_image:
        try:
            tft.jpg(last_image, 0, 0, gc9a01.SLOW)
        except Exception as e:
            print("Error displaying image:", e)

    # Calculate remaining beer percentage
    if current_beer['volume'] > 0:
        # Assume a keg is typically 5000ml (5L) when full
        full_volume = 5000  # Can be adjusted
        remaining_percent = min(100, int((current_beer['volume'] / full_volume) * 100))
    else:
        remaining_percent = 0

    # Display beer information as overlay
    y_offset = 180
    tft.text(current_beer['beer_name'] or "No beer", 10, y_offset, gc9a01.WHITE)
    tft.text(f"{current_beer['beer_abv']}% ABV" if current_beer['beer_abv'] else "", 10, y_offset + 15, gc9a01.WHITE)
    tft.text(f"Left: {remaining_percent}%", 10, y_offset + 30, gc9a01.WHITE)

def flow_callback(p):
    """Interrupt handler for flow sensor pulses"""
    global flow_count, flow_start_time, flow_active

    flow_count += 1

    # If flow wasn't active, mark it as started
    if not flow_active and flow_count >= FLOW_DETECTION_THRESHOLD:
        flow_active = True
        flow_start_time = time.ticks_ms()
        print("Flow started")

        # Start the timer to check for flow stop
        timer_flow.init(period=FLOW_TIMEOUT, mode=Timer.PERIODIC, callback=check_flow_stop)

def check_flow_stop(t):
    """Timer callback to check if flow has stopped"""
    global flow_count, flow_active, flow_start_time

    # Store the count and reset for next check
    current_count = flow_count
    flow_count = 0

    if flow_active and current_count < FLOW_DETECTION_THRESHOLD:
        # Flow has stopped
        flow_active = False
        flow_duration = (time.ticks_ms() - flow_start_time) / 1000  # Convert to seconds
        print(f"Flow stopped after {flow_duration} seconds")

        # Stop the timer
        timer_flow.deinit()

        # Report to server
        report_pour_event("stop", flow_duration)

def report_pour_event(event_type, duration=None):
    """Report pour event to the server"""
    try:
        if event_type == "start":
            data = {"event_type": "start"}
        else:
            data = {"event_type": "stop", "duration": duration}

        response = requests.post(
            f"{SERVER_URL}/api/tap/{TAP_ID}/pour_event",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data)
        )

        if response.status_code == 200:
            print(f"Pour event reported: {event_type}")
            if event_type == "stop":
                # Refresh tap info after reporting stop event
                fetch_tap_info()
            return True
        else:
            print(f"Error reporting pour event: {response.status_code}")
            return False
    except Exception as e:
        print("Error reporting pour event:", e)
        return False

def main():
    """Main function to initialize and run the system"""
    global timer_flow

    # Initialize hardware
    if not init_display():
        print("Failed to initialize display, can't continue")
        return

    # Setup flow sensor interrupt
    flow_pin.irq(trigger=Pin.IRQ_FALLING, handler=flow_callback)

    # Create timer for flow detection
    timer_flow = Timer(0)

    # Connect to WiFi
    if not connect_wifi():
        print("Failed to connect to WiFi, retrying in 5 seconds")
        time.sleep(5)
        if not connect_wifi():
            print("Failed to connect to WiFi again, can't continue")
            display_message("WiFi Failed!", 100)
            return

    # Initial fetch of tap info
    if not fetch_tap_info():
        print("Failed to fetch tap info, can't continue")
        return

    # Main loop
    refresh_interval = 60  # seconds between refreshes
    last_refresh = time.time()

    while True:
        # Periodically refresh tap info
        current_time = time.time()
        if current_time - last_refresh >= refresh_interval:
            print("Refreshing tap info...")
            fetch_tap_info()
            last_refresh = current_time

        # Give some time to other tasks
        time.sleep(1)
        gc.collect()  # Run garbage collection to free memory

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Fatal error:", e)
        if tft:
            display_message(f"Error: {e}", 100)