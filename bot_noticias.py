#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V4.0
CORRECCIÓN CRÍTICA: Historial persistente + fix syntax errors
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
from urllib.parse import urlparse

# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────
NEWS_API_KEY       = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY   = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY      = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID         = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN    = os.getenv('FB_ACCESS_TOKEN')

# RUTAS — en la raíz del repo para que git las encuentre fácil
HISTORIAL_PATH     = os.getenv('HISTORIAL_PATH', 'historial_publicaciones.json')
ESTADO_PATH        = os.getenv('ESTADO_PATH',    'estado_bot.json')

TIEMPO_ENTRE_PUBLICACIONES = 55   # minutos (un poco menos que 1h para dar margen)
UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 300  # aumentado para mejor cobertura
DIAS_HISTORIAL             = 14   # guardar 2 semanas

BLACKLIST_TITULOS = [
    r'^\s*última hora\s*$',
    r'^\s*breaking news\s*$',
    r'^\s*noticias de hoy\s*$',
    r'^\s*\d+\s*$',
]

PALABRAS_ALTA_PRIORIDAD = [
    "guerra", "conflicto armado", "invasion", "ofensiva militar", "bombardeo",
    "misiles", "ataque aereo", "drones militares", "movilizacion militar",
    "tropas", "escalada de tension", "amenaza nuclear", "armas nucleares",
    "terrorismo", "atentado", "ataque terrorista",
    "ucrania", "rusia", "israel", "gaza", "iran", "china", "taiwan",
    "corea del norte", "otan", "nato", "brics", "medio oriente",
    "siria", "yemen", "sudan",
    "crisis humanitaria", "refugiados",
    "crisis de gobierno", "golpe de estado", "coup", "estado de emergencia",
    "negociaciones de paz", "alto el fuego", "sanciones internacionales",
    "economia mundial", "inflacion", "crisis economica", "recesion",
    "petroleo", "gas", "crisis energetica",
    "ciberataque", "hackeo", "inteligencia artificial",
    "ultima hora", "urgente", "breaking",
    "putin", "zelensky", "trump", "biden", "netanyahu", "khamenei",
    "xi jinping", "kim jong un", "macron", "scholz",
    "hamas", "hezbollah", "isis", "estado islamico", "taliban", "houthis",
    "elon musk",
]

PALABRAS_MEDIA_PRIORIDAD = [
    "economia", "mercados", "FMI", "banco mundial",
    "tecnologia", "innovacion", "salud", "educacion",
    "medio ambiente", "cambio climatico",
    "comercio internacional", "empresas",
]

# ──────────────────────────────────────────────────────────
# UTILIDADES BÁSICAS
# ──────────────────────────────────────────────────────────
def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
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
            except:
                pass
    return default.copy()

def guardar_json(ruta, datos):
    try:
        directorio = os.path.dirname(ruta)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON {ruta}: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto:
        return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url(url):
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)', '', parsed.netloc.lower())
        path   = parsed.path.lower().rstrip('/')
        path   = re.sub(r'/index\.(html|php|htm|asp)$', '', path)
        path   = re.sub(r'\.html?$', '', path)
        return f"{netloc}{path}"
    except:
        return url.lower().strip()

def extraer_dominio(url):
    try:
        parts = urlparse(url).netloc.lower().split('.')
        return '.'.join(parts[-2:]) if len(parts) > 2 else '.'.join(parts)
    except:
        return ""

def similitud_titulos(t1, t2):
    if not t1 or not t2:
        return 0.0
    stopwords = {'el','la','los','las','un','una','en','de','del','al','y','o',
                 'que','con','por','para','sobre','entre','the','of','and','to',
                 'in','is','a','an','it','as','at','by','from','not','or'}
    def normalizar(t):
        t = re.sub(r'[^\w\s]', '', t.lower().strip())
        t = re.sub(r'\s+', ' ', t)
        palabras = [p for p in t.split() if p not in stopwords and len(p) > 3]
        return ' '.join(palabras)
    return SequenceMatcher(None, normalizar(t1), normalizar(t2)).ratio()

def similitud_contenido(c1, c2, longitud=120):
    if not c1 or not c2:
        return 0.0
    def n(c):
        c = re.sub(r'[^\w\s]', '', c.lower().strip())
        return re.sub(r'\s+', ' ', c)[:longitud]
    return SequenceMatcher(None, n(c1), n(c2)).ratio()

def es_titulo_generico(titulo):
    if not titulo:
        return True
    tl = titulo.lower().strip()
    for patron in BLACKLIST_TITULOS:
        if re.match(patron, tl):
            return True
    stop = {'el','la','de','y','en','the','of','to','hoy','los','las'}
    palabras = [p for p in re.findall(r'\b\w+\b', tl) if p not in stop and len(p) > 3]
    return len(set(palabras)) < 4

def limpiar_texto(texto):
    if not texto:
        return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    t = t.strip()
    if t and t[-1] not in '.!?':
        t += '.'
    return t.strip()

def calcular_puntaje(titulo, desc):
    txt = f"{titulo} {desc}".lower()
    p = 0
    for frase in PALABRAS_ALTA_PRIORIDAD:
        if frase.lower() in txt:
            p += 7
        else:
            for palabra in frase.lower().split():
                if len(palabra) >= 4 and palabra in txt:
                    p += 3
                    break
    for frase in PALABRAS_MEDIA_PRIORIDAD:
        for palabra in frase.lower().split():
            if len(palabra) >= 3 and palabra in txt:
                p += 1
                break
    if 30 <= len(titulo) <= 150:
        p += 2
    if len(desc) >= 50:
        p += 2
    return p

# ──────────────────────────────────────────────────────────
# HISTORIAL — LÓGICA ANTI-DUPLICADOS
# ──────────────────────────────────────────────────────────
HISTORIAL_DEFAULT = {
    'urls': [],
    'urls_normalizadas': [],
    'hashes': [],
    'timestamps': [],
    'titulos': [],
    'descripciones': [],
    'hashes_contenido': [],
    'hashes_permanentes': [],
    'estadisticas': {'total_publicadas': 0}
}

def cargar_historial():
    h = cargar_json(HISTORIAL_PATH, HISTORIAL_DEFAULT)
    for k, v in HISTORIAL_DEFAULT.items():
        if k not in h:
            h[k] = v if not isinstance(v, dict) else v.copy()
    _limpiar_historial_antiguo(h)
    return h

def _limpiar_historial_antiguo(h):
    ahora = datetime.now()
    indices_validos = []
    for i, ts in enumerate(h.get('timestamps', [])):
        try:
            if (ahora - datetime.fromisoformat(ts)).days < DIAS_HISTORIAL:
                indices_validos.append(i)
        except:
            continue

    claves_con_indice = ['urls', 'urls_normalizadas', 'hashes', 'timestamps',
                         'titulos', 'descripciones', 'hashes_contenido']
    for key in claves_con_indice:
        if key in h and isinstance(h[key], list):
            h[key] = [h[key][i] for i in indices_validos if i < len(h[key])]

    # Limitar hashes permanentes
    if len(h.get('hashes_permanentes', [])) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]

def noticia_ya_publicada(h, url, titulo, desc=""):
    """
    Devuelve (True, razon) si la noticia ya fue publicada, (False, "nuevo") si es nueva.
    """
    if es_titulo_generico(titulo):
        return True, "titulo_generico"

    url_n   = normalizar_url(url)
    hash_t  = generar_hash(titulo)
    hash_d  = generar_hash(desc) if desc else ""
    dominio = extraer_dominio(url)

    # 1. URL normalizada exacta
    if url_n in h.get('urls_normalizadas', []):
        log(f"   ❌ URL duplicada: {url_n[:60]}", 'debug')
        return True, "url_duplicada"

    # 2. Hash de título exacto (incluye permanentes)
    todos_hashes = set(h.get('hashes', [])) | set(h.get('hashes_permanentes', []))
    if hash_t in todos_hashes:
        log(f"   ❌ Hash título duplicado", 'debug')
        return True, "hash_titulo"

    # 3. Hash de descripción
    if hash_d and hash_d in h.get('hashes_contenido', []):
        log(f"   ❌ Hash contenido duplicado", 'debug')
        return True, "hash_contenido"

    # 4. Similitud de títulos (global)
    for th in h.get('titulos', []):
        if not isinstance(th, str):
            continue
        sim = similitud_titulos(titulo, th)
        if sim >= UMBRAL_SIMILITUD_TITULO:
            log(f"   ❌ Título similar ({sim:.1%}): {th[:50]}", 'debug')
            return True, f"titulo_similar_{sim:.2f}"

    # 5. Mismo dominio + título muy parecido
    for i, uh in enumerate(h.get('urls', [])):
        if extraer_dominio(uh) == dominio and i < len(h.get('titulos', [])):
            sim = similitud_titulos(titulo, h['titulos'][i])
            if sim >= 0.82:
                log(f"   ❌ Misma noticia en {dominio} ({sim:.1%})", 'debug')
                return True, f"mismo_sitio_{sim:.2f}"

    # 6. Similitud de descripción
    if desc:
        for dh in h.get('descripciones', []):
            if isinstance(dh, str) and dh:
                if similitud_contenido(desc, dh, 150) >= UMBRAL_SIMILITUD_CONTENIDO:
                    log(f"   ❌ Descripción similar", 'debug')
                    return True, "descripcion_similar"

    return False, "nuevo"

def guardar_en_historial(h, url, titulo, desc=""):
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)

    # Doble check antes de guardar
    if url_n in h.get('urls_normalizadas', []):
        log("⚠️ Intento de duplicado en guardar_en_historial", 'advertencia')
        return h

    h['urls'].append(url)
    h['urls_normalizadas'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['hashes_permanentes'].append(hash_t)
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1

    # Recortar listas largas
    for k in ['urls', 'urls_normalizadas', 'hashes', 'timestamps',
              'titulos', 'descripciones', 'hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA:
            h[k] = h[k][-MAX_TITULOS_HISTORIA:]

    if len(h['hashes_permanentes']) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]

    if guardar_json(HISTORIAL_PATH, h):
        log(f"💾 Historial guardado: {len(h['urls'])} entradas", 'exito')
    else:
        log("❌ Error guardando historial", 'error')

    return h

# ──────────────────────────────────────────────────────────
# CONTROL DE TIEMPO
# ──────────────────────────────────────────────────────────
def verificar_tiempo():
    e = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u:
        return True
    try:
        minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Publicado hace {minutos:.0f} min — mínimo {TIEMPO_ENTRE_PUBLICACIONES} min", 'info')
            return False
    except:
        pass
    return True

def guardar_estado():
    guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})

# ──────────────────────────────────────────────────────────
# FUENTES DE NOTICIAS
# ──────────────────────────────────────────────────────────
def obtener_newsapi():
    if not NEWS_API_KEY:
        return []
    queries = [
        'Ukraine war Russia Putin Zelensky',
        'Israel Gaza Hamas Iran conflict',
        'China Taiwan US tensions',
        'Trump Biden US politics',
        'economy inflation recession',
        'NATO EU Europe summit',
        'cyberattack hacking security',
        'coup dictatorship sanctions',
        'climate change disaster',
        'India Pakistan Asia conflict',
    ]
    noticias = []
    for q in queries:
        try:
            r = requests.get(
                'https://newsapi.org/v2/everything',
                params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es',
                        'sortBy': 'publishedAt', 'pageSize': 5},
                timeout=15
            ).json()
            if r.get('status') == 'ok':
                for a in r.get('articles', []):
                    t = a.get('title', '')
                    if t and '[Removed]' not in t:
                        d = a.get('description', '')
                        noticias.append({
                            'titulo':      limpiar_texto(t),
                            'descripcion': limpiar_texto(d),
                            'url':         a.get('url', ''),
                            'imagen':      a.get('urlToImage'),
                            'fuente':      f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}",
                            'fecha':       a.get('publishedAt'),
                            'puntaje':     calcular_puntaje(t, d),
                        })
        except Exception as e:
            log(f"NewsAPI error ({q[:20]}): {e}", 'advertencia')
            continue
    log(f"NewsAPI: {len(noticias)} noticias", 'info')
    return noticias

def obtener_newsdata():
    if not NEWSDATA_API_KEY:
        return []
    categorias = ['world', 'politics', 'business', 'technology']
    noticias = []
    for cat in categorias:
        try:
            r = requests.get(
                'https://newsdata.io/api/1/news',
                params={'apikey': NEWSDATA_API_KEY, 'language': 'es',
                        'category': cat, 'size': 10},
                timeout=15
            ).json()
            if r.get('status') == 'success':
                for a in r.get('results', []):
                    t = a.get('title', '')
                    if t:
                        d = a.get('description', '')
                        noticias.append({
                            'titulo':      limpiar_texto(t),
                            'descripcion': limpiar_texto(d),
                            'url':         a.get('link', ''),
                            'imagen':      a.get('image_url'),
                            'fuente':      f"NewsData:{a.get('source_id', 'Unknown')}",
                            'fecha':       a.get('pubDate'),
                            'puntaje':     calcular_puntaje(t, d),
                        })
        except Exception as e:
            log(f"NewsData error ({cat}): {e}", 'advertencia')
            continue
    log(f"NewsData: {len(noticias)} noticias", 'info')
    return noticias

def obtener_gnews():
    if not GNEWS_API_KEY:
        return []
    topicos = ['world', 'nation', 'business', 'technology']
    noticias = []
    for topic in topicos:
        try:
            r = requests.get(
                'https://gnews.io/api/v4/top-headlines',
                params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 10, 'topic': topic},
                timeout=15
            ).json()
            for a in r.get('articles', []):
                t = a.get('title', '')
                if t:
                    d = a.get('description', '')
                    noticias.append({
                        'titulo':      limpiar_texto(t),
                        'descripcion': limpiar_texto(d),
                        'url':         a.get('url', ''),
                        'imagen':      a.get('image'),
                        'fuente':      f"GNews:{a.get('source', {}).get('name', 'Unknown')}",
                        'fecha':       a.get('publishedAt'),
                        'puntaje':     calcular_puntaje(t, d),
                    })
        except Exception as e:
            log(f"GNews error ({topic}): {e}", 'advertencia')
            continue
    log(f"GNews: {len(noticias)} noticias", 'info')
    return noticias

def obtener_rss():
    fuentes = [
        ('http://feeds.bbci.co.uk/mundo/rss.xml',             'BBC Mundo'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada', 'El País'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/mundo/', 'Infobae'),
        ('https://feeds.france24.com/es/',                    'France 24'),
        ('https://www.efe.com/efe/espana/1/rss',              'EFE'),
    ]
    noticias = []
    for url_feed, nombre in fuentes:
        try:
            r = requests.get(url_feed, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries:
                continue
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t:
                    continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l:
                    continue
                d = re.sub(r'<[^>]+>', '', e.get('summary', '') or e.get('description', ''))
                img = None
                if hasattr(e, 'media_content') and e.media_content:
                    img = e.media_content[0].get('url')
                noticias.append({
                    'titulo':      limpiar_texto(t),
                    'descripcion': limpiar_texto(d),
                    'url':         l,
                    'imagen':      img,
                    'fuente':      f"RSS:{nombre}",
                    'fecha':       e.get('published'),
                    'puntaje':     calcular_puntaje(t, d),
                })
        except Exception as e:
            log(f"RSS error ({nombre}): {e}", 'advertencia')
            continue
    log(f"RSS: {len(noticias)} noticias", 'info')
    return noticias

# ──────────────────────────────────────────────────────────
# DEDUPLICACIÓN LOCAL (dentro del batch actual)
# ──────────────────────────────────────────────────────────
def deduplicar_batch(noticias):
    urls_vistas    = set()
    titulos_vistos = []
    resultado      = []

    for n in noticias:
        url_n  = normalizar_url(n.get('url', ''))
        titulo = n.get('titulo', '')

        if not url_n or not titulo:
            continue
        if url_n in urls_vistas:
            continue

        es_dup = False
        for t_previo in titulos_vistos:
            if similitud_titulos(titulo, t_previo) > 0.78:
                es_dup = True
                break

        if es_dup:
            continue

        urls_vistas.add(url_n)
        titulos_vistos.append(titulo)
        resultado.append(n)

    log(f"Dedup batch: {len(noticias)} → {len(resultado)} únicas", 'info')
    return resultado

# ──────────────────────────────────────────────────────────
# EXTRACCIÓN DE CONTENIDO E IMAGEN
# ──────────────────────────────────────────────────────────
def extraer_contenido(url):
    if not url:
        return None, None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        for e in s(['script', 'style', 'nav', 'header', 'footer']):
            e.decompose()
        for selector in ['article', '[class*="article-content"]', '[class*="entry-content"]', '[class*="post-content"]']:
            art = s.select_one(selector)
            if art:
                ps = [p for p in art.find_all('p') if len(p.get_text()) > 40]
                if len(ps) >= 2:
                    txt = ' '.join([limpiar_texto(p.get_text()) for p in ps])
                    if len(txt) > 200:
                        return txt[:2000], None
        return None, None
    except:
        return None, None

def extraer_imagen_web(url):
    if not url:
        return None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for prop in ['og:image', 'twitter:image']:
            tag = s.find('meta', property=prop) or s.find('meta', attrs={'name': prop})
            if tag:
                img = tag.get('content', '').strip()
                if img and img.startswith('http') and 'google' not in img.lower():
                    return img
        return None
    except:
        return None

def descargar_imagen(url):
    if not url:
        return None
    for bloqueo in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon', 'favicon']:
        if bloqueo in url.lower():
            return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200:
            return None
        if 'image' not in r.headers.get('content-type', ''):
            return None
        img = Image.open(BytesIO(r.content))
        w, h = img.size
        if w < 400 or h < 300:
            return None
        if w / h > 4 or w / h < 0.2:
            return None
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((1200, 1200))
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=85)
        if os.path.getsize(p) < 5000:
            os.remove(p)
            return None
        return p
    except:
        return None

def crear_imagen_titulo(titulo):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        img  = Image.new('RGB', (1200, 630), color='#0f172a')
        draw = ImageDraw.Draw(img)
        try:
            fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            fb = fs = ImageFont.load_default()
        draw.rectangle([(0, 0), (1200, 8)], fill='#3b82f6')
        tt = textwrap.fill(titulo[:140], width=36)
        ls = tt.split('\n')
        y  = (630 - len(ls) * 50) // 2 - 50
        draw.text((60, y), tt, font=fb, fill='white')
        draw.text((60, 550), "🌍 Noticias Internacionales", font=fs, fill='#94a3b8')
        draw.text((60, 580), "Verdad Hoy • Agencia de Noticias", font=fs, fill='#64748b')
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img.save(p, 'JPEG', quality=90)
        return p
    except:
        return None

# ──────────────────────────────────────────────────────────
# CONSTRUCCIÓN Y PUBLICACIÓN
# ──────────────────────────────────────────────────────────
def dividir_parrafos(texto):
    if not texto:
        return []
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    if len(oraciones) < 3:
        return [texto] if len(texto) > 100 else []
    parrafos, actual, palabras = [], [], 0
    for i, o in enumerate(oraciones):
        actual.append(o)
        palabras += len(o.split())
        if palabras >= 40 or i == len(oraciones) - 1:
            if len(' '.join(actual).split()) >= 15:
                parrafos.append(' '.join(actual))
            actual, palabras = [], 0
    return parrafos[:8]

def construir_publicacion(titulo, contenido, creditos, fuente):
    t    = limpiar_texto(titulo)
    pars = dividir_parrafos(contenido)
    if len(pars) < 2:
        ors  = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        pars = [' '.join(ors[i:i+2]) for i in range(0, len(ors), 2)][:8]
    lineas = [f"📰 ÚLTIMA HORA | {t}", ""]
    for i, p in enumerate(pars):
        lineas.append(p)
        if i < len(pars) - 1:
            lineas.append("")
    lineas += ["", "──────────────────────────────", ""]
    if creditos:
        lineas += [f"✍️ {creditos}", ""]
    lineas.append(f"📎 {fuente}")
    return '\n'.join(lineas)

def generar_hashtags(titulo, contenido):
    txt = f"{titulo} {contenido}".lower()
    tags = ['#NoticiasInternacionales', '#ÚltimaHora']
    mapa = {
        r'guerra|conflicto|ataque|bombardeo': '#ConflictoArmado',
        r'ucrania|rusia|putin':               '#UcraniaRusia',
        r'gaza|israel|hamas':                 '#IsraelGaza',
        r'trump|biden|eeuu|estados unidos':   '#PolíticaGlobal',
        r'economía|inflación|recesión':       '#EconomíaMundial',
        r'china|taiwan':                      '#ChinaTaiwán',
        r'iran|medio oriente':                '#MedioOriente',
        r'terrorismo|atentado':               '#Terrorismo',
    }
    for patron, tag in mapa.items():
        if re.search(patron, txt):
            tags.append(tag)
            break
    tags.append('#Mundo')
    return ' '.join(tags)

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    mensaje = f"{texto}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    if len(mensaje) > 2000:
        lineas = texto.split('\n')
        tc = ""
        for ln in lineas:
            if len(tc + ln + "\n") < 1600:
                tc += ln + "\n"
            else:
                break
        mensaje = f"{tc.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    mensaje = re.sub(r'https?://\S+', '', mensaje)
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            r = requests.post(
                url,
                files={'file': ('imagen.jpg', f, 'image/jpeg')},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            ).json()
        if 'id' in r:
            log(f"✅ Publicado en Facebook — ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook: {r.get('error', {}).get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando: {e}", 'error')
    return False

# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("🌍 BOT DE NOTICIAS - V4.0 (HISTORIAL PERSISTENTE)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Historial: {os.path.abspath(HISTORIAL_PATH)}")
    print(f"📁 Estado:    {os.path.abspath(ESTADO_PATH)}")
    print("=" * 60)

    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR CRÍTICO: Faltan credenciales Facebook (FB_PAGE_ID / FB_ACCESS_TOKEN)", 'error')
        return False

    # Control de tiempo — PRIMERA barrera
    if not verificar_tiempo():
        return False

    # Cargar historial
    h = cargar_historial()
    total_historial = len(h.get('urls', []))
    log(f"📊 Historial: {total_historial} entradas | Permanentes: {len(h.get('hashes_permanentes', []))}")

    # Recolectar noticias
    noticias = []
    if NEWS_API_KEY:
        noticias.extend(obtener_newsapi())
    if NEWSDATA_API_KEY:
        noticias.extend(obtener_newsdata())
    if GNEWS_API_KEY:
        noticias.extend(obtener_gnews())
    if len(noticias) < 15:
        log("⚠️ Pocas noticias, complementando con RSS...", 'advertencia')
        noticias.extend(obtener_rss())

    if not noticias:
        log("ERROR: Ninguna fuente devolvió noticias", 'error')
        return False

    # Deduplicar batch y ordenar
    noticias = deduplicar_batch(noticias)
    noticias.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    log(f"📰 Candidatas ordenadas por puntaje: {len(noticias)}")

    # Buscar noticia válida
    seleccionada = None
    contenido    = None
    creditos     = None
    intentos     = 0

    for i, nt in enumerate(noticias):
        if intentos >= 60:
            log(f"⚠️ Límite de intentos alcanzado (60)", 'advertencia')
            break

        url    = nt.get('url', '')
        titulo = nt.get('titulo', '')
        desc   = nt.get('descripcion', '')

        if not url or not titulo:
            continue

        intentos += 1

        # Recargar historial cada 15 intentos (por si hay concurrencia)
        if intentos % 15 == 0:
            h = cargar_historial()

        log(f"\n[{i+1}] Puntaje {nt.get('puntaje',0)} | {titulo[:55]}...", 'debug')

        dup, razon = noticia_ya_publicada(h, url, titulo, desc)
        if dup:
            log(f"   ❌ {razon}", 'debug')
            continue

        if nt.get('puntaje', 0) < 3:
            log(f"   ❌ Puntaje insuficiente ({nt.get('puntaje', 0)})", 'debug')
            continue

        log(f"   ✅ Candidata válida — extrayendo contenido...")

        cont_web, cred_web = extraer_contenido(url)

        if cont_web and len(cont_web) >= 200:
            log(f"   ✅ Contenido web: {len(cont_web)} chars", 'exito')
            contenido    = cont_web
            creditos     = cred_web
            seleccionada = nt
            break
        elif desc and len(desc) >= 150:
            log(f"   ✅ Usando descripción: {len(desc)} chars", 'exito')
            contenido    = desc
            creditos     = None
            seleccionada = nt
            break
        else:
            log(f"   ❌ Contenido insuficiente ({len(cont_web or desc or '')} chars)", 'advertencia')

    if not seleccionada:
        log("ERROR: No se encontró ninguna noticia válida nueva", 'error')
        return False

    log(f"\n📝 PUBLICANDO: {seleccionada['titulo'][:70]}")
    log(f"   Fuente: {seleccionada['fuente']} | Puntaje: {seleccionada.get('puntaje', 0)}")

    # Construir texto
    pub = construir_publicacion(seleccionada['titulo'], contenido, creditos, seleccionada['fuente'])
    ht  = generar_hashtags(seleccionada['titulo'], contenido)

    # Imagen
    log("🖼️  Procesando imagen...")
    img_path = None
    if seleccionada.get('imagen'):
        img_path = descargar_imagen(seleccionada['imagen'])
    if not img_path:
        img_url = extraer_imagen_web(seleccionada['url'])
        if img_url:
            img_path = descargar_imagen(img_url)
    if not img_path:
        img_path = crear_imagen_titulo(seleccionada['titulo'])
    if not img_path:
        log("ERROR: No se pudo obtener imagen", 'error')
        return False

    # Publicar
    ok = publicar_facebook(seleccionada['titulo'], pub, img_path, ht)

    # Limpiar imagen temporal
    try:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
    except:
        pass

    if ok:
        # Guardar historial Y estado SIEMPRE que la publicación sea exitosa
        desc_completa = (seleccionada.get('descripcion', '') + ' ' + contenido[:400]).strip()
        h = guardar_en_historial(h, seleccionada['url'], seleccionada['titulo'], desc_completa)
        guardar_estado()
        total = h.get('estadisticas', {}).get('total_publicadas', 0)
        log(f"✅ ÉXITO — Total publicadas en historial: {total}", 'exito')
        log(f"💡 IMPORTANTE: El workflow debe hacer git push de {HISTORIAL_PATH} y {ESTADO_PATH}", 'advertencia')
        return True
    else:
        log("❌ Publicación fallida — historial NO actualizado", 'error')
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
