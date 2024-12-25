from django.core.management.base import BaseCommand, CommandError
from tvshow.models import Show
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from tvshow.utils.tvdb_api_wrap import get_series_with_id

class Command(BaseCommand):
    help = 'Updates the database from thetvdb api. This should be run on a cronjob or similar.'

    def handle(self, *args, **options):
        print('updating database')
        show_list = Show.objects.filter(Q(runningStatus='Continuing'),Q(last_updated__lte=timezone.now()-timedelta(days=7)))
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
        
        print('Update task completed!')