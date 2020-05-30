import creds
import config
from random_album import play_random_album

import argparse
import logging
from time import sleep

gpio_available = True
try:
    from gpiozero import Button, LED, PWMLED
    from signal import pause
    logging.info('Gpiozero found')
except ImportError:
    gpio_available = False
    logging.info('Gpiozero not available')

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

if gpio_available:
    led = PWMLED(17, active_high = False)
print('Ready')

def do_stuff():
    if gpio_available:
        led.blink(on_time = 0.3, n = 1)
    if args.test:
        print('playing')
        sleep(1)
    else:
        play_random_album(
            creds.SPOTIPY_CLIENT_ID,
            creds.SPOTIPY_CLIENT_SECRET,
            creds.REDIRECT_URI,
            config.USERNAME,
            config.PLAYLIST,
            config.DEVICE_NAME,
            config.ALBUM_MINIMUM_TRACKS)
    if gpio_available:
        led.blink(on_time = 0.1, off_time = 0.1, n = 3)

if gpio_available:
    button = Button(27) # Defaults to pull-up using internal resistor
    button.when_pressed = do_stuff
    pause()
else:
    while True:
        input("Hit return:")
        do_stuff()
