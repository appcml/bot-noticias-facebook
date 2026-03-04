import requests
import random
import re
import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse

# --- CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ---
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    raise ValueError("Faltan variables de entorno")

FUENTES_PREMIUM = {
    'internacional': ['bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'aljazeera.com', 'elpais.com', 'clarin.com'],
    'economia': ['bloomberg.com', 'forbes.com', 'eleconomista.es', 'expansion.com', 'ambito.com'],
    'tecnologia': ['techcrunch.com', 'theverge.com', 'wired.com', 'xataka.com', 'fayerwayer.com'],
    'politica': ['politico.com', 'axios.com', 'infobae.com', 'animalpolitico.com', 'reforma.com']
}

HISTORIAL_URLS = set()
MAX_HISTORIAL = 100

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    fecha_ayer = (datetime.now().timestamp() - 86400)
    
    busquedas_todas = [
        ('guerra OR ataque OR conflicto OR misil OR bombardeo', 'crisis'),
        ('iran OR israel OR gaza OR medio oriente', 'crisis'),
        ('trump OR biden OR elecciones OR casa blanca', 'politica'),
        ('gobierno OR congreso OR senado OR ley OR votacion', 'politica'),
        ('economia OR inflacion OR dolar OR peso OR mercado', 'economia'),
        ('bolsa OR wall street OR fed OR reserva federal', 'economia'),
        ('inteligencia artificial OR chatgpt OR openai OR google', 'tech'),
        ('ciberseguridad OR hacker OR virus OR ransomware', 'tech'),
        ('terremoto OR sismo OR huracan OR inundacion', 'emergencia'),
        ('accidente OR incendio OR explosion OR emergencia', 'emergencia')
    ]
    
    busquedas_hoy = random.sample(busquedas_todas, min(5, len(busquedas_todas)))
    todas_noticias = []
    
    for query, categoria in busquedas_hoy:
        url = f"https://newsapi.org/v2/everything?q={query}&language=es&from={datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')}&to={fecha_hoy}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        
        try:
            print(f"[BÚSQUEDA] {categoria}: {query[:40]}...")
            response = requests.get(url, timeout=15)
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                for art in data['articles']:
                    if es_noticia_valida(art):
                        score = calcular_score(art, categoria)
                        art['categoria'] = categoria
                        art['score'] = score
                        art['url_hash'] = hashlib.md5(art['url'].encode()).hexdigest()[:16]
                        todas_noticias.append(art)
                        print(f"  Encontrada: {art['title'][:50]}... (score: {score})")
                        
        except Exception as e:
            print(f"[ERROR] en búsqueda {categoria}: {e}")
    
    print(f"\n[INFO] Total noticias encontradas: {len(todas_noticias)}")
    
    noticias_unicas = {}
    for art in todas_noticias:
        if art['url_hash'] not in noticias_unicas:
            noticias_unicas[art['url_hash']] = art
    
    noticias_lista = list(noticias_unicas.values())
    print(f"[INFO] Noticias únicas: {len(noticias_lista)}")
    
    noticias_nuevas = [n for n in noticias_lista if n['url'] not in HISTORIAL_URLS]
    print(f"[INFO] Noticias no publicadas antes: {len(noticias_nuevas)}")
    
    noticias_nuevas.sort(key=lambda x: x['score'], reverse=True)
    
    return noticias_nuevas[:5]

def es_noticia_valida(art):
    if not art.get('title'):
        return False
    if "[Removed]" in art.get('title', ''):
        return False
    if len(art.get('title', '')) < 20:
        return False
    
    if not art.get('description'):
        return False
    if len(art.get('description', '')) < 80:
        return False
    
    url = art.get('url', '')
    if not url or not url.startswith('http'):
        return False
    
    dominios_malos = ['news.google.com', 'google.com/news', 'facebook.com', 'twitter.com']
    if any(mal in url.lower() for mal in dominios_malos):
        return False
    
    return True

def calcular_score(art, categoria):
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    impacto_muy_alto = {
        'guerra': 30, 'ataque': 30, 'muertos': 30, 'heridos': 25,
        'trump': 25, 'biden': 25, 'elecciones': 20,
        'crisis': 20, 'urgente': 20, 'alerta': 20, 'breaking': 20,
        'invasion': 25, 'misil': 25, 'bomba': 25,
        'economia': 15, 'inflacion': 20, 'dolar': 15,
        'ia': 15, 'inteligencia artificial': 20, 'chatgpt': 15
    }
    
    for palabra, puntos in impacto_muy_alto.items():
        if palabra in texto:
            score += puntos
    
    fuente = urlparse(art.get('url', '')).netloc.lower()
    for cat, fuentes in FUENTES_PREMIUM.items():
        if any(f in fuente for f in fuentes):
            score += 20
            break
    
    try:
        fecha_pub = art.get('publishedAt', '')
        if fecha_pub:
            fecha_art = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00'))
            horas_diferencia = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            
            if horas_diferencia < 1:
                score += 30
            elif horas_diferencia < 6:
                score += 20
            elif horas_diferencia < 24:
                score += 10
    except:
        pass
    
    if categoria in ['crisis', 'emergencia']:
        score += 15
    
    return score

def detectar_tono(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    
    graves = ['muerte', 'muertos', 'ataque', 'guerra', 'tragedia', 'desastre', 'crisis', 'urgente']
    positivas = ['avance', 'descubrimiento', 'innovacion', 'acuerdo', 'paz', 'logro', 'éxito']
    neutrales = ['estudio', 'análisis', 'reporte', 'datos', 'encuesta', 'investigación']
    
    if any(p in texto for p in graves):
        return 'grave'
    elif any(p in texto for p in positivas):
        return 'positivo'
    elif any(p in texto for p in neutrales):
        return 'analitico'
    else:
        return 'neutral'

def generar_redaccion_inteligente(noticia, categoria):
    titulo = noticia['title']