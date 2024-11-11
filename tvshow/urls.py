from django.urls import re_path as url
from .views import (home, add_search, add ,single_show, episode_swt, season_swt, search, update_show, update_show_rating, recommended, update_all_continuing, delete_show, mark_all_unwatched, mark_all_watched, later, now, stop)
urlpatterns = [
    url(r'^(?P<view_type>|all|watch_later|stopped_watching||)$', home),
    url(r'^update_all_shows', update_all_continuing),
    url(r'^update_show', update_show),
    url(r'^delete_show', delete_show),
    url(r'^update_rating', update_show_rating),
    url(r'^recommended', recommended),
    url(r'^add_search', add_search),
    url(r'^add', add),
    url(r'^search', search, name='search'),
    url(r'^show/(?P<show_slug>[a-zA-Z0-9-]*$)', single_show),
    url(r'^episode_swt', episode_swt),
    url(r'^season_swt', season_swt),
    url(r'^mark_all_unwatched', mark_all_unwatched),
    url(r'^mark_all_watched', mark_all_watched),
    url(r'^later', later),
    url(r'^now', now),
    url(r'^stop', stop),
]
