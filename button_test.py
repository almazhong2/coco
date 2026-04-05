import time 
import board
import neopixel
import Rpi.GPIO as GPIO
import pygame

#configuration
PIXEL_PIN = board.D18
NUM_PIXELS = 240
BUTTON_PIN = 17

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness = 0.1,
    auto_write=True
)

#button setp
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)



try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW: #button is pressed
            print("pressed!")

            #start music
            #music setup
            pygame.mixer.init()
            pygame.mixer.music.load("song cut.mp3")
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(loops=1)

            pixels.fill((255, 0, 0))
            time.sleep(5)

            pixels.fill((0, 255, 0))
            time.sleep(5)

            pixels.fill((0, 0, 255))
            time.sleep(5)

            pixels.fill((0, 0, 0))

            for i in range(NUM_PIXELS-1):
                pixels[i] = (255, 0, 0)
                pixels[i+1] = (255, 0, 0)
                time.sleep(0.05)
                pixels[i] = (0, 0, 0)
            
            pixels[NUM_PIXELS-1] = (0, 0, 0)

            pixels.fill((0, 0, 0))

            pygame.mixer.music.stop()

            while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.01)
            time.sleep(0.05)
        
        time.sleep(0.01)

except KeyboardInterrupt:
    pixels.fill((0, 0, 0))
    pygame.mixer.music.stop()
    GPIO.cleanup()
