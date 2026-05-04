#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales - V6.0
NUEVO EN V6:
  - Publica PRIMERO en WordPress (cada 30 min, todo el día)
  - Luego publica en Facebook (8 veces/día, solo horario pico)
  - Link de verdadhoy.com incluido en cada post de Facebook
  - Imagen OBLIGATORIA para publicar (no se publica sin imagen)
  - Categorías sincronizadas con WordPress
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

# ── NUEVO V6: WordPress ────────────────────────────────────
WP_URL             = os.getenv('WP_URL', 'https://verdadhoy.com')
WP_USER            = os.getenv('WP_USER', 'verdadhoy_admin')
WP_APP_PASSWORD    = os.getenv('WP_APP_PASSWORD', '')

# RUTAS
HISTORIAL_PATH     = os.getenv('HISTORIAL_PATH', 'historial_publicaciones.json')
ESTADO_PATH        = os.getenv('ESTADO_PATH',    'estado_bot.json')
ESTADO_WP_PATH     = 'estado_wp.json'   # control separado para WordPress
ESTADO_FB_PATH     = 'estado_fb.json'   # control separado para Facebook

# Tiempos
TIEMPO_ENTRE_WP_MIN    = 30   # WordPress: cada 30 minutos
TIEMPO_ENTRE_FB_MIN    = 55   # Facebook: mínimo 55 min entre posts
UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 300
DIAS_HISTORIAL             = 14

# ── ENGAGEMENT ─────────────────────────────────────────────
MAX_POSTS_FB_DIA  = 8   # Facebook: máximo 8/día
MAX_POSTS_WP_DIA  = 48  # WordPress: máximo 48/día (cada 30 min)

# Horarios pico Facebook (hora UTC) — solo para RRSS
HORARIOS_PICO_UTC = [
    (0, 4),
    (10, 14),
    (17, 22),
]

# ── CATEGORÍAS WORDPRESS ────────────────────────────────────
# Deben coincidir con los slugs que creaste en WordPress
CATEGORIA_WP = {
    'guerra':       'internacional',
    'politica':     'politica',
    'economia':     'economia',
    'tecnologia':   'tecnologia',
    'desastre':     'internacional',
    'deportes':     'deportes',
    'ciencia':      'ciencia-y-salud',
    'general':      'internacional',
}

# IDs de categorías WordPress (se obtienen automáticamente al publicar)
_cache_categorias_wp = {}

# CTAs por tema para Facebook
CTAS_POR_TEMA = {
    'guerra': [
        "¿Crees que esto puede escalar a un conflicto mayor? Dinos abajo 👇",
        "¿Qué solución ves a este conflicto? Comenta 👇",
        "¿El mundo está haciendo suficiente? Tu opinión importa 👇",
    ],
    'politica': [
        "¿Estás de acuerdo con esta decisión? Comenta SÍ o NO 👇",
        "¿Qué opinas de esta medida? Tu voz cuenta 👇",
        "¿Cómo crees que afectará esto a la región? Dinos 👇",
    ],
    'economia': [
        "¿Sientes esto en tu bolsillo? Cuéntanos 👇",
        "¿Cómo te afecta esta situación económica? Comenta 👇",
        "¿Crees que mejorará la economía? SÍ o NO 👇",
    ],
    'tecnologia': [
        "¿La IA nos ayuda o nos amenaza? Comenta 👇",
        "¿Usarías esta tecnología? Dinos 👇",
        "¿El futuro te emociona o te preocupa? Opina 👇",
    ],
    'desastre': [
        "Nuestros pensamientos con los afectados 🙏 Comenta abajo 👇",
        "¿Cómo podemos ayudar en situaciones así? Opina 👇",
    ],
    'general': [
        "¿Qué piensas de esta noticia? Comenta abajo 👇",
        "¿Sabías esto? Dinos SÍ o NO 👇",
        "Comparte si crees que todos deben saberlo 🔁",
    ],
}

CTAS_VIDEO_POR_TEMA = {
    'guerra':     "¿Crees que esto escalará?",
    'politica':   "¿Estás de acuerdo?  SÍ o NO",
    'economia':   "¿Te afecta esto?",
    'tecnologia': "¿A favor o en contra?",
    'desastre':   "Deja tu mensaje de apoyo 🙏",
    'general':    "¿Qué opinas de esta noticia?",
}

CTA_VIDEO_CIERRE = "💬 Comenta · 👍 Reacciona · 🔁 Comparte\nMás detalles en la descripción 👇"

VOCES_TTS = [
    "es-MX-DaliaNeural",
    "es-MX-JorgeNeural",
    "es-CO-SalomeNeural",
    "es-AR-ElenaNeural",
]

# ──────────────────────────────────────────────────────────
# DETECCIÓN DE TEMA
# ──────────────────────────────────────────────────────────
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
    if any(p in txt for p in ["futbol", "deporte", "olimpiadas", "mundial", "copa",
                               "atletismo", "tenis", "baloncesto", "nba", "fifa"]):
        return 'deportes'
    if any(p in txt for p in ["salud", "medicina", "ciencia", "investigacion",
                               "vacuna", "virus", "cancer", "enfermedad"]):
        return 'ciencia'
    return 'general'

def agregar_cta(texto, titulo="", descripcion=""):
    tema = detectar_tema(titulo, descripcion)
    cta  = random.choice(CTAS_POR_TEMA.get(tema, CTAS_POR_TEMA['general']))
    return f"{texto}\n\n{cta}"

def obtener_cta_video(titulo, descripcion=""):
    tema      = detectar_tema(titulo, descripcion)
    linea_cta = CTAS_VIDEO_POR_TEMA.get(tema, CTAS_VIDEO_POR_TEMA['general'])
    return linea_cta, CTA_VIDEO_CIERRE

def obtener_voz_aleatoria():
    voz = random.choice(VOCES_TTS)
    log(f"🎙️ Voz seleccionada: {voz}", 'info')
    return voz

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
    "putin", "zelensky", "trump", "biden", "netanyahu",
    "xi jinping", "kim jong un", "macron",
    "hamas", "hezbollah", "isis", "taliban", "houthis",
    "elon musk",
]

PALABRAS_MEDIA_PRIORIDAD = [
    "economia", "mercados", "FMI", "banco mundial",
    "tecnologia", "innovacion", "salud", "educacion",
    "medio ambiente", "cambio climatico",
    "comercio internacional", "empresas",
]

# ──────────────────────────────────────────────────────────
# UTILIDADES
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
# HISTORIAL
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
    'estadisticas': {'total_publicadas': 0, 'total_wp': 0, 'total_fb': 0}
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
    if len(h.get('hashes_permanentes', [])) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]

def noticia_ya_publicada(h, url, titulo, desc=""):
    if es_titulo_generico(titulo):
        return True, "titulo_generico"
    url_n   = normalizar_url(url)
    hash_t  = generar_hash(titulo)
    hash_d  = generar_hash(desc) if desc else ""
    dominio = extraer_dominio(url)
    if url_n in h.get('urls_normalizadas', []):
        return True, "url_duplicada"
    todos_hashes = set(h.get('hashes', [])) | set(h.get('hashes_permanentes', []))
    if hash_t in todos_hashes:
        return True, "hash_titulo"
    if hash_d and hash_d in h.get('hashes_contenido', []):
        return True, "hash_contenido"
    for th in h.get('titulos', []):
        if not isinstance(th, str):
            continue
        sim = similitud_titulos(titulo, th)
        if sim >= UMBRAL_SIMILITUD_TITULO:
            return True, f"titulo_similar_{sim:.2f}"
    for i, uh in enumerate(h.get('urls', [])):
        if extraer_dominio(uh) == dominio and i < len(h.get('titulos', [])):
            sim = similitud_titulos(titulo, h['titulos'][i])
            if sim >= 0.82:
                return True, f"mismo_sitio_{sim:.2f}"
    if desc:
        for dh in h.get('descripciones', []):
            if isinstance(dh, str) and dh:
                if similitud_contenido(desc, dh, 150) >= UMBRAL_SIMILITUD_CONTENIDO:
                    return True, "descripcion_similar"
    return False, "nuevo"

def guardar_en_historial(h, url, titulo, desc=""):
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)
    if url_n in h.get('urls_normalizadas', []):
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
    for k in ['urls', 'urls_normalizadas', 'hashes', 'timestamps',
              'titulos', 'descripciones', 'hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA:
            h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    if len(h['hashes_permanentes']) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]
    if guardar_json(HISTORIAL_PATH, h):
        log(f"💾 Historial guardado: {len(h['urls'])} entradas", 'exito')
    return h

# ──────────────────────────────────────────────────────────
# CONTROL DE TIEMPO — SEPARADO PARA WP Y FB
# ──────────────────────────────────────────────────────────
def puede_publicar_wp():
    """WordPress: cada 30 minutos, todo el día."""
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True
    e = cargar_json(ESTADO_WP_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u:
        return True
    try:
        minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_WP_MIN:
            log(f"⏱️ WP: publicado hace {minutos:.0f} min — mínimo {TIEMPO_ENTRE_WP_MIN} min", 'info')
            return False
    except:
        pass
    return True

def puede_publicar_fb(h):
    """Facebook: solo en horario pico + máximo 8/día + mínimo 55 min entre posts."""
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True

    # Control horario pico
    hora_utc = datetime.utcnow().hour
    en_pico = any(inicio <= hora_utc < fin for inicio, fin in HORARIOS_PICO_UTC)
    if not en_pico:
        log(f"⏰ FB: fuera de horario pico (UTC {hora_utc:02d}h)", 'info')
        return False

    # Control límite diario
    hoy = datetime.now().date()
    posts_hoy = sum(
        1 for ts in h.get('timestamps', [])
        if ts and datetime.fromisoformat(ts).date() == hoy
    )
    if posts_hoy >= MAX_POSTS_FB_DIA:
        log(f"🚫 FB: límite diario alcanzado ({posts_hoy}/{MAX_POSTS_FB_DIA})", 'advertencia')
        return False

    # Control tiempo mínimo entre posts
    e = cargar_json(ESTADO_FB_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if u:
        try:
            minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
            if minutos < TIEMPO_ENTRE_FB_MIN:
                log(f"⏱️ FB: publicado hace {minutos:.0f} min — mínimo {TIEMPO_ENTRE_FB_MIN} min", 'info')
                return False
        except:
            pass

    log(f"✅ FB: en horario pico, {posts_hoy}/{MAX_POSTS_FB_DIA} posts hoy", 'info')
    return True

def guardar_estado_wp():
    guardar_json(ESTADO_WP_PATH, {'ultima_publicacion': datetime.now().isoformat()})

def guardar_estado_fb():
    guardar_json(ESTADO_FB_PATH, {'ultima_publicacion': datetime.now().isoformat()})

# ──────────────────────────────────────────────────────────
# NUEVO V6: PUBLICAR EN WORDPRESS
# ──────────────────────────────────────────────────────────
def obtener_id_categoria_wp(slug_categoria):
    """Obtiene el ID de una categoría de WordPress por su slug."""
    global _cache_categorias_wp
    if slug_categoria in _cache_categorias_wp:
        return _cache_categorias_wp[slug_categoria]
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories",
            params={'slug': slug_categoria, 'per_page': 1},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=15
        ).json()
        if r and isinstance(r, list) and len(r) > 0:
            cat_id = r[0]['id']
            _cache_categorias_wp[slug_categoria] = cat_id
            log(f"📂 Categoría WP '{slug_categoria}' → ID {cat_id}", 'info')
            return cat_id
    except Exception as e:
        log(f"⚠️ Error obteniendo categoría WP '{slug_categoria}': {e}", 'advertencia')
    return None

def subir_imagen_wp(imagen_path, titulo):
    """Sube una imagen a la biblioteca de medios de WordPress."""
    if not imagen_path or not os.path.exists(imagen_path):
        return None
    try:
        nombre_archivo = f"noticia-{generar_hash(titulo)}.jpg"
        with open(imagen_path, 'rb') as f:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media",
                headers={
                    'Content-Disposition': f'attachment; filename="{nombre_archivo}"',
                    'Content-Type': 'image/jpeg',
                },
                data=f.read(),
                auth=(WP_USER, WP_APP_PASSWORD),
                timeout=60
            ).json()
        if 'id' in r:
            log(f"🖼️ Imagen subida a WP — ID: {r['id']}", 'exito')
            return r['id']
        else:
            log(f"⚠️ Error subiendo imagen a WP: {r.get('message', 'desconocido')}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Excepción subiendo imagen WP: {e}", 'advertencia')
    return None

def publicar_en_wordpress(titulo, contenido, tema, imagen_path, fuente_url):
    """
    Publica una noticia en WordPress y retorna la URL del artículo.
    REQUIERE imagen obligatoriamente.
    """
    if not WP_APP_PASSWORD:
        log("⚠️ WP_APP_PASSWORD no configurado — saltando WordPress", 'advertencia')
        return None

    if not imagen_path:
        log("❌ No hay imagen — no se publica en WordPress", 'error')
        return None

    # Subir imagen primero
    imagen_id = subir_imagen_wp(imagen_path, titulo)
    if not imagen_id:
        log("❌ No se pudo subir imagen a WP — cancelando", 'error')
        return None

    # Obtener categoría
    slug_cat = CATEGORIA_WP.get(tema, 'internacional')
    cat_id   = obtener_id_categoria_wp(slug_cat)
    categorias = [cat_id] if cat_id else []

    # Construir contenido HTML para WordPress
    contenido_html = f"""
<p>{contenido[:2000]}</p>

<hr>
<p><strong>Fuente original:</strong> <a href="{fuente_url}" target="_blank" rel="nofollow noopener">{fuente_url}</a></p>
<p><em>Información verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
"""

    # Datos del post
    post_data = {
        'title':          titulo,
        'content':        contenido_html,
        'status':         'publish',
        'featured_media': imagen_id,
        'categories':     categorias,
        'meta': {
            '_yoast_wpseo_metadesc': contenido[:155],  # Meta descripción para SEO
        }
    }

    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        ).json()

        if 'id' in r:
            url_articulo = r.get('link', f"{WP_URL}/?p={r['id']}")
            log(f"✅ Publicado en WordPress — ID: {r['id']} | URL: {url_articulo}", 'exito')
            return url_articulo
        else:
            log(f"❌ Error WordPress: {r.get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando en WP: {e}", 'error')

    return None

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
    topicos = ['world', 'nation', 'business', 'technology', 'sports', 'health']
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
# DEDUPLICACIÓN
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
            return None
        ct = r.headers.get('content-type', '')
        if 'image' not in ct and 'octet' not in ct:
            return None
        data = r.content
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 200 or h < 150:
            return None
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.thumbnail((1280, 1280))
        # Agregar watermark verdadhoy.com
        img = agregar_watermark(img, posicion='esquina_inferior_derecha')
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=88)
        if os.path.getsize(p) < 3000:
            os.remove(p)
            return None
        log(f"🖼️ Imagen descargada con watermark: {w}x{h}", 'debug')
        return p
    except Exception as e:
        log(f"⚠️ Error descargando imagen: {e}", 'debug')
        return None

def agregar_watermark(img, posicion='esquina_inferior_derecha'):
    """
    Agrega watermark 'verdadhoy.com' a una imagen PIL.
    Posiciones: esquina_inferior_derecha, esquina_inferior_izquierda,
                esquina_superior_derecha, esquina_superior_izquierda
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        ancho, alto = img.size

        # Fuente para el watermark
        try:
            font_wm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except:
            font_wm = ImageFont.load_default()

        texto_wm = "verdadhoy.com"

        # Calcular tamaño del texto
        try:
            bbox = draw.textbbox((0, 0), texto_wm, font=font_wm)
            txt_w = bbox[2] - bbox[0]
            txt_h = bbox[3] - bbox[1]
        except:
            txt_w, txt_h = 140, 20

        margen = 14
        padding = 6

        # Calcular posición
        if posicion == 'esquina_inferior_derecha':
            x = ancho - txt_w - margen - padding * 2
            y = alto - txt_h - margen - padding * 2
        elif posicion == 'esquina_inferior_izquierda':
            x = margen
            y = alto - txt_h - margen - padding * 2
        elif posicion == 'esquina_superior_derecha':
            x = ancho - txt_w - margen - padding * 2
            y = margen
        else:  # superior izquierda
            x = margen
            y = margen

        # Fondo semitransparente detrás del texto
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [x - padding, y - padding,
             x + txt_w + padding, y + txt_h + padding],
            radius=4,
            fill=(0, 0, 0, 160)  # negro semitransparente
        )
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')

        # Texto del watermark
        draw = ImageDraw.Draw(img)
        # Sombra
        draw.text((x + 1, y + 1), texto_wm, font=font_wm, fill=(0, 0, 0, 180))
        # Texto principal en dorado
        draw.text((x, y), texto_wm, font=font_wm, fill='#f5c518')

        return img
    except Exception as e:
        log(f"⚠️ Error agregando watermark: {e}", 'debug')
        return img

def aplicar_watermark_a_archivo(imagen_path):
    """Aplica watermark a un archivo de imagen y lo guarda en el mismo path."""
    try:
        from PIL import Image
        img = Image.open(imagen_path).convert('RGB')
        img = agregar_watermark(img, posicion='esquina_inferior_derecha')
        img.save(imagen_path, 'JPEG', quality=88)
        log("🏷️ Watermark agregado a imagen", 'exito')
        return imagen_path
    except Exception as e:
        log(f"⚠️ Error aplicando watermark: {e}", 'debug')
        return imagen_path

def crear_imagen_titulo(titulo):
    """Genera imagen de respaldo con el título — solo si no hay imagen real."""
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
        draw.text((60, 580), "Verdad Hoy • Tu fuente confiable", font=fs, fill='#64748b')
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        # Watermark antes de guardar
        img = agregar_watermark(img, posicion='esquina_inferior_derecha')
        img.save(p, 'JPEG', quality=90)
        log("🖼️ Imagen generada desde título (fallback)", 'advertencia')
        return p
    except:
        return None

# ──────────────────────────────────────────────────────────
# CONSTRUCCIÓN DEL POST FACEBOOK
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

def construir_publicacion_fb(titulo, contenido, fuente, url_wp):
    """Construye el texto del post de Facebook con link a WordPress."""
    t    = limpiar_texto(titulo)
    pars = dividir_parrafos(contenido)
    if len(pars) < 2:
        ors  = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        pars = [' '.join(ors[i:i+2]) for i in range(0, len(ors), 2)][:20]
    lineas = [f"📰 ÚLTIMA HORA | {t}", ""]
    for i, p in enumerate(pars[:3]):  # Máximo 3 párrafos en Facebook
        lineas.append(p)
        if i < 2:
            lineas.append("")
    lineas += [
        "",
        "──────────────────────────────",
        "",
        f"🔗 Lee la nota completa aquí:",
        f"👉 {url_wp}",
        "",
        f"📎 {fuente}",
    ]
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
    tags.append('#VerdadHoy #Mundo')
    return ' '.join(tags)

def _truncar_mensaje(texto, hashtags, firma, limite=60000):
    sufijo = f"\n\n{hashtags}\n\n— {firma}"
    espacio = limite - len(sufijo)
    if len(texto) > espacio:
        texto = texto[:espacio - 4].rsplit(' ', 1)[0] + ' [...]'
    return f"{texto}{sufijo}"

# ──────────────────────────────────────────────────────────
# GENERACIÓN DE VIDEO
# ──────────────────────────────────────────────────────────
def crear_video_noticia(titulo, resumen, fondo_path=None):
    """Genera un video MP4 con el titular y resumen de la noticia."""
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
        import textwrap
        import numpy as np

        duracion = 30
        fps      = 24
        ancho, alto = 1280, 720
        mitad = ancho // 2

        def cargar_fuente(paths, size):
            for p in paths:
                try:
                    from PIL import ImageFont
                    return ImageFont.truetype(p, size)
                except:
                    continue
            from PIL import ImageFont
            return ImageFont.load_default()

        font_paths     = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        font_paths_reg = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        font_breaking  = cargar_fuente(font_paths, 24)
        font_titulo    = cargar_fuente(font_paths, 44)
        font_resumen   = cargar_fuente(font_paths_reg, 24)

        def crear_frame_pil(progreso=1.0):
            frame = Image.new('RGB', (ancho, alto), '#0d1117')
            if fondo_path and os.path.exists(fondo_path):
                try:
                    img = Image.open(fondo_path).convert('RGB')
                    img_ratio = img.width / img.height
                    target_ratio = mitad / alto
                    if img_ratio > target_ratio:
                        new_h, new_w = alto, int(alto * img_ratio)
                    else:
                        new_w, new_h = mitad, int(mitad / img_ratio)
                    img = img.resize((new_w, new_h), Image.LANCZOS)
                    x = (new_w - mitad) // 2
                    y = (new_h - alto) // 2
                    img = img.crop((x, y, x + mitad, y + alto))
                    img = ImageEnhance.Sharpness(img).enhance(1.4)
                    frame.paste(img, (mitad, 0))
                except:
                    pass
            panel = Image.new('RGB', (mitad + 40, alto), '#0d1117')
            frame.paste(panel, (0, 0))
            draw = ImageDraw.Draw(frame)
            draw.rectangle([(0, 0), (ancho, 52)], fill='#dc2626')
            draw.text((20, 14), "  ÚLTIMA HORA  |  VERDAD HOY", font=font_breaking, fill='white')
            draw.rectangle([(20, 68), (mitad - 20, 71)], fill='#3b82f6')
            titulo_wrap = textwrap.fill(titulo[:110], width=22)
            y_t = 90
            for linea in titulo_wrap.split('\n'):
                draw.text((20, y_t), linea, font=font_titulo, fill='white')
                y_t += 52
            y_r = y_t + 20
            resumen_wrap = textwrap.fill(resumen[:200], width=34)
            for linea in resumen_wrap.split('\n'):
                if y_r < alto - 120:
                    draw.text((20, y_r), linea, font=font_resumen, fill='#94a3b8')
                    y_r += 32
            # Panel CTA inferior
            draw.rectangle([(0, alto - 90), (ancho, alto)], fill='#dc2626')
            cta_tema, cta_cierre = obtener_cta_video(titulo)
            draw.text((20, alto - 80), cta_tema, font=font_resumen, fill='white')
            draw.text((20, alto - 48), "verdadhoy.com", font=font_resumen, fill='#fbbf24')
            return np.array(frame)

        frames = [crear_frame_pil(progreso=t/duracion) for t in range(duracion * fps)]
        clip = ImageClip(frames[0]).set_duration(duracion)

        video_path = f'/tmp/video_{generar_hash(titulo)}.mp4'

        # Intentar agregar audio TTS
        audio_path = None
        try:
            import edge_tts
            import asyncio
            voz = obtener_voz_aleatoria()
            texto_tts = f"{titulo}. {resumen[:300]}"
            audio_path = f'/tmp/audio_{generar_hash(titulo)}.mp3'

            async def generar_audio():
                comunicar = edge_tts.Communicate(texto_tts, voz)
                await comunicar.save(audio_path)

            asyncio.run(generar_audio())
            log("🎙️ Audio TTS generado", 'exito')
        except Exception as e:
            log(f"⚠️ TTS no disponible: {e} — video sin audio", 'advertencia')
            audio_path = None

        if audio_path and os.path.exists(audio_path):
            try:
                audio_clip = AudioFileClip(audio_path).subclip(0, duracion)
                clip = clip.set_audio(audio_clip)
                clip.write_videofile(video_path, codec='libx264', audio_codec='aac',
                                     preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)
                audio_clip.close()
            except:
                clip.write_videofile(video_path, codec='libx264', audio=False,
                                     preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)
            finally:
                try:
                    os.remove(audio_path)
                except:
                    pass
        else:
            clip.write_videofile(video_path, codec='libx264', audio=False,
                                 preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)

        clip.close()
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log(f"✅ Video generado: {size_mb:.1f} MB, {duracion}s", 'exito')
        return video_path

    except ImportError:
        log("⚠️ moviepy no disponible — usando imagen", 'advertencia')
        return None
    except Exception as e:
        log(f"⚠️ Error generando video: {e}", 'advertencia')
        return None

# ──────────────────────────────────────────────────────────
# PUBLICACIÓN EN FACEBOOK
# ──────────────────────────────────────────────────────────
def publicar_facebook_video(titulo, texto, video_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    descripcion = _truncar_mensaje(texto, hashtags, "🌐 Verdad Hoy | verdadhoy.com")
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
        with open(video_path, 'rb') as f:
            r = requests.post(
                url,
                files={'source': ('video.mp4', f, 'video/mp4')},
                data={'title': titulo[:255], 'description': descripcion,
                      'access_token': FB_ACCESS_TOKEN},
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

def publicar_facebook_imagen(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    mensaje = _truncar_mensaje(texto, hashtags, "🌐 Verdad Hoy | verdadhoy.com")
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
            log(f"✅ Imagen publicada en Facebook — ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook imagen: {r.get('error', {}).get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando imagen: {e}", 'error')
    return False

# ──────────────────────────────────────────────────────────
# MAIN — FLUJO PRINCIPAL V6
# ──────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("🌍 BOT DE NOTICIAS - V6.0 (WordPress + Facebook)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Verificar qué debe publicarse en esta ejecución
    publicar_wp = puede_publicar_wp()
    h = cargar_historial()
    publicar_fb = puede_publicar_fb(h)

    if not publicar_wp and not publicar_fb:
        log("⏱️ Nada que publicar en esta ejecución — esperando próximo ciclo", 'info')
        return None

    log(f"📋 Tareas: WordPress={'SÍ' if publicar_wp else 'NO'} | Facebook={'SÍ' if publicar_fb else 'NO'}", 'info')

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

    noticias = deduplicar_batch(noticias)
    noticias.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    log(f"📰 Candidatas ordenadas: {len(noticias)}", 'info')

    # Buscar noticia válida CON IMAGEN (obligatoria)
    seleccionada = None
    contenido    = None
    img_path     = None
    intentos     = 0

    for i, nt in enumerate(noticias):
        if intentos >= 60:
            break

        url    = nt.get('url', '')
        titulo = nt.get('titulo', '')
        desc   = nt.get('descripcion', '')

        if not url or not titulo:
            continue

        intentos += 1

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

        # Obtener contenido
        cont_web, _ = extraer_contenido(url)
        if cont_web and len(cont_web) >= 200:
            contenido_ok = cont_web
        elif desc and len(desc) >= 150:
            contenido_ok = desc
        else:
            log(f"   ❌ Contenido insuficiente", 'advertencia')
            continue

        # IMAGEN OBLIGATORIA — buscar en múltiples fuentes
        imagen_encontrada = None
        if nt.get('imagen'):
            imagen_encontrada = descargar_imagen(nt['imagen'])
        if not imagen_encontrada:
            img_url = extraer_imagen_web(url)
            if img_url:
                imagen_encontrada = descargar_imagen(img_url)
        if not imagen_encontrada:
            # Solo en último caso: generar imagen desde título
            imagen_encontrada = crear_imagen_titulo(titulo)

        if not imagen_encontrada:
            log(f"   ❌ Sin imagen disponible — saltando noticia", 'advertencia')
            continue

        log(f"   ✅ Noticia válida con imagen — procesando...")
        seleccionada = nt
        contenido    = contenido_ok
        img_path     = imagen_encontrada
        break

    if not seleccionada:
        log("ERROR: No se encontró ninguna noticia válida con imagen", 'error')
        return False

    log(f"\n📝 SELECCIONADA: {seleccionada['titulo'][:70]}")
    log(f"   Fuente: {seleccionada['fuente']} | Puntaje: {seleccionada.get('puntaje', 0)}")

    tema = detectar_tema(seleccionada['titulo'], seleccionada.get('descripcion', ''))
    log(f"   Tema: {tema}", 'info')

    exito_wp = False
    exito_fb = False
    url_articulo_wp = None

    # ── PASO 1: Publicar en WordPress ─────────────────────
    if publicar_wp:
        log("\n🌐 Publicando en WordPress...", 'info')
        url_articulo_wp = publicar_en_wordpress(
            titulo    = seleccionada['titulo'],
            contenido = contenido,
            tema      = tema,
            imagen_path = img_path,
            fuente_url  = seleccionada['url'],
        )
        if url_articulo_wp:
            exito_wp = True
            guardar_estado_wp()
            h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1
            log(f"✅ WordPress OK: {url_articulo_wp}", 'exito')
        else:
            log("❌ WordPress falló", 'error')

    # ── PASO 2: Publicar en Facebook (con link a WP) ──────
    if publicar_fb:
        log("\n📘 Publicando en Facebook...", 'info')

        # Usar URL de WordPress si existe, si no usar URL original
        link_fb = url_articulo_wp or seleccionada['url']

        pub = construir_publicacion_fb(
            titulo   = seleccionada['titulo'],
            contenido = contenido,
            fuente   = seleccionada['fuente'],
            url_wp   = link_fb,
        )
        pub = agregar_cta(pub, seleccionada['titulo'], seleccionada.get('descripcion', ''))
        ht  = generar_hashtags(seleccionada['titulo'], contenido)

        # Intentar como video
        resumen_video = contenido[:300] if contenido else seleccionada.get('descripcion', '')
        video_path = crear_video_noticia(
            titulo      = seleccionada['titulo'],
            resumen     = resumen_video,
            fondo_path  = img_path,
        )

        if video_path:
            log("📹 Publicando como VIDEO en Facebook...", 'info')
            exito_fb = publicar_facebook_video(seleccionada['titulo'], pub, video_path, ht)
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except:
                pass

        if not exito_fb:
            log("🖼️ Fallback: publicando como imagen en Facebook...", 'advertencia')
            exito_fb = publicar_facebook_imagen(seleccionada['titulo'], pub, img_path, ht)

        if exito_fb:
            guardar_estado_fb()
            h['estadisticas']['total_fb'] = h['estadisticas'].get('total_fb', 0) + 1

    # Limpiar imagen temporal
    try:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
    except:
        pass

    # Guardar historial si algo se publicó
    if exito_wp or exito_fb:
        desc_completa = (seleccionada.get('descripcion', '') + ' ' + contenido[:400]).strip()
        h = guardar_en_historial(h, seleccionada['url'], seleccionada['titulo'], desc_completa)
        total = h.get('estadisticas', {}).get('total_publicadas', 0)
        wp_total = h.get('estadisticas', {}).get('total_wp', 0)
        fb_total = h.get('estadisticas', {}).get('total_fb', 0)
        log(f"\n✅ RESUMEN: Total={total} | WP={wp_total} | FB={fb_total}", 'exito')
        log(f"💡 IMPORTANTE: El workflow debe hacer git push de los archivos JSON", 'advertencia')
        return True
    else:
        log("❌ No se publicó en ninguna plataforma", 'error')
        return False


if __name__ == "__main__":
    try:
        resultado = main()
        exit(0 if resultado is not False else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
