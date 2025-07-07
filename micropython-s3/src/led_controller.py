# led_controller.py - LED control functionality
import neopixel
from machine import Pin, Timer
from config import STATUS_LED_PIN, LED_COUNT, STATUS_RED, STATUS_YELLOW, STATUS_GREEN
from config import KEG_FULL, KEG_MEDIUM, KEG_LOW, KEG_EMPTY

class LEDController:
    def __init__(self):
        self.status_leds = neopixel.NeoPixel(Pin(STATUS_LED_PIN), LED_COUNT)
        self.connection_blink_timer = None
        self.connection_blink_state = False

    def set_status_led(self, color):
        """Set all LEDs to the same color for status indication"""
        print(f"set_status_led : {color}")

        for i in range(LED_COUNT):
            self.status_leds[i] = color
        self.status_leds.write()

    def set_keg_level_leds(self, remaining_percent):
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
                    self.status_leds[i] = KEG_LOW
                elif led_position_percent <= 75:
                    # Middle 50% - Yellow (medium)
                    self.status_leds[i] = KEG_MEDIUM
                else:
                    # Top 25% - Green (full)
                    self.status_leds[i] = KEG_FULL
            else:
                # Turn off LEDs that shouldn't be lit
                self.status_leds[i] = KEG_EMPTY

        self.status_leds.write()

    def set_battery_level_leds_connecting(self, battery_percentage):
        """Set LEDs to show battery level during connection with blinking top LED"""
        # Calculate how many LEDs should be lit based on battery percentage
        if battery_percentage > 0:
            leds_to_light = max(1, int((battery_percentage / 100.0) * LED_COUNT))
        else:
            leds_to_light = 0

        print(f"Connection battery display: {battery_percentage}% = {leds_to_light} LEDs")

        for i in range(LED_COUNT):
            if i < leds_to_light - 1:
                # Static yellow LEDs for all but the top one
                self.status_leds[i] = STATUS_YELLOW
            elif i == leds_to_light - 1:
                # Top LED blinks
                if self.connection_blink_state:
                    self.status_leds[i] = STATUS_YELLOW
                else:
                    self.status_leds[i] = KEG_EMPTY  # Off
            else:
                # Turn off LEDs that shouldn't be lit
                self.status_leds[i] = KEG_EMPTY

        self.status_leds.write()

    def connection_blink_callback(self, timer):
        """Timer callback to handle blinking during connection"""
        self.connection_blink_state = not self.connection_blink_state

        print("connection_blink_callback")

        # Get current battery status and update LEDs
        # Note: We need to pass the battery monitor to get current status
        if hasattr(self, '_battery_monitor'):
            battery_info = self._battery_monitor.get_battery_status()
            self.set_battery_level_leds_connecting(battery_info['percentage'])

    def start_connection_battery_display(self, battery_monitor):
        """Start the battery level display during connection"""
        print("start_connection_battery_display")

        # Store reference to battery monitor for callback
        self._battery_monitor = battery_monitor

        # Initialize battery display
        battery_info = battery_monitor.get_battery_status()
        self.set_battery_level_leds_connecting(battery_info['percentage'])

        # Start blinking timer (blink every 500ms)
        self.connection_blink_timer = Timer(1)
        self.connection_blink_timer.init(period=500, mode=Timer.PERIODIC, callback=self.connection_blink_callback)

    def stop_connection_battery_display(self):
        """Stop the battery level display and clean up timer"""
        print("stop_connection_battery_display")

        if self.connection_blink_timer:
            self.connection_blink_timer.deinit()
            self.connection_blink_timer = None
        else:
            print("stop_connection_battery_display NO TIMER TO STOP")

        # Clear battery monitor reference
        if hasattr(self, '_battery_monitor'):
            delattr(self, '_battery_monitor')