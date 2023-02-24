import flask
import requests
import uuid
import urllib
import webbrowser
import json
import sys
from random import randint, shuffle

# Local host ip address is almost always 127.0.0.1
HOST_IP_ADDRESS = ''
HOST_PORT = '8080'

# Env vars
CLIENT_ID = ''
CLIENT_SECRET = ''
BASE64_ENCODED = ''
REDIRECT_URI = ''

welcome_text = '''''
██████╗ ██╗     ███████╗███╗   ██╗██████╗ ███████╗██████╗ ███████╗███╗   ███╗
██╔══██╗██║     ██╔════╝████╗  ██║██╔══██╗██╔════╝██╔══██╗██╔════╝████╗ ████║
██████╔╝██║     █████╗  ██╔██╗ ██║██║  ██║█████╗  ██████╔╝█████╗  ██╔████╔██║
██╔══██╗██║     ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗██╔══╝  ██║╚██╔╝██║
██████╔╝███████╗███████╗██║ ╚████║██████╔╝███████╗██║  ██║██║     ██║ ╚═╝ ██║
╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝
                                                                             
'''''

app = flask.Flask('BlenderFM')

@app.route('/')
def login():
    auth_request_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'state': str(uuid.uuid4()),
        'scope': 'playlist-modify-private playlist-modify-public',
        'show_dialog': 'true'
    }

    auth_url = 'https://accounts.spotify.com/authorize/?' + urllib.parse.urlencode(auth_request_params)

    webbrowser.open(auth_url)

    return 'Welcome to BlenderFM!! This app works from the command-line.'

def get_access_token(code):
    endpoint = 'https://accounts.spotify.com/api/token/?'

    body = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    } 

    header = {
        'Authorization': 'Basic ' + BASE64_ENCODED,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response: requests.Response = requests.post(endpoint, data=body, headers=header)
    if response.status_code == 200:
        return response.json()
    
    raise Exception(f'Failed to obtain Access Token. Response: {response.text}')

@app.route('/callback')
def callback():
    code = flask.request.args.get('code')
    credentials = get_access_token(code)
    token = credentials['access_token']

    user_id = get_profile(token)

    print(welcome_text)
    while True:
        artist_ids = get_artists(token)
        playlist_name, playlist_length = get_playlist_details(len(artist_ids))
        songs = get_all_songs(token, artist_ids, playlist_length)
        songs = list(songs)
        shuffle(songs)
        make_playlist(token, user_id, playlist_name, songs)

        ans = input('\n\nDo you want to Blend more artists? (y/n) ').strip().lower()
        if ans == 'n':
            print('\nBye!')
            break

    return 'Thank you for using BlenderFM!!'


def get_artists(token):
    search_url = 'https://api.spotify.com/v1/search?'
    header = {
        'Authorization': f'Bearer {token}'
    }

    while True:
        try:
            number = int(input('How many artists would you like to Blend? ').strip())

            if number <= 0:
                continue
            
            print(' ')
            print('Enter artists...')
            break
        except ValueError:
            print('You must input a valid number')
            continue

    

    if number <= 0:
            sys.exit('Bye!')
    
    artist_ids = {}
    for i in range(number):
        artist = input(f'{i+1}. ')
        body = {
            'q': artist,
            'type': 'artist',
            'limit': 1
        }

        response: requests.Response = requests.get(search_url, headers=header, params=body)
        if response.status_code == 200:
            response = response.json()
            content = response['artists']['items']
            artist_url = str(content[0]['external_urls']['spotify'])
            artist_id = artist_url.split('artist/')[1]
            artist_ids[artist] = artist_id
            
        else:
            raise Exception(f'Failed to search. Response: {response.text}')

    print(' ')    
    return artist_ids

def get_playlist_details(num_artists):
    name = input('Enter playlist name: ').strip()
    
    while True:
        try:
            length = int(input('How many songs in the playlist? (max 100) ').strip())

            if length <= 0:
                continue

            if length < num_artists:
                print(f'Your playlist is too short! You need at least {num_artists} songs')
                continue

            break
        except ValueError:
            print('You must input a valid number')
            length = int(input('How many songs in the playlist? (max 100) '))
    
    print('\n** If artists\' total songs are less than entered number, playlist will be shorter\n')

    return name, length

def get_all_songs(token, ids, length):
    num_artists = len(ids)
    rem = length % num_artists
    limit = (length - rem) / num_artists

    songs = set()

    for id in ids:
        start_len = len(songs)
        indiv_songs = get_artist_music(token, ids[id])
        if len(indiv_songs) > limit:
            while len(songs) - start_len < limit:
                i = randint(0,len(indiv_songs)-1)
                songs.add(indiv_songs[i])

    for id in ids:
        while rem > 0:
            start_len = len(songs)
            indiv_songs = get_artist_music(token, ids[id])
            while len(songs) == start_len:
                i = randint(0,len(indiv_songs)-1)
                songs.add(indiv_songs[i])
            rem -= 1

    return songs
    
def make_playlist(token, user_id, name, songs):
    uris = [f'spotify:track:{song}' for song in songs]

    playlist_id = create_playlist(token, user_id, name)
    update_playlist_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    header = {
        'Authorization': f'Bearer {token}'
    }
    body = {
        'uris': uris
    }

    response: requests.Response = requests.post(update_playlist_url, headers=header, data=json.dumps(body))
    if response.status_code == 201:
        print(f'Playlis \"{name}\" was added to your library!')
        print('Check it out!!')
        
    else:
        raise Exception(f'Failed to add songs to playlist. Response: {response.text}')

def create_playlist(token, user_id, name):
    playlist_url = f'https://api.spotify.com/v1/users/{user_id}/playlists'
    body = {
        'name': name
    }
    header = {
        'Authorization': f'Bearer {token}'
    }

    response: requests.Response = requests.post(playlist_url, headers=header, data=json.dumps(body))
    if response.status_code == 201:
        response = response.json()
        playlist_id = str(response['id'])
        
    else:
        raise Exception(f'Failed to get create playlist. Response: {response.text}')

    return playlist_id

def get_profile(token):
    profile_url = 'https://api.spotify.com/v1/me'
    header = {
        'Authorization': f'Bearer {token}'
    }

    response: requests.Response = requests.get(profile_url, headers=header)
    if response.status_code == 200:
        response = response.json()
        user_id = str(response['id'])
        
    else:
        raise Exception(f'Failed to get profile. Response: {response.text}')
    
    return user_id

def get_artist_music(token, artist_id):
    albums = get_albums(token, artist_id)

    header = {
        'Authorization': f'Bearer {token}'
    }

    songs = []

    for album in albums:
        song_url = f'https://api.spotify.com/v1/albums/{album}/tracks'

        response: requests.Response = requests.get(song_url, headers=header)
        if response.status_code == 200:
            response = response.json()
            items = response['items']
            for item in items:
                songs.append(str(item['id']))
            
        else:
            raise Exception(f'Failed to get albums. Response: {response.text}')

    return songs


def get_albums(token, artist_id):
    album_url = f'https://api.spotify.com/v1/artists/{artist_id}/albums'
    header = {
        'Authorization': f'Bearer {token}'
    }
    body = {
        'include_groups': 'album',
        # 'limit': limit
    }

    albums = []

    response: requests.Response = requests.get(album_url, headers=header, params=body)
    if response.status_code == 200:
        response = response.json()
        items = response['items']
        for item in items:
            albums.append(str(item['id']))
        
    else:
        raise Exception(f'Failed to get albums. Response: {response.text}')

    return albums

if __name__ == '__main__':
    app.run(HOST_IP_ADDRESS, HOST_PORT)
