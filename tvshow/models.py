from django.db import models
from datetime import datetime
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q
from django.contrib.auth.models import User
import json
from .utils.tvdb_api_wrap import *

class Show(models.Model):
	id = models.AutoField(primary_key=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
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
	language = models.CharField(max_length=10, default='eng')
	airsDays = models.JSONField(default=dict)
	airsTime = models.CharField(max_length=10, null=True)
	delayWatch = models.IntegerField(default=0) #how many days to delay showing on "watch next", ex: you watch on a streaming service that makes the show available x days after it airs

	def __str__(self):
		return self.seriesName

	def add_show(self, data, runningStatus, user):
		self.user = user
		self.language = data['originalLanguage']
		if runningStatus == 'Continuing':
			try:
				self.airsDays = data['airsDays']
				self.airsTime = data['airsTime']
			except:
				pass
		self.delayWatch = 0
		if self.language != 'eng':
			t = get_series_translation(data['id'],'eng')
			self.seriesName = t['name']
			try:
				self.overview = t['overview']
			except:
				pass
		else:
			self.seriesName = data['name']
			self.overview = data['overview']
		try:
			self.slug = data['slug']
		except:
			self.slug = slugify(self.seriesName)
		self.banner = get_image_link(data['id'])
		for i in range(len(data['remoteIds'])):
			if data['remoteIds'][i]['sourceName'] == 'IMDB':
				self.imdbID = data['remoteIds'][i]['id']
		self.tvdbID = data['id']
		#self.siteRating = data['score']
		self.network = data['originalNetwork']['name']
		self.runningStatus = runningStatus
		self.genre_list = json.dumps(data['genres'])
		self.last_updated = timezone.now()
		self.watch_later = False
		self.stopped_watching = False
		try:
			self.firstAired = datetime.strptime(data['aired'], '%Y-%m-%d').date()
		except:
			try:
				self.firstAired = datetime.strptime(data['first_air_time'], '%Y-%m-%d').date()
			except:
				pass
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
	def total_aired_episodes(self):
		return Episode.objects.filter(Q(season__show = self),Q(firstAired__lt=timezone.now())).count()

	@property
	def get_genres(self):
		return json.loads(self.genre_list)

	@property
	def next_episode(self):
		return Episode.objects.filter(Q(season__show=self),Q(status_watched=False)).first()

	def update_show_data(self,season_to_update):
		flag = False
		tvdbID = self.tvdbID
		show_online_data = get_series_with_id(tvdbID)
		self.banner = show_online_data['image']
		if self.runningStatus == 'Continuing':
			try:
				self.airsDays = show_online_data['airsDays']
				self.airsTime = show_online_data['airsTime']
			except:
				pass
		self.save()
		if season_to_update == '0':
			current_season = self.season_set.all().last()
		else:
			current_season = self.season_set.get(number=season_to_update)
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
		if season_to_update == '0':
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
	id = models.AutoField(primary_key=True)
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
	id = models.AutoField(primary_key=True)
	season = models.ForeignKey(Season, on_delete=models.CASCADE)
	episodeName = models.CharField(max_length=50, blank=True, null=True)
	number = models.IntegerField()
	firstAired = models.DateField(null=True, blank = True)
	date_watched = models.DateField(null=True, blank=True)
	tvdbID = models.CharField(max_length=50)
	overview = models.TextField(null=True, blank=True)
	status_watched = models.BooleanField(default=False)
	episodeImage = models.CharField(max_length=150, null=True, blank=True)
	finaleType = models.CharField(max_length=30, null=True, blank=True)

	def __str__(self):
		showname = self.season.show.seriesName
		return_string = showname + " S" + str(self.season.number) + "E" + str(self.number)
		return return_string

	def add_episode(self, season, data):
		self.season = season
		self.episodeName = data['name']
		try:
			self.overview = data['overview']
		except:
			pass
		self.number = int(data['number'])
		try:
			self.firstAired = datetime.strptime(data['aired'], '%Y-%m-%d').date()
		except:
			pass
		try:
			self.episodeImage = data['image']
		except:
			pass
		self.tvdbID = data['id']
		self.finaleType = data['finaleType']
		self.save()

	def wst(self):
		if self.status_watched:
			self.status_watched = False
			self.date_watched = None
		else:
			self.status_watched = True
			self.date_watched = timezone.now()
		self.save()
		self.season.show.save()
		if self.season.watch_count == self.season.episode_count:
			self.season.status_watched = True
			self.season.save()
		else:
			self.season.status_watched = False
			self.season.save()

	def compare_or_update(self, new_data):
		t = {}
		if self.season.show.language != 'eng':
			try:
				t = get_episode_translation(self.tvdbID,'eng')
				self.episodeName = t['name']
				self.overview = t['overview']
			except:
				pass
		else:
			self.episodeName = new_data['name']

		self.finaleType = new_data['finaleType']
		
		if new_data['aired'] != "":
			try:
				self.firstAired = new_data['aired']
			except:
				pass
		if self.overview is None:
			if self.season.show.language != 'eng':
				try:
					self.overview = t['overview']
				except:
					self.overview = new_data['overview']
			else:
				self.overview = new_data['overview']
		if self.episodeImage is None:
			try:
				t = get_episode(self.tvdbID)
				self.episodeImage = t['image']
			except:
				pass
		self.save()
