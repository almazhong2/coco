import pygame
import os
import time
 
os.environ["SDL_AUDIODRIVER"] = "alsa"
os.environ["AUDIODEV"] = "hw:2,0"
 
pygame.mixer.init()
pygame.mixer.music.load("m2.mp3")
pygame.mixer.music.set_volume(0.25)
pygame.mixer.music.play(loops=-1)  # -1 = loop forever
 
print("Playing m2.mp3 — press Ctrl+C to stop")
 
try:
    while True:
        time.sleep(1)
 
except KeyboardInterrupt:
    pygame.mixer.music.stop()
    print("Stopped.")