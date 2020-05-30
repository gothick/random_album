import spotipy
import creds
import config
import spotipy.util as util
import random

import argparse
import logging

from gpiozero import Button, LED, PWMLED
from signal import pause
from time import sleep

# http://stackoverflow.com/q/14097061/78845
parser = argparse.ArgumentParser(
    description='A script to play the entire album of a track randomly selected from a playlist on a particular device.'
)
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-t", "--test", help="just pretend to trigger spotify", action="store_true")

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

def find_playlist_by_name(sp, name):
    results = sp.current_user_playlists(limit = 50, offset = 0)
    playlists = results['items']
    playlist = next(filter(lambda p: p['name'] == name, playlists), None)
    while playlist is None and results['next']:
        results = sp.next(results)
        playlists = results['items']
        playlist = next(filter(lambda p: p['name'] == name, playlists), None)
    return playlist


def find_device_id_by_name(sp, name):
    results = sp.devices()
    devices = results['devices']
    device = next(filter(lambda d: d['name'] == name, devices), None)
    if device:
        return device['id']

def play_random_album():
    # Spotify app scopes (permissions)
    scope = 'streaming user-read-playback-state user-modify-playback-state playlist-read-private app-remote-control'

    token = util.prompt_for_user_token(
        config.USERNAME,
        scope,
        client_id = creds.SPOTIPY_CLIENT_ID,
        client_secret = creds.SPOTIPY_CLIENT_SECRET,
        redirect_uri = creds.REDIRECT_URI
    )

    if token:
        sp = spotipy.Spotify(auth=token)
        # Find our Future Listening playlist.
        playlist = find_playlist_by_name(sp, config.PLAYLIST)
        total_tracks = playlist['tracks']['total']

        while True:
            # Pick a random song from it
            random_track = random.randint(0, total_tracks - 1)
            tracks = sp.playlist_tracks(playlist['id'],limit=1, offset=random_track)
            track = tracks['items'][0]['track']
            print(f"Found track {track['name']} by {track['artists'][0]['name']}")
            print(f"...from an album called {track['album']['name']}")
            track_count = track['album']['total_tracks']
            print(f"...with {track_count} tracks.")
            if track_count >= config.ALBUM_MINIMUM_TRACKS:
                break
            print('Trying again to find a bigger album')

        # Found an album with a decent number of tracks. Play it!
        device_id = find_device_id_by_name(sp, config.DEVICE_NAME)
        album_uri = track['album']['uri']
        sp.start_playback(context_uri = album_uri, device_id = device_id)
        print("Started playback of entire album.")
    else:
        # Getting the token will likely throw an exception rather than
        # just return Nothing, but just in case...
        print('Could not authenticate.')

#while True:
#    try:
#        input("Hit return")
#        play_random_album()
#    except Exception as e:
#        logging.error("Ignoring exception: %s", str(e))

led = PWMLED(17, active_high = False)

def do_stuff():
    led.blink(on_time = 0.3, n = 1)
    if args.test:
        print('playing')
        sleep(1)
    else:
        play_random_album()
    led.blink(on_time = 0.1, off_time = 0.1, n = 3)

print('Ready')
button = Button(27) # Defaults to pull-up using internal resistor
button.when_pressed = do_stuff
pause()
