# battery_monitor.py - Battery monitoring functionality
import time
from machine import Pin, ADC
from config import BATTERY_ADC_PIN, BATTERY_MIN_VOLTAGE, BATTERY_MAX_VOLTAGE

class BatteryMonitor:
    def __init__(self):
        self.battery_adc = None
        self.battery_connected = False
        self.battery_voltage = 0.0
        self.battery_percentage = 0

        self.init_battery_monitor()

    def init_battery_monitor(self):
        """Initialize battery monitoring"""
        try:
            # Initialize ADC for battery monitoring on GPIO1
            self.battery_adc = ADC(Pin(BATTERY_ADC_PIN))
            self.battery_adc.atten(ADC.ATTN_11DB)  # For 3.3V reference, allows reading up to ~3.9V

            # Take initial reading to check if battery is connected
            test_voltage = self.read_battery_voltage()

            # If voltage is above a threshold, assume battery is connected
            if test_voltage > 2.5:  # Adjust threshold as needed
                self.battery_connected = True
                print(f"Battery detected: {test_voltage:.2f}V")
            else:
                self.battery_connected = False
                print("No battery detected")

            return True
        except Exception as e:
            print(f"Error initializing battery monitor: {e}")
            self.battery_connected = False
            return False

    def read_battery_voltage(self):
        """Read battery voltage from ADC using the board's specific conversion formula"""
        if not self.battery_adc:
            return 0.0

        try:
            # Take multiple readings and average them for stability
            readings = []
            for _ in range(5):
                raw_value = self.battery_adc.read()
                readings.append(raw_value)
                time.sleep_ms(10)

            avg_reading = sum(readings) / len(readings)

            # Use the conversion formula from the wiki:
            # voltage = 3.3 / (1<<12) * 3 * AD_Value
            # This accounts for the 200K+100K voltage divider (factor of 3)
            voltage = (3.3 / (1 << 12)) * 3 * avg_reading

            self.battery_voltage = voltage
            return voltage
        except Exception as e:
            print(f"Error reading battery voltage: {e}")
            return 0.0

    def calculate_battery_percentage(self):
        """Calculate battery percentage based on voltage"""
        if not self.battery_connected or self.battery_voltage == 0:
            self.battery_percentage = 0
            return 0

        # Linear interpolation between min and max voltage
        if self.battery_voltage >= BATTERY_MAX_VOLTAGE:
            self.battery_percentage = 100
        elif self.battery_voltage <= BATTERY_MIN_VOLTAGE:
            self.battery_percentage = 0
        else:
            voltage_range = BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE
            current_range = self.battery_voltage - BATTERY_MIN_VOLTAGE
            self.battery_percentage = int((current_range / voltage_range) * 100)

        return self.battery_percentage

    def get_battery_status(self):
        """Get complete battery status"""
        if not self.battery_connected:
            return {
                'connected': False,
                'voltage': 0.0,
                'percentage': 0,
                'status': 'Not connected'
            }

        voltage = self.read_battery_voltage()
        percentage = self.calculate_battery_percentage()

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

    def print_battery_info(self):
        """Print battery information to console"""
        battery_info = self.get_battery_status()

        if battery_info['connected']:
            print(f"Battery: {battery_info['voltage']:.2f}V ({battery_info['percentage']}%) - {battery_info['status']}")
        else:
            print("Battery: Not connected")

        return battery_info