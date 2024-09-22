# locness-pico-fluorologger
# Brett Longworth
#
# Turner Cyclops 7 flurometer interface
# read and store voltage and time
# control fluormeter gain
 
import time
import board
import busio
import digitalio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_sdcard
import storage
import adafruit_pcf8523
import alarm

# Set up I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Set up ADS1115
ads = ADS.ADS1115(i2c)

# Set up analog input on ADS1115
chan = AnalogIn(ads, ADS.P0)

# Set up digital outputs for gain control
# TODO: Check polarity of control signals
gain_1x = digitalio.DigitalInOut(board.D2)
gain_10x = digitalio.DigitalInOut(board.D3)
gain_100x = digitalio.DigitalInOut(board.D4)
gain_1x.direction = digitalio.Direction.OUTPUT
gain_10x.direction = digitalio.Direction.OUTPUT
gain_100x.direction = digitalio.Direction.OUTPUT

# Set up SD card
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D10)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# Set up RTC
rtc = adafruit_pcf8523.PCF8523(i2c)

# Initialize gain to 1x
current_gain = 1
gain_1x.value = True
gain_10x.value = False
gain_100x.value = False

def set_gain(gain):
    global current_gain
    if gain == 1:
        gain_1x.value = True
        gain_10x.value = False
        gain_100x.value = False
        current_gain = 1
    elif gain == 10:
        gain_1x.value = False
        gain_10x.value = True
        gain_100x.value = False
        current_gain = 10
    elif gain == 100:
        gain_1x.value = False
        gain_10x.value = False
        gain_100x.value = True
        current_gain = 100

def get_average_voltage(num_samples=10):
    total = 0
    for _ in range(num_samples):
        total += chan.voltage
        time.sleep(0.01)
    return total / num_samples
 
# Set the interval for data collection (in seconds)
INTERVAL = 1.0

# Create a time alarm
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + INTERVAL)

# main loop
while True:
    # Light sleep until the alarm goes off
    # TODO: test whether light sleep affects digital outs
    alarm.light_sleep_until_alarms(time_alarm)
    
    # Ensure gain is set correctly after wake-up
    # will reset gain if lost during light sleep-
    # but fluorometer needs settling time
    # set_gain(current_gain)

    voltage = get_average_voltage()
    
    # Get current time from RTC
    t = rtc.datetime
    
    # Create output string
    output = f"{t},{current_gain},{voltage:.3f}"
    
    # Write to SD card
    # TODO: write header if new file
    with open("/sd/voltage_log.csv", "a") as f:
        f.write(output + "\n")
    
    # Print to serial monitor
    # TODO: Use second serial port
    # TODO: Format for meshtastic or use protobufs
    # TODO: Get GPS data from gps or radio serial
    # can use spot trace data for post-processing
    print(output)
    
    # Adjust gain if necessary
    if voltage > 2.5 and current_gain > 1:
        set_gain(current_gain // 10)
    elif voltage < 0.5 and current_gain < 100:
        set_gain(current_gain * 10)
    
    # Reset the alarm for the next interval
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + INTERVAL)   # TODO: use scheduler to run on every second