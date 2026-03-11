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
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')  # Opcional: Google News via API
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')

# TIEMPO: Publicar cada 1 HORA (60 minutos)
TIEMPO_ENTRE_PUBLICACIONES = 60  # minutos

# Ventana de tiempo para considerar noticia como "ya publicada" (48 horas)
VENTANA_DUPLICADOS_HORAS = 48

# Prioridad de fuentes (orden de intento)
# 1. NewsAPI (requiere API key)
# 2. NewsData.io (requiere API key)  
# 3. GNews API (opcional, requiere API key)
# 4. Google News RSS (fallback)
# 5. RSS tradicionales (último recurso)

# =============================================================================
# PALABRAS CLAVE PARA RELEVANCIA
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
    return default

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
    return hashlib.sha256(texto_normalizado.encode()).hexdigest()

def limpiar_texto_final(texto):
    """Limpieza profesional final"""
    if not texto:
        return ""
    
    texto = html_module.unescape(texto)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    
    # Corregir palabras pegadas
    texto = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1. \2', texto)
    texto = re.sub(r'\.([A-Za-zÁÉÍÓÚáéíóúÑñ])', r'. \1', texto)
    texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
    texto = re.sub(r'\.+', '.', texto)
    texto = re.sub(r'\s+', ' ', texto)
    
    # Caracteres especiales
    texto = texto.replace('…', '...').replace('–', '-').replace('—', '-')
    texto = texto.replace('"', '"').replace('"', '"')
    texto = texto.replace(''', "'").replace(''', "'")
    
    return texto.strip()

def es_noticia_reciente(fecha_str):
    """Verifica si la noticia es reciente (últimas 24h)"""
    if not fecha_str:
        return True
    try:
        # Intentar parsear diferentes formatos de fecha
        for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %z']:
            try:
                fecha = datetime.strptime(fecha_str, fmt)
                break
            except:
                continue
        else:
            return True
        
        diferencia = datetime.utcnow() - fecha
        return diferencia <= timedelta(hours=24)
    except:
        return True

# =============================================================================
# GESTIÓN DE ESTADO Y ESTADÍSTICAS MEJORADA
# =============================================================================

def cargar_historial():
    default = {
        'urls': [], 
        'titulos_hashes': [],  # Hashes de títulos
        'contenidos_hashes': [],  # Hashes de contenido
        'timestamps': [],  # Cuándo se publicó
        'ultima_publicacion': None,
        'estadisticas': {
            'total_publicadas': 0,
            'por_fuente': {}
        }
    }
    return cargar_json(HISTORIAL_PATH, default)

def limpiar_historial_antiguo(historial):
    """Elimina entradas antiguas del historial (más de 48h)"""
    ahora = datetime.now()
    indices_a_mantener = []
    
    for i, ts_str in enumerate(historial.get('timestamps', [])):
        try:
            ts = datetime.fromisoformat(ts_str)
            if (ahora - ts) < timedelta(hours=VENTANA_DUPLICADOS_HORAS):
                indices_a_mantener.append(i)
        except:
            continue
    
    # Filtrar listas manteniendo solo índices recientes
    for key in ['urls', 'titulos_hashes', 'contenidos_hashes', 'timestamps']:
        if key in historial:
            historial[key] = [historial[key][i] for i in indices_a_mantener if i < len(historial[key])]
    
    return historial

def guardar_historial(historial, url, titulo, contenido, fuente):
    """Guarda noticia en historial con múltiples hashes para evitar duplicados"""
    # Limpiar historial antiguo primero
    historial = limpiar_historial_antiguo(historial)
    
    # Generar múltiples identificadores
    hash_titulo = generar_hash(titulo)
    hash_contenido = generar_hash(contenido[:200]) if contenido else hash_titulo
    url_limpia = re.sub(r'\?.*$', '', url)  # Remover parámetros de URL
    
    ahora = datetime.now().isoformat()
    
    historial['urls'].append(url_limpia)
    historial['titulos_hashes'].append(hash_titulo)
    historial['contenidos_hashes'].append(hash_contenido)
    historial['timestamps'].append(ahora)
    historial['ultima_publicacion'] = ahora
    
    # Actualizar estadísticas
    if 'estadisticas' not in historial:
        historial['estadisticas'] = {'total_publicadas': 0, 'por_fuente': {}}
    
    historial['estadisticas']['total_publicadas'] += 1
    if fuente not in historial['estadisticas']['por_fuente']:
        historial['estadisticas']['por_fuente'][fuente] = 0
    historial['estadisticas']['por_fuente'][fuente] += 1
    
    # Limitar tamaño (últimas 1000)
    max_historial = 1000
    for key in ['urls', 'titulos_hashes', 'contenidos_hashes', 'timestamps']:
        if len(historial[key]) > max_historial:
            historial[key] = historial[key][-max_historial:]
    
    guardar_json(HISTORIAL_PATH, historial)

def noticia_ya_publicada(historial, url, titulo, descripcion=""):
    """
    Verificación robusta de duplicados usando múltiples criterios
    """
    if not historial:
        return False
    
    # Limpiar historial antiguo antes de verificar
    historial = limpiar_historial_antiguo(historial)
    
    # Normalizar URL (sin parámetros)
    url_limpia = re.sub(r'\?.*$', '', url)
    url_base = re.sub(r'https?://(www\.)?', '', url_limpia).rstrip('/')
    
    # Verificar URL
    for url_hist in historial.get('urls', []):
        url_hist_limpia = re.sub(r'\?.*$', '', url_hist)
        url_hist_base = re.sub(r'https?://(www\.)?', '', url_hist_limpia).rstrip('/')
        
        # Coincidencia exacta o de base
        if url_limpia == url_hist_limpia or url_base == url_hist_base:
            return True
        
        # Verificar si son del mismo dominio y path similar (misma noticia, diferente fuente)
        if url_base.split('/')[-1] == url_hist_base.split('/')[-1] and len(url_base.split('/')[-1]) > 20:
            return True
    
    # Verificar hash de título
    hash_titulo = generar_hash(titulo)
    if hash_titulo in historial.get('titulos_hashes', []):
        return True
    
    # Verificar hash de contenido (primeros 200 chars)
    contenido_combinado = f"{titulo} {descripcion}"[:200]
    hash_contenido = generar_hash(contenido_combinado)
    if hash_contenido in historial.get('contenidos_hashes', []):
        return True
    
    # Verificación fuzzy: similitud de títulos
    titulo_normalizado = re.sub(r'[^\w]', '', titulo.lower())
    for titulo_hist_hash in historial.get('titulos_hashes', []):
        # Esto requeriría almacenar títulos completos, por ahora usamos el hash
        pass
    
    return False

def cargar_estado():
    default = {'ultima_publicacion': None, 'ultima_fuente': None, 'conteo_hoy': 0}
    return cargar_json(ESTADO_PATH, default)

def guardar_estado(estado):
    guardar_json(ESTADO_PATH, estado)

def verificar_tiempo_entre_publicaciones():
    """Verifica si ha pasado suficiente tiempo desde la última publicación"""
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
# FUENTES DE NOTICIAS PRIORITARIAS
# =============================================================================

def obtener_noticias_newsapi():
    """NewsAPI - Fuente principal (requiere API key)"""
    if not NEWS_API_KEY:
        return []
    
    noticias = []
    try:
        # Endpoints: todo y top-headlines
        endpoints = [
            'https://newsapi.org/v2/top-headlines',
            'https://newsapi.org/v2/everything'
        ]
        
        params_list = [
            {'apiKey': NEWS_API_KEY, 'language': 'es', 'pageSize': 20},
            {'apiKey': NEWS_API_KEY, 'q': 'news', 'language': 'es', 'sortBy': 'publishedAt', 'pageSize': 20}
        ]
        
        for endpoint, params in zip(endpoints, params_list):
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
                            'puntaje': calcular_puntaje(titulo, article.get('description', '')) + 5  # Bonus API
                        })
            except Exception as e:
                log(f"Error NewsAPI endpoint: {e}", 'debug')
                continue
                
    except Exception as e:
        log(f"Error NewsAPI: {e}", 'advertencia')
    
    log(f"NewsAPI: {len(noticias)} noticias", 'debug')
    return noticias

def obtener_noticias_newsdata():
    """NewsData.io - Segunda fuente prioritaria"""
    if not NEWSDATA_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://newsdata.io/api/1/news'
        params = {
            'apikey': NEWSDATA_API_KEY,
            'language': 'es',
            'size': 20
        }
        
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
    """GNews API - Tercera opción (alternativa a Google News RSS)"""
    if not GNEWS_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {
            'apikey': GNEWS_API_KEY,
            'lang': 'es',
            'max': 20
        }
        
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
    """Google News RSS - Fallback"""
    feeds = [
        'https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es',
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=ES&ceid=ES:es',
        'https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERBU0FtVnVLQUFQAQ?hl=es&gl=ES&ceid=ES:es',  # Mundo
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
                
                # Limpiar título (quitar fuente al final)
                if ' - ' in titulo:
                    titulo = titulo.rsplit(' - ', 1)[0]
                
                link = entry.get('link', '')
                # Resolver redirect de Google News
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
        except Exception as e:
            log(f"Error Google News RSS: {e}", 'debug')
    
    log(f"Google News RSS: {len(noticias)} noticias", 'debug')
    return noticias

def obtener_noticias_rss_tradicionales():
    """RSS tradicionales - Último recurso"""
    feeds = [
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        'https://rss.cnn.com/rss/edition.rss',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
        'https://e00-elmundo.uecdn.es/rss/portada.xml',
        'https://www.infobae.com/feeds/rss/',
    ]
    
    noticias = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Seleccionar 3 feeds aleatorios para variedad
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
                
                # Extraer imagen
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
        except Exception as e:
            continue
    
    log(f"RSS Tradicionales: {len(noticias)} noticias", 'debug')
    return noticias

def calcular_puntaje(titulo, descripcion):
    """Calcula relevancia de la noticia"""
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    # Palabras clave
    for palabra in PALABRAS_CLAVE:
        if palabra.lower() in texto:
            puntaje += 3 if palabra in ['urgente', 'breaking', 'última hora', 'alerta'] else 1
    
    # Longitud óptima del título
    if 40 <= len(titulo) <= 100:
        puntaje += 2
    
    # Penalizar titulares muy cortos o muy largos
    if len(titulo) < 20 or len(titulo) > 150:
        puntaje -= 2
    
    # Bonus por contenido
    if descripcion and len(descripcion) > 100:
        puntaje += 1
    
    return puntaje

# =============================================================================
# EXTRACCIÓN WEB Y GENERACIÓN DE CONTENIDO
# =============================================================================

def extraer_contenido_web(url):
    """Extrae contenido completo de la página web"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Eliminar elementos no deseados
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'ads']):
            elem.decompose()
        
        resultado = {'titulo': '', 'descripcion': '', 'imagen': None}
        
        # Título
        h1 = soup.find('h1')
        if h1:
            resultado['titulo'] = limpiar_texto_final(h1.get_text())
        
        # Meta descripción
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
        if meta_desc:
            resultado['descripcion'] = limpiar_texto_final(meta_desc.get('content', ''))
        
        # Contenido del artículo
        selectores = [
            'article', 
            '[class*="article-body"]', 
            '[class*="content"]', 
            '[class*="post-content"]',
            'main',
            '.entry-content',
            '#article-body'
        ]
        
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
        
        # Imagen
        og_image = soup.find('meta', property='og:image')
        if og_image:
            img_url = og_image.get('content', '')
            if img_url and not any(x in img_url.lower() for x in ['logo', 'icon', 'avatar']):
                resultado['imagen'] = img_url
        
        # Twitter card image fallback
        if not resultado['imagen']:
            twitter_img = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_img:
                resultado['imagen'] = twitter_img.get('content', '')
        
        return resultado
    except Exception as e:
        log(f"Error extrayendo web: {e}", 'debug')
        return None

def generar_texto_publicacion(noticia):
    """Genera texto profesional para Facebook"""
    url = noticia['url']
    
    # Intentar extraer de la web
    datos_web = extraer_contenido_web(url)
    
    if datos_web and datos_web.get('descripcion') and len(datos_web['descripcion']) > 150:
        descripcion = datos_web['descripcion']
    else:
        descripcion = noticia.get('descripcion', '')
        if len(descripcion) < 100:
            descripcion = f"{noticia['titulo']}. Los detalles de esta información están siendo verificados por nuestras fuentes."
    
    # Limpiar y formatear
    descripcion = limpiar_texto_final(descripcion)
    
    # Truncar si es muy largo
    if len(descripcion) > 1200:
        descripcion = descripcion[:1200].rsplit('.', 1)[0] + '.'
    
    texto_final = f"{descripcion}\n\n📰 Fuente: {noticia['fuente']}"
    return limpiar_texto_final(texto_final)

def generar_hashtags(noticia):
    """Genera hashtags relevantes"""
    texto = f"{noticia['titulo']}".lower()
    hashtags = ['#Noticias', '#ÚltimaHora']
    
    temas = {
        'política': '#Política', 
        'gobierno': '#Política', 
        'economía': '#Economía',
        'mercado': '#Economía',
        'guerra': '#Internacional', 
        'conflicto': '#Internacional',
        'deporte': '#Deportes', 
        'fútbol': '#Deportes',
        'tecnología': '#Tecnología',
        'ciencia': '#Ciencia',
        'salud': '#Salud',
        'música': '#Entretenimiento',
        'cine': '#Entretenimiento'
    }
    
    for palabra, tag in temas.items():
        if palabra in texto:
            hashtags.append(tag)
            break
    
    # Hashtag geográfico
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
        
        # Convertir a RGB si es necesario
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Redimensionar manteniendo aspecto
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        # Guardar temporal
        temp_path = f'/tmp/noticia_{generar_hash(url)[:10]}.jpg'
        img.save(temp_path, 'JPEG', quality=85, optimize=True)
        return temp_path
        
    except Exception as e:
        log(f"Error descargando imagen: {e}", 'debug')
        return None

def crear_imagen_texto(titulo):
    """Crea imagen con el título si no hay imagen disponible"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # Crear imagen base
        img = Image.new('RGB', (1200, 630), color='#1e3a8a')
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar fuentes
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            font_title = ImageFont.load_default()
            font_sub = font_title
        
        # Dibujar título envuelto
        titulo_wrapped = textwrap.fill(titulo[:140], width=35)
        draw.text((60, 80), titulo_wrapped, font=font_title, fill='white')
        
        # Marca de agua
        draw.text((60, 550), "Verdad Hoy • Noticias al minuto", font=font_sub, fill='#93c5fd')
        
        # Guardar
        temp_path = f'/tmp/noticia_gen_{generar_hash(titulo)[:10]}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
        
    except Exception as e:
        log(f"Error creando imagen: {e}", 'debug')
        return None

def publicar_en_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook con imagen"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales de Facebook", 'error')
        return False
    
    # Construir mensaje
    mensaje = f"{texto}\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto 🌐"
    
    # Truncar si excede límite de Facebook (2000 chars aprox)
    if len(mensaje) > 1900:
        texto_corto = texto[:1500].rsplit('.', 1)[0] + '.'
        mensaje = f"{texto_corto}\n\n[Leer noticia completa en el enlace]\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto 🌐"
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('imagen.jpg', f, 'image/jpeg')}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }
            
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
    print(f"🔒 Anti-duplicados: {VENTANA_DUPLICADOS_HORAS}h de ventana")
    print("="*60)
    
    # Verificar credenciales
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    # Verificar tiempo entre publicaciones
    if not verificar_tiempo_entre_publicaciones():
        return False
    
    # Cargar historial y estado
    historial = cargar_historial()
    estado = cargar_estado()
    
    # Mostrar estadísticas
    stats = historial.get('estadisticas', {})
    total = stats.get('total_publicadas', 0)
    log(f"📊 Total publicadas histórico: {total}")
    
    # =================================================================
    # OBTENER NOTICIAS DE TODAS LAS FUENTES (en orden de prioridad)
    # =================================================================
    
    todas_noticias = []
    
    # 1. NewsAPI (máxima prioridad)
    if NEWS_API_KEY:
        log("🔍 Consultando NewsAPI...", 'info')
        noticias = obtener_noticias_newsapi()
        todas_noticias.extend(noticias)
    
    # 2. NewsData.io
    if NEWSDATA_API_KEY and len(todas_noticias) < 10:
        log("🔍 Consultando NewsData.io...", 'info')
        noticias = obtener_noticias_newsdata()
        todas_noticias.extend(noticias)
    
    # 3. GNews API
    if GNEWS_API_KEY and len(todas_noticias) < 10:
        log("🔍 Consultando GNews...", 'info')
        noticias = obtener_noticias_gnews()
        todas_noticias.extend(noticias)
    
    # 4. Google News RSS (si no hay suficientes de APIs)
    if len(todas_noticias) < 15:
        log("🔍 Consultando Google News RSS...", 'info')
        noticias = obtener_noticias_google_news_rss()
        todas_noticias.extend(noticias)
    
    # 5. RSS tradicionales (fallback final)
    if len(todas_noticias) < 20:
        log("🔍 Consultando RSS tradicionales...", 'info')
        noticias = obtener_noticias_rss_tradicionales()
        todas_noticias.extend(noticias)
    
    log(f"📰 Total noticias recolectadas: {len(todas_noticias)}")
    
    if not todas_noticias:
        log("No se encontraron noticias en ninguna fuente", 'error')
        return False
    
    # =================================================================
    # FILTRAR DUPLICADOS Y SELECCIONAR
    # =================================================================
    
    # Ordenar por puntaje (relevancia)
    todas_noticias.sort(key=lambda x: x.get('puntaje', 0), reverse=True)
    
    # Filtrar duplicados y seleccionar la mejor noticia nueva
    noticia_seleccionada = None
    
    for noticia in todas_noticias:
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        descripcion = noticia.get('descripcion', '')
        
        if not url or not titulo:
            continue
        
        # Verificar si ya fue publicada
        if noticia_ya_publicada(historial, url, titulo, descripcion):
            log(f"⏭️  Duplicado detectado: {titulo[:50]}...", 'debug')
            continue
        
        # Verificar que sea reciente (últimas 24h)
        if not es_noticia_reciente(noticia.get('fecha')):
            continue
        
        noticia_seleccionada = noticia
        break
    
    if not noticia_seleccionada:
        log("Todas las noticias disponibles ya fueron publicadas recientemente", 'advertencia')
        
        # Último recurso: tomar la de mayor puntaje aunque sea duplicado antiguo
        # pero con diferente fuente o título ligeramente modificado
        for noticia in todas_noticias[:5]:
            # Forzar publicación si tiene alto puntaje y es de API (contenido fresco)
            if noticia.get('puntaje', 0) > 10 and 'API' in noticia.get('fuente', ''):
                noticia_seleccionada = noticia
                log("⚠️  Forzando publicación de noticia de alta relevancia", 'advertencia')
                break
        
        if not noticia_seleccionada:
            return False
    
    # =================================================================
    # PROCESAR Y PUBLICAR
    # =================================================================
    
    log(f"\n📝 NOTICIA SELECCIONADA:")
    log(f"   Título: {noticia_seleccionada['titulo'][:70]}...")
    log(f"   Fuente: {noticia_seleccionada['fuente']}")
    log(f"   URL: {noticia_seleccionada['url'][:60]}...")
    
    # Generar contenido
    texto = generar_texto_publicacion(noticia_seleccionada)
    hashtags = generar_hashtags(noticia_seleccionada)
    
    # Obtener imagen
    log("🖼️  Procesando imagen...")
    imagen_path = None
    
    # 1. Intentar imagen de la noticia
    if noticia_seleccionada.get('imagen'):
        imagen_path = descargar_imagen(noticia_seleccionada['imagen'])
    
    # 2. Extraer de la web
    if not imagen_path:
        datos_web = extraer_contenido_web(noticia_seleccionada['url'])
        if datos_web and datos_web.get('imagen'):
            imagen_path = descargar_imagen(datos_web['imagen'])
    
    # 3. Crear imagen con texto
    if not imagen_path:
        imagen_path = crear_imagen_texto(noticia_seleccionada['titulo'])
    
    if not imagen_path:
        log("ERROR: No se pudo obtener imagen", 'error')
        return False
    
    # Publicar
    exito = publicar_en_facebook(
        noticia_seleccionada['titulo'], 
        texto, 
        imagen_path, 
        hashtags
    )
    
    # Limpiar archivo temporal
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    # =================================================================
    # GUARDAR ESTADO
    # =================================================================
    
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
        
        # Mostrar estadísticas actualizadas
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
