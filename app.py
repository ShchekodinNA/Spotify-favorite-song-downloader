import random
import string
import time
import urllib.request
import urllib.parse
import yt_dlp
import re
import spotipy
from flask import Flask, request, url_for, session, redirect
from spotipy.oauth2 import SpotifyOAuth
import os

spotify_client_id = os.environ['SPOTIFY_CLIENT_ID']
spotify_client_secret = os.environ['SPOTIFY_CLIENT_SECRET']
TOKEN_INFO = 'token_info'

SAVE_PATH = os.path.join(os.getcwd(), "downloads")

YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': SAVE_PATH + '/%(title)s.%(ext)s'
}


app = Flask(__name__)

app.secret_key = "".join([random.choice(string.ascii_letters + string.ascii_letters) for _ in range(10)])

app.config['SESSION_COOKIE_NAME'] = 'Spotify Downloader'


@app.route('/')
def login():
    sp_oath = create_spotify_oauth()
    auth_url = sp_oath.get_authorize_url()
    return redirect(auth_url)


@app.route('/redirect')
def redirectPg():
    sp_oath = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oath.get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect('getTracks')


@app.route('/getTracks')
def getTracks():
    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])
        all_songs = get_list_of_all_songs(sp)
        reformated_songs = reformat_spotify_item_list(all_songs)
        yt_prepared_songs = prepare_statement_to_search_in_youtube(reformated_songs)
        yt_url_song_lst = yt_searcher(yt_prepared_songs)
        yt_mp3_download(yt_url_song_lst)
        return yt_url_song_lst
    except:
        print('User not logged in')
        return redirect('/')


def yt_mp3_download(links:list[str]):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as yd1:
            yd1.download(links)
    except:
        pass

def yt_searcher(songs: list[str]) -> list[str]:
    res = []
    yt_search_url = 'https://www.youtube.com/results?search_query='
    for i, itm in enumerate(songs):
        try:
            cr_html_txt = urllib.request.urlopen(f"{yt_search_url}{urllib.parse.quote_plus(itm)}").read().decode()
            needed_yt_url = re.search(r'watch\?v=(\S{11})', cr_html_txt)
            res.append(f"https://www.youtube.com/{needed_yt_url.group()}")
            print(f"success:\t{res[-1]}:\t{i}:\t{itm}")
        except:
            print(f"error:\t{i}:\t{itm}")
    return res


def prepare_statement_to_search_in_youtube(rsongs: list[str]) -> list:
    res = []
    for itm in rsongs:
        buf = "+".join(itm.split(' '))
        res.append(buf)
    return res


def reformat_spotify_item_list(songs: list) -> list[str]:
    rslt = []
    for itm in songs:
        subitm = itm["track"]
        rslt.append(f'{subitm["artists"][0]["name"]} {subitm["name"]}')
    return rslt


def get_list_of_all_songs(spotify: spotipy.Spotify) -> list:
    all_songs = []
    iterat = 0
    while True:
        buff = spotify.current_user_saved_tracks(limit=50, offset=iterat * 50)['items']
        all_songs += buff
        if len(buff) < 50:
            break
        iterat += 1
    return all_songs


def get_token():
    token_info = session.get(TOKEN_INFO)
    if not token_info:
        raise "some error"
    now = int(time.time())

    is_expired = token_info["expires_at"] >= now + 60
    if is_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session[TOKEN_INFO] = token_info
    return token_info


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=url_for('redirectPg', _external=True),
        scope='playlist-read-private user-read-private user-library-read'
    )


if __name__ == '__main__':
    app.run()
