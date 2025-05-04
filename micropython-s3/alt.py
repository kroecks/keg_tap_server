# main.py for ESP32 S3 with 240x240 display for Keg Tap monitoring
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
from machine import Pin, SPI, Timer, freq
import gc9a01
try:
    import jpegdec
except ImportError:
    print("jpegdec module not available, using builtin jpeg support")
    jpegdec = None

# Set CPU frequency to 240MHz for better performance
freq(240000000)

# Configuration
WIFI_SSID = "Nexus"
WIFI_PASSWORD = "thescaryd00r"
SERVER_URL = "http://beerpi:5000"  # Replace with your Raspberry Pi IP
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

            print("Retrieved image, displaying tap info")
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

def fit_image_to_display(img_width, img_height, display_width=DISPLAY_WIDTH, display_height=DISPLAY_HEIGHT):
    """
    Calculate the dimensions to fit an image within the display while maintaining aspect ratio
    Returns: (new_width, new_height, x_offset, y_offset)
    """
    # Calculate aspect ratios
    img_aspect = img_width / img_height
    display_aspect = display_width / display_height

    # Determine which dimension is the limiting factor
    if img_aspect > display_aspect:
        # Image is wider than display (relative to height)
        new_width = display_width
        new_height = int(display_width / img_aspect)
        x_offset = 0
        y_offset = (display_height - new_height) // 2
    else:
        # Image is taller than display (relative to width)
        new_height = display_height
        new_width = int(display_height * img_aspect)
        y_offset = 0
        x_offset = (display_width - new_width) // 2

    return new_width, new_height, x_offset, y_offset

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
    print("display tap info")
    """Display the current tap information and beer image"""
    global tft, current_beer, last_image

    if not tft or not current_beer:
        return

    # Clear the screen
    tft.fill(0)

    print("display image")
    # Display beer image if available
    if last_image:
        try:
            display_scaled_image(last_image)
        except Exception as e:
            print("Error displaying image:", e)

    print("finished display image")

    # Calculate remaining beer percentage
    if current_beer['volume'] > 0:
        # Assume a keg is typically 5000ml (5L) when full
        full_volume = 5000  # Can be adjusted
        remaining_percent = min(100, int((current_beer['volume'] / full_volume) * 100))
    else:
        remaining_percent = 0

    # Display beer information as overlay
    y_offset = 180
    center(noto_sans, current_beer['beer_name'] or "No beer", 10 + y_offset, gc9a01.WHITE)
    center(noto_sans,f"{current_beer['beer_abv']}% ABV" if current_beer['beer_abv'] else "", 25 + y_offset, gc9a01.WHITE)
    center(noto_sans, f"Left: {remaining_percent}%", 40 + y_offset, gc9a01.WHITE)

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

                # Check for Start of Frame markers
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

                    return width, height
                else:
                    # Skip this section
                    size_bytes = f.read(2)
                    if len(size_bytes) < 2:
                        return None

                    size = (size_bytes[0] << 8) + size_bytes[1] - 2
                    f.seek(size, 1)  # Skip ahead
    except Exception as e:
        print("Error reading JPEG dimensions:", e)
        return None

def display_scaled_image(image_path):
    """Display an image scaled to fit the display"""
    if not tft:
        return

    # Get image dimensions
    dimensions = get_jpeg_dimensions(image_path)
    if not dimensions:
        print("Could not determine image dimensions")
        # Fall back to using the full display size
        tft.jpg(image_path, 0, 0, gc9a01.SLOW)
        return

    img_width, img_height = dimensions
    print(f"Original image dimensions: {img_width}x{img_height}")

    # Calculate scaling parameters
    new_width, new_height, x_offset, y_offset = fit_image_to_display(img_width, img_height)
    print(f"Scaled dimensions: {new_width}x{new_height}, offset: ({x_offset},{y_offset})")

    # Clear the image area
    tft.fill_rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, 0)  # Black background

    # If jpegdec module is available, use it for better scaling
    if jpegdec:
        try:
            jpeg = jpegdec.JPEG(tft)
            jpeg.open(image_path)
            jpeg.scale(new_width / img_width)
            jpeg.decode(x_offset, y_offset)
        except Exception as e:
            print("Error with jpegdec:", e)
            # Fall back to built-in method
            tft.jpg(image_path, x_offset, y_offset, gc9a01.SLOW)
    else:
        # Use built-in JPG method - note this may not respect scaling
        # but will at least center the image
        tft.jpg(image_path, x_offset, y_offset, gc9a01.SLOW)

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