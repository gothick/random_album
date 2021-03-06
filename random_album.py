import spotipy
import spotipy.util as util
import random
import logging

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

def toggle_playback(client_id, client_secret, redirect_uri, username) -> bool:
    did_something = False
    scope = 'user-read-playback-state user-modify-playback-state'
    logging.info('Prompting for user token')
    token = util.prompt_for_user_token(
        username,
        scope,
        client_id,
        client_secret,
        redirect_uri
    )
    if token:
        sp = spotipy.Spotify(auth=token)
        p = sp.current_playback()
        if p and p['is_playing']:
            logging.info('Pausing playback')
            sp.pause_playback()
            did_something = True
        else:
            # Wasn't playing. But we can't just start;
            # we have to see if it's possible first.
            logging.debug(p)
            if p:
                logging.info('Resuming playback')
                sp.start_playback()
                did_something = True
            else:
                logging.info('Nothing to resume')
    else:
        print('Could not authenticate.')
    return did_something

def play_random_album(client_id, client_secret, redirect_uri, username, target_playlist, device_name, album_minimum_tracks = 0):
    # Spotify app scopes (permissions)
    scope = 'streaming user-read-playback-state user-modify-playback-state playlist-read-private app-remote-control'
    logging.info('Prompting for user token.')
    token = util.prompt_for_user_token(
        username,
        scope,
        client_id,
        client_secret,
        redirect_uri
    )

    if token:
        sp = spotipy.Spotify(auth=token)
        # Find our Future Listening playlist.
        playlist = find_playlist_by_name(sp, target_playlist)
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
            if track_count >= album_minimum_tracks:
                break
            print('Trying again to find a bigger album')

        # Found an album with a decent number of tracks. Play it!
        device_id = None
        if device_name is not None:
            device_id = find_device_id_by_name(sp, device_name)
        album_uri = track['album']['uri']
        sp.start_playback(context_uri = album_uri, device_id = device_id)
        print("Started playback of entire album.")
    else:
        # Getting the token will likely throw an exception rather than
        # just return Nothing, but just in case...
        print('Could not authenticate.')
