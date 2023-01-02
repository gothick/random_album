import spotipy
import spotipy.util as util
import random
import logging

class RandomAlbum:
    def __init__(self, username, client_id, client_secret, redirect_uri):
        self.scope = scope = 'streaming user-read-playback-state user-modify-playback-state playlist-read-private app-remote-control'
        logging.info('Prompting for user token.')
        token = util.prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)
        if token:
            self.sp = spotipy.Spotify(auth=token)
        else:
            # Getting the token will likely throw an exception rather than
            # just return Nothing, but just in case...
            print('Could not authenticate.')
            self.sp = None

    def find_playlist_by_name(self, name):
        results = self.sp.current_user_playlists(limit = 50, offset = 0)
        playlists = results['items']
        playlist = next(filter(lambda p: p['name'] == name, playlists), None)
        while playlist is None and results['next']:
            results = self.sp.next(results)
            playlists = results['items']
            playlist = next(filter(lambda p: p['name'] == name, playlists), None)
        return playlist

    def find_device_id_by_name(self, name):
        results = self.sp.devices()
        devices = results['devices']
        device = next(filter(lambda d: d['name'] == name, devices), None)
        if device:
            return device['id']

    def toggle_playback(self) -> bool:
        did_something = False
        p = self.sp.current_playback()
        if p and p['is_playing']:
            logging.info('Pausing playback')
            self.sp.pause_playback()
            did_something = True
        else:
            # Wasn't playing. But we can't just start;
            # we have to see if it's possible first.
            logging.debug(p)
            if p:
                logging.info('Resuming playback')
                self.sp.start_playback()
                did_something = True
            else:
                logging.info('Nothing to resume')
        return did_something

    def play_random_album(self, target_playlist, device_name, album_minimum_tracks = 0):
        # Find our Future Listening playlist.
        playlist = self.find_playlist_by_name(target_playlist)
        total_tracks = playlist['tracks']['total']

        while True:
            # Pick a random song from it
            random_track = random.randint(0, total_tracks - 1)
            tracks = self.sp.playlist_tracks(playlist['id'],limit=1, offset=random_track)
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
            device_id = self.find_device_id_by_name(device_name)
        album_uri = track['album']['uri']
        self.sp.start_playback(context_uri = album_uri, device_id = device_id)
        print("Started playback of entire album.")
