from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect
from .utils.tvdb_api_wrap import search_series_list, get_series_with_id, get_all_episodes, get_image_link, get_series_translation, search_movie_list, get_movie_with_id, get_image_from_search
from .utils.recs_api_wrap import get_recommendations
from .models import Show,Season,Episode,Movie
from django.db.models import Q
from django.contrib import messages
from datetime import timedelta, datetime
from django.utils import timezone
from random import shuffle
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
import os

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            auth.login(request, user)
            return HttpResponseRedirect('/')
        else:
            # Handle failed login attempt (e.g., display error message)
            pass
    return render(request, 'tvshow/login.html')

def user_action(request):
    action = request.GET.get('action', '')
    if action == 'register':
        return user_register(request)
    elif action == 'logout':
        return user_logout(request)
    else:
        return
    
def user_register(request):
    result = {
        'code':0,
        'msg':''
    }
    if request.method == 'GET':
        return render(request, 'tvshow/register.html')
    
    username = request.POST.get('username', '')
    password1 = request.POST.get('password', '')

    user = User.objects.create_user(username,None,password1)
    result['msg'] = str(user)
    result['code'] = 1
    return HttpResponseRedirect('/')

def user_logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/login')

@login_required(login_url='/login')
def home(request, view_type):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    time = datetime.now()
    
    # Base queryset for the user's shows
    shows = user.show_set.all().order_by('-modified')
    genre_filter = request.GET.get('genre', '').strip()
    language_filter = request.GET.get('language', '').strip()

    # Robust helper function with case-insensitive lookup and safe parsing fallbacks
    def extract_genres(show):
        if not show.genre_list:
            return []
        extracted = []
        try:
            raw = show.genre_list
            if isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except Exception:
                    import ast
                    data = ast.literal_eval(raw)
            else:
                data = raw
                
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    name_val = None
                    for k, v in item.items():
                        if k.lower() == 'name':
                            name_val = v
                            break
                    if name_val and isinstance(name_val, str):
                        extracted.append(name_val.strip().title())
                elif isinstance(item, str):
                    clean_str = item.strip()
                    if clean_str:
                        extracted.append(clean_str.title())
        except Exception:
            pass
        return list(set(extracted))

    # 1. Extract unique clean genres and languages for the dropdowns
    available_genres = set()
    available_languages = set()
    
    for s in shows:
        for g in extract_genres(s):
            available_genres.add(g)
        if s.language:
            available_languages.add(s.language.strip())
            
    available_genres = sorted(list(available_genres))
    available_languages = sorted(list(available_languages))

    # 2. Handle View Type filters
    if view_type == 'all':
        show_data = list(shows)
        flag = False
    elif view_type == 'watch_later':
        show_data = [show for show in shows if show.watch_later]
        flag = False
    elif view_type == 'stopped_watching':
        show_data = [show for show in shows if show.stopped_watching]
        flag = False
    elif view_type == 'upcoming':
        data = [show for show in shows if show.next_episode and show.next_episode.firstAired and (show.next_episode.firstAired > time.date() - timedelta(days=show.delayWatch))]
        show_data = sorted(data, key=lambda x: x.next_episode.firstAired)
        flag = True
    else: # Watch Next view (default)
        data = [show for show in shows if not show.is_watched and not show.watch_later and not show.stopped_watching and show.next_episode.firstAired + timedelta(days=show.delayWatch) <= time.date()]
        for show in data:
            show.watched_pct = show.episode_watch_count / show.total_episodes * 100
        show_data = data
        flag = True

    # 3. Apply Python-side Filters ONLY when viewing 'all'
    if view_type:
        if genre_filter:
            filtered_shows = []
            for show in show_data:
                show_genres = [g.lower() for g in extract_genres(show)]
                if genre_filter.lower() in show_genres:
                    filtered_shows.append(show)
            show_data = filtered_shows

        if language_filter:
            show_data = [show for show in show_data if show.language and show.language.strip().lower() == language_filter.lower()]
        
    return render(request, 'tvshow/home.html', {
        'show_data': show_data, 
        'flag': flag, 
        'time': time, 
        'view_type': view_type,
        'genre_filter': genre_filter,
        'language_filter': language_filter,
        'available_genres': available_genres,
        'available_languages': available_languages
    })
    
@login_required(login_url='/login')
def movies(request, view_type):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    movie_data = user.movie_set.all()
    if view_type == 'movies':
        movie_data = [movie for movie in movie_data if not movie.status_watched]
    elif view_type == 'movies_history':
        movie_data = [movie for movie in movie_data if movie.status_watched]
    else:
        movie_data = movie_data
    return render(request, 'tvshow/home_movies.html', {'movie_data':movie_data, 'view_type':view_type})

@login_required(login_url='/login')
def history(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    shows = Show.objects.filter(user=user)
    episode_data_full = Episode.objects.filter(season__show__in=shows, status_watched=True).order_by('-date_watched')
    episode_data = episode_data_full[:25]
    return render(request, 'tvshow/history.html', {'episode_data': episode_data})

@login_required(login_url='/login')
def update_show(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_info')
        season_to_update = request.POST.get('season',0)
        show = Show.objects.get(user=user, id=show_id)
        if show:
            show.update_show_data(season_to_update)
            show.last_updated = timezone.now()
            show.save()
            return HttpResponseRedirect('/show/%s'%show.slug)
    return HttpResponseRedirect('/')

# @login_required(login_url='/login')
# def update_show_rating(request):
#     if request.method == 'POST':
#         show_id = request.POST.get('show_id')
#         show = Show.objects.get(id=show_id)
#         if show:
#             new_rating = request.POST.get('new_rating')
#             show.userRating = new_rating
#             show.save()
#             return HttpResponseRedirect('/show/%s'%show.slug)
#     return HttpResponseRedirect('/')

@login_required(login_url='/login')
def recommendations_page(request):
    access_token = os.getenv("TMDB_ACCESS_TOKEN")
    
    # Catches None (unset), "" (blank), and "   " (whitespace-only)
    if not access_token or not access_token.strip():
        return render(request, 'tvshow/recommendations.html', {
            'recommended_shows': [],
            'has_token': False
        })
        
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    
    user_shows = user.show_set.all()
    user_show_names = set(show.seriesName.lower().strip() for show in user_shows)
    
    seed_shows = list(user_shows.order_by('-modified')[:5])
    
    recommended_pool = []
    seen_recommendations = set(user_show_names)
    
    for show in seed_shows:
        rec_data = get_recommendations(show.seriesName, media_type='show', limit=5)
        
        for item in rec_data.get("similar", {}).get("results", []):
            name = item.get("name")
            tmdb_overview = item.get("overview", "")
            
            if not name:
                continue
                
            clean_name_lower = name.lower().strip()
            
            if clean_name_lower not in seen_recommendations:
                seen_recommendations.add(clean_name_lower)
                
                image_url, tvdb_overview, imdb_id, tvdb_id, status = None, "", None, None, ""
                try:
                    image_url, _, imdb_id, tvdb_id, status = get_image_from_search(name)
                except Exception:
                    pass
                
                recommended_pool.append({
                    'name': name,
                    'image_url': image_url,
                    'overview': tmdb_overview if tmdb_overview else tvdb_overview,
                    'imdbID': imdb_id,
                    'tvdb_id': tvdb_id,
                    'status': status
                })

    return render(request, 'tvshow/recommendations.html', {
        'recommended_shows': recommended_pool,
        'has_token': True
    })

@login_required(login_url='/login')
def add(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        slug = ''
        tvdbID = request.POST.get('show_id')
        runningStatus = request.POST.get('runningStatus')
        try :
            show = Show.objects.get(user_id=user_id, tvdbID=tvdbID)
            slug = show.slug
        except:
            show_data = get_series_with_id(int(tvdbID))
            if show_data is not None:
                show = Show()
                show.add_show(show_data, runningStatus, user)
                slug = show.slug
                seasons_data = get_all_episodes(int(tvdbID), 1)
                for i in range(len(seasons_data)):
                    string = 'Season' + str(i+1)
                    season_data = seasons_data[string]
                    season = Season()
                    season.add_season(show, i+1)
                    season_episodes_data = seasons_data[string]
                    for season_episode in season_episodes_data['episodes']:
                        #print(season_episode)
                        if season_episode['name']:
                            episode = Episode()
                            episode.add_episode(season, season_episode)
        return HttpResponseRedirect('/show/%s'%slug)
    return HttpResponseRedirect('/all')

@login_required(login_url='/login')
def add_movie(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        slug = ''
        tvdbID = request.POST.get('movie_id')
        overview = request.POST.get('overview')
        try :
            movie = Movie.objects.get(user_id=user_id, tvdbID=tvdbID)
            slug = movie.slug
        except:
            movie_data = get_movie_with_id(int(tvdbID))
            if movie_data is not None:
                movie = Movie()
                movie.add_movie(movie_data, overview, user)
                slug = movie.slug
        return HttpResponseRedirect('/movie/%s'%slug)
    return HttpResponseRedirect('/all')

@login_required(login_url='/login')
def add_search(request):
    context = {}
    context['Flag'] = False
    if request.method == 'POST':
        search_string = request.POST.get('search_string')
        show_datalist_full = search_series_list(search_string)
        show_datalist = show_datalist_full[:10]
        if show_datalist is not None:
            for show in show_datalist:
                if 'primary_language' in show:
                    if show['primary_language'] != 'eng':
                        try:
                            show_eng = get_series_translation(show['tvdb_id'],'eng')
                            show['name'] = show_eng['name']
                            show['overview'] = show_eng['overview']
                        except:
                            pass
                try:
                    show['image'] = get_image_link(show['tvdb_id'])
                except:
                    show['image'] = 'http://twokeyfun.com/noimage.jpg'
            context['Flag'] = True
            context['show_datalist'] = show_datalist
        
    return render(request, 'tvshow/add_search.html', {'context':context})

@login_required(login_url='/login')
def add_search_movie(request):
    context = {}
    context['Flag'] = False
    if request.method == 'POST':
        search_string = request.POST.get('search_string')
        movie_datalist_full = search_movie_list(search_string)
        movie_datalist = movie_datalist_full[:10]
        if movie_datalist is not None:
            context['Flag'] = True
            context['movie_datalist'] = movie_datalist
        
    return render(request, 'tvshow/add_search_movie.html', {'context':context})

@login_required(login_url='/login')
def single_show(request, show_slug):
    rec_flag = request.POST.get('rec_flag', False)
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    show = Show.objects.get(user=user, slug__iexact = show_slug)
    next_episode = show.next_episode
    watched_pct = (show.episode_watch_count / show.total_episodes * 100) if show.total_episodes > 0 else 0
    
    time_obj = datetime.strptime(show.airsTime, "%H:%M").time() if show.airsTime else None
    
    recommended = []
    if rec_flag:
        try:
            # This calls your TMDB wrapper which is forced to en-US
            get_recommended = get_recommendations(show.seriesName, 'show')
            if get_recommended and "similar" in get_recommended:
                results = get_recommended["similar"].get("results", [])
                for item in results:
                    name = item.get('name')
                    tmdb_overview = item.get('overview', '') # English overview straight from TMDB
                    
                    if not name:
                        continue
                        
                    # Fetch image and IDs from TVDB safely without letting TVDB overwrite our English overview
                    image_url, tvdb_overview, imdb_id, tvdb_id, status = None, "", None, None, ""
                    try:
                        image_url, _, imdb_id, tvdb_id, status = get_image_from_search(name)
                    except Exception:
                        pass
                        
                    recommended.append({
                        'name': name,
                        'image_url': image_url,
                        'overview': tmdb_overview if tmdb_overview else tvdb_overview, # Fallback to English TMDB description
                        'imdbID': imdb_id,
                        'tvdb_id': tvdb_id,
                        'status': status
                    })
        except Exception as e:
            print(f"Could not fetch recommendations: {e}")
            recommended = []

    return render(request, 'tvshow/single.html', {
        'show': show, 
        'next_episode': next_episode, 
        'watched_pct': watched_pct, 
        'time': time_obj, 
        'rec_flag': rec_flag, 
        'recommended': recommended 
    })

@login_required(login_url='/login')
def single_movie(request, movie_slug):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    movie = Movie.objects.get(user=user, slug__iexact = movie_slug)
    
    return render(request, 'tvshow/single_movie.html', {'movie':movie})

@login_required(login_url='/login')
def episode_swt(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        shows = Show.objects.filter(user=user)
        episode_id = request.POST.get('episode_swt')
        from_home = request.POST.get('home','')
        episode = Episode.objects.get(season__show__in=shows, id = episode_id)
        if episode:
            episode.wst()
            show = episode.season.show
            if from_home == 'home':
                return HttpResponseRedirect('/')
            else:
                return HttpResponseRedirect('/show/%s'%show.slug)
    return HttpResponseRedirect('/all')

@login_required(login_url='/login')
def season_swt(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        shows = Show.objects.filter(user=user)
        season_id = request.POST.get('season_swt')
        season = Season.objects.get(show__in=shows, id = season_id)
        if season:
            season.wst()
            show = season.show
            return HttpResponseRedirect('/show/%s'%show.slug)
    return HttpResponseRedirect('/all')

@login_required(login_url='/login')
def movie_swt(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        movie_id = request.POST.get('movie_swt')
        movie = Movie.objects.get(user=user,id = movie_id)
        from_home = request.POST.get('home','')
        if movie:
            movie.wst()
            if from_home == 'home':
                return HttpResponseRedirect('/movies')
            else:
                return HttpResponseRedirect('/movie/%s'%movie.slug)
    return HttpResponseRedirect('/all')

@login_required(login_url='/login')
def search(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    shows = Show.objects.filter(user=user)
    search_query = request.GET.get('query')
    show_list = Show.objects.filter(user=user, seriesName__icontains=search_query)
    episode_list = Episode.objects.filter(Q(episodeName__icontains=search_query)|Q(overview__icontains=search_query),season__show__in=shows)[:10]
    if (show_list or episode_list) and search_query:
        return render(request, 'tvshow/search_page.html', {'show_data':show_list, 'episode_list':episode_list})
    return HttpResponseRedirect('/all')

@login_required(login_url='/login')
def refresh_all_continuing(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    #show_list = Show.objects.filter(Q(runningStatus='Continuing'),Q(last_updated__lte=timezone.now()-timedelta(days=7)),user=user)
    show_list = Show.objects.filter(user=user).exclude(runningStatus="Ended")
    for show in show_list:
        flag = show.refresh_show_data()
        if flag:
            messages.success(request, '%s has been refreshed.'%show.seriesName)
            print('%s has been refreshed.'%show.seriesName)
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def refresh_show(request):
    if request.method == "POST":
        show_id = request.POST.get('show_id')
        show = Show.objects.get(id=show_id)
        flag = show.refresh_show_data()
        if flag:
            #messages.success(request, '%s has been refreshed.'%show.seriesName)
            print('%s has been refreshed.'%show.seriesName)
    return HttpResponseRedirect('/show/%s'%show.slug)

@login_required(login_url='/login')
def update_all_continuing(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    show_list = Show.objects.filter(Q(last_updated__lte=timezone.now()-timedelta(days=7)),user=user).exclude(runningStatus="Ended")
    for show in show_list:
        flag = show.update_show_data("0")
        show.last_updated = timezone.now()
        show_data = get_series_with_id(int(show.tvdbID))
        try:
            show.network = show_data['latestNetwork']['name']
        except:
            pass
        show.save()
        if flag:
            messages.success(request, '%s has been updated.'%show.seriesName)
            print('%s has been updated.'%show.seriesName)
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def delete_show(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_id')
        if show_id:
            try:
                show = Show.objects.get(user=user, id=show_id)
                show.delete()
                return HttpResponseRedirect('/')
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def delete_movie(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        movie_id = request.POST.get('movie_id')
        if movie_id:
            try:
                movie = Movie.objects.get(user=user, id=movie_id)
                movie.delete()
                return HttpResponseRedirect('/')
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def mark_all_unwatched(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_id')
        if show_id:
            try:
                show = Show.objects.get(user=user, id=show_id)
                for season in show.season_set.all():
                    season.set_watched(False)
                return HttpResponseRedirect('/')
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')
                
@login_required(login_url='/login')
def mark_all_watched(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_id')
        if show_id:
            try:
                show = Show.objects.get(user=user, id=show_id)
                for season in show.season_set.all():
                    season.set_watched(True)
                return HttpResponseRedirect('/')
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def later(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_id')
        if show_id:
            try:
                show = Show.objects.get(user=user, id=show_id)
                show.watch_later = True
                show.save()
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def now(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_id')
        if show_id:
            try:
                show = Show.objects.get(user=user, id=show_id)
                show.watch_later = False
                show.stopped_watching = False
                show.save()
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def stop(request):
    if request.method == 'POST':
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        show_id = request.POST.get('show_id')
        if show_id:
            try:
                show = Show.objects.get(user=user, id=show_id)
                show.stopped_watching = True
                show.save()
            except:
                return HttpResponseRedirect('/')
    return HttpResponseRedirect('/')

@login_required(login_url='/login')
def set_watch_delay(request):
        if request.method == 'POST':
            user_id = request.user.id
            user = User.objects.get(id=user_id)
            show_id = request.POST.get('show_id')
            show = Show.objects.get(user=user, id=show_id)
            if show:
                new_delay = request.POST.get('new_delay')
                show.delayWatch = new_delay
                show.save()
                return HttpResponseRedirect('/show/%s'%show.slug)
        return HttpResponseRedirect('/')