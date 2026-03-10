#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias para Facebook - Versión Final Corregida
- IGNORA texto de Google News (viene cortado y con errores)
- Extrae TODO contenido directamente de la página web original
- Limpieza profunda de caracteres y espaciado
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

TIEMPO_ENTRE_PUBLICACIONES = 0  # 0 para pruebas, 60 para producción

# =============================================================================
# FUENTES RSS
# =============================================================================

RSS_FEEDS = [
    'https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es',
    'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=ES&ceid=ES:es',
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://rss.cnn.com/rss/edition.rss',
    'https://www.eltiempo.com/rss/mundo.xml',
    'https://www.infobae.com/feeds/rss/',
    'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
]

PALABRAS_CLAVE = [
    'urgente', 'última hora', 'breaking', 'alerta', 'crisis', 'guerra', 'conflicto',
    'ataque', 'bombardeo', 'invasión', 'polémica', 'escándalo', 'revelan', 'confirmado',
    'histórico', 'sin precedentes', 'impactante', 'grave', 'tensión', 'protesta',
]

# =============================================================================
# LIMPIEZA PROFESIONAL MEJORADA
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
    """
    Limpieza final agresiva para texto profesional perfecto
    """
    if not texto:
        return ""
    
    # Decodificar HTML
    texto = html_module.unescape(texto)
    
    # Eliminar tags HTML residuales
    texto = re.sub(r'<[^>]+>', ' ', texto)
    
    # CORREGIR: Separar palabras pegadas con mayúscula (ej: "luzLa" → "luz. La")
    # Buscar minúscula seguida de mayúscula e insertar punto y espacio
    texto = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1. \2', texto)
    
    # CORREGIR: Separar después de punto si no hay espacio
    texto = re.sub(r'\.([A-Za-zÁÉÍÓÚáéíóúÑñ])', r'. \1', texto)
    
    # CORREGIR: Espacios antes de puntuación
    texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
    
    # CORREGIR: Puntuación doble
    texto = re.sub(r'\.+', '.', texto)
    texto = re.sub(r',+', ',', texto)
    
    # Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar caracteres especiales problemáticos
    texto = texto.replace('…', '...').replace('–', '-').replace('—', '-')
    texto = texto.replace('"', '"').replace('"', '"')
    texto = texto.replace(''', "'").replace(''', "'")
    
    # Eliminar "..." al final si existe (indica texto cortado)
    texto = re.sub(r'\.\.\.$', '.', texto)
    texto = re.sub(r'\.\.\.([^\s])', r'... \1', texto)
    
    # Eliminar espacios al inicio/final
    texto = texto.strip()
    
    # Asegurar punto final
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto

# =============================================================================
# GESTIÓN DE ESTADO
# =============================================================================

def cargar_historial():
    default = {'urls': [], 'titulos': [], 'hashes': [], 'ultima_publicacion': None}
    return cargar_json(HISTORIAL_PATH, default)

def guardar_historial(historial, url, titulo):
    url_hash = generar_hash(url)
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['hashes'].append(url_hash)
    historial['ultima_publicacion'] = datetime.now().isoformat()
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
    default = {'ultima_publicacion': None, 'total_publicadas': 0, 'ultima_fuente': None}
    return cargar_json(ESTADO_PATH, default)

def guardar_estado(estado):
    guardar_json(ESTADO_PATH, estado)

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

def obtener_noticias_rss():
    """Obtiene noticias de RSS - SOLO título y URL, IGNORA descripción de Google News"""
    noticias = []
    
    for feed_url in RSS_FEEDS:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            feed = feedparser.parse(feed_url, request_headers=headers)
            es_google_news = 'news.google.com' in feed_url
            
            entries = feed.entries[:5] if es_google_news else feed.entries[:3]
            
            for entry in entries:
                titulo_raw = entry.get('title', '')
                if not titulo_raw or len(titulo_raw) < 10 or '[Removed]' in titulo_raw:
                    continue
                
                # Limpiar título
                titulo = html_module.unescape(titulo_raw)
                if ' - ' in titulo:
                    titulo = titulo.rsplit(' - ', 1)[0]
                titulo = limpiar_texto_final(titulo)
                
                link = entry.get('link', '')
                if es_google_news:
                    link = limpiar_link_google_news(link)
                    fuente = 'Google News'
                else:
                    fuente = feed.feed.get('title', 'RSS')
                
                # ← IMPORTANTE: Para Google News, NO usar la descripción del feed
                # (viene cortada y con errores). Se extraerá de la web después.
                if es_google_news:
                    descripcion = ''  # Se llenará después con scraping
                else:
                    descripcion = limpiar_texto_final(entry.get('summary', ''))
                
                noticias.append({
                    'titulo': titulo,
                    'descripcion': descripcion,  # Vacío para Google News
                    'url': link,
                    'imagen': None,  # Se extraerá después
                    'fuente': fuente,
                    'puntaje': 3 if es_google_news else 1,
                    'es_google_news': es_google_news
                })
                
        except Exception as e:
            log(f"Error RSS: {str(e)[:50]}", 'advertencia')
    
    return noticias

# =============================================================================
# EXTRACCIÓN WEB COMPLETA (LA CLAVE DEL ÉXITO)
# =============================================================================

def extraer_contenido_completo_de_url(url):
    """
    Extrae TODA la información directamente de la página web original.
    IGNORA completamente cualquier texto del feed RSS.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
        
        resp = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Eliminar elementos no deseados
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'figure', 'figcaption', 'noscript']):
            elem.decompose()
        
        resultado = {
            'titulo': '',
            'descripcion': '',
            'imagen': None
        }
        
        # 1. Extraer título de la página (mejor que el del RSS)
        titulo_tag = soup.find('h1') or soup.find('meta', property='og:title')
        if titulo_tag:
            if titulo_tag.name == 'h1':
                resultado['titulo'] = limpiar_texto_final(titulo_tag.get_text())
            else:
                resultado['titulo'] = limpiar_texto_final(titulo_tag.get('content', ''))
        
        # 2. Extraer descripción/contenido completo
        # Buscar el cuerpo del artículo con múltiples selectores
        selectores_contenido = [
            'article',
            '[class*="article-body"]',
            '[class*="articleBody"]',
            '[class*="content-body"]',
            '[class*="post-content"]',
            '[class*="entry-content"]',
            '[class*="story-body"]',
            '[class*="news-text"]',
            '[class*="cuerpo"]',
            '[class*="texto"]',
            'main',
            '#content',
            '.content'
        ]
        
        contenido_elem = None
        for selector in selectores_contenido:
            contenido_elem = soup.select_one(selector)
            if contenido_elem:
                break
        
        if contenido_elem:
            # Extraer todos los párrafos
            parrafos = []
            for p in contenido_elem.find_all(['p', 'h2', 'h3']):
                texto = p.get_text(separator=' ', strip=True)
                texto = limpiar_texto_final(texto)
                # Solo párrafos sustanciales
                if len(texto) > 50 and len(texto) < 500:
                    parrafos.append(texto)
            
            # Unir los mejores párrafos (hasta 4)
            if parrafos:
                resultado['descripcion'] = '\n\n'.join(parrafos[:4])
        
        # 3. Si no se encontró contenido, buscar en todo el body
        if not resultado['descripcion']:
            body = soup.find('body')
            if body:
                # Buscar todos los párrafos con texto sustancial
                parrafos = []
                for p in body.find_all('p'):
                    texto = p.get_text(strip=True)
                    texto = limpiar_texto_final(texto)
                    if 80 < len(texto) < 400 and not any(x in texto.lower() for x in ['cookie', 'privacidad', 'suscribirse']):
                        parrafos.append(texto)
                if parrafos:
                    resultado['descripcion'] = '\n\n'.join(parrafos[:3])
        
        # 4. Extraer imagen
        # Meta tags
        for meta in ['og:image', 'twitter:image']:
            tag = soup.find('meta', property=meta) or soup.find('meta', attrs={'name': meta})
            if tag:
                img_url = tag.get('content', '')
                if img_url and not any(x in img_url.lower() for x in ['logo', 'icon', 'avatar', 'user']):
                    resultado['imagen'] = img_url
                    break
        
        # Buscar en contenido si no se encontró
        if not resultado['imagen'] and contenido_elem:
            for img in contenido_elem.find_all('img'):
                src = img.get('src', '')
                width = img.get('width', '0')
                if src and int(width) > 300 if width else True:
                    if not any(x in src.lower() for x in ['logo', 'icon', 'avatar']):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            parsed = urlparse(url)
                            src = f"{parsed.scheme}://{parsed.netloc}{src}"
                        resultado['imagen'] = src
                        break
        
        return resultado
        
    except Exception as e:
        log(f"Error extrayendo de {url[:50]}: {e}", 'error')
        return None

# =============================================================================
# GENERACIÓN DE PUBLICACIÓN
# =============================================================================

def generar_texto_profesional(noticia):
    """
    Genera texto 100% profesional extrayendo TODO de la web original.
    NO usa el texto del feed RSS para Google News.
    """
    url = noticia['url']
    
    log(f"Extrayendo contenido completo de: {url[:60]}...", 'debug')
    
    # Extraer TODO de la página web original
    datos_web = extraer_contenido_completo_de_url(url)
    
    if not datos_web:
        log("No se pudo extraer de la web, usando respaldo", 'advertencia')
        return generar_texto_respaldo(noticia)
    
    # Usar título de la web si es mejor, o el del RSS
    titulo = datos_web['titulo'] if datos_web['titulo'] else noticia['titulo']
    titulo = limpiar_texto_final(titulo)
    
    # Usar descripción extraída de la web (completa, no cortada)
    descripcion = datos_web['descripcion']
    
    if not descripcion or len(descripcion) < 100:
        log("Descripción muy corta, usando respaldo", 'advertencia')
        return generar_texto_respaldo(noticia)
    
    # Limpiar una última vez
    descripcion = limpiar_texto_final(descripcion)
    
    # Verificar que no tenga errores de palabras pegadas
    # Si encuentra palabras pegadas, intentar separarlas
    descripcion = corregir_palabras_pegadas(descripcion)
    
    # Construir texto final
    texto_final = f"{descripcion}\n\nFuente: {noticia['fuente']}."
    
    # Verificación final
    texto_final = limpiar_texto_final(texto_final)
    
    log(f"Texto generado: {len(texto_final)} caracteres", 'exito')
    return texto_final

def corregir_palabras_pegadas(texto):
    """
    Corrige específicamente palabras pegadas como "luzLa", "golpeEl", etc.
    """
    # Patrones comunes de palabras pegadas en noticias
    correcciones = [
        (r'luz([A-Z])', r'luz. \1'),
        (r'golpe([A-Z])', r'golpe. \1'),
        (r'país([A-Z])', r'país. \1'),
        (r'mundo([A-Z])', r'mundo. \1'),
        (r'hora([A-Z])', r'hora. \1'),
        (r'día([A-Z])', r'día. \1'),
        (r'año([A-Z])', r'año. \1'),
        (r'tiempo([A-Z])', r'tiempo. \1'),
        (r'razón([A-Z])', r'razón. \1'),
        (r'guerra([A-Z])', r'guerra. \1'),
        (r'paz([A-Z])', r'paz. \1'),
    ]
    
    for patron, reemplazo in correcciones:
        texto = re.sub(patron, reemplazo, texto)
    
    return texto

def generar_texto_respaldo(noticia):
    """Genera texto básico si falla la extracción web"""
    titulo = noticia['titulo']
    # Crear un texto genérico pero profesional
    parrafos = [
        f"Se reporta una noticia de última hora: {titulo}",
        "Los detalles están siendo confirmados por las fuentes oficiales correspondientes.",
        "Se espera más información en las próximas horas a medida que se desarrollen los hechos."
    ]
    texto = '\n\n'.join(parrafos)
    texto += f"\n\nFuente: {noticia['fuente']}."
    return limpiar_texto_final(texto)

def generar_hashtags(noticia):
    texto = f"{noticia['titulo']}".lower()
    hashtags = ['#Noticias', '#Actualidad']
    
    temas = {
        'política': '#Política', 'gobierno': '#Política', 'presidente': '#Política',
        'economía': '#Economía', 'mercado': '#Economía',
        'guerra': '#Conflicto', 'ataque': '#Conflicto', 'bombardeo': '#Conflicto',
        'deporte': '#Deportes', 'fútbol': '#Deportes',
    }
    
    for palabra, hashtag in temas.items():
        if palabra in texto:
            hashtags.append(hashtag)
            break
    
    hashtags.append('#Mundo')
    return ' '.join(hashtags)

# =============================================================================
# IMÁGENES
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

# =============================================================================
# PUBLICACIÓN
# =============================================================================

def publicar_en_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales", 'error')
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto"
    
    # Limitar si es necesario
    if len(mensaje) > 2000:
        parrafos = texto.split('\n\n')
        texto_corto = ''
        for p in parrafos:
            if len(texto_corto) + len(p) < 1700:
                texto_corto += p + '\n\n'
            else:
                break
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
        if resp.status_code == 200 and 'id' in result:
            log(f"Publicado: {result['id']}", 'exito')
            return True
        else:
            log(f"Error FB: {result.get('error', {}).get('message', str(result))}", 'error')
            return False
    except Exception as e:
        log(f"Error: {e}", 'error')
        return False

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🤖 BOT DE NOTICIAS - FACEBOOK")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales", 'error')
        return False
    
    estado = cargar_estado()
    
    # Verificar tiempo (simplificado)
    if estado.get('ultima_publicacion') and TIEMPO_ENTRE_PUBLICACIONES > 0:
        try:
            ultima = datetime.fromisoformat(estado['ultima_publicacion'])
            if (datetime.now() - ultima).total_seconds() / 60 < TIEMPO_ENTRE_PUBLICACIONES:
                log("⏳ Esperando tiempo entre publicaciones", 'advertencia')
                return True
        except:
            pass
    
    historial = cargar_historial()
    
    log("Recolectando noticias...")
    noticias = obtener_noticias_rss()
    
    if not noticias:
        log("No hay noticias", 'error')
        return False
    
    # Seleccionar primera noticia nueva
    noticia = None
    for n in noticias:
        if not noticia_ya_publicada(historial, n['url'], n['titulo']):
            noticia = n
            break
    
    if not noticia:
        noticia = noticias[0]  # Rotar si todas son viejas
    
    log(f"\n📝 NOTICIA: {noticia['titulo'][:50]}...")
    log(f"   Fuente: {noticia['fuente']}")
    log(f"   URL: {noticia['url'][:60]}...")
    
    # Extraer contenido completo de la web
    texto = generar_texto_profesional(noticia)
    hashtags = generar_hashtags(noticia)
    
    # Obtener imagen
    log("Procesando imagen...")
    imagen_path = None
    
    # Intentar extraer imagen de la web
    datos_web = extraer_contenido_completo_de_url(noticia['url'])
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
        guardar_historial(historial, noticia['url'], noticia['titulo'])
        estado['ultima_publicacion'] = datetime.now().isoformat()
        estado['ultima_fuente'] = noticia['fuente']
        estado['total_publicadas'] = estado.get('total_publicadas', 0) + 1
        guardar_estado(estado)
        log("✅ PUBLICACIÓN COMPLETADA", 'exito')
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
