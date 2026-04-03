"""
rhythm_pi.py

Raspberry Pi version of the rhythm game:
- Uses 4 button inputs through GPIO Zero
- Uses one addressable LED chain (4 logical strips wired in sequence)
- Keeps the same beatmap/timing/scoring structure as the Pygame version

Assumptions:
- The LEDs are one continuous addressable chain (e.g. NeoPixels / WS2812)
- The chain is arranged as 4 logical lanes one after another
- Each lane has LEDS_PER_LANE LEDs
- One button corresponds to one lane
- beatmap.py provides: notes, NUM_ROWS, TRAVEL_TIME

Install (typical):
    sudo pip3 install adafruit-circuitpython-neopixel gpiozero

Run:
    sudo python3 rhythm_pi.py

Notes:
- NeoPixel libraries on Raspberry Pi generally require root access.
- GPIO pin numbers below use BCM numbering.
"""

import time
import board
import neopixel
from gpiozero import Button
from beatmap import notes, NUM_ROWS, TRAVEL_TIME

# --------------------------------------------------
# Hardware configuration
# --------------------------------------------------
NUM_LANES = 4
LEDS_PER_LANE = 30
TOTAL_LEDS = NUM_LANES * LEDS_PER_LANE

# One continuous LED chain data pin
PIXEL_PIN = board.D18

# Button GPIO pins (BCM numbering)
BUTTON_PINS = [5, 6, 13, 19]

# NeoPixel options
BRIGHTNESS = 0.20
AUTO_WRITE = False
PIXEL_ORDER = neopixel.GRB

# --------------------------------------------------
# Game configuration
# --------------------------------------------------
HIT_WINDOW = 0.30
WIN_SCORE = 22
START_DELAY = 3.0
FPS = 60

# Logical travel space:
# notes move from row 0 -> NUM_ROWS-1 over TRAVEL_TIME seconds
TARGET_ROW = NUM_ROWS - 1

# Each falling note occupies this many LEDs vertically
NOTE_SIZE = 4

# Optional: invert these if a physical strip is mounted in reverse
# False = top-to-bottom matches low->high index within the lane
# True  = reverse the LED order within that lane
REVERSE_LANE = [False, False, False, False]

# Colors
OFF = (0, 0, 0)
NOTE_COLOR = (255, 60, 60)
HIT_LINE_COLOR = (0, 80, 0)
COUNTDOWN_COLOR = (0, 0, 80)
SUCCESS_FLASH = (0, 120, 0)
MISS_FLASH = (120, 0, 0)

# --------------------------------------------------
# Input setup
# --------------------------------------------------
buttons = [Button(pin, pull_up=True, bounce_time=0.03) for pin in BUTTON_PINS]

# --------------------------------------------------
# LED setup
# --------------------------------------------------
pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    TOTAL_LEDS,
    brightness=BRIGHTNESS,
    auto_write=AUTO_WRITE,
    pixel_order=PIXEL_ORDER,
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def play_chord(note):
    print(f"Correct! Played lane {note['lane']}")


def play_wrong():
    print("Wrong key or bad timing!")


def end_message(game_won):
    if game_won:
        print("Congratulations! You have escaped the underworld")
    else:
        print("The underworld got you and you have been forgotten forever.")


def find_hittable_note(current_time, lane, remaining_notes):
    """
    Return the first note in this lane that is close enough in time to hit.
    """
    for note in remaining_notes:
        if note["lane"] == lane and abs(note["time"] - current_time) <= HIT_WINDOW:
            return note
    return None


def note_row_position(note_time, current_time):
    """
    Convert note timing into a logical row position.

    A note starts at row 0 when current_time == note_time - TRAVEL_TIME
    and reaches TARGET_ROW when current_time == note_time.
    """
    spawn_time = note_time - TRAVEL_TIME

    if current_time < spawn_time:
        return None

    progress = (current_time - spawn_time) / TRAVEL_TIME
    row = round(progress * TARGET_ROW)
    return row


def lane_led_index(lane, position_in_lane):
    """
    Maps (lane, position) to physical LED index for serpentine wiring.

    position_in_lane:
        0 = TOP
        LEDS_PER_LANE-1 = BOTTOM (hit line)
    """

    if position_in_lane < 0 or position_in_lane >= LEDS_PER_LANE:
        return None

    # Convert to "distance from bottom"
    # since your physical bottom is the start of each lane segment
    from_bottom = (LEDS_PER_LANE - 1) - position_in_lane

    if lane == 0:
        return 0 + from_bottom

    elif lane == 1:
        return 30 + (LEDS_PER_LANE - 1 - from_bottom)

    elif lane == 2:
        return 60 + from_bottom

    elif lane == 3:
        return 90 + (LEDS_PER_LANE - 1 - from_bottom)

    return None


def set_lane_pixel(lane, position_in_lane, color):
    idx = lane_led_index(lane, position_in_lane)
    if idx is not None:
        pixels[idx] = color


def clear_pixels():
    pixels.fill(OFF)


def draw_hit_line():
    """
    Light the bottom LED in each lane to mark the target row.
    """
    for lane in range(NUM_LANES):
        set_lane_pixel(lane, TARGET_ROW, HIT_LINE_COLOR)


def draw_note(lane, row, color=NOTE_COLOR, size=NOTE_SIZE):
    """
    Draw a note as a short vertical block ending at 'row'.
    Example for size=2: rows [row-1, row]
    """
    start = row - (size - 1)
    end = row
    for r in range(start, end + 1):
        if 0 <= r < LEDS_PER_LANE:
            set_lane_pixel(lane, r, color)


def show_countdown(seconds_left):
    clear_pixels()
    cols_to_light = min(NUM_LANES, max(1, int(seconds_left)))
    for lane in range(cols_to_light):
        for row in range(LEDS_PER_LANE):
            set_lane_pixel(lane, row, COUNTDOWN_COLOR)
    pixels.show()


def flash_all(color, duration=0.08):
    pixels.fill(color)
    pixels.show()
    time.sleep(duration)
    clear_pixels()
    pixels.show()


def draw_game(current_time, remaining_notes):
    clear_pixels()
    draw_hit_line()

    for note in remaining_notes:
        row = note_row_position(note["time"], current_time)
        if row is None:
            continue
        if row >= LEDS_PER_LANE + NOTE_SIZE:
            continue
        draw_note(note["lane"], row)

    pixels.show()


def read_pressed_lanes(prev_states):
    """
    Returns list of lanes that were newly pressed this frame.
    gpiozero Button.is_pressed is True while held, so we edge-detect here.
    """
    new_presses = []
    for lane, button in enumerate(buttons):
        now = button.is_pressed
        if now and not prev_states[lane]:
            new_presses.append(lane)
        prev_states[lane] = now
    return new_presses


def play():
    score = 0
    game_playing = True
    game_won = False

    remaining_notes = [note.copy() for note in notes]
    start_time = time.time() + START_DELAY
    prev_button_states = [False] * NUM_LANES

    try:
        while game_playing:
            now = time.time()
            current_time = now - start_time
            time_until_start = start_time - now

            # Countdown period
            if time_until_start > 0:
                countdown = max(1, int(time_until_start) + 1)
                show_countdown(countdown)
                time.sleep(1 / FPS)
                continue

            # Check new button presses
            for chosen_lane in read_pressed_lanes(prev_button_states):
                correct_note = find_hittable_note(current_time, chosen_lane, remaining_notes)

                if correct_note is not None:
                    score += 1
                    play_chord(correct_note)
                    remaining_notes.remove(correct_note)
                    print(f"Score: {score}")
                    flash_all(SUCCESS_FLASH, duration=0.03)
                else:
                    score -= 1
                    play_wrong()
                    print(f"Score: {score}")
                    flash_all(MISS_FLASH, duration=0.03)

            # Remove missed notes
            missed_notes = []
            for note in remaining_notes:
                if current_time > note["time"] + HIT_WINDOW:
                    missed_notes.append(note)

            for note in missed_notes:
                remaining_notes.remove(note)
                score -= 1
                print(f"Missed lane {note['lane']}")
                print(f"Score: {score}")

            # Win / loss conditions
            if not remaining_notes:
                game_won = score >= 0
                game_playing = False

            if score < 0:
                game_playing = False
                game_won = False

            if score >= WIN_SCORE:
                game_won = True
                game_playing = False

            draw_game(current_time, remaining_notes)
            time.sleep(1 / FPS)

    finally:
        clear_pixels()
        pixels.show()
        end_message(game_won)


if __name__ == "__main__":
    play()