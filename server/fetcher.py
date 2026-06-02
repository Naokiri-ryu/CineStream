# server/fetcher.py
import requests

def fetch_from_mal(title):
    """Mengambil data dari MyAnimeList menggunakan Jikan API v4 (Gratis)"""
    try:
        url = f"https://api.jikan.moe/v4/anime?q={requests.utils.quote(title)}&limit=1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json().get('data', [])
            if data:
                anime = data[0]
                return {
                    "title": anime.get("title_english") or anime.get("title"),
                    "description": anime.get("synopsis"),
                    "genre": ", ".join([g["name"] for g in anime.get("genres", [])]),
                    "year": anime.get("year") or (anime.get("aired", {}).get("prop", {}).get("from", {}).get("year")),
                    "duration": anime.get("duration"), # Berupa string ex: "24 min per ep"
                    "poster_url": anime.get("images", {}).get("jpg", {}).get("large_image_url")
                }
    except Exception as e:
        print(f"[Fetcher] Gagal mengambil data dari MAL: {e}")
    return None

def fetch_from_imdb(title, api_key="abcdefg"): 
    """
    Mengambil data dari IMDb menggunakan OMDb API.
    Dapatkan API Key gratis di http://www.omdbapi.com/apikey.aspx
    """
    if api_key == "abcdefg" or not api_key:
        return None
    try:
        url = f"http://www.omdbapi.com/?t={requests.utils.quote(title)}&apikey={api_key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("Response") == "True":
                # Konversi durasi "120 min" -> integer 120
                try:
                    duration = int(data.get("Runtime", "0").split()[0])
                except:
                    duration = 0
                    
                return {
                    "title": data.get("Title"),
                    "description": data.get("Plot"),
                    "genre": data.get("Genre"),
                    "year": int(data.get("Year")[:4]) if data.get("Year") else None,
                    "duration": duration,
                    "poster_url": data.get("Poster")
                }
    except Exception as e:
        print(f"[Fetcher] Gagal mengambil data dari IMDb: {e}")
    return None