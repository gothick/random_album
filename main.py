import spotipy
import creds
import spotipy.util as util

username  = 'gothick'

scope = 'streaming user-modify-playback-state playlist-read-private app-remote-control'

token = util.prompt_for_user_token(
    username,
    scope,
    client_id = creds.SPOTIPY_CLIENT_ID,
    client_secret = creds.SPOTIPY_CLIENT_SECRET,
    redirect_uri = creds.REDIRECT_URI
    )

if token:

    sp = spotipy.Spotify(auth=token)

    results = sp.search(q='Honeyblood', limit=20)
    for idx, track in enumerate(results['tracks']['items']):
        print(idx, track['name'])

    playlists = sp.current_user_playlists(limit = 50, offset = 0)
    for playlist in playlists['items']:
        print(playlist['name'])
else:
    print('Could not authenticate.')
