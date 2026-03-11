#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook
- Prioridad: Conflictos bélicos, política global, economía mundial
- Fuentes: NewsAPI, NewsData, GNews (todo internacional)
- Extracción de texto completo desde la web para evitar cortes
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

TERMINOS_EXCLUIR = [
    'liga local', 'campeonato municipal', 'feria del pueblo', 
    'concurso de belleza local', 'festival regional', 'torneo de barrio',
    'elecciones municipales de', 'alcaldía de', 'alcalde de', 'gobernador de',
    'partido local', 'equipo local', 'deporte local',
]

# Frases a eliminar del contenido extraído
FRASES_A_ELIMINAR = [
    'se esperan más detalles en las próximas horas',
    'se esperan mas detalles en las proximas horas',
    'más detalles en las próximas horas',
    'mas detalles en las proximas horas',
    'en desarrollo',
    'continúa en desarrollo',
    'continua en desarrollo',
    'información en desarrollo',
    'informacion en desarrollo',
    'actualización en curso',
    'actualizacion en curso',
    'noticia en desarrollo',
    'esto es una información en desarrollo',
    'esto es una informacion en desarrollo',
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
    if not texto:
        return ""
    texto_normalizado = re.sub(r'[^\w\s]', '', texto.lower().strip())
    texto_normalizado = re.sub(r'\s+', ' ', texto_normalizado)
    return hashlib.md5(texto_normalizado.encode()).hexdigest()[:16]

def limpiar_texto(texto):
    if not texto:
        return ""
    
    texto = html_module.unescape(texto)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)
    texto = re.sub(r'https?://\S*', '', texto)
    texto = re.sub(r'[.…]{2,}\s*$', '.', texto)
    
    texto = texto.strip()
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto.strip()

def es_noticia_excluible(titulo, descripcion=""):
    texto = f"{titulo} {descripcion}".lower()
    for termino in TERMINOS_EXCLUIR:
        if termino.lower() in texto:
            return True
    return False

def calcular_puntaje_internacional(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    for palabra in PALABRAS_ALTA_PRIORIDAD:
        if palabra.lower() in texto:
            puntaje += 10
    
    for palabra in PALABRAS_MEDIA_PRIORIDAD:
        if palabra.lower() in texto:
            puntaje += 3
    
    fuentes_reconocidas = ['reuters', 'afp', 'ap ', 'associated press', 'bbc', 'cnn', 'al jazeera']
    for fuente in fuentes_reconocidas:
        if fuente in texto:
            puntaje += 2
            break
    
    if es_noticia_excluible(titulo, descripcion):
        puntaje -= 20
    
    if 50 <= len(titulo) <= 120:
        puntaje += 2
    
    return puntaje

# =============================================================================
# EXTRACCIÓN DE CONTENIDO COMPLETO DE LA WEB
# =============================================================================

def extraer_contenido_completo(url):
    """
    Extrae el contenido completo de la noticia desde la URL.
    Separa el cuerpo de la noticia de los créditos/autor.
    """
    if not url:
        return None, None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    }
    
    try:
        log(f"   🔍 Extrayendo contenido de: {url[:60]}...", 'debug')
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Eliminar elementos no deseados
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'button']):
            element.decompose()
        
        contenido = None
        creditos = None
        
        # Buscar créditos/autor primero
        creditos = extraer_creditos(soup)
        
        # Estrategia 1: Buscar article o main
        for tag in ['article', 'main', '[role="main"]']:
            if tag.startswith('['):
                elemento = soup.select_one(tag)
            else:
                elemento = soup.find(tag)
            
            if elemento:
                texto, creds = extraer_texto_y_creditos(elemento)
                if len(texto) > 200:
                    contenido = texto
                    if creds and not creditos:
                        creditos = creds
                    log(f"   ✅ Extraído de <{tag}>: {len(contenido)} caracteres", 'debug')
                    break
        
        # Estrategia 2: Buscar por clases comunes de contenido
        if not contenido:
            clases_comunes = [
                'article-content', 'content', 'post-content', 'entry-content',
                'article-body', 'story-body', 'news-body', 'text-content',
                'cuerpo-noticia', 'cuerpo', 'articulo', 'noticia-texto',
                'article__body', 'article-body-content', 'story-content'
            ]
            
            for clase in clases_comunes:
                elemento = soup.find(class_=lambda x: x and clase in x.lower())
                if elemento:
                    texto, creds = extraer_texto_y_creditos(elemento)
                    if len(texto) > 200:
                        contenido = texto
                        if creds and not creditos:
                            creditos = creds
                        log(f"   ✅ Extraído de clase '{clase}': {len(contenido)} caracteres", 'debug')
                        break
        
        # Estrategia 3: Buscar divs con mucho texto
        if not contenido:
            candidatos = []
            for div in soup.find_all(['div', 'section']):
                texto, creds = extraer_texto_y_creditos(div)
                # Debe tener párrafos y longitud considerable
                if len(texto) > 300 and texto.count('.') > 3:
                    candidatos.append((len(texto), texto, creds, div))
            
            if candidatos:
                candidatos.sort(reverse=True)
                contenido = candidatos[0][1]
                if candidatos[0][2] and not creditos:
                    creditos = candidatos[0][2]
                log(f"   ✅ Extraído de div con más texto: {len(contenido)} caracteres", 'debug')
        
        # Estrategia 4: Extraer todos los párrafos del body
        if not contenido:
            body = soup.find('body')
            if body:
                parrafos = []
                for p in body.find_all('p'):
                    texto = limpiar_parrafo(p.get_text())
                    if len(texto) > 50:
                        parrafos.append(texto)
                
                if parrafos:
                    contenido = ' '.join(parrafos[:10])
                    log(f"   ✅ Extraído de párrafos sueltos: {len(contenido)} caracteres", 'debug')
        
        if contenido and len(contenido) > 100:
            # Limpiar frases genéricas del contenido
            contenido = eliminar_frases_genericas(contenido)
            return contenido[:1500], creditos
        
        return None, creditos
        
    except Exception as e:
        log(f"   ⚠️ Error extrayendo contenido: {e}", 'debug')
        return None, None

def extraer_creditos(soup):
    """Extrae el autor/fecha de la noticia."""
    creditos = None
    
    # Buscar en metadatos
    for meta in ['author', 'article:author', 'byline']:
        tag = soup.find('meta', attrs={'name': meta}) or soup.find('meta', property=meta)
        if tag:
            creditos = tag.get('content', '').strip()
            if creditos:
                break
    
    # Buscar en elementos comunes de autor
    if not creditos:
        clases_autor = ['author', 'byline', 'autor', 'firma', 'creditos', 'article-author']
        for clase in clases_autor:
            elem = soup.find(class_=lambda x: x and clase in x.lower())
            if elem:
                creditos = elem.get_text(strip=True)
                if creditos and len(creditos) < 200:
                    break
    
    # Buscar patrones de fecha/autor al inicio del artículo
    if not creditos:
        patrones = [
            r'([A-Z][a-z]+ [A-Z][a-z]+.*?)\d{1,2}/\d{1,2}/\d{4}',
            r'Por[: ]+([A-Z][^\n]{3,50}?)\n',
            r'^([A-Z][^\n]{2,30}?)\d{1,2} de [a-z]+ de \d{4}',
        ]
        texto_completo = soup.get_text()[:500]
        for patron in patrones:
            match = re.search(patron, texto_completo, re.IGNORECASE)
            if match:
                creditos = match.group(1).strip()
                break
    
    if creditos:
        creditos = re.sub(r'\s+', ' ', creditos).strip()
        if len(creditos) > 150:
            creditos = creditos[:150] + '...'
        log(f"   👤 Créditos encontrados: {creditos[:60]}...", 'debug')
    
    return creditos

def extraer_texto_y_creditos(elemento):
    """Extrae texto limpio y busca créditos dentro del elemento."""
    if not elemento:
        return "", None
    
    texto_raw = elemento.get_text(separator='\n', strip=True)
    
    lineas = texto_raw.split('\n')
    creditos = None
    lineas_contenido = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        if i < 3 and not creditos:
            if (re.search(r'\d{1,2}/\d{1,2}/\d{4}', linea_limpia) or
                re.search(r'\d{1,2} de [a-z]+ de \d{4}', linea_limpia, re.IGNORECASE) or
                re.search(r'^[A-Z][a-z]+ [A-Z][a-z]+.*?(Córdoba|Madrid|Barcelona|Sevilla)', linea_limpia) or
                re.search(r'^[A-Z][a-z]+ [A-Z][a-z]+.*?[Aa]ctualizad', linea_limpia) or
                linea_limpia.startswith('Por:') or linea_limpia.startswith('Por ')):
                
                creditos = linea_limpia
                continue
        
        lineas_contenido.append(linea_limpia)
    
    texto = '\n'.join(lineas_contenido)
    texto = limpiar_parrafo(texto)
    
    return texto, creditos

def limpiar_parrafo(texto):
    """Limpia un párrafo de texto."""
    if not texto:
        return ""
    
    lineas_bloqueadas = [
        'cookies', 'aceptar', 'publicidad', 'suscríbete', 'newsletter',
        'compartir', 'facebook', 'twitter', 'whatsapp', 'telegram',
        'relacionados', 'también te puede interesar', 'más noticias',
        'copyright', 'todos los derechos', 'política de privacidad',
        'aviso legal', 'contacto', 'quiénes somos', 'síguenos en',
        'siguenos en', 'redes sociales', 'comentarios'
    ]
    
    lineas = texto.split('\n')
    lineas_limpias = []
    for linea in lineas:
        linea_lower = linea.lower().strip()
        if not any(bloque in linea_lower for bloque in lineas_bloqueadas):
            lineas_limpias.append(linea)
    
    texto = ' '.join(lineas_limpias)
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return limpiar_texto(texto)

def eliminar_frases_genericas(texto):
    """Elimina frases genéricas de desarrollo de la noticia."""
    if not texto:
        return texto
    
    texto_lower = texto.lower()
    
    for frase in FRASES_A_ELIMINAR:
        patron = re.compile(re.escape(frase), re.IGNORECASE)
        texto = patron.sub('', texto)
    
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto

# =============================================================================
# GESTIÓN DE HISTORIAL
# =============================================================================

def cargar_historial():
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
# PROCESAMIENTO Y PUBLICACIÓN
# =============================================================================

def extraer_imagen_web(url):
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

def dividir_en_parrafos_coherentes(texto, max_oraciones_por_parrafo=3):
    """
    Divide el texto en párrafos coherentes de 2-3 oraciones cada uno.
    Busca puntos de corte lógicos (después de citas, datos completos, etc.)
    """
    if not texto:
        return []
    
    # Dividir en oraciones manteniendo la puntuación
    oraciones = re.split(r'(?<=[.!?])\s+', texto)
    oraciones = [o.strip() for o in oraciones if len(o.strip()) > 10]
    
    if not oraciones:
        return [texto] if len(texto) > 20 else []
    
    parrafos = []
    parrafo_actual = []
    
    for i, oracion in enumerate(oraciones):
        parrafo_actual.append(oracion)
        
        # Decidir si cerrar el párrafo aquí
        cerrar_parrafo = False
        
        # Si tenemos suficientes oraciones
        if len(parrafo_actual) >= max_oraciones_por_parrafo:
            cerrar_parrafo = True
        
        # Si la oración termina en cita o dato importante
        if '"' in oracion or '«' in oracion or '»' in oracion:
            if len(parrafo_actual) >= 2:
                cerrar_parrafo = True
        
        # Si la siguiente oración empieza con conector de nuevo párrafo
        if i < len(oraciones) - 1:
            siguiente = oraciones[i + 1].lower()
            conectores_nuevo = ['sin embargo', 'por otro lado', 'además', 'por su parte', 
                              'en cuanto a', 'respecto a', 'por el contrario', 'asimismo',
                              'por tanto', 'en consecuencia', 'no obstante', 'a su vez']
            if any(siguiente.startswith(c) for c in conectores_nuevo):
                cerrar_parrafo = True
        
        if cerrar_parrafo and parrafo_actual:
            parrafos.append(' '.join(parrafo_actual))
            parrafo_actual = []
    
    # Agregar último párrafo si quedó algo
    if parrafo_actual:
        parrafos.append(' '.join(parrafo_actual))
    
    return parrafos

def construir_texto_publicacion(titulo, contenido_completo, creditos, fuente):
    """
    Construye el texto de la publicación con formato mejorado y espaciado.
    """
    titulo_limpio = limpiar_texto(titulo)
    
    # Procesar contenido en párrafos coherentes
    if contenido_completo:
        parrafos = dividir_en_parrafos_coherentes(contenido_completo, max_oraciones_por_parrafo=3)
    else:
        parrafos = ["Información en desarrollo. Los detalles de esta noticia internacional están siendo verificados por nuestros corresponsales."]
    
    # Limitar a máximo 4 párrafos para no hacerlo muy largo
    if len(parrafos) > 4:
        parrafos = parrafos[:4]
    
    # Construir líneas con espaciado adecuado
    lineas = []
    
    # Título destacado
    lineas.append(f"📰 ÚLTIMA HORA | {titulo_limpio}")
    lineas.append("")  # Línea en blanco
    
    # Párrafos de contenido con separación
    for i, parrafo in enumerate(parrafos):
        lineas.append(parrafo)
        if i < len(parrafos) - 1:  # No agregar línea extra después del último
            lineas.append("")  # Línea en blanco entre párrafos
    
    # Línea separadora antes de metadatos
    lineas.append("")
    lineas.append("─" * 30)  # Separador visual
    lineas.append("")
    
    # Créditos si existen
    if creditos:
        creditos_limpio = re.sub(r'\d{1,2}/\d{1,2}/\d{4}.*$', '', creditos).strip()
        creditos_limpio = re.sub(r'\d{1,2} de [a-z]+ de \d{4}.*$', '', creditos_limpio, flags=re.IGNORECASE).strip()
        if creditos_limpio:
            lineas.append(f"✍️ Autor: {creditos_limpio}")
            lineas.append("")
    
    # Fuente
    lineas.append(f"📎 Fuente: {fuente}")
    
    texto = '\n'.join(lineas)
    
    # Limpieza final
    texto = re.sub(r'https?://\S+', '', texto)
    texto = re.sub(r'\n{4,}', '\n\n\n', texto)  # Máximo 2 líneas en blanco seguidas
    
    return texto.strip()

def publicar_facebook(titulo, texto_completo, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales Facebook", 'error')
        return False
    
    # Construir mensaje final con espaciado
    mensaje = f"{texto_completo}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    
    # Verificar límite de caracteres
    if len(mensaje) > 1900:
        # Truncar manteniendo estructura
        lineas = texto_completo.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1500:
                texto_cortado += linea + "\n"
            else:
                break
        
        mensaje = f"{texto_cortado.rstrip()}\n\n[Continúa...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    
    # Limpieza final
    mensaje = re.sub(r'https?://\S+', '', mensaje)
    mensaje = re.sub(r'www\.\S+', '', mensaje)
    mensaje = re.sub(r'\n{4,}', '\n\n\n', mensaje)
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
    log(f"   URL: {noticia_seleccionada['url'][:70]}...")
    
    # =================================================================
    # EXTRACCIÓN DE CONTENIDO COMPLETO
    # =================================================================
    
    log("🌐 Extrayendo contenido completo de la web...")
    contenido_completo, creditos = extraer_contenido_completo(noticia_seleccionada['url'])
    
    if contenido_completo:
        log(f"   ✅ Contenido extraído: {len(contenido_completo)} caracteres", 'exito')
        if creditos:
            log(f"   👤 Créditos: {creditos[:60]}...", 'debug')
    else:
        log("   ⚠️ No se pudo extraer contenido completo, usando descripción de API", 'advertencia')
        contenido_completo = noticia_seleccionada.get('descripcion', '')
    
    # =================================================================
    # CONSTRUIR TEXTO DE PUBLICACIÓN
    # =================================================================
    
    log("📝 Construyendo texto de publicación...")
    texto_publicacion = construir_texto_publicacion(
        noticia_seleccionada['titulo'],
        contenido_completo,
        creditos,
        noticia_seleccionada['fuente']
    )
    
    log(f"   📄 Texto final ({len(texto_publicacion)} caracteres):", 'debug')
    for i, linea in enumerate(texto_publicacion.split('\n')[:6]):
        log(f"      {linea[:70]}{'...' if len(linea) > 70 else ''}", 'debug')
    
    # Generar hashtags
    hashtags = generar_hashtags_internacional(
        noticia_seleccionada['titulo'], 
        contenido_completo or noticia_seleccionada.get('descripcion', '')
    )
    
    # =================================================================
    # PROCESAR IMAGEN
    # =================================================================
    
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
    
    # =================================================================
    # PUBLICAR
    # =================================================================
    
    exito = publicar_facebook(
        noticia_seleccionada['titulo'],
        texto_publicacion,
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
