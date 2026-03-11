#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias para Facebook - API First (NewsAPI, NewsData, Google News)
- Prioridad: NewsAPI > NewsData > Google News > RSS tradicionales
- Anti-duplicados: Sistema robusto de hashes + ventana temporal de 48h
- Frecuencia: 1 hora entre publicaciones
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
from urllib.parse import urlparse, quote

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

TIEMPO_ENTRE_PUBLICACIONES = 60
VENTANA_DUPLICADOS_HORAS = 48

# =============================================================================
# PALABRAS CLAVE
# =============================================================================

PALABRAS_CLAVE = [
    'urgente', 'última hora', 'breaking', 'alerta', 'crisis', 'guerra', 'conflicto',
    'ataque', 'bombardeo', 'invasión', 'polémica', 'escándalo', 'revelan', 'confirmado',
    'histórico', 'sin precedentes', 'impactante', 'grave', 'tensión', 'protesta',
    'gobierno', 'presidente', 'elecciones', 'economía', 'mercado', 'bolsa',
    'pandemia', 'virus', 'vacuna', 'cambio climático', 'desastre', 'tragedia',
    'muere', 'fallece', 'asesinato', 'detenido', 'operativo', 'rescate',
    'acuerdo', 'tratado', 'sanciones', 'inflación', 'recesión', 'huelga',
    'manifestación', 'violencia', 'ataque terrorista', 'golpe de estado',
    'dimisión', 'renuncia', 'corrupción', 'fraude', 'investigación', 'juicio',
    'sentencia', 'extradición', 'frontera', 'migración', 'refugiados',
    'terremoto', 'huracán', 'inundación', 'incendio', 'accidente', 'avión',
    'nuclear', 'arma', 'misil', 'dron', 'ciberataque', 'hackeo',
    'descubrimiento', 'avance', 'innovación', 'record', 'máximo histórico',
    'mínimo histórico', 'colapso', 'quiebra', 'rescate', 'ayuda',
    'Trump', 'Biden', 'Putin', 'Zelensky', 'Maduro', 'Milei', 'Bukele',
    'México', 'Argentina', 'España', 'Colombia', 'Chile', 'Perú', 'Ecuador',
    'tecnología', 'inteligencia artificial', 'IA', 'bitcoin', 'cripto'
]

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    icono = iconos.get(tipo, 'ℹ️')
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {icono} {mensaje}")
    if tipo == 'error':
        print(f"::error::{mensaje}")

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
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
    if not texto:
        return ""
    texto_normalizado = re.sub(r'[^\w\s]', '', texto.lower().strip())
    texto_normalizado = re.sub(r'\s+', ' ', texto_normalizado)
    return hashlib.sha256(texto_normalizado.encode()).hexdigest()

def limpiar_texto_final(texto):
    if not texto:
        return ""
    
    texto = html_module.unescape(texto)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1. \2', texto)
    texto = re.sub(r'\.([A-Za-zÁÉÍÓÚáéíóúÑñ])', r'. \1', texto)
    texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
    texto = re.sub(r'\.+', '.', texto)
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.replace('…', '...').replace('–', '-').replace('—', '-')
    texto = texto.replace('"', '"').replace('"', '"')
    texto = texto.replace(''', "'").replace(''', "'")
    
    return texto.strip()

def es_noticia_reciente(fecha_str):
    if not fecha_str:
        return True
    try:
        formatos = ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %z']
        for fmt in formatos:
            try:
                fecha = datetime.strptime(fecha_str, fmt)
                diferencia = datetime.utcnow() - fecha
                return diferencia <= timedelta(hours=24)
            except:
                continue
        return True
    except:
        return True

# =============================================================================
# GESTIÓN DE ESTADO Y ESTADÍSTICAS
# =============================================================================

def cargar_historial():
    default = {
        'urls': [], 
        'titulos_hashes': [],
        'contenidos_hashes': [],
        'timestamps': [],
        'ultima_publicacion': None,
        'estadisticas': {
            'total_publicadas': 0,
            'por_fuente': {}
        }
    }
    datos = cargar_json(HISTORIAL_PATH, default)
    # Asegurar que todas las claves existan
    for key in default:
        if key not in datos:
            datos[key] = default[key]
    return datos

def limpiar_historial_antiguo(historial):
    """Elimina entradas antiguas del historial (más de 48h)"""
    ahora = datetime.now()
    indices_validos = []
    
    timestamps = historial.get('timestamps', [])
    for i, ts_str in enumerate(timestamps):
        try:
            ts = datetime.fromisoformat(ts_str)
            if (ahora - ts) < timedelta(hours=VENTANA_DUPLICADOS_HORAS):
                indices_validos.append(i)
        except:
            continue
    
    # Filtrar todas las listas manteniendo solo índices válidos
    for key in ['urls', 'titulos_hashes', 'contenidos_hashes', 'timestamps']:
        if key in historial:
            lista_original = historial[key]
            historial[key] = [lista_original[i] for i in indices_validos if i < len(lista_original)]
    
    return historial

def guardar_historial(historial, url, titulo, contenido, fuente):
    """Guarda noticia en historial con múltiples hashes"""
    historial = limpiar_historial_antiguo(historial)
    
    hash_titulo = generar_hash(titulo)
    hash_contenido = generar_hash(contenido[:200]) if contenido else hash_titulo
    url_limpia = re.sub(r'\?.*$', '', url)
    
    ahora = datetime.now().isoformat()
    
    historial['urls'].append(url_limpia)
    historial['titulos_hashes'].append(hash_titulo)
    historial['contenidos_hashes'].append(hash_contenido)
    historial['timestamps'].append(ahora)
    historial['ultima_publicacion'] = ahora
    
    if 'estadisticas' not in historial:
        historial['estadisticas'] = {'total_publicadas': 0, 'por_fuente': {}}
    
    historial['estadisticas']['total_publicadas'] += 1
    if fuente not in historial['estadisticas']['por_fuente']:
        historial['estadisticas']['por_fuente'][fuente] = 0
    historial['estadisticas']['por_fuente'][fuente] += 1
    
    # Limitar a últimas 1000
    max_historial = 1000
    for key in ['urls', 'titulos_hashes', 'contenidos_hashes', 'timestamps']:
        if len(historial[key]) > max_historial:
            historial[key] = historial[key][-max_historial:]
    
    guardar_json(HISTORIAL_PATH, historial)

def noticia_ya_publicada(historial, url, titulo, descripcion=""):
    """Verificación robusta de duplicados"""
    if not historial:
        return False
    
    historial = limpiar_historial_antiguo(historial)
    
    url_limpia = re.sub(r'\?.*$', '', url)
    url_base = re.sub(r'https?://(www\.)?', '', url_limpia).rstrip('/')
    
    # Verificar URL
    for url_hist in historial.get('urls', []):
        url_hist_limpia = re.sub(r'\?.*$', '', url_hist)
        url_hist_base = re.sub(r'https?://(www\.)?', '', url_hist_limpia).rstrip('/')
        
        if url_limpia == url_hist_limpia or url_base == url_hist_base:
            return True
        
        if url_base.split('/')[-1] == url_hist_base.split('/')[-1] and len(url_base.split('/')[-1]) > 20:
            return True
    
    # Verificar hash de título
    hash_titulo = generar_hash(titulo)
    if hash_titulo in historial.get('titulos_hashes', []):
        return True
    
    # Verificar hash de contenido
    contenido_combinado = f"{titulo} {descripcion}"[:200]
    hash_contenido = generar_hash(contenido_combinado)
    if hash_contenido in historial.get('contenidos_hashes', []):
        return True
    
    return False

def cargar_estado():
    default = {'ultima_publicacion': None, 'ultima_fuente': None, 'conteo_hoy': 0}
    datos = cargar_json(ESTADO_PATH, default)
    for key in default:
        if key not in datos:
            datos[key] = default[key]
    return datos

def guardar_estado(estado):
    guardar_json(ESTADO_PATH, estado)

def verificar_tiempo_entre_publicaciones():
    estado = cargar_estado()
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        diferencia = datetime.now() - ultima_dt
        minutos_transcurridos = diferencia.total_seconds() / 60
        
        if minutos_transcurridos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️  Esperando... Última publicación hace {minutos_transcurridos:.0f} minutos", 'info')
            return False
        return True
    except:
        return True

# =============================================================================
# FUENTES DE NOTICIAS
# =============================================================================

def obtener_noticias_newsapi():
    if not NEWS_API_KEY:
        return []
    
    noticias = []
    try:
        endpoints = [
            ('https://newsapi.org/v2/top-headlines', {'apiKey': NEWS_API_KEY, 'language': 'es', 'pageSize': 20}),
            ('https://newsapi.org/v2/everything', {'apiKey': NEWS_API_KEY, 'q': 'news', 'language': 'es', 'sortBy': 'publishedAt', 'pageSize': 20})
        ]
        
        for endpoint, params in endpoints:
            try:
                resp = requests.get(endpoint, params=params, timeout=15)
                data = resp.json()
                
                if data.get('status') == 'ok':
                    for article in data.get('articles', []):
                        titulo = article.get('title', '')
                        if not titulo or '[Removed]' in titulo:
                            continue
                        
                        noticias.append({
                            'titulo': limpiar_texto_final(titulo),
                            'descripcion': limpiar_texto_final(article.get('description', '')),
                            'url': article.get('url', ''),
                            'imagen': article.get('urlToImage'),
                            'fuente': f"NewsAPI:{article.get('source', {}).get('name', 'Desconocido')}",
                            'fecha': article.get('publishedAt'),
                            'puntaje': calcular_puntaje(titulo, article.get('description', '')) + 5
                        })
            except:
                continue
                
    except Exception as e:
        log(f"Error NewsAPI: {e}", 'advertencia')
    
    log(f"NewsAPI: {len(noticias)} noticias", 'debug')
    return noticias

def obtener_noticias_newsdata():
    if not NEWSDATA_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://newsdata.io/api/1/news'
        params = {'apikey': NEWSDATA_API_KEY, 'language': 'es', 'size': 20}
        
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        if data.get('status') == 'success':
            for article in data.get('results', []):
                titulo = article.get('title', '')
                if not titulo:
                    continue
                
                noticias.append({
                    'titulo': limpiar_texto_final(titulo),
                    'descripcion': limpiar_texto_final(article.get('description', '')),
                    'url': article.get('link', ''),
                    'imagen': article.get('image_url'),
                    'fuente': f"NewsData:{article.get('source_id', 'Desconocido')}",
                    'fecha': article.get('pubDate'),
                    'puntaje': calcular_puntaje(titulo, article.get('description', '')) + 4
                })
    except Exception as e:
        log(f"Error NewsData: {e}", 'advertencia')
    
    log(f"NewsData: {len(noticias)} noticias", 'debug')
    return noticias

def obtener_noticias_gnews():
    if not GNEWS_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 20}
        
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        for article in data.get('articles', []):
            titulo = article.get('title', '')
            if not titulo:
                continue
            
            noticias.append({
                'titulo': limpiar_texto_final(titulo),
                'descripcion': limpiar_texto_final(article.get('description', '')),
                'url': article.get('url', ''),
                'imagen': article.get('image'),
                'fuente': f"GNews:{article.get('source', {}).get('name', 'Desconocido')}",
                'fecha': article.get('publishedAt'),
                'puntaje': calcular_puntaje(titulo, article.get('description', '')) + 3
            })
    except Exception as e:
        log(f"Error GNews: {e}", 'advertencia')
    
    log(f"GNews: {len(noticias)} noticias", 'debug')
    return noticias

def obtener_noticias_google_news_rss():
    feeds = [
        'https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es',
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=ES&ceid=ES:es',
        'https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERBU0FtVnVLQUFQAQ?hl=es&gl=ES&ceid=ES:es',
    ]
    
    noticias = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url, request_headers=headers)
            
            for entry in feed.entries[:10]:
                titulo = entry.get('title', '')
                if not titulo or '[Removed]' in titulo:
                    continue
                
                if ' - ' in titulo:
                    titulo = titulo.rsplit(' - ', 1)[0]
                
                link = entry.get('link', '')
                try:
                    resp = requests.head(link, allow_redirects=True, timeout=10, headers=headers)
                    link_final = resp.url
                except:
                    link_final = link
                
                noticias.append({
                    'titulo': limpiar_texto_final(titulo),
                    'descripcion': '',
                    'url': link_final,
                    'imagen': None,
                    'fuente': 'Google News RSS',
                    'fecha': entry.get('published'),
                    'puntaje': calcular_puntaje(titulo, '')
                })
        except:
            continue
    
    log(f"Google News RSS: {len(noticias)} noticias", 'debug')
    return noticias

def obtener_noticias_rss_tradicionales():
    feeds = [
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        'https://rss.cnn.com/rss/edition.rss',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
        'https://e00-elmundo.uecdn.es/rss/portada.xml',
        'https://www.infobae.com/feeds/rss/',
    ]
    
    noticias = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    feeds_seleccionados = random.sample(feeds, min(3, len(feeds)))
    
    for feed_url in feeds_seleccionados:
        try:
            feed = feedparser.parse(feed_url, request_headers=headers)
            fuente = feed.feed.get('title', feed_url.split('/')[2]).replace('RSS', '').strip()
            
            for entry in feed.entries[:5]:
                titulo = entry.get('title', '')
                if not titulo or '[Removed]' in titulo:
                    continue
                
                if ' - ' in titulo:
                    titulo = titulo.rsplit(' - ', 1)[0]
                
                imagen = None
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    imagen = entry.enclosures[0].get('href', '')
                
                noticias.append({
                    'titulo': limpiar_texto_final(titulo),
                    'descripcion': limpiar_texto_final(entry.get('summary', '')),
                    'url': entry.get('link', ''),
                    'imagen': imagen,
                    'fuente': fuente,
                    'fecha': entry.get('published'),
                    'puntaje': calcular_puntaje(titulo, entry.get('summary', ''))
                })
        except:
            continue
    
    log(f"RSS Tradicionales: {len(noticias)} noticias", 'debug')
    return noticias

def calcular_puntaje(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    for palabra in PALABRAS_CLAVE:
        if palabra.lower() in texto:
            puntaje += 3 if palabra in ['urgente', 'breaking', 'última hora', 'alerta'] else 1
    
    if 40 <= len(titulo) <= 100:
        puntaje += 2
    
    if len(titulo) < 20 or len(titulo) > 150:
        puntaje -= 2
    
    if descripcion and len(descripcion) > 100:
        puntaje += 1
    
    return puntaje

# =============================================================================
# EXTRACCIÓN WEB Y GENERACIÓN DE CONTENIDO
# =============================================================================

def extraer_contenido_web(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'ads']):
            elem.decompose()
        
        resultado = {'titulo': '', 'descripcion': '', 'imagen': None}
        
        h1 = soup.find('h1')
        if h1:
            resultado['titulo'] = limpiar_texto_final(h1.get_text())
        
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
        if meta_desc:
            resultado['descripcion'] = limpiar_texto_final(meta_desc.get('content', ''))
        
        selectores = ['article', '[class*="article-body"]', '[class*="content"]', '[class*="post-content"]', 'main', '.entry-content', '#article-body']
        
        contenido = None
        for selector in selectores:
            contenido = soup.select_one(selector)
            if contenido:
                break
        
        if contenido:
            parrafos = []
            for p in contenido.find_all(['p', 'h2', 'h3']):
                texto = p.get_text(strip=True)
                texto = limpiar_texto_final(texto)
                if len(texto) > 60 and len(texto) < 500:
                    parrafos.append(texto)
            
            if parrafos:
                resultado['descripcion'] = '\n\n'.join(parrafos[:3])
        
        og_image = soup.find('meta', property='og:image')
        if og_image:
            img_url = og_image.get('content', '')
            if img_url and not any(x in img_url.lower() for x in ['logo', 'icon', 'avatar']):
                resultado['imagen'] = img_url
        
        if not resultado['imagen']:
            twitter_img = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_img:
                resultado['imagen'] = twitter_img.get('content', '')
        
        return resultado
    except:
        return None

def generar_texto_publicacion(noticia):
    url = noticia['url']
    datos_web = extraer_contenido_web(url)
    
    if datos_web and datos_web.get('descripcion') and len(datos_web['descripcion']) > 150:
        descripcion = datos_web['descripcion']
    else:
        descripcion = noticia.get('descripcion', '')
        if len(descripcion) < 100:
            descripcion = f"{noticia['titulo']}. Los detalles de esta información están siendo verificados por nuestras fuentes."
    
    descripcion = limpiar_texto_final(descripcion)
    
    if len(descripcion) > 1200:
        descripcion = descripcion[:1200].rsplit('.', 1)[0] + '.'
    
    texto_final = f"{descripcion}\n\n📰 Fuente: {noticia['fuente']}"
    return limpiar_texto_final(texto_final)

def generar_hashtags(noticia):
    texto = f"{noticia['titulo']}".lower()
    hashtags = ['#Noticias', '#ÚltimaHora']
    
    temas = {
        'política': '#Política', 'gobierno': '#Política', 'economía': '#Economía',
        'mercado': '#Economía', 'guerra': '#Internacional', 'conflicto': '#Internacional',
        'deporte': '#Deportes', 'fútbol': '#Deportes', 'tecnología': '#Tecnología',
        'ciencia': '#Ciencia', 'salud': '#Salud', 'música': '#Entretenimiento', 'cine': '#Entretenimiento'
    }
    
    for palabra, tag in temas.items():
        if palabra in texto:
            hashtags.append(tag)
            break
    
    paises = {
        'mexico': '#México', 'españa': '#España', 'argentina': '#Argentina',
        'colombia': '#Colombia', 'chile': '#Chile', 'peru': '#Perú',
        'eeuu': '#EEUU', 'estados unidos': '#EEUU', 'europa': '#Europa'
    }
    
    for pais, tag in paises.items():
        if pais in texto:
            hashtags.append(tag)
            break
    
    return ' '.join(hashtags)

# =============================================================================
# IMÁGENES Y PUBLICACIÓN
# =============================================================================

def descargar_imagen(url):
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
        
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        temp_path = f'/tmp/noticia_{generar_hash(url)[:10]}.jpg'
        img.save(temp_path, 'JPEG', quality=85, optimize=True)
        return temp_path
        
    except:
        return None

def crear_imagen_texto(titulo):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.new('RGB', (1200, 630), color='#1e3a8a')
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            font_title = ImageFont.load_default()
            font_sub = font_title
        
        titulo_wrapped = textwrap.fill(titulo[:140], width=35)
        draw.text((60, 80), titulo_wrapped, font=font_title, fill='white')
        draw.text((60, 550), "Verdad Hoy • Noticias al minuto", font=font_sub, fill='#93c5fd')
        
        temp_path = f'/tmp/noticia_gen_{generar_hash(titulo)[:10]}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
        
    except:
        return None

def publicar_en_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales de Facebook", 'error')
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto 🌐"
    
    if len(mensaje) > 1900:
        texto_corto = texto[:1500].rsplit('.', 1)[0] + '.'
        mensaje = f"{texto_corto}\n\n[Leer noticia completa en el enlace]\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto 🌐"
    
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
            log(f"Error Facebook: {result.get('error', {}).get('message', 'Unknown')}", 'error')
            return False
            
    except Exception as e:
        log(f"Error publicando: {e}", 'error')
        return False

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🤖 BOT DE NOTICIAS - FACEBOOK")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Frecuencia: Cada {TIEMPO_ENTRE_PUBLICACIONES} minutos")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    if not verificar_tiempo_entre_publicaciones():
        return False
    
    historial = cargar_historial()
    estado = cargar_estado()
    
    stats = historial.get('estadisticas', {})
    log(f"📊 Total publicadas histórico: {stats.get('total_publicadas', 0)}")
    
    # OBTENER NOTICIAS
    todas_noticias = []
    
    if NEWS_API_KEY:
        log("🔍 Consultando NewsAPI...", 'info')
        noticias = obtener_noticias_newsapi()
        todas_noticias.extend(noticias)
    
    if NEWSDATA_API_KEY and len(todas_noticias) < 10:
        log("🔍 Consultando NewsData.io...", 'info')
        noticias = obtener_noticias_newsdata()
        todas_noticias.extend(noticias)
    
    if GNEWS_API_KEY and len(todas_noticias) < 10:
        log("🔍 Consultando GNews...", 'info')
        noticias = obtener_noticias_gnews()
        todas_noticias.extend(noticias)
    
    if len(todas_noticias) < 15:
        log("🔍 Consultando Google News RSS...", 'info')
        noticias = obtener_noticias_google_news_rss()
        todas_noticias.extend(noticias)
    
    if len(todas_noticias) < 20:
        log("🔍 Consultando RSS tradicionales...", 'info')
        noticias = obtener_noticias_rss_tradicionales()
        todas_noticias.extend(noticias)
    
    log(f"📰 Total noticias recolectadas: {len(todas_noticias)}")
    
    if not todas_noticias:
        log("No se encontraron noticias", 'error')
        return False
    
    # FILTRAR Y SELECCIONAR
    todas_noticias.sort(key=lambda x: x.get('puntaje', 0), reverse=True)
    
    noticia_seleccionada = None
    
    for noticia in todas_noticias:
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        descripcion = noticia.get('descripcion', '')
        
        if not url or not titulo:
            continue
        
        if noticia_ya_publicada(historial, url, titulo, descripcion):
            log(f"⏭️  Duplicado: {titulo[:50]}...", 'debug')
            continue
        
        if not es_noticia_reciente(noticia.get('fecha')):
            continue
        
        noticia_seleccionada = noticia
        break
    
    if not noticia_seleccionada:
        log("Todas las noticias ya fueron publicadas", 'advertencia')
        return False
    
    # PUBLICAR
    log(f"\n📝 NOTICIA SELECCIONADA:")
    log(f"   Título: {noticia_seleccionada['titulo'][:70]}...")
    log(f"   Fuente: {noticia_seleccionada['fuente']}")
    
    texto = generar_texto_publicacion(noticia_seleccionada)
    hashtags = generar_hashtags(noticia_seleccionada)
    
    log("🖼️  Procesando imagen...")
    imagen_path = None
    
    if noticia_seleccionada.get('imagen'):
        imagen_path = descargar_imagen(noticia_seleccionada['imagen'])
    
    if not imagen_path:
        datos_web = extraer_contenido_web(noticia_seleccionada['url'])
        if datos_web and datos_web.get('imagen'):
            imagen_path = descargar_imagen(datos_web['imagen'])
    
    if not imagen_path:
        imagen_path = crear_imagen_texto(noticia_seleccionada['titulo'])
    
    if not imagen_path:
        log("ERROR: No se pudo obtener imagen", 'error')
        return False
    
    exito = publicar_en_facebook(noticia_seleccionada['titulo'], texto, imagen_path, hashtags)
    
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        guardar_historial(
            historial, 
            noticia_seleccionada['url'], 
            noticia_seleccionada['titulo'],
            noticia_seleccionada.get('descripcion', ''),
            noticia_seleccionada['fuente']
        )
        
        estado['ultima_publicacion'] = datetime.now().isoformat()
        estado['ultima_fuente'] = noticia_seleccionada['fuente']
        guardar_estado(estado)
        
        historial_actualizado = cargar_historial()
        stats = historial_actualizado.get('estadisticas', {})
        log(f"📈 Total acumulado: {stats.get('total_publicadas', 0)} noticias", 'exito')
        
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
