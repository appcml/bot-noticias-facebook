#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias para Facebook - Prioriza Fuentes Alternativas (90%)
- 90% de noticias de fuentes RSS alternativas (BBC, CNN, El País, etc.)
- 10% máximo de Google News solo como respaldo
- Extracción completa de contenido web para calidad profesional
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
from urllib.parse import urlparse

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')

# TIEMPO: Publicar cada 30 minutos
TIEMPO_ENTRE_PUBLICACIONES = 28  # 28 minutos para asegurar publicación cada 30 min

# PORCENTAJE MÁXIMO DE GOOGLE NEWS: 10%
# Esto significa 90% fuentes alternativas, 10% máximo Google News
PORCENTAJE_MAX_GOOGLE_NEWS = 0.10  # 10% máximo

# =============================================================================
# FUENTES RSS SEPARADAS - AMPLIADAS
# =============================================================================

# FUENTES ALTERNATIVAS (90% de las publicaciones) - 45+ FUENTES
RSS_FEEDS_ALTERNATIVOS = [
    # Internacionales
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://rss.cnn.com/rss/edition.rss',
    'https://www.france24.com/es/rss',
    'https://www.dw.com/es/actualidad/s-30684/rss',
    'https://feeds.skynews.com/feeds/rss/world.xml',
    'https://www.reutersagency.com/feed/?best-topics=world',
    
    # España
    'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
    'https://e00-elmundo.uecdn.es/rss/portada.xml',
    'https://www.eldiario.es/rss/',
    'https://www.lavanguardia.com/mvc/feed/rss/home',
    'https://www.abc.es/rss/feeds/abc_ultima.xml',
    'https://www.publico.es/rss/',
    'https://www.europapress.es/rss/',
    'https://www.rtve.es/api/rss/noticias/',
    'https://www.elconfidencial.com/rss/',
    'https://www.20minutos.es/rss/',
    
    # México
    'https://www.excelsior.com.mx/rss.xml',
    'https://reforma.com/rss/portada.xml',
    'https://www.sinembargo.mx/feed',
    'https://www.24-horas.mx/feed',
    'https://www.informador.mx/rss/mexico.xml',
    'https://www.elfinanciero.com.mx/rss/portada.xml',
    'https://www.debate.com.mx/rss.xml',
    'https://www.razon.com.mx/rss.xml',
    
    # Argentina
    'https://www.clarin.com/rss/mundo/',
    'https://www.infobae.com/feeds/rss/',
    'https://www.lanacion.com.ar/rss/',
    'https://www.pagina12.com.ar/rss.xml',
    
    # Chile
    'https://www.latercera.com/feed/',
    'https://www.emol.com/rss.xml',
    'https://www.df.cl/rss.xml',
    
    # Colombia
    'https://www.eltiempo.com/rss/mundo.xml',
    'https://www.elespectador.com/rss.xml',
    'https://www.semana.com/rss.xml',
    
    # Perú
    'https://elcomercio.pe/rss.xml',
    'https://larepublica.pe/rss.xml',
    
    # Uruguay
    'https://www.elobservador.com.uy/rss.xml',
    
    # Venezuela
    'https://www.elnacional.com/rss.xml',
    
    # Ecuador
    'https://www.eluniverso.com/rss.xml',
    
    # Bolivia
    'https://www.lostiempos.com/rss.xml',
    
    # Tecnología y Economía
    'https://www.xataka.com/rss.xml',
    'https://feeds.weblogssl.com/genbeta',
    'https://www.expansion.com/rss/portada.xml',
    
    # Deportes
    'https://as.com/rss/tags/ultimas_noticias.xml',
    'https://www.marca.com/rss/portada.xml',
    
    # Otros
    'https://www.eluniversal.com.mx/rss/mundo.xml',
]

# GOOGLE NEWS (Máximo 10% de las publicaciones) - SOLO 2 FEEDS
RSS_FEEDS_GOOGLE = [
    'https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es',
    'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=ES&ceid=ES:es',
]

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
]

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    icono = iconos.get(tipo, 'ℹ️')
    print(f"{icono} {mensaje}")
    if tipo == 'error':
        print(f"::error::{mensaje}")

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def generar_hash(texto):
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()

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
    
    # Eliminar cortes
    texto = re.sub(r'\.\.\.$', '.', texto)
    
    return texto.strip()

# =============================================================================
# GESTIÓN DE ESTADO Y ESTADÍSTICAS
# =============================================================================

def cargar_historial():
    default = {
        'urls': [], 
        'titulos': [], 
        'hashes': [], 
        'ultima_publicacion': None,
        'estadisticas': {
            'total_alternativas': 0,
            'total_google': 0,
            'total_publicadas': 0
        }
    }
    return cargar_json(HISTORIAL_PATH, default)

def guardar_historial(historial, url, titulo, es_google_news=False):
    url_hash = generar_hash(url)
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['hashes'].append(url_hash)
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    # Actualizar estadísticas
    if 'estadisticas' not in historial:
        historial['estadisticas'] = {'total_alternativas': 0, 'total_google': 0, 'total_publicadas': 0}
    
    historial['estadisticas']['total_publicadas'] += 1
    if es_google_news:
        historial['estadisticas']['total_google'] += 1
    else:
        historial['estadisticas']['total_alternativas'] += 1
    
    # Mantener solo últimas 500
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    historial['hashes'] = historial['hashes'][-500:]
    
    guardar_json(HISTORIAL_PATH, historial)

def noticia_ya_publicada(historial, url, titulo):
    url_hash = generar_hash(url)
    if url_hash in historial.get('hashes', []):
        return True
    if url in historial.get('urls', []):
        return True
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:30]
    for t in historial.get('titulos', []):
        if titulo_simple == re.sub(r'[^\w]', '', t.lower())[:30]:
            return True
    return False

def cargar_estado():
    default = {'ultima_publicacion': None, 'ultima_fuente': None}
    return cargar_json(ESTADO_PATH, default)

def guardar_estado(estado):
    guardar_json(ESTADO_PATH, estado)

def debe_usar_google_news(historial):
    """
    Decide si usar Google News basado en el porcentaje actual.
    Retorna True SOLO si Google News está por DEBAJO del 10% objetivo.
    """
    stats = historial.get('estadisticas', {
        'total_alternativas': 0, 
        'total_google': 0, 
        'total_publicadas': 0
    })
    
    total = stats.get('total_publicadas', 0)
    
    if total == 0:
        # Primera publicación: usar alternativa (no Google News)
        return False
    
    alternativas = stats.get('total_alternativas', 0)
    google = stats.get('total_google', 0)
    
    porcentaje_google = google / total if total > 0 else 0
    
    log(f"📊 Estadísticas actuales: {alternativas} alternativas, {google} Google News ({porcentaje_google*100:.1f}%)", 'debug')
    
    # SOLO usar Google News si estamos por DEBAJO del 10% máximo
    # y solo para "rellenar" hasta el 10%, no más
    if porcentaje_google < PORCENTAJE_MAX_GOOGLE_NEWS:
        # Verificar si realmente necesitamos Google News o seguimos con alternativas
        # Solo usar Google News si llevamos muchas publicaciones seguidas de alternativas
        # para mantener el equilibrio del 10%
        if alternativas > 0:
            ratio = google / alternativas if alternativas > 0 else 0
            # Si el ratio es menor a 0.11 (aprox 10%), podemos usar Google News
            if ratio < 0.11:
                log("📈 Toca publicar de Google News para mantener equilibrio del 10%", 'debug')
                return True
    
    log("📉 Porcentaje de Google News adecuado o alto, buscando alternativa", 'debug')
    return False

# =============================================================================
# EXTRACCIÓN DE NOTICIAS
# =============================================================================

def limpiar_link_google_news(url):
    try:
        if 'news.google.com' in url:
            resp = requests.head(url, allow_redirects=True, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if resp.status_code == 200:
                return re.sub(r'\?.*$', '', resp.url)
        return url
    except:
        return url

def procesar_feed_alternativo(feed_url):
    """Procesa feeds de fuentes alternativas (BBC, CNN, etc.)"""
    noticias = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        feed = feedparser.parse(feed_url, request_headers=headers)
        fuente = feed.feed.get('title', feed_url.split('/')[2]).replace('RSS', '').strip()
        
        for entry in feed.entries[:5]:  # Tomar hasta 5
            titulo_raw = entry.get('title', '')
            if not titulo_raw or len(titulo_raw) < 10 or '[Removed]' in titulo_raw:
                continue
            
            titulo = html_module.unescape(titulo_raw)
            if ' - ' in titulo:
                titulo = titulo.rsplit(' - ', 1)[0]
            titulo = limpiar_texto_final(titulo)
            
            descripcion = limpiar_texto_final(entry.get('summary', entry.get('description', '')))
            
            # Extraer imagen del feed
            imagen = None
            if hasattr(entry, 'media_content') and entry.media_content:
                imagen = entry.media_content[0].get('url', '')
            elif hasattr(entry, 'enclosures') and entry.enclosures:
                imagen = entry.enclosures[0].get('href', '')
            
            noticias.append({
                'titulo': titulo,
                'descripcion': descripcion,
                'url': entry.get('link', ''),
                'imagen': imagen,
                'fuente': fuente,
                'puntaje': calcular_puntaje(titulo, descripcion) + 2,  # Bonus por ser alternativa
                'es_google_news': False
            })
    except Exception as e:
        log(f"Error feed alternativo: {str(e)[:50]}", 'advertencia')
    
    return noticias

def procesar_feed_google(feed_url):
    """Procesa feeds de Google News"""
    noticias = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        feed = feedparser.parse(feed_url, request_headers=headers)
        
        for entry in feed.entries[:5]:
            titulo_raw = entry.get('title', '')
            if not titulo_raw or len(titulo_raw) < 10 or '[Removed]' in titulo_raw:
                continue
            
            titulo = html_module.unescape(titulo_raw)
            if ' - ' in titulo:
                titulo = titulo.rsplit(' - ', 1)[0]
            titulo = limpiar_texto_final(titulo)
            
            link = entry.get('link', '')
            link = limpiar_link_google_news(link)
            
            noticias.append({
                'titulo': titulo,
                'descripcion': '',  # Se extraerá de la web
                'url': link,
                'imagen': None,  # Se extraerá de la web
                'fuente': 'Google News',
                'puntaje': calcular_puntaje(titulo, ''),
                'es_google_news': True
            })
    except Exception as e:
        log(f"Error Google News: {str(e)[:50]}", 'advertencia')
    
    return noticias

def calcular_puntaje(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    for palabra in PALABRAS_CLAVE:
        if palabra in texto:
            puntaje += 2 if palabra in ['urgente', 'breaking', 'última hora'] else 1
    if 30 <= len(titulo) <= 100:
        puntaje += 1
    return puntaje

# =============================================================================
# EXTRACCIÓN WEB COMPLETA
# =============================================================================

def extraer_contenido_web(url):
    """Extrae contenido completo de la página web"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        
        resultado = {'titulo': '', 'descripcion': '', 'imagen': None}
        
        # Título
        h1 = soup.find('h1')
        if h1:
            resultado['titulo'] = limpiar_texto_final(h1.get_text())
        
        # Contenido
        selectores = ['article', '[class*="article-body"]', '[class*="content"]', 'main', '.entry-content']
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
                if 60 < len(texto) < 400:
                    parrafos.append(texto)
            resultado['descripcion'] = '\n\n'.join(parrafos[:4])
        
        # Imagen
        og_image = soup.find('meta', property='og:image')
        if og_image:
            img_url = og_image.get('content', '')
            if img_url and not any(x in img_url.lower() for x in ['logo', 'icon', 'avatar']):
                resultado['imagen'] = img_url
        
        return resultado
    except:
        return None

# =============================================================================
# GENERACIÓN DE TEXTO
# =============================================================================

def generar_texto_publicacion(noticia):
    """Genera texto profesional"""
    url = noticia['url']
    
    # Extraer de la web para contenido completo
    datos_web = extraer_contenido_web(url)
    
    if datos_web and datos_web.get('descripcion') and len(datos_web['descripcion']) > 100:
        descripcion = datos_web['descripcion']
    else:
        # Usar descripción del feed o generar básica
        descripcion = noticia.get('descripcion', '')
        if len(descripcion) < 100:
            descripcion = f"Se reporta una noticia de última hora: {noticia['titulo']}. Los detalles están siendo confirmados por las fuentes oficiales."
    
    # Limpiar final
    descripcion = limpiar_texto_final(descripcion)
    
    # Corregir palabras pegadas específicas
    descripcion = re.sub(r'luz([A-Z])', r'luz. \1', descripcion)
    descripcion = re.sub(r'golpe([A-Z])', r'golpe. \1', descripcion)
    descripcion = re.sub(r'país([A-Z])', r'país. \1', descripcion)
    
    texto_final = f"{descripcion}\n\nFuente: {noticia['fuente']}."
    return limpiar_texto_final(texto_final)

def generar_hashtags(noticia):
    texto = noticia['titulo'].lower()
    hashtags = ['#Noticias', '#Actualidad']
    
    temas = {
        'política': '#Política', 'gobierno': '#Política', 'economía': '#Economía',
        'guerra': '#Conflicto', 'deporte': '#Deportes', 'tecnología': '#Tecnología',
    }
    
    for palabra, tag in temas.items():
        if palabra in texto:
            hashtags.append(tag)
            break
    
    hashtags.append('#Mundo')
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
        img.thumbnail((1200, 1200))
        temp_path = f'/tmp/noticia_{generar_hash(url)[:8]}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
    except:
        return None

def crear_imagen_texto(titulo):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        img = Image.new('RGB', (1200, 630), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        titulo_wrapped = textwrap.fill(titulo[:150], width=40)
        draw.text((60, 100), titulo_wrapped, font=font, fill='white')
        draw.text((60, 550), "Verdad Hoy - Noticias al minuto", font=font_small, fill='#aaa')
        temp_path = f'/tmp/noticia_gen_{generar_hash(titulo)[:8]}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
    except:
        return None

def publicar_en_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto"
    
    if len(mensaje) > 2000:
        parrafos = texto.split('\n\n')
        texto_corto = ''
        for p in parrafos:
            if len(texto_corto) + len(p) < 1700:
                texto_corto += p + '\n\n'
        texto = texto_corto.strip() + "\n\n[Ver noticia completa en el enlace]"
        mensaje = f"{texto}\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto"
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
        result = resp.json()
        return resp.status_code == 200 and 'id' in result
    except:
        return False

# =============================================================================
# FUNCIÓN PRINCIPAL CON LÓGICA DE PRIORIZACIÓN
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🤖 BOT DE NOTICIAS - FACEBOOK")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objetivo: 90% alternativas, máximo 10% Google News")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales", 'error')
        return False
    
    estado = cargar_estado()
    historial = cargar_historial()
    
    # Mostrar estadísticas actuales
    stats = historial.get('estadisticas', {'total_alternativas': 0, 'total_google': 0, 'total_publicadas': 0})
    total = stats.get('total_publicadas', 0)
    if total > 0:
        alt_pct = (stats.get('total_alternativas', 0) / total) * 100
        goog_pct = (stats.get('total_google', 0) / total) * 100
        # CORREGIDO: Error de formato aquí - usar .1f sin el % dentro
        log(f"📊 Historial: {alt_pct:.1f}% alternativas ({stats['total_alternativas']}), {goog_pct:.1f}% Google ({stats['total_google']})")
    
    # DECIDIR FUENTE: ¿Usar Google News o alternativas?
    usar_google = debe_usar_google_news(historial)
    
    noticias = []
    
    if usar_google:
        log("🔍 Buscando en Google News (límite 10%)...", 'info')
        for feed in RSS_FEEDS_GOOGLE:
            noticias.extend(procesar_feed_google(feed))
    else:
        log("🔍 Buscando en fuentes alternativas (90%)...", 'info')
        # Mezclar feeds alternativos para variedad
        feeds_alt = RSS_FEEDS_ALTERNATIVOS.copy()
        random.shuffle(feeds_alt)
        # Aumentado a 8 feeds para más variedad
        for feed in feeds_alt[:8]:
            noticias.extend(procesar_feed_alternativo(feed))
    
    if not noticias:
        log("No se encontraron noticias en la fuente seleccionada", 'advertencia')
        # Intentar la otra fuente como respaldo
        if usar_google:
            log("Intentando fuentes alternativas como respaldo...", 'info')
            for feed in RSS_FEEDS_ALTERNATIVOS[:6]:
                noticias.extend(procesar_feed_alternativo(feed))
        else:
            # Solo intentar Google News si realmente lo necesitamos (está por debajo del 10%)
            stats = historial.get('estadisticas', {'total_alternativas': 0, 'total_google': 0, 'total_publicadas': 0})
            total = stats.get('total_publicadas', 0)
            if total > 0:
                goog_pct = (stats.get('total_google', 0) / total) * 100
                if goog_pct < PORCENTAJE_MAX_GOOGLE_NEWS * 100:
                    log("Intentando Google News como respaldo...", 'info')
                    for feed in RSS_FEEDS_GOOGLE:
                        noticias.extend(procesar_feed_google(feed))
    
    if not noticias:
        log("No hay noticias disponibles", 'error')
        return False
    
    log(f"Total noticias recolectadas: {len(noticias)}")
    
    # Seleccionar noticia no publicada
    noticia = None
    for n in sorted(noticias, key=lambda x: x['puntaje'], reverse=True):
        if not noticia_ya_publicada(historial, n['url'], n['titulo']):
            noticia = n
            break
    
    if not noticia:
        # Rotar: usar la primera de mayor puntaje
        noticia = sorted(noticias, key=lambda x: x['puntaje'], reverse=True)[0]
        log("Todas las noticias ya fueron publicadas, rotando...", 'advertencia')
    
    tipo_fuente = "Google News" if noticia.get('es_google_news') else "Alternativa"
    log(f"\n📝 NOTICIA SELECCIONADA ({tipo_fuente}):")
    log(f"   Título: {noticia['titulo'][:60]}...")
    log(f"   Fuente: {noticia['fuente']}")
    
    # Generar contenido
    texto = generar_texto_publicacion(noticia)
    hashtags = generar_hashtags(noticia)
    
    # Obtener imagen
    log("Procesando imagen...")
    imagen_path = None
    
    if noticia.get('imagen'):
        imagen_path = descargar_imagen(noticia['imagen'])
    
    if not imagen_path:
        # Extraer de la web
        datos_web = extraer_contenido_web(noticia['url'])
        if datos_web and datos_web.get('imagen'):
            imagen_path = descargar_imagen(datos_web['imagen'])
    
    if not imagen_path:
        imagen_path = crear_imagen_texto(noticia['titulo'])
    
    if not imagen_path:
        log("ERROR: Sin imagen", 'error')
        return False
    
    # Publicar
    exito = publicar_en_facebook(noticia['titulo'], texto, imagen_path, hashtags)
    
    # Limpiar
    try:
        if imagen_path and os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        guardar_historial(historial, noticia['url'], noticia['titulo'], noticia.get('es_google_news', False))
        estado['ultima_publicacion'] = datetime.now().isoformat()
        estado['ultima_fuente'] = noticia['fuente']
        guardar_estado(estado)
        
        # Mostrar estadísticas actualizadas - CORREGIDO
        stats = historial.get('estadisticas', {})
        total = stats.get('total_publicadas', 1)
        alt_pct = (stats.get('total_alternativas', 0) / total) * 100
        goog_pct = (stats.get('total_google', 0) / total) * 100
        # CORREGIDO: Usar formato correcto sin % dentro del especificador
        log(f"✅ PUBLICADO - Estadísticas: {alt_pct:.1f}% alt / {goog_pct:.1f}% goog", 'exito')
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
