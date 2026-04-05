import time
import board
import neopixel
import RPi.GPIO as GPIO
import pygame

# configuration
PIXEL_PIN = board.D18
NUM_PIXELS = 240
BUTTON_PIN = 17

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=0.1,
    auto_write=True
)

# button setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# red = 0-59
# yellow = 60-119
# green = 120-179
# blue = 180-239


def strum_red(pixels, speed):
    OFF = (0, 0, 0)
    RED = (255, 0, 0)

    for i in range(0, 64):
        if 0 <= i <= 59:
            pixels[i] = RED
        if 0 <= i - 1 <= 59:
            pixels[i - 1] = RED
        if 0 <= i - 2 <= 59:
            pixels[i - 2] = RED
        if 0 <= i - 3 <= 59:
            pixels[i - 3] = RED
        if 0 <= i - 4 <= 59:
            pixels[i - 4] = RED

        time.sleep(speed)

        if 0 <= i <= 59:
            pixels[i] = OFF
        if 0 <= i - 1 <= 59:
            pixels[i - 1] = OFF
        if 0 <= i - 2 <= 59:
            pixels[i - 2] = OFF
        if 0 <= i - 3 <= 59:
            pixels[i - 3] = OFF
        if 0 <= i - 4 <= 59:
            pixels[i - 4] = OFF


def strum_yellow(pixels, speed):
    OFF = (0, 0, 0)
    YELLOW = (255, 255, 0)

    for i in range(123, 59, -1):
        if 60 <= i <= 119:
            pixels[i] = YELLOW
        if 60 <= i - 1 <= 119:
            pixels[i - 1] = YELLOW
        if 60 <= i - 2 <= 119:
            pixels[i - 2] = YELLOW
        if 60 <= i - 3 <= 119:
            pixels[i - 3] = YELLOW
        if 60 <= i - 4 <= 119:
            pixels[i - 4] = YELLOW

        time.sleep(speed)

        if 60 <= i <= 119:
            pixels[i] = OFF
        if 60 <= i - 1 <= 119:
            pixels[i - 1] = OFF
        if 60 <= i - 2 <= 119:
            pixels[i - 2] = OFF
        if 60 <= i - 3 <= 119:
            pixels[i - 3] = OFF
        if 60 <= i - 4 <= 119:
            pixels[i - 4] = OFF


def strum_green(pixels, speed):
    OFF = (0, 0, 0)
    GREEN = (0, 255, 0)

    for i in range(120, 184):
        if 120 <= i <= 179:
            pixels[i] = GREEN
        if 120 <= i - 1 <= 179:
            pixels[i - 1] = GREEN
        if 120 <= i - 2 <= 179:
            pixels[i - 2] = GREEN
        if 120 <= i - 3 <= 179:
            pixels[i - 3] = GREEN
        if 120 <= i - 4 <= 179:
            pixels[i - 4] = GREEN

        time.sleep(speed)

        if 120 <= i <= 179:
            pixels[i] = OFF
        if 120 <= i - 1 <= 179:
            pixels[i - 1] = OFF
        if 120 <= i - 2 <= 179:
            pixels[i - 2] = OFF
        if 120 <= i - 3 <= 179:
            pixels[i - 3] = OFF
        if 120 <= i - 4 <= 179:
            pixels[i - 4] = OFF


def strum_blue(pixels, speed):
    OFF = (0, 0, 0)
    BLUE = (0, 0, 255)

    for i in range(243, 179, -1):
        if 180 <= i <= 239:
            pixels[i] = BLUE
        if 180 <= i - 1 <= 239:
            pixels[i - 1] = BLUE
        if 180 <= i - 2 <= 239:
            pixels[i - 2] = BLUE
        if 180 <= i - 3 <= 239:
            pixels[i - 3] = BLUE
        if 180 <= i - 4 <= 239:
            pixels[i - 4] = BLUE

        time.sleep(speed)

        if 180 <= i <= 239:
            pixels[i] = OFF
        if 180 <= i - 1 <= 239:
            pixels[i - 1] = OFF
        if 180 <= i - 2 <= 239:
            pixels[i - 2] = OFF
        if 180 <= i - 3 <= 239:
            pixels[i - 3] = OFF
        if 180 <= i - 4 <= 239:
            pixels[i - 4] = OFF


try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print("pressed!")

            pygame.mixer.init()
            pygame.mixer.music.load("song cut.mp3")
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(loops=1)

            # example test calls
            # strum_red(pixels, 0.05)
            # strum_yellow(pixels, 0.05)
            # strum_green(pixels, 0.05)
            # strum_blue(pixels, 0.05)
            strum_red(pixels, 0.02)
            strum_yellow(pixels, 0.02)
            strum_green(pixels, 0.02)
            strum_blue(pixels, 0.02)

            strum_red(pixels, 0.01)
            strum_yellow(pixels, 0.01)
            strum_green(pixels, 0.01)
            strum_blue(pixels, 0.01)

            strum_red(pixels, 0.03)
            strum_yellow(pixels, 0.03)
            strum_green(pixels, 0.03)
            strum_blue(pixels, 0.03)
        

            pygame.mixer.music.stop()

            #debounce
            while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.01)
            time.sleep(0.05)

        time.sleep(0.01)

except KeyboardInterrupt:
    pixels.fill((0, 0, 0))
    pygame.mixer.music.stop()
    GPIO.cleanup()
