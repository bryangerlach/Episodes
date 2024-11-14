from django.db import models
from datetime import datetime
from django.utils.text import slugify
from django.db.models import Q
import json
from .utils.tvdb_api_wrap import download_image,get_season_episode_list,get_all_episodes,get_series_with_id

class Show(models.Model):
	tvdbID = models.CharField(max_length=50)
	seriesName = models.CharField(max_length=50)
	overview = models.TextField()
	banner = models.CharField(max_length=150, null=True, blank=True)
	imdbID = models.CharField(max_length=50, null=True, blank=True)
	status_watched = models.BooleanField(default=False)
	slug = models.SlugField(null = True, blank = True)
	runningStatus = models.CharField(max_length=50)
	firstAired = models.DateField(null=True, blank=True)
	modified = models.DateTimeField(null=True, blank=True, auto_now=True, auto_now_add=False)
	siteRating = models.DecimalField(max_digits=5, null=True, decimal_places=3 , blank=True, default=0)
	userRating = models.DecimalField(max_digits=5, null=True, decimal_places=3 , blank=True, default=0)
	network = models.CharField(max_length=50)
	genre_list = models.TextField(null=True, blank=True)
	last_updated = models.DateTimeField(null=True, blank=True)
	watch_later = models.BooleanField(default = False)
	stopped_watching = models.BooleanField(default = False)

	def __str__(self):
		return self.seriesName

	def add_show(self, data, runningStatus):
		self.seriesName = data['name']
		self.slug = slugify(self.seriesName)
		self.overview = data['overview']
		self.banner = download_image(data['id'])
		for i in range(len(data['remoteIds'])):
			if data['remoteIds'][i]['sourceName'] == 'IMDB':
				self.imdbID = data['remoteIds'][i]['id']
		self.tvdbID = data['id']
		#self.siteRating = data['score']
		self.network = data['originalNetwork']['name']
		self.runningStatus = runningStatus
		self.genre_list = json.dumps(data['genres'])
		self.last_updated = datetime.now()
		self.watch_later = False
		self.stopped_watching = False
		try:
			self.firstAired = datetime.strptime(data['aired'], '%Y-%m-%d').date()
		except:
			pass
		self.save()

	@property
	def is_watched(self):
		flag = True
		season_count = Season.objects.filter(show = self)
		for season in season_count:
			if not season.status_watched_check and season.episode_count != 0:
				flag=False
				break
		return flag

	@property
	def episode_watch_count(self):
		return Episode.objects.filter(Q(season__show = self),Q(status_watched=True)).count()

	@property
	def total_episodes(self):
		return Episode.objects.filter(season__show = self).count()

	@property
	def get_genres(self):
		return json.loads(self.genre_list)

	@property
	def next_episode(self):
		return Episode.objects.filter(Q(season__show=self),Q(status_watched=False)).first()

	def update_show_data(self):
		flag = False
		tvdbID = self.tvdbID
		current_season = self.season_set.all().last()
		current_season_db_data = current_season.episode_set.all()
		current_season_oln_data = get_season_episode_list(tvdbID, current_season.number)
		counter = 0
		if current_season_oln_data:
			for db_episode,oln_episode in zip(current_season_db_data, current_season_oln_data['episodes']):
				db_episode.compare_or_update(oln_episode)
				counter+=1
			if counter < len(current_season_oln_data):
				for new_episode in current_season_oln_data['episodes'][counter:]:
					if new_episode['name'] == "":
						new_episode['name'] = 'TBA'
					episode = Episode()
					episode.add_episode(current_season,new_episode)
					flag=True
		range_starter = current_season.number + 1
		new_seasons = get_all_episodes(tvdbID, range_starter)
		for i in range(len(new_seasons)):
			string = 'Season' + str(range_starter+i)
			season_data = new_seasons[string]
			season = Season()
			season.add_season(self, i+range_starter)
			season_episodes_data = new_seasons[string]
			flag=True
			for season_episode in season_episodes_data:
				if season_episode['name']:
					episode = Episode()
					episode.add_episode(season, season_episode)
		return flag
	
	def update_imdb(self):
		#this was used to update data after a database update. no longer needed?
		#TODO: change this to be a refresh all data for a show function
		online_show_data = get_series_with_id(self.tvdbID)
		for i in range(len(online_show_data['remoteIds'])):
			if online_show_data['remoteIds'][i]['sourceName'] == 'IMDB':
				self.imdbID = online_show_data['remoteIds'][i]['id']

class Season(models.Model):
	show = models.ForeignKey(Show, on_delete=models.CASCADE)
	number = models.IntegerField()
	status_watched = models.BooleanField(default = False)

	def __str__(self):
		showname = self.show.seriesName
		return_string = showname + " S" + str(self.number)
		return return_string

	def add_season(self, show, number):
		self.show = show
		self.number = number
		self.save()

	def wst(self):
		self.show.save()
		if self.status_watched:
			self.episode_set.all().update(status_watched = False)
			self.status_watched = False
			self.save()
		else:
			episodes = self.episode_set.all()
			for episode in episodes:
				if episode.firstAired < datetime.now().date():
					episode.status_watched = True
					episode.save()
			self.status_watched = True
			self.save()

	def set_watched(self, watched):
		episodes = self.episode_set.all()
		for episode in episodes:
			if episode.firstAired < datetime.now().date() or not watched:
				episode.status_watched = watched
				episode.save()
		self.status_watched = watched
		self.save()

	@property
	def watch_count(self):
		return Episode.objects.filter(Q(season=self),Q(status_watched=True),Q(firstAired__lte=datetime.now())).count()

	@property
	def episode_count(self):
		return Episode.objects.filter(Q(season=self), Q(firstAired__lte=datetime.now())).count()

	@property
	def status_watched_check(self):
		flag = self.watch_count == self.episode_count
		if(self.status_watched is not flag):
			self.status_watched = flag
			self.save()
		return flag

class Episode(models.Model):
	season = models.ForeignKey(Season, on_delete=models.CASCADE)
	episodeName = models.CharField(max_length=50, blank=True, null=True)
	number = models.IntegerField()
	firstAired = models.DateField(null=True, blank = True)
	date_watched = models.DateField(null=True, blank=True, auto_now=True, auto_now_add=False)
	tvdbID = models.CharField(max_length=50)
	overview = models.TextField(null=True, blank=True)
	status_watched = models.BooleanField(default=False)

	def __str__(self):
		showname = self.season.show.seriesName
		return_string = showname + " S" + str(self.season.number) + "E" + str(self.number)
		return return_string

	def add_episode(self, season, data):
		self.season = season
		self.episodeName = data['name']
		self.number = int(data['number'])
		try:
			self.firstAired = datetime.strptime(data['aired'], '%Y-%m-%d').date()
		except:
			pass
		self.tvdbID = data['id']
		try:
			self.overview = data['overview']
		except:
			pass
		self.save()

	def wst(self):
		self.status_watched = not(self.status_watched)
		self.save()
		self.season.show.save()
		if self.season.watch_count == self.season.episode_count:
			self.season.status_watched = True
			self.season.save()
		else:
			self.season.status_watched = False
			self.season.save()

	def compare_or_update(self, new_data):
		self.episodeName = new_data['name']
		self.save()
		if new_data['aired'] != "":
			try:
				self.firstAired = new_data['aired']
				self.save()
			except:
				pass
		if self.overview is None:
			self.overview = new_data['overview']
			self.save()
