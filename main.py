import creds
import config
from random_album import play_random_album

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
    from gpiozero import Button, LED, PWMLED
    from signal import pause,signal,SIGTERM
    logging.info('Gpiozero found')
except ImportError:
    gpio_available = False
    logging.info('Gpiozero not available')

def sigterm_handler(signal, frame):
    # If systemd kills our process we want to shut down gracefully, releasing
    # our GPIO pins and as a side-effect, turning off the LED.
    button.close()
    led.close()

if gpio_available:
    led = PWMLED(config.GPIO_LED, active_high = False)
    signal(SIGTERM, sigterm_handler)

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
    button = Button(config.GPIO_BUTTON) # Defaults to pull-up using internal resistor
    button.when_pressed = do_stuff
    pause()
else:
    while True:
        input("Hit return:")
        do_stuff()
