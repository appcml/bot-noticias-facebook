#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias para Facebook
Publica noticias automáticamente cada 30 minutos
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
from urllib.parse import urlparse

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')

# Tiempo mínimo entre publicaciones (en minutos)
TIEMPO_ENTRE_PUBLICACIONES = 28  # Reducido para asegurar que publique cada 30 min

# =============================================================================
# FUENTES DE NOTICIAS
# =============================================================================

RSS_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://rss.cnn.com/rss/edition.rss',
    'https://www.france24.com/es/rss',
    'https://www.dw.com/es/actualidad/s-30684/rss',
    'https://www.eltiempo.com/rss/mundo.xml',
    'https://www.clarin.com/rss/mundo/',
    'https://www.latercera.com/feed/',
    'https://www.infobae.com/feeds/rss/',
    'https://www.20minutos.es/rss/',
    'https://www.elconfidencial.com/rss/',
    'https://www.rtve.es/api/rss/noticias/',
    'https://www.eldiario.es/rss/',
    'https://feeds.skynews.com/feeds/rss/world.xml',
    'https://www.reutersagency.com/feed/?best-topics=world',
    'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
    'https://elmundo.es/rss/portada.xml',
    'https://www.lavanguardia.com/mvc/feed/rss/home',
    'https://www.abc.es/rss/feeds/abc_ultima.xml',
    'https://www.publico.es/rss/',
    'https://www.europapress.es/rss/',
    'https://www.xataka.com/rss.xml',
    'https://feeds.weblogssl.com/genbeta',
    'https://www.expansion.com/rss/portada.xml',
    'https://as.com/rss/tags/ultimas_noticias.xml',
    'https://www.marca.com/rss/portada.xml',
]

PALABRAS_CLAVE = [
    'urgente', 'última hora', 'breaking', 'alerta', 'crisis', 'guerra', 'conflicto',
    'ataque', 'bombardeo', 'invasión', 'polémica', 'escándalo', 'revelan', 'confirmado',
    'histórico', 'sin precedentes', 'impactante', 'grave', 'tensión', 'protesta',
    'gobierno', 'presidente', 'elecciones', 'economía', 'mercado', 'bolsa',
    'pandemia', 'virus', 'vacuna', 'cambio climático', 'desastre', 'tragedia',
    'muere', 'fallece', 'asesinato', 'detenido', 'operativo', 'rescate',
]

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def log(mensaje, tipo='info'):
    """Imprime mensajes con formato"""
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    icono = iconos.get(tipo, 'ℹ️')
    print(f"{icono} {mensaje}")

def cargar_json(ruta, default=None):
    """Carga un archivo JSON o retorna valor por defecto"""
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error cargando {ruta}: {e}", 'error')
    return default

def guardar_json(ruta, datos):
    """Guarda datos en archivo JSON"""
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"Error guardando {ruta}: {e}", 'error')
        return False

def generar_hash(texto):
    """Genera hash MD5 de un texto"""
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()

def limpiar_texto(texto):
    """Limpia texto de HTML y espacios extras"""
    if not texto:
        return ""
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

# =============================================================================
# GESTIÓN DE HISTORIAL Y ESTADO
# =============================================================================

def cargar_historial():
    """Carga el historial de publicaciones"""
    default = {'urls': [], 'titulos': [], 'hashes': [], 'ultima_publicacion': None}
    historial = cargar_json(HISTORIAL_PATH, default)
    log(f"Historial cargado: {len(historial['urls'])} noticias publicadas")
    return historial

def guardar_historial(historial, url, titulo):
    """Guarda una nueva publicación en el historial"""
    url_hash = generar_hash(url)
    
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['hashes'].append(url_hash)
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    # Mantener solo últimas 500
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    historial['hashes'] = historial['hashes'][-500:]
    
    guardar_json(HISTORIAL_PATH, historial)
    log("Noticia guardada en historial", 'exito')

def noticia_ya_publicada(historial, url, titulo):
    """Verifica si una noticia ya fue publicada"""
    url_hash = generar_hash(url)
    
    if url_hash in historial.get('hashes', []):
        return True
    if url in historial.get('urls', []):
        return True
    
    # Verificar similitud de título
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:30]
    for t in historial.get('titulos', []):
        t_simple = re.sub(r'[^\w]', '', t.lower())[:30]
        if titulo_simple == t_simple:
            return True
    
    return False

def cargar_estado():
    """Carga el estado del bot"""
    default = {
        'ultima_publicacion': None,
        'total_publicadas': 0,
        'ultima_fuente': None
    }
    return cargar_json(ESTADO_PATH, default)

def guardar_estado(estado):
    """Guarda el estado del bot"""
    guardar_json(ESTADO_PATH, estado)

def verificar_tiempo_ultima_publicacion(estado):
    """
    Verifica si ya pasó el tiempo mínimo entre publicaciones.
    Retorna: (puede_publicar, minutos_transcurridos, minutos_faltantes)
    """
    if not estado.get('ultima_publicacion'):
        log("Primera ejecución - no hay historial de publicaciones", 'debug')
        return True, 0, 0
    
    try:
        ultima = datetime.fromisoformat(estado['ultima_publicacion'])
        ahora = datetime.now()
        transcurrido = (ahora - ultima).total_seconds() / 60
        
        log(f"Última publicación: {ultima.strftime('%H:%M:%S')} ({transcurrido:.1f} minutos atrás)", 'debug')
        
        if transcurrido < TIEMPO_ENTRE_PUBLICACIONES:
            faltan = TIEMPO_ENTRE_PUBLICACIONES - transcurrido
            log(f"Faltan {faltan:.1f} minutos para siguiente publicación", 'advertencia')
            return False, transcurrido, faltan
        
        log(f"Tiempo suficiente transcurrido ({transcurrido:.1f} minutos)", 'exito')
        return True, transcurrido, 0
        
    except Exception as e:
        log(f"Error verificando tiempo: {e}", 'error')
        # Si hay error, permitir publicar para no bloquear
        return True, 0, 0

# =============================================================================
# BÚSQUEDA DE NOTICIAS
# =============================================================================

def obtener_noticias_newsapi():
    """Obtiene noticias de NewsAPI"""
    noticias = []
    if not NEWS_API_KEY:
        log("NewsAPI no configurado", 'advertencia')
        return noticias
    
    terminos = ['noticias', 'actualidad', 'mundo', 'internacional']
    
    for termino in random.sample(terminos, 2):
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    'q': termino,
                    'language': 'es',
                    'sortBy': 'publishedAt',
                    'pageSize': 10,
                    'apiKey': NEWS_API_KEY
                },
                timeout=15
            )
            data = resp.json()
            
            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    titulo = art.get('title', '')
                    if not titulo or '[Removed]' in titulo:
                        continue
                    
                    noticias.append({
                        'titulo': titulo,
                        'descripcion': limpiar_texto(art.get('description', '')),
                        'url': art.get('url', ''),
                        'imagen': art.get('urlToImage', ''),
                        'fuente': art.get('source', {}).get('name', 'NewsAPI'),
                        'puntaje': calcular_puntaje(titulo, art.get('description', ''))
                    })
        except Exception as e:
            log(f"Error NewsAPI: {str(e)[:50]}", 'advertencia')
    
    log(f"NewsAPI: {len(noticias)} noticias")
    return noticias

def obtener_noticias_rss():
    """Obtiene noticias de feeds RSS"""
    noticias = []
    feeds = RSS_FEEDS.copy()
    random.shuffle(feeds)
    
    log(f"Consultando {len(feeds[:12])} feeds RSS...", 'debug')
    
    for feed_url in feeds[:12]:
        try:
            feed = feedparser.parse(feed_url)
            fuente = feed.feed.get('title', feed_url.split('/')[2])
            
            for entry in feed.entries[:3]:
                titulo = entry.get('title', '')
                if not titulo or len(titulo) < 10 or '[Removed]' in titulo:
                    continue
                
                descripcion = limpiar_texto(entry.get('summary', entry.get('description', '')))
                
                noticias.append({
                    'titulo': titulo,
                    'descripcion': descripcion,
                    'url': entry.get('link', ''),
                    'imagen': extraer_imagen_rss(entry),
                    'fuente': fuente,
                    'puntaje': calcular_puntaje(titulo, descripcion)
                })
        except Exception as e:
            continue
    
    log(f"RSS: {len(noticias)} noticias")
    return noticias

def extraer_imagen_rss(entry):
    """Extrae imagen de una entrada RSS"""
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('url'):
                return media['url']
    
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('href'):
                return enc['href']
    
    return None

def calcular_puntaje(titulo, descripcion):
    """Calcula relevancia de una noticia"""
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    for palabra in PALABRAS_CLAVE:
        if palabra in texto:
            puntaje += 2 if palabra in ['urgente', 'breaking', 'última hora'] else 1
    
    if 30 <= len(titulo) <= 100:
        puntaje += 1
    
    return puntaje

def seleccionar_noticia(noticias, historial, estado):
    """Selecciona la mejor noticia no publicada"""
    if not noticias:
        log("No hay noticias para seleccionar", 'error')
        return None
    
    # Filtrar ya publicadas
    nuevas = [n for n in noticias if not noticia_ya_publicada(historial, n['url'], n['titulo'])]
    log(f"Noticias nuevas: {len(nuevas)} de {len(noticias)}", 'debug')
    
    # Si no hay nuevas, usar cualquiera (rotación forzada para mantener frecuencia)
    if not nuevas:
        log("No hay noticias nuevas, usando rotación", 'advertencia')
        candidatas = noticias
    else:
        candidatas = nuevas
    
    # Evitar misma fuente consecutiva
    ultima_fuente = estado.get('ultima_fuente', '')
    diferentes = [n for n in candidatas if n['fuente'] != ultima_fuente]
    if diferentes:
        candidatas = diferentes
    
    # Ordenar por puntaje
    candidatas.sort(key=lambda x: x['puntaje'], reverse=True)
    
    seleccionada = candidatas[0] if candidatas else None
    if seleccionada:
        log(f"Seleccionada noticia de: {seleccionada['fuente']}", 'debug')
    
    return seleccionada

# =============================================================================
# PROCESAMIENTO DE NOTICIAS
# =============================================================================

def extraer_contenido_web(url):
    """Extrae contenido de una URL con espaciado correcto"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        
        selectores = ['article', '[class*="article-body"]', '[class*="content"]', 'main']
        contenido = None
        
        for selector in selectores:
            contenido = soup.select_one(selector)
            if contenido:
                break
        
        if not contenido:
            return None
        
        parrafos = []
        for p in contenido.find_all(['p', 'h2', 'h3']):
            texto = p.get_text(separator=' ', strip=True)
            texto = re.sub(r'\s+', ' ', texto)
            if len(texto) > 40:
                parrafos.append(texto)
        
        return ' '.join(parrafos)
        
    except Exception as e:
        log(f"Error extrayendo contenido: {str(e)[:50]}", 'advertencia')
        return None

def generar_texto_publicacion(noticia):
    """Genera el texto para publicar en Facebook con espaciado correcto"""
    titulo = noticia['titulo']
    descripcion = noticia['descripcion']
    fuente = noticia['fuente']
    
    contenido = extraer_contenido_web(noticia['url'])
    if not contenido:
        contenido = descripcion
    
    contenido = re.sub(r'\s+', ' ', contenido).strip()
    
    oraciones_raw = re.split(r'[.!?]+', contenido)
    oraciones = []
    
    for s in oraciones_raw:
        s = s.strip()
        if 30 < len(s) < 300:
            oraciones.append(s)
    
    vistas = set()
    oraciones_unicas = []
    for o in oraciones:
        o_lower = o.lower().strip()
        if o_lower not in vistas:
            vistas.add(o_lower)
            oraciones_unicas.append(o)
    
    oraciones = oraciones_unicas
    
    parrafos = []
    i = 0
    while i < len(oraciones):
        if i + 1 < len(oraciones):
            parrafo = f"{oraciones[i]}. {oraciones[i+1]}."
        else:
            parrafo = f"{oraciones[i]}."
        
        parrafo = re.sub(r'\s+', ' ', parrafo).strip()
        parrafos.append(parrafo)
        i += 2
    
    if len(parrafos) < 2:
        desc_limpia = re.sub(r'\s+', ' ', descripcion).strip()
        parrafos = [
            desc_limpia[:250] + ("..." if len(desc_limpia) > 250 else ""),
            "Se esperan más detalles en las próximas horas."
        ]
    
    parrafos = parrafos[:4]
    texto = '\n\n'.join(parrafos)
    
    # Limpieza final para evitar palabras pegadas
    texto = re.sub(r'([.!?])([A-Za-zÁÉÍÓÚáéíóúÑñ])', r'\1 \2', texto)
    texto = re.sub(r' +', ' ', texto)
    
    texto += f"\n\nFuente: {fuente}."
    
    return texto

def generar_hashtags(noticia):
    """Genera hashtags para la publicación"""
    texto = f"{noticia['titulo']} {noticia['descripcion']}".lower()
    hashtags = ['#Noticias', '#Actualidad']
    
    if any(p in texto for p in ['política', 'gobierno', 'presidente']):
        hashtags.append('#Política')
    elif any(p in texto for p in ['economía', 'mercado', 'bolsa']):
        hashtags.append('#Economía')
    elif any(p in texto for p in ['deporte', 'fútbol', 'partido']):
        hashtags.append('#Deportes')
    elif any(p in texto for p in ['tecnología', 'internet', 'app']):
        hashtags.append('#Tecnología')
    else:
        hashtags.append('#Internacional')
    
    paises = {
        'españa': 'España', 'madrid': 'España', 'barcelona': 'España',
        'méxico': 'Mexico', 'argentina': 'Argentina', 'chile': 'Chile',
        'colombia': 'Colombia', 'perú': 'Peru', 'venezuela': 'Venezuela',
        'brasil': 'Brasil', 'francia': 'Francia', 'alemania': 'Alemania',
        'italia': 'Italia', 'reino unido': 'ReinoUnido', 'rusia': 'Rusia',
        'ucrania': 'Ucrania', 'china': 'China', 'japón': 'Japon',
        'estados unidos': 'EstadosUnidos', 'usa': 'EstadosUnidos',
    }
    
    for pais, tag in paises.items():
        if pais in texto:
            hashtags.append(f'#{tag}')
            break
    else:
        hashtags.append('#Mundo')
    
    return ' '.join(hashtags)

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
        
        temp_path = f'/tmp/noticia_{generar_hash(url)[:8]}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        
        return temp_path
        
    except Exception as e:
        log(f"Error descargando imagen: {str(e)[:50]}", 'advertencia')
        return None

# =============================================================================
# PUBLICACIÓN EN FACEBOOK
# =============================================================================

def publicar_en_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales de Facebook", 'error')
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto"
    
    if len(mensaje) > 2000:
        parrafos = texto.split('\n\n')
        texto_corto = '\n\n'.join(parrafos[:-1])
        mensaje = f"{texto_corto}\n\n[Ver noticia completa en la fuente]\n\n{hashtags}\n\n— Verdad Hoy: Noticias al minuto"
    
    log(f"Publicando ({len(mensaje)} caracteres)...")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={
                    'message': mensaje,
                    'access_token': FB_ACCESS_TOKEN
                },
                timeout=60
            )
        
        result = resp.json()
        
        if resp.status_code == 200 and 'id' in result:
            log(f"Publicado exitosamente: {result['id']}", 'exito')
            return True
        else:
            error = result.get('error', {}).get('message', str(result))
            log(f"Error de Facebook: {error}", 'error')
            return False
            
    except Exception as e:
        log(f"Error publicando: {e}", 'error')
        return False

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """Función principal del bot"""
    print("\n" + "="*60)
    print("🤖 BOT DE NOTICIAS - FACEBOOK")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Tiempo mínimo entre publicaciones: {TIEMPO_ENTRE_PUBLICACIONES} minutos")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    log("Credenciales OK")
    
    # Cargar estado y verificar tiempo
    estado = cargar_estado()
    puede_publicar, minutos_transcurridos, minutos_faltantes = verificar_tiempo_ultima_publicacion(estado)
    
    if not puede_publicar:
        log(f"⏳ AÚN NO ES HORA DE PUBLICAR", 'advertencia')
        log(f"   Última publicación: hace {minutos_transcurridos:.1f} minutos", 'info')
        log(f"   Debe esperar: {minutos_faltantes:.1f} minutos más", 'info')
        log(f"   Próxima ejecución válida: en {minutos_faltantes:.0f} minutos", 'info')
        return True  # No es error, solo no es hora
    
    # Si llegamos aquí, podemos publicar
    log("✅ ES HORA DE PUBLICAR - Iniciando proceso", 'exito')
    
    historial = cargar_historial()
    
    log("Buscando noticias...")
    noticias = []
    noticias.extend(obtener_noticias_newsapi())
    noticias.extend(obtener_noticias_rss())
    
    log(f"Total noticias encontradas: {len(noticias)}")
    
    if not noticias:
        log("No se encontraron noticias", 'error')
        return False
    
    noticia = seleccionar_noticia(noticias, historial, estado)
    
    if not noticia:
        log("No se pudo seleccionar noticia", 'error')
        return False
    
    log(f"Seleccionada: {noticia['titulo'][:60]}...")
    log(f"Fuente: {noticia['fuente']} | Puntaje: {noticia['puntaje']}")
    
    texto = generar_texto_publicacion(noticia)
    hashtags = generar_hashtags(noticia)
    
    log("Procesando imagen...")
    imagen_path = descargar_imagen(noticia.get('imagen'))
    
    if not imagen_path:
        contenido = extraer_contenido_web(noticia['url'])
        if contenido:
            urls_img = re.findall(r'https?://[^\s"<>]+\.(?:jpg|jpeg|png)', contenido)
            for url_img in urls_img[:2]:
                imagen_path = descargar_imagen(url_img)
                if imagen_path:
                    break
    
    if not imagen_path:
        log("No se pudo obtener imagen", 'error')
        return False
    
    log("Imagen lista")
    
    log("Publicando en Facebook...")
    exito = publicar_en_facebook(noticia['titulo'], texto, imagen_path, hashtags)
    
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
        
        print("\n" + "="*60)
        log("PUBLICACIÓN COMPLETADA", 'exito')
        print(f"📰 {noticia['titulo'][:50]}...")
        print(f"🏢 {noticia['fuente']}")
        print(f"📊 Total publicadas: {estado['total_publicadas']}")
        print(f"⏰ Próxima: {(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')}")
        print("="*60)
        return True
    else:
        estado['intentos_fallidos'] = estado.get('intentos_fallidos', 0) + 1
        guardar_estado(estado)
        return False

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0 if resultado else 1)
    except KeyboardInterrupt:
        log("Interrumpido por usuario", 'advertencia')
        exit(1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
