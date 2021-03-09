# coding=utf-8
from os import environ

API_ID = int(environ.get('API_ID'))
API_HASH = environ.get('API_HASH')

db_URL = environ.get('POSTGRES_URI')


class MainChannel:
    USERNAME = environ.get("CHANNEL_USERNAME")


admins = ['me']
LOG_FILE = ''  # no file - ''
algo_limit = int(environ.setdefault("ALGOLIMIT", "40"))


class AllowPhotoPosts:
    caption = False
    forwards = False
    author = False
    grouped = False  # album








