import time
import board
import neopixel
import RPi.GPIO as GPIO
import pygame
import os

################ CONFIGURATION ################
os.environ["SDL_AUDIODRIVER"] = "alsa"
os.environ["AUDIODEV"] = "hw:2,0"

PIXEL_PIN = board.D18
NUM_PIXELS = 240
FRAME_DELAY = 0.015
STREAK_LENGTH = 12
FLASH_FRAMES = 8

HIT_ZONE_MIN = 25
HIT_ZONE_MAX = 35

#for ending lights
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS,
    brightness = 0.1,
    auto_write = False
)

################ GPIO SETUP ################
GPIO.setmode(GPIO.BCM)
BUTTON_PINS = {
    17: "start",
    27: "red",
    22: "yellow",
    23: "green",
    24: "blue",
}

for pin in BUTTON_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


################ STRIP SETUP ################
STRIPS = {
    "red":      {"range": (0, 59), "forward": True, "color": (255, 0, 0)},
    "yellow":   {"range": (60, 119), "forward": False, "color": (255, 255, 0)},
    "green":    {"range": (120, 179), "forward": True, "color": (0, 255, 0)},
    "blue":     {"range": (180, 239), "forward": False, "color": (0, 0, 255)},
}

################ STREAK CLASS ################
class Streak:
    def __init__(self, strip_name, speed=1):
        strip = STRIPS[strip_name]
        self.color = strip["color"]
        self.start = strip["range"][0]
        self.end = strip["range"][1]
        self.length = self.end - self.start
        self.forward = strip["forward"]
        self.speed = speed
        self.head = -STREAK_LENGTH
        self.flash_frames = 0
    
    @property
    def done(self):
        return self.head > self.length + STREAK_LENGTH
    
    @property
    def in_zone(self):
        return HIT_ZONE_MIN <= self. head <= HIT_ZONE_MAX
    
    def hit(self):
        self.flash_frames = FLASH_FRAMES

    def advance(self):
        self.head += self.speed
        if self.flash_frames > 0:
            self.flash_frames -= 1
        
    
    def draw(self, pixel_buffer):
        display_color = (255, 255, 255) if self.flash_frames > 0 else self.color

        for offset in range(STREAK_LENGTH):
            pos = self.head - offset
            if 0 <= pos <= self.length:
                if self.forward:
                    index = self.start + pos
                else:
                    index= self.end - pos

                
                fade = (STREAK_LENGTH - offset) / STREAK_LENGTH
                r,g,b = display_color

                pixel_buffer[index] = (int(r*fade), int(g*fade), int(b*fade))

#hit detection
def button_pressed(active_streaks, button_states):
    for pin, strip_name in BUTTON_PINS.items():
        if strip_name == "start":
            continue

        button_held = GPIO.input(pin) == GPIO.LOW
        held_last = button_states.get(pin, False)
        pressed = button_held and not held_last
        button_states[pin] = button_held

        if pressed:
            for streak in active_streaks:
                if streak.color == STRIPS[strip_name]["color"] and streak.in_zone:
                    streak.hit()
                    break


def start_button_pressed(start_state):
    held = GPIO.input(17) == GPIO.LOW
    pressed = held and not start_state
    return pressed, held

#main loop
def run_sequence(sequence):
    active_streaks = []
    pending = list(sequence)
    button_states = {}
    frame = 0
    start_state = True

    state = "IDLE"
    print("press start to begin...")
    while True:
        start_pressed, start_state = start_button_pressed(start_state)

        if state == "IDLE" and start_pressed:
            state = "RUNNING"
            pygame.mixer.music.play(loops=1)
            print("Running")

        elif state == "RUNNING" and start_pressed:
            state = "PAUSED"
            pygame.mixer.music.pause()
            pixels.fill((0, 0, 0))
            pixels.show()
            print("Paused")
        
        elif state == "PAUSED" and start_pressed:
            state = "RUNNING"
            pygame.mixer.music.unpause()
            print("Resume")
        
        if state == "RUNNING":
            while pending and pending[0][2] <= frame:
                name, speed, _ = pending.pop(0)
                active_streaks.append(Streak(name, speed))

            button_pressed(active_streaks, button_states)
            pixel_buffer = [(0, 0 , 0)] * NUM_PIXELS
        
            for streak in active_streaks:
                streak.advance()
                streak.draw(pixel_buffer)
        
            active_streaks = [s for s in active_streaks if not s.done]

            for i, color in enumerate(pixel_buffer):
                pixels[i] = color
            pixels.show()

            if not pending and not active_streaks:
                print("song finished, press start to play again")
                pygame.mixer.music.stop()
                pixels.fill((0,0,0))
                pixels.show()
                return 
            
            frame += 1

        time.sleep(FRAME_DELAY)
        


#song and show
def play_song():
    pygame.mixer.init()
    pygame.mixer.music.load("song cut.mp3")
    pygame.mixer.music.set_volume(0.5)

    sequence = [
        # Intro: slow, spaced (0-8s)
        ("red",    2, 0),
        ("yellow", 2, 40),
        ("green",  2, 80),
        ("blue",   2, 120),
        ("red",    2, 180),
        ("green",  2, 220),
        ("yellow", 2, 300),
        ("blue",   2, 340),
        # Building: pairs (8-16s)
        ("red",    3, 530),  ("green",  3, 530),
        ("yellow", 3, 580),  ("blue",   3, 580),
        ("red",    3, 640),  ("yellow", 3, 655),
        ("green",  3, 640),  ("blue",   3, 655),
        ("red",    3, 720),  ("blue",   3, 720),
        ("yellow", 3, 760),  ("green",  3, 760),
        ("red",    3, 820),  ("yellow", 3, 830),
        ("green",  3, 840),  ("blue",   3, 850),
        # Chorus: fast and dense (16-24s)
        ("red",    4, 1070), ("yellow", 4, 1085),
        ("green",  4, 1100), ("blue",   4, 1115),
        ("red",    4, 1150), ("green",  4, 1150),
        ("yellow", 4, 1175), ("blue",   4, 1175),
        ("red",    4, 1210), ("blue",   4, 1210),
        ("red",    4, 1250), ("yellow", 4, 1250),
        ("green",  4, 1290), ("blue",   4, 1290),
        ("green",  4, 1330), ("red",    4, 1330),
        ("yellow", 5, 1380), ("blue",   5, 1390),
        ("red",    5, 1400), ("green",  5, 1410),
        ("red",    4, 1450), ("yellow", 4, 1460),
        ("green",  4, 1470), ("blue",   4, 1480),
        ("red",    4, 1520), ("green",  4, 1520),
        ("yellow", 4, 1545), ("blue",   4, 1545),
        # Break: sparse (24-28s)
        ("red",    2, 1600),
        ("blue",   2, 1670),
        ("yellow", 2, 1740),
        ("green",  2, 1810),
        # Final build (28-33s)
        ("red",    3, 1870), ("yellow", 3, 1890),
        ("green",  3, 1910), ("blue",   3, 1930),
        ("red",    4, 1980), ("yellow", 4, 1990),
        ("green",  4, 2000), ("blue",   4, 2010),
        ("red",    5, 2060), ("green",  5, 2060),
        ("yellow", 5, 2080), ("blue",   5, 2080),
        ("red",    5, 2120), ("yellow", 5, 2125),
        ("green",  5, 2130), ("blue",   5, 2135),
        ("red",    5, 2160), ("yellow", 5, 2163),
        ("green",  5, 2166), ("blue",   5, 2169),
        # Outro (33-35s)
        ("red",    2, 2200),
        ("blue",   2, 2230),
        ("yellow", 2, 2260),
        ("green",  2, 2290),
    ]

    run_sequence(sequence)

try:
    while True:
        play_song()
            
except KeyboardInterrupt:
    pixels.fill((0,  0, 0))
    pixels.show()
    pygame.mixer.music.stop()
    GPIO.cleanup()




        
