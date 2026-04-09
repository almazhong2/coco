import time
import random
import math
import board
import neopixel
 
# ── Hardware config ───────────────────────────────────────────────────────────
LED_COUNT      = 100          # Number of Pebble LEDs
LED_PIN        = board.D18    # GPIO 18 — must be a PWM-capable pin
LED_BRIGHTNESS = 0.7          # 0.0–1.0  (keep ≤ 0.8 to stay within PSU limits)
LED_ORDER      = neopixel.GRB # Most WS2812B pebble strips are GRB; change to RGB if colours look wrong
 
# ── Pixel strip ───────────────────────────────────────────────────────────────
pixels = neopixel.NeoPixel(
    LED_PIN,
    LED_COUNT,
    brightness=LED_BRIGHTNESS,
    auto_write=False,       # We call pixels.show() manually for smooth effects
    pixel_order=LED_ORDER,
)
 
# ── Coco palette ──────────────────────────────────────────────────────────────
ORANGE = (255, 107,  53)
PINK   = (255,  61, 127)
BLUE   = (  0, 102, 255)
PURPLE = (155,  48, 255)
BLACK  = (  0,   0,   0)
 
PALETTE = [ORANGE, PINK, BLUE, PURPLE]
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def lerp_color(c1, c2, t):
    """Linear interpolate between two RGB tuples. t in [0.0, 1.0]."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
 
def set_all(colour):
    """Fill every pixel with one colour and push to strip."""
    pixels.fill(colour)
    pixels.show()
 
def clear():
    pixels.fill(BLACK)
    pixels.show()
 
 
# ── Effects ───────────────────────────────────────────────────────────────────
 
def solid_cycle(duration=8.0):
    """Smoothly cycle through all four Coco colours across the whole strip."""
    n     = len(PALETTE)
    start = time.monotonic()
    while time.monotonic() - start < duration:
        elapsed = time.monotonic() - start
        phase   = (elapsed / duration) * n
        idx     = int(phase) % n
        t       = phase - int(phase)
        colour  = lerp_color(PALETTE[idx], PALETTE[(idx + 1) % n], t)
        set_all(colour)
        time.sleep(0.02)
 
 
def theatre_chase(duration=10.0, wait_ms=80):
    """Running theatre-style chase in rotating Coco colours."""
    start       = time.monotonic()
    palette_idx = 0
    step        = 0
    while time.monotonic() - start < duration:
        colour = PALETTE[palette_idx % len(PALETTE)]
        for i in range(LED_COUNT):
            pixels[i] = colour if (i + step) % 3 == 0 else BLACK
        pixels.show()
        time.sleep(wait_ms / 1000.0)
        step += 1
        if step % 3 == 0:
            palette_idx += 1
 
 
def rainbow_coco(duration=12.0, wait_ms=20):
    """
    Each LED gets a colour from the Coco palette based on its position,
    and the whole pattern scrolls.
    """
    start  = time.monotonic()
    offset = 0
    while time.monotonic() - start < duration:
        for i in range(LED_COUNT):
            pos    = (i + offset) % (len(PALETTE) * 25)
            idx    = int(pos // 25) % len(PALETTE)
            t      = (pos % 25) / 25.0
            colour = lerp_color(PALETTE[idx], PALETTE[(idx + 1) % len(PALETTE)], t)
            pixels[i] = colour
        pixels.show()
        offset += 1
        time.sleep(wait_ms / 1000.0)
 
 
def sparkle(duration=8.0, density=0.15, wait_ms=40):
    """Random pixels twinkle through the Coco palette against a dark base."""
    base  = lerp_color(PURPLE, BLACK, 0.85)
    start = time.monotonic()
    set_all(base)
    while time.monotonic() - start < duration:
        lit = random.sample(range(LED_COUNT), k=max(1, int(LED_COUNT * density)))
        for i in lit:
            pixels[i] = random.choice(PALETTE)
        pixels.show()
        time.sleep(wait_ms / 1000.0)
        for i in lit:
            pixels[i] = base
        pixels.show()
 
 
def breathe(duration=12.0):
    """The entire strip breathes (fades in/out) cycling through Coco colours."""
    start      = time.monotonic()
    colour_idx = 0
    steps      = 60
    while time.monotonic() - start < duration:
        colour = PALETTE[colour_idx % len(PALETTE)]
        for s in range(steps):
            set_all(lerp_color(BLACK, colour, s / steps))
            time.sleep(0.015)
        for s in range(steps, -1, -1):
            set_all(lerp_color(BLACK, colour, s / steps))
            time.sleep(0.015)
        colour_idx += 1
 
 
def wave(duration=12.0, wait_ms=30):
    """A sine-wave of brightness rolls along the strip in rotating colours."""
    start      = time.monotonic()
    phase      = 0.0
    colour_idx = 0
    while time.monotonic() - start < duration:
        colour = PALETTE[colour_idx % len(PALETTE)]
        next_c = PALETTE[(colour_idx + 1) % len(PALETTE)]
        for i in range(LED_COUNT):
            brightness = (math.sin((i / LED_COUNT) * 2 * math.pi + phase) + 1) / 2
            c = lerp_color(next_c, colour, brightness)
            c = lerp_color(BLACK, c, brightness ** 0.5)
            pixels[i] = c
        pixels.show()
        phase += 0.15
        if phase > 2 * math.pi * 4:
            phase = 0.0
            colour_idx += 1
        time.sleep(wait_ms / 1000.0)
 
 
def comet(duration=10.0, tail=12, wait_ms=25):
    """A bright comet with a fading tail shoots across the strip in Coco colours."""
    start      = time.monotonic()
    colour_idx = 0
    while time.monotonic() - start < duration:
        colour = PALETTE[colour_idx % len(PALETTE)]
        for head in range(LED_COUNT + tail):
            pixels.fill(BLACK)
            for t in range(tail):
                pos = head - t
                if 0 <= pos < LED_COUNT:
                    fade        = 1.0 - (t / tail)
                    pixels[pos] = lerp_color(BLACK, colour, fade ** 2)
            pixels.show()
            time.sleep(wait_ms / 1000.0)
        colour_idx += 1
 
 
# ── Main show ─────────────────────────────────────────────────────────────────
 
SHOW = [
    ("Breathe",       breathe,       dict(duration=12)),
    ("Solid Cycle",   solid_cycle,   dict(duration=8)),
    ("Rainbow Coco",  rainbow_coco,  dict(duration=12)),
    ("Comet",         comet,         dict(duration=10)),
    ("Wave",          wave,          dict(duration=12)),
    ("Sparkle",       sparkle,       dict(duration=8)),
    ("Theatre Chase", theatre_chase, dict(duration=10)),
]
 
def run_show(repeat=True):
    print("Coco Light Show starting — press Ctrl-C to stop\n")
    try:
        while True:
            for name, fx, kwargs in SHOW:
                print(f"  >  {name}")
                fx(**kwargs)
                clear()
                time.sleep(0.4)
            if not repeat:
                break
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        clear()
        print("LEDs cleared. Goodbye!")
 
 
if __name__ == "__main__":
    run_show()
