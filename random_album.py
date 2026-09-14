import spotipy
import random
import logging
import threading
import time
import json
import re

class RandomAlbum:
    def __init__(self, username, client_id, client_secret, redirect_uri, playlist_cache_max_age_seconds = 7 * 24 * 60 * 60):
        self.scope = 'streaming user-read-playback-state user-modify-playback-state playlist-read-private app-remote-control'
        self.username = username
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.playlist_cache_max_age_seconds = playlist_cache_max_age_seconds
        # Built lazily and then reused for the lifetime of the process, so we
        # only pay for a fresh TLS connection once rather than on every
        # button press (that handshake was costing ~5s per press on a Pi 1).
        self.__sp = None
        # Guards self.__sp, the playlist caches and the device id cache:
        # they're used both from GPIO button callbacks and from the
        # keepalive timer thread below.
        self.__lock = threading.Lock()
        self.__keepalive_timer = None
        # Parsed playlist caches, kept in memory for the lifetime of the
        # process (keyed by playlist name) so a button press never has to
        # re-read and re-parse a, potentially large, cache file from disk.
        # The on-disk copy exists purely so a fresh process start doesn't
        # need to rebuild from the API immediately.
        self.__playlist_caches = {}
        # Resolved Spotify Connect device ids, keyed by device name. Device
        # lists can be flaky (a speaker group that hasn't been "woken" up
        # yet just won't be in sp.devices()), and ids aren't guaranteed
        # stable forever either, so this is a cache, not a fact: a failed
        # start_playback drops the entry and re-resolves before the next
        # attempt rather than trusting it indefinitely.
        self.__device_ids = {}

    def __get_sp(self):
        if self.__sp is None:
            logging.info('Creating Spotify client.')
            auth_manager = spotipy.SpotifyOAuth(
                username=self.username,
                scope=self.scope,
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
            )
            self.__sp = spotipy.Spotify(auth_manager=auth_manager)
        return self.__sp

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

    def __resolve_device_id(self, sp, name, attempts = 3, retry_delay_seconds = 1):
        # Spotify Connect device discovery (especially for speaker groups)
        # can lag a button press, so give it a couple of short retries
        # before accepting that the device really isn't there right now.
        for attempt in range(attempts):
            device_id = self.__find_device_id_by_name(sp, name)
            if device_id:
                return device_id
            if attempt < attempts - 1:
                time.sleep(retry_delay_seconds)
        logging.warning(f"Could not find a device called '{name}' after {attempts} attempt(s); falling back to Spotify's currently active device.")
        return None

    def __get_device_id(self, sp, name):
        device_id = self.__device_ids.get(name)
        if device_id is not None:
            return device_id
        device_id = self.__resolve_device_id(sp, name)
        if device_id is not None:
            self.__device_ids[name] = device_id
        return device_id

    def __invalidate_device_id(self, name):
        self.__device_ids.pop(name, None)

    def __cache_path_for_playlist(self, name):
        slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        return f'.playlist_cache-{slug}.json'

    def __load_playlist_cache(self, name):
        try:
            with open(self.__cache_path_for_playlist(name)) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def __save_playlist_cache(self, name, cache):
        with open(self.__cache_path_for_playlist(name), 'w') as f:
            json.dump(cache, f)

    def __cache_is_stale(self, cache):
        return time.time() - cache.get('fetched_at', 0) > self.playlist_cache_max_age_seconds

    def __refresh_playlist_cache(self, target_playlist):
        # Rebuilds the on-disk cache from scratch by paging through every
        # track in the playlist. This is the expensive, multi-request path;
        # it should only run when there's no cache yet, or from the
        # keepalive timer in the background, never on the hot button-press
        # path.
        sp = self.__get_sp()
        playlist = self.__find_playlist_by_name(sp, target_playlist)
        if playlist is None:
            raise ValueError(f"Could not find a playlist called '{target_playlist}'")

        tracks = []
        results = sp.playlist_tracks(playlist['id'])
        while True:
            for item in results['items']:
                track = item.get('track')
                if track is None:
                    # Local files / unavailable tracks turn up as None.
                    continue
                tracks.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album_name': track['album']['name'],
                    'album_uri': track['album']['uri'],
                    'album_total_tracks': track['album']['total_tracks'],
                })
            if not results['next']:
                break
            results = sp.next(results)

        cache = {
            'playlist_id': playlist['id'],
            'fetched_at': time.time(),
            'tracks': tracks,
        }
        self.__save_playlist_cache(target_playlist, cache)
        self.__playlist_caches[target_playlist] = cache
        logging.info(f"Refreshed playlist cache for '{target_playlist}' ({len(tracks)} tracks).")
        return cache

    def __get_playlist_cache(self, target_playlist):
        cache = self.__playlist_caches.get(target_playlist)
        if cache is not None:
            return cache
        cache = self.__load_playlist_cache(target_playlist)
        if cache is not None:
            self.__playlist_caches[target_playlist] = cache
            return cache
        logging.info(f"No cache yet for playlist '{target_playlist}'; fetching now.")
        return self.__refresh_playlist_cache(target_playlist)

    def toggle_playback(self) -> bool:
        did_something = False
        with self.__lock:
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
        with self.__lock:
            logging.info(f"Preparing to play a random album from playlist '{target_playlist}' on device '{device_name}' with minimum {album_minimum_tracks} tracks.")
            sp = self.__get_sp()
            cache = self.__get_playlist_cache(target_playlist)

            # Playlist membership changes don't actually matter here (we play
            # by album URI, not by playlist membership), so we can pick
            # entirely from the cache without hitting the API at all.
            candidates = [t for t in cache['tracks'] if t['album_total_tracks'] >= album_minimum_tracks]
            if not candidates:
                candidates = cache['tracks']
            random.shuffle(candidates)

            device_id = None
            if device_name is not None:
                device_id = self.__get_device_id(sp, device_name)

            # A cached track's album may occasionally have vanished from
            # Spotify entirely since we last refreshed. If so, just spin the
            # wheel again with a different track rather than treating it as
            # fatal - bounded so a genuinely unrelated failure (e.g. no
            # active device) doesn't loop forever.
            max_attempts = min(3, len(candidates))
            for track in candidates[:max_attempts]:
                print(f"Found track {track['name']} by {track['artist']}")
                print(f"...from an album called {track['album_name']}")
                print(f"...with {track['album_total_tracks']} tracks.")
                logging.info(f"Attempting to play album '{track['album_name']}' by {track['artist']}")
                try:
                    sp.start_playback(context_uri = track['album_uri'], device_id = device_id)
                    print("Started playback of entire album.")
                    return
                except spotipy.SpotifyException:
                    logging.exception(f"Couldn't play '{track['album_name']}'; trying a different album, the cache may be stale.")
                    if device_name is not None:
                        # The failure might equally be a stale cached
                        # device_id rather than a stale album URI, so drop
                        # it and re-resolve from scratch before the next
                        # attempt.
                        self.__invalidate_device_id(device_name)
                        device_id = self.__get_device_id(sp, device_name)
            logging.error(f"Gave up trying to play an album from '{target_playlist}' after {max_attempts} attempt(s).")

    def keep_alive(self):
        """Touch the API so the underlying connection (and any NAT/load-balancer
        state along the way) doesn't go idle and get dropped, which would force
        a slow, full TLS handshake on the next button press. Also refreshes any
        playlist cache that's gone stale, so that work never falls on a
        button press either."""
        try:
            # Deliberately ping the API *outside* self.__lock: this call
            # doesn't touch any of the state the lock protects, and holding
            # it here would block a button press for as long as the network
            # call takes to time out (e.g. a slow/flaky DNS lookup), making
            # the whole thing look hung.
            with self.__lock:
                sp = self.__get_sp()
            sp.current_user()
            with self.__lock:
                # Iterate the in-memory caches (not the disk files) so a
                # staleness check never costs us a large JSON parse either.
                for playlist_name, cache in list(self.__playlist_caches.items()):
                    if self.__cache_is_stale(cache):
                        self.__refresh_playlist_cache(playlist_name)
            logging.debug('Keepalive ping sent.')
        except Exception:
            logging.exception('Keepalive ping failed.')

    def start_keepalive(self, interval_seconds):
        def _tick():
            self.keep_alive()
            self.__keepalive_timer = threading.Timer(interval_seconds, _tick)
            self.__keepalive_timer.daemon = True
            self.__keepalive_timer.start()
        _tick()

    def stop_keepalive(self):
        if self.__keepalive_timer:
            self.__keepalive_timer.cancel()
