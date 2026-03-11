#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook
- Prioridad: Conflictos bélicos, política global, economía mundial
- Fuentes: NewsAPI, NewsData, GNews (todo internacional)
- Anti-duplicados mejorado
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
import html as html_module
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')

TIEMPO_ENTRE_PUBLICACIONES = 60  # 60 minutos
VENTANA_DUPLICADOS_HORAS = 24    # 24 horas de memoria de duplicados

# =============================================================================
# PALABRAS CLAVE INTERNACIONALES PRIORITARIAS
# =============================================================================

# ALTA PRIORIDAD (Conflictos y crisis globales)
PALABRAS_ALTA_PRIORIDAD = [
    'guerra', 'conflicto', 'bombardeo', 'ataque', 'invasión', 'invasion',
    'misil', 'dron', 'ataque aéreo', 'ataque aereo', 'ofensiva', 'combate',
    'tregua', 'cese al fuego', 'negociaciones', 'acuerdo de paz',
    'Ucrania', 'Rusia', 'Gaza', 'Israel', 'Palestina', 'Líbano', 'libano',
    'Trump', 'Biden', 'Putin', 'Zelensky', 'Zelenskiy', 'Netanyahu',
    'OTAN', 'NATO', 'ONU', 'UE', 'Unión Europea', 'union europea',
    'sanciones', 'embargo', 'crisis diplomática', 'crisis diplomatica',
    'tensión internacional', 'tension internacional', 'reunión de emergencia',
    'cumbre', 'G7', 'G20', 'BRICS', 'COP', 'clima', 'cambio climático',
    'desastre natural', 'terremoto', 'tsunami', 'huracán', 'huracan',
    'pandemia', 'epidemia', 'virus', 'emergencia sanitaria',
]

# PRIORIDAD MEDIA (Economía global y política internacional)
PALABRAS_MEDIA_PRIORIDAD = [
    'economía mundial', 'economia mundial', 'mercados globales', 'crisis financiera',
    'recesión', 'recesion', 'inflación', 'inflacion', 'deuda', 'FMI', 'Banco Mundial',
    'reserva federal', 'fed', 'bce', 'banco central', 'tipos de interés', 'tipos de interes',
    'petróleo', 'petroleo', 'gas', 'energía', 'energia', 'crisis energética',
    'dólar', 'dolar', 'euro', 'yuan', 'divisas', 'cambio divisa',
    'comercio internacional', 'aranceles', 'guerra comercial', 'brexit',
    'elecciones', 'golpe de estado', 'protestas', 'manifestaciones', 'revolución',
    'corrupción', 'corrupcion', 'escándalo', 'escandalo', 'investigación',
    'China', 'EEUU', 'Estados Unidos', 'Rusia', 'India', 'Brasil', 'México', 'Mexico',
    'Alemania', 'Francia', 'Reino Unido', 'Italia', 'Japón', 'Japon', 'Corea',
    'Oriente Medio', 'oriente medio', 'medio oriente', 'África', 'africa', 'Asia',
    'Latinoamérica', 'latinoamerica', 'Sudamérica', 'sudamerica', 'Europa',
]

# TÉRMINOS A EVITAR (Noticias locales no relevantes)
TERMINOS_EXCLUIR = [
    'liga local', 'campeonato municipal', 'feria del pueblo', 
    'concurso de belleza local', 'festival regional', 'torneo de barrio',
    'elecciones municipales de', 'alcaldía de', 'alcalde de', 'gobernador de',
    'partido local', 'equipo local', 'deporte local',
]

# PLANTILLAS PROFESIONALES PARA NOTICIAS
PLANTILLAS_APERTURA = [
    "ÚLTIMA HORA | {titulo}",
    "NOTICIA INTERNACIONAL | {titulo}",
    "DESARROLLO | {titulo}",
    "INFORMACIÓN EN PROGRESO | {titulo}",
    "ALERTA MUNDIAL | {titulo}",
]

PLANTILLAS_DESARROLLO = [
    "Según información preliminar, {contenido}",
    "Fuentes internacionales reportan que {contenido}",
    "Los primeros reportes indican que {contenido}",
    "De acuerdo con agencias de noticias globales, {contenido}",
    "Informes desde el lugar de los hechos señalan que {contenido}",
]

PLANTILLAS_CIERRE = [
    "Se esperan más detalles en las próximas horas.",
    "La situación continúa en desarrollo.",
    "Estaremos actualizando conforme se conozcan más datos.",
    "Las autoridades competentes aún no han emitido un comunicado oficial completo.",
    "Se recomienda seguir fuentes oficiales para información actualizada.",
]

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    icono = iconos.get(tipo, 'ℹ️')
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {icono} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                if not contenido:
                    return default.copy()
                return json.loads(contenido)
        except Exception as e:
            log(f"Error cargando JSON: {e}", 'error')
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"Error guardando JSON: {e}", 'error')
        return False

def generar_hash(texto):
    """Genera hash único para identificar noticias"""
    if not texto:
        return ""
    texto_normalizado = re.sub(r'[^\w\s]', '', texto.lower().strip())
    texto_normalizado = re.sub(r'\s+', ' ', texto_normalizado)
    return hashlib.md5(texto_normalizado.encode()).hexdigest()[:16]

def limpiar_texto(texto):
    """Limpieza avanzada de texto para evitar cortes"""
    if not texto:
        return ""
    
    # Decodificar HTML
    texto = html_module.unescape(texto)
    
    # Eliminar etiquetas HTML
    texto = re.sub(r'<[^>]+>', ' ', texto)
    
    # Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar caracteres de control y especiales que causan cortes
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)
    
    # Eliminar URLs truncadas al final (causantes de cortes visuales)
    texto = re.sub(r'https?://\S*$', '', texto)
    
    # Eliminar "..." o "…" sueltos al final que indican continuación truncada
    texto = re.sub(r'[.…]{2,}\s*$', '.', texto)
    
    # Asegurar que termine en puntuación completa
    texto = texto.strip()
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto.strip()

def es_noticia_excluible(titulo, descripcion=""):
    """Verifica si la noticia es local/no relevante internacionalmente"""
    texto = f"{titulo} {descripcion}".lower()
    for termino in TERMINOS_EXCLUIR:
        if termino.lower() in texto:
            return True
    return False

def calcular_puntaje_internacional(titulo, descripcion):
    """Calcula relevancia para noticias internacionales"""
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    # Alta prioridad
    for palabra in PALABRAS_ALTA_PRIORIDAD:
        if palabra.lower() in texto:
            puntaje += 10
    
    # Media prioridad
    for palabra in PALABRAS_MEDIA_PRIORIDAD:
        if palabra.lower() in texto:
            puntaje += 3
    
    # Bonus por fuentes reconocidas
    fuentes_reconocidas = ['reuters', 'afp', 'ap ', 'associated press', 'bbc', 'cnn', 'al jazeera']
    for fuente in fuentes_reconocidas:
        if fuente in texto:
            puntaje += 2
            break
    
    # Penalizar noticias locales
    if es_noticia_excluible(titulo, descripcion):
        puntaje -= 20
    
    # Bonus por longitud adecuada
    if 50 <= len(titulo) <= 120:
        puntaje += 2
    
    return puntaje

# =============================================================================
# GESTIÓN DE HISTORIAL
# =============================================================================

def cargar_historial():
    """Carga historial con estructura garantizada"""
    default = {
        'urls': [], 
        'hashes': [],
        'timestamps': [],
        'estadisticas': {'total_publicadas': 0}
    }
    datos = cargar_json(HISTORIAL_PATH, default)
    
    for key in ['urls', 'hashes', 'timestamps']:
        if key not in datos or not isinstance(datos[key], list):
            datos[key] = []
    
    if 'estadisticas' not in datos or not isinstance(datos['estadisticas'], dict):
        datos['estadisticas'] = {'total_publicadas': 0}
    
    return datos

def limpiar_historial_antiguo(historial):
    """Elimina entradas antiguas del historial"""
    if not historial or not isinstance(historial, dict):
        return {'urls': [], 'hashes': [], 'timestamps': [], 'estadisticas': {'total_publicadas': 0}}
    
    ahora = datetime.now()
    indices_validos = []
    
    timestamps = historial.get('timestamps', [])
    if not isinstance(timestamps, list):
        timestamps = []
    
    for i, ts_str in enumerate(timestamps):
        try:
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str)
                if (ahora - ts) < timedelta(hours=VENTANA_DUPLICADOS_HORAS):
                    indices_validos.append(i)
        except:
            continue
    
    nuevo_historial = {
        'urls': [],
        'hashes': [],
        'timestamps': [],
        'estadisticas': historial.get('estadisticas', {'total_publicadas': 0})
    }
    
    urls = historial.get('urls', [])
    hashes = historial.get('hashes', [])
    
    for i in indices_validos:
        if i < len(urls):
            nuevo_historial['urls'].append(urls[i])
        if i < len(hashes):
            nuevo_historial['hashes'].append(hashes[i])
        if i < len(timestamps):
            nuevo_historial['timestamps'].append(timestamps[i])
    
    return nuevo_historial

def noticia_ya_publicada(historial, url, titulo):
    """Verifica si una noticia ya fue publicada"""
    if not historial or not isinstance(historial, dict):
        return False
    
    url_limpia = re.sub(r'\?.*$', '', url)
    url_base = re.sub(r'https?://(www\.)?', '', url_limpia).lower().rstrip('/')
    
    urls_guardadas = historial.get('urls', [])
    if not isinstance(urls_guardadas, list):
        urls_guardadas = []
    
    for url_hist in urls_guardadas:
        if not isinstance(url_hist, str):
            continue
        url_hist_limpia = re.sub(r'\?.*$', '', url_hist)
        url_hist_base = re.sub(r'https?://(www\.)?', '', url_hist_limpia).lower().rstrip('/')
        
        if url_base == url_hist_base:
            return True
        
        url_slug = url_base.split('/')[-1]
        hist_slug = url_hist_base.split('/')[-1]
        if url_slug and hist_slug and len(url_slug) > 15:
            if url_slug[:20] == hist_slug[:20]:
                return True
    
    hash_titulo = generar_hash(titulo)
    hashes_guardados = historial.get('hashes', [])
    if not isinstance(hashes_guardados, list):
        hashes_guardados = []
    
    if hash_titulo in hashes_guardados:
        return True
    
    return False

def guardar_historial(historial, url, titulo):
    """Guarda noticia en historial"""
    historial = limpiar_historial_antiguo(historial)
    
    url_limpia = re.sub(r'\?.*$', '', url)
    hash_titulo = generar_hash(titulo)
    ahora = datetime.now().isoformat()
    
    historial['urls'].append(url_limpia)
    historial['hashes'].append(hash_titulo)
    historial['timestamps'].append(ahora)
    
    stats = historial.get('estadisticas', {'total_publicadas': 0})
    if not isinstance(stats, dict):
        stats = {'total_publicadas': 0}
    stats['total_publicadas'] = stats.get('total_publicadas', 0) + 1
    historial['estadisticas'] = stats
    
    max_size = 500
    for key in ['urls', 'hashes', 'timestamps']:
        if len(historial[key]) > max_size:
            historial[key] = historial[key][-max_size:]
    
    guardar_json(HISTORIAL_PATH, historial)

def cargar_estado():
    default = {'ultima_publicacion': None}
    datos = cargar_json(ESTADO_PATH, default)
    return datos

def guardar_estado(estado):
    guardar_json(ESTADO_PATH, estado)

def verificar_tiempo():
    """Verifica si debe publicar según tiempo configurado"""
    estado = cargar_estado()
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos = (datetime.now() - ultima_dt).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {minutos:.0f} min", 'info')
            return False
        return True
    except:
        return True

# =============================================================================
# FUENTES DE NOTICIAS INTERNACIONALES
# =============================================================================

def obtener_newsapi_internacional():
    """Obtiene noticias internacionales de NewsAPI"""
    if not NEWS_API_KEY:
        return []
    
    noticias = []
    queries = [
        'war OR conflict OR Ukraine OR Russia OR Gaza OR Israel',
        'Trump OR Biden OR Putin OR international politics',
        'economy OR inflation OR markets OR IMF OR Federal Reserve',
        'NATO OR UN OR EU OR summit OR diplomacy',
        'climate OR disaster OR earthquake OR hurricane',
    ]
    
    for q in queries:
        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'apiKey': NEWS_API_KEY,
                'q': q,
                'language': 'es',
                'sortBy': 'publishedAt',
                'pageSize': 10
            }
            
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    titulo = art.get('title', '')
                    if not titulo or '[Removed]' in titulo:
                        continue
                    
                    desc = art.get('description', '')
                    
                    if es_noticia_excluible(titulo, desc):
                        continue
                    
                    noticias.append({
                        'titulo': limpiar_texto(titulo),
                        'descripcion': limpiar_texto(desc),
                        'url': art.get('url', ''),
                        'imagen': art.get('urlToImage'),
                        'fuente': f"NewsAPI:{art.get('source', {}).get('name', 'Unknown')}",
                        'fecha': art.get('publishedAt'),
                        'puntaje': calcular_puntaje_internacional(titulo, desc)
                    })
        except Exception as e:
            log(f"Error NewsAPI query '{q}': {e}", 'debug')
            continue
    
    urls_vistas = set()
    noticias_unicas = []
    for n in noticias:
        url_base = re.sub(r'\?.*$', '', n['url'])
        if url_base not in urls_vistas:
            urls_vistas.add(url_base)
            noticias_unicas.append(n)
    
    log(f"NewsAPI: {len(noticias_unicas)} noticias internacionales", 'info')
    return noticias_unicas

def obtener_newsdata_internacional():
    """Obtiene noticias de NewsData.io"""
    if not NEWSDATA_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://newsdata.io/api/1/news'
        params = {
            'apikey': NEWSDATA_API_KEY,
            'language': 'es',
            'category': 'world,politics,business',
            'size': 30
        }
        
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        if data.get('status') == 'success':
            for art in data.get('results', []):
                titulo = art.get('title', '')
                if not titulo:
                    continue
                
                desc = art.get('description', '')
                
                if es_noticia_excluible(titulo, desc):
                    continue
                
                noticias.append({
                    'titulo': limpiar_texto(titulo),
                    'descripcion': limpiar_texto(desc),
                    'url': art.get('link', ''),
                    'imagen': art.get('image_url'),
                    'fuente': f"NewsData:{art.get('source_id', 'Unknown')}",
                    'fecha': art.get('pubDate'),
                    'puntaje': calcular_puntaje_internacional(titulo, desc)
                })
    except Exception as e:
        log(f"Error NewsData: {e}", 'advertencia')
    
    log(f"NewsData: {len(noticias)} noticias", 'info')
    return noticias

def obtener_gnews_internacional():
    """Obtiene noticias de GNews"""
    if not GNEWS_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {
            'apikey': GNEWS_API_KEY,
            'lang': 'es',
            'max': 20,
            'topic': 'world'
        }
        
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        for art in data.get('articles', []):
            titulo = art.get('title', '')
            if not titulo:
                continue
            
            desc = art.get('description', '')
            
            if es_noticia_excluible(titulo, desc):
                continue
            
            noticias.append({
                'titulo': limpiar_texto(titulo),
                'descripcion': limpiar_texto(desc),
                'url': art.get('url', ''),
                'imagen': art.get('image'),
                'fuente': f"GNews:{art.get('source', {}).get('name', 'Unknown')}",
                'fecha': art.get('publishedAt'),
                'puntaje': calcular_puntaje_internacional(titulo, desc)
            })
    except Exception as e:
        log(f"Error GNews: {e}", 'advertencia')
    
    log(f"GNews: {len(noticias)} noticias", 'info')
    return noticias

def obtener_google_news_rss():
    """Obtiene noticias de Google News RSS (internacional)"""
    feeds = [
        'https://news.google.com/rss?hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERBU0FtVnVLQUFQAQ?hl=es&gl=US&ceid=US:es',
    ]
    
    noticias = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url, request_headers=headers)
            
            for entry in feed.entries[:8]:
                titulo = entry.get('title', '')
                if not titulo or '[Removed]' in titulo:
                    continue
                
                if ' - ' in titulo:
                    titulo = titulo.rsplit(' - ', 1)[0]
                
                link = entry.get('link', '')
                try:
                    resp = requests.head(link, allow_redirects=True, timeout=8, headers=headers)
                    link_final = resp.url
                except:
                    link_final = link
                
                if es_noticia_excluible(titulo):
                    continue
                
                noticias.append({
                    'titulo': limpiar_texto(titulo),
                    'descripcion': '',
                    'url': link_final,
                    'imagen': None,
                    'fuente': 'Google News',
                    'fecha': entry.get('published'),
                    'puntaje': calcular_puntaje_internacional(titulo, '')
                })
        except Exception as e:
            log(f"Error Google RSS: {e}", 'debug')
    
    log(f"Google News RSS: {len(noticias)} noticias", 'info')
    return noticias

# =============================================================================
# PROCESAMIENTO Y PUBLICACIÓN MEJORADOS
# =============================================================================

def extraer_imagen_web(url):
    """Intenta extraer imagen de la URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for meta in ['og:image', 'twitter:image']:
            tag = soup.find('meta', property=meta) or soup.find('meta', attrs={'name': meta})
            if tag:
                img_url = tag.get('content', '')
                if img_url and img_url.startswith('http'):
                    return img_url
        
        img = soup.find('img')
        if img:
            src = img.get('src', '')
            if src and src.startswith('http'):
                return src
    except:
        pass
    return None

def descargar_imagen(url):
    """Descarga y optimiza imagen"""
    if not url or not url.startswith('http'):
        return None
    try:
        from PIL import Image
        from io import BytesIO
        
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code != 200:
            return None
        
        img = Image.open(BytesIO(resp.content))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        img.thumbnail((1200, 1200))
        
        temp_path = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
    except:
        return None

def crear_imagen_titulo(titulo):
    """Crea imagen con el título"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.new('RGB', (1200, 630), color='#1e3a8a')
        draw = ImageDraw.Draw(img)
        
        try:
            font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_big = ImageFont.load_default()
            font_small = font_big
        
        titulo_envuelto = textwrap.fill(titulo[:130], width=38)
        draw.text((50, 80), titulo_envuelto, font=font_big, fill='white')
        
        draw.text((50, 550), "🌍 Noticias Internacionales • Verdad Hoy", font=font_small, fill='#93c5fd')
        
        temp_path = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
    except:
        return None

def generar_hashtags_internacional(titulo, descripcion):
    """Genera hashtags relevantes para noticias internacionales"""
    texto = f"{titulo} {descripcion}".lower()
    hashtags = ['#NoticiasInternacionales', '#ÚltimaHora']
    
    temas = {
        'guerra|conflicto|ataque|bombardeo': '#ConflictoArmado',
        'ucrania|rusia': '#UcraniaRusia',
        'gaza|israel|palestina': '#IsraelGaza',
        'trump|biden|putin|zelensky': '#PolíticaGlobal',
        'economía|mercados|inflación|recesión': '#EconomíaMundial',
        'clima|calentamiento|desastre|terremoto': '#CrisisClimática',
        'onu|otan|ue|g7|g20': '#DiplomaciaInternacional',
        'pandemia|virus|covid': '#SaludGlobal',
    }
    
    for patron, tag in temas.items():
        if re.search(patron, texto):
            hashtags.append(tag)
            break
    
    hashtags.append('#Mundo')
    return ' '.join(hashtags)

def redactar_texto_profesional(titulo, descripcion, fuente):
    """
    Genera un texto completo y profesional para la publicación.
    Evita cortes abruptos y mantiene tono informativo de agencia de noticias.
    SIN ENLACES NI URLs.
    """
    # Limpiar y preparar el contenido base
    titulo_limpio = limpiar_texto(titulo)
    desc_limpia = limpiar_texto(descripcion)
    
    # Seleccionar plantillas aleatorias para variedad
    apertura = random.choice(PLANTILLAS_APERTURA).format(titulo=titulo_limpio)
    
    # Construir el cuerpo del texto
    parrafos = []
    
    # Primer párrafo: Introducción con el título como gancho
    parrafos.append(f"📰 {apertura}")
    parrafos.append("")  # Línea en blanco
    
    # Segundo párrafo: Descripción procesada o contenido generado
    if len(desc_limpia) > 50:
        # Si tenemos descripción válida, la usamos con una plantilla de desarrollo
        plantilla_dev = random.choice(PLANTILLAS_DESARROLLO)
        
        # Asegurar que la descripción no termine truncada
        # Buscar la última oración completa (terminada en .!? y seguida de espacio o fin)
        oraciones = re.split(r'(?<=[.!?])\s+', desc_limpia)
        
        # Filtrar oraciones muy cortas (probablemente truncadas) y reconstruir
        oraciones_completas = []
        for oracion in oraciones:
            oracion = oracion.strip()
            if len(oracion) > 20:  # Evitar fragmentos muy cortos
                oraciones_completas.append(oracion)
        
        if oraciones_completas:
            contenido = ' '.join(oraciones_completas)
            # Asegurar que termine en punto
            if contenido[-1] not in '.!?':
                contenido += '.'
            parrafos.append(plantilla_dev.format(contenido=contenido))
        else:
            # Si no hay oraciones completas, generar texto genérico profesional
            parrafos.append(plantilla_dev.format(
                contenido=f"se reportan desarrollos importantes relacionados con esta información internacional que está siendo seguida por medios de comunicación globales."
            ))
    else:
        # Si no hay descripción, generar texto profesional genérico
        parrafos.append(random.choice(PLANTILLAS_DESARROLLO).format(
            contenido=f"medios internacionales están reportando este acontecimiento de relevancia global. Los detalles específicos están siendo verificados por corresponsales en la región."
        ))
    
    parrafos.append("")  # Línea en blanco
    
    # Tercer párrafo: Contexto o cierre
    parrafos.append(random.choice(PLANTILLAS_CIERRE))
    
    # Cuarto párrafo: Solo mención de fuente, sin enlace
    parrafos.append("")
    parrafos.append(f"📎 Información proporcionada por: {fuente}")
    
    # Unir todo con saltos de línea apropiados
    texto_completo = '\n'.join(parrafos)
    
    # Verificación final: eliminar cualquier URL residual
    texto_completo = re.sub(r'https?://\S+', '', texto_completo)
    texto_completo = re.sub(r'www\.\S+', '', texto_completo)
    
    # Eliminar líneas vacías múltiples
    texto_completo = re.sub(r'\n{3,}', '\n\n', texto_completo)
    
    return texto_completo.strip()

def publicar_facebook(titulo, texto_completo, imagen_path, hashtags):
    """Publica en Facebook con texto profesional completo SIN ENLACES"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales Facebook", 'error')
        return False
    
    # Construir mensaje final sin ningún enlace
    mensaje = f"{texto_completo}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    
    # Verificar límite de caracteres de Facebook (aproximadamente 2000 para posts con imagen)
    if len(mensaje) > 1900:
        # Truncar inteligentemente manteniendo coherencia
        partes = texto_completo.split('\n\n')
        texto_cortado = ""
        for parte in partes:
            if len(texto_cortado + parte + "\n\n") < 1500:
                texto_cortado += parte + "\n\n"
            else:
                break
        
        mensaje = f"{texto_cortado}[Información en desarrollo]\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    
    # Limpieza final: asegurar que no quedó ningún enlace
    mensaje = re.sub(r'https?://\S+', '', mensaje)
    mensaje = re.sub(r'www\.\S+', '', mensaje)
    mensaje = re.sub(r'\n{3,}', '\n\n', mensaje)
    mensaje = mensaje.strip()
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('imagen.jpg', f, 'image/jpeg')}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN}
            
            resp = requests.post(url, files=files, data=data, timeout=60)
            result = resp.json()
        
        if resp.status_code == 200 and 'id' in result:
            log(f"✅ Publicado ID: {result['id']}", 'exito')
            return True
        else:
            log(f"Error FB: {result.get('error', {}).get('message', 'Unknown')}", 'error')
            return False
    except Exception as e:
        log(f"Error publicando: {e}", 'error')
        return False

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS INTERNACIONALES")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Frecuencia: Cada {TIEMPO_ENTRE_PUBLICACIONES} minutos")
    print("🎯 Foco: Conflictos, Política Global, Economía Mundial")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    historial = cargar_historial()
    log(f"📊 Historial: {len(historial.get('urls', []))} URLs guardadas (ventana {VENTANA_DUPLICADOS_HORAS}h)")
    
    todas_noticias = []
    
    if NEWS_API_KEY:
        noticias = obtener_newsapi_internacional()
        todas_noticias.extend(noticias)
    
    if NEWSDATA_API_KEY and len(todas_noticias) < 15:
        noticias = obtener_newsdata_internacional()
        todas_noticias.extend(noticias)
    
    if GNEWS_API_KEY and len(todas_noticias) < 20:
        noticias = obtener_gnews_internacional()
        todas_noticias.extend(noticias)
    
    if len(todas_noticias) < 25:
        noticias = obtener_google_news_rss()
        todas_noticias.extend(noticias)
    
    log(f"📰 Total recolectadas: {len(todas_noticias)} noticias")
    
    if not todas_noticias:
        log("ERROR: No se encontraron noticias", 'error')
        return False
    
    todas_noticias.sort(key=lambda x: x.get('puntaje', 0), reverse=True)
    
    log("🏆 Top 5 noticias por relevancia:", 'debug')
    for i, n in enumerate(todas_noticias[:5]):
        log(f"   {i+1}. [{n['puntaje']}] {n['titulo'][:50]}...", 'debug')
    
    noticia_seleccionada = None
    intentos = 0
    
    for noticia in todas_noticias:
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        
        if not url or not titulo:
            continue
        
        intentos += 1
        
        if noticia_ya_publicada(historial, url, titulo):
            log(f"⏭️  Ya publicada: {titulo[:40]}...", 'debug')
            continue
        
        if noticia.get('puntaje', 0) < 5:
            log(f"⏭️  Puntaje bajo ({noticia['puntaje']}): {titulo[:40]}...", 'debug')
            continue
        
        noticia_seleccionada = noticia
        break
    
    log(f"🔍 Revisadas: {intentos} noticias")
    
    if not noticia_seleccionada:
        log("⚠️  Buscando mejor opción disponible...", 'advertencia')
        for noticia in todas_noticias:
            if noticia.get('puntaje', 0) > 0:
                noticia_seleccionada = noticia
                break
    
    if not noticia_seleccionada:
        log("ERROR: No hay noticias disponibles para publicar", 'error')
        return False
    
    log(f"\n📝 NOTICIA SELECCIONADA:")
    log(f"   Título: {noticia_seleccionada['titulo']}")
    log(f"   Puntaje: {noticia_seleccionada['puntaje']}")
    log(f"   Fuente: {noticia_seleccionada['fuente']}")
    
    # =================================================================
    # NUEVO SISTEMA DE REDACCIÓN PROFESIONAL SIN ENLACES
    # =================================================================
    
    log("📝 Redactando texto profesional...")
    
    # Generar texto completo y profesional
    texto_profesional = redactar_texto_profesional(
        noticia_seleccionada['titulo'],
        noticia_seleccionada.get('descripcion', ''),
        noticia_seleccionada['fuente']
    )
    
    # Generar hashtags
    hashtags = generar_hashtags_internacional(
        noticia_seleccionada['titulo'], 
        noticia_seleccionada.get('descripcion', '')
    )
    
    # Obtener imagen
    log("🖼️  Procesando imagen...")
    imagen_path = None
    
    if noticia_seleccionada.get('imagen'):
        imagen_path = descargar_imagen(noticia_seleccionada['imagen'])
    
    if not imagen_path:
        img_url = extraer_imagen_web(noticia_seleccionada['url'])
        if img_url:
            imagen_path = descargar_imagen(img_url)
    
    if not imagen_path:
        imagen_path = crear_imagen_titulo(noticia_seleccionada['titulo'])
    
    if not imagen_path:
        log("ERROR: No se pudo crear imagen", 'error')
        return False
    
    # Publicar con el nuevo texto profesional sin enlaces
    exito = publicar_facebook(
        noticia_seleccionada['titulo'],
        texto_profesional,
        imagen_path,
        hashtags
    )
    
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        guardar_historial(historial, noticia_seleccionada['url'], noticia_seleccionada['titulo'])
        
        estado = cargar_estado()
        estado['ultima_publicacion'] = datetime.now().isoformat()
        guardar_estado(estado)
        
        hist_actualizado = cargar_historial()
        total = hist_actualizado.get('estadisticas', {}).get('total_publicadas', 0)
        log(f"✅ ÉXITO - Total acumulado: {total} noticias", 'exito')
        return True
    
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
