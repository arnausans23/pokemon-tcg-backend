from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Pokemon TCG Trader Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv('POKEMON_TCG_API_KEY', '')
BASE_URL = "https://api.pokemontcg.io/v2"
HEADERS = {'X-Api-Key': API_KEY} if API_KEY else {}

@app.get("/")
def root():
    return {
        "message": "Pokemon TCG Trader API",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/api/search")
def search_cards(q: str = "pikachu"):
    if ':' not in q:
        q = f'name:*{q}*'
    
    try:
        response = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params={'q': q, 'pageSize': 20}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/trending")
def get_trending():
    try:
        response = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params={
                'q': 'rarity:"Rare Secret"',
                'pageSize': 10
            }
        )
        
        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to fetch trending"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/sets")
def get_sets():
    try:
        response = requests.get(
            f"{BASE_URL}/sets",
            headers=HEADERS,
            params={'pageSize': 20}
        )
        
        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to fetch sets"}
    except Exception as e:
        return {"error": str(e)}
