import spotipy
import creds
import spotipy.util as util
import pprint # For debugging
import random

username  = 'gothick'
scope = 'streaming user-read-playback-state user-modify-playback-state playlist-read-private app-remote-control'

pp = pprint.PrettyPrinter(indent=4)

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


token = util.prompt_for_user_token(
    username,
    scope,
    client_id = creds.SPOTIPY_CLIENT_ID,
    client_secret = creds.SPOTIPY_CLIENT_SECRET,
    redirect_uri = creds.REDIRECT_URI
)

if token:
    sp = spotipy.Spotify(auth=token)
    # Find our Future Listening playlist.
    playlist = find_playlist_by_name(sp, "Future Listening")
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
        if track_count > 4:
            break
        print("Trying again to find a bigger album")
        #pp.pprint(track['album'])
        #pp.pprint(track['album']['total_tracks'])
        # print(f"Found track {track['album']['name']}")

    # Found an album with a decent number of tracks. Play it!
    device_id = find_device_id_by_name(sp, 'Stereo Sub Pair')

    # pp.pprint(track['album'])
    album_uri = track['album']['uri']
    print(album_uri)
    # pp.pprint(sp.devices())

    sp.start_playback(context_uri = album_uri, device_id = device_id)

else:
    print('Could not authenticate.')
