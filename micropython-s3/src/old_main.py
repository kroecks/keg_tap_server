# old_main.py for ESP32 S3 with 240x240 display for Keg Tap monitoring
import gc
import network
import urequests as requests
import time
import json
import os
import io
from truetype import NotoSans_32 as noto_sans
from truetype import NotoSerif_32 as noto_serif
from truetype import NotoSansMono_32 as noto_mono
from machine import Pin, SPI, Timer, freq, ADC
import gc9a01
import neopixel
from micropython import const

# Set CPU frequency to 240MHz for better performance
freq(240000000)

# Configuration
WIFI_SSID = "Nexus"
WIFI_PASSWORD = "thescaryd00r"
SERVER_URL = "http://beerpi.kenandmidi.com:5000"  # Replace with your Raspberry Pi IP
TAP_ID = "tap_1"  # Can be modified for each device

# Display configuration
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

# Flow sensor pin and settings
FLOW_SENSOR_PIN = 4  # GPIO4 for flow sensor input
flow_pin = Pin(FLOW_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
flow_count = 0
flow_start_time = 0
flow_active = False
FLOW_DETECTION_THRESHOLD = 5  # Number of pulses to detect as active flow
FLOW_TIMEOUT = 2000  # milliseconds without pulses to consider flow stopped

# Status/Keg Level LED strip on port 33
STATUS_LED_PIN = 33
LED_COUNT = 8
status_leds = neopixel.NeoPixel(Pin(STATUS_LED_PIN), LED_COUNT)

# Status LED colors (for startup sequence)
STATUS_RED = (255, 0, 0)      # No WiFi
STATUS_YELLOW = (255, 255, 0)  # WiFi connected, loading tap data
STATUS_GREEN = (0, 255, 0)     # Tap data loaded successfully

# Keg level colors
KEG_FULL = (0, 255, 0)        # Green for full levels
KEG_MEDIUM = (255, 255, 0)    # Yellow for medium levels
KEG_LOW = (255, 0, 0)         # Red for low levels
KEG_EMPTY = (0, 0, 0)         # Off for empty

# Initialize display
tft = None
last_image = None
current_beer = None

connection_blink_timer = None
connection_blink_state = False

gc.enable()
gc.collect()

# Directory for storing images
IMAGE_DIR = "/images"
try:
    os.mkdir(IMAGE_DIR)
except:
    pass  # Directory already exists

# Flag to control whether we try to use server-side resizing
USE_SERVER_RESIZE = True  # Set to False if your server doesn't support this feature


###############################################################################

# Battery monitoring configuration
BATTERY_ADC_PIN = 1  # GPIO1 - battery voltage measurement pin per wiki
BATTERY_MIN_VOLTAGE = 3.2  # Minimum safe voltage (adjust based on your battery)
BATTERY_MAX_VOLTAGE = 4.2  # Maximum voltage for LiPo battery (adjust if different)
# Voltage divider: 200K + 100K resistors, so divider ratio is (200K+100K)/100K = 3.0

# Global variables
battery_adc = None
battery_connected = False
battery_voltage = 0.0
battery_percentage = 0

def init_battery_monitor():
    """Initialize battery monitoring"""
    global battery_adc, battery_connected

    try:
        # Initialize ADC for battery monitoring on GPIO1
        battery_adc = ADC(Pin(BATTERY_ADC_PIN))
        battery_adc.atten(ADC.ATTN_11DB)  # For 3.3V reference, allows reading up to ~3.9V

        # Take initial reading to check if battery is connected
        test_voltage = read_battery_voltage()

        # If voltage is above a threshold, assume battery is connected
        if test_voltage > 2.5:  # Adjust threshold as needed
            battery_connected = True
            print(f"Battery detected: {test_voltage:.2f}V")
        else:
            battery_connected = False
            print("No battery detected")

        return True
    except Exception as e:
        print(f"Error initializing battery monitor: {e}")
        battery_connected = False
        return False

def read_battery_voltage():
    """Read battery voltage from ADC using the board's specific conversion formula"""
    global battery_adc, battery_voltage

    if not battery_adc:
        return 0.0

    try:
        # Take multiple readings and average them for stability
        readings = []
        for _ in range(5):
            raw_value = battery_adc.read()
            readings.append(raw_value)
            time.sleep_ms(10)

        avg_reading = sum(readings) / len(readings)

        # Use the conversion formula from the wiki:
        # voltage = 3.3 / (1<<12) * 3 * AD_Value
        # This accounts for the 200K+100K voltage divider (factor of 3)
        voltage = (3.3 / (1 << 12)) * 3 * avg_reading

        battery_voltage = voltage
        return voltage
    except Exception as e:
        print(f"Error reading battery voltage: {e}")
        return 0.0

def calculate_battery_percentage():
    """Calculate battery percentage based on voltage"""
    global battery_percentage

    if not battery_connected or battery_voltage == 0:
        battery_percentage = 0
        return 0

    # Linear interpolation between min and max voltage
    if battery_voltage >= BATTERY_MAX_VOLTAGE:
        battery_percentage = 100
    elif battery_voltage <= BATTERY_MIN_VOLTAGE:
        battery_percentage = 0
    else:
        voltage_range = BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE
        current_range = battery_voltage - BATTERY_MIN_VOLTAGE
        battery_percentage = int((current_range / voltage_range) * 100)

    return battery_percentage

def get_battery_status():
    """Get complete battery status"""
    if not battery_connected:
        return {
            'connected': False,
            'voltage': 0.0,
            'percentage': 0,
            'status': 'Not connected'
        }

    voltage = read_battery_voltage()
    percentage = calculate_battery_percentage()

    # Determine status
    if percentage > 75:
        status = 'Good'
    elif percentage > 50:
        status = 'Fair'
    elif percentage > 25:
        status = 'Low'
    else:
        status = 'Critical'

    return {
        'connected': True,
        'voltage': voltage,
        'percentage': percentage,
        'status': status
    }

def print_battery_info():
    """Print battery information to console"""
    battery_info = get_battery_status()

    if battery_info['connected']:
        print(f"Battery: {battery_info['voltage']:.2f}V ({battery_info['percentage']}%) - {battery_info['status']}")
    else:
        print("Battery: Not connected")

    return battery_info

# Modified fetch_tap_info function to include battery monitoring
def fetch_tap_info_with_battery():
    """Enhanced fetch_tap_info function that includes battery monitoring"""
    global current_beer

    # Check battery status
    battery_info = print_battery_info()

    try:
        display_message("Fetching tap info...")
        # Keep status LED yellow while fetching
        set_status_led(STATUS_YELLOW)

        response = requests.get(f"{SERVER_URL}/api/tap/{TAP_ID}")

        if response.status_code == 200:
            data = response.json()
            current_beer = data
            print("Tap info:", data)

            # Download the beer image if it exists
            if data['image_path']:
                download_beer_image()

            print("Retrieved image, displaying tap info")
            display_tap_info_with_battery(battery_info)
            return True
        else:
            print(f"Error fetching tap info: {response.status_code}")
            display_message(f"Error: {response.status_code}")
            # Keep status LED yellow on error
            set_status_led(STATUS_YELLOW)
            time.sleep(2)
            return False
    except Exception as e:
        print("Error fetching tap info:", e)
        display_message("Connection Error")
        # Keep status LED yellow on error
        set_status_led(STATUS_YELLOW)
        time.sleep(2)
        return False

def display_tap_info_with_battery(battery_info):
    """Enhanced display function that includes battery info"""
    global tft, current_beer, last_image

    if not tft or not current_beer:
        return

    # Clear the screen
    tft.fill(0)

    # Display beer image if available (same as before)
    if last_image:
        try:
            dimensions = get_jpeg_dimensions(last_image)
            if dimensions:
                img_width, img_height = dimensions
                print(f"Image dimensions: {img_width}x{img_height}")

                if img_width <= DISPLAY_WIDTH and img_height <= DISPLAY_HEIGHT:
                    x_offset = (DISPLAY_WIDTH - img_width) // 2
                    y_offset = (DISPLAY_HEIGHT - img_height) // 2
                    print(f"Displaying image centered at ({x_offset},{y_offset})")
                    tft.jpg(last_image, x_offset, y_offset, gc9a01.SLOW)
                else:
                    print("Image larger than display, centering and displaying")
                    img_center_x = img_width // 2
                    img_center_y = img_height // 2
                    x_offset = -(img_center_x - DISPLAY_WIDTH // 2)
                    y_offset = -(img_center_y - DISPLAY_HEIGHT // 2)
                    print(f"Centering large image with offset ({x_offset},{y_offset})")
                    tft.jpg(last_image, x_offset, y_offset, gc9a01.SLOW)
            else:
                print("Unable to determine image dimensions, displaying at origin")
                tft.jpg(last_image, 0, 0, gc9a01.FAST)
        except Exception as e:
            print("Error displaying image:", e)

    # Calculate remaining beer percentage
    if current_beer['volume'] > 0:
        remaining_percent = min(100, int((current_beer['volume'] / current_beer['full_volume']) * 100))
    else:
        remaining_percent = 0

    # Update the keg level LEDs
    set_keg_level_leds(remaining_percent)

    # Display beer information as overlay
    center(noto_sans, current_beer['beer_name'] or "No beer", 50, gc9a01.WHITE)
    center(noto_sans, f"{current_beer['beer_abv']}% ABV" if current_beer['beer_abv'] else "", 180, gc9a01.WHITE)

    # Display battery info if connected
    if battery_info['connected']:
        battery_text = f"Batt: {battery_info['percentage']}%"
        center(noto_sans, battery_text, 200, gc9a01.YELLOW)

def set_status_led(color):
    """Set all LEDs to the same color for status indication"""

    print(f"set_status_led : {color}")

    for i in range(LED_COUNT):
        status_leds[i] = color
    status_leds.write()

def set_keg_level_leds(remaining_percent):
    """Set LEDs based on keg fullness percentage"""
    # Calculate how many LEDs should be lit based on percentage
    leds_to_light = int((remaining_percent / 100.0) * LED_COUNT)

    print(f"set_keg_level_leds leds_to_light: {leds_to_light} remaining_percent {remaining_percent}")

    for i in range(LED_COUNT):
        if i < leds_to_light:
            # Determine color based on percentage ranges
            led_position_percent = ((i + 1) / LED_COUNT) * 100

            if led_position_percent <= 25:
                # Bottom 25% - Red (low)
                status_leds[i] = KEG_LOW
            elif led_position_percent <= 75:
                # Middle 50% - Yellow (medium)
                status_leds[i] = KEG_MEDIUM
            else:
                # Top 25% - Green (full)
                status_leds[i] = KEG_FULL
        else:
            # Turn off LEDs that shouldn't be lit
            status_leds[i] = KEG_EMPTY

    status_leds.write()

def init_display():
    global tft
    try:
        print("Init display 1...")
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

        print("Init display 2...")

        # Enable display and clear screen
        tft.init()
        print("Init display 3...")
        tft.fill(0)  # Clear screen with black
        print("Init display 4...")
        display_message("Connecting...")
        return True
    except Exception as e:
        print("Display initialization error:", e)
        return False

def center(font, s, row, color=gc9a01.WHITE):
    screen = tft.width()                     # get screen width
    width = tft.write_len(font, s)           # get the width of the string
    if width and width < screen:             # if the string < display
        col = tft.width() // 2 - width // 2  # find the column to center
    else:                                    # otherwise
        col = 0                              # left justify

    tft.write(font, s, col, row, color)      # and write the string

def display_message(message, y_pos=120):
    """Display a centered message on the screen"""
    if tft:
        center(noto_sans, message, y_pos, gc9a01.RED)

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
            # Set status LED to yellow (WiFi connected, loading data)
            # set_status_led(STATUS_YELLOW)
            time.sleep(2)
            return True
        else:
            print("Failed to connect to WiFi")
            display_message("WiFi Failed!", 100)
            # Keep status LED red
            time.sleep(2)
            return False
    else:
        print("Already connected to WiFi")
        ip = wlan.ifconfig()[0]
        print(f"IP: {ip}")
        # Set status LED to yellow (WiFi connected, loading data)
        return True

def fetch_tap_info():
    """Fetch tap information from the server"""
    global current_beer

    try:
        display_message("Fetching tap info...")
        # Keep status LED yellow while fetching
        start_connection_battery_display()

        response = requests.get(f"{SERVER_URL}/api/tap/{TAP_ID}")

        if response.status_code == 200:
            stop_connection_battery_display()
            data = response.json()
            current_beer = data
            print("Tap info:", data)

            # Download the beer image if it exists
            if data['image_path']:
                download_beer_image()

            print("Retrieved image, displaying tap info")
            display_tap_info()
            return True
        else:
            print(f"Error fetching tap info: {response.status_code}")
            display_message(f"Error: {response.status_code}")
            # Keep status LED yellow on error
            set_status_led(STATUS_RED)
            time.sleep(2)
            return False
    except Exception as e:
        print("Error fetching tap info:", e)
        display_message("Connection Error")
        # Keep status LED yellow on error
        set_status_led(STATUS_RED)
        time.sleep(2)
        return False

def get_jpeg_dimensions(filename):
    """
    Extract dimensions from a JPEG file header
    Returns (width, height) or None if dimensions can't be determined
    """
    try:
        with open(filename, "rb") as f:
            # Check for JPEG SOI marker
            if f.read(2) != b'\xFF\xD8':
                return None

            while True:
                marker = f.read(2)
                if len(marker) < 2:
                    return None

                # Check for Start of Frame markers (SOF0, SOF1, SOF2)
                if marker[0] == 0xFF and marker[1] in [0xC0, 0xC1, 0xC2]:
                    # Skip length (2 bytes)
                    f.read(2)
                    # Skip precision (1 byte)
                    f.read(1)

                    # Read height and width (2 bytes each)
                    height_bytes = f.read(2)
                    width_bytes = f.read(2)

                    height = (height_bytes[0] << 8) + height_bytes[1]
                    width = (width_bytes[0] << 8) + width_bytes[1]

                    print(f"get_jpeg_dimensions dimensions: {filename} {width}x{height}")
                    return width, height
                else:
                    # Skip this section
                    size_bytes = f.read(2)
                    if len(size_bytes) < 2:
                        return None

                    size = (size_bytes[0] << 8) + size_bytes[1] - 2
                    if size < 0:
                        return None  # Corrupt JPEG
                    f.seek(size, 1)  # Skip ahead
    except Exception as e:
        print("Error reading JPEG dimensions:", e)
        return None

def fit_image_to_display(img_width, img_height):
    """
    Calculate scaling to fit image within display while maintaining aspect ratio
    Returns: (new_width, new_height, x_offset, y_offset)
    """
    print(f"fit_image_to_display dimensions: {img_width}x{img_height}")

    # Calculate aspect ratios
    img_aspect = img_width / img_height
    display_aspect = DISPLAY_WIDTH / DISPLAY_HEIGHT

    # Determine which dimension is the limiting factor
    if img_aspect > display_aspect:
        # Image is wider than display (relative to height)
        new_width = DISPLAY_WIDTH
        new_height = int(DISPLAY_WIDTH / img_aspect)
        x_offset = 0
        y_offset = (DISPLAY_HEIGHT - new_height) // 2
    else:
        # Image is taller than display (relative to width)
        new_height = DISPLAY_HEIGHT
        new_width = int(DISPLAY_HEIGHT * img_aspect)
        y_offset = 0
        x_offset = (DISPLAY_WIDTH - new_width) // 2

    return new_width, new_height, x_offset, y_offset

def download_beer_image():
    """Download the beer image from the server"""
    global last_image

    try:
        # First attempt: Try to get a server-resized image if the feature is enabled
        if USE_SERVER_RESIZE:
            try:
                # Request pre-scaled image from server - adapt URL as needed for your server
                resized_image_path = f"{IMAGE_DIR}/{TAP_ID}_resized.jpg"

                # Remove existing image if it exists
                try:
                    os.remove(resized_image_path)
                except:
                    pass

                # Request resized image - adjust URL as needed for your API
                print("Requesting resized image from server...")
                response = requests.get(
                    f"{SERVER_URL}/api/tap/{TAP_ID}/image?width={DISPLAY_WIDTH}&height={DISPLAY_HEIGHT}")

                if response.status_code == 200:
                    with open(resized_image_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Resized image downloaded to {resized_image_path}")
                    last_image = resized_image_path
                    return True
                else:
                    print("Server resize failed, falling back to original image")
                    # Fall through to download original image
            except Exception as e:
                print("Error with server resize:", e)
                # Fall through to download original image

        # Download the original image if server resize failed or is disabled
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

    print(f"display_tap_info")

    if not tft or not current_beer:
        return

    # Clear the screen
    tft.fill(0)

    # Display beer image if available
    if last_image:
        try:
            # Get image dimensions
            dimensions = get_jpeg_dimensions(last_image)
            if dimensions:
                img_width, img_height = dimensions
                print(f"Image dimensions: {img_width}x{img_height}")

                # If image is small enough, display directly in the center
                if img_width <= DISPLAY_WIDTH and img_height <= DISPLAY_HEIGHT:
                    x_offset = (DISPLAY_WIDTH - img_width) // 2
                    y_offset = (DISPLAY_HEIGHT - img_height) // 2
                    print(f"Displaying image centered at ({x_offset},{y_offset})")
                    tft.jpg(last_image, x_offset, y_offset, gc9a01.SLOW)
                else:
                    # For larger images, we need a display strategy
                    # Since we can't scale without jpegdec, we'll center and crop
                    #                     display_scaled_image(last_image)
                    print("Image larger than display, centering and displaying")

                    # Calculate center points
                    img_center_x = img_width // 2
                    img_center_y = img_height // 2

                    # Calculate x and y offsets as negative values
                    # This effectively crops to the center of the image
                    x_offset = -(img_center_x - DISPLAY_WIDTH // 2)
                    y_offset = -(img_center_y - DISPLAY_HEIGHT // 2)

                    print(f"Centering large image with offset ({x_offset},{y_offset})")
                    tft.jpg(last_image, x_offset, y_offset, gc9a01.SLOW)
            else:
                # Can't determine dimensions, just display at 0,0
                print("Unable to determine image dimensions, displaying at origin")
                tft.jpg(last_image, 0, 0, gc9a01.FAST)
        except Exception as e:
            print("Error displaying image:", e)

    # Calculate remaining beer percentage
    if current_beer['volume'] > 0:
        # Assume a keg is typically 5000ml (5L) when full
        remaining_percent = min(100, int((current_beer['volume'] / current_beer['full_volume']) * 100))
    else:
        remaining_percent = 0

    # Update the keg level LEDs
    set_keg_level_leds(remaining_percent)

    # Display beer information as overlay
    y_offset = 180
    center(noto_sans, current_beer['beer_name'] or "No beer", 50, gc9a01.WHITE)
    center(noto_sans,f"{current_beer['beer_abv']}% ABV" if current_beer['beer_abv'] else "", y_offset, gc9a01.WHITE)
#     center(noto_sans, f"Left: {remaining_percent}%", 20 + y_offset, gc9a01.WHITE)

    print_battery_info()

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

def set_battery_level_leds_connecting(battery_percentage):
    """Set LEDs to show battery level during connection with blinking top LED"""
    global connection_blink_state

    # Calculate how many LEDs should be lit based on battery percentage
    if battery_percentage > 0:
        leds_to_light = max(1, int((battery_percentage / 100.0) * LED_COUNT))
    else:
        leds_to_light = 0

    print(f"Connection battery display: {battery_percentage}% = {leds_to_light} LEDs")

    for i in range(LED_COUNT):
        if i < leds_to_light - 1:
            # Static yellow LEDs for all but the top one
            status_leds[i] = STATUS_YELLOW
        elif i == leds_to_light - 1:
            # Top LED blinks
            if connection_blink_state:
                status_leds[i] = STATUS_YELLOW
            else:
                status_leds[i] = KEG_EMPTY  # Off
        else:
            # Turn off LEDs that shouldn't be lit
            status_leds[i] = KEG_EMPTY

    status_leds.write()

def connection_blink_callback(timer):
    """Timer callback to handle blinking during connection"""
    global connection_blink_state

    connection_blink_state = not connection_blink_state

    print("connection_blink_callback")

    # Get current battery status and update LEDs
    battery_info = get_battery_status()
    set_battery_level_leds_connecting(battery_info['percentage'])

def start_connection_battery_display():
    """Start the battery level display during connection"""
    global connection_blink_timer

    print("start_connection_battery_display")

    # Initialize battery display
    battery_info = get_battery_status()
    set_battery_level_leds_connecting(battery_info['percentage'])

    # Start blinking timer (blink every 500ms)
    connection_blink_timer = Timer(1)
    connection_blink_timer.init(period=500, mode=Timer.PERIODIC, callback=connection_blink_callback)

def stop_connection_battery_display():
    """Stop the battery level display and clean up timer"""
    global connection_blink_timer

    print("start_connection_battery_display")

    if connection_blink_timer:
        connection_blink_timer.deinit()
        connection_blink_timer = None
    else:
        print("start_connection_battery_display NO TIMER TO STOP")

def main():
    """Main function to initialize and run the system"""
    global timer_flow

    init_battery_monitor()

    # Initialize status LED to red (starting state)
    set_status_led(STATUS_RED)

    # Initialize hardware
    if not init_display():
        print("Failed to initialize display, can't continue")
        return

    # Setup flow sensor interrupt
    flow_pin.irq(trigger=Pin.IRQ_FALLING, handler=flow_callback)

    # Create timer for flow detection
    timer_flow = Timer(0)

    start_connection_battery_display()

    # Connect to WiFi
    if not connect_wifi():
        print("Failed to connect to WiFi, retrying in 5 seconds")
        time.sleep(5)
        if not connect_wifi():
            print("Failed to connect to WiFi again, can't continue")
            display_message("WiFi Failed!", 100)
            # Keep status LED red
            set_status_led(STATUS_RED)
            return

    stop_connection_battery_display()

    # Initial fetch of tap info
    if not fetch_tap_info():
        print("Failed to fetch tap info, can't continue")
        # Keep status LED yellow on failure
        set_status_led(STATUS_YELLOW)
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
        # Set status LED to red on fatal error
        set_status_led(STATUS_RED)
