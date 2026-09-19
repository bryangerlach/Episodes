import os
import requests

ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"

def get_recommendations(query, media_type='show', limit=5, info=1):
    if not ACCESS_TOKEN:
        print("Error: TMDB_ACCESS_TOKEN environment variable is not set.")
        return {"similar": {"results": []}}
        
    tmdb_type = 'tv' if media_type == 'show' else 'movie'
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    try:
        search_url = f"{BASE_URL}/search/{tmdb_type}"
        search_params = {"query": query, "language": "en-US"}
        search_res = requests.get(search_url, headers=headers, params=search_params)
        search_res.raise_for_status()
        search_data = search_res.json()
        
        results = search_data.get('results', [])
        if not results:
            return {"similar": {"results": []}}
            
        item_id = results[0]['id']
        
        rec_url = f"{BASE_URL}/{tmdb_type}/{item_id}/recommendations"
        rec_params = {"language": "en-US"}
        rec_res = requests.get(rec_url, headers=headers, params=rec_params)
        rec_res.raise_for_status()
        rec_data = rec_res.json()
        
        formatted_results = []
        # REMOVED [:limit] here so we get the full pool of recommendations
        for item in rec_data.get('results', []):
            name = item.get('name') if tmdb_type == 'tv' else item.get('title')
            overview = item.get('overview', '')
            
            # Explicit details call if overview is missing or has non-English scripts
            if (not overview or any(ord(char) > 127 for char in overview[:20])) and item.get('id'):
                detail_url = f"{BASE_URL}/{tmdb_type}/{item['id']}"
                detail_res = requests.get(detail_url, headers=headers, params={"language": "en-US"})
                if detail_res.status_code == 200:
                    detail_data = detail_res.json()
                    overview = detail_data.get('overview', overview)
            
            if name:
                formatted_results.append({
                    "name": name,
                    "overview": overview
                })
                
        return {"similar": {"results": formatted_results}}
        
    except Exception as e:
        print(f"TMDB Recommendations Error: {e}")
        return {"similar": {"results": []}}

def clean_query(query):
    return query