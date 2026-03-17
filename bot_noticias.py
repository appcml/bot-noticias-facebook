#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V4.1 (FALLBACK ROBUSTO)
Fuentes: NewsAPI, NewsData, GNews, ApiTube, TheNewsAPI, Currents, Google News, RSS
"""

import requests
import feedparser
import re
import hashlib
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
APITUBE_API_KEY = os.getenv('APITUBE_API_KEY')
THENEWSAPI_TOKEN = os.getenv('THENEWSAPI_TOKEN')
CURRENTS_API_KEY = os.getenv('CURRENTS_API_KEY')

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')
TIEMPO_ENTRE_PUBLICACIONES = 30  # 30 minutos
UMBRAL_SIMILITUD_TITULO = 0.75
UMBRAL_SIMILITUD_CONTENIDO = 0.65
MAX_TITULOS_HISTORIA = 200
MIN_NOTICIAS_POR_FUENTE = 3  # Mínimo para considerar fuente como "funcional"

BLACKLIST_TITULOS = [r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$']
PALABRAS_ALTA_PRIORIDAD = ["guerra hoy", "conflicto armado", "dictadura", "sanciones", "ucrania", "rusia", "gaza", "israel", "hamas", "iran", "china", "taiwan", "otan", "brics", "economia mundial", "inflacion", "crisis humanitaria", "refugiados", "derechos humanos", "protestas", "coup", "minerales estrategicos", "tierras raras", "drones", "inteligencia artificial guerra", "ciberataque", "zelensky", "netanyahu", "trump", "biden", "putin", "elecciones", "fraude", "corrupcion", "crisis", "ataque", "bombardeo", "invasion"]
PALABRAS_MEDIA_PRIORIDAD = ['economía', 'mercados', 'FMI', 'China', 'EEUU', 'Alemania', 'petroleo', 'gas', 'europa', 'asia', 'latinoamerica', 'mexico', 'brasil', 'argentina']

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None: default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default.copy()
        except Exception as e:
            log(f"Error cargando JSON {ruta}: {e}", 'error')
            try:
                backup = f"{ruta}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                os.rename(ruta, backup)
                log(f"Backup creado: {backup}", 'advertencia')
            except: pass
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto: return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url_v3(url):
    if not url: return ""
    try:
        parsed = urlparse(url)
    except:
        return url.lower().strip()
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()
    netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)', '', netloc)
    path = re.sub(r'/index\.(html|php|htm|asp)$', '/', path)
    path = path.rstrip('/')
    path = re.sub(r'\.html?$', '', path)
    url_base = f"{netloc}{path}"
    query_params = []
    if parsed.query:
        params = parsed.query.split('&')
        for p in params:
            if '=' in p:
                key = p.split('=')[0].lower()
                if key in ['id', 'article', 'post', 'p', 'noticia', 'newsid', 'story']:
                    query_params.append(p.lower())
    if query_params:
        url_base += '?' + '&'.join(sorted(query_params))
    return url_base

def extraer_dominio_principal(url):
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        parts = netloc.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return netloc
    except:
        return ""

def calcular_similitud_titulos(t1, t2):
    if not t1 or not t2: return 0.0
    def n(t): 
        t = re.sub(r'[^\w\s]', '', t.lower().strip())
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'\b(el|la|los|las|un|una|en|de|del|al|y|o|que|con|por|para|sobre|entre|hacia|desde|hasta|durante|mediante|segun|según|hace|mas|más|muy|tan|tanto|como|cómo|cuando|donde|quien|cual|cuales|cuál|cuáles|esto|eso|aquello|este|ese|aquel|esta|esa|aquella|estos|esos|aquellos|estas|esas|aquellas|mi|tu|su|nuestro|vuestro|sus|mis|tus|nuestros|vuestros|me|te|se|nos|os|lo|le|les|ya|aun|aún|tambien|también|ademas|además|sin|embargo|porque|pues|asi|así|luego|entonces|aunque|a pesar|sin embargo|no obstante|the|of|and|to|in|is|that|for|it|with|as|on|be|this|was|are|at|by|from|have|has|had|not|been|or|an|but|their|more|will|would|could|should|may|might|can|shall)\b', '', t)
        return t.strip()
    return SequenceMatcher(None, n(t1), n(t2)).ratio()

def calcular_similitud_contenido(c1, c2, longitud=100):
    if not c1 or not c2: return 0.0
    def n(c):
        c = re.sub(r'[^\w\s]', '', c.lower().strip())
        c = re.sub(r'\s+', ' ', c)
        return c[:longitud]
    return SequenceMatcher(None, n(c1), n(c2)).ratio()

def es_titulo_generico(titulo):
    if not titulo: return True
    tl = titulo.lower().strip()
    for p in BLACKLIST_TITULOS:
        if re.match(p, tl): return True
    stop = {'el','la','de','y','en','the','of','to','hoy'}
    pal = [p for p in re.findall(r'\b\w+\b', tl) if p not in stop and len(p)>3]
    return len(set(pal)) < 4

def limpiar_texto(texto):
    if not texto: return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    t = t.strip()
    if t and t[-1] not in '.!?': t += '.'
    return t.strip()

def calcular_puntaje(titulo, desc):
    txt = f"{titulo} {desc}".lower()
    p = 0
    for f in PALABRAS_ALTA_PRIORIDAD:
        pal = f.lower().split()
        for pa in pal:
            if len(pa) >= 4 and pa in txt:
                p += 3
                break
        if f.lower() in txt: p += 7
    for f in PALABRAS_MEDIA_PRIORIDAD:
        for pa in f.lower().split():
            if len(pa) >= 3 and pa in txt:
                p += 1
                break
    if 30 <= len(titulo) <= 150: p += 2
    if len(desc) >= 50: p += 2
    return p

def extraer_contenido(url):
    if not url: return None, None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        for e in s(['script','style','nav','header','footer']): e.decompose()
        art = s.find('article')
        if art:
            ps = art.find_all('p')
            if len(ps) >= 3:
                txt = ' '.join([limpiar_texto(p.get_text()) for p in ps if len(p.get_text()) > 40])
                if len(txt) > 300: return txt[:2000], None
        for c in ['article-content','entry-content','post-content']:
            e = s.find(class_=lambda x: x and c in x.lower())
            if e:
                ps = e.find_all('p')
                if len(ps) >= 2:
                    txt = ' '.join([limpiar_texto(p.get_text()) for p in ps if len(p.get_text()) > 40])
                    if len(txt) > 300: return txt[:2000], None
        return None, None
    except: return None, None

def dividir_parrafos(texto):
    if not texto: return []
    ors = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    if len(ors) < 3: return [texto] if len(texto) > 100 else []
    pars, actual, palabras = [], [], 0
    for i, o in enumerate(ors):
        actual.append(o)
        palabras += len(o.split())
        if palabras >= 40 or i == len(ors)-1:
            if len(' '.join(actual).split()) >= 15:
                pars.append(' '.join(actual))
            actual, palabras = [], 0
    return pars[:8]

def construir_publicacion(titulo, contenido, creditos, fuente):
    t = limpiar_texto(titulo)
    pars = dividir_parrafos(contenido)
    if len(pars) < 2:
        ors = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        pars = [' '.join(ors[i:i+2]) for i in range(0, len(ors), 2)][:8]
    lineas = [f"📰 ÚLTIMA HORA | {t}", ""]
    for i, p in enumerate(pars):
        lineas.append(p)
        if i < len(pars)-1: lineas.append("")
    lineas.extend(["", "──────────────────────────────", ""])
    if creditos: lineas.extend([f"✍️ {creditos}", ""])
    lineas.append(f"📎 {fuente}")
    return '\n'.join(lineas)

def cargar_historial():
    d = {
        'urls': [], 'urls_normalizadas': [], 'hashes': [], 'timestamps': [], 
        'titulos': [], 'descripciones': [], 'hashes_contenido': [], 
        'hashes_permanentes': [], 'estadisticas': {'total_publicadas': 0}
    }
    h = cargar_json(HISTORIAL_PATH, d)
    for k in d: 
        if k not in h: h[k] = d[k]
    limpiar_historial_antiguo(h)
    return h

def limpiar_historial_antiguo(h):
    try:
        ahora = datetime.now()
        indices_a_mantener = []
        for i, ts in enumerate(h.get('timestamps', [])):
            try:
                fecha = datetime.fromisoformat(ts)
                if (ahora - fecha).days < 7:
                    indices_a_mantener.append(i)
            except: continue
        for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps', 'titulos', 'descripciones', 'hashes_contenido']:
            if key in h and isinstance(h[key], list):
                h[key] = [h[key][i] for i in indices_a_mantener if i < len(h[key])]
        if len(h.get('hashes_permanentes', [])) > 100:
            h['hashes_permanentes'] = h['hashes_permanentes'][-100:]
    except Exception as e:
        log(f"Error limpiando historial: {e}", 'error')

def noticia_ya_publicada(h, url, titulo, desc=""):
    if not h: return False, "sin_historial"
    url_n = normalizar_url_v3(url)
    hash_t = generar_hash(titulo)
    hash_d = generar_hash(desc) if desc else ""
    dominio = extraer_dominio_principal(url)
    
    log(f"   🔍 Verificando duplicados:", 'debug')
    log(f"      URL norm: {url_n[:80]}...", 'debug')
    
    if es_titulo_generico(titulo): 
        return True, "titulo_generico"
    
    for uh in h.get('urls_normalizadas', []):
        if isinstance(uh, str) and url_n == uh: 
            return True, "url_normalizada_exacta"
    
    for i, uh in enumerate(h.get('urls', [])):
        if not isinstance(uh, str): continue
        if extraer_dominio_principal(uh) == dominio:
            titulo_h = h.get('titulos', [])[i] if i < len(h.get('titulos', [])) else ""
            if titulo_h and calcular_similitud_titulos(titulo, titulo_h) >= 0.85:
                return True, f"misma_noticia_sitio"
    
    todos_h = list(dict.fromkeys(h.get('hashes', []) + h.get('hashes_permanentes', [])))
    if hash_t in todos_h: 
        return True, "hash_titulo_exacto"
    
    if hash_d and hash_d in h.get('hashes_contenido', []):
        return True, "hash_contenido_exacto"
    
    for th in h.get('titulos', []):
        if not isinstance(th, str): continue
        if calcular_similitud_titulos(titulo, th) >= UMBRAL_SIMILITUD_TITULO: 
            return True, f"similitud_titulo"
    
    if desc:
        for dh in h.get('descripciones', []):
            if not isinstance(dh, str) or not dh: continue
            if calcular_similitud_contenido(desc, dh, 150) >= UMBRAL_SIMILITUD_CONTENIDO:
                return True, f"similitud_contenido"
    
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc=""):
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido','hashes_permanentes','estadisticas']:
        if k not in h: h[k] = [] if k != 'estadisticas' else {'total_publicadas': 0}
    
    url_n = normalizar_url_v3(url)
    hash_t = generar_hash(titulo)
    
    for uh in h.get('urls_normalizadas', []):
        if isinstance(uh, str) and uh == url_n:
            log(f"⚠️ Intento de duplicado detectado en guardar_historial", 'advertencia')
            return h
    
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1
    h['hashes_permanentes'].append(hash_t)
    
    if len(h['hashes_permanentes']) > 300: 
        h['hashes_permanentes'] = h['hashes_permanentes'][-300:]
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA: 
            h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    
    guardar_json(HISTORIAL_PATH, h)
    return h

def verificar_tiempo():
    e = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u: return True
    try:
        m = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if m < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {m:.0f} min (objetivo: {TIEMPO_ENTRE_PUBLICACIONES} min)", 'info')
            return False
    except: pass
    return True

# ============================================================================
# TODAS LAS FUENTES DE NOTICIAS (7 APIs + RSS)
# ============================================================================

def obtener_newsapi():
    if not NEWS_API_KEY: 
        log("NewsAPI: No API key configurada", 'debug')
        return []
    n = []
    queries = [
        'Ukraine war Russia', 'Israel Gaza conflict', 'China Taiwan',
        'economy inflation', 'NATO Europe', 'cyberattack', 'coup'
    ]
    for q in queries[:3]:  # Limitar para no exceder rate limits
        try:
            r = requests.get('https://newsapi.org/v2/everything', 
                           params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es', 
                                  'sortBy': 'publishedAt', 'pageSize': 5}, 
                           timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'ok':
                    for a in data.get('articles', []):
                        t = a.get('title', '')
                        if t and '[Removed]' not in t:
                            d = a.get('description', '')
                            n.append({
                                'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 
                                'url': a.get('url', ''), 'imagen': a.get('urlToImage'), 
                                'fuente': f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}", 
                                'fecha': a.get('publishedAt'), 'puntaje': calcular_puntaje(t, d)
                            })
            else:
                log(f"NewsAPI error {r.status_code}", 'error')
        except Exception as e:
            log(f"NewsAPI excepción: {e}", 'error')
    log(f"NewsAPI.org: {len(n)} noticias", 'info')
    return n

def obtener_newsdata():
    if not NEWSDATA_API_KEY: 
        log("NewsData: No API key configurada", 'debug')
        return []
    n = []
    categorias = ['world', 'politics', 'business']
    for cat in categorias:
        try:
            r = requests.get('https://newsdata.io/api/1/news', 
                            params={'apikey': NEWSDATA_API_KEY, 'language': 'es', 
                                   'category': cat, 'size': 10}, 
                            timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'success':
                    for a in data.get('results', []):
                        t = a.get('title', '')
                        if t:
                            d = a.get('description', '')
                            n.append({
                                'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 
                                'url': a.get('link', ''), 'imagen': a.get('image_url'), 
                                'fuente': f"NewsData:{a.get('source_id', 'Unknown')}", 
                                'fecha': a.get('pubDate'), 'puntaje': calcular_puntaje(t, d)
                            })
            else:
                log(f"NewsData error {r.status_code}", 'error')
        except Exception as e:
            log(f"NewsData excepción: {e}", 'error')
    log(f"NewsData.io: {len(n)} noticias", 'info')
    return n

def obtener_gnews():
    if not GNEWS_API_KEY: 
        log("GNews: No API key configurada", 'debug')
        return []
    n = []
    topicos = ['world', 'nation', 'business']
    for topic in topicos:
        try:
            r = requests.get('https://gnews.io/api/v4/top-headlines', 
                            params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 10, 'topic': topic}, 
                            timeout=15)
            if r.status_code == 200:
                data = r.json()
                for a in data.get('articles', []):
                    t = a.get('title', '')
                    if t:
                        d = a.get('description', '')
                        n.append({
                            'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 
                            'url': a.get('url', ''), 'imagen': a.get('image'), 
                            'fuente': f"GNews:{a.get('source', {}).get('name', 'Unknown')}", 
                            'fecha': a.get('publishedAt'), 'puntaje': calcular_puntaje(t, d)
                        })
            else:
                log(f"GNews error {r.status_code}", 'error')
        except Exception as e:
            log(f"GNews excepción: {e}", 'error')
    log(f"GNews.io: {len(n)} noticias", 'info')
    return n

def obtener_apitube():
    if not APITUBE_API_KEY: 
        log("ApiTube: No API key configurada", 'debug')
        return []
    n = []
    try:
        headers = {'X-API-Key': APITUBE_API_KEY}
        params = {'language.code': 'es', 'per_page': 20}
        r = requests.get('https://api.apitube.io/v1/news/everything', 
                        headers=headers, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            for item in data.get('data', []):
                t = item.get('title', '')
                if not t or '[Removed]' in t: continue
                d = item.get('description', '') or item.get('summary', {}).get('sentence', '')
                url = item.get('url', '')
                if 'apitube.io' in url:
                    url = item.get('source', {}).get('url', url)
                n.append({
                    'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d),
                    'url': url, 'imagen': item.get('image', None),
                    'fuente': f"ApiTube:{item.get('source', {}).get('domain', 'Unknown')}",
                    'fecha': item.get('published_at', ''),
                    'puntaje': calcular_puntaje(t, d)
                })
        else:
            log(f"ApiTube error {r.status_code}: {r.text[:100]}", 'error')
    except Exception as e:
        log(f"ApiTube excepción: {e}", 'error')
    log(f"ApiTube.io: {len(n)} noticias", 'info')
    return n

def obtener_thenewsapi():
    if not THENEWSAPI_TOKEN: 
        log("TheNewsAPI: No API key configurada", 'debug')
        return []
    n = []
    endpoints = [
        ('https://api.thenewsapi.com/v1/news/top', {'locale': 'us,es,latam', 'language': 'es', 'limit': 15}),
        ('https://api.thenewsapi.com/v1/news/all', {'language': 'es', 'limit': 10}),
    ]
    for url, params in endpoints:
        try:
            params['api_token'] = THENEWSAPI_TOKEN
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                for item in data.get('data', []):
                    t = item.get('title', '')
                    if not t: continue
                    d = item.get('description', '') or item.get('snippet', '')
                    n.append({
                        'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d),
                        'url': item.get('url', ''), 'imagen': item.get('image_url', None),
                        'fuente': f"TheNewsAPI:{item.get('source', 'Unknown')}",
                        'fecha': item.get('published_at', ''),
                        'puntaje': calcular_puntaje(t, d)
                    })
            else:
                log(f"TheNewsAPI error {r.status_code}: {r.text[:100]}", 'error')
        except Exception as e:
            log(f"TheNewsAPI excepción: {e}", 'error')
    log(f"TheNewsAPI.com: {len(n)} noticias", 'info')
    return n

def obtener_currents():
    if not CURRENTS_API_KEY: 
        log("Currents: No API key configurada", 'debug')
        return []
    n = []
    try:
        headers = {'Authorization': CURRENTS_API_KEY}
        r = requests.get('https://api.currentsapi.services/v1/latest-news',
                        headers=headers, params={'language': 'es'}, timeout=20)
        if r.status_code == 200:
            data = r.json()
            for item in data.get('news', []):
                t = item.get('title', '')
                if not t: continue
                d = item.get('description', '')
                n.append({
                    'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d),
                    'url': item.get('url', ''), 'imagen': item.get('image', None),
                    'fuente': f"Currents:{item.get('author', item.get('source', 'Unknown'))}",
                    'fecha': item.get('published', ''),
                    'puntaje': calcular_puntaje(t, d)
                })
        else:
            log(f"Currents error {r.status_code}: {r.text[:100]}", 'error')
    except Exception as e:
        log(f"Currents excepción: {e}", 'error')
    log(f"CurrentsAPI: {len(n)} noticias", 'info')
    return n

def resolver_redireccion_google(url):
    if not url or not url.startswith('https://news.google.com'): return url
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
        u = r.url
        if 'google.com' in u and '/sorry' in u: return None
        if u == url:
            u = requests.head(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True).url
        return re.sub(r'\?.*$', '', re.sub(r'#.*$', '', u))
    except: return None

def obtener_google_news():
    feeds = [
        'https://news.google.com/rss?hl=es&gl=US&ceid=US:es', 
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNRE55YXpBU0JXVnVMVWRDS0FBUAE?hl=es&gl=US&ceid=US:es',
    ]
    n = []
    for f in feeds:
        try:
            feed = feedparser.parse(f, request_headers={'User-Agent': 'Mozilla/5.0'})
            if not feed or not feed.entries: continue
            for e in feed.entries[:10]:
                t = e.get('title', '')
                if not t or '[Removed]' in t: continue
                if ' - ' in t: t = t.rsplit(' - ', 1)[0]
                l = e.get('link', '')
                u = resolver_redireccion_google(l)
                if not u: continue
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                n.append({
                    'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 
                    'url': u, 'imagen': None, 'fuente': 'Google News', 
                    'fecha': e.get('published'), 'puntaje': calcular_puntaje(t, d)
                })
        except: continue
    log(f"Google News: {len(n)} noticias", 'info')
    return n

def obtener_rss_alternativos():
    feeds = [
        'http://feeds.bbci.co.uk/mundo/rss.xml', 
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
        'https://www.infobae.com/arc/outboundfeeds/rss/mundo/',
        'https://feeds.reuters.com/reuters/hotnews',
    ]
    n = []
    for f in feeds:
        try:
            r = requests.get(f, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200: continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries: continue
            fn = feed.feed.get('title', 'RSS')[:20]
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t: continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l: continue
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                img = None
                if 'media_content' in e: img = e.media_content[0].get('url')
                elif 'links' in e:
                    for ld in e.links:
                        if ld.get('type', '').startswith('image/'): 
                            img = ld.get('href')
                            break
                n.append({
                    'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 
                    'url': l, 'imagen': img, 'fuente': f"RSS:{fn}", 
                    'fecha': e.get('published'), 'puntaje': calcular_puntaje(t, d)
                })
        except: continue
    log(f"RSS Alternativos: {len(n)} noticias", 'info')
    return n

# ============================================================================
# PROCESAMIENTO DE IMÁGENES Y PUBLICACIÓN
# ============================================================================

def extraer_imagen_web(url):
    if not url: return None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for m in ['og:image', 'twitter:image']:
            t = s.find('meta', property=m) or s.find('meta', attrs={'name': m})
            if t:
                i = t.get('content', '').strip()
                if i and i.startswith('http') and 'google' not in i.lower(): return i
        art = s.find('article') or s.find('main')
        if art:
            for img in art.find_all('img'):
                src = img.get('data-src') or img.get('src', '')
                if src and src.startswith('http') and 'google' not in src.lower() and 'logo' not in src.lower():
                    return src
        return None
    except: return None

def descargar_imagen(url):
    if not url: return None
    for b in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon', 'favicon']:
        if b in url.lower(): return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200: return None
        if 'image' not in r.headers.get('content-type', ''): return None
        img = Image.open(BytesIO(r.content))
        w, h = img.size
        if w < 400 or h < 300: return None
        if w/h > 4 or w/h < 0.2: return None
        if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
        img.thumbnail((1200, 1200))
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=85)
        if os.path.getsize(p) < 5000:
            os.remove(p)
            return None
        return p
    except: return None

def crear_imagen_titulo(titulo):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        img = Image.new('RGB', (1200, 630), color='#0f172a')
        draw = ImageDraw.Draw(img)
        try:
            fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            fb = fs = ImageFont.load_default()
        draw.rectangle([(0, 0), (1200, 8)], fill='#3b82f6')
        tt = textwrap.fill(titulo[:140], width=36)
        ls = tt.split('\n')
        y = (630 - len(ls)*50) // 2 - 50
        draw.text((60, y), tt, font=fb, fill='white')
        draw.text((60, 550), "🌍 Noticias Internacionales", font=fs, fill='#94a3b8')
        draw.text((60, 580), "Verdad Hoy • Agencia de Noticias", font=fs, fill='#64748b')
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img.save(p, 'JPEG', quality=90)
        return p
    except: return None

def generar_hashtags(t, c):
    txt = f"{t} {c}".lower()
    h = ['#NoticiasInternacionales', '#ÚltimaHora']
    temas = {
        'guerra|conflicto|ataque': '#ConflictoArmado', 
        'ucrania|rusia|putin': '#UcraniaRusia', 
        'gaza|israel|hamas': '#IsraelGaza', 
        'trump|biden': '#PolíticaGlobal', 
        'economía|inflación': '#EconomíaMundial', 
        'china|taiwan': '#ChinaTaiwán'
    }
    for p, tag in temas.items():
        if re.search(p, txt): 
            h.append(tag)
            break
    h.append('#Mundo')
    return ' '.join(h)

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN: return False
    m = f"{texto}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    if len(m) > 2000:
        l = texto.split('\n')
        tc = ""
        for ln in l:
            if len(tc + ln + "\n") < 1600: tc += ln + "\n"
            else: break
        m = f"{tc.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    m = re.sub(r'https?://\S+', '', m)
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            r = requests.post(url, files={'file': ('imagen.jpg', f, 'image/jpeg')}, 
                            data={'message': m, 'access_token': FB_ACCESS_TOKEN}, 
                            timeout=60).json()
        if 'id' in r:
            log(f"✅ Publicado ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook: {r.get('error', {}).get('message', 'Unknown')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando: {e}", 'error')
    return False

# ============================================================================
# FUNCIÓN PRINCIPAL CON FALLBACK ROBUSTO
# ============================================================================

def recolectar_noticias_todas_fuentes():
    """
    Intenta TODAS las fuentes siempre, sin importar cuántas noticias tenga.
    Esto garantiza máxima cobertura y redundancia.
    """
    todas_noticias = []
    estadisticas_fuentes = {}
    
    # Lista de todas las fuentes disponibles
    fuentes = [
        ('NewsAPI', obtener_newsapi, NEWS_API_KEY),
        ('NewsData', obtener_newsdata, NEWSDATA_API_KEY),
        ('GNews', obtener_gnews, GNEWS_API_KEY),
        ('ApiTube', obtener_apitube, APITUBE_API_KEY),
        ('TheNewsAPI', obtener_thenewsapi, THENEWSAPI_TOKEN),
        ('Currents', obtener_currents, CURRENTS_API_KEY),
        ('Google News', obtener_google_news, True),  # No requiere API key
        ('RSS Alternativos', obtener_rss_alternativos, True),  # No requiere API key
    ]
    
    for nombre, funcion, tiene_credencial in fuentes:
        if not tiene_credencial:
            estadisticas_fuentes[nombre] = 0
            continue
            
        try:
            noticias = funcion()
            count = len(noticias)
            estadisticas_fuentes[nombre] = count
            if count > 0:
                todas_noticias.extend(noticias)
                log(f"✅ {nombre}: {count} noticias añadidas", 'exito')
            else:
                log(f"⚠️ {nombre}: Sin noticias", 'advertencia')
        except Exception as e:
            log(f"❌ {nombre}: Error - {e}", 'error')
            estadisticas_fuentes[nombre] = 0
    
    # Log resumen
    log(f"\n📊 RESUMEN FUENTES:", 'info')
    for fuente, count in estadisticas_fuentes.items():
        status = "✅" if count > 0 else "❌"
        log(f"   {status} {fuente}: {count} noticias", 'info')
    log(f"📰 TOTAL: {len(todas_noticias)} noticias de todas las fuentes\n", 'info')
    
    return todas_noticias

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V4.1 (FALLBACK ROBUSTO - 8 FUENTES)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    h = cargar_historial()
    log(f"📊 Historial: {len(h.get('urls', []))} URLs previas")
    
    # NUEVO: Recolectar de TODAS las fuentes siempre
    n = recolectar_noticias_todas_fuentes()
    
    if not n:
        log("ERROR CRÍTICO: Ninguna fuente devolvió noticias", 'error')
        return False
    
    # Deduplicación
    urls_vistas = set()
    titulos_vistos = {}
    n_unicas = []
    
    for nt in n:
        url_n = normalizar_url_v3(nt.get('url', ''))
        if url_n in urls_vistas:
            continue
            
        duplicado_temp = False
        for t_existente in titulos_vistos.keys():
            if calcular_similitud_titulos(nt.get('titulo', ''), t_existente) > 0.8:
                duplicado_temp = True
                break
        
        if duplicado_temp:
            continue
            
        urls_vistas.add(url_n)
        titulos_vistos[nt.get('titulo', '')] = url_n
        n_unicas.append(nt)
    
    n = n_unicas
    log(f"📰 Únicas tras deduplicación: {len(n)} noticias")
    
    # Ordenar por puntaje
    n.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    
    # Buscar noticia válida
    sel = None
    cont = None
    cred = None
    
    for i, nt in enumerate(n[:50]):  # Revisar top 50
        url = nt.get('url', '')
        t = nt.get('titulo', '')
        d = nt.get('descripcion', '')
        
        if not url or not t: 
            continue
        
        dup, rz = noticia_ya_publicada(h, url, t, d)
        if dup:
            log(f"   [{i+1}] ❌ Duplicada: {t[:50]}... ({rz})", 'debug')
            continue
        
        log(f"   [{i+1}] ✅ Candidata: {t[:50]}... (Puntaje: {nt.get('puntaje', 0)})")
        
        cont, cred = extraer_contenido(url)
        
        if cont and len(cont) >= 150:
            sel = nt
            break
        elif d and len(d) >= 100:
            cont = d
            sel = nt
            break
    
    if not sel:
        log("ERROR: No hay noticias válidas nuevas", 'error')
        return False
    
    # Construir y publicar
    pub = construir_publicacion(sel['titulo'], cont, cred, sel['fuente'])
    ht = generar_hashtags(sel['titulo'], cont)
    
    log("🖼️  Procesando imagen...")
    img_path = None
    
    if sel.get('imagen') and 'Google' not in sel.get('fuente', ''):
        img_path = descargar_imagen(sel['imagen'])
    
    if not img_path:
        iu = extraer_imagen_web(sel['url'])
        if iu: 
            img_path = descargar_imagen(iu)
    
    if not img_path:
        img_path = crear_imagen_titulo(sel['titulo'])
    
    if not img_path:
        log("ERROR: Sin imagen", 'error')
        return False
    
    ok = publicar_facebook(sel['titulo'], pub, img_path, ht)
    
    try:
        if os.path.exists(img_path): 
            os.remove(img_path)
    except: 
        pass
    
    if ok:
        h = guardar_historial(h, sel['url'], sel['titulo'], sel.get('descripcion', '') + ' ' + cont[:400])
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log(f"✅ ÉXITO - Total histórico: {h.get('estadisticas', {}).get('total_publicadas', 0)} noticias", 'exito')
        return True
    else:
        log("❌ Publicación fallida", 'error')
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
