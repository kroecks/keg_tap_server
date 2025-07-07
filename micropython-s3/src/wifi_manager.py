# wifi_manager.py - WiFi connection management
import network
import time
from config import WIFI_SSID, WIFI_PASSWORD

class WiFiManager:
    def __init__(self, display_manager):
        self.display_manager = display_manager
        self.wlan = network.WLAN(network.STA_IF)

    def connect(self):
        """Connect to WiFi network"""
        self.display_manager.display_message("Connecting to WiFi...")

        self.wlan.active(True)

        if not self.wlan.isconnected():
            print("Connecting to WiFi...")
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)

            # Wait for connection with timeout
            max_wait = 20
            while max_wait > 0:
                if self.wlan.isconnected():
                    break
                max_wait -= 1
                print("Waiting for connection...")
                time.sleep(1)

            if self.wlan.isconnected():
                print("Connected to WiFi")
                ip = self.wlan.ifconfig()[0]
                print(f"IP: {ip}")
                self.display_manager.display_message(f"Connected: {ip}", 100)
                time.sleep(2)
                return True
            else:
                print("Failed to connect to WiFi")
                self.display_manager.display_message("WiFi Failed!", 100)
                time.sleep(2)
                return False
        else:
            print("Already connected to WiFi")
            ip = self.wlan.ifconfig()[0]
            print(f"IP: {ip}")
            return True

    def is_connected(self):
        """Check if WiFi is connected"""
        return self.wlan.isconnected()

    def get_ip(self):
        """Get current IP address"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None