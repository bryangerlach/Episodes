import re
import requests
    
API_KEY = "1045953-Episodes-D63C45BA"  # Replace with your actual API key
BASE_URL = "https://tastedive.com/api/similar"

def get_recommendations(query, media_type, limit=5, info=1):
    cleaned_query = clean_query(query)
    params = {
        "q": cleaned_query,
        "type": media_type,
        "k": API_KEY,
        "limit": limit,
        "info": info
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors

    return response.json()

def clean_query(query):
  """
  Replaces spaces with "+" and removes all special characters from the given query.

  Args:
    query: The input query string.

  Returns:
    The cleaned query string.
  """
  # Replace spaces with "+"
  cleaned_query = query.replace("%2B", "+")
  cleaned_query = query.replace(" ", "+")

  # Remove all special characters
  cleaned_query = re.sub(r"[^\w+]", "", cleaned_query)

  return cleaned_query