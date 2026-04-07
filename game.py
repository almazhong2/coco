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
FLASH_FRAMES = 8

HIT_ZONE_MIN = 25
HIT_ZONE_MAX = 35

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
        self.strip_name = strip_name
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

################ ORANGE LIGHTS SETUP ################
class UnderworldControl:
    ORANGE_DIM = (20, 8, 0)
    ORANGE_BRIGHT = (255, 80, 0)
    WHITE = (255, 255, 255)

    def __init__(self):
        self.state = "IDLE"
        self.hit_count = 0
        self.frame = 0

        self.idle_phase = 0.0
        self.end_timers = [random.randint(0, 20) for _ in range(PEBBLE_COUNT)]
    
    def set_state(self, state):

        self.state = state
        self.frame = 0
        
        if state == "IDLE":
            self.idle_phase = 0.0
        if state == "PLAYING":
            self.hit_count = 0
        if state == "ENDING":
            self.end_timers = [random.randint(0, 20) for _ in range(PEBBLE_COUNT)]
    
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
        # triangle wave: phase 0-49 ramps up, 50-99 ramps down
        self.idle_phase = (self.idle_phase + 0.5) % 100      
        if self.idle_phase < 50:
            brightness = self.idle_phase / 50
        else:
            brightness = (100 - self.idle_phase) / 50

        # scale white by brightness, keep a dim floor
        floor = 0.05
        b     = floor + brightness * (1 - floor)
        color = (int(255 * b), int(255 * b), int(255 * b))

        pebbles.fill(color)
        pebbles.show()
    
    def _update_playing(self):

        # each hit lights up roughly 2 more pixels
        lit = min(self.hit_count * 2, PEBBLE_COUNT)

        for i in range(PEBBLE_COUNT):
            if i < lit:
                # scale brightness based on how high up we are
                # pixels near bottom are dimmer, top brighter
                progress = i / PEBBLE_COUNT
                r = int(self.ORANGE_DIM[0] + 
                        progress * (self.ORANGE_BRIGHT[0] - self.ORANGE_DIM[0]))
                g = int(self.ORANGE_DIM[1] +
                        progress * (self.ORANGE_BRIGHT[1] - self.ORANGE_DIM[1]))
                b = 0
                pebbles[i] = (r, g, b)
            else:
                pebbles[i] = self.ORANGE_DIM
        
        pebbles.show()

    def _update_ending(self):

        for i in range(PEBBLE_COUNT):
            self.end_timers[i] -= 1
            if self.end_timers[i] <= 0:
                pebbles[i] = self.WHITE

                self.end_timers[i] = random.randint(5, 30)
            else:
                pebbles[i] = (0, 0, 0)
        
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

        #less spaced
        ("red",    2, 360),
        ("yellow", 2, 380),
        ("green",  2, 400),
        ("blue",   2, 420),
        ("red",    2, 440),
        ("green",  2, 460),
        ("yellow", 2, 480),
        ("blue",   2, 500),
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




        
