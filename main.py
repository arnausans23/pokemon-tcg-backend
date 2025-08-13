"""
Backend API para Pokemon TCG Trader
Conecta Lovable con la API de Pokemon TCG
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import json

# Cargar variables de entorno
load_dotenv()

# Crear app FastAPI
app = FastAPI(
    title="Pokemon TCG Trader Backend",
    description="API para servir datos a Lovable",
    version="1.0.0"
)

# Configurar CORS para que Lovable pueda acceder
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, pon aquí la URL de tu app de Lovable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración
API_KEY = os.getenv('POKEMON_TCG_API_KEY')
BASE_URL = "https://api.pokemontcg.io/v2"
HEADERS = {'X-Api-Key': API_KEY} if API_KEY else {}

# Cache simple en memoria
cache = {}
CACHE_DURATION = 3600  # 1 hora

def get_cached_or_fetch(cache_key: str, fetch_function, *args, **kwargs):
    """Helper para manejar cache"""
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if (datetime.now() - timestamp).seconds < CACHE_DURATION:
            return cached_data
    
    # Fetch new data
    data = fetch_function(*args, **kwargs)
    cache[cache_key] = (data, datetime.now())
    return data


# ============= ENDPOINTS =============

@app.get("/")
def root():
    """Endpoint de prueba"""
    return {
        "message": "Pokemon TCG Trader API",
        "status": "online",
        "endpoints": {
            "search": "/api/search?q=charizard",
            "card": "/api/card/{id}",
            "trending": "/api/trending",
            "set": "/api/set/{id}",
            "sets": "/api/sets"
        }
    }


@app.get("/api/search")
def search_cards(
    q: str,
    page: int = 1,
    pageSize: int = 20,
    orderBy: Optional[str] = None
):
    """
    Buscar cartas
    Ejemplos de query:
    - name:charizard
    - set.name:base
    - rarity:Rare Secret
    """
    try:
        params = {
            'q': q,
            'page': page,
            'pageSize': pageSize
        }
        if orderBy:
            params['orderBy'] = orderBy
        
        response = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Procesar y enriquecer datos
            cards = data.get('data', [])
            for card in cards:
                # Añadir datos calculados
                card['market_price'] = extract_market_price(card)
                card['pull_rate'] = calculate_pull_rate(card)
                card['price_trend'] = calculate_trend(card)
            
            return {
                "success": True,
                "data": cards,
                "page": page,
                "pageSize": pageSize,
                "count": data.get('count', 0),
                "totalCount": data.get('totalCount', 0)
            }
        else:
            raise HTTPException(status_code=response.status_code, detail="Error fetching data")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/card/{card_id}")
def get_card_detail(card_id: str):
    """Obtener detalles de una carta específica con datos enriquecidos"""
    try:
        # Intentar cache primero
        cache_key = f"card_{card_id}"
        
        def fetch_card():
            response = requests.get(
                f"{BASE_URL}/cards/{card_id}",
                headers=HEADERS
            )
            if response.status_code == 200:
                return response.json()['data']
            return None
        
        card = get_cached_or_fetch(cache_key, fetch_card)
        
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Enriquecer datos
        enriched = {
            **card,
            "market_price": extract_market_price(card),
            "all_prices": extract_all_prices(card),
            "pull_rate": calculate_pull_rate(card),
            "price_trend": calculate_trend(card),
            "investment_analysis": calculate_investment(card),
            "related_cards": get_related_cards_ids(card)
        }
        
        return {"success": True, "data": enriched}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trending")
def get_trending_cards():
    """
    Obtener cartas trending (hot & cold)
    En producción, esto vendría de una base de datos con histórico de precios
    """
    try:
        # Por ahora, simulamos con cartas de alta rareza (hot) y comunes (cold)
        
        # Hot cards - Cartas secretas y ultra raras
        hot_params = {
            'q': 'rarity:"Rare Secret" OR rarity:"Hyper Rare"',
            'page': 1,
            'pageSize': 5,
            'orderBy': '-set.releaseDate'
        }
        
        hot_response = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params=hot_params
        )
        
        # Cold cards - Para simular, usamos cartas comunes recientes
        cold_params = {
            'q': 'rarity:"Rare"',
            'page': 1,
            'pageSize': 5,
            'orderBy': 'set.releaseDate'
        }
        
        cold_response = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params=cold_params
        )
        
        hot_cards = []
        cold_cards = []
        
        if hot_response.status_code == 200:
            for card in hot_response.json()['data']:
                hot_cards.append({
                    'id': card['id'],
                    'name': card['name'],
                    'image': card['images']['small'],
                    'set': card['set']['name'],
                    'rarity': card.get('rarity'),
                    'market_price': extract_market_price(card),
                    'price_change': 15.5,  # Simulado, en producción vendría de BD
                    'price_change_percent': 12.3,  # Simulado
                    'pull_rate': calculate_pull_rate(card)
                })
        
        if cold_response.status_code == 200:
            for card in cold_response.json()['data']:
                cold_cards.append({
                    'id': card['id'],
                    'name': card['name'],
                    'image': card['images']['small'],
                    'set': card['set']['name'],
                    'rarity': card.get('rarity'),
                    'market_price': extract_market_price(card),
                    'price_change': -5.2,  # Simulado
                    'price_change_percent': -8.7,  # Simulado
                    'pull_rate': calculate_pull_rate(card)
                })
        
        return {
            "success": True,
            "data": {
                "hot_cards": hot_cards,
                "cold_cards": cold_cards,
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sets")
def get_all_sets(page: int = 1, pageSize: int = 20):
    """Obtener todos los sets"""
    try:
        response = requests.get(
            f"{BASE_URL}/sets",
            headers=HEADERS,
            params={'page': page, 'pageSize': pageSize, 'orderBy': '-releaseDate'}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Enriquecer con datos de trending
            sets = data['data']
            for set_item in sets:
                # En producción, estos datos vendrían de análisis real
                set_item['trending'] = {
                    'total_value_change': 8.5,  # Simulado
                    'hot_cards_count': 3,
                    'average_pull_rate': 2.5
                }
            
            return {
                "success": True,
                "data": sets,
                "page": page,
                "totalCount": data.get('totalCount', 0)
            }
        else:
            raise HTTPException(status_code=response.status_code, detail="Error fetching sets")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/set/{set_id}")
def get_set_detail(set_id: str):
    """Obtener detalles de un set con análisis de mercado"""
    try:
        # Obtener info del set
        set_response = requests.get(
            f"{BASE_URL}/sets/{set_id}",
            headers=HEADERS
        )
        
        if set_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Set not found")
        
        set_data = set_response.json()['data']
        
        # Obtener todas las cartas del set para análisis
        cards_response = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params={'q': f'set.id:{set_id}', 'pageSize': 250}
        )
        
        total_value = 0
        chase_cards = []
        rarity_distribution = {}
        
        if cards_response.status_code == 200:
            cards = cards_response.json()['data']
            
            for card in cards:
                # Calcular valor total
                price = extract_market_price(card)
                total_value += price
                
                # Identificar chase cards (>$30)
                if price > 30:
                    chase_cards.append({
                        'id': card['id'],
                        'name': card['name'],
                        'image': card['images']['small'],
                        'market_price': price,
                        'rarity': card.get('rarity'),
                        'pull_rate': calculate_pull_rate(card)
                    })
                
                # Distribución de rareza
                rarity = card.get('rarity', 'Unknown')
                rarity_distribution[rarity] = rarity_distribution.get(rarity, 0) + 1
        
        # Ordenar chase cards por precio
        chase_cards.sort(key=lambda x: x['market_price'], reverse=True)
        
        return {
            "success": True,
            "data": {
                **set_data,
                "market_analysis": {
                    "total_set_value": round(total_value, 2),
                    "average_card_value": round(total_value / set_data['total'], 2) if set_data['total'] > 0 else 0,
                    "chase_cards": chase_cards[:10],
                    "rarity_distribution": rarity_distribution,
                    "investment_rating": calculate_set_rating(total_value, set_data['total'])
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/related/{card_id}")
def get_related_cards(card_id: str, limit: int = 8):
    """Obtener cartas relacionadas para 'Traders Also Watch'"""
    try:
        # Primero obtener la carta original
        card_response = requests.get(
            f"{BASE_URL}/cards/{card_id}",
            headers=HEADERS
        )
        
        if card_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Card not found")
        
        card = card_response.json()['data']
        related = []
        
        # 1. Mismo Pokemon, diferentes sets
        name_query = f'name:"{card["name"]}" -id:{card_id}'
        same_pokemon = requests.get(
            f"{BASE_URL}/cards",
            headers=HEADERS,
            params={'q': name_query, 'pageSize': 3}
        )
        
        if same_pokemon.status_code == 200:
            for related_card in same_pokemon.json()['data'][:3]:
                related.append(format_related_card(related_card))
        
        # 2. Mismo set, rareza similar
        if 'set' in card and 'rarity' in card:
            set_query = f'set.id:{card["set"]["id"]} rarity:"{card["rarity"]}" -id:{card_id}'
            same_set = requests.get(
                f"{BASE_URL}/cards",
                headers=HEADERS,
                params={'q': set_query, 'pageSize': 2}
            )
            
            if same_set.status_code == 200:
                for related_card in same_set.json()['data'][:2]:
                    related.append(format_related_card(related_card))
        
        # Eliminar duplicados
        seen = set()
        unique_related = []
        for card in related:
            if card['id'] not in seen:
                seen.add(card['id'])
                unique_related.append(card)
                if len(unique_related) >= limit:
                    break
        
        return {
            "success": True,
            "data": unique_related
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= FUNCIONES AUXILIARES =============

def extract_market_price(card: Dict) -> float:
    """Extrae el precio de mercado de una carta"""
    try:
        # Intentar obtener precio normal primero
        prices = card.get('tcgplayer', {}).get('prices', {})
        
        # Orden de preferencia: normal, holofoil, unlimited, 1stEdition
        for variant in ['normal', 'holofoil', 'unlimited', '1stEdition']:
            if variant in prices and 'market' in prices[variant]:
                return prices[variant]['market'] or 0
        
        # Si no hay precio de mercado, intentar con mid
        for variant in prices:
            if 'mid' in prices[variant]:
                return prices[variant]['mid'] or 0
        
        return 0
    except:
        return 0


def extract_all_prices(card: Dict) -> Dict:
    """Extrae todos los precios disponibles"""
    try:
        prices = card.get('tcgplayer', {}).get('prices', {})
        all_prices = {}
        
        for condition, price_data in prices.items():
            all_prices[condition] = {
                'low': price_data.get('low', 0),
                'mid': price_data.get('mid', 0),
                'high': price_data.get('high', 0),
                'market': price_data.get('market', 0),
                'directLow': price_data.get('directLow', 0)
            }
        
        return all_prices
    except:
        return {}


def calculate_pull_rate(card: Dict) -> Dict:
    """Calcula el pull rate estimado basado en la rareza"""
    rarity = card.get('rarity', 'Common')
    
    # Pull rates estimados por rareza
    pull_rates = {
        'Common': {'rate': 65.0, 'packs': 1},
        'Uncommon': {'rate': 30.0, 'packs': 1},
        'Rare': {'rate': 10.0, 'packs': 1},
        'Rare Holo': {'rate': 3.33, 'packs': 3},
        'Rare Holo EX': {'rate': 1.66, 'packs': 6},
        'Rare Holo GX': {'rate': 1.66, 'packs': 6},
        'Rare Holo V': {'rate': 1.66, 'packs': 6},
        'Rare Holo VMAX': {'rate': 0.83, 'packs': 12},
        'Rare Ultra': {'rate': 0.83, 'packs': 12},
        'Rare Secret': {'rate': 0.25, 'packs': 40},
        'Rare Rainbow': {'rate': 0.25, 'packs': 40},
        'Hyper Rare': {'rate': 0.25, 'packs': 40},
        'Special Illustration Rare': {'rate': 0.25, 'packs': 40}
    }
    
    rate_info = pull_rates.get(rarity, {'rate': 5.0, 'packs': 2})
    
    return {
        'percentage': rate_info['rate'],
        'one_in_packs': rate_info['packs'],
        'rarity': rarity
    }


def calculate_trend(card: Dict) -> Dict:
    """
    Calcula la tendencia de precio
    En producción, esto vendría de una base de datos con histórico
    """
    # Por ahora, retornamos datos simulados
    import random
    
    trend = random.choice(['up', 'down', 'stable'])
    change_percent = random.uniform(-15, 25) if trend != 'stable' else random.uniform(-2, 2)
    
    return {
        'direction': trend,
        'change_percent': round(change_percent, 2),
        'change_value': round(extract_market_price(card) * (change_percent / 100), 2)
    }


def calculate_investment(card: Dict) -> Dict:
    """Calcula análisis de inversión (comprar single vs abrir packs)"""
    market_price = extract_market_price(card)
    pull_rate = calculate_pull_rate(card)
    
    packs_needed = pull_rate['one_in_packs']
    pack_cost = 4.50  # Precio promedio de un pack
    
    opening_cost = packs_needed * pack_cost
    
    return {
        'market_price': market_price,
        'average_opening_cost': round(opening_cost, 2),
        'packs_needed_average': packs_needed,
        'roi_percentage': round(((market_price - opening_cost) / opening_cost * 100), 2) if opening_cost > 0 else 0,
        'recommendation': 'BUY_SINGLE' if market_price < opening_cost else 'OPEN_PACKS'
    }


def calculate_set_rating(total_value: float, total_cards: int) -> str:
    """Calcula el rating de inversión de un set"""
    avg_value = total_value / total_cards if total_cards > 0 else 0
    
    if avg_value > 10:
        return "⭐⭐⭐⭐⭐ Exceptional"
    elif avg_value > 5:
        return "⭐⭐⭐⭐ Very Good"
    elif avg_value > 2:
        return "⭐⭐⭐ Good"
    elif avg_value > 1:
        return "⭐⭐ Regular"
    else:
        return "⭐ Basic"


def get_related_cards_ids(card: Dict) -> List[str]:
    """Obtiene IDs de cartas relacionadas (para que el frontend las cargue)"""
    # En una implementación completa, esto haría queries inteligentes
    # Por ahora retornamos una lista vacía que el frontend puede llenar
    return []


def format_related_card(card: Dict) -> Dict:
    """Formatea una carta relacionada para la respuesta"""
    return {
        'id': card['id'],
        'name': card['name'],
        'set': card['set']['name'],
        'image': card['images']['small'],
        'market_price': extract_market_price(card),
        'pull_rate': calculate_pull_rate(card)['percentage'],
        'price_trend': calculate_trend(card),
        'rarity': card.get('rarity')
    }


# ============= INICIALIZACIÓN =============

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    
    print(f"""
    🚀 Pokemon TCG Trader Backend iniciado!
    
    📍 API local: http://localhost:{port}
    📍 Documentación: http://localhost:{port}/docs
    
    🔗 Endpoints principales:
    - GET /api/search?q=charizard
    - GET /api/card/{{id}}
    - GET /api/trending
    - GET /api/sets
    - GET /api/set/{{id}}
    - GET /api/related/{{card_id}}
    
    💡 Tip: Abre http://localhost:{port}/docs para probar la API
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)