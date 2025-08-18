import time
import tvdb_v4_official
from django.conf import settings

# --- Client Caching Mechanism ---
# We will store the client instance and when its token was generated.
_tvdb_client = None
_client_creation_time = 0
# TVDB tokens last 24 hours. We'll refresh after 23.5 hours to be safe.
TOKEN_LIFESPAN_SECONDS = 23.5 * 60 * 60

def get_tvdb_client():
	"""
	Returns a valid TVDB client instance.

	It creates a new client if the existing one is missing or its
	token is nearing expiration.
	"""
	global _tvdb_client, _client_creation_time

	# Check if the client is invalid or its token is old
	is_client_invalid = not _tvdb_client
	is_token_expired = (time.time() - _client_creation_time) > TOKEN_LIFESPAN_SECONDS

	if is_client_invalid or is_token_expired:
		print("Creating a new TVDB client instance...")
		# Initialize the client. This automatically performs login and gets a new token.
		_tvdb_client = tvdb_v4_official.TVDB("67322ef0-b51d-41b2-8af6-fcc3d07b1c1e")
		_client_creation_time = time.time()

	return _tvdb_client

# --- Refactor Your Functions to Use the Factory ---

def search_series_list(series_name):
	tvdb = get_tvdb_client() 
	return tvdb.search(series_name,type="series")

def search_movie_list(movie_name):
	tvdb = get_tvdb_client()
	return tvdb.search(movie_name,type="movie")

def get_series_with_id(tvdbID):
	tvdb = get_tvdb_client()
	return tvdb.get_series_extended(tvdbID)

def get_movie_with_id(tvdbID):
	tvdb = get_tvdb_client()
	return tvdb.get_movie_extended(tvdbID)

def get_season_episode_list(tvdbID, number):
	tvdb = get_tvdb_client()
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
	tvdb = get_tvdb_client()
	return tvdb.get_series_translation(tvdbID,language)

def get_episode_translation(tvdb_epid,language):
	tvdb = get_tvdb_client()
	return tvdb.get_episode_translation(tvdb_epid,language)

def get_episode(episodeID):
	tvdb = get_tvdb_client()
	return tvdb.get_episode(episodeID)

def get_episode_extended(episodeID):
	tvdb = get_tvdb_client()
	return tvdb.get_episode_extended(episodeID)

def get_series(tvdbID):
	tvdb = get_tvdb_client()
	return tvdb.get_series(tvdbID)

def get_image_link(tvdbID):
	tvdb = get_tvdb_client()
	series = tvdb.get_series_artworks(tvdbID, 'en')
	image = series['image']
	#print(image)
	return image

def get_image_from_search(series_name):
	tvdb = get_tvdb_client()
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
