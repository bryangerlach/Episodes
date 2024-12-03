from django.urls import re_path as url
from tvshow import views as views
urlpatterns = [
    url(r'^(?P<view_type>|all|watch_later|stopped_watching|upcoming||)$', views.home),
    url(r'^update_all_shows', views.update_all_continuing),
    url(r'^update_show', views.update_show),
    url(r'^delete_show', views.delete_show),
    # url(r'^update_rating', views.update_show_rating),
    url(r'^add_search', views.add_search),
    url(r'^add', views.add),
    url(r'^search', views.search, name='search'),
    url(r'^show/(?P<show_slug>[a-zA-Z0-9-]*$)', views.single_show),
    url(r'^episode_swt', views.episode_swt),
    url(r'^season_swt', views.season_swt),
    url(r'^mark_all_unwatched', views.mark_all_unwatched),
    url(r'^mark_all_watched', views.mark_all_watched),
    url(r'^later', views.later),
    url(r'^now', views.now),
    url(r'^stop', views.stop),
    url(r'^login', views.login_view),
    url(r'^logout',views.user_logout),
    url(r'^user_action',views.user_action),
    url(r'^user_register',views.user_register),
    url(r'^history',views.history),
    url(r'^set_watch_delay', views.set_watch_delay)
]
