import requests
    
API_KEY = "1045953-Episodes-D63C45BA"  # Replace with your actual API key
BASE_URL = "https://tastedive.com/api/similar"

def get_recommendations(query, media_type, limit=5, info=1):
    params = {
        "q": query,
        "type": media_type,
        "k": API_KEY,
        "limit": limit,
        "info": info
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors

    return response.json()