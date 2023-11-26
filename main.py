import creds
import config
from random_album import RandomAlbum

import argparse
import logging
from time import sleep

# http://stackoverflow.com/q/14097061/78845
parser = argparse.ArgumentParser(
    description='A script to play the entire album of a track randomly selected from a playlist on a particular device.'
)
parser.add_argument("-v", "--verbose", action='count', default = 0, help="-v: INFO level output verbosity -vv: DEBUG level output versbosity")
parser.add_argument("-t", "--test", help="just pretend to trigger spotify", action="store_true")

args = parser.parse_args()

if args.verbose == 1:
    logging.basicConfig(level=logging.INFO)

if args.verbose == 2:
    logging.basicConfig(level=logging.DEBUG)

# We may not be running on a Pi
gpio_available = True
try:
    from gpiozero import Button, PWMLED
    from signal import pause,signal,SIGTERM
    logging.info('Gpiozero found')
except ImportError:
    gpio_available = False
    logging.info('Gpiozero not available')

def sigterm_handler(signal, frame):
    # If systemd kills our process we want to shut down gracefully, releasing
    # our GPIO pins and as a side-effect, turning off the LED.
    [button.close() for button in buttons]
    [led.close() for led in leds]

if gpio_available:
    leds = [PWMLED(pin, active_high = False) for pin in config.LED_PINS]
    buttons = [Button(pin) for pin in config.BUTTON_PINS]
    signal(SIGTERM, sigterm_handler)

print('Ready')

def do_stuff(i):
    logging.info(f'In do_stuff ({i})');
    device_name = config.DEVICE_NAME
    if args.test:
        print('playing')
        sleep(1)
    else:
        ra.play_random_album(config.PLAYLISTS[i], device_name, config.ALBUM_MINIMUM_TRACKS)
    if gpio_available:
        leds[i].blink(on_time = 0.1, off_time = 0.1, n = 3)

ra = RandomAlbum(config.USERNAME, creds.SPOTIPY_CLIENT_ID, creds.SPOTIPY_CLIENT_SECRET, creds.REDIRECT_URI)
if gpio_available:
    for i, b in enumerate(buttons):
        # https://stackoverflow.com/a/2295372/300836
        b.when_pressed = lambda i=i: do_stuff(i)
    pause()
else:
    while True:
        max = len(config.PLAYLISTS) - 1
        i = int(input(f"Give me a number between 0 and {max}:"))
        if not 0 <= i <= max:
            print(f"That wasn't between 0 and {max}!")
            continue
        do_stuff(i)
