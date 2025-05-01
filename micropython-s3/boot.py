# boot.py - ESP32 S3 startup file
import time
import machine
import gc
import esp32

# Increase clock speed for better performance
machine.freq(240000000)

# Configure to be more memory efficient
gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

# Print system info
print("Starting Keg Tap Display System")
print("Memory Free:", gc.mem_free())
print("ESP32 Flash Size:", esp32.flash_size())

# Provide some time for system to initialize
time.sleep(1)

# Force garbage collection before main.py runs
gc.collect()