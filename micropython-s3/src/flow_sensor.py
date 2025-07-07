# flow_sensor.py - Flow sensor management
import time
from machine import Pin, Timer
from config import FLOW_SENSOR_PIN, FLOW_DETECTION_THRESHOLD, FLOW_TIMEOUT

class FlowSensor:
    def __init__(self, api_client):
        self.api_client = api_client
        self.flow_pin = Pin(FLOW_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
        self.flow_count = 0
        self.flow_start_time = 0
        self.flow_active = False
        self.timer_flow = Timer(0)

        # Setup flow sensor interrupt
        self.flow_pin.irq(trigger=Pin.IRQ_FALLING, handler=self.flow_callback)

    def flow_callback(self, p):
        """Interrupt handler for flow sensor pulses"""
        self.flow_count += 1

        # If flow wasn't active, mark it as started
        if not self.flow_active and self.flow_count >= FLOW_DETECTION_THRESHOLD:
            self.flow_active = True
            self.flow_start_time = time.ticks_ms()
            print("Flow started")

            # Start the timer to check for flow stop
            self.timer_flow.init(period=FLOW_TIMEOUT, mode=Timer.PERIODIC, callback=self.check_flow_stop)

    def check_flow_stop(self, t):
        """Timer callback to check if flow has stopped"""
        # Store the count and reset for next check
        current_count = self.flow_count
        self.flow_count = 0

        if self.flow_active and current_count < FLOW_DETECTION_THRESHOLD:
            # Flow has stopped
            self.flow_active = False
            flow_duration = (time.ticks_ms() - self.flow_start_time) / 1000  # Convert to seconds
            print(f"Flow stopped after {flow_duration} seconds")

            # Stop the timer
            self.timer_flow.deinit()

            # Report to server
            self.api_client.report_pour_event("stop", flow_duration)