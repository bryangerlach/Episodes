import requests
from django.core.management.base import BaseCommand
from tvshow.models import Show 
from tvshow.utils.tvdb_api_wrap import get_series_with_id

class Command(BaseCommand):
    help = 'Fetches and updates original_country for all existing shows from the TVDB API.'

    def handle(self, *args, **options):
        shows = Show.objects.all()
        total_shows = shows.count()
        self.stdout.write(f"Found {total_shows} shows to update.")

        updated_count = 0
        for show in shows:
            try:
                tvdb_id = getattr(show, 'tvdbID', None)
                if not tvdb_id:
                    self.stdout.write(self.style.WARNING(f"Skipping {show}: No TVDB ID found."))
                    continue

                series_data = get_series_with_id(int(tvdb_id))
                if isinstance(series_data, dict):
                    show.original_country = series_data.get('originalCountry') or ''
                
                show.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated {show} -> Country: {show.original_country or 'N/A'}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to update {show}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {updated_count} out of {total_shows} shows."))