import os
import requests

# Fetch the Read Access Token from environment variables
ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"

def get_recommendations(query, media_type='show', limit=5, info=1):
    if not ACCESS_TOKEN:
        print("Error: TMDB_ACCESS_TOKEN environment variable is not set.")
        return {"similar": {"results": []}}
        
    tmdb_type = 'tv' if media_type == 'show' else 'movie'
    
    # Set up the Bearer Token authentication headers
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    try:
        # Step 1: Search for the show to get its TMDB ID
        search_url = f"{BASE_URL}/search/{tmdb_type}"
        search_params = {
            "query": query
        }
        search_res = requests.get(search_url, headers=headers, params=search_params)
        search_res.raise_for_status()
        search_data = search_res.json()
        
        results = search_data.get('results', [])
        if not results:
            return {"similar": {"results": []}}
            
        item_id = results[0]['id']
        
        # Step 2: Fetch official recommendations using the TMDB ID
        rec_url = f"{BASE_URL}/{tmdb_type}/{item_id}/recommendations"
        rec_res = requests.get(rec_url, headers=headers)
        rec_res.raise_for_status()
        rec_data = rec_res.json()
        
        # Step 3: Format the results into the exact dictionary structure views.py expects
        formatted_results = []
        for item in rec_data.get('results', [])[:limit]:
            name = item.get('name') if tmdb_type == 'tv' else item.get('title')
            if name:
                formatted_results.append({"name": name})
                
        return {"similar": {"results": formatted_results}}
        
    except Exception as e:
        print(f"TMDB Recommendations Error: {e}")
        return {"similar": {"results": []}}

def clean_query(query):
    return query