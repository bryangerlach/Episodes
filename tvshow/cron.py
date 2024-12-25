from tvshow.models import Show
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from tvshow.utils.tvdb_api_wrap import get_series_with_id

def update_db_cron():
    show_list = Show.objects.filter(Q(runningStatus='Continuing'),Q(last_updated__lte=timezone.now()-timedelta(days=4)))
    for show in show_list:
        try:
            flag = show.update_show_data("0")
            show.last_updated = timezone.now()
            show_data = get_series_with_id(int(show.tvdbID))
            try:
                show.network = show_data['latestNetwork']['name']
            except:
                pass
            show.save()
            if flag:
                print('%s has been updated.'%show.seriesName)
        except:
            print('%s had errors while updating.'%show.seriesName)
    
    print('Completed db update')