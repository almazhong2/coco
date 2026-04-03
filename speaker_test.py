import pygame
import time

# 1. Setup the player
pygame.mixer.init()

# 2. Load your file (make sure the name matches!)
pygame.mixer.music.load("song.mp3")

# 3. Start playing
print("Playing audio now...")
pygame.mixer.music.play()

# 4. Wait for a specific time frame (e.g., 10 seconds)
time.sleep(60) 

# 5. Stop the audio
pygame.mixer.music.stop()
print("Test finished.")