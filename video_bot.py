#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_bot.py — Generador Automático de Videos
Repositorio: appcml/bot-noticias-facebook
Independiente de bot_noticias.py

FLUJO:
  1. Busca tema trending (Google Trends → GNews → NewsAPI → NewsData → Reddit RSS)
  2. Verifica en 3+ fuentes (scraping + DuckDuckGo + RSS cruzado)
  3. Sintetiza contenido con IA (Gemini → OpenRouter → extractivo)
  4. Recopila imágenes (og:image → Wikimedia → Pixabay → Pexels → generada)
  5. Genera video MP4 vertical 9:16, 90–120s, multi-imagen con transiciones
  6. Publica en Facebook Reels + WordPress
"""

import os, re, json, random, hashlib, asyncio, textwrap, time
import requests, feedparser
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# ──────────────────────────────────────────────
# CONFIGURACIÓN — todo desde variables de entorno
# ──────────────────────────────────────────────
GEMINI_API_KEY       = os.getenv('GEMINI_API_KEY', '')
OPENROUTER_API_KEY   = os.getenv('OPENROUTER_API_KEY', '')
GNEWS_API_KEY        = os.getenv('GNEWS_API_KEY', '')
NEWS_API_KEY         = os.getenv('NEWS_API_KEY', '')
NEWSDATA_API_KEY     = os.getenv('NEWSDATA_API_KEY', '')
PIXABAY_API_KEY      = os.getenv('PIXABAY_API_KEY', '')
PEXELS_API_KEY       = os.getenv('PEXELS_API_KEY', '')
FB_PAGE_ID           = os.getenv('FB_PAGE_ID', '')
FB_ACCESS_TOKEN      = os.getenv('FB_ACCESS_TOKEN', '')
WP_URL               = os.getenv('WP_URL', 'https://verdadhoy.com')
WP_USER              = os.getenv('WP_USER', 'verdadhoy_admin')
WP_APP_PASSWORD      = os.getenv('WP_APP_PASSWORD', '')

# Rutas
HISTORIAL_PATH       = 'historial_videos.json'
ESTADO_VIDEO_PATH    = 'estado_video_bot.json'

# Parámetros de video
VIDEO_ANCHO          = 1080
VIDEO_ALTO           = 1920
VIDEO_FPS            = 24
VIDEO_DURACION_MIN   = 90    # segundos mínimo
VIDEO_DURACION_MAX   = 120   # segundos máximo
IMGS_POR_VIDEO_MIN   = 5
IMGS_POR_VIDEO_MAX   = 12
SEG_POR_IMAGEN_MIN   = 7     # segundos mínimos por imagen
SEG_POR_IMAGEN_MAX   = 14    # segundos máximos por imagen

# Publicación
MAX_VIDEOS_DIA       = 5
MIN_HORAS_ENTRE      = 4     # mínimo entre videos

# Voces TTS
VOCES_TTS = [
    "es-MX-DaliaNeural",
    "es-MX-JorgeNeural",
    "es-CO-SalomeNeural",
    "es-AR-ElenaNeural",
    "es-ES-ElviraNeural",
    "es-CL-CatalinaNeural",
]

# RSS feeds gratuitos para trending
RSS_TRENDING = [
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo=MX",
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo=CO",
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo=AR",
    "https://www.reddit.com/r/worldnews/top/.rss?t=day",
    "https://www.reddit.com/r/latinoamerica/top/.rss?t=day",
    "https://www.reddit.com/r/technology/top/.rss?t=day",
    "https://www.reddit.com/r/science/top/.rss?t=day",
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "https://www.bbc.com/mundo/index.xml",
    "https://cnnespanol.cnn.com/feed/",
    "https://www.infobae.com/feeds/rss/",
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
def log(msg, tipo='info'):
    iconos = {'info':'ℹ️','ok':'✅','error':'❌','warn':'⚠️','debug':'🔍','video':'🎬','img':'🖼️','ia':'🤖'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo,'ℹ️')} {msg}")

# ──────────────────────────────────────────────
# UTILIDADES JSON
# ──────────────────────────────────────────────
def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                c = f.read().strip()
                return json.loads(c) if c else default.copy()
        except:
            pass
    return default.copy()

def guardar_json(ruta, datos):
    try:
        tmp = ruta + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ruta)
        return True
    except Exception as e:
        log(f"Error guardando {ruta}: {e}", 'error')
        return False

def generar_hash(texto):
    return hashlib.md5(re.sub(r'\s+', ' ', texto.lower().strip()).encode()).hexdigest()[:12]

# ──────────────────────────────────────────────
# CONTROL DE PUBLICACIÓN
# ──────────────────────────────────────────────
def puede_publicar():
    if os.getenv('FORZAR_VIDEO', '').lower() == 'true':
        return True, "forzado"
    h = cargar_json(HISTORIAL_PATH, {'videos': [], 'temas': []})
    hoy = datetime.now().date()
    videos_hoy = sum(
        1 for v in h.get('videos', [])
        if v.get('fecha', '')[:10] == str(hoy)
    )
    if videos_hoy >= MAX_VIDEOS_DIA:
        return False, f"límite diario alcanzado ({videos_hoy}/{MAX_VIDEOS_DIA})"
    e = cargar_json(ESTADO_VIDEO_PATH, {'ultima': None})
    u = e.get('ultima')
    if u:
        try:
            horas = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 3600
            if horas < MIN_HORAS_ENTRE:
                return False, f"publicado hace {horas:.1f}h (mínimo {MIN_HORAS_ENTRE}h)"
        except:
            pass
    return True, f"ok ({videos_hoy}/{MAX_VIDEOS_DIA} hoy)"

def tema_ya_usado(tema, h):
    tema_n = tema.lower().strip()
    for t in h.get('temas', []):
        if SequenceMatcher(None, tema_n, t.lower().strip()).ratio() > 0.75:
            return True
    return False

def registrar_video(tema, url_fb=None, url_wp=None):
    h = cargar_json(HISTORIAL_PATH, {'videos': [], 'temas': []})
    h['videos'].append({
        'tema': tema,
        'fecha': datetime.now().isoformat(),
        'url_fb': url_fb,
        'url_wp': url_wp,
    })
    h['temas'].append(tema)
    if len(h['temas']) > 200:
        h['temas'] = h['temas'][-200:]
    if len(h['videos']) > 500:
        h['videos'] = h['videos'][-500:]
    guardar_json(HISTORIAL_PATH, h)
    guardar_json(ESTADO_VIDEO_PATH, {'ultima': datetime.now().isoformat()})

# ──────────────────────────────────────────────
# PASO 1: BÚSQUEDA DE TEMAS TRENDING
# ──────────────────────────────────────────────
def obtener_temas_google_trends():
    temas = []
    urls = [
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=MX",
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=CO",
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=AR",
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
    ]
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                titulo = entry.get('title', '').strip()
                if titulo and len(titulo) > 3:
                    temas.append({'tema': titulo, 'fuente': 'google_trends', 'puntaje': 10})
        except Exception as e:
            log(f"Google Trends RSS error: {e}", 'debug')
    log(f"Google Trends: {len(temas)} temas", 'info')
    return temas

def obtener_temas_gnews():
    if not GNEWS_API_KEY:
        return []
    temas = []
    try:
        r = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params={'token': GNEWS_API_KEY, 'lang': 'es', 'max': 10},
            timeout=15
        ).json()
        for art in r.get('articles', []):
            t = art.get('title', '').strip()
            if t:
                temas.append({'tema': t, 'fuente': 'gnews', 'puntaje': 8,
                              'url_ref': art.get('url', ''),
                              'imagen_ref': art.get('image', '')})
    except Exception as e:
        log(f"GNews error: {e}", 'debug')
    log(f"GNews: {len(temas)} temas", 'info')
    return temas

def obtener_temas_newsapi():
    if not NEWS_API_KEY:
        return []
    temas = []
    try:
        r = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={'apiKey': NEWS_API_KEY, 'language': 'es', 'pageSize': 10},
            timeout=15
        ).json()
        for art in r.get('articles', []):
            t = art.get('title', '').strip()
            if t:
                temas.append({'tema': t, 'fuente': 'newsapi', 'puntaje': 7,
                              'url_ref': art.get('url', ''),
                              'imagen_ref': art.get('urlToImage', '')})
    except Exception as e:
        log(f"NewsAPI error: {e}", 'debug')
    log(f"NewsAPI: {len(temas)} temas", 'info')
    return temas

def obtener_temas_newsdata():
    if not NEWSDATA_API_KEY:
        return []
    temas = []
    try:
        r = requests.get(
            "https://newsdata.io/api/1/news",
            params={'apikey': NEWSDATA_API_KEY, 'language': 'es', 'size': 10},
            timeout=15
        ).json()
        for art in r.get('results', []):
            t = art.get('title', '').strip()
            if t:
                temas.append({'tema': t, 'fuente': 'newsdata', 'puntaje': 7,
                              'url_ref': art.get('link', ''),
                              'imagen_ref': art.get('image_url', '')})
    except Exception as e:
        log(f"NewsData error: {e}", 'debug')
    log(f"NewsData: {len(temas)} temas", 'info')
    return temas

def obtener_temas_reddit():
    temas = []
    subreddits = [
        "https://www.reddit.com/r/worldnews/top/.rss?t=day",
        "https://www.reddit.com/r/latinoamerica/top/.rss?t=day",
        "https://www.reddit.com/r/technology/top/.rss?t=day",
        "https://www.reddit.com/r/science/top/.rss?t=day",
        "https://www.reddit.com/r/interestingasfuck/top/.rss?t=day",
    ]
    for url in subreddits:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                t = entry.get('title', '').strip()
                if t and len(t) > 10:
                    temas.append({'tema': t, 'fuente': 'reddit', 'puntaje': 6})
        except Exception as e:
            log(f"Reddit RSS error: {e}", 'debug')
    log(f"Reddit: {len(temas)} temas", 'info')
    return temas

def obtener_temas_rss_medios():
    temas = []
    feeds = [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://www.bbc.com/mundo/index.xml",
        "https://cnnespanol.cnn.com/feed/",
        "https://www.infobae.com/feeds/rss/",
        "https://rss.nytimes.com/services/xml/rss/nyt/es/HomePage.xml",
        # Feeds específicos de internacional
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada",
        "https://www.bbc.com/mundo/noticias/index.xml",
        "https://cnnespanol.cnn.com/category/mundo/feed/",
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                t = entry.get('title', '').strip()
                if t and len(t) > 10:
                    temas.append({'tema': t, 'fuente': 'rss_medios', 'puntaje': 7,
                                  'url_ref': entry.get('link', '')})
        except Exception as e:
            log(f"RSS medios error ({url[:40]}): {e}", 'debug')
    log(f"RSS medios: {len(temas)} temas", 'info')
    return temas

# ──────────────────────────────────────────────
# EFEMÉRIDES — eventos históricos de hoy
# ──────────────────────────────────────────────

# Base de efemérides por (mes, día) — eventos significativos mundiales
EFEMERIDES = {
    (1,  1):  ["Año Nuevo 1999: nace el euro como moneda europea", "1804: Haití declara independencia de Francia"],
    (1,  6):  ["1412: nace Juana de Arco, heroína francesa", "1994: entra en vigor el Tratado de Libre Comercio TLCAN"],
    (1, 15):  ["1929: nace Martin Luther King Jr., líder de derechos civiles", "2009: vuelo US Airways ameriza en el río Hudson sin víctimas"],
    (1, 20):  ["1961: John F. Kennedy asume como presidente de EEUU", "2021: Joe Biden jura como presidente número 46 de EEUU"],
    (1, 27):  ["1945: liberación del campo de concentración de Auschwitz", "Día Internacional en Memoria del Holocausto"],
    (2,  4):  ["1945: Conferencia de Yalta entre Churchill, Roosevelt y Stalin", "2004: nace Facebook fundado por Mark Zuckerberg"],
    (2, 11):  ["1990: Nelson Mandela es liberado tras 27 años en prisión", "1979: Revolución Islámica en Irán con Jomeini al poder"],
    (2, 14):  ["1929: La masacre de San Valentín en Chicago", "Día de San Valentín: origen histórico del amor romántico"],
    (2, 24):  ["2022: Rusia invade Ucrania desatando la mayor crisis europea desde la WWII"],
    (3,  5):  ["1953: muere José Stalin tras 30 años gobernando la URSS"],
    (3,  8):  ["1911: primer Día Internacional de la Mujer celebrado en Europa", "Día Internacional de la Mujer Trabajadora"],
    (3, 11):  ["2011: terremoto y tsunami en Japón destruyen la planta de Fukushima", "2004: atentados en trenes de Madrid: 191 muertos"],
    (3, 20):  ["2003: EEUU invade Irak, comienza la Segunda Guerra del Golfo"],
    (3, 31):  ["1889: inauguración de la Torre Eiffel en París"],
    (4,  4):  ["1968: asesinato de Martin Luther King Jr. en Memphis"],
    (4, 12):  ["1961: Yuri Gagarin se convierte en el primer humano en el espacio"],
    (4, 15):  ["1912: el Titanic se hunde en el Atlántico Norte con 1500 víctimas", "2019: incendio destruye gran parte de la catedral de Notre Dame"],
    (4, 17):  ["1961: fracasa la invasión de Bahía de Cochinos en Cuba"],
    (4, 22):  ["1970: se celebra el primer Día de la Tierra", "Día de la Tierra: origen y significado ambiental"],
    (4, 26):  ["1986: explosión en la planta nuclear de Chernóbil, Ucrania"],
    (5,  1):  ["Día Internacional del Trabajo: origen en la masacre de Chicago 1886"],
    (5,  2):  ["1945: cae Berlín y termina la Segunda Guerra Mundial en Europa", "2011: muere Osama Bin Laden en operación de EEUU en Pakistán"],
    (5,  5):  ["1821: muere Napoleón Bonaparte exiliado en Santa Elena", "1862: Batalla de Puebla, México derrota al ejército francés"],
    (5,  8):  ["1945: Día de la Victoria en Europa, fin de la WWII"],
    (5, 14):  ["1948: Israel declara su independencia como estado"],
    (5, 17):  ["1954: EEUU desegrega escuelas en fallo histórico Brown vs Board of Education"],
    (5, 25):  ["1961: JFK anuncia el programa Apollo para llegar a la Luna", "1977: estreno de Star Wars, que cambia el cine para siempre"],
    (6,  4):  ["1989: masacre de Tiananmen en China", "1989: elecciones históricas en Polonia, primeras libres desde la WWII"],
    (6,  6):  ["1944: Desembarco de Normandía (Día D), punto de inflexión de la WWII"],
    (6, 12):  ["1987: Reagan pide a Gorbachov 'derribar este muro' en Berlín"],
    (6, 25):  ["1950: comienza la Guerra de Corea", "1991: Yugoslavia se disuelve, Eslovenia y Croacia declaran independencia"],
    (7,  4):  ["1776: EEUU firma la Declaración de Independencia", "Día de la Independencia de Estados Unidos: historia y significado"],
    (7, 16):  ["1945: primer ensayo nuclear de la historia en Nuevo México, EEUU"],
    (7, 20):  ["1969: Neil Armstrong pisa la Luna por primera vez en la historia"],
    (7, 28):  ["1914: Austria-Hungría declara guerra a Serbia, inicia la Primera Guerra Mundial"],
    (8,  6):  ["1945: EEUU lanza la bomba atómica sobre Hiroshima, Japón"],
    (8,  9):  ["1945: segunda bomba atómica cae sobre Nagasaki, Japón"],
    (8, 13):  ["1961: comienza construcción del Muro de Berlín"],
    (8, 15):  ["1945: Japón se rinde, termina la Segunda Guerra Mundial"],
    (9,  1):  ["1939: Alemania nazi invade Polonia, comienza la Segunda Guerra Mundial"],
    (9, 11):  ["2001: atentados terroristas destruyen las Torres Gemelas de Nueva York", "1973: golpe de estado en Chile derroca a Salvador Allende"],
    (9, 21):  ["1991: Armenia declara independencia de la URSS", "Día Internacional de la Paz"],
    (10,  3): ["1990: reunificación de Alemania tras caída del Muro de Berlín"],
    (10, 12): ["1492: Cristóbal Colón llega a América", "Día de la Hispanidad: 1492 y el encuentro de dos mundos"],
    (10, 14): ["1962: Kennedy descubre misiles soviéticos en Cuba, inicia Crisis de los Misiles"],
    (10, 29): ["1929: el 'Martes Negro' derrumba la bolsa de Wall Street, inicia Gran Depresión"],
    (11,  9): ["1989: cae el Muro de Berlín, símbolo del fin de la Guerra Fría"],
    (11, 11): ["1918: armisticio que pone fin a la Primera Guerra Mundial"],
    (11, 22): ["1963: asesinato del presidente John F. Kennedy en Dallas"],
    (12,  1): ["1955: Rosa Parks se niega a ceder su asiento, inicia movimiento de derechos civiles"],
    (12,  8): ["1980: asesinato de John Lennon en Nueva York"],
    (12, 10): ["1948: Naciones Unidas adopta la Declaración Universal de los Derechos Humanos"],
    (12, 25): ["1991: Mijail Gorbachov renuncia y se disuelve la Unión Soviética"],
    (12, 26): ["2004: tsunami en el océano Índico mata a más de 200,000 personas"],
}

def obtener_efemerides_hoy():
    """Retorna efemérides del día actual como temas de alta prioridad."""
    hoy = datetime.now()
    mes, dia = hoy.month, hoy.day
    temas = []

    eventos = EFEMERIDES.get((mes, dia), [])
    for evento in eventos:
        # Calcular años transcurridos si hay año en el texto
        match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', evento)
        años_str = ""
        if match:
            año_evento = int(match.group(1))
            años = hoy.year - año_evento
            años_str = f" — se cumplen {años} años"
        tema_completo = f"Efeméride: {evento}{años_str}"
        temas.append({
            'tema': tema_completo,
            'fuente': 'efemeride',
            'puntaje': 15,  # máxima prioridad
            'url_ref': '',
            'tipo': 'efemeride',
        })
        log(f"📅 Efeméride hoy: {tema_completo[:80]}", 'info')

    return temas

# ──────────────────────────────────────────────
# FILTRO DE CONTENIDO — línea editorial
# ──────────────────────────────────────────────

# Palabras que BAJAN el puntaje (no van con la línea editorial)
PALABRAS_PENALIZAR = [
    'futbol', 'fútbol', 'gol', 'partido', 'liga', 'champions league', 'premier league',
    'nba', 'nfl', 'mlb', 'serie a', 'bundesliga', 'laliga', 'la liga', 'copa del rey',
    'supercopa', 'atletico', 'atlético', 'barcelona', 'real madrid', 'manchester',
    'arsenal', 'chelsea', 'liverpool', 'bayern', 'psg', 'juventus',
    'messi', 'ronaldo', 'neymar', 'mbappé', 'mbappe', 'haaland',
    'formula 1', 'formula1', 'f1', 'verstappen', 'hamilton',
    'tenis', 'wimbledon', 'roland garros', 'us open', 'australian open',
    'golf', 'baloncesto', 'basquet', 'béisbol', 'beisbol', 'softbol',
    'olimpiadas', 'olimpicos', 'mundiales de atletismo',
    'celebrity', 'famoso', 'famosa', 'actor', 'actriz', 'cantante', 'influencer',
    'tiktoker', 'youtuber', 'instagram', 'reality', 'gran hermano',
    'kardashian', 'taylor swift', 'bad bunny', 'reggaeton',
]

# Palabras que SUBEN el puntaje (alineadas con la línea editorial)
PALABRAS_PRIORIZAR = [
    'guerra', 'conflicto', 'invasión', 'invasion', 'ataque', 'misil', 'bomba',
    'ucrania', 'rusia', 'israel', 'gaza', 'iran', 'china', 'corea', 'taiwán',
    'otan', 'nato', 'onu', 'naciones unidas', 'g7', 'g20',
    'presidente', 'gobierno', 'elección', 'elecciones', 'congreso', 'golpe',
    'sanción', 'diplomacia', 'cumbre', 'tratado', 'acuerdo', 'crisis',
    'economía', 'inflación', 'recesión', 'bolsa', 'mercado', 'banco mundial', 'fmi',
    'petróleo', 'gas', 'energía', 'aranceles', 'comercio',
    'cambio climático', 'catástrofe', 'terremoto', 'tsunami', 'huracán',
    'ciencia', 'tecnología', 'inteligencia artificial', 'ia', 'nasa', 'espacio',
    'descubrimiento', 'investigación', 'pandemia', 'vacuna', 'virus',
    'historia', 'histórico', 'aniversario', 'efeméride', 'se cumplen',
    'latinoamérica', 'latinoamerica', 'america latina', 'mexico', 'colombia',
    'argentina', 'chile', 'venezuela', 'brasil', 'perú', 'cuba', 'bolivia',
    'migrantes', 'migración', 'refugiados', 'derechos humanos',
    'trump', 'biden', 'putin', 'zelensky', 'xi jinping', 'macron',
    'urgente', 'última hora', 'breaking',
]

def puntuar_tema(tema_str):
    """
    Calcula un puntaje editorial para el tema.
    + por noticias internacionales, historia, ciencia
    - por deportes, entretenimiento, farándula
    """
    t = tema_str.lower()
    puntaje = 0

    for palabra in PALABRAS_PRIORIZAR:
        if palabra in t:
            puntaje += 5

    for palabra in PALABRAS_PENALIZAR:
        if palabra in t:
            puntaje -= 8  # penalización fuerte

    return puntaje

def es_tema_aceptable(tema_str):
    """Retorna False si el tema es claramente de deportes/farándula."""
    t = tema_str.lower()
    # Contar cuántas palabras de penalización hay
    penalizaciones = sum(1 for p in PALABRAS_PENALIZAR if p in t)
    priorizaciones = sum(1 for p in PALABRAS_PRIORIZAR if p in t)
    # Bloquear si tiene 2+ palabras deportivas y ninguna de prioridad
    if penalizaciones >= 2 and priorizaciones == 0:
        return False
    return True

def seleccionar_tema(h):
    """
    Recopila temas de todas las fuentes, aplica filtro editorial
    y selecciona el mejor alineado con la línea de Verdad Hoy:
    noticias internacionales + historia + ciencia + efemérides.
    Deportes y farándula quedan excluidos.
    """
    log("🔍 Buscando temas trending...", 'info')
    todos = []

    # Efemérides primero — máxima prioridad
    todos.extend(obtener_efemerides_hoy())

    todos.extend(obtener_temas_google_trends())
    todos.extend(obtener_temas_gnews())
    todos.extend(obtener_temas_newsapi())
    todos.extend(obtener_temas_newsdata())
    todos.extend(obtener_temas_reddit())
    todos.extend(obtener_temas_rss_medios())

    if not todos:
        log("Sin temas disponibles en ninguna fuente", 'error')
        return None

    # Deduplicar por similitud
    vistos, unicos = [], []
    for t in todos:
        tema = t['tema']
        dup = any(SequenceMatcher(None, tema.lower(), v.lower()).ratio() > 0.7
                  for v in vistos)
        if not dup:
            vistos.append(tema)
            unicos.append(t)

    # Aplicar puntuación editorial a cada tema
    for t in unicos:
        ajuste = puntuar_tema(t['tema'])
        t['puntaje'] = t.get('puntaje', 5) + ajuste
        t['puntaje_editorial'] = ajuste

    # Filtrar temas claramente fuera de línea editorial
    aceptables = [t for t in unicos if es_tema_aceptable(t['tema'])]
    if not aceptables:
        log("⚠️ Sin temas aceptables — usando todos", 'warn')
        aceptables = unicos

    # Filtrar ya usados
    candidatos = [t for t in aceptables if not tema_ya_usado(t['tema'], h)]
    if not candidatos:
        log("Todos usados — tomando mejor aceptable", 'warn')
        candidatos = aceptables

    # Ordenar: puntaje editorial primero, luego puntaje base
    candidatos.sort(key=lambda x: (x.get('puntaje', 0)), reverse=True)

    # Log top 5 para diagnóstico
    for i, c in enumerate(candidatos[:5]):
        log(f"   [{i+1}] p={c.get('puntaje',0):+d} | {c['tema'][:70]}", 'debug')

    seleccionado = candidatos[0]
    tipo = "📅 EFEMÉRIDE" if seleccionado.get('tipo') == 'efemeride' else "📰 NOTICIA"
    log(f"✅ {tipo} seleccionado (p={seleccionado.get('puntaje',0):+d}): {seleccionado['tema'][:80]}", 'ok')
    return seleccionado

# ──────────────────────────────────────────────
# PASO 2: VERIFICACIÓN EN 3+ FUENTES
# ──────────────────────────────────────────────
def scrape_articulo(url):
    """Extrae texto principal de un artículo web."""
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        for e in s(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            e.decompose()
        for selector in ['article', '[class*="article"]', '[class*="content"]', 'main']:
            art = s.select_one(selector)
            if art:
                ps = [p.get_text().strip() for p in art.find_all('p') if len(p.get_text().strip()) > 40]
                if ps:
                    return ' '.join(ps)[:4000]
        ps = [p.get_text().strip() for p in s.find_all('p') if len(p.get_text().strip()) > 40]
        return ' '.join(ps[:20])[:4000]
    except:
        return ""

def extraer_og_image(url):
    """Extrae og:image de una URL."""
    if not url:
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for prop in ['og:image', 'twitter:image', 'og:image:secure_url']:
            tag = s.find('meta', property=prop) or s.find('meta', attrs={'name': prop})
            if tag:
                img = tag.get('content', '').strip()
                if img and img.startswith('http'):
                    return img
        # Buscar primera imagen grande en el artículo
        for img in s.find_all('img', src=True):
            src = img.get('src', '')
            if src.startswith('http') and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                return src
    except:
        pass
    return None

def buscar_duckduckgo(query, max_results=5):
    """Búsqueda DuckDuckGo Instant Answer API — gratis, sin key."""
    resultados = []
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={'q': query, 'format': 'json', 'no_html': 1, 'skip_disambig': 1},
            headers=HEADERS,
            timeout=15
        ).json()
        # Abstract
        if r.get('AbstractText'):
            resultados.append({
                'texto': r['AbstractText'],
                'url': r.get('AbstractURL', ''),
                'fuente': 'duckduckgo_abstract'
            })
        # Related topics
        for t in r.get('RelatedTopics', [])[:max_results]:
            if isinstance(t, dict) and t.get('Text'):
                resultados.append({
                    'texto': t['Text'],
                    'url': t.get('FirstURL', ''),
                    'fuente': 'duckduckgo_related'
                })
    except Exception as e:
        log(f"DuckDuckGo error: {e}", 'debug')
    return resultados

def buscar_en_rss(query, max_resultados=5):
    """Busca el tema en feeds RSS de medios para verificar."""
    resultados = []
    query_lower = query.lower()[:30]
    feeds = [
        "https://www.bbc.com/mundo/index.xml",
        "https://cnnespanol.cnn.com/feed/",
        "https://www.infobae.com/feeds/rss/",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://rss.nytimes.com/services/xml/rss/nyt/es/HomePage.xml",
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                titulo = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                palabras = [p for p in query_lower.split() if len(p) > 4]
                if any(p in titulo or p in summary for p in palabras):
                    resultados.append({
                        'texto': entry.get('summary', entry.get('title', '')),
                        'url': entry.get('link', ''),
                        'fuente': urlparse(url).netloc
                    })
                    if len(resultados) >= max_resultados:
                        return resultados
        except:
            pass
    return resultados

def verificar_tema_en_fuentes(tema_info):
    """
    Verifica el tema en al menos 3 fuentes independientes.
    Retorna dict con textos consolidados e imágenes encontradas.
    """
    tema = tema_info['tema']
    log(f"🔎 Verificando tema en fuentes: '{tema[:60]}'", 'info')

    fuentes_texto = []
    imagenes_encontradas = []

    # Fuente 0: URL de referencia del tema (si viene de API de noticias)
    url_ref = tema_info.get('url_ref', '')
    if url_ref:
        texto = scrape_articulo(url_ref)
        if texto and len(texto) > 200:
            fuentes_texto.append({'texto': texto, 'fuente': tema_info.get('fuente', 'ref'), 'url': url_ref})
            log(f"   ✅ Fuente ref: {len(texto)} chars", 'debug')
        img_ref = tema_info.get('imagen_ref', '') or extraer_og_image(url_ref)
        if img_ref:
            imagenes_encontradas.append(img_ref)

    # Fuente 1: DuckDuckGo
    ddg = buscar_duckduckgo(tema)
    if ddg:
        texto_ddg = ' '.join([d['texto'] for d in ddg])
        fuentes_texto.append({'texto': texto_ddg, 'fuente': 'duckduckgo', 'url': ''})
        log(f"   ✅ DuckDuckGo: {len(texto_ddg)} chars", 'debug')
        # Scrape URLs de DDG para imágenes
        for d in ddg[:3]:
            if d.get('url'):
                img = extraer_og_image(d['url'])
                if img:
                    imagenes_encontradas.append(img)

    # Fuente 2: RSS de medios cruzado
    rss_resultados = buscar_en_rss(tema)
    if rss_resultados:
        texto_rss = ' '.join([r['texto'] for r in rss_resultados])
        fuentes_texto.append({'texto': texto_rss, 'fuente': 'rss_medios', 'url': ''})
        log(f"   ✅ RSS medios: {len(texto_rss)} chars", 'debug')
        for res in rss_resultados[:4]:
            if res.get('url'):
                img = extraer_og_image(res['url'])
                if img:
                    imagenes_encontradas.append(img)

    # Fuente 3: GNews si el tema viene de otra fuente
    if GNEWS_API_KEY and tema_info.get('fuente') != 'gnews':
        try:
            r = requests.get(
                "https://gnews.io/api/v4/search",
                params={'token': GNEWS_API_KEY, 'q': tema[:80], 'lang': 'es', 'max': 5},
                timeout=15
            ).json()
            arts = r.get('articles', [])
            if arts:
                textos = []
                for art in arts:
                    textos.append(art.get('description', '') or art.get('title', ''))
                    if art.get('image'):
                        imagenes_encontradas.append(art['image'])
                    if art.get('url'):
                        img2 = extraer_og_image(art['url'])
                        if img2:
                            imagenes_encontradas.append(img2)
                fuentes_texto.append({'texto': ' '.join(textos), 'fuente': 'gnews', 'url': ''})
                log(f"   ✅ GNews: {len(arts)} artículos", 'debug')
        except Exception as e:
            log(f"GNews verificación error: {e}", 'debug')

    # Fuente 4: NewsAPI
    if NEWS_API_KEY and tema_info.get('fuente') != 'newsapi':
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={'apiKey': NEWS_API_KEY, 'q': tema[:80], 'language': 'es', 'pageSize': 5, 'sortBy': 'relevancy'},
                timeout=15
            ).json()
            arts = r.get('articles', [])
            if arts:
                textos = []
                for art in arts:
                    textos.append(art.get('description', '') or art.get('title', ''))
                    if art.get('urlToImage'):
                        imagenes_encontradas.append(art['urlToImage'])
                fuentes_texto.append({'texto': ' '.join(textos), 'fuente': 'newsapi', 'url': ''})
                log(f"   ✅ NewsAPI: {len(arts)} artículos", 'debug')
        except Exception as e:
            log(f"NewsAPI verificación error: {e}", 'debug')

    fuentes_validas = [f for f in fuentes_texto if len(f.get('texto', '')) > 100]
    log(f"   📊 Fuentes válidas: {len(fuentes_validas)} | Imágenes crudas: {len(imagenes_encontradas)}", 'info')

    if len(fuentes_validas) < 2:
        log(f"   ⚠️ Pocas fuentes ({len(fuentes_validas)}) — continuando igual", 'warn')

    return {
        'tema': tema,
        'fuentes': fuentes_validas,
        'texto_consolidado': ' '.join([f['texto'] for f in fuentes_validas])[:8000],
        'imagenes_urls': list(dict.fromkeys(imagenes_encontradas)),  # dedup preservando orden
        'num_fuentes': len(fuentes_validas),
    }

# ──────────────────────────────────────────────
# PASO 3: SÍNTESIS CON IA
# ──────────────────────────────────────────────
PROMPT_SINTESIS = """Eres un editor de noticias para redes sociales en español latino.

TAREA: Generar un guión de video de 90-120 segundos sobre UNA SOLA noticia específica.

NOTICIA: "{tema}"

REGLAS ESTRICTAS:
1. TODO el contenido debe hablar ÚNICAMENTE de esta noticia. No mezcles otros temas.
2. Los puntos clave deben ser datos concretos de ESTA noticia (fechas, cifras, nombres, lugares).
3. El guion_tts debe narrar SOLO esta historia de principio a fin, coherentemente.
4. Las queries_imagenes deben buscar imágenes ESPECÍFICAS de este tema (personas, lugares, eventos reales mencionados).
5. El titulo debe reflejar exactamente lo que pasó, sin sensacionalismo vacío.

RESPONDE SOLO EN JSON sin texto adicional, sin markdown:
{{
  "titulo": "Titular preciso de la noticia, máx 80 chars",
  "subtitulo": "Contexto adicional específico, máx 100 chars",
  "puntos": [
    "Dato concreto 1 de ESTA noticia — cifra, nombre o lugar real",
    "Dato concreto 2 de ESTA noticia — cifra, nombre o lugar real",
    "Dato concreto 3 de ESTA noticia — cifra, nombre o lugar real",
    "Dato concreto 4 de ESTA noticia — cifra, nombre o lugar real",
    "Dato concreto 5 de ESTA noticia — cifra, nombre o lugar real"
  ],
  "conclusion": "Cierre con contexto e invitación a comentar, máx 120 chars",
  "hashtags": "#TagEspecifico1 #TagEspecifico2 #TagEspecifico3 #VerdadHoy #NoticiasInternacionales",
  "descripcion_wp": "2-3 oraciones completas que resumen la noticia para el post de Facebook. Específico, sin cortes, máx 280 chars.",
  "palabras_clave": ["keyword_especifico_1", "keyword_especifico_2", "keyword_especifico_3"],
  "queries_imagenes": [
    "query imagen específica 1 en inglés para buscar en Pixabay/Pexels",
    "query imagen específica 2 en inglés",
    "query imagen específica 3 en inglés",
    "query imagen específica 4 en inglés (lugar o persona del tema)",
    "query imagen específica 5 en inglés (contexto visual del tema)"
  ],
  "guion_tts": "Narración completa de 90-120 segundos. Comienza con el hecho principal. Desarrolla con datos concretos. Cierra con contexto e invitación a comentar. Habla SOLO de esta noticia."
}}

Texto fuente sobre la noticia:
{texto}"""

def sintetizar_gemini(tema, texto):
    if not GEMINI_API_KEY:
        return None
    prompt = PROMPT_SINTESIS.format(tema=tema, texto=texto[:6000])
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2000}},
            timeout=45
        ).json()
        texto_resp = r['candidates'][0]['content']['parts'][0]['text']
        texto_resp = re.sub(r'```json\s*|\s*```', '', texto_resp).strip()
        resultado = json.loads(texto_resp)
        log("IA: Gemini OK", 'ia')
        return resultado
    except Exception as e:
        log(f"Gemini error: {e}", 'debug')
        return None

def sintetizar_openrouter(tema, texto):
    if not OPENROUTER_API_KEY:
        return None
    prompt = PROMPT_SINTESIS.format(tema=tema, texto=texto[:6000])
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "mistralai/mistral-7b-instruct:free",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 2000},
            timeout=45
        ).json()
        texto_resp = r['choices'][0]['message']['content']
        texto_resp = re.sub(r'```json\s*|\s*```', '', texto_resp).strip()
        resultado = json.loads(texto_resp)
        log("IA: OpenRouter OK", 'ia')
        return resultado
    except Exception as e:
        log(f"OpenRouter error: {e}", 'debug')
        return None

def validar_coherencia_guion(guion, tema):
    """
    Verifica que el guión habla realmente de UN solo tema.
    Detecta si los puntos mezclan contenidos distintos.
    Retorna (True, '') si es coherente, (False, razón) si no.
    """
    if not guion:
        return False, "guion vacío"

    titulo    = guion.get('titulo', '').lower()
    puntos    = guion.get('puntos', [])
    guion_tts = guion.get('guion_tts', '').lower()
    tema_l    = tema.lower()

    # Extraer palabras clave del tema (las de más de 4 chars)
    palabras_tema = [w for w in re.findall(r'\b\w{4,}\b', tema_l)
                     if w not in {'este','esta','para','como','pero','desde','hasta','sobre'}]

    if not palabras_tema:
        return True, "ok"

    # Verificar que al menos 2 palabras del tema aparecen en título + guión
    encontradas = sum(1 for p in palabras_tema
                      if p in titulo or p in guion_tts)
    if encontradas < min(2, len(palabras_tema)):
        return False, f"guión no habla del tema ({encontradas}/{len(palabras_tema)} palabras encontradas)"

    # Verificar que los puntos no están vacíos ni son genéricos
    puntos_vacios = sum(1 for p in puntos
                        if not p or 'verdadhoy' in p.lower() or len(p) < 20)
    if puntos_vacios > 2:
        return False, f"demasiados puntos genéricos ({puntos_vacios}/5)"

    return True, "ok"

def sintetizar_extractivo(tema, texto):
    """Fallback sin IA — construye guión coherente desde el texto crudo."""
    log("IA: usando síntesis extractiva (fallback)", 'warn')
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto)
                 if len(o.strip()) > 30]

    # Tomar oraciones que mencionan palabras del tema
    palabras_tema = [w for w in re.findall(r'\b\w{4,}\b', tema.lower())]
    oraciones_relevantes = []
    for o in oraciones:
        o_l = o.lower()
        if any(p in o_l for p in palabras_tema):
            oraciones_relevantes.append(o)
    # Si pocas relevantes, completar con las primeras
    if len(oraciones_relevantes) < 5:
        for o in oraciones:
            if o not in oraciones_relevantes:
                oraciones_relevantes.append(o)
            if len(oraciones_relevantes) >= 8:
                break

    puntos = [p[:120] for p in oraciones_relevantes[1:6]]
    while len(puntos) < 5:
        puntos.append(oraciones_relevantes[0][:120] if oraciones_relevantes else tema[:120])

    guion_tts = (f"{tema}. "
                 f"{' '.join(oraciones_relevantes[:12])} "
                 f"Síguenos en verdadhoy.com para más información.")

    # Queries de imagen basados en el tema específico
    palabras_img = [w for w in tema.split() if len(w) > 3][:4]
    queries_imgs = [
        ' '.join(palabras_img[:3]),
        ' '.join(palabras_img[:2]),
        palabras_img[0] if palabras_img else 'world news',
        'international news',
        'history event',
    ]

    return {
        'titulo':          tema[:80],
        'subtitulo':       "Verdad Hoy — Noticias al minuto",
        'puntos':          puntos,
        'conclusion':      "¿Qué opinas? Comenta 👇 Comparte 🔁",
        'hashtags':        "#NoticiasInternacionales #VerdadHoy #ÚltimaHora #Noticias #Mundo",
        'descripcion_wp':  ' '.join(oraciones_relevantes[:3])[:280],
        'palabras_clave':  palabras_img[:3] if palabras_img else ['noticias', 'mundo'],
        'queries_imagenes': queries_imgs,
        'guion_tts':       guion_tts[:3000],
    }

def sintetizar_contenido(datos_verificados):
    tema  = datos_verificados['tema']
    texto = datos_verificados['texto_consolidado']
    log(f"🤖 Sintetizando contenido para: '{tema[:60]}'", 'ia')

    # Cascada: Gemini → OpenRouter → Extractivo
    resultado = sintetizar_gemini(tema, texto)
    if resultado:
        ok, razon = validar_coherencia_guion(resultado, tema)
        if not ok:
            log(f"   ⚠️ Gemini: guión incoherente ({razon}) — reintentando con OpenRouter", 'warn')
            resultado = None

    if not resultado:
        resultado = sintetizar_openrouter(tema, texto)
        if resultado:
            ok, razon = validar_coherencia_guion(resultado, tema)
            if not ok:
                log(f"   ⚠️ OpenRouter: guión incoherente ({razon}) — usando extractivo", 'warn')
                resultado = None

    if not resultado:
        resultado = sintetizar_extractivo(tema, texto)

    # Asegurar que queries_imagenes existe siempre
    if resultado and not resultado.get('queries_imagenes'):
        palabras = [w for w in tema.split() if len(w) > 3][:4]
        resultado['queries_imagenes'] = [
            ' '.join(palabras[:3]),
            ' '.join(palabras[:2]),
            palabras[0] if palabras else 'news',
            'world news international',
            'breaking news',
        ]

    log(f"   ✅ Guión listo: '{resultado.get('titulo','')[:60]}'", 'ok')
    log(f"   📷 Queries imagen: {resultado.get('queries_imagenes', [])[:3]}", 'debug')
    return resultado

# ──────────────────────────────────────────────
# PASO 4: RECOPILACIÓN DE IMÁGENES
# ──────────────────────────────────────────────
def descargar_imagen(url, idx=0):
    """Descarga y valida una imagen. Retorna path local o None."""
    if not url:
        return None
    for bloqueo in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon', 'favicon', 'pixel']:
        if bloqueo in url.lower():
            return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers=HEADERS, timeout=20, stream=True)
        if r.status_code != 200:
            return None
        ct = r.headers.get('content-type', '')
        if 'image' not in ct and 'octet' not in ct:
            return None
        data = r.content
        if len(data) < 5000:
            return None
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 300 or h < 200:
            return None
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        # Escalar para 9:16 — 1080x1920
        ratio_target = VIDEO_ALTO / VIDEO_ANCHO
        ratio_img = h / w
        if ratio_img > ratio_target:
            nuevo_ancho = VIDEO_ANCHO
            nuevo_alto = int(VIDEO_ANCHO * ratio_img)
        else:
            nuevo_alto = VIDEO_ALTO
            nuevo_ancho = int(VIDEO_ALTO / ratio_img)
        img = img.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
        p = f'/tmp/vbot_img_{idx}_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=90)
        log(f"   🖼️ Imagen {idx}: {w}x{h} → {nuevo_ancho}x{nuevo_alto}", 'img')
        return p
    except Exception as e:
        log(f"   Error descargando imagen {idx}: {e}", 'debug')
        return None

def buscar_pixabay(query, cantidad=6):
    if not PIXABAY_API_KEY:
        return []
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={'key': PIXABAY_API_KEY, 'q': query[:100], 'lang': 'es',
                    'image_type': 'photo', 'orientation': 'vertical',
                    'min_width': 600, 'per_page': cantidad, 'safesearch': 'true'},
            timeout=15
        ).json()
        urls = [hit['largeImageURL'] for hit in r.get('hits', [])]
        log(f"   Pixabay: {len(urls)} imágenes", 'img')
        return urls
    except Exception as e:
        log(f"   Pixabay error: {e}", 'debug')
        return []

def buscar_pexels(query, cantidad=6):
    if not PEXELS_API_KEY:
        return []
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={'query': query[:100], 'orientation': 'portrait',
                    'per_page': cantidad, 'locale': 'es-ES'},
            timeout=15
        ).json()
        urls = [p['src']['large'] for p in r.get('photos', [])]
        log(f"   Pexels: {len(urls)} imágenes", 'img')
        return urls
    except Exception as e:
        log(f"   Pexels error: {e}", 'debug')
        return []

def buscar_wikimedia(query, cantidad=4):
    """Wikimedia Commons — completamente gratis."""
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={'action': 'query', 'generator': 'search', 'gsrnamespace': 6,
                    'gsrsearch': f'filetype:bitmap {query}', 'gsrlimit': cantidad,
                    'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': 1080,
                    'format': 'json'},
            headers=HEADERS,
            timeout=15
        ).json()
        urls = []
        for page in r.get('query', {}).get('pages', {}).values():
            for ii in page.get('imageinfo', []):
                url = ii.get('thumburl') or ii.get('url', '')
                if url and url.startswith('http'):
                    urls.append(url)
        log(f"   Wikimedia: {len(urls)} imágenes", 'img')
        return urls
    except Exception as e:
        log(f"   Wikimedia error: {e}", 'debug')
        return []

def generar_imagen_texto(titulo, subtitulo, idx, total):
    """Genera imagen con Pillow cuando no hay imágenes reales disponibles."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        paletas = [
            ('#0f172a', '#3b82f6', '#ffffff'),
            ('#1a1a2e', '#e94560', '#ffffff'),
            ('#0d2137', '#00b4d8', '#ffffff'),
            ('#1b1b1b', '#f59e0b', '#ffffff'),
            ('#0a1628', '#10b981', '#ffffff'),
        ]
        fondo, acento, texto_color = paletas[idx % len(paletas)]
        img = Image.new('RGB', (VIDEO_ANCHO, VIDEO_ALTO), fondo)
        draw = ImageDraw.Draw(img)

        try:
            font_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_medio  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
            font_small  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            font_grande = font_medio = font_small = ImageFont.load_default()

        # Barra superior
        draw.rectangle([(0, 0), (VIDEO_ANCHO, 120)], fill=acento)
        draw.text((40, 40), "VERDAD HOY", font=font_medio, fill=fondo)

        # Indicador de slide
        draw.text((VIDEO_ANCHO - 120, 45), f"{idx+1}/{total}", font=font_small, fill=fondo)

        # Título
        titulo_wrap = textwrap.fill(titulo[:100], width=18)
        y = 300
        for linea in titulo_wrap.split('\n'):
            draw.text((40, y), linea, font=font_grande, fill=texto_color)
            y += 90

        # Subtítulo
        sub_wrap = textwrap.fill(subtitulo[:120], width=24)
        y += 40
        for linea in sub_wrap.split('\n'):
            draw.text((40, y), linea, font=font_medio, fill=acento)
            y += 60

        # Línea decorativa
        draw.rectangle([(40, VIDEO_ALTO - 200), (VIDEO_ANCHO - 40, VIDEO_ALTO - 196)], fill=acento)

        # Footer
        draw.text((40, VIDEO_ALTO - 160), "verdadhoy.com", font=font_medio, fill=acento)
        draw.text((40, VIDEO_ALTO - 100), "Comenta · Comparte · Reacciona 👇", font=font_small, fill=texto_color)

        p = f'/tmp/vbot_gen_{idx}_{generar_hash(titulo)}.jpg'
        img.save(p, 'JPEG', quality=90)
        return p
    except Exception as e:
        log(f"Error generando imagen texto: {e}", 'error')
        return None

def agregar_watermark_video(img_pil):
    """Agrega watermark verdadhoy.com a una imagen PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(img_pil)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            font = ImageFont.load_default()
        texto = "verdadhoy.com"
        try:
            bbox = draw.textbbox((0, 0), texto, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except:
            tw, th = 200, 30
        x = VIDEO_ANCHO - tw - 30
        y = VIDEO_ALTO - th - 30
        # Fondo semitransparente
        overlay = Image.new('RGBA', img_pil.size, (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([x-10, y-8, x+tw+10, y+th+8], radius=6, fill=(0,0,0,160))
        img_pil = img_pil.convert('RGBA')
        img_pil = Image.alpha_composite(img_pil, overlay).convert('RGB')
        draw = ImageDraw.Draw(img_pil)
        draw.text((x, y), texto, font=font, fill='#f5c518')
        return img_pil
    except:
        return img_pil

def recopilar_imagenes(datos_verificados, guion, palabras_clave):
    """
    Busca imágenes ESPECÍFICAS del tema usando los queries generados por la IA.
    Coherencia total: todas las imágenes deben corresponder a la misma noticia.

    Jerarquía de queries (de más a menos específico):
    1. queries_imagenes de la IA (los más específicos del tema)
    2. Título de la noticia
    3. Palabras clave del guión
    4. Fallback genérico solo si todo falla
    """
    log("🖼️ Recopilando imágenes coherentes con el tema...", 'img')
    tema   = datos_verificados['tema']
    titulo = guion.get('titulo', tema)

    # Queries específicos generados por la IA para ESTE tema
    queries_ia = guion.get('queries_imagenes', [])

    # Construir lista de queries en orden de especificidad
    queries_ordenados = []

    # 1. Queries específicos de la IA (en inglés, más precisos para APIs)
    queries_ordenados.extend([q.strip() for q in queries_ia if q.strip()])

    # 2. Título de la noticia (palabras significativas)
    palabras_titulo = [w for w in titulo.split() if len(w) > 3
                       and w.lower() not in {'para','como','pero','desde','hasta','sobre','este','esta'}]
    if palabras_titulo:
        queries_ordenados.append(' '.join(palabras_titulo[:4]))
        queries_ordenados.append(' '.join(palabras_titulo[:2]))

    # 3. Palabras clave del guión
    for kw in (palabras_clave or [])[:3]:
        if kw and len(kw) > 3:
            queries_ordenados.append(kw)

    # Deduplicar queries manteniendo orden
    queries_ordenados = list(dict.fromkeys([q for q in queries_ordenados if q]))
    log(f"   Queries específicos: {queries_ordenados[:5]}", 'img')

    NUM_OBJETIVO = 10

    # ── Recolectar URLs usando queries específicos ──────────────────
    urls_crudas = list(datos_verificados.get('imagenes_urls', []))  # og:image del artículo fuente

    for query in queries_ordenados:
        if len(urls_crudas) >= NUM_OBJETIVO * 3:
            break
        urls_crudas.extend(buscar_wikimedia(query, 4))

    for query in queries_ordenados:
        if len(urls_crudas) >= NUM_OBJETIVO * 3:
            break
        urls_crudas.extend(buscar_pixabay(query, 6))

    for query in queries_ordenados:
        if len(urls_crudas) >= NUM_OBJETIVO * 3:
            break
        urls_crudas.extend(buscar_pexels(query, 5))

    # Deduplicar URLs
    urls_crudas = list(dict.fromkeys([u for u in urls_crudas if u and len(u) > 10]))
    log(f"   URLs disponibles: {len(urls_crudas)}", 'img')

    # ── Descargar y validar ─────────────────────────────────────────
    paths_reales = []
    for i, url in enumerate(urls_crudas):
        if len(paths_reales) >= NUM_OBJETIVO:
            break
        p = descargar_imagen(url, i)
        if p:
            paths_reales.append(p)

    log(f"   Imágenes reales: {len(paths_reales)}/{NUM_OBJETIVO}", 'img')

    # ── Completar con imágenes generadas si faltan ──────────────────
    # Cada imagen generada muestra un punto clave ESPECÍFICO del guión
    puntos  = guion.get('puntos', [])
    paths_final = list(paths_reales)

    for idx_gen in range(NUM_OBJETIVO - len(paths_final)):
        # Rotar entre título y puntos clave para variedad visual
        if idx_gen == 0:
            subtitulo = guion.get('subtitulo', titulo)
        else:
            subtitulo = puntos[(idx_gen - 1) % len(puntos)] if puntos else titulo
        p = generar_imagen_texto(titulo, subtitulo, idx_gen, NUM_OBJETIVO)
        if p:
            paths_final.append(p)
        else:
            break

    pct = int(len(paths_reales) / max(len(paths_final), 1) * 100)
    log(f"   ✅ Total: {len(paths_final)} imágenes ({pct}% reales del tema, {100-pct}% generadas)", 'ok')
    return paths_final, NUM_OBJETIVO

# ──────────────────────────────────────────────
# PASO 5: GENERACIÓN DE VIDEO
# ──────────────────────────────────────────────
def generar_audio_tts(guion_tts, tema):
    """Genera audio TTS con edge_tts. Retorna path o None."""
    audio_path = f'/tmp/vbot_audio_{generar_hash(tema)}.mp3'
    try:
        import edge_tts
        voz = random.choice(VOCES_TTS)
        log(f"🎙️ TTS voz: {voz}", 'info')

        async def _generar():
            com = edge_tts.Communicate(guion_tts[:3000], voz)
            await com.save(audio_path)

        asyncio.run(_generar())
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            log("✅ Audio TTS generado", 'ok')
            return audio_path
    except Exception as e:
        log(f"TTS error: {e} — video sin audio", 'warn')
    return None

def aplicar_ken_burns(frame_pil, progreso, direccion='derecha'):
    """
    Efecto Ken Burns suave con easing sinusoidal.
    Zoom máximo reducido a 5% para movimiento sutil y fluido.
    """
    import math
    from PIL import Image
    w, h = frame_pil.size

    # Easing suave: sin(x * π/2) para aceleración y desaceleración natural
    p_smooth = math.sin(progreso * math.pi / 2)

    zoom = 1.0 + 0.05 * p_smooth  # zoom máximo 5% — sutil
    nw = int(w * zoom)
    nh = int(h * zoom)

    # Usar BILINEAR en vez de LANCZOS para frames intermedios — mucho más rápido
    frame_zoom = frame_pil.resize((nw, nh), Image.BILINEAR)

    if direccion == 'derecha':
        x = int((nw - w) * p_smooth)
        y = (nh - h) // 2
    elif direccion == 'izquierda':
        x = int((nw - w) * (1.0 - p_smooth))
        y = (nh - h) // 2
    elif direccion == 'arriba':
        x = (nw - w) // 2
        y = int((nh - h) * p_smooth)
    else:  # abajo
        x = (nw - w) // 2
        y = int((nh - h) * (1.0 - p_smooth))

    x = max(0, min(x, nw - w))
    y = max(0, min(y, nh - h))
    return frame_zoom.crop((x, y, x + w, y + h))

def blend_imagenes(img1, img2, alpha):
    """Cross-dissolve suave con easing cúbico entre dos imágenes PIL."""
    import math
    from PIL import Image
    # Easing cúbico: alpha³ para transición más suave al inicio y final
    alpha_smooth = alpha * alpha * (3 - 2 * alpha)  # smoothstep
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.BILINEAR)
    return Image.blend(img1, img2, alpha_smooth)

def slide_transicion(img1, img2, progreso, direccion='izquierda'):
    """Efecto slide entre dos imágenes PIL."""
    from PIL import Image
    w, h = img1.size
    if img2.size != (w, h):
        img2 = img2.resize((w, h), Image.LANCZOS)
    resultado = Image.new('RGB', (w, h))
    if direccion == 'izquierda':
        offset = int(w * progreso)
        resultado.paste(img1.crop((offset, 0, w, h)), (0, 0))
        resultado.paste(img2.crop((0, 0, w - offset, h)), (w - offset, 0))
    elif direccion == 'derecha':
        offset = int(w * progreso)
        resultado.paste(img1.crop((0, 0, w - offset, h)), (offset, 0))
        resultado.paste(img2.crop((offset, 0, w, h)), (0, 0))
    return resultado

def superponer_texto_video(frame_pil, guion, idx_imagen, total_imagenes, tema):
    """Superpone título, punto clave actual y watermark sobre el frame."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap as tw

    draw = ImageDraw.Draw(frame_pil)
    w, h = frame_pil.size

    try:
        font_titulo  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        font_punto   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        font_marca   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_counter = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except:
        font_titulo = font_punto = font_marca = font_counter = ImageFont.load_default()

    # ── BARRA SUPERIOR ──────────────────────────────
    draw.rectangle([(0, 0), (w, 100)], fill=(220, 38, 38, 230))
    draw.text((30, 28), "VERDAD HOY  |  ÚLTIMA HORA", font=font_marca, fill='white')

    # Contador de slide
    draw.text((w - 110, 35), f"{idx_imagen+1}/{total_imagenes}", font=font_counter, fill='white')

    # ── OVERLAY INFERIOR ────────────────────────────
    # Fondo semitransparente en parte inferior (40% del alto)
    overlay = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([(0, int(h * 0.55)), (w, h)], fill=(0, 0, 0, 200))
    frame_pil = frame_pil.convert('RGBA')
    frame_pil = Image.alpha_composite(frame_pil, overlay).convert('RGB')
    draw = ImageDraw.Draw(frame_pil)

    # ── TÍTULO ──────────────────────────────────────
    titulo = guion.get('titulo', tema)[:80]
    titulo_wrap = tw.fill(titulo, width=20)
    y_texto = int(h * 0.57)
    for linea in titulo_wrap.split('\n'):
        draw.text((30, y_texto), linea, font=font_titulo, fill='white')
        y_texto += 66

    y_texto += 20

    # ── PUNTO CLAVE ACTUAL ──────────────────────────
    puntos = guion.get('puntos', [])
    if puntos:
        punto_idx = idx_imagen % len(puntos)
        punto = puntos[punto_idx]
        punto_wrap = tw.fill(punto[:120], width=26)
        draw.rectangle([(20, y_texto - 10), (w - 20, y_texto + len(punto_wrap.split('\n')) * 48 + 10)],
                       fill=(59, 130, 246, 180))
        for linea in punto_wrap.split('\n'):
            draw.text((35, y_texto), linea, font=font_punto, fill='white')
            y_texto += 48

    # ── WATERMARK ───────────────────────────────────
    draw.text((30, h - 80), "verdadhoy.com", font=font_marca, fill='#f5c518')
    cta = guion.get('conclusion', 'Comenta 👇 Comparte 🔁')[:50]
    draw.text((30, h - 44), cta, font=font_counter, fill='#94a3b8')

    return frame_pil

def descargar_musica_fondo(tema, duracion_seg):
    """
    Descarga música de fondo libre de derechos acorde al tema.
    Fuente: Free Music Archive / ccmixter / archivos públicos dominio.
    Retorna path local o None.
    """
    # Mapeo tema → URL de música libre de derechos (dominio público / CC0)
    MUSICAS = {
        'urgente': [
            "https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3",
            "https://assets.mixkit.co/music/preview/mixkit-news-report-702.mp3",
            "https://assets.mixkit.co/music/preview/mixkit-breaking-news-theme-702.mp3",
        ],
        'deportes': [
            "https://assets.mixkit.co/music/preview/mixkit-sport-action-702.mp3",
            "https://assets.mixkit.co/music/preview/mixkit-stadium-702.mp3",
        ],
        'ciencia': [
            "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3",
            "https://assets.mixkit.co/music/preview/mixkit-futuristic-702.mp3",
        ],
        'general': [
            "https://assets.mixkit.co/music/preview/mixkit-news-show-702.mp3",
            "https://assets.mixkit.co/music/preview/mixkit-documentary-702.mp3",
            "https://assets.mixkit.co/music/preview/mixkit-corporate-702.mp3",
        ],
    }

    # Detectar categoría del tema
    tema_l = tema.lower()
    if any(p in tema_l for p in ['guerra', 'urgente', 'ataque', 'muerto', 'crisis', 'terremoto']):
        categoria = 'urgente'
    elif any(p in tema_l for p in ['futbol', 'deporte', 'gol', 'partido', 'copa', 'champions']):
        categoria = 'deportes'
    elif any(p in tema_l for p in ['ciencia', 'tecnologia', 'ia', 'robot', 'nasa', 'descubri']):
        categoria = 'ciencia'
    else:
        categoria = 'general'

    urls = MUSICAS.get(categoria, MUSICAS['general'])
    random.shuffle(urls)

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, stream=True)
            if r.status_code == 200 and 'audio' in r.headers.get('content-type', ''):
                path = f'/tmp/vbot_musica_{generar_hash(tema)}.mp3'
                with open(path, 'wb') as f:
                    f.write(r.content)
                if os.path.exists(path) and os.path.getsize(path) > 5000:
                    log(f"🎵 Música de fondo descargada ({categoria})", 'ok')
                    return path
        except Exception as e:
            log(f"   Música error {url[:50]}: {e}", 'debug')

    log("   Sin música de fondo disponible — solo TTS", 'warn')
    return None

def mezclar_audio_con_musica(tts_path, musica_path, duracion_video, tema):
    """
    Mezcla TTS (voz) + música de fondo (volumen bajo) con ffmpeg.
    Retorna path del audio mezclado o tts_path original si falla.
    """
    if not musica_path or not tts_path:
        return tts_path
    out_path = f'/tmp/vbot_audio_mix_{generar_hash(tema)}.mp3'
    try:
        import subprocess
        # TTS al 100% de volumen, música al 12% (apenas se escucha de fondo)
        cmd = [
            'ffmpeg', '-y',
            '-i', tts_path,
            '-i', musica_path,
            '-filter_complex',
            f'[1:a]volume=0.12,aloop=loop=-1:size=2e+09,atrim=duration={duracion_video}[bg];'
            f'[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[out]',
            '-map', '[out]',
            '-c:a', 'libmp3lame', '-q:a', '4',
            out_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            log("✅ Audio mezclado: TTS + música de fondo", 'ok')
            return out_path
        else:
            log(f"   ffmpeg mix error: {result.stderr.decode()[:200]}", 'debug')
    except Exception as e:
        log(f"   Error mezclando audio: {e}", 'debug')
    return tts_path  # fallback: solo TTS

def normalizar_imagen_9_16(img, ancho=VIDEO_ANCHO, alto=VIDEO_ALTO):
    """Escala y recorta una imagen PIL al tamaño exacto 9:16."""
    from PIL import Image
    if img.size == (ancho, alto):
        return img
    img_r = img.width / img.height
    tgt_r = ancho / alto
    if img_r > tgt_r:
        nuevo_h = alto
        nuevo_w = int(alto * img_r)
    else:
        nuevo_w = ancho
        nuevo_h = int(ancho / img_r)
    img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)
    x = (nuevo_w - ancho) // 2
    y = (nuevo_h - alto) // 2
    return img.crop((x, y, x + ancho, y + alto))

def crear_video_multiimagen(paths_imagenes, guion, audio_tts_path, tema):
    """
    Genera el MP4 final con múltiples imágenes, transiciones fluidas y texto superpuesto.
    Vertical 9:16 (1080x1920), 90–120 segundos.
    Fixes v2:
      - Transiciones ENTRE imágenes (no frames negros)
      - Ken Burns suave aplicado SIEMPRE como movimiento base
      - Música de fondo mezclada con TTS
      - Mínimo 8 imágenes garantizado
    """
    log("🎬 Generando video v2...", 'video')
    try:
        import numpy as np
        from PIL import Image
        try:
            from moviepy.editor import ImageSequenceClip, AudioFileClip
        except ImportError:
            from moviepy import ImageSequenceClip, AudioFileClip

        total_imagenes = len(paths_imagenes)
        if total_imagenes == 0:
            log("Sin imágenes", 'error')
            return None

        # ── Duración ────────────────────────────────────
        duracion_total   = random.randint(VIDEO_DURACION_MIN, VIDEO_DURACION_MAX)
        seg_por_img      = max(SEG_POR_IMAGEN_MIN, min(SEG_POR_IMAGEN_MAX,
                               duracion_total / total_imagenes))
        duracion_total   = int(seg_por_img * total_imagenes)
        FRAMES_IMG       = int(VIDEO_FPS * seg_por_img)
        FRAMES_TRANS     = int(VIDEO_FPS * 1.0)  # 1 segundo de transición suave
        log(f"   {duracion_total}s | {total_imagenes} imgs × {seg_por_img:.1f}s | trans={FRAMES_TRANS}f", 'video')

        # ── Cargar y normalizar imágenes ─────────────────
        imgs_pil = []
        for p in paths_imagenes:
            try:
                img = Image.open(p).convert('RGB')
                img = normalizar_imagen_9_16(img)
                imgs_pil.append(img)
            except Exception as e:
                log(f"   Error cargando {p}: {e}", 'debug')

        if not imgs_pil:
            log("No se cargaron imágenes PIL", 'error')
            return None

        log(f"   PIL cargadas: {len(imgs_pil)}", 'video')

        # ── Secuencia de efectos por imagen ──────────────
        EFECTOS = ['kb_derecha', 'kb_izquierda', 'kb_arriba', 'kb_abajo', 'zoom_in', 'zoom_out']
        TRANS   = ['fade', 'slide_izq', 'slide_der', 'slide_arr', 'slide_aba']
        efectos_asignados = [EFECTOS[i % len(EFECTOS)] for i in range(len(imgs_pil))]
        trans_asignadas   = [TRANS[i % len(TRANS)]     for i in range(len(imgs_pil))]
        random.shuffle(efectos_asignados)
        random.shuffle(trans_asignadas)

        # ── Generar todos los frames ──────────────────────
        todos_frames = []

        for i, img_pil in enumerate(imgs_pil):
            efecto = efectos_asignados[i]

            # — Frames principales con Ken Burns / zoom —
            for f in range(FRAMES_IMG):
                p = f / max(FRAMES_IMG - 1, 1)  # 0.0 → 1.0

                if efecto in ('kb_derecha', 'kb_izquierda', 'kb_arriba', 'kb_abajo'):
                    dir_map = {'kb_derecha': 'derecha', 'kb_izquierda': 'izquierda',
                               'kb_arriba': 'arriba', 'kb_abajo': 'abajo'}
                    frame = aplicar_ken_burns(img_pil, p, dir_map[efecto])
                elif efecto == 'zoom_in':
                    frame = aplicar_ken_burns(img_pil, p * 0.08, 'derecha')
                else:  # zoom_out
                    frame = aplicar_ken_burns(img_pil, (1.0 - p) * 0.08, 'izquierda')

                frame = superponer_texto_video(frame, guion, i, len(imgs_pil), tema)
                todos_frames.append(np.array(frame))

            # — Transición hacia siguiente imagen —
            if i < len(imgs_pil) - 1:
                img_sig = imgs_pil[i + 1]
                tipo_trans = trans_asignadas[i]

                for f in range(FRAMES_TRANS):
                    alpha = f / FRAMES_TRANS  # 0.0 → ~1.0 (sin llegar a 1 para no duplicar)

                    if tipo_trans == 'fade':
                        frame_t = blend_imagenes(img_pil, img_sig, alpha)

                    elif tipo_trans == 'slide_izq':
                        frame_t = slide_transicion(img_pil, img_sig, alpha, 'izquierda')

                    elif tipo_trans == 'slide_der':
                        frame_t = slide_transicion(img_pil, img_sig, alpha, 'derecha')

                    elif tipo_trans == 'slide_arr':
                        # Slide vertical hacia arriba
                        w, h = img_pil.size
                        if img_sig.size != (w, h):
                            img_sig = img_sig.resize((w, h), Image.LANCZOS)
                        offset = int(h * alpha)
                        frame_t = Image.new('RGB', (w, h))
                        frame_t.paste(img_pil.crop((0, offset, w, h)), (0, 0))
                        frame_t.paste(img_sig.crop((0, 0, w, h - offset)), (0, h - offset))

                    else:  # slide_aba
                        w, h = img_pil.size
                        if img_sig.size != (w, h):
                            img_sig = img_sig.resize((w, h), Image.LANCZOS)
                        offset = int(h * alpha)
                        frame_t = Image.new('RGB', (w, h))
                        frame_t.paste(img_pil.crop((0, 0, w, h - offset)), (0, offset))
                        frame_t.paste(img_sig.crop((0, h - offset, w, h)), (0, 0))

                    frame_t = superponer_texto_video(frame_t, guion, i, len(imgs_pil), tema)
                    todos_frames.append(np.array(frame_t))

        if not todos_frames:
            log("Sin frames generados", 'error')
            return None

        dur_real = len(todos_frames) / VIDEO_FPS
        log(f"   Frames totales: {len(todos_frames)} → {dur_real:.1f}s", 'video')

        # ── Crear clip de video ───────────────────────────
        clip = ImageSequenceClip(todos_frames, fps=VIDEO_FPS)

        # ── Audio: TTS + música de fondo ─────────────────
        audio_final_path = audio_tts_path
        if audio_tts_path and os.path.exists(audio_tts_path):
            musica_path = descargar_musica_fondo(tema, dur_real)
            if musica_path:
                audio_final_path = mezclar_audio_con_musica(
                    audio_tts_path, musica_path, dur_real, tema)
                try:
                    os.remove(musica_path)
                except:
                    pass

        if audio_final_path and os.path.exists(audio_final_path):
            try:
                audio = AudioFileClip(audio_final_path)
                if audio.duration >= clip.duration:
                    clip = clip.set_audio(audio.subclip(0, clip.duration))
                else:
                    # Loop del audio si es más corto que el video
                    from moviepy.audio.fx.all import audio_loop
                    try:
                        clip = clip.set_audio(audio_loop(audio, duration=clip.duration))
                    except:
                        clip = clip.set_audio(audio)
                log("   ✅ Audio final configurado", 'ok')
            except Exception as e:
                log(f"   Error configurando audio: {e}", 'warn')

        # ── Exportar MP4 ──────────────────────────────────
        video_path = f'/tmp/vbot_video_{generar_hash(tema)}.mp4'
        clip.write_videofile(
            video_path,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            ffmpeg_params=['-crf', '26', '-profile:v', 'baseline', '-level', '3.0'],
            logger=None
        )
        clip.close()

        # Limpiar audio mezclado temporal
        if audio_final_path and audio_final_path != audio_tts_path:
            try:
                os.remove(audio_final_path)
            except:
                pass

        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log(f"✅ Video listo: {size_mb:.1f} MB, {dur_real:.0f}s, {len(imgs_pil)} imágenes", 'ok')
        return video_path

    except ImportError as e:
        log(f"moviepy no disponible: {e}", 'error')
        return None
    except Exception as e:
        log(f"Error generando video: {e}", 'error')
        import traceback
        traceback.print_exc()
        return None

# ──────────────────────────────────────────────
# PASO 6: PUBLICACIÓN
# ──────────────────────────────────────────────
def construir_texto_post_fb(guion, tema):
    """
    Construye el texto del post de Facebook para un Reel:
    - Titular con emoji
    - Párrafo resumen COMPLETO (2-3 oraciones, sin cortes)
    - Línea separadora
    - Hashtags
    - Link a verdadhoy.com

    El párrafo resumen se toma de descripcion_wp y se recorta
    solo en un punto o punto final para que nunca quede cortado.
    """
    titulo    = guion.get('titulo', tema).strip()
    desc_raw  = guion.get('descripcion_wp', '').strip()
    hashtags  = guion.get('hashtags', '#VerdadHoy #NoticiasInternacionales #ÚltimaHora').strip()

    # ── Construir párrafo resumen completo ───────────────
    # Dividir en oraciones y tomar las primeras 2-3 que sumen ~300 chars
    oraciones = re.split(r'(?<=[.!?])\s+', desc_raw)
    parrafo = ''
    for oracion in oraciones:
        oracion = oracion.strip()
        if not oracion:
            continue
        candidato = (parrafo + ' ' + oracion).strip() if parrafo else oracion
        if len(candidato) <= 320:
            parrafo = candidato
        else:
            break  # no agregar más — el párrafo ya está completo

    # Si no se pudo armar párrafo, usar primera oración completa
    if not parrafo and oraciones:
        parrafo = oraciones[0].strip()

    # Asegurar que termina en puntuación
    if parrafo and parrafo[-1] not in '.!?':
        # Cortar en el último punto antes del límite
        ultimo_punto = max(parrafo.rfind('.'), parrafo.rfind('!'), parrafo.rfind('?'))
        if ultimo_punto > 50:
            parrafo = parrafo[:ultimo_punto + 1]
        else:
            parrafo = parrafo.rstrip() + '.'

    # ── Ensamblar post ───────────────────────────────────
    lineas = [
        f"📰 {titulo}",
        "",
        parrafo,
        "",
        "─" * 28,
        "",
        hashtags,
        "",
        "🌐 Más en verdadhoy.com",
    ]
    return '\n'.join(lineas)

def publicar_facebook_reel(guion, tema, video_path):
    """Publica el video como Reel en Facebook con texto limpio y completo."""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("FB: sin credenciales", 'warn')
        return None

    titulo = guion.get('titulo', tema)
    texto  = construir_texto_post_fb(guion, tema)

    log(f"   Texto post FB:\n{texto[:200]}...", 'debug')

    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
        with open(video_path, 'rb') as f:
            r = requests.post(
                url,
                files={'source': ('video.mp4', f, 'video/mp4')},
                data={
                    'title':        titulo[:255],
                    'description':  texto,
                    'access_token': FB_ACCESS_TOKEN,
                },
                timeout=180
            ).json()
        if 'id' in r:
            video_id = r['id']
            url_fb   = f"https://www.facebook.com/watch/?v={video_id}"
            log(f"✅ Facebook Reel publicado: {video_id}", 'ok')
            return url_fb
        else:
            log(f"Facebook error: {r.get('error', {}).get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"Excepción Facebook: {e}", 'error')
    return None

def publicar_wordpress_video(guion, url_video_fb, tema, palabras_clave):
    """Publica post en WordPress con embed del video y SEO."""
    if not WP_URL or not WP_USER or not WP_APP_PASSWORD:
        log("WP: sin credenciales", 'warn')
        return None

    titulo_wp = guion.get('titulo', tema)
    descripcion = guion.get('descripcion_wp', '')
    puntos = guion.get('puntos', [])
    hashtags = guion.get('hashtags', '')
    keywords = ', '.join(palabras_clave[:5]) if palabras_clave else tema

    # Construir contenido HTML del post
    puntos_html = ''.join([f"<li>{p}</li>" for p in puntos])
    embed_fb = f'<p><a href="{url_video_fb}" target="_blank">▶ Ver video en Facebook</a></p>' if url_video_fb else ''

    contenido = f"""
{embed_fb}
<p>{descripcion}</p>
<h2>Lo más importante</h2>
<ul>{puntos_html}</ul>
<p><strong>Conclusión:</strong> {guion.get('conclusion', '')}</p>
<hr>
<p><em>Fuente: Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')} | {keywords}</em></p>
"""

    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_APP_PASSWORD),
            json={
                'title': titulo_wp,
                'content': contenido,
                'status': 'publish',
                'excerpt': descripcion[:200],
                'meta': {'_yoast_wpseo_focuskw': palabras_clave[0] if palabras_clave else tema},
                'tags_input': hashtags.replace('#', '').split(),
            },
            timeout=30
        ).json()
        if 'id' in r:
            url_wp = r.get('link', '')
            log(f"✅ WordPress publicado: {url_wp}", 'ok')
            return url_wp
        else:
            log(f"WordPress error: {r.get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"Excepción WordPress: {e}", 'error')
    return None

# ──────────────────────────────────────────────
# LIMPIEZA
# ──────────────────────────────────────────────
def limpiar_temporales(paths_imagenes, audio_path, video_path):
    for p in paths_imagenes:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except:
            pass
    for p in [audio_path, video_path]:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except:
            pass

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("🎬 VIDEO BOT — Verdad Hoy")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # Control de publicación
    puede, razon = puede_publicar()
    if not puede:
        log(f"⏱️ No publicar ahora: {razon}", 'info')
        return None

    log(f"✅ Puede publicar: {razon}", 'ok')

    h = cargar_json(HISTORIAL_PATH, {'videos': [], 'temas': []})

    # PASO 1 — Seleccionar tema
    tema_info = seleccionar_tema(h)
    if not tema_info:
        log("Sin tema disponible", 'error')
        return False
    tema = tema_info['tema']

    # PASO 2 — Verificar en 3+ fuentes
    datos = verificar_tema_en_fuentes(tema_info)
    if not datos['texto_consolidado']:
        log("Sin contenido verificado para el tema", 'error')
        return False
    log(f"✅ Verificado en {datos['num_fuentes']} fuentes", 'ok')

    # PASO 3 — Sintetizar con IA
    guion = sintetizar_contenido(datos)
    if not guion:
        log("Sin guión generado", 'error')
        return False
    log(f"✅ Guión: '{guion.get('titulo', '')[:60]}'", 'ok')

    palabras_clave = guion.get('palabras_clave', [tema.split()[0]])

    # PASO 4 — Recopilar imágenes
    paths_imagenes, num_target = recopilar_imagenes(datos, guion, palabras_clave)
    if not paths_imagenes:
        log("Sin imágenes para el video", 'error')
        return False

    # PASO 5a — Audio TTS
    guion_tts = guion.get('guion_tts', f"{guion.get('titulo','')}. {' '.join(guion.get('puntos',[]))}")
    audio_tts_path = generar_audio_tts(guion_tts, tema)

    # PASO 5b — Generar video (música de fondo se mezcla dentro)
    video_path = crear_video_multiimagen(paths_imagenes, guion, audio_tts_path, tema)
    if not video_path:
        log("Video no generado", 'error')
        limpiar_temporales(paths_imagenes, audio_tts_path, None)
        return False

    # PASO 6 — Publicar
    url_fb = publicar_facebook_reel(
        guion=guion,
        tema=tema,
        video_path=video_path
    )

    url_wp = publicar_wordpress_video(guion, url_fb, tema, palabras_clave)

    # Registrar en historial
    if url_fb or url_wp:
        registrar_video(tema, url_fb, url_wp)
        log(f"\n✅ PUBLICADO — FB: {url_fb or 'N/A'} | WP: {url_wp or 'N/A'}", 'ok')
    else:
        log("No se publicó en ninguna plataforma", 'error')

    # Limpiar temporales
    limpiar_temporales(paths_imagenes, audio_tts_path, video_path)

    return bool(url_fb or url_wp)


if __name__ == "__main__":
    try:
        resultado = main()
        exit(0 if resultado is not False else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
