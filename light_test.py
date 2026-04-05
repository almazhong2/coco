import time
import board
import neopixel

PIXEL_PIN = board.D18   # GPIO18 (pin 12)
NUM_PIXELS = 240

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=0.2,
    auto_write=True
)

# Test 1: All red
pixels.fill((255, 0, 0))
time.sleep(1)

# Test 2: All green
pixels.fill((0, 255, 0))
time.sleep(1)

# Test 3: All blue
pixels.fill((0, 0, 255))
time.sleep(1)

# Test 4: One-by-one white
pixels.fill((0, 0, 0))
for i in range(NUM_PIXELS):
    pixels[i] = (255, 0, 0)
    pixels[i+1] = (255, 0, 0)
    time.sleep(0.05)
    pixels[i] = (0, 0, 0)

    pixels[NUM_PIXELS-1] = (0, 0, 0)

# Turn off
pixels.fill((0, 0, 0))
