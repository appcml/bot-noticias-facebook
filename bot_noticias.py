#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V5.0
MEJORAS DE ENGAGEMENT:
  - Horarios pico para audiencia hispanohablante
  - CTA automático al final de cada publicación
  - Límite diario de posts (máx. 6/día)
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
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

# ── ENGAGEMENT V5 ──────────────────────────────────────────
MAX_POSTS_POR_DIA = 8  # Mas de 6/dia penaliza el alcance organico en Facebook

# Horarios pico para audiencia hispanohablante (hora UTC)
# Rangos amplios para cubrir distintas zonas horarias:
# 00-04 UTC = tarde/noche America Central y Mexico
# 10-14 UTC = manana Espana / manana America del Sur
# 17-22 UTC = tarde-noche Espana / mediodia America
HORARIOS_PICO_UTC = [
    (0, 4),
    (10, 14),
    (17, 22),
]

# CTAs por tema — usados en descripción del post y video
CTAS_POR_TEMA = {
    'guerra': [
        "¿Crees que esto puede escalar a un conflicto mayor? Dinos abajo 👇",
        "¿Qué solución ves a este conflicto? Comenta 👇",
        "¿El mundo está haciendo suficiente? Tu opinión importa 👇",
        "¿Esto te preocupa? Cuéntanos qué piensas 👇",
    ],
    'politica': [
        "¿Estás de acuerdo con esta decisión? Comenta SÍ o NO 👇",
        "¿Qué opinas de esta medida? Tu voz cuenta 👇",
        "¿Cómo crees que afectará esto a la región? Dinos 👇",
        "¿Confías en estos líderes? Comenta abajo 👇",
    ],
    'economia': [
        "¿Sientes esto en tu bolsillo? Cuéntanos 👇",
        "¿Cómo te afecta esta situación económica? Comenta 👇",
        "¿Crees que mejorará la economía? SÍ o NO 👇",
        "¿Qué medidas tomarías tú? Opina abajo 👇",
    ],
    'tecnologia': [
        "¿La IA nos ayuda o nos amenaza? Comenta 👇",
        "¿Usarías esta tecnología? Dinos 👇",
        "¿El futuro te emociona o te preocupa? Opina 👇",
        "¿Qué piensas de este avance? Cuéntanos 👇",
    ],
    'desastre': [
        "Nuestros pensamientos con los afectados 🙏 Comenta abajo 👇",
        "¿Cómo podemos ayudar en situaciones así? Opina 👇",
        "¿El mundo reacciona a tiempo ante estas crisis? 👇",
        "¿Has vivido algo similar? Cuéntanos 👇",
    ],
    'general': [
        "¿Qué piensas de esta noticia? Comenta abajo 👇",
        "¿Sabías esto? Dinos SÍ o NO 👇",
        "¿Te sorprende? Cuéntanos qué opinas 👇",
        "Comparte si crees que todos deben saberlo 🔁",
    ],
}

# CTAs para el VIDEO (panel rojo al final) — por tema
CTAS_VIDEO_POR_TEMA = {
    'guerra':     "¿Crees que escalará? COMENTA 👇",
    'politica':   "¿De acuerdo? SÍ o NO en comentarios 👇",
    'economia':   "¿Te afecta esto? CUÉNTANOS 👇",
    'tecnologia': "¿A favor o en contra? OPINA 👇",
    'desastre':   "Deja tu mensaje de apoyo 🙏 COMENTA",
    'general':    "¿Qué opinas? COMENTA AHORA 👇",
}

def detectar_tema(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(p in txt for p in ["guerra", "bombardeo", "misil", "ataque", "conflicto",
                               "invasion", "tropas", "nuclear", "terroris", "hamas",
                               "hezbollah", "ucrania", "gaza", "israel", "rusia"]):
        return 'guerra'
    if any(p in txt for p in ["trump", "biden", "presidente", "gobierno", "eleccion",
                               "politica", "congreso", "sancion", "diplomaci",
                               "golpe de estado", "otan", "nato"]):
        return 'politica'
    if any(p in txt for p in ["economia", "inflacion", "recesion", "bolsa", "mercado",
                               "petroleo", "dolar", "fmi", "banco", "crisis economica"]):
        return 'economia'
    if any(p in txt for p in ["inteligencia artificial", "tecnologia", "ia ", "robot",
                               "ciberataque", "hackeo", "elon musk", "openai"]):
        return 'tecnologia'
    if any(p in txt for p in ["terremoto", "huracan", "inundacion", "desastre",
                               "victimas", "muertos", "evacuacion", "tsunami"]):
        return 'desastre'
    return 'general'

def agregar_cta(texto, titulo="", descripcion=""):
    """Agrega un CTA temático al final del texto de la publicación."""
    tema = detectar_tema(titulo, descripcion)
    cta  = random.choice(CTAS_POR_TEMA.get(tema, CTAS_POR_TEMA['general']))
    return f"{texto}\n\n{cta}"

def obtener_cta_video(titulo, descripcion=""):
    """Retorna el CTA corto para mostrar en el panel rojo del video."""
    tema = detectar_tema(titulo, descripcion)
    return CTAS_VIDEO_POR_TEMA.get(tema, CTAS_VIDEO_POR_TEMA['general'])

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
    # Si se activa manualmente con FORZAR_PUBLICACION=true, saltar control de tiempo
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        log("⚡ Modo forzado — omitiendo control de tiempo", 'advertencia')
        return True
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
# CONTROL DE ENGAGEMENT (V5)
# ──────────────────────────────────────────────────────────
def esta_en_horario_pico():
    """Devuelve True si la hora UTC actual está en una ventana de alta audiencia."""
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        log("⚡ Modo forzado — omitiendo control de horario pico", 'advertencia')
        return True
    hora_utc = datetime.utcnow().hour
    for inicio, fin in HORARIOS_PICO_UTC:
        if inicio <= hora_utc < fin:
            return True
    log(f"⏰ Fuera de horario pico (hora UTC: {hora_utc:02d}:xx) — publicación omitida", 'info')
    return False

def limite_diario_alcanzado(h):
    """Devuelve True si ya se publicaron MAX_POSTS_POR_DIA hoy."""
    hoy = datetime.now().date()
    publicadas_hoy = sum(
        1 for ts in h.get('timestamps', [])
        if ts and datetime.fromisoformat(ts).date() == hoy
    )
    if publicadas_hoy >= MAX_POSTS_POR_DIA:
        log(f"🚫 Límite diario alcanzado: {publicadas_hoy}/{MAX_POSTS_POR_DIA} posts hoy", 'advertencia')
        return True
    log(f"📊 Posts hoy: {publicadas_hoy}/{MAX_POSTS_POR_DIA}", 'info')
    return False


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
                        return txt[:5000], None
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
            log(f"⚠️ Imagen HTTP {r.status_code}: {url[:60]}", 'debug')
            return None
        ct = r.headers.get('content-type', '')
        if 'image' not in ct and 'octet' not in ct:
            log(f"⚠️ Content-type no imagen: {ct}", 'debug')
            return None
        data = r.content
        img = Image.open(BytesIO(data))
        w, h = img.size
        # Límites más permisivos — solo descartar íconos muy pequeños
        if w < 200 or h < 150:
            log(f"⚠️ Imagen muy pequeña: {w}x{h}", 'debug')
            return None
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.thumbnail((1280, 1280))
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=88)
        if os.path.getsize(p) < 3000:
            os.remove(p)
            return None
        log(f"🖼️ Imagen descargada: {w}x{h} → {p}", 'debug')
        return p
    except Exception as e:
        log(f"⚠️ Error descargando imagen: {e}", 'debug')
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
# GENERACIÓN DE VIDEO (V5)
# ──────────────────────────────────────────────────────────
def crear_frame(titulo, resumen, logo_texto, ancho=1280, alto=720,
                fondo_path=None, progreso=0.0):
    """
    Genera un frame PIL con diseño split:
    - Mitad derecha: imagen nítida de la noticia
    - Mitad izquierda: panel oscuro con texto
    progreso: 0.0 a 1.0 para controlar opacidad del texto (fade-in).
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import textwrap

    mitad = ancho // 2  # 640px

    # ── Fondo base oscuro ──────────────────────────────────
    frame = Image.new('RGB', (ancho, alto), '#0d1117')

    # ── Imagen nítida en la mitad derecha ──────────────────
    if fondo_path:
        try:
            img = Image.open(fondo_path).convert('RGB')
            # Recortar y escalar para llenar la mitad derecha
            img_ratio = img.width / img.height
            target_ratio = mitad / alto
            if img_ratio > target_ratio:
                new_h = alto
                new_w = int(alto * img_ratio)
            else:
                new_w = mitad
                new_h = int(mitad / img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Centrar crop
            x = (new_w - mitad) // 2
            y = (new_h - alto) // 2
            img = img.crop((x, y, x + mitad, y + alto))
            # Leve mejora de nitidez y contraste
            img = ImageEnhance.Sharpness(img).enhance(1.4)
            img = ImageEnhance.Contrast(img).enhance(1.1)
            # Gradiente izquierdo para fusionar con panel de texto
            grad = Image.new('RGBA', (mitad, alto), (0, 0, 0, 0))
            gd = ImageDraw.Draw(grad)
            for x_g in range(80):
                alpha_g = int(255 * (1 - x_g / 80))
                gd.line([(x_g, 0), (x_g, alto)], fill=(13, 17, 23, alpha_g))
            img_rgba = img.convert('RGBA')
            img_rgba = Image.alpha_composite(img_rgba, grad)
            frame.paste(img_rgba.convert('RGB'), (mitad, 0))
        except Exception as e:
            log(f"⚠️ Error cargando imagen fondo: {e}", 'debug')

    # ── Panel izquierdo semitransparente ───────────────────
    panel = Image.new('RGBA', (mitad + 40, alto), (13, 17, 23, 230))
    frame.paste(panel.convert('RGB'), (0, 0))

    draw = ImageDraw.Draw(frame)

    # ── Fuentes ────────────────────────────────────────────
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    font_paths_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    def cargar_fuente(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
        return ImageFont.load_default()

    font_breaking = cargar_fuente(font_paths, 24)
    font_titulo   = cargar_fuente(font_paths, 44)
    font_resumen  = cargar_fuente(font_paths_reg, 24)
    font_logo     = cargar_fuente(font_paths, 20)

    alpha = int(255 * min(progreso * 2, 1.0))  # fade-in

    # ── Barra superior roja "ÚLTIMA HORA" ─────────────────
    draw.rectangle([(0, 0), (ancho, 52)], fill='#dc2626')
    draw.text((20, 14), "  ÚLTIMA HORA  |  VERDAD HOY", font=font_breaking, fill='white')

    # ── Línea acento azul ──────────────────────────────────
    draw.rectangle([(20, 68), (mitad - 20, 71)], fill='#3b82f6')

    # ── Título (fade-in, limitado al panel izquierdo) ─────
    titulo_wrap = textwrap.fill(titulo[:110], width=22)
    lineas_titulo = titulo_wrap.split('\n')
    y_titulo = 90
    for linea in lineas_titulo:
        tmp = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
        d2  = ImageDraw.Draw(tmp)
        d2.text((20, y_titulo), linea, font=font_titulo, fill=(255, 255, 255, alpha))
        frame = Image.alpha_composite(frame.convert('RGBA'), tmp).convert('RGB')
        draw  = ImageDraw.Draw(frame)
        y_titulo += 56

    # ── Línea separadora ──────────────────────────────────
    sep_y = y_titulo + 10
    draw.rectangle([(20, sep_y), (mitad - 30, sep_y + 2)], fill='#3b82f6')

    # ── Resumen (aparece después, limitado al panel) ──────
    if progreso > 0.5:
        alpha2 = int(255 * min((progreso - 0.5) * 2, 1.0))
        resumen_corto = resumen[:200] + ('...' if len(resumen) > 200 else '')
        resumen_wrap  = textwrap.fill(resumen_corto, width=38)
        tmp2 = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
        d3   = ImageDraw.Draw(tmp2)
        d3.text((20, sep_y + 14), resumen_wrap, font=font_resumen,
                fill=(203, 213, 225, alpha2))
        frame = Image.alpha_composite(frame.convert('RGBA'), tmp2).convert('RGB')
        draw  = ImageDraw.Draw(frame)

    # ── Barra inferior con logo ────────────────────────────
    draw.rectangle([(0, alto - 44), (ancho, alto)], fill='#1e293b')
    draw.text((20, alto - 30), f"  {logo_texto}  •  noticias internacionales",
              font=font_logo, fill='#94a3b8')

    return frame


def crear_audio_noticia(titulo, resumen):
    """
    Genera audio TTS en español latino usando espeak (offline, sin API key).
    Retorna la ruta del archivo .mp3 o None si falla.
    """
    try:
        import subprocess
        resumen_corto = resumen[:300]
        for sep in ['. ', '! ', '? ']:
            idx = resumen_corto.rfind(sep)
            if idx > 80:
                resumen_corto = resumen_corto[:idx + 1]
                break

        guion = (
            f"Última hora. {titulo}. "
            f"{resumen_corto} "
            f"Lee todos los detalles en la publicación."
        )
        guion = re.sub(r'[#@\[\]<>*_]', '', guion)
        guion = re.sub(r'https?://\S+', '', guion)
        guion = re.sub(r'\s+', ' ', guion).strip()

        hash_a    = generar_hash(titulo)
        wav_path  = f'/tmp/noticia_audio_{hash_a}.wav'
        mp3_path  = f'/tmp/noticia_audio_{hash_a}.mp3'

        # Generar WAV con espeak (offline, español latinoamericano)
        r = subprocess.run(
            ['espeak', '-v', 'es-la', '-s', '145', '-p', '48', '-a', '180',
             '-w', wav_path, guion],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0 or not os.path.exists(wav_path):
            log(f"⚠️ espeak falló: {r.stderr[:100]}", 'advertencia')
            return None

        # Convertir WAV → MP3 con ffmpeg
        subprocess.run(
            ['ffmpeg', '-y', '-i', wav_path, '-codec:a', 'libmp3lame', '-q:a', '4', mp3_path],
            capture_output=True, timeout=30
        )
        try:
            os.remove(wav_path)
        except:
            pass

        if os.path.exists(mp3_path):
            log(f"🔊 Audio TTS generado ({os.path.getsize(mp3_path)//1024} KB)", 'exito')
            return mp3_path

        return None
    except FileNotFoundError:
        log("⚠️ espeak no instalado — video sin audio", 'advertencia')
        return None
    except Exception as e:
        log(f"⚠️ Error generando audio: {e} — video sin audio", 'advertencia')
        return None


def crear_video_noticia(titulo, resumen, fondo_path=None, duracion=28, fps=24):
    """
    Genera un video MP4 con:
    - Voz TTS que lee el titular y resumen
    - Efecto Ken Burns (zoom lento) en la imagen
    - Panel CTA rojo temático al final
    """
    try:
        from moviepy.editor import ImageSequenceClip, AudioFileClip
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
        import textwrap

        log("🎬 Generando video noticiario...", 'info')

        # CTA temático para el video
        cta_video = obtener_cta_video(titulo, resumen)

        # ── 1. Generar audio TTS ──────────────────────────
        audio_path  = crear_audio_noticia(titulo, resumen)
        audio_dur   = 0.0
        if audio_path:
            try:
                ac = AudioFileClip(audio_path)
                audio_dur = ac.duration
                ac.close()
                duracion = max(20, min(50, int(audio_dur) + 2))
                log(f"⏱️ Duración ajustada al audio: {duracion}s (audio: {audio_dur:.1f}s)", 'info')
            except Exception as e:
                log(f"⚠️ No se pudo leer duración del audio: {e}", 'advertencia')
                duracion = 28

        ancho, alto  = 1280, 720
        mitad        = ancho // 2
        total_frames = duracion * fps

        # ── 2. Pre-cargar imagen para Ken Burns ───────────
        img_base = None
        if fondo_path:
            try:
                img_base = Image.open(fondo_path).convert('RGB')
                scale_w = int(mitad * 1.25)
                scale_h = int(alto  * 1.25)
                img_base = img_base.resize((scale_w, scale_h), Image.LANCZOS)
                img_base = ImageEnhance.Sharpness(img_base).enhance(1.4)
                img_base = ImageEnhance.Contrast(img_base).enhance(1.1)
            except Exception as e:
                log(f"⚠️ Error cargando imagen: {e}", 'debug')
                img_base = None

        # ── 3. Fuentes ────────────────────────────────────
        fp_b = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        fp_r = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]

        def carga_font(paths, size):
            for p in paths:
                try: return ImageFont.truetype(p, size)
                except: continue
            return ImageFont.load_default()

        font_bk  = carga_font(fp_b, 24)
        font_tit = carga_font(fp_b, 44)
        font_res = carga_font(fp_r, 24)
        font_log = carga_font(fp_b, 20)
        font_cta = carga_font(fp_b, 36)

        # Fase CTA: últimos 5 segundos del video
        cta_inicio = max(0.75, 1.0 - (5 / duracion))

        # ── 4. Generar frames ─────────────────────────────
        frames = []
        for i in range(total_frames):
            t = i / total_frames

            # Progreso texto (fade-in)
            if t < 0.08:   progreso = 0.0
            elif t < 0.50: progreso = (t - 0.08) / 0.42
            elif t < 0.85: progreso = 1.0
            else:          progreso = 1.0 - (t - 0.85) / 0.15
            progreso = max(0.0, min(1.0, progreso))
            alpha    = int(255 * min(progreso * 2, 1.0))

            # Fase CTA activa en últimos 5s
            en_cta     = t >= cta_inicio
            alpha_cta  = int(255 * min((t - cta_inicio) / 0.08, 1.0)) if en_cta else 0

            # ── Frame base
            frame = Image.new('RGB', (ancho, alto), '#0d1117')

            # ── Ken Burns zoom out
            if img_base:
                scale_w, scale_h = img_base.size
                zoom    = 1.25 - (0.25 * t)
                crop_w  = int(mitad * zoom)
                crop_h  = int(alto  * zoom)
                cx      = max(0, min((scale_w - crop_w) // 2, scale_w - crop_w))
                cy      = max(0, min((scale_h - crop_h) // 2, scale_h - crop_h))
                img_c   = img_base.crop((cx, cy, cx + crop_w, cy + crop_h))
                img_c   = img_c.resize((mitad, alto), Image.LANCZOS)
                grad    = Image.new('RGBA', (mitad, alto), (0, 0, 0, 0))
                gd      = ImageDraw.Draw(grad)
                for xg in range(80):
                    gd.line([(xg, 0), (xg, alto)], fill=(13, 17, 23, int(255 * (1 - xg / 80))))
                frame.paste(Image.alpha_composite(img_c.convert('RGBA'), grad).convert('RGB'), (mitad, 0))

            # ── Panel izquierdo
            frame.paste(Image.new('RGB', (mitad + 40, alto), '#0d1117'), (0, 0))
            draw = ImageDraw.Draw(frame)

            # ── Barra roja superior
            draw.rectangle([(0, 0), (ancho, 52)], fill='#dc2626')
            draw.text((20, 14), "  ÚLTIMA HORA  |  VERDAD HOY", font=font_bk, fill='white')

            # ── Línea azul
            draw.rectangle([(20, 68), (mitad - 20, 71)], fill='#3b82f6')

            # ── Título
            y = 90
            for linea in textwrap.fill(titulo[:110], width=22).split('\n'):
                tmp = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                ImageDraw.Draw(tmp).text((20, y), linea, font=font_tit, fill=(255, 255, 255, alpha))
                frame = Image.alpha_composite(frame.convert('RGBA'), tmp).convert('RGB')
                draw  = ImageDraw.Draw(frame)
                y += 56

            sep_y = y + 10
            draw.rectangle([(20, sep_y), (mitad - 30, sep_y + 2)], fill='#3b82f6')

            # ── Resumen
            if progreso > 0.5 and not en_cta:
                alpha2 = int(255 * min((progreso - 0.5) * 2, 1.0))
                tmp2   = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                ImageDraw.Draw(tmp2).text((20, sep_y + 14),
                    textwrap.fill(resumen[:200] + ('...' if len(resumen) > 200 else ''), width=38),
                    font=font_res, fill=(203, 213, 225, alpha2))
                frame = Image.alpha_composite(frame.convert('RGBA'), tmp2).convert('RGB')
                draw  = ImageDraw.Draw(frame)

            # ── Panel CTA rojo (últimos 5s) ───────────────
            if en_cta and alpha_cta > 0:
                cta_h  = 100
                cta_y  = alto - 44 - cta_h - 10
                # Fondo rojo con alpha
                cta_bg = Image.new('RGBA', (ancho, cta_h), (220, 38, 38, alpha_cta))
                frame_rgba = frame.convert('RGBA')
                frame_rgba.paste(cta_bg, (0, cta_y), cta_bg)
                frame = frame_rgba.convert('RGB')
                draw  = ImageDraw.Draw(frame)
                # Texto CTA centrado
                bbox  = draw.textbbox((0, 0), cta_video, font=font_cta)
                tw    = bbox[2] - bbox[0]
                tx    = (ancho - tw) // 2
                ty    = cta_y + (cta_h - (bbox[3] - bbox[1])) // 2
                tmp3  = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                ImageDraw.Draw(tmp3).text((tx, ty), cta_video, font=font_cta,
                                          fill=(255, 255, 255, alpha_cta))
                frame = Image.alpha_composite(frame.convert('RGBA'), tmp3).convert('RGB')
                draw  = ImageDraw.Draw(frame)

            # ── Barra inferior logo
            draw.rectangle([(0, alto - 44), (ancho, alto)], fill='#1e293b')
            draw.text((20, alto - 30), "  Verdad Hoy | Agencia de Noticias  •  noticias internacionales",
                      font=font_log, fill='#94a3b8')

            frames.append(np.array(frame))

        # ── 5. Ensamblar video + audio ─────────────────────
        clip       = ImageSequenceClip(frames, fps=fps)
        hash_v     = generar_hash(titulo)
        video_path = f'/tmp/noticia_video_{hash_v}.mp4'

        if audio_path and os.path.exists(audio_path):
            try:
                audio_clip = AudioFileClip(audio_path)
                safe_dur   = min(audio_clip.duration - 0.3, duracion - 0.3)
                audio_clip = audio_clip.subclip(0, max(1.0, safe_dur))
                clip       = clip.set_audio(audio_clip)
                clip.write_videofile(video_path, codec='libx264', audio_codec='aac',
                                     preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)
                audio_clip.close()
                log("🔊 Audio mezclado correctamente en el video", 'exito')
            except Exception as e:
                log(f"⚠️ Error mezclando audio: {e} — generando sin audio", 'advertencia')
                clip.write_videofile(video_path, codec='libx264', audio=False,
                                     preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)
            finally:
                try: os.remove(audio_path)
                except: pass
        else:
            clip.write_videofile(video_path, codec='libx264', audio=False,
                                 preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)

        clip.close()
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log(f"✅ Video generado: {video_path} ({size_mb:.1f} MB, {duracion}s)", 'exito')
        return video_path

    except ImportError:
        log("⚠️ moviepy no disponible — usando imagen", 'advertencia')
        return None
    except Exception as e:
        log(f"⚠️ Error generando video: {e} — usando imagen", 'advertencia')
        return None
    try:
        from moviepy.editor import ImageSequenceClip, AudioFileClip
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
        import textwrap

        log("🎬 Generando video noticiario...", 'info')

        # ── 1. Generar audio TTS ──────────────────────────
        audio_path  = crear_audio_noticia(titulo, resumen)
        audio_dur   = 0.0
        if audio_path:
            try:
                ac = AudioFileClip(audio_path)
                audio_dur = ac.duration
                ac.close()
                # Video = audio + 2s de margen (mín 20s, máx 50s)
                duracion = max(20, min(50, int(audio_dur) + 2))
                log(f"⏱️ Duración ajustada al audio: {duracion}s (audio: {audio_dur:.1f}s)", 'info')
            except Exception as e:
                log(f"⚠️ No se pudo leer duración del audio: {e}", 'advertencia')
                duracion = 28

        ancho, alto  = 1280, 720
        mitad        = ancho // 2
        total_frames = duracion * fps

        # ── 2. Pre-cargar imagen para Ken Burns ───────────
        img_base = None
        if fondo_path:
            try:
                img_base = Image.open(fondo_path).convert('RGB')
                # Escalar a un tamaño mayor al target para poder hacer zoom out
                scale_w = int(mitad * 1.25)
                scale_h = int(alto  * 1.25)
                img_base = img_base.resize((scale_w, scale_h), Image.LANCZOS)
                img_base = ImageEnhance.Sharpness(img_base).enhance(1.4)
                img_base = ImageEnhance.Contrast(img_base).enhance(1.1)
            except Exception as e:
                log(f"⚠️ Error cargando imagen: {e}", 'debug')
                img_base = None

        # ── 3. Fuentes (cargar una vez) ───────────────────
        fp_b = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        fp_r = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]

        def carga_font(paths, size):
            for p in paths:
                try: return ImageFont.truetype(p, size)
                except: continue
            return ImageFont.load_default()

        font_bk  = carga_font(fp_b, 24)
        font_tit = carga_font(fp_b, 44)
        font_res = carga_font(fp_r, 24)
        font_log = carga_font(fp_b, 20)

        # ── 4. Generar frames con Ken Burns ───────────────
        frames = []
        for i in range(total_frames):
            t = i / total_frames  # 0.0 → 1.0

            # Progreso del texto (fade-in)
            if t < 0.08:   progreso = 0.0
            elif t < 0.50: progreso = (t - 0.08) / 0.42
            elif t < 0.85: progreso = 1.0
            else:          progreso = 1.0 - (t - 0.85) / 0.15
            progreso = max(0.0, min(1.0, progreso))
            alpha    = int(255 * min(progreso * 2, 1.0))

            # ── Frame base oscuro
            frame = Image.new('RGB', (ancho, alto), '#0d1117')

            # ── Ken Burns: zoom 125%→100% (zoom out lento)
            if img_base:
                scale_w, scale_h = img_base.size
                # Interpolación lineal de zoom: empieza recortado, termina encuadrado
                zoom = 1.25 - (0.25 * t)          # 1.25 → 1.00
                crop_w = int(mitad * zoom)
                crop_h = int(alto  * zoom)
                # Centrar el crop
                cx = (scale_w - crop_w) // 2
                cy = (scale_h - crop_h) // 2
                cx = max(0, min(cx, scale_w - crop_w))
                cy = max(0, min(cy, scale_h - crop_h))
                img_crop = img_base.crop((cx, cy, cx + crop_w, cy + crop_h))
                img_crop = img_crop.resize((mitad, alto), Image.LANCZOS)

                # Gradiente izquierdo para fusionar con panel
                grad = Image.new('RGBA', (mitad, alto), (0, 0, 0, 0))
                gd   = ImageDraw.Draw(grad)
                for xg in range(80):
                    ag = int(255 * (1 - xg / 80))
                    gd.line([(xg, 0), (xg, alto)], fill=(13, 17, 23, ag))
                img_rgba = Image.alpha_composite(img_crop.convert('RGBA'), grad)
                frame.paste(img_rgba.convert('RGB'), (mitad, 0))

            # ── Panel izquierdo
            panel = Image.new('RGBA', (mitad + 40, alto), (13, 17, 23, 235))
            frame.paste(panel.convert('RGB'), (0, 0))
            draw = ImageDraw.Draw(frame)

            # ── Barra roja superior
            draw.rectangle([(0, 0), (ancho, 52)], fill='#dc2626')
            draw.text((20, 14), "  ÚLTIMA HORA  |  VERDAD HOY", font=font_bk, fill='white')

            # ── Línea azul acento
            draw.rectangle([(20, 68), (mitad - 20, 71)], fill='#3b82f6')

            # ── Título con fade-in
            titulo_wrap = textwrap.fill(titulo[:110], width=22)
            y = 90
            for linea in titulo_wrap.split('\n'):
                tmp = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                ImageDraw.Draw(tmp).text((20, y), linea, font=font_tit,
                                         fill=(255, 255, 255, alpha))
                frame = Image.alpha_composite(frame.convert('RGBA'), tmp).convert('RGB')
                draw  = ImageDraw.Draw(frame)
                y += 56

            # ── Separador
            sep_y = y + 10
            draw.rectangle([(20, sep_y), (mitad - 30, sep_y + 2)], fill='#3b82f6')

            # ── Resumen con fade-in retardado
            if progreso > 0.5:
                alpha2 = int(255 * min((progreso - 0.5) * 2, 1.0))
                res_c  = resumen[:200] + ('...' if len(resumen) > 200 else '')
                tmp2   = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                ImageDraw.Draw(tmp2).text((20, sep_y + 14),
                    textwrap.fill(res_c, width=38),
                    font=font_res, fill=(203, 213, 225, alpha2))
                frame = Image.alpha_composite(frame.convert('RGBA'), tmp2).convert('RGB')
                draw  = ImageDraw.Draw(frame)

            # ── Barra inferior logo
            draw.rectangle([(0, alto - 44), (ancho, alto)], fill='#1e293b')
            draw.text((20, alto - 30), "  Verdad Hoy | Agencia de Noticias  •  noticias internacionales",
                      font=font_log, fill='#94a3b8')

            frames.append(np.array(frame))

        # ── 5. Ensamblar video + audio ─────────────────────
        clip      = ImageSequenceClip(frames, fps=fps)
        hash_v    = generar_hash(titulo)
        video_path = f'/tmp/noticia_video_{hash_v}.mp4'

        if audio_path and os.path.exists(audio_path):
            try:
                # FIX: recortar audio a duración del video - 0.3s para evitar error de límite
                audio_clip = AudioFileClip(audio_path)
                safe_dur   = min(audio_clip.duration - 0.3, duracion - 0.3)
                audio_clip = audio_clip.subclip(0, max(1.0, safe_dur))
                clip       = clip.set_audio(audio_clip)
                clip.write_videofile(
                    video_path,
                    codec='libx264',
                    audio_codec='aac',
                    preset='ultrafast',
                    ffmpeg_params=['-crf', '28'],
                    logger=None,
                )
                audio_clip.close()
                log("🔊 Audio mezclado correctamente en el video", 'exito')
            except Exception as e:
                log(f"⚠️ Error mezclando audio: {e} — generando sin audio", 'advertencia')
                clip.write_videofile(
                    video_path, codec='libx264', audio=False,
                    preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None,
                )
            finally:
                try:
                    os.remove(audio_path)
                except:
                    pass
        else:
            clip.write_videofile(
                video_path, codec='libx264', audio=False,
                preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None,
            )

        clip.close()
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log(f"✅ Video generado: {video_path} ({size_mb:.1f} MB, {duracion}s)", 'exito')
        return video_path

    except ImportError:
        log("⚠️ moviepy no disponible — usando imagen", 'advertencia')
        return None
    except Exception as e:
        log(f"⚠️ Error generando video: {e} — usando imagen", 'advertencia')
        return None


def _truncar_mensaje(texto, hashtags, firma, limite=60000):
    """Trunca el mensaje al límite real de Facebook (63.206 chars) conservando hashtags y firma."""
    sufijo = f"\n\n{hashtags}\n\n— {firma}"
    espacio = limite - len(sufijo)
    if len(texto) > espacio:
        texto = texto[:espacio - 4].rsplit(' ', 1)[0] + ' [...]'
    return re.sub(r'https?://\S+', '', f"{texto}{sufijo}")

def publicar_facebook_video(titulo, texto, video_path, hashtags):
    """Publica un video nativo en Facebook (mayor alcance orgánico que fotos)."""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    descripcion = _truncar_mensaje(texto, hashtags, "🌐 Verdad Hoy | Agencia de Noticias Internacionales")
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
        with open(video_path, 'rb') as f:
            r = requests.post(
                url,
                files={'source': ('video.mp4', f, 'video/mp4')},
                data={
                    'title':        titulo[:255],
                    'description':  descripcion,
                    'access_token': FB_ACCESS_TOKEN,
                },
                timeout=120,
            ).json()
        if 'id' in r:
            log(f"✅ Video publicado en Facebook — ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook video: {r.get('error', {}).get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando video: {e}", 'error')
    return False


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
    return parrafos[:20]

def construir_publicacion(titulo, contenido, creditos, fuente):
    t    = limpiar_texto(titulo)
    pars = dividir_parrafos(contenido)
    if len(pars) < 2:
        ors  = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        pars = [' '.join(ors[i:i+2]) for i in range(0, len(ors), 2)][:20]
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
    mensaje = _truncar_mensaje(texto, hashtags, "🌐 Verdad Hoy | Agencia de Noticias Internacionales")
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
    print("🌍 BOT DE NOTICIAS - V5.0 (ENGAGEMENT OPTIMIZADO)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Historial: {os.path.abspath(HISTORIAL_PATH)}")
    print(f"📁 Estado:    {os.path.abspath(ESTADO_PATH)}")
    print("=" * 60)

    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR CRÍTICO: Faltan credenciales Facebook (FB_PAGE_ID / FB_ACCESS_TOKEN)", 'error')
        return False  # Error real — exit 1

    # Control de tiempo — PRIMERA barrera (salida normal — exit 0)
    if not verificar_tiempo():
        return None

    # Control de horario pico — SEGUNDA barrera (salida normal — exit 0)
    if not esta_en_horario_pico():
        return None

    # Cargar historial
    h = cargar_historial()
    total_historial = len(h.get('urls', []))
    log(f"📊 Historial: {total_historial} entradas | Permanentes: {len(h.get('hashes_permanentes', []))}")

    # Control de límite diario — TERCERA barrera (salida normal — exit 0)
    if limite_diario_alcanzado(h):
        return None

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
    pub = agregar_cta(pub, seleccionada['titulo'], seleccionada.get('descripcion', ''))  # V5: CTA temático
    ht  = generar_hashtags(seleccionada['titulo'], contenido)

    # Imagen (usada como fondo del video o fallback)
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

    # ── Intentar publicar como VIDEO (mayor alcance) ──────
    resumen_video = contenido[:300] if contenido else seleccionada.get('descripcion', '')
    video_path = crear_video_noticia(
        titulo=seleccionada['titulo'],
        resumen=resumen_video,
        fondo_path=img_path,
    )

    ok = False
    if video_path:
        log("📹 Publicando como VIDEO nativo...", 'info')
        ok = publicar_facebook_video(seleccionada['titulo'], pub, video_path, ht)
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
        except:
            pass

    # ── Fallback a IMAGEN si el video falló ───────────────
    if not ok:
        log("🖼️  Fallback: publicando como imagen...", 'advertencia')
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
        resultado = main()
        # None = salida normal (tiempo, horario, límite diario) → exit 0
        # True = publicación exitosa → exit 0
        # False = error real → exit 1
        exit(0 if resultado is not False else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
