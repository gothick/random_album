import spotipy
import creds
import spotipy.util as util
import pprint # For debugging
import random

username  = 'gothick'
scope = 'streaming user-modify-playback-state playlist-read-private app-remote-control'

pp = pprint.PrettyPrinter(indent=4)

def get_playlists(sp):
    results = sp.current_user_playlists(limit = 50, offset =0)
    playlists = results['items']
    while results['next']:
        results = sp.next(results)
        playlists.extend(results['items'])
    return playlists

def find_playlist_by_name(sp, name):
    results = sp.current_user_playlists(limit = 50, offset = 0)
    playlists = results['items']
    playlist = next(filter(lambda p: p['name'] == name, playlists), None)
    while playlist is None and results['next']:
        results = sp.next(results)
        playlists = results['items']
        playlist = next(filter(lambda p: p['name'] == name, playlists), None)
    return playlist

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

    # Pick a random song from it
    total_tracks = playlist['tracks']['total']
    random_track = random.randint(0, total_tracks - 1)
    tracks = sp.playlist_tracks(playlist['id'],limit=1, offset=random_track)
    pp.pprint(tracks['items'][0])


else:
    print('Could not authenticate.')
