import requests
import random
import re
import hashlib
import os
import json
import feedparser  # RSS feeds - SIN LÍMITE
from datetime import datetime, timedelta
from urllib.parse import urlparse, urldefrag
from PIL import Image
from io import BytesIO

# Múltiples fuentes de noticias
NEWS_API_KEY = os.getenv('NEWS_API_KEY')  # NewsAPI (casi agotado)
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')  # GNews (alternativa)
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000

# RSS Feeds gratuitos (NO TIENEN LÍMITE DE REQUESTS)
RSS_FEEDS = [
    # Internacional
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.reuters.com/rssFeed/worldNews',
    'https://feeds.npr.org/1001/rss.xml',
    # Tecnología
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    # Política/Economía
    'https://feeds.politico.com/politics/news.xml',
    'https://feeds.marketwatch.com/marketwatch/topstories/',
]

def normalizar_url(url):
    if not url:
        return ""
    url, _ = urldefrag(url)
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url_limpia = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, nuevo_query, ''
        ))
        return url_limpia.lower().strip().rstrip('/')
    except:
        return url.lower().strip().rstrip('/')

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('urls', [])), set(data.get('hashes', []))
        except:
            return set(), set()
    return set(), set()

def guardar_historial(urls, hashes):
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': list(hashes)[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat()
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_texto(texto, idioma='EN'):
    if not DEEPL_API_KEY or idioma != 'EN' or not texto:
        return texto
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto[:1000],
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except:
        pass
    return texto

def buscar_noticias_newsapi():
    """Intentar NewsAPI (puede fallar por límite)"""
    if not NEWS_API_KEY:
        return []
    
    try:
        url = "https://newsapi.org/v2/top-headlines"  # Top headlines es más confiable
        params = {
            'category': 'general',
            'language': 'en',
            'pageSize': 20,
            'apiKey': NEWS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == 'ok':
            print(f"✅ NewsAPI: {len(data.get('articles', []))} artículos")
            return data.get('articles', [])
        else:
            print(f"⚠️ NewsAPI error: {data.get('message', 'Unknown')}")
            return []
    except Exception as e:
        print(f"⚠️ NewsAPI falló: {e}")
        return []

def buscar_noticias_gnews():
    """GNews como respaldo"""
    if not GNEWS_API_KEY:
        return []
    
    try:
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'lang': 'en',
            'max': 20,
            'apikey': GNEWS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'articles' in data:
            print(f"✅ GNews: {len(data['articles'])} artículos")
            # Normalizar formato al de NewsAPI
            articulos = []
            for art in data['articles']:
                articulos.append({
                    'title': art.get('title', ''),
                    'description': art.get('description', ''),
                    'url': art.get('url', ''),
                    'urlToImage': art.get('image', ''),
                    'publishedAt': art.get('publishedAt', ''),
                    'source': {'name': art.get('source', {}).get('name', 'GNews')}
                })
            return articulos
        else:
            print(f"⚠️ GNews error: {data.get('errors', 'Unknown')}")
            return []
    except Exception as e:
        print(f"⚠️ GNews falló: {e}")
        return []

def buscar_noticias_rss():
    """RSS Feeds - ILIMITADO y gratuito"""
    noticias = []
    
    # Seleccionar 3 feeds aleatorios para variedad
    feeds_hoy = random.sample(RSS_FEEDS, min(3, len(RSS_FEEDS)))
    
    for feed_url in feeds_hoy:
        try:
            print(f"📡 RSS: {feed_url[:40]}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:10]:  # Top 10 de cada feed
                # Extraer imagen del contenido si existe
                imagen = None
                if 'media_content' in entry:
                    imagen = entry.media_content[0].get('url', '')
                elif 'links' in entry:
                    for link in entry.links:
                        if
