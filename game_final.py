import time
import board
import neopixel
import RPi.GPIO as GPIO
import pygame
import os
import random

################ CONFIGURATION ################
os.environ["SDL_AUDIODRIVER"] = "alsa"
os.environ["AUDIODEV"] = "hw:2,0"

PIXEL_PIN = board.D18
NUM_PIXELS = 240
FRAME_DELAY = 0.02
STREAK_LENGTH = 12
FLASH_FRAMES = 5

HIT_ZONE_MIN = 45
HIT_ZONE_MAX = 55

PEBBLE_PIN = board.D21
PEBBLE_COUNT = 100

#for ending lights
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS,
    brightness = 0.1,
    auto_write = False
)

pebbles = neopixel.NeoPixel(
    PEBBLE_PIN, PEBBLE_COUNT,
    brightness = 0.3,
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

STRUM_PIN = 19
GPIO.setup(STRUM_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)


################ STRIP SETUP ################
STRIPS = {
    "green":  {"range": (0,   59),  "forward": False, "color": (0,   255, 0),  "zone": (0,  3)},
    "red":    {"range": (60,  119), "forward": True,  "color": (255, 0,   0),  "zone": (55, 59)},
    "yellow": {"range": (120, 179), "forward": False, "color": (255, 255, 51), "zone": (0,  3)},
    "blue":   {"range": (180, 239), "forward": True,  "color": (0,   0,   255),"zone": (55, 59)},
}

#green (0, 255, 0), red (255, 0, 0), yellow (255, 255, 51), blue (0, 0, 255)

################ STREAK CLASS ################
class Streak:
    def __init__(self, strip_name, speed=1):
        strip = STRIPS[strip_name]
        self.color = strip["color"]
        self.strip_name = strip_name
        self.start = strip["range"][0]
        self.end = strip["range"][1]
        self.length = self.end - self.start
        self.forward = strip["forward"]
        self.zone_min = strip["zone"][0]   # ← NEW
        self.zone_max = strip["zone"][1]
        self.speed = speed
        self.head = -STREAK_LENGTH
        self.flash_frames = 0
    
    @property
    def done(self):
        return self.head > self.length + STREAK_LENGTH
    
    @property
    def in_zone(self):
        return self.zone_min <= int(self.head) <= self.zone_max
    
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
                    index = int(self.start + pos)
                else:
                    index= int(self.end - pos)

                
                fade = (STREAK_LENGTH - offset) / STREAK_LENGTH
                r,g,b = display_color

                pixel_buffer[index] = (int(r*fade), int(g*fade), int(b*fade))

################ ORANGE LIGHTS SETUP ################
class UnderworldControl:
    WHITE = (255, 255, 255)

    # CORRECT — orange has r > g, b = 0
    # ORANGE colors — correct for GRB (first=green channel, second=red channel)
    ORANGE_DIM    = (3,   0,  40)   # g=3,  r=40  → dim orange
    ORANGE_MID    = (15,  0, 120)   # g=15, r=120 → mid orange
    ORANGE_BRIGHT = (30,  0, 255)   # g=30, r=255 → bright orange
    OFF           = (0,   0,  0)

    def __init__(self):
        self.state = "IDLE"
        self.hit_count = 0
        self.frame = 0

        self.idle_phase = 0.0
        self.end_timers = [random.randint(20, 60) for _ in range(PEBBLE_COUNT)]
    
    def set_state(self, state):

        self.state = state
        self.frame = 0
        
        if state == "IDLE":
            self.idle_phase = 0.0
        if state == "PLAYING":
            self.hit_count = 0
        if state == "ENDING":
            self.end_timers = [random.randint(20, 70) for _ in range(PEBBLE_COUNT)]
    
    def hit(self):
        self.hit_count += 1
    
    def update(self):
        if self.state == "IDLE":
            self._update_idle()
        elif self.state == "PLAYING":
            self._update_playing()
        elif self.state == "ENDING":
            self._update_ending()
        
        self.frame += 1

    
    def _update_idle(self):
        self.idle_phase = (self.idle_phase + 0.5) % 100
        if self.idle_phase < 50:
            brightness = self.idle_phase / 50
        else:
            brightness = (100 - self.idle_phase) / 50

        floor = 0.1
        b     = floor + brightness * (1 - floor)
        g_val = int(self.ORANGE_BRIGHT[0] * b)
        r_val = int(self.ORANGE_BRIGHT[1] * b)
        pebbles.fill((g_val, r_val, 0))   # GRB: (g, r, 0)
        pebbles.show()
    
    def _update_playing(self):
        #orange will gradually get brighter across the strip
        # how many pebbles should be lit based on hit count
        target_lit = min(self.hit_count * (PEBBLE_COUNT // 5), PEBBLE_COUNT)
        for i in range(PEBBLE_COUNT):
            if i < target_lit:
                progress = i / max(target_lit - 1, 1)
                g_out = int(self.ORANGE_DIM[0] + progress * (self.ORANGE_MID[0] - self.ORANGE_DIM[0]))
                r_out = int(self.ORANGE_DIM[1] + progress * (self.ORANGE_MID[1] - self.ORANGE_DIM[1]))
                pebbles[i] = (g_out, r_out, 0)   # GRB: (g, r, 0)
            else:
                pebbles[i] = self.OFF
        pebbles.show()

    def _update_ending(self):

        for i in range(PEBBLE_COUNT):
            self.end_timers[i] -= 1
            if self.end_timers[i] <= 0:
                pebbles[i] = self.ORANGE_MID          # ← CHANGED: 3-tuple
                self.end_timers[i] = random.randint(20, 70)  # ← CHANGED: slow reset
            else:
                pebbles[i] = self.OFF
        pebbles.show()



################ STRUM DETECTION ################
class StrumDetector:
    def __init__(self):
        self.down_last = False

    
    def update(self):
        down_held = GPIO.input(STRUM_PIN) == GPIO.LOW
        just_strummed = down_held and not self.down_last
        self.down_last = down_held
        return just_strummed


################ HIT DETECTION ################

#notes
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

#strum
def check_strum(active_streaks, strum_detector, pebble):
    if not strum_detector.update():
        return
    
    held_buttons = set()

    for pin, strip_name in BUTTON_PINS.items():
        if strip_name != "start" and GPIO.input(pin) == GPIO.LOW:
            held_buttons.add(strip_name)
        
    for streak in active_streaks:
        if streak.in_zone and streak.strip_name in held_buttons:
            streak.hit()
            pebble.hit()

#start
def start_button_pressed(start_state):
    held = GPIO.input(17) == GPIO.LOW
    pressed = held and not start_state
    return pressed, held

#main loop
def run_sequence(sequence, pebble):
    active_streaks = []
    pending = list(sequence)
    button_states = {}
    strum_detector = StrumDetector()
    frame = 0 
    start_state = True

    state = "IDLE"
    print("press start to begin...")
    while True:
        start_pressed, start_state = start_button_pressed(start_state)

        if state == "IDLE" and start_pressed:
            state = "RUNNING"
            pygame.mixer.music.play(loops=1)
            pebble.set_state("PLAYING")
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
        
        if pebble.state != "ENDING":
            pebble.update()
        
        if state == "RUNNING":
            while pending and pending[0][2] <= frame:
                name, speed, _ = pending.pop(0)
                active_streaks.append(Streak(name, speed))

            button_pressed(active_streaks, button_states)
            check_strum(active_streaks, strum_detector, pebble)
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
                pebble.set_state("ENDING")
                _run_ending(pebble)
                return 
            
            frame += 1

        time.sleep(FRAME_DELAY)
        

#end sequence
def _run_ending(pebble):
    end_duration = int(5 / FRAME_DELAY)
    for _ in range(end_duration):
        pebble.update()
        time.sleep(FRAME_DELAY)
    pebble.set_state("IDLE")

#song and show
def play_song(pebble):
    pygame.mixer.init()
    pygame.mixer.music.load("rememberme.mp3")
    pygame.mixer.music.set_volume(0.5)

    sequence = [
    # Gentle intro, one note at a time (0-4s)
    ("blue",   0.75,   0),
    ("green",  0.75,  40),
    ("red",    0.75, 90),
    ("yellow", 0.75, 140),
    ("blue",   0.75, 180),

    # First verse: singles then a few pairs (4-14s)
    ("yellow", 1, 200),
    ("blue",   1, 210),
    ("green",  1, 250),
    ("blue",   1, 300),   # pair with green
    ("red",    1, 350),
    ("yellow", 1, 350),
    ("red",    1, 400),   # pair with yellow
    ("red",    1, 430),
    ("green",  1, 460),
    ("blue",   1, 490),   # pair with green

    # Build: a few 1.5s (14-20s)
    ("red",    1.5, 510),
    ("green",  1.5, 530),
    ("blue",   1.5, 530),
    ("yellow", 1.5, 550),
    ("red",    1.5, 590),
    ("yellow", 1.5, 620),
    ("blue",   1.5, 650),
    ]

    run_sequence(sequence, pebble)

try:
    pebble = UnderworldControl()
    while True:
        play_song(pebble)
            
except KeyboardInterrupt:
    pixels.fill((0,  0, 0))
    pixels.show()
    pygame.mixer.music.stop()
    GPIO.cleanup()




        
