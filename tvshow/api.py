import json
import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Episode, Show
from django.contrib.auth.models import User

@csrf_exempt
def jellyfin_webhook_view(request, username=None):
    user = User.objects.filter(username=username).first()
    shows = Show.objects.filter(user=user)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        notification_type = data.get('NotificationType')
        item_type = data.get('ItemType')
        
        print(f"Received webhook: {notification_type} for {item_type}")

        if notification_type == 'PlaybackStop' and item_type == 'Episode':
            series_name = data.get('SeriesName')
            season_number = data.get('SeasonNumber')
            episode_number = data.get('EpisodeNumber')
            
            playback_position = data.get('PlaybackPositionTicks', 0)
            run_time = data.get('RunTimeTicks', 1)
            percent_watched = (playback_position / run_time) * 100 if run_time > 0 else 0
            
            print(f"Show: {series_name} S{season_number}E{episode_number} - Watched: {percent_watched:.1f}%")

            # For testing, let's relax the percentage rule or keep it >= 85
            if percent_watched >= 85:
                # Case-insensitive lookup for series name
                episode = Episode.objects.filter(
                    season__show__in=shows,
                    season__show__seriesName__iexact=series_name,
                    season__number=season_number,
                    number=episode_number
                ).first()
                
                if episode:
                    episode.status_watched = True
                    episode.date_watched = timezone.now()
                    episode.save()
                    episode.season.show.save()
                    if episode.season.watch_count == episode.season.episode_count:
                        episode.season.status_watched = True
                        episode.season.save()
                    else:
                        episode.season.status_watched = False
                        episode.season.save()
                    
                    return JsonResponse({'status': 'success', 'message': f'Marked {episode} as watched.'})
                else:
                    return JsonResponse({'status': 'error', 'message': f'Episode not found in DB for {series_name} S{season_number}E{episode_number}'}, status=404)

        return JsonResponse({'status': 'ignored', 'message': 'Event ignored or below watch threshold.'})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)