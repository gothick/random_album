import spotipy
import spotipy.util as util
import random
import logging

class RandomAlbum:
    def __init__(self, username, client_id, client_secret, redirect_uri):
        self.scope = 'streaming user-read-playback-state user-modify-playback-state playlist-read-private app-remote-control'
        self.username = username
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def __get_sp(self):
        logging.info('Prompting for user token.')
        token = util.prompt_for_user_token(self.username, self.scope, self.client_id, self.client_secret, self.redirect_uri)
        if token:
            sp = spotipy.Spotify(auth=token)
        else:
            # Getting the token will likely throw an exception rather than
            # just return Nothing, but just in case...
            print('Could not authenticate.')
            sp = None
        return sp

    def __find_playlist_by_name(self, sp, name):
        results = sp.current_user_playlists(limit = 50, offset = 0)
        playlists = results['items']
        playlist = next(filter(lambda p: p['name'] == name, playlists), None)
        while playlist is None and results['next']:
            results = sp.next(results)
            playlists = results['items']
            playlist = next(filter(lambda p: p['name'] == name, playlists), None)
        return playlist

    def __find_device_id_by_name(self, sp, name):
        results = sp.devices()
        devices = results['devices']
        device = next(filter(lambda d: d['name'] == name, devices), None)
        if device:
            # Beacuse the Amazon devices have started coming back like:
            # 2e1b9eca-eb34-42bb-a270-c5a044d3de62_amzn_1 when what
            # actually works here is "2e1b9eca-eb34-42bb-a270-c5a044d3de62"
            # https://community.spotify.com/t5/Spotify-for-Developers/player-transfer-to-Echo-Dot-Groups-failing/m-p/5509388#M8084
            device_id = device['id'].split('_amzn', 1)[0]
            return device_id

    def toggle_playback(self) -> bool:
        did_something = False
        sp = self.__get_sp()
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
        return did_something

    def play_random_album(self, target_playlist, device_name, album_minimum_tracks = 0):
        # Find our Future Listening playlist.
        sp = self.__get_sp()
        playlist = self.__find_playlist_by_name(sp, target_playlist)
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
            device_id = self.__find_device_id_by_name(sp, device_name)
        album_uri = track['album']['uri']
        sp.start_playback(context_uri = album_uri, device_id = device_id)
        print("Started playback of entire album.")
