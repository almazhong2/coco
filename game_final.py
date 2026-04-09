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

HIT_ZONE_MIN = 42
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
    auto_write = False,
    pixel_order = neopixel.GRBW
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
    "green":      {"range": (0, 59), "forward": False, "color": (0, 255, 0)},
    "red":   {"range": (60, 119), "forward": True, "color": (255, 0, 0)},
    "yellow":    {"range": (120, 179), "forward": False, "color": (255, 255, 51)},
    "blue":     {"range": (180, 239), "forward": True, "color": (0, 0, 255)},
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
    WHITE = (0, 0, 0, 255)

    ORANGE_LEVELS = [
        (8, 3, 0, 0),
        (30, 10, 0, 0),
        (80, 25, 0, 0),
        (160, 50, 0, 0),
        (255, 80, 0, 0),
    ]

    def __init__(self):
        self.state = "IDLE"
        self.hit_count = 0
        self.frame = 0

        self.idle_phase = 0.0
        self.lit_count = 0
        self.end_timers = [random.randint(0, 20) for _ in range(PEBBLE_COUNT)]
    
    def set_state(self, state):

        self.state = state
        self.frame = 0
        
        if state == "IDLE":
            self.idle_phase = 0.0
        if state == "PLAYING":
            self.hit_count = 0
            self.lit_count = 0
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
        w = int(255*b)

        pebbles.fill((0,0,0, w))
        pebbles.show()
    
    def _update_playing(self):
        #orange will gradually get brighter across the strip
        # how many pebbles should be lit based on hit count
        target_lit = min(self.hit_count * 2, PEBBLE_COUNT)

        # pick brightness level based on hits
        level_idx  = min(self.hit_count // 10, len(self.ORANGE_LEVELS) - 1)
        top_color  = self.ORANGE_LEVELS[level_idx]

        # bottom of lit region is dimmer — heat-rising feel
        bottom_scale = 0.15
        bottom_color = (
            int(top_color[0] * bottom_scale),
            int(top_color[1] * bottom_scale),
            0, 0
        )

        for i in range(PEBBLE_COUNT):
            if i < target_lit:
                progress = i / max(target_lit - 1, 1)
                r = int(bottom_color[0] + progress * (top_color[0] - bottom_color[0]))
                g = int(bottom_color[1] + progress * (top_color[1] - bottom_color[1]))
                pebbles[i] = (r, g, 0, 0)   # ← CHANGED: 4-tuple for RGBW
            else:
                pebbles[i] = (0, 0, 0, 0)   # ← CHANGED: off pixels also 4-tuple

        pebbles.show()

    def _update_ending(self):

        for i in range(PEBBLE_COUNT):
            self.end_timers[i] -= 1
            if self.end_timers[i] <= 0:
                pebbles[i] = self.ORANGE_LEVELS[-1]

                self.end_timers[i] = random.randint(15, 60)
            else:
                pebbles[i] = (0, 0, 0, 0)
        
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
        # ── Very gentle intro, one note at a time (0-13s)
        ("green",  0.5,   0),
        ("red",    0.5,  76),
        ("yellow", 0.5, 152),
        ("blue",   0.5, 228),
        ("green",  0.5, 304),
        ("red",    0.5, 380),
        ("yellow", 0.5, 456),
        ("blue",   0.5, 532),
        ("green",  0.5, 608),

        # ── First verse: still single notes, speed 1 (13-26s)
        ("red",    1,  650),
        ("yellow", 1,  688),
        ("blue",   1,  726),
        ("green",  1,  764),
        ("red",    1,  802),
        ("yellow", 1,  840),
        ("blue",   1,  878),
        ("green",  1,  916),
        ("red",    1,  954),
        ("yellow", 1,  992),
        ("blue",   1, 1030),
        ("green",  1, 1068),
        ("red",    1, 1106),
        ("yellow", 1, 1144),
        ("blue",   1, 1182),
        ("green",  1, 1220),
        ("red",    1, 1258),

        # ── Build: pairs begin, speed 1.5 (26-39s)
        ("yellow", 1.5, 1300),
        ("blue",   1.5, 1300),
        ("green",  1.5, 1338),
        ("red",    1.5, 1338),
        ("yellow", 1.5, 1376),
        ("blue",   1.5, 1414),
        ("green",  1.5, 1414),
        ("red",    1.5, 1452),
        ("yellow", 1.5, 1490),
        ("blue",   1.5, 1490),
        ("green",  1.5, 1528),
        ("red",    1.5, 1566),
        ("yellow", 1.5, 1566),
        ("blue",   1.5, 1604),
        ("green",  1.5, 1642),
        ("red",    1.5, 1642),
        ("yellow", 1.5, 1680),
        ("blue",   1.5, 1718),
        ("green",  1.5, 1756),
        ("red",    1.5, 1794),
        ("yellow", 1.5, 1832),
        ("blue",   1.5, 1870),
        ("green",  1.5, 1908),

        # ── Final section: speed 2, fuller pairs (39-52s)
        ("red",    2, 1950), ("yellow", 2, 1950),
        ("blue",   2, 1988), ("green",  2, 1988),
        ("red",    2, 2026), ("yellow", 2, 2040),
        ("blue",   2, 2064), ("green",  2, 2078),
        ("red",    2, 2102), ("yellow", 2, 2102),
        ("blue",   2, 2140), ("green",  2, 2154),
        ("red",    2, 2178), ("yellow", 2, 2192),
        ("blue",   2, 2216), ("green",  2, 2216),
        ("red",    2, 2254), ("yellow", 2, 2268),
        ("blue",   2, 2292), ("green",  2, 2292),
        ("red",    2, 2330), ("yellow", 2, 2344),
        ("blue",   2, 2368),
        ("green",  2, 2392),
        ("red",    2, 2430),
        ("yellow", 2, 2468),
        ("blue",   2, 2506),
        ("green",  2, 2544),
        ("red",    2, 2582),
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




        
