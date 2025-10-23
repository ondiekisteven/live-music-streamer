import requests

from music_db import MusicDatabaseMysql as DB


db = DB()


def fetch_metadata(url): 

    url = 'https://www.youtube.com/oembed?url=https%3A%2F%2Fyoutube.com%2Fwatch%3Fv%3DuFHWebBmi9Q&format=json'
    ...
