#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V4.8 (CERO TOLERANCIA INGLÉS)
Bot periodístico profesional - Solo contenido en español limpio
"""

import requests
import feedparser
import re
import hashlib
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
APITUBE_API_KEY = os.getenv('APITUBE_API_KEY')
THENEWSAPI_TOKEN = os.getenv('THENEWSAPI_TOKEN')
CURRENTS_API_KEY = os.getenv('CURRENTS_API_KEY')

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')
TIEMPO_ENTRE_PUBLICACIONES = 30
UMBRAL_SIMILITUD_TITULO = 0.75
MAX_TITULOS_HISTORIA = 200

BLACKLIST_TITULOS = [r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$']
PALABRAS_ALTA_PRIORIDAD = ["guerra hoy", "conflicto armado", "dictadura", "sanciones", "ucrania", "rusia", "gaza", "israel", "hamas", "iran", "china", "taiwan", "otan", "brics", "economia mundial", "inflacion", "crisis humanitaria", "refugiados", "derechos humanos", "protestas", "coup", "minerales estrategicos", "tierras raras", "drones", "inteligencia artificial guerra", "ciberataque", "zelensky", "netanyahu", "trump", "biden", "putin", "elecciones", "fraude", "corrupcion", "crisis", "ataque", "bombardeo", "invasion"]
PALABRAS_MEDIA_PRIORIDAD = ['economía', 'mercados', 'FMI', 'China', 'EEUU', 'Alemania', 'petroleo', 'gas', 'europa', 'asia', 'latinoamerica', 'mexico', 'brasil', 'argentina']

# Palabras agregador
PALABRAS_AGREGADOR = [
    'meneos', 'clics', 'clicks', 'menéalo', 'enviado:', 'hace', 'horas', 'días',
    'comentarios', 'compartir en facebook', 'compartir en twitter', 'compartir por correo',
    'etiquetas:', 'tags:', 'karma', 'puntos', 'votos', 'positivo', 'negativo',
    'reddit', 'upvotes', 'downvotes', 'submitted', 'posted by', 'u/', 'r/',
    'hacker news', 'hn', 'points', 'ycombinator',
    'slashdot', 'firehose', 'mod', 'score',
    'digg', 'dugg', 'bury',
    'fark', 'totalfark', 'ultrafark',
    '4chan', 'anon', 'thread', 'replies', 'bump',
    '9gag', 'upvote', 'downvote', 'hot', 'trending', 'viral',
    'whatsapp', 'telegram', 'compartir', 'share', 'tweet', 'like', 'follow'
]

# FRASES EN INGLÉS COMUNES EN NOTICIAS (para detección y eliminación)
FRASES_INGLES_COMUNES = [
    # Frases completas típicas
    r'i stand with',
    r'i support',
    r'we believe',
    r'this is unacceptable',
    r'this is unacceptable',
    r'however',
    r'therefore',
    r'furthermore',
    r'nevertheless',
    r'meanwhile',
    r'according to',
    r'in addition',
    r'as a result',
    r'due to',
    r'because of',
    r'in order to',
    r'with regard to',
    r'in response to',
    r'following',
    r'despite',
    r'although',
    r'while',
    r'during',
    r'before',
    r'after',
    r'between',
    r'among',
    r'against',
    r'towards',
    r'throughout',
    r'within',
    r'without',
    r'beyond',
    r'across',
    r'around',
    r'behind',
    r'beneath',
    r'beside',
    r'between',
    r'beyond',
    r'inside',
    r'outside',
    r'under',
    r'over',
    r'above',
    r'below',
    r'up',
    r'down',
    r'on',
    r'off',
    r'in',
    r'out',
    r'at',
    r'by',
    r'for',
    r'with',
    r'about',
    r'into',
    r'through',
    r'during',
    r'before',
    r'after',
    r'above',
    r'below',
    r'to',
    r'from',
    r'up',
    r'down',
    r'in',
    r'out',
    r'on',
    r'off',
    r'over',
    r'under',
    r'again',
    r'further',
    r'then',
    r'once',
    r'here',
    r'there',
    r'when',
    r'where',
    r'why',
    r'how',
    r'all',
    r'any',
    r'both',
    r'each',
    r'few',
    r'more',
    r'most',
    r'other',
    r'some',
    r'such',
    r'no',
    r'nor',
    r'not',
    r'only',
    r'own',
    r'same',
    r'so',
    r'than',
    r'too',
    r'very',
    r'can',
    r'will',
    r'just',
    r'should',
    r'now',
]

# Patrones de cortes
PATRONES_CORTE = [
    r'…$', r'\.\.\.$', r'\.\s*\.\s*\.$',
    r'\s+de…$', r'\s+de\.\.\.$', r'\s+a…$', r'\s+en…$',
    r'\s+que…$', r'\s+con…$', r'\s+por…$', r'\s+para…$',
    r'\s+un…$', r'\s+una…$', r'\s+los…$', r'\s+las…$',
    r'\s+del…$', r'\s+al…$', r'[a-záéíóúñ]\…$', r'[a-záéíóúñ]\.\.\.$',
]

# Links sociales
PATRONES_LINKS_SOCIALES = [
    r'pic\.twitter\.com/\S+',
    r't\.co/\S+',
    r'twitter\.com/\S+',
    r'x\.com/\S+',
    r'facebook\.com/\S+',
    r'instagram\.com/\S+',
    r'youtu\.be/\S+',
    r'youtube\.com/\S+',
    r'tiktok\.com/\S+',
    r'reddit\.com/\S+',
    r'linkedin\.com/\S+',
    r'telegram\.me/\S+',
    r'wa\.me/\S+',
]

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None: default = {}
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
            except: pass
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto: return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url_v3(url):
    if not url: return ""
    try:
        parsed = urlparse(url)
    except:
        return url.lower().strip()
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()
    netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)', '', netloc)
    path = re.sub(r'/index\.(html|php|htm|asp)$', '/', path)
    path = path.rstrip('/')
    path = re.sub(r'\.html?$', '', path)
    url_base = f"{netloc}{path}"
    query_params = []
    if parsed.query:
        params = parsed.query.split('&')
        for p in params:
            if '=' in p:
                key = p.split('=')[0].lower()
                if key in ['id', 'article', 'post', 'p', 'noticia', 'newsid', 'story']:
                    query_params.append(p.lower())
    if query_params:
        url_base += '?' + '&'.join(sorted(query_params))
    return url_base

def extraer_dominio_principal(url):
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        parts = netloc.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return netloc
    except:
        return ""

def calcular_similitud_titulos(t1, t2):
    if not t1 or not t2: return 0.0
    def n(t): 
        t = re.sub(r'[^\w\s]', '', t.lower().strip())
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'\b(el|la|los|las|un|una|en|de|del|al|y|o|que|con|por|para|sobre|entre|hacia|desde|hasta|durante|mediante|segun|según|hace|mas|más|muy|tan|tanto|como|cómo|cuando|donde|quien|cual|cuales|cuál|cuáles|esto|eso|aquello|este|ese|aquel|esta|esa|aquella|estos|esos|aquellos|estas|esas|aquellas|mi|tu|su|nuestro|vuestro|sus|mis|tus|nuestros|vuestros|me|te|se|nos|os|lo|le|les|ya|aun|aún|tambien|también|ademas|además|sin|embargo|porque|pues|asi|así|luego|entonces|aunque|a pesar|sin embargo|no obstante|the|of|and|to|in|is|that|for|it|with|as|on|be|this|was|are|at|by|from|have|has|had|not|been|or|an|but|their|more|will|would|could|should|may|might|can|shall)\b', '', t)
        return t.strip()
    return SequenceMatcher(None, n(t1), n(t2)).ratio()

def es_titulo_generico(titulo):
    if not titulo: return True
    tl = titulo.lower().strip()
    for p in BLACKLIST_TITULOS:
        if re.match(p, tl): return True
    stop = {'el','la','de','y','en','the','of','to','hoy'}
    pal = [p for p in re.findall(r'\b\w+\b', tl) if p not in stop and len(p)>3]
    return len(set(pal)) < 4

# ============================================================================
# SISTEMA CERO TOLERANCIA INGLÉS
# ============================================================================

def eliminar_links_sociales(texto):
    """Elimina todos los links de redes sociales."""
    if not texto:
        return texto
    
    texto_limpio = texto
    for patron in PATRONES_LINKS_SOCIALES:
        texto_limpio = re.sub(patron, '', texto_limpio, flags=re.IGNORECASE)
    
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def detectar_frase_ingles(linea):
    """
    Detecta si una línea contiene frases en inglés completas.
    Retorna (tiene_ingles, frase_detectada)
    """
    if not linea:
        return False, ""
    
    linea_lower = linea.lower().strip()
    
    # Verificar frases completas en inglés
    for frase in FRASES_INGLES_COMUNES:
        if frase in linea_lower:
            return True, frase
    
    # Detectar oraciones completas en inglés (más de 3 palabras inglesas consecutivas)
    palabras = linea.split()
    contador_ingles = 0
    for palabra in palabras:
        p_lower = palabra.lower().strip('.,!?;:"')
        # Palabras comunes en inglés que no son comunes en español
        if p_lower in ['the', 'and', 'that', 'have', 'for', 'not', 'with', 'you', 'this', 'but', 
                       'his', 'from', 'they', 'she', 'her', 'been', 'their', 'said', 'each',
                       'which', 'will', 'about', 'could', 'other', 'after', 'first', 'never',
                       'these', 'think', 'where', 'being', 'every', 'great', 'might', 'shall',
                       'stand', 'represent', 'however', 'allowing', 'return', 'granting', 'wild',
                       'card', 'fast', 'tracking', 'participation', 'without', 'qualification',
                       'unacceptable', 'while', 'aggression', 'against', 'paralympians', 'everything']:
            contador_ingles += 1
        else:
            if contador_ingles >= 3:  # Si tuvimos 3+ palabras inglesas seguidas
                return True, "secuencia de palabras en inglés"
            contador_ingles = 0
    
    if contador_ingles >= 3:
        return True, "secuencia de palabras en inglés al final"
    
    return False, ""

def filtrar_lineas_ingles(texto):
    """
    Filtra línea por línea, eliminando cualquier línea con contenido en inglés.
    """
    if not texto:
        return ""
    
    lineas = texto.split('\n')
    lineas_limpias = []
    
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        
        # Verificar si es línea de agregador
        es_agregador = False
        for palabra in PALABRAS_AGREGADOR:
            if palabra in linea.lower():
                es_agregador = True
                break
        
        if es_agregador:
            continue
        
        # Verificar si tiene frases en inglés
        tiene_ingles, frase = detectar_frase_ingles(linea)
        if tiene_ingles:
            log(f"   🚫 Eliminada línea con inglés: '{frase[:30]}...'", 'debug')
            continue
        
        # Verificar que tenga suficiente español
        palabras = linea.split()
        if len(palabras) < 3:
            continue
        
        lineas_limpias.append(linea)
    
    return '\n'.join(lineas_limpias)

def verificar_es_espanol_completo(texto):
    """
    Verificación estricta: el texto debe ser 100% español (permitiendo nombres propios).
    Retorna (es_valido, problema, texto_limpio)
    """
    if not texto:
        return False, "texto vacío", ""
    
    # Paso 1: Eliminar links
    texto = eliminar_links_sociales(texto)
    
    # Paso 2: Filtrar línea por línea
    texto = filtrar_lineas_ingles(texto)
    
    if not texto.strip():
        return False, "texto vacío después de filtrar inglés", ""
    
    # Paso 3: Verificación final de palabras sueltas en inglés
    palabras = texto.split()
    palabras_ingles_sueltas = 0
    
    for palabra in palabras:
        p_clean = palabra.lower().strip('.,!?;:"()[]{}')
        if p_clean in ['the', 'and', 'that', 'have', 'for', 'not', 'with', 'you', 'this', 
                       'but', 'his', 'from', 'they', 'she', 'her', 'been', 'their', 'said']:
            palabras_ingles_sueltas += 1
    
    # Si más del 2% son palabras inglesas sueltas, rechazar
    if len(palabras) > 0 and (palabras_ingles_sueltas / len(palabras)) > 0.02:
        return False, f"demasiadas palabras en inglés sueltas ({palabras_ingles_sueltas})", ""
    
    # Paso 4: Verificar longitud mínima
    if len(palabras) < 40:
        return False, f"texto muy corto ({len(palabras)} palabras)", ""
    
    # Paso 5: Verificar que haya al menos 2 párrafos
    parrafos = [p.strip() for p in texto.split('\n\n') if len(p.strip()) > 30]
    if len(parrafos) < 2:
        return False, f"solo {len(parrafos)} párrafo(s)", ""
    
    return True, "texto 100% español", texto

def limpiar_texto_mejorado(texto):
    """Limpieza básica."""
    if not texto: 
        return ""
    
    import html
    t = html.unescape(texto)
    
    t = re.sub(r'<br\s*/?>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<p>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'</p>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<[^>]+>', ' ', t)
    
    t = re.sub(r'https?://\S*', '', t)
    
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n+', '\n', t)
    
    patron = r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])'
    t = re.sub(patron, r'\1 \2', t)
    
    lineas = [linea.strip() for linea in t.split('\n') if linea.strip()]
    return '\n'.join(lineas).strip()

def calcular_puntaje(titulo, desc):
    txt = f"{titulo} {desc}".lower()
    p = 0
    for f in PALABRAS_ALTA_PRIORIDAD:
        pal = f.lower().split()
        for pa in pal:
            if len(pa) >= 4 and pa in txt:
                p += 3
                break
        if f.lower() in txt: p += 7
    for f in PALABRAS_MEDIA_PRIORIDAD:
        for pa in f.lower().split():
            if len(pa) >= 3 and pa in txt:
                p += 1
                break
    if 30 <= len(titulo) <= 150: p += 2
    if len(desc) >= 50: p += 2
    return p

# ============================================================================
# EXTRACCIÓN CON FILTRO ESTRICTO DE INGLÉS
# ============================================================================

def extraer_contenido_puro(url, descripcion_original="", max_intentos=3):
    """
    Extrae contenido con filtro estricto de inglés.
    """
    if not url: 
        return None, None
    
    intento = 0
    while intento < max_intentos:
        intento += 1
        log(f"   🔍 Intento {intento}/{max_intentos}...", 'debug')
        
        contenido, cred = extraer_contenido_raw(url, descripcion_original, estrategia=intento)
        
        if not contenido:
            continue
        
        # Verificación estricta de español
        es_valido, problema, contenido_limpio = verificar_es_espanol_completo(contenido)
        
        if es_valido and len(contenido_limpio.split()) >= 45:
            log(f"   ✅ Contenido 100% español: {len(contenido_limpio.split())} palabras", 'exito')
            return contenido_limpio, cred or "Agencias"
        
        log(f"   ⚠️ {problema}", 'advertencia')
    
    # Fallback: usar descripción si es español
    if descripcion_original and len(descripcion_original) > 100:
        log("   ⚠️ Intentando con descripción original...", 'advertencia')
        es_valido, problema, desc_limpia = verificar_es_espanol_completo(descripcion_original)
        if es_valido and len(desc_limpia.split()) >= 40:
            return desc_limpia, "Resumen de la noticia"
    
    return None, None

def extraer_contenido_raw(url, descripcion_original="", estrategia=1):
    if not url:
        return None, None
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
        s = BeautifulSoup(r.content, 'html.parser')
        
        for e in s(['script','style','nav','header','footer','aside','form','button','iframe','noscript',
                   'div[class*="comments"]', 'div[class*="votos"]', 'div[class*="karma"]',
                   'div[class*="share"]', 'div[class*="social"]', 'div[class*="metadata"]']): 
            e.decompose()
        
        contenido_parrafos = []
        
        if estrategia == 1:
            art = s.find('article')
            if art:
                ps = art.find_all('p')
                for p in ps:
                    texto_p = p.get_text().strip()
                    if 70 < len(texto_p) < 700:
                        limpio = limpiar_texto_mejorado(texto_p)
                        limpio_sin_links = eliminar_links_sociales(limpio)
                        if limpio_sin_links and len(limpio_sin_links.split()) > 12:
                            contenido_parrafos.append(limpio_sin_links)
            
            if len(contenido_parrafos) < 3:
                for clase in ['article-content', 'entry-content', 'post-content', 'content-body', 
                             'story-body', 'news-text', 'text-content']:
                    div = s.find(['div', 'section'], class_=lambda x: x and clase in str(x).lower())
                    if div:
                        ps = div.find_all('p')
                        for p in ps:
                            texto_p = p.get_text().strip()
                            if 70 < len(texto_p) < 700:
                                limpio = limpiar_texto_mejorado(texto_p)
                                limpio_sin_links = eliminar_links_sociales(limpio)
                                if limpio_sin_links and len(limpio_sin_links.split()) > 12:
                                    contenido_parrafos.append(limpio_sin_links)
                        if len(contenido_parrafos) >= 3:
                            break
        
        elif estrategia == 2:
            body = s.find('body')
            if body:
                ps = body.find_all('p')
                for p in ps:
                    texto_p = p.get_text().strip()
                    if 100 < len(texto_p) < 600 and len(texto_p.split()) > 15:
                        if any(c in texto_p for c in ['.', ',', ';']) and not re.match(r'^[\d\sK]+$', texto_p):
                            limpio = limpiar_texto_mejorado(texto_p)
                            limpio_sin_links = eliminar_links_sociales(limpio)
                            if limpio_sin_links and limpio_sin_links not in contenido_parrafos:
                                contenido_parrafos.append(limpio_sin_links)
        
        elif estrategia == 3:
            meta_desc = s.find('meta', attrs={'name': 'description'}) or s.find('meta', property='og:description')
            if meta_desc:
                desc = meta_desc.get('content', '')
                if desc and len(desc) > 100:
                    desc_limpia = eliminar_links_sociales(limpiar_texto_mejorado(desc))
                    contenido_parrafos.append(desc_limpia)
        
        if len(contenido_parrafos) >= 2:
            return '\n\n'.join(contenido_parrafos[:8]), None
        
        return None, None
        
    except Exception as e:
        log(f"   Error: {str(e)[:80]}", 'error')
        return None, None

def dividir_en_parrafos_presentacion(texto):
    if not texto:
        return []
    
    if '\n\n' in texto:
        return [p.strip() for p in texto.split('\n\n') if len(p.strip()) > 25][:6]
    
    if '\n' in texto:
        pars = [p.strip() for p in texto.split('\n') if len(p.strip()) > 25]
        if len(pars) >= 2:
            return pars[:6]
    
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    if len(oraciones) < 2:
        return [texto] if len(texto) > 50 else []
    
    parrafos = []
    i = 0
    while i < len(oraciones):
        grupo = oraciones[i:i+2] if i + 2 < len(oraciones) else oraciones[i:]
        parrafo = ' '.join(grupo)
        if len(parrafo.split()) >= 12:
            parrafos.append(parrafo)
        i += len(grupo)
        if len(parrafos) >= 6:
            break
    
    return parrafos

def construir_publicacion(titulo, contenido, creditos, fuente):
    t = limpiar_texto_mejorado(titulo)
    pars = dividir_en_parrafos_presentacion(contenido)
    
    if not pars:
        pars = [contenido[:600]] if contenido else []
    
    lineas = [f"📰 ÚLTIMA HORA | {t}", ""]
    
    for i, p in enumerate(pars):
        lineas.append(p)
        if i < len(pars) - 1: 
            lineas.append("")
    
    lineas.extend(["", "──────────────────────────────", ""])
    
    if creditos: 
        lineas.extend([f"✍️ {creditos}", ""])
    
    lineas.append(f"📎 {fuente}")
    
    return '\n'.join(lineas)

def cargar_historial():
    d = {
        'urls': [], 'urls_normalizadas': [], 'hashes': [], 'timestamps': [], 
        'titulos': [], 'descripciones': [], 'hashes_contenido': [], 
        'hashes_permanentes': [], 'estadisticas': {'total_publicadas': 0}
    }
    h = cargar_json(HISTORIAL_PATH, d)
    for k in d: 
        if k not in h: h[k] = d[k]
    limpiar_historial_antiguo(h)
    return h

def limpiar_historial_antiguo(h):
    try:
        ahora = datetime.now()
        indices_a_mantener = []
        for i, ts in enumerate(h.get('timestamps', [])):
            try:
                fecha = datetime.fromisoformat(ts)
                if (ahora - fecha).days < 7:
                    indices_a_mantener.append(i)
            except: 
                continue
        
        for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps', 'titulos', 'descripciones', 'hashes_contenido']:
            if key in h and isinstance(h[key], list):
                h[key] = [h[key][i] for i in indices_a_mantener if i < len(h[key])]
        
        if len(h.get('hashes_permanentes', [])) > 100:
            h['hashes_permanentes'] = h['hashes_permanentes'][-100:]
            
    except Exception as e:
        log(f"Error limpiando historial: {e}", 'error')

def noticia_ya_publicada(h, url, titulo, desc=""):
    if not h: 
        return False, "sin_historial"
    
    url_n = normalizar_url_v3(url)
    hash_t = generar_hash(titulo)
    dominio = extraer_dominio_principal(url)
    
    if es_titulo_generico(titulo): 
        return True, "titulo_generico"
    
    for uh in h.get('urls_normalizadas', []):
        if isinstance(uh, str) and url_n == uh: 
            return True, "url_normalizada_exacta"
    
    for i, uh in enumerate(h.get('urls', [])):
        if not isinstance(uh, str): 
            continue
        if extraer_dominio_principal(uh) == dominio:
            titulo_h = h.get('titulos', [])[i] if i < len(h.get('titulos', [])) else ""
            if titulo_h and calcular_similitud_titulos(titulo, titulo_h) >= 0.85:
                return True, f"misma_noticia_sitio"
    
    todos_h = list(dict.fromkeys(h.get('hashes', []) + h.get('hashes_permanentes', [])))
    if hash_t in todos_h: 
        return True, "hash_titulo_exacto"
    
    for th in h.get('titulos', []):
        if not isinstance(th, str): 
            continue
        if calcular_similitud_titulos(titulo, th) >= UMBRAL_SIMILITUD_TITULO: 
            return True, f"similitud_titulo"
    
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc=""):
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido','hashes_permanentes','estadisticas']:
        if k not in h: 
            h[k] = [] if k != 'estadisticas' else {'total_publicadas': 0}
    
    url_n = normalizar_url_v3(url)
    hash_t = generar_hash(titulo)
    
    for uh in h.get('urls_normalizadas', []):
        if isinstance(uh, str) and uh == url_n:
            return h
    
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1
    h['hashes_permanentes'].append(hash_t)
    
    if len(h['hashes_permanentes']) > 300: 
        h['hashes_permanentes'] = h['hashes_permanentes'][-300:]
    
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA: 
            h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    
    guardar_json(HISTORIAL_PATH, h)
    return h

def verificar_tiempo():
    e = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u: 
        return True
    
    try:
        m = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if m < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {m:.0f} min (objetivo: {TIEMPO_ENTRE_PUBLICACIONES} min)", 'info')
            return False
    except: 
        pass
    
    return True

# ============================================================================
# FUENTES Y PUBLICACIÓN
# ============================================================================

def resolver_redireccion_google(url):
    if not url or not url.startswith('https://news.google.com'): 
        return None
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
        u = r.url
        
        if 'google.com' in u and '/sorry' in u: 
            return None
        
        if u == url:
            u = requests.head(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True).url
        
        u = re.sub(r'\?.*$', '', re.sub(r'#.*$', '', u))
        
        return u if u != url and 'google.com' not in u else None
        
    except: 
        return None

def obtener_newsapi():
    if not NEWS_API_KEY: 
        return []
    n = []
    queries = ['Ukraine war Russia', 'China Taiwan', 'economy inflation']
    for q in queries[:2]:
        try:
            r = requests.get('https://newsapi.org/v2/everything', 
                           params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es', 
                                  'sortBy': 'publishedAt', 'pageSize': 5}, 
                           timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'ok':
                    for a in data.get('articles', []):
                        t = a.get('title', '')
                        if t and '[Removed]' not in t:
                            d = a.get('description', '') or ''
                            n.append({
                                'titulo': limpiar_texto_mejorado(t), 
                                'descripcion': limpiar_texto_mejorado(d), 
                                'url': a.get('url', ''), 
                                'imagen': a.get('urlToImage'), 
                                'fuente': f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}", 
                                'fecha': a.get('publishedAt'), 
                                'puntaje': calcular_puntaje(t, d)
                            })
        except: 
            pass
    log(f"NewsAPI.org: {len(n)} noticias", 'info')
    return n

def extraer_imagen_web(url):
    if not url: 
        return None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        
        for m in ['og:image', 'twitter:image']:
            t = s.find('meta', property=m) or s.find('meta', attrs={'name': m})
            if t:
                i = t.get('content', '').strip()
                if i and i.startswith('http') and 'google' not in i.lower(): 
                    return i
        
        art = s.find('article') or s.find('main')
        if art:
            for img in art.find_all('img'):
                src = img.get('data-src') or img.get('src', '')
                if src and src.startswith('http') and 'google' not in src.lower():
                    return src
        return None
    except: 
        return None

def descargar_imagen(url):
    if not url: 
        return None
    for b in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon']:
        if b in url.lower(): 
            return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200: 
            return None
        if 'image' not in r.headers.get('content-type', ''): 
            return None
        
        img = Image.open(BytesIO(r.content))
        w, h = img.size
        if w < 400 or h < 300: 
            return None
        
        if img.mode in ('RGBA', 'P'): 
            img = img.convert('RGB')
        img.thumbnail((1200, 1200))
        
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=85)
        
        if os.path.getsize(p) < 5000:
            os.remove(p)
            return None
        return p
    except: 
        return None

def crear_imagen_titulo(titulo):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.new('RGB', (1200, 630), color='#0f172a')
        draw = ImageDraw.Draw(img)
        
        try:
            fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            fb = fs = ImageFont.load_default()
        
        draw.rectangle([(0, 0), (1200, 8)], fill='#3b82f6')
        
        tt = textwrap.fill(titulo[:140], width=36)
        ls = tt.split('\n')
        y = (630 - len(ls)*50) // 2 - 50
        
        draw.text((60, y), tt, font=fb, fill='white')
        draw.text((60, 550), "🌍 Noticias Internacionales", font=fs, fill='#94a3b8')
        draw.text((60, 580), "Verdad Hoy • Agencia de Noticias", font=fs, fill='#64748b')
        
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img.save(p, 'JPEG', quality=90)
        return p
    except: 
        return None

def generar_hashtags(t, c):
    txt = f"{t} {c}".lower()
    h = ['#NoticiasInternacionales', '#ÚltimaHora']
    temas = {
        'guerra|conflicto|ataque': '#ConflictoArmado', 
        'ucrania|rusia|putin': '#UcraniaRusia', 
        'gaza|israel|hamas': '#IsraelGaza', 
        'trump|biden': '#PolíticaGlobal', 
        'economía|inflación': '#EconomíaMundial', 
        'china|taiwan': '#ChinaTaiwán'
    }
    for p, tag in temas.items():
        if re.search(p, txt): 
            h.append(tag)
            break
    h.append('#Mundo')
    return ' '.join(h)

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN: 
        return False
    
    m = f"{texto}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    
    if len(m) > 2000:
        lineas = texto.split('\n')
        tc = ""
        for ln in lineas:
            if len(tc + ln + "\n") < 1400: 
                tc += ln + "\n"
            else: 
                break
        m = f"{tc.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            r = requests.post(url, files={'file': ('imagen.jpg', f, 'image/jpeg')}, 
                            data={'message': m, 'access_token': FB_ACCESS_TOKEN}, 
                            timeout=60).json()
        
        if 'id' in r:
            log(f"✅ Publicado ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook: {r.get('error', {}).get('message', 'Unknown')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando: {e}", 'error')
    
    return False

# ============================================================================
# FUNCIÓN PRINCIPAL CON FILTRO ESTRICTO
# ============================================================================

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V4.8 (CERO TOLERANCIA INGLÉS)")
    print("📰 Bot periodístico profesional - Solo español")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    h = cargar_historial()
    log(f"📊 Historial: {len(h.get('urls', []))} URLs previas")
    
    # Recolectar noticias
    n = obtener_newsapi()
    
    if not n:
        log("ERROR CRÍTICO: Ninguna fuente devolvió noticias", 'error')
        return False
    
    # Deduplicación
    urls_vistas = set()
    n_unicas = []
    for nt in n:
        url_n = normalizar_url_v3(nt.get('url', ''))
        if url_n not in urls_vistas:
            urls_vistas.add(url_n)
            n_unicas.append(nt)
    
    n = n_unicas
    log(f"📰 Únicas tras deduplicación: {len(n)} noticias")
    
    # Ordenar por puntaje
    n.sort(key=lambda x: x.get('puntaje', 0), reverse=True)
    
    # Buscar noticia válida 100% español
    sel = None
    cont = None
    cred = None
    
    for i, nt in enumerate(n[:40]):  # Aumentado a 40 intentos
        url = nt.get('url', '')
        t = nt.get('titulo', '')
        d = nt.get('descripcion', '')
        
        if not url or not t: 
            continue
        
        # Saltar agregadores conocidos
        es_agregador_url = any(agg in url.lower() for agg in ['meneame', 'reddit', 'news.ycombinator'])
        if es_agregador_url:
            log(f"   [{i+1}] ⚠️ Saltando agregador: {url[:40]}...", 'advertencia')
            continue
        
        dup, rz = noticia_ya_publicada(h, url, t, d)
        if dup:
            log(f"   [{i+1}] ❌ Duplicada: {t[:50]}...", 'debug')
            continue
        
        log(f"   [{i+1}] ✅ Candidata: {t[:50]}...")
        
        # Extraer con filtro estricto de inglés
        cont, cred = extraer_contenido_puro(url, d, max_intentos=3)
        
        if cont and len(cont.split()) >= 45:
            # Verificación final estricta
            es_valido, problema, cont_final = verificar_es_espanol_completo(cont)
            
            if es_valido and len(cont_final.split()) >= 45:
                sel = nt
                cont = cont_final
                log(f"   ✅ NOTICIA VALIDADA - 100% ESPAÑOL", 'exito')
                log(f"   📊 {len(cont.split())} palabras, {len(cont.split(chr(10)))} párrafos", 'info')
                break
            else:
                log(f"   ❌ Falló validación final: {problema}", 'error')
        else:
            log(f"   ❌ Sin contenido suficiente o no es español", 'error')
    
    if not sel:
        log("ERROR: No se encontró noticia 100% en español", 'error')
        return False
    
    # Construir y publicar
    pub = construir_publicacion(sel['titulo'], cont, cred or "Agencias", sel['fuente'])
    ht = generar_hashtags(sel['titulo'], cont)
    
    log("🖼️  Procesando imagen...")
    img_path = None
    
    if sel.get('imagen'):
        img_path = descargar_imagen(sel['imagen'])
    
    if not img_path:
        iu = extraer_imagen_web(sel['url'])
        if iu: 
            img_path = descargar_imagen(iu)
    
    if not img_path:
        img_path = crear_imagen_titulo(sel['titulo'])
    
    if not img_path:
        log("ERROR: Sin imagen", 'error')
        return False
    
    ok = publicar_facebook(sel['titulo'], pub, img_path, ht)
    
    try:
        if os.path.exists(img_path): 
            os.remove(img_path)
    except: 
        pass
    
    if ok:
        h = guardar_historial(h, sel['url'], sel['titulo'], cont[:400])
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log(f"✅ ÉXITO - Total histórico: {h.get('estadisticas', {}).get('total_publicadas', 0)} noticias", 'exito')
        return True
    else:
        log("❌ Publicación fallida", 'error')
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
