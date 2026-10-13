from unittest.mock import patch

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from datetime import date, datetime, timedelta

from tvshow.models import Show, Season, Episode, Movie
from tvshow.utils.utils import extract_genres, fetch_deduplicated_recommendations


class ModelTestHelpersMixin:
    def create_user(self, username='tester', password='password123'):
        return User.objects.create_user(username=username, password=password)

    def create_show(self, user, **kwargs):
        defaults = {
            'user': user,
            'seriesName': 'Test Show',
            'overview': 'Overview',
            'runningStatus': 'Continuing',
            'network': 'Network',
            'tvdbID': '123',
        }
        defaults.update(kwargs)
        return Show.objects.create(**defaults)

    def create_season(self, show, number=1, status_watched=False):
        return Season.objects.create(show=show, number=number, status_watched=status_watched)

    def create_episode(self, season, number=1, name='Episode', firstAired=None, status_watched=False, tvdbID=None):
        if firstAired is None:
            firstAired = None
        if tvdbID is None:
            tvdbID = 'ep-%s-%s' % (season.id, number)
        return Episode.objects.create(
            season=season,
            episodeName=name,
            number=number,
            firstAired=firstAired,
            status_watched=status_watched,
            tvdbID=tvdbID,
        )


class ShowModelTests(ModelTestHelpersMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()

    def test_total_episodes_and_aired_episodes(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        self.create_episode(season, number=1, firstAired=date(2020, 1, 1))
        self.create_episode(season, number=2, firstAired=date(2020, 2, 1))
        self.create_episode(season, number=3, firstAired=date(2099, 1, 1))
        self.create_episode(season, number=4, firstAired=None)

        self.assertEqual(show.total_episodes, 4)
        self.assertEqual(show.total_aired_episodes, 2)

    def test_episode_watch_count(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        self.create_episode(season, number=1, status_watched=True)
        self.create_episode(season, number=2, status_watched=False)
        self.assertEqual(show.episode_watch_count, 1)

    def test_is_watched_true_with_fully_watched_season(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        self.create_episode(season, number=1, status_watched=True)
        self.create_episode(season, number=2, status_watched=True)
        self.assertTrue(show.is_watched)

    def test_is_watched_false_with_unwatched_episode(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        self.create_episode(season, number=1, firstAired=date(2020, 1, 1), status_watched=True)
        self.create_episode(season, number=2, firstAired=date(2020, 1, 1), status_watched=False)
        self.assertFalse(show.is_watched)

    def test_is_watched_true_for_empty_show(self):
        show = self.create_show(self.user)
        self.assertTrue(show.is_watched)

    def test_is_watched_ignores_empty_seasons(self):
        show = self.create_show(self.user)
        full_season = self.create_season(show, number=1)
        empty_season = self.create_season(show, number=2)
        self.create_episode(full_season, number=1, status_watched=True)
        # Empty season has no episodes; is_watched should still be true.
        self.assertTrue(show.is_watched)

    def test_next_episode_returns_earliest_unwatched_aired(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        late = self.create_episode(season, number=2, firstAired=date(2020, 3, 1), status_watched=False)
        early = self.create_episode(season, number=1, firstAired=date(2020, 1, 1), status_watched=False)
        self.create_episode(season, number=3, firstAired=date(2020, 2, 1), status_watched=True)
        self.assertEqual(show.next_episode, early)

    def test_next_episode_none_when_all_watched(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        self.create_episode(season, number=1, status_watched=True)
        self.assertIsNone(show.next_episode)

    def test_upcoming_episode_returns_future_unwatched(self):
        show = self.create_show(self.user)
        season = self.create_season(show)
        past = self.create_episode(season, number=1, firstAired=date(2020, 1, 1), status_watched=False)
        future = self.create_episode(season, number=2, firstAired=date(2099, 1, 1), status_watched=False)
        self.assertEqual(show.upcoming_episode, future)

    def test_get_genres_property(self):
        show = self.create_show(self.user, genre_list='[{"name": "Drama"}, {"name": "Sci-Fi"}]')
        self.assertEqual(show.get_genres, [{'name': 'Drama'}, {'name': 'Sci-Fi'}])

    def test_str(self):
        show = self.create_show(self.user, seriesName='My Show')
        self.assertEqual(str(show), 'My Show')

    def test_add_show_simple(self):
        # Exercise add_show with offline-like data shape (no network calls except wrappers)
        with patch('tvshow.models.get_image_link', return_value='http://img'), \
             patch('tvshow.models.get_series_translation', side_effect=Exception('nope')):
            show = Show()
            data = {
                'id': 999,
                'name': 'Added Show',
                'overview': 'Added overview',
                'originalLanguage': 'eng',
                'originalCountry': 'US',
                'aired': '2020-01-01',
                'slug': 'added-show',
                'genres': [{'name': 'Drama'}],
                'remoteIds': [{'sourceName': 'IMDB', 'id': 'tt123'}],
                'originalNetwork': {'name': 'HBO'},
            }
            show.add_show(data, 'Continuing', self.user)
            self.assertEqual(show.seriesName, 'Added Show')
            self.assertEqual(show.tvdbID, 999)
            self.assertEqual(show.imdbID, 'tt123')
            self.assertEqual(show.network, 'HBO')
            self.assertEqual(show.user, self.user)
            self.assertIsNotNone(show.pk)

    def test_add_show_translation_path(self):
        with patch('tvshow.models.get_image_link', return_value='http://img'), \
             patch('tvshow.models.get_series_translation', return_value={'name': 'English Name', 'overview': 'English overview'}):
            show = Show()
            data = {
                'id': 1000,
                'name': 'Original Name',
                'overview': 'Original overview',
                'originalLanguage': 'jpn',
                'originalCountry': 'JP',
                'aired': '2020-01-01',
                'slug': 'original-name',
                'genres': [],
                'remoteIds': [],
                'originalNetwork': {'name': 'Fuji'},
                'airsDays': {'Monday': True},
                'airsTime': '20:00',
            }
            show.add_show(data, 'Continuing', self.user)
            self.assertEqual(show.seriesName, 'English Name')
            self.assertEqual(show.overview, 'English overview')
            self.assertEqual(show.airsDays, {'Monday': True})
            self.assertEqual(show.airsTime, '20:00')


class SeasonModelTests(ModelTestHelpersMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.show = self.create_show(self.user)

    def test_watch_count_and_episode_count(self):
        season = self.create_season(self.show)
        today = timezone.now().date()
        past = today - timedelta(days=5)
        future = today + timedelta(days=5)
        self.create_episode(season, number=1, firstAired=past, status_watched=True)
        self.create_episode(season, number=2, firstAired=future, status_watched=False)
        self.create_episode(season, number=3, firstAired=past, status_watched=False)
        self.assertEqual(season.episode_count, 2)  # both past
        self.assertEqual(season.watch_count, 1)

    def test_status_watched_check_sets_and_returns_flag(self):
        season = self.create_season(self.show)
        today = timezone.now().date()
        past = today - timedelta(days=5)
        ep = self.create_episode(season, number=1, firstAired=past, status_watched=False)
        self.assertFalse(season.status_watched_check)
        self.assertFalse(season.status_watched)
        ep.status_watched = True
        ep.save()
        self.assertTrue(season.status_watched_check)
        self.assertTrue(season.status_watched)

    def test_wst_toggles_episodes_and_status(self):
        season = self.create_season(self.show)
        past = date(2020, 1, 1)
        ep = self.create_episode(season, number=1, firstAired=past, status_watched=False)

        # Currently not watched -> wst marks aired episodes watched
        season.wst()
        ep.refresh_from_db()
        season.refresh_from_db()
        self.assertTrue(ep.status_watched)
        self.assertTrue(season.status_watched)

        # Now watched -> wst unmarks all
        season.wst()
        ep.refresh_from_db()
        season.refresh_from_db()
        self.assertFalse(ep.status_watched)
        self.assertFalse(season.status_watched)

    def test_set_watched_true_marks_aired_episodes(self):
        season = self.create_season(self.show)
        today = timezone.now().date()
        past = today - timedelta(days=5)
        future = today + timedelta(days=5)
        past_ep = self.create_episode(season, number=1, firstAired=past, status_watched=False)
        future_ep = self.create_episode(season, number=2, firstAired=future, status_watched=False)

        season.set_watched(True)
        past_ep.refresh_from_db()
        future_ep.refresh_from_db()
        season.refresh_from_db()
        self.assertTrue(past_ep.status_watched)
        self.assertFalse(future_ep.status_watched)
        self.assertTrue(season.status_watched)

    def test_set_watched_false_unmarks_all_episodes(self):
        season = self.create_season(self.show)
        today = timezone.now().date()
        past = today - timedelta(days=5)
        ep1 = self.create_episode(season, number=1, firstAired=past, status_watched=True)
        season.status_watched = True
        season.save()
        season.set_watched(False)
        ep1.refresh_from_db()
        season.refresh_from_db()
        self.assertFalse(ep1.status_watched)
        self.assertFalse(season.status_watched)

    def test_str(self):
        season = self.create_season(self.show, number=3)
        self.assertEqual(str(season), 'Test Show S3')


class EpisodeModelTests(ModelTestHelpersMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.show = self.create_show(self.user)
        self.season = self.create_season(self.show)

    def test_wst_toggles_status_and_date(self):
        ep = self.create_episode(self.season, number=1, status_watched=False)
        ep.wst()
        ep.refresh_from_db()
        self.assertTrue(ep.status_watched)
        self.assertIsNotNone(ep.date_watched)
        ep.wst()
        ep.refresh_from_db()
        self.assertFalse(ep.status_watched)
        self.assertIsNone(ep.date_watched)

    def test_wst_updates_season_status(self):
        ep = self.create_episode(self.season, number=1, status_watched=False, firstAired=date(2020, 1, 1))
        ep.wst()
        self.season.refresh_from_db()
        self.assertTrue(self.season.status_watched)

    def test_compare_or_update_sets_fields(self):
        ep = self.create_episode(self.season, number=1, name='Old', firstAired=None)
        ep.overview = None
        ep.episodeImage = None
        ep.imdbID = None
        ep.save()
        new_data = {
            'name': 'New Name',
            'finaleType': 'season',
            'runtime': 45,
            'aired': '2021-02-02',
            'overview': 'New overview',
        }
        with patch('tvshow.models.get_episode', return_value={'image': 'http://epimg'}), \
             patch('tvshow.models.get_episode_extended', return_value={'remoteIds': [{'sourceName': 'IMDB', 'id': 'tt999'}]}):
            ep.compare_or_update(new_data)
        ep.refresh_from_db()
        self.assertEqual(ep.episodeName, 'New Name')
        self.assertEqual(ep.finaleType, 'season')
        self.assertEqual(ep.runtime, 45)
        self.assertEqual(str(ep.firstAired), '2021-02-02')
        self.assertEqual(ep.overview, 'New overview')
        self.assertEqual(ep.episodeImage, 'http://epimg')
        self.assertEqual(ep.imdbID, 'tt999')

    def test_add_episode(self):
        with patch('tvshow.models.get_episode_translation', side_effect=Exception('nope')):
            ep = Episode()
            data = {
                'id': 'ep-new',
                'name': 'Pilot',
                'number': '1',
                'aired': '2020-05-05',
                'image': 'http://img',
                'overview': 'Pilot overview',
                'runtime': 30,
                'finaleType': None,
            }
            ep.add_episode(self.season, data)
            self.assertEqual(ep.episodeName, 'Pilot')
            self.assertEqual(ep.number, 1)
            self.assertEqual(str(ep.firstAired), '2020-05-05')
            self.assertEqual(ep.episodeImage, 'http://img')
            self.assertEqual(ep.runtime, 30)
            self.assertIsNotNone(ep.pk)

    def test_str(self):
        ep = self.create_episode(self.season, number=4, name='Ep4')
        self.assertEqual(str(ep), 'Test Show S1E4')


class MovieModelTests(ModelTestHelpersMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()

    def test_wst_toggles(self):
        movie = Movie.objects.create(
            user=self.user, tvdbID='m1', name='Movie', overview='o',
            country='US', director='D', studio='S', genre_list='[]',
            status='Released', year='2020',
        )
        movie.wst()
        movie.refresh_from_db()
        self.assertTrue(movie.status_watched)
        self.assertIsNotNone(movie.date_watched)
        movie.wst()
        movie.refresh_from_db()
        self.assertFalse(movie.status_watched)
        self.assertIsNone(movie.date_watched)

    def test_get_genres(self):
        movie = Movie.objects.create(
            user=self.user, tvdbID='m2', name='Movie2', overview='o',
            country='US', director='D', studio='S', genre_list='[{"name":"Action"}]',
            status='Released', year='2020',
        )
        self.assertEqual(movie.get_genres, [{'name': 'Action'}])

    def test_add_movie(self):
        movie = Movie()
        data = {
            'id': 55,
            'name': 'Movie X',
            'slug': 'movie-x',
            'image': 'http://mimg',
            'genres': [{'name': 'Drama'}],
            'remoteIds': [{'sourceName': 'IMDB', 'id': 'tt55'}],
            'status': {'name': 'Released'},
            'year': '2021',
            'runtime': 120,
        }
        movie.add_movie(data, 'Overview X', self.user)
        self.assertEqual(movie.name, 'Movie X')
        self.assertEqual(movie.tvdbID, 55)
        self.assertEqual(movie.imdbID, 'tt55')
        self.assertEqual(movie.slug, 'movie-x')
        self.assertEqual(movie.image_url, 'http://mimg')
        self.assertEqual(movie.status, 'Released')
        self.assertEqual(movie.year, '2021')
        self.assertEqual(movie.runtime, 120)
        self.assertIsNotNone(movie.pk)

    def test_str(self):
        movie = Movie.objects.create(
            user=self.user, tvdbID='m3', name='Named Movie', overview='o',
            country='US', director='D', studio='S', genre_list='[]',
            status='Released', year='2020',
        )
        self.assertEqual(str(movie), 'Named Movie')


class UtilsTests(TestCase):
    def test_extract_genres_dict_list(self):
        show = type('Show', (), {})()
        show.genre_list = '[{"name": "Drama"}, {"name": "sci-fi"}]'
        self.assertEqual(set(extract_genres(show)), {'Drama', 'Sci-Fi'})

    def test_extract_genres_string_list(self):
        show = type('Show', (), {})()
        show.genre_list = '["action", "comedy"]'
        self.assertEqual(set(extract_genres(show)), {'Action', 'Comedy'})

    def test_extract_genres_list_object(self):
        show = type('Show', (), {})()
        show.genre_list = [{'name': 'Drama'}]
        self.assertEqual(extract_genres(show), ['Drama'])

    def test_extract_genres_empty(self):
        show = type('Show', (), {})()
        show.genre_list = ''
        self.assertEqual(extract_genres(show), [])
        show.genre_list = None
        self.assertEqual(extract_genres(show), [])

    def test_extract_genres_malformed(self):
        show = type('Show', (), {})()
        show.genre_list = '{not valid json'
        self.assertEqual(extract_genres(show), [])

    def test_fetch_recommendations_filters_and_dedups(self):
        user = User.objects.create_user('recuser', password='pass')
        from django.contrib.auth.models import User as U
        # Attach show_set accessor by using real user
        existing = Show.objects.create(
            user=user, seriesName='Existing Show', overview='o',
            runningStatus='Continuing', network='N', tvdbID='111',
        )

        tmdb_results = {
            'similar': {
                'results': [
                    {'name': 'Existing Show'},
                    {'name': 'New One'},
                    {'name': 'New Two'},
                    {'name': 'Dup Tvdb'},
                    {'name': 'Dup Tvdb Alias'},
                ]
            }
        }

        def fake_image(name):
            mapping = {
                'New One': ('img1', '', 'imdb1', '222', 'Continuing'),
                'New Two': ('img2', '', 'imdb2', '333', 'Continuing'),
                'Dup Tvdb': ('img3', '', 'imdb3', '444', 'Continuing'),
                'Dup Tvdb Alias': ('img4', '', 'imdb4', '444', 'Continuing'),
            }
            return mapping[name]

        with patch('tvshow.utils.utils.get_recommendations', return_value=tmdb_results), \
             patch('tvshow.utils.utils.get_image_from_search', side_effect=fake_image):
            recs = fetch_deduplicated_recommendations(user, 'Seed Show', target_count=10)

        names = [r['name'] for r in recs]
        self.assertNotIn('Existing Show', names)
        self.assertIn('New One', names)
        self.assertIn('New Two', names)
        self.assertIn('Dup Tvdb', names)
        self.assertNotIn('Dup Tvdb Alias', names)
        self.assertEqual(len(recs), 3)


class JellyfinWebhookTests(ModelTestHelpersMixin, TestCase):
    def setUp(self):
        self.user = self.create_user('juser')
        self.client = Client()
        self.show = self.create_show(self.user, seriesName='Webhook Show')
        self.season = self.create_season(self.show, number=1)
        self.episode = self.create_episode(self.season, number=1, name='Pilot', firstAired=date(2020, 1, 1))

    def url(self):
        return '/api/jellyfin-webhook/%s/' % self.user.username

    def test_method_not_allowed(self):
        resp = self.client.get(self.url())
        self.assertEqual(resp.status_code, 405)

    def test_marks_episode_watched(self):
        payload = {
            'NotificationType': 'PlaybackStop',
            'ItemType': 'Episode',
            'SeriesName': 'Webhook Show',
            'SeasonNumber': 1,
            'EpisodeNumber': 1,
            'PlaybackPositionTicks': 90,
            'RunTimeTicks': 100,
        }
        resp = self.client.post(self.url(), data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        self.episode.refresh_from_db()
        self.season.refresh_from_db()
        self.assertTrue(self.episode.status_watched)
        self.assertTrue(self.season.status_watched)

    def test_ignored_when_below_threshold(self):
        payload = {
            'NotificationType': 'PlaybackStop',
            'ItemType': 'Episode',
            'SeriesName': 'Webhook Show',
            'SeasonNumber': 1,
            'EpisodeNumber': 1,
            'PlaybackPositionTicks': 10,
            'RunTimeTicks': 100,
        }
        resp = self.client.post(self.url(), data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ignored')
        self.episode.refresh_from_db()
        self.assertFalse(self.episode.status_watched)

    def test_episode_not_found(self):
        payload = {
            'NotificationType': 'PlaybackStop',
            'ItemType': 'Episode',
            'SeriesName': 'Webhook Show',
            'SeasonNumber': 1,
            'EpisodeNumber': 999,
            'PlaybackPositionTicks': 90,
            'RunTimeTicks': 100,
        }
        resp = self.client.post(self.url(), data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()['status'], 'error')


class AuthAndViewTests(ModelTestHelpersMixin, TestCase):
    def setUp(self):
        self.client = Client()
        self.user = self.create_user('viewuser')

    def test_login_page_get(self):
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)

    def test_login_valid_redirects(self):
        resp = self.client.post('/login', {'username': 'viewuser', 'password': 'password123'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/')

    def test_login_invalid_stays(self):
        resp = self.client.post('/login', {'username': 'viewuser', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 200)

    def test_home_requires_login(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp['Location'])

    def test_home_authenticated(self):
        self.client.login(username='viewuser', password='password123')
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_movies_page(self):
        self.client.login(username='viewuser', password='password123')
        resp = self.client.get('/movies')
        self.assertEqual(resp.status_code, 200)

    def test_history_page(self):
        self.client.login(username='viewuser', password='password123')
        resp = self.client.get('/history')
        self.assertEqual(resp.status_code, 200)

    def test_stats_page(self):
        self.client.login(username='viewuser', password='password123')
        resp = self.client.get('/stats')
        self.assertEqual(resp.status_code, 200)

    def test_search_with_results(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user, seriesName='Searchable Show')
        resp = self.client.get('/search?query=Searchable')
        self.assertEqual(resp.status_code, 200)

    def test_search_without_results_redirects(self):
        self.client.login(username='viewuser', password='password123')
        resp = self.client.get('/search?query=zzzzzzz')
        self.assertEqual(resp.status_code, 302)

    def test_user_register(self):
        resp = self.client.post('/user_register', {'username': 'newuser', 'password': 'password123'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout(self):
        self.client.login(username='viewuser', password='password123')
        resp = self.client.get('/logout')
        self.assertEqual(resp.status_code, 302)

    def test_episode_swt_toggle(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user)
        season = self.create_season(show)
        ep = self.create_episode(season, number=1, firstAired=date(2020, 1, 1), status_watched=False)
        resp = self.client.post('/episode_swt', {'episode_swt': str(ep.id)})
        self.assertEqual(resp.status_code, 302)
        ep.refresh_from_db()
        self.assertTrue(ep.status_watched)

    def test_season_swt_toggle(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user)
        season = self.create_season(show)
        ep = self.create_episode(season, number=1, firstAired=date(2020, 1, 1), status_watched=False)
        resp = self.client.post('/season_swt', {'season_swt': str(season.id)})
        self.assertEqual(resp.status_code, 302)
        ep.refresh_from_db()
        season.refresh_from_db()
        self.assertTrue(ep.status_watched)
        self.assertTrue(season.status_watched)

    def test_movie_swt_toggle(self):
        self.client.login(username='viewuser', password='password123')
        movie = Movie.objects.create(
            user=self.user, tvdbID='mv1', name='Movie', overview='o',
            country='US', director='D', studio='S', genre_list='[]',
            status='Released', year='2020',
        )
        resp = self.client.post('/movie_swt', {'movie_swt': str(movie.id)})
        self.assertEqual(resp.status_code, 302)
        movie.refresh_from_db()
        self.assertTrue(movie.status_watched)

    def test_later_now_stop(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user)
        # later
        self.client.post('/later', {'show_id': str(show.id)})
        show.refresh_from_db()
        self.assertTrue(show.watch_later)
        # stop
        self.client.post('/stop', {'show_id': str(show.id)})
        show.refresh_from_db()
        self.assertTrue(show.stopped_watching)
        # now
        self.client.post('/now', {'show_id': str(show.id)})
        show.refresh_from_db()
        self.assertFalse(show.watch_later)
        self.assertFalse(show.stopped_watching)

    def test_set_watch_delay(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user)
        resp = self.client.post('/set_watch_delay', {'show_id': str(show.id), 'new_delay': '3'})
        self.assertEqual(resp.status_code, 302)
        show.refresh_from_db()
        self.assertEqual(show.delayWatch, 3)

    def test_mark_all_watched_and_unwatched(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user)
        season = self.create_season(show)
        ep = self.create_episode(season, number=1, firstAired=date(2020, 1, 1), status_watched=False)
        self.client.post('/mark_all_watched', {'show_id': str(show.id)})
        ep.refresh_from_db()
        self.assertTrue(ep.status_watched)
        self.client.post('/mark_all_unwatched', {'show_id': str(show.id)})
        ep.refresh_from_db()
        self.assertFalse(ep.status_watched)

    def test_delete_show(self):
        self.client.login(username='viewuser', password='password123')
        show = self.create_show(self.user)
        resp = self.client.post('/delete_show', {'show_id': str(show.id)})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Show.objects.filter(id=show.id).exists())

    def test_add_search_get(self):
        self.client.login(username='viewuser', password='password123')
        # add_search with GET returns context Flag False
        resp = self.client.get('/add_search')
        self.assertEqual(resp.status_code, 200)
