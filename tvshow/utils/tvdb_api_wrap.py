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

tvdb = tvdb_v4_official.TVDB("43ac286b-ff13-4878-b172-82228d6f3cc7")

def search_series_list(series_name):
	return tvdb.search(series_name,type="series")

def search_movie_list(movie_name):
	return tvdb.search(movie_name,type="movie")

def get_series_with_id(tvdbID):
	return tvdb.get_series_extended(tvdbID)

def get_movie_with_id(tvdbID):
	return tvdb.get_movie_extended(tvdbID)

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

def get_series_translation(tvdbID,language):
	return tvdb.get_series_translation(tvdbID,language)

def get_episode_translation(tvdb_epid,language):
	return tvdb.get_episode_translation(tvdb_epid,language)

def get_episode(episodeID):
	return tvdb.get_episode(episodeID)

def get_series(tvdbID):
	return tvdb.get_series(tvdbID)

def get_image_link(tvdbID):
	series = tvdb.get_series_artworks(tvdbID, 'en')
	image = series['image']
	#print(image)
	return image

def get_image_from_search(series_name):
	query = tvdb.search(series_name,type="series")
	image_link = query[0]['image_url']
	overview = query[0]['overview']
	tvdb_id = query[0]['tvdb_id']
	status = query[0]['status']
	imdbID = ""
	for rid in query[0]['remote_ids']:
		if rid['sourceName'] == "IMDB":
			imdbID = rid['id']
	return image_link, overview, imdbID, tvdb_id, status
