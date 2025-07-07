# main.py - Main entry point for ESP32 Keg Tap Monitor
import gc
import time
from machine import Pin, Timer, freq
from config import *
from wifi_manager import WiFiManager
from display_manager import DisplayManager
from battery_monitor import BatteryMonitor
from led_controller import LEDController
from flow_sensor import FlowSensor
from api_client import APIClient

# Set CPU frequency to 240MHz for better performance
# freq(240000000)

# Global objects
wifi_manager = None
display_manager = None
battery_monitor = None
led_controller = None
flow_sensor = None
api_client = None

def initialize_hardware():
    """Initialize all hardware components"""
    global wifi_manager, display_manager, battery_monitor, led_controller, flow_sensor, api_client

    # Initialize battery monitor
    battery_monitor = BatteryMonitor()

    # Initialize LED controller
    led_controller = LEDController()
    led_controller.set_status_led(STATUS_RED)  # Starting state

    # Initialize display
    display_manager = DisplayManager()
    if not display_manager.init_display():
        print("Failed to initialize display, can't continue")
        return False

    # Initialize WiFi manager
    wifi_manager = WiFiManager(display_manager)

    # Initialize API client
    api_client = APIClient(display_manager, led_controller, battery_monitor)

    # Initialize flow sensor
    flow_sensor = FlowSensor(api_client)

    return True

def main():
    """Main function to initialize and run the system"""
    gc.enable()
    gc.collect()

    # Initialize all hardware
    if not initialize_hardware():
        print("Failed to initialize hardware")
        return

    # Start battery display during connection
    led_controller.start_connection_battery_display(battery_monitor)

    # Connect to WiFi
    if not wifi_manager.connect():
        print("Failed to connect to WiFi, retrying in 5 seconds")
        time.sleep(5)
        if not wifi_manager.connect():
            print("Failed to connect to WiFi again, can't continue")
            display_manager.display_message("WiFi Failed!", 100)
            led_controller.set_status_led(STATUS_RED)
            return

    # Stop battery display
    led_controller.stop_connection_battery_display()

    # Initial fetch of tap info
    if not api_client.fetch_tap_info():
        print("Failed to fetch tap info, can't continue")
        led_controller.set_status_led(STATUS_YELLOW)
        return

    # Main loop
    refresh_interval = 60  # seconds between refreshes
    last_refresh = time.time()

    while True:
        # Periodically refresh tap info
        current_time = time.time()
        if current_time - last_refresh >= refresh_interval:
            print("Refreshing tap info...")
            api_client.fetch_tap_info()
            last_refresh = current_time

        # Give some time to other tasks
        time.sleep(1)
        gc.collect()  # Run garbage collection to free memory

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Fatal error:", e)
        if display_manager:
            display_manager.display_message(f"Error: {e}", 100)
        if led_controller:
            led_controller.set_status_led(STATUS_RED)