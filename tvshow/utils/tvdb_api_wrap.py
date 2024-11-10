import requests
import json
from django.utils import six
import os,time
from django.conf import settings
from datetime import datetime
import tvdb_v4_official

if six.PY2:
	from urllib import quote
else:
	from urllib.parse import quote

tvdb = tvdb_v4_official.TVDB("5f83a2b4-0f01-4d4d-9ffd-62e5c1779ea9")

def search_series_list(series_name):
	return tvdb.search(series_name)

def get_series_with_id(tvdbID):
	return tvdb.get_series_extended(tvdbID)

def get_season_episode_list(tvdbID, number):
	series = tvdb.get_series_extended(tvdbID)
	for season in sorted(series["seasons"], key=lambda x: (x["type"]["name"], x["number"])):
		if season["type"]["name"] == "Aired Order" and season["number"] == number:
			season = tvdb.get_season_extended(season["id"])
			break
		else:
			season = None
	return season

def get_all_episodes(tvdbID,start_season):
	show = {}
	for i in range(start_season,100):
		season_data = get_season_episode_list(tvdbID, i)
		if season_data:
			show['Season'+str(i)] = season_data
		else:
			break
	return show

def download_image(tvdbID):
	series = tvdb.get_series_artworks(tvdbID, 'en')
	image = series['image']
	#print(image)
	return image
