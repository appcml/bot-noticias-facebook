import requests
import random
import re
import hashlib
import os
import json
from datetime import datetime
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"DEBUG: NEWS_API_KEY presente: {bool(NEWS_API_KEY)}")
print(f"DEBUG: FB_PAGE_ID presente: {bool(FB_PAGE_ID)}")
print(f"DEBUG: FB_ACCESS_TOKEN presente: {bool(FB_ACCESS_TOKEN)}")

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    print("ERROR: Variables faltantes esenciales")
    raise ValueError("Faltan variables de entorno esenciales")

print("DEBUG: Variables esenciales OK")

FUENTES_PREMIUM = {
    'internacional': ['bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'aljazeera.com', 'elpais.com', 'clarin.com', 'nytimes.com', 'washingtonpost.com'],
    'economia': ['bloomberg.com', 'forbes.com', 'eleconomista.es', 'expansion.com', 'ambito.com', 'ft.com', 'wsj.com'],
    'tecnologia': ['techcrunch.com', 'theverge.com', 'wired.com', 'xataka.com', 'fayerwayer.com', 'arstechnica.com'],
    'politica': ['politico.com', 'axios.com', 'infobae.com', 'animalpolitico.com', 'reforma.com']
}

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 200

def cargar_historial():
    """Carga el historial de URLs publicadas desde archivo"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('urls', [])), data.get('hashes', [])
        except:
            return set(), []
    return set(), []

def guardar_historial(urls, hashes):
    """Guarda el historial de URLs publicadas"""
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': hashes[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat()
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_texto(texto, idioma_origen='EN'):
    """Traduce texto del inglés al español usando DeepL"""
    if not DEEPL_API_KEY or idioma_origen.upper() != 'EN':
        return texto
    
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto,
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"[TRADUCCIÓN] Error: {e}")
    
    return texto

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"BUSCANDO NOTICIAS VIRALES - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    fecha_ayer = (datetime.now().timestamp() - 86400)
    
    busquedas_virales = [
        ('breaking news OR "just now" OR "developing story"', 'internacional'),
        ('world news today OR international news', 'internacional'),
        ('politics crisis OR emergency OR urgent', 'politica'),
        ('economy markets crash OR surge OR record', 'economia'),
        ('technology AI artificial intelligence breakthrough', 'tech'),
        ('war conflict OR attack OR missile OR invasion', 'crisis'),
        ('disaster earthquake OR hurricane OR flood', 'emergencia')
    ]
    
    busquedas_hoy = random.sample(busquedas_virales, min(5, len(busquedas_virales)))
    todas_noticias = []
    
    for query, categoria in busquedas_hoy:
        url_es = f"https://newsapi.org/v2/everything?q={query}&language=es&from={datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')}&to={fecha_hoy}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        url_en = f"https://newsapi.org/v2/everything?q={query}&language=en&from={datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')}&to={fecha_hoy}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        
        try:
            print(f"[BÚSQUEDA] {categoria}: {query[:40]}...")
            
            response = requests.get(url_es, timeout=15)
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                for art in data['articles']:
                    if es_noticia_valida(art):
                        score = calcular_score(art, categoria)
                        art['categoria'] = categoria
                        art['score'] = score
                        art['url_hash'] = hashlib.md5(art['url'].encode()).hexdigest()[:16]
                        art['idioma'] = 'ES'
                        art['titulo_original'] = art['title']
                        art['descripcion_original'] = art['description']
                        todas_noticias.append(art)
                        print(f"  [ES] {art['title'][:50]}... (score: {score})")
            
            if DEEPL_API_KEY:
                response_en = requests.get(url_en, timeout=15)
                data_en = response_en.json()
                
                if data_en.get('status') == 'ok' and data_en.get('articles'):
                    for art in data_en['articles']:
                        if es_noticia_valida(art):
                            score = calcular_score(art, categoria)
                            art['categoria'] = categoria
                            art['score'] = score
                            art['url_hash'] = hashlib.md5(art['url'].encode()).hexdigest()[:16]
                            art['idioma'] = 'EN'
                            art['titulo_original'] = art['title']
                            art['descripcion_original'] = art['description']
                            art['title'] = traducir_texto(art['title'], 'EN')
                            art['description'] = traducir_texto(art['description'], 'EN')
                            todas_noticias.append(art)
                            print(f"  [EN→ES] {art['title'][:50]}... (score: {score})")
                            
        except Exception as e:
            print(f"[ERROR] en búsqueda {categoria}: {e}")
    
    print(f"\n[INFO] Total noticias encontradas: {len(todas_noticias)}")
    
    noticias_unicas = {}
    for art in todas_noticias:
        if art['url_hash'] not in noticias_unicas:
            noticias_unicas[art['url_hash']] = art
    
    noticias_lista = list(noticias_unicas.values())
    print(f"[INFO] Noticias únicas: {len(noticias_lista)}")
    
    # Solo noticias con imagen disponible
    noticias_con_imagen = [n for n in noticias_lista if n.get('urlToImage') and n['urlToImage'].startswith('http')]
    print(f"[INFO] Noticias con imagen: {len(noticias_con_imagen)}")
    
    noticias_nuevas = [n for n in noticias_con_imagen if n['url'] not in HISTORIAL_URLS and n['url_hash'] not in HISTORIAL_HASHES]
    print(f"[INFO] Noticias no publicadas antes: {len(noticias_nuevas)}")
    
    noticias_nuevas.sort(key=lambda x: x['score'], reverse=True)
    return noticias_nuevas[:5]

def es_noticia_valida(art):
    if not art.get('title'):
        return False
    if "[Removed]" in art.get('title',
