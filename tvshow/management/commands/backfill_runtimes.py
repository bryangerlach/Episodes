from django.core.management.base import BaseCommand
from django.db.models import Q
from tvshow.models import Show
from tvshow.utils.tvdb_api_wrap import get_all_episodes, get_series_with_id

class Command(BaseCommand):
    help = 'Fetches and backfills episode runtimes from the TVDB API for all existing shows.'

    def handle(self, *args, **options):
        shows = Show.objects.all()
        self.stdout.write(f"Starting runtime backfill for {shows.count()} shows...")

        for show in shows:
            if not show.tvdbID:
                continue

            # Smart check: Skip if all episodes already have a valid runtime (> 0)
            missing_runtimes = show.season_set.filter(
                Q(episode__runtime=0) | Q(episode__runtime__isnull=True)
            ).exists()

            if not missing_runtimes:
                self.stdout.write(f"Skipping (already complete): {show.seriesName}")
                continue

            self.stdout.write(f"Processing: {show.seriesName} (TVDB ID: {show.tvdbID})")

            try:
                # 1. Fetch series-level data to get a default fallback runtime
                series_data = get_series_with_id(int(show.tvdbID))
                series_runtime = 30  # Default fallback
                if isinstance(series_data, dict):
                    series_runtime = series_data.get('runtime', 30) or 30

                # 2. Fetch all seasons and episodes using your wrapper function
                seasons_data = get_all_episodes(int(show.tvdbID), 1)
                
                updated_count = 0
                for season_key, season_dict in seasons_data.items():
                    if not isinstance(season_dict, dict):
                        continue
                    
                    season_number = season_dict.get('number')
                    episodes_list = season_dict.get('episodes', [])
                    
                    if season_number is None:
                        try:
                            season_number = int(season_key.replace('Season', ''))
                        except ValueError:
                            continue

                    # Match season in database
                    season_obj = show.season_set.filter(number=season_number).first()
                    if not season_obj:
                        continue

                    # Loop through episodes and update runtime
                    for ep_data in episodes_list:
                        ep_tvdb_id = str(ep_data.get('id'))
                        # Use episode runtime if available, otherwise series fallback
                        ep_runtime = ep_data.get('runtime') or series_runtime

                        rows_updated = season_obj.episode_set.filter(tvdbID=ep_tvdb_id, runtime=0).update(runtime=ep_runtime)
                        if rows_updated > 0:
                            updated_count += rows_updated

                self.stdout.write(self.style.SUCCESS(f"  -> Updated {updated_count} episodes for {show.seriesName}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Error processing {show.seriesName}: {e}"))

        self.stdout.write(self.style.SUCCESS("Runtime backfill complete across all shows!"))