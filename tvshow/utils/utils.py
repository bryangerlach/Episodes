import re
from .recs_api_wrap import get_recommendations
from .tvdb_api_wrap import get_image_from_search

def fetch_deduplicated_recommendations(user, seed_show_name, target_count=5):
    """
    Fetches TMDB recommendations for a given show name, filters out any shows
    already present in the user's library (using normalized titles and multi-field IDs),
    and ensures a consistent target count of recommendations.
    """
    recommended = []
    try:
        user_shows = user.show_set.all()
        
        # Helper to strip spaces, punctuation, and casing for bulletproof title matching
        def norm_title(t):
            if not t:
                return ""
            return re.sub(r'[^a-z0-9]', '', t.lower())

        # Collect normalized titles of existing library shows
        user_norm_names = set(norm_title(s.seriesName) for s in user_shows)
        user_norm_names.add(norm_title(seed_show_name)) # Also exclude the seed show itself
        
        # Collect all possible ID fields stored on existing shows
        user_tvdb_ids = set()
        for s in user_shows:
            for field in ['show_id', 'tvdb_id', 'tvdbID', 'id']:
                val = getattr(s, field, None)
                if val is not None:
                    user_tvdb_ids.add(str(val).strip())
        
        # Call the TMDB wrapper function
        get_recommended = get_recommendations(seed_show_name, 'show')
        if get_recommended and "similar" in get_recommended:
            results = get_recommended["similar"].get("results", [])
            
            for item in results:
                # Stop once we hit our target count of valid recommendations
                if len(recommended) >= target_count:
                    break
                    
                name = item.get('name')
                tmdb_overview = item.get('overview', '') 
                
                if not name:
                    continue
                    
                clean_norm_name = norm_title(name)
                
                # Skip if normalized title matches an existing library show
                if clean_norm_name in user_norm_names:
                    continue
                    
                # Fetch image and IDs from TVDB safely
                image_url, tvdb_overview, imdb_id, tvdb_id, status = None, "", None, None, ""
                try:
                    image_url, _, imdb_id, tvdb_id, status = get_image_from_search(name)
                except Exception:
                    pass
                    
                # Skip if the resolved TVDB ID is already in the user's library
                if tvdb_id and str(tvdb_id).strip() in user_tvdb_ids:
                    continue
                
                # Mark as seen for this session
                user_norm_names.add(clean_norm_name)
                if tvdb_id:
                    user_tvdb_ids.add(str(tvdb_id).strip())
                    
                recommended.append({
                    'name': name,
                    'image_url': image_url,
                    'overview': tmdb_overview if tmdb_overview else tvdb_overview,
                    'imdbID': imdb_id,
                    'tvdb_id': tvdb_id,
                    'status': status
                })
    except Exception as e:
        print(f"Could not fetch recommendations: {e}")
        recommended = []

    return recommended

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