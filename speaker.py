import os
import time
import subprocess
import signal

# Optional: set ALSA device
os.environ["AUDIODEV"] = "hw:2,0"

# Start mpg123 in loop mode
player = subprocess.Popen(
    ["mpg123", "--loop", "-1", "m2.mp3"],
    env=os.environ
)

print("Playing m2.mp3 — press Ctrl+C to stop")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    player.send_signal(signal.SIGINT)   # politely stop mpg123
    player.wait()
    print("Stopped.")
