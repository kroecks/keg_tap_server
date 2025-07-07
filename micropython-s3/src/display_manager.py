# display_manager.py - Display management
import os
from machine import Pin, SPI
import gc9a01
from truetype import NotoSans_32 as noto_sans
from config import DISPLAY_WIDTH, DISPLAY_HEIGHT, IMAGE_DIR

class DisplayManager:
    def __init__(self):
        self.tft = None
        self.last_image = None
        self.current_beer = None

        # Create image directory
        try:
            os.mkdir(IMAGE_DIR)
        except:
            pass  # Directory already exists

    def init_display(self):
        """Initialize the display hardware"""
        try:
            print("Init display 1...")
            # Initialize display
            self.tft = gc9a01.GC9A01(
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
            self.tft.init()
            print("Init display 3...")
            self.tft.fill(0)  # Clear screen with black
            print("Init display 4...")
            self.display_message("Connecting...")
            return True
        except Exception as e:
            print("Display initialization error:", e)
            return False

    def center(self, font, s, row, color=gc9a01.WHITE):
        """Center text on the display"""
        screen = self.tft.width()                     # get screen width
        width = self.tft.write_len(font, s)           # get the width of the string
        if width and width < screen:                  # if the string < display
            col = self.tft.width() // 2 - width // 2  # find the column to center
        else:                                         # otherwise
            col = 0                                   # left justify

        self.tft.write(font, s, col, row, color)      # and write the string

    def display_message(self, message, y_pos=120):
        """Display a centered message on the screen"""
        if self.tft:
            self.center(noto_sans, message, y_pos, gc9a01.RED)

    def get_jpeg_dimensions(self, filename):
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

    def display_tap_info(self, beer_data, battery_info=None):
        """Display the current tap information and beer image"""
        if not self.tft or not beer_data:
            return

        self.current_beer = beer_data

        # Clear the screen
        self.tft.fill(0)

        # Display beer image if available
        if self.last_image:
            try:
                # Get image dimensions
                dimensions = self.get_jpeg_dimensions(self.last_image)
                if dimensions:
                    img_width, img_height = dimensions
                    print(f"Image dimensions: {img_width}x{img_height}")

                    # If image is small enough, display directly in the center
                    if img_width <= DISPLAY_WIDTH and img_height <= DISPLAY_HEIGHT:
                        x_offset = (DISPLAY_WIDTH - img_width) // 2
                        y_offset = (DISPLAY_HEIGHT - img_height) // 2
                        print(f"Displaying image centered at ({x_offset},{y_offset})")
                        self.tft.jpg(self.last_image, x_offset, y_offset, gc9a01.SLOW)
                    else:
                        # For larger images, center and crop
                        print("Image larger than display, centering and displaying")

                        # Calculate center points
                        img_center_x = img_width // 2
                        img_center_y = img_height // 2

                        # Calculate x and y offsets as negative values
                        x_offset = -(img_center_x - DISPLAY_WIDTH // 2)
                        y_offset = -(img_center_y - DISPLAY_HEIGHT // 2)

                        print(f"Centering large image with offset ({x_offset},{y_offset})")
                        self.tft.jpg(self.last_image, x_offset, y_offset, gc9a01.SLOW)
                else:
                    # Can't determine dimensions, just display at 0,0
                    print("Unable to determine image dimensions, displaying at origin")
                    self.tft.jpg(self.last_image, 0, 0, gc9a01.FAST)
            except Exception as e:
                print("Error displaying image:", e)
        else:
            print("ERROR! Last image not found!")

        # Display beer information as overlay
        self.center(noto_sans, beer_data['beer_name'] or "No beer", 50, gc9a01.WHITE)
        self.center(noto_sans, f"{beer_data['beer_abv']}% ABV" if beer_data['beer_abv'] else "", 180, gc9a01.WHITE)

        # Display battery info if connected and provided
        if battery_info and battery_info['connected']:
            battery_text = f"Batt: {battery_info['percentage']}%"
            self.center(noto_sans, battery_text, 200, gc9a01.YELLOW)

    def set_last_image(self, image_path):
        """Set the last downloaded image path"""
        self.last_image = image_path