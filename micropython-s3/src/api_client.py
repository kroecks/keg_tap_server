# network_manager.py - Network and API management

import network
import urequests as requests
import json
import os
import time
from config import (WIFI_SSID, WIFI_PASSWORD, SERVER_URL, TAP_ID,
                    IMAGE_DIR, USE_SERVER_RESIZE, DISPLAY_WIDTH, DISPLAY_HEIGHT)

import urequests as requests
import json
import os
from config import SERVER_URL, TAP_ID, IMAGE_DIR, USE_SERVER_RESIZE, DISPLAY_WIDTH, DISPLAY_HEIGHT
from config import STATUS_YELLOW, STATUS_RED

class APIClient:
    def __init__(self, display_manager, led_controller, battery_monitor):
        self.display_manager = display_manager
        self.led_controller = led_controller
        self.battery_monitor = battery_monitor
        self.current_beer = None

    def fetch_tap_info(self):
        """Fetch tap information from the server"""
        try:
            print("Fetching tap info...")
            self.display_manager.display_message("Fetching tap info...")
            # Keep status LED yellow while fetching
            self.led_controller.start_connection_battery_display(self.battery_monitor)

            response = requests.get(f"{SERVER_URL}/api/tap/{TAP_ID}")

            print(f"Response code {response.status_code}...")
            if response.status_code == 200:
                data = response.json()
                self.current_beer = data
                print("Tap info:", data)

                # Download the beer image if it exists
                if data['image_path']:
                    self.download_beer_image()

                print("Retrieved image, displaying tap info")
                self.led_controller.stop_connection_battery_display()
                self.display_manager.display_tap_info(data)
                # Calculate remaining beer percentage
                if self.current_beer['volume'] > 0:
                    remaining_percent = min(100, int((self.current_beer['volume'] / self.current_beer['full_volume']) * 100))
                else:
                    remaining_percent = 0

                # Update the keg level LEDs

                self.led_controller.set_keg_level_leds(remaining_percent)
                return True, data
            else:
                print(f"Error fetching tap info: {response.status_code}")
                self.display_manager.display_message(f"Error: {response.status_code}")
                self.led_controller.stop_connection_battery_display()
                self.led_controller.set_status_led(STATUS_RED)
                return False, None
        except Exception as e:
            print("Error fetching tap info:", e)
            self.display_manager.display_message(f"Connection Error")
            self.led_controller.stop_connection_battery_display()
            self.led_controller.set_status_led(STATUS_RED)
            return False, None

    def download_beer_image(self):
        """Download the beer image from the server"""
        try:
            # First attempt: Try to get a server-resized image if the feature is enabled
            if USE_SERVER_RESIZE:
                try:
                    # Request pre-scaled image from server
                    resized_image_path = f"{IMAGE_DIR}/{TAP_ID}_resized.jpg"

                    # Remove existing image if it exists
                    try:
                        os.remove(resized_image_path)
                    except:
                        pass

                    # Request resized image
                    print("Requesting resized image from server...")
                    response = requests.get(
                        f"{SERVER_URL}/api/tap/{TAP_ID}/image?width={DISPLAY_WIDTH}&height={DISPLAY_HEIGHT}")

                    if response.status_code == 200:
                        with open(resized_image_path, 'wb') as f:
                            f.write(response.content)
                        print(f"Resized image downloaded to {resized_image_path}")
                        self.display_manager.set_last_image(resized_image_path)
                        return True, resized_image_path
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
                self.display_manager.set_last_image(image_path)
                return True, image_path
            else:
                print(f"Error downloading image: {response.status_code}")
                return False, None
        except Exception as e:
            print("Error downloading image:", e)
            return False, None

    def report_pour_event(self, event_type, duration=None):
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
                return True
            else:
                print(f"Error reporting pour event: {response.status_code}")
                return False
        except Exception as e:
            print("Error reporting pour event:", e)
            return False

    def is_connected(self):
        """Check if WiFi is still connected"""
        return self.wlan and self.wlan.isconnected()

    def get_current_beer(self):
        """Get the current beer data"""
        return self.current_beer