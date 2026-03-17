#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V4.2 (CORREGIDO - LIMPIEZA MEJORADA)
Fuentes: NewsAPI, NewsData, GNews, ApiTube, TheNewsAPI, Currents, Google News, RSS
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
TIEMPO_ENTRE_PUBLICACIONES = 30  # 30 minutos
UMBRAL_SIMILITUD_TITULO = 0.75
UMBRAL_SIMILITUD_CONTENIDO = 0.65
MAX_TITULOS_HISTORIA = 200
MIN_NOTICIAS_POR_FUENTE = 3

BLACKLIST_TITULOS = [r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$']
PALABRAS_ALTA_PRIORIDAD = ["guerra hoy", "conflicto armado", "dictadura", "sanciones", "ucrania", "rusia", "gaza", "israel", "hamas", "iran", "china", "taiwan", "otan", "brics", "economia mundial", "inflacion", "crisis humanitaria", "refugiados", "derechos humanos", "protestas", "coup", "minerales estrategicos", "tierras raras", "drones", "inteligencia artificial guerra", "ciberataque", "zelensky", "netanyahu", "trump", "biden", "putin", "elecciones", "fraude", "corrupcion", "crisis", "ataque", "bombardeo", "invasion"]
PALABRAS_MEDIA_PRIORIDAD = ['economía', 'mercados', 'FMI', 'China', 'EEUU', 'Alemania', 'petroleo', 'gas', 'europa', 'asia', 'latinoamerica', 'mexico', 'brasil', 'argentina']

# NUEVO: Lista de fuentes/medios comunes que pueden aparecer pegados al texto
FUENTES_MEDIOS = [
    'cnn', 'bbc', 'fox news', 'msnbc', 'abc news', 'cbs news', 'nbc news', 
    'reuters', 'associated press', 'ap news', 'bloomberg', 'the guardian', 
    'the new york times', 'new york times', 'the washington post', 'washington post',
    'los angeles times', 'la times', 'el paÍs', 'el mundo', 'el diario', 
    'univision', 'telemundo', 'caracol', 'rcn', 'clarín', 'infobae', 'cnn en español',
    'cnn español', 'el nuevo día', 'el nuevo dia', 'la nación', 'la nacion',
    'financial times', 'the wall street journal', 'wall street journal',
    'al jazeera', 'rt', 'russia today', 'france 24', 'deutsche welle', 'dw',
    'china daily', 'xinhua', 'tass', 'agenzia nova', 'ansa', 'efe', ' Europa Press'
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
                log(f"Backup creado: {backup}", 'advertencia')
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

def calcular_similitud_contenido(c1, c2, longitud=100):
    if not c1 or not c2: return 0.0
    def n(c):
        c = re.sub(r'[^\w\s]', '', c.lower().strip())
        c = re.sub(r'\s+', ' ', c)
        return c[:longitud]
    return SequenceMatcher(None, n(c1), n(c2)).ratio()

def es_titulo_generico(titulo):
    if not titulo: return True
    tl = titulo.lower().strip()
    for p in BLACKLIST_TITULOS:
        if re.match(p, tl): return True
    stop = {'el','la','de','y','en','the','of','to','hoy'}
    pal = [p for p in re.findall(r'\b\w+\b', tl) if p not in stop and len(p)>3]
    return len(set(pal)) < 4

# ============================================================================
# NUEVAS FUNCIONES DE LIMPIEZA MEJORADAS
# ============================================================================

def separar_palabras_pegadas(texto):
    """
    Separa palabras que quedaron pegadas en camelCase o PascalCase.
    Ejemplo: 'EspañolIsrael' → 'Español Israel', 'TimesEl' → 'Times El'
    """
    if not texto:
        return texto
    
    # Patrón para detectar cambios de caso que indican palabras separadas
    # Ej: "CNN en EspañolIsrael" → "CNN en Español Israel"
    patron = r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])'
    texto = re.sub(patron, r'\1 \2', texto)
    
    # Separar cuando hay un nombre de medio seguido de mayúscula
    # Ej: "TimesEl" → "Times El"
    for fuente in FUENTES_MEDIOS:
        patron = rf'({re.escape(fuente)})([A-ZÁÉÍÓÚÑ])'
        texto = re.sub(patron, r'\1 \2', texto, flags=re.IGNORECASE)
    
    return texto

def limpiar_fuentes_medios(texto):
    """
    Elimina o separa nombres de fuentes que quedaron pegados al contenido.
    """
    if not texto:
        return texto
    
    # Lista de patrones de fuentes seguidas de texto
    patrones_fuentes = [
        r'CNN en Español', r'BBC', r'Univision', r'Los Angeles Times',
        r'El Nuevo Día', r'El País', r'Reuters', r'Associated Press',
        r'Fox News', r'MSNBC', r'ABC News', r'CBS News', r'NBC News',
        r'Bloomberg', r'The Guardian', r'New York Times', r'Washington Post',
        r'La Nación', r'Clarín', r'Infobae', r'El Mundo'
    ]
    
    # Separar fuentes que están pegadas al inicio de oraciones
    for patron in patrones_fuentes:
        # Si la fuente está pegada a una mayúscula (inicio de siguiente oración)
        texto = re.sub(rf'({patron})([A-ZÁÉÍÓÚÑ])', r'\1. \2', texto, flags=re.IGNORECASE)
        # Si la fuente está pegada con minúscula
        texto = re.sub(rf'({patron})([a-záéíóúñ])', r'\1 \2', texto, flags=re.IGNORECASE)
    
    return texto

def limpiar_texto_mejorado(texto):
    """
    Versión mejorada de limpiar_texto con correcciones adicionales.
    """
    if not texto: 
        return ""
    
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    
    # NUEVO: Separar palabras pegadas
    t = separar_palabras_pegadas(t)
    
    # NUEVO: Limpiar fuentes de medios pegadas
    t = limpiar_fuentes_medios(t)
    
    # NUEVO: Eliminar múltiples espacios que pudieron quedar
    t = re.sub(r'\s+', ' ', t)
    
    t = t.strip()
    
    # Asegurar puntuación final
    if t and t[-1] not in '.!?': 
        t += '.'
    
    return t.strip()

def detectar_texto_incoherente(texto):
    """
    Detecta si el texto tiene problemas de coherencia (múltiples fuentes mezcladas,
    cambios abruptos de tema, etc.)
    Retorna True si el texto parece incoherente.
    """
    if not texto or len(texto) < 50:
        return True
    
    # Detectar múltiples nombres de fuentes en el texto (indica mezcla de noticias)
    fuentes_encontradas = []
    for fuente in FUENTES_MEDIOS:
        if re.search(rf'\b{re.escape(fuente)}\b', texto, re.IGNORECASE):
            fuentes_encontradas.append(fuente)
    
    # Si hay 3 o más fuentes diferentes, probablemente es una mezcla de noticias
    if len(fuentes_encontradas) >= 3:
        log(f"   ⚠️ Texto incoherente detectado: {len(fuentes_encontradas)} fuentes diferentes encontradas", 'advertencia')
        return True
    
    # Detectar cambios abruptos de caso (indica concatenación)
    cambios_caso = len(re.findall(r'[a-záéíóúñ][A-ZÁÉÍÓÚÑ]', texto))
    if cambios_caso > 5:
        log(f"   ⚠️ Posible concatenación detectada: {cambios_caso} cambios de caso", 'advertencia')
        return True
    
    # Verificar que las oraciones tengan sentido (longitud promedio razonable)
    oraciones = [o.strip() for o in re.split(r'[.!?]+', texto) if len(o.strip()) > 10]
    if len(oraciones) > 0:
        longitudes = [len(o.split()) for o in oraciones]
        if max(longitudes) > 50:  # Oración demasiado larga
            log(f"   ⚠️ Oración extremadamente larga detectada ({max(longitudes)} palabras)", 'advertencia')
            return True
    
    return False

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
# EXTRACCIÓN DE CONTENIDO MEJORADA
# ============================================================================

def extraer_contenido_mejorado(url, descripcion_original=""):
    """
    Versión mejorada de extracción de contenido con validaciones adicionales.
    """
    if not url: 
        return None, None
    
    # Si es Google News, intentar resolver redirección primero
    if 'news.google.com' in url:
        url_resuelto = resolver_redireccion_google(url)
        if url_resuelto:
            url = url_resuelto
            log(f"   🔀 Redirigido a: {url[:80]}...", 'debug')
        else:
            log("   ⚠️ No se pudo resolver redirección de Google News", 'advertencia')
            # Usar descripción original si está disponible
            if descripcion_original and len(descripcion_original) > 100:
                return limpiar_texto_mejorado(descripcion_original), "Descripción de feed"
            return None, None
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        
        # Eliminar elementos no deseados
        for e in s(['script','style','nav','header','footer','aside','form','button']): 
            e.decompose()
        
        # Buscar artículo principal
        art = s.find('article')
        contenido_encontrado = None
        
        if art:
            ps = art.find_all('p')
            if len(ps) >= 2:
                txt = ' '.join([limpiar_texto_mejorado(p.get_text()) for p in ps if len(p.get_text()) > 40])
                if len(txt) > 200:
                    contenido_encontrado = txt[:1500]
        
        # Si no se encontró en article, buscar en clases comunes
        if not contenido_encontrado:
            for c in ['article-content','entry-content','post-content','content-body','story-body']:
                e = s.find(class_=lambda x: x and c in x.lower())
                if e:
                    ps = e.find_all('p')
                    if len(ps) >= 2:
                        txt = ' '.join([limpiar_texto_mejorado(p.get_text()) for p in ps if len(p.get_text()) > 40])
                        if len(txt) > 200:
                            contenido_encontrado = txt[:1500]
                            break
        
        # Si aún no hay contenido, buscar todos los párrafos del body
        if not contenido_encontrado:
            body = s.find('body')
            if body:
                ps = body.find_all('p')
                # Filtrar párrafos más estrictamente
                textos_validos = []
                for p in ps:
                    texto_p = p.get_text().strip()
                    # Debe tener longitud adecuada y no ser navegación/legal
                    if len(texto_p) > 60 and len(texto_p) < 800:
                        # Evitar párrafos que parezcan menús o legales
                        if not any(palabra in texto_p.lower() for palabra in 
                                  ['cookies', 'términos de uso', 'política de privacidad', 
                                   'copyright', 'derechos reservados', 'síguenos en']):
                            textos_validos.append(limpiar_texto_mejorado(texto_p))
                
                if len(textos_validos) >= 2:
                    contenido_encontrado = ' '.join(textos_validos[:6])  # Limitar a 6 párrafos
        
        # Validar el contenido encontrado
        if contenido_encontrado:
            # Verificar coherencia
            if detectar_texto_incoherente(contenido_encontrado):
                log("   ⚠️ Contenido extraído parece incoherente, usando descripción alternativa", 'advertencia')
                if descripcion_original and len(descripcion_original) > 100:
                    return limpiar_texto_mejorado(descripcion_original), "Descripción de feed (fallback)"
                return None, None
            
            # Verificar que no tenga demasiadas fuentes pegadas
            fuentes_count = sum(1 for fuente in FUENTES_MEDIOS 
                              if re.search(rf'\b{re.escape(fuente)}\b', contenido_encontrado, re.IGNORECASE))
            if fuentes_count >= 2:
                log(f"   ⚠️ Contenido tiene {fuentes_count} referencias a fuentes, posible mezcla", 'advertencia')
                # Intentar limpiar más agresivamente
                contenido_encontrado = limpiar_fuentes_medios(contenido_encontrado)
            
            return contenido_encontrado[:2000], None
        
        # Fallback a descripción original
        if descripcion_original and len(descripcion_original) > 100:
            return limpiar_texto_mejorado(descripcion_original), "Descripción de feed"
            
        return None, None
        
    except Exception as e:
        log(f"   Error extrayendo contenido: {e}", 'error')
        if descripcion_original and len(descripcion_original) > 100:
            return limpiar_texto_mejorado(descripcion_original), "Descripción de feed (error)"
        return None, None

def dividir_parrafos(texto):
    if not texto: 
        return []
    
    # Dividir en oraciones primero
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    
    if len(oraciones) < 2: 
        return [texto] if len(texto) > 100 else []
    
    # Agrupar oraciones en párrafos de ~40-60 palabras
    parrafos, parrafo_actual, palabras_actuales = [], [], 0
    
    for i, oracion in enumerate(oraciones):
        parrafo_actual.append(oracion)
        palabras_actuales += len(oracion.split())
        
        # Crear nuevo párrafo cuando alcanzamos ~50 palabras o es la última oración
        if palabras_actuales >= 50 or i == len(oraciones) - 1:
            if len(' '.join(parrafo_actual).split()) >= 15:
                parrafos.append(' '.join(parrafo_actual))
            parrafo_actual, palabras_actuales = [], 0
    
    return parrafos[:6]  # Limitar a 6 párrafos máximo

def construir_publicacion(titulo, contenido, creditos, fuente):
    t = limpiar_texto_mejorado(titulo)
    pars = dividir_parrafos(contenido)
    
    # Si no hay párrafos válidos, intentar dividir de otra forma
    if len(pars) < 2:
        oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        pars = []
        temp = []
        palabras = 0
        for oracion in oraciones:
            temp.append(oracion)
            palabras += len(oracion.split())
            if palabras >= 40:
                pars.append(' '.join(temp))
                temp, palabras = [], 0
        if temp:
            pars.append(' '.join(temp))
        pars = pars[:6]
    
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
    hash_d = generar_hash(desc) if desc else ""
    dominio = extraer_dominio_principal(url)
    
    log(f"   🔍 Verificando duplicados:", 'debug')
    log(f"      URL norm: {url_n[:80]}...", 'debug')
    
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
    
    if hash_d and hash_d in h.get('hashes_contenido', []):
        return True, "hash_contenido_exacto"
    
    for th in h.get('titulos', []):
        if not isinstance(th, str): 
            continue
        if calcular_similitud_titulos(titulo, th) >= UMBRAL_SIMILITUD_TITULO: 
            return True, f"similitud_titulo"
    
    if desc:
        for dh in h.get('descripciones', []):
            if not isinstance(dh, str) or not dh: 
                continue
            if calcular_similitud_contenido(desc, dh, 150) >= UMBRAL_SIMILITUD_CONTENIDO:
                return True, f"similitud_contenido"
    
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc=""):
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido','hashes_permanentes','estadisticas']:
        if k not in h: 
            h[k] = [] if k != 'estadisticas' else {'total_publicadas': 0}
    
    url_n = normalizar_url_v3(url)
    hash_t = generar_hash(titulo)
    
    for uh in h.get('urls_normalizadas', []):
        if isinstance(uh, str) and uh == url_n:
            log(f"⚠️ Intento de duplicado detectado en guardar_historial", 'advertencia')
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
# FUENTES DE NOTICIAS (mantenidas igual, solo se muestra una como ejemplo)
# ============================================================================

def obtener_newsapi():
    if not NEWS_API_KEY: 
        log("NewsAPI: No API key configurada", 'debug')
        return []
    n = []
    queries = [
        'Ukraine war Russia', 'Israel Gaza conflict', 'China Taiwan',
        'economy inflation', 'NATO Europe', 'cyberattack', 'coup'
    ]
    for q in queries[:3]:
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
                            d = a.get('description', '')
                            n.append({
                                'titulo': limpiar_texto_mejorado(t), 
                                'descripcion': limpiar_texto_mejorado(d), 
                                'url': a.get('url', ''), 
                                'imagen': a.get('urlToImage'), 
                                'fuente': f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}", 
                                'fecha': a.get('publishedAt'), 
                                'puntaje': calcular_puntaje(t, d)
                            })
            else:
                log(f"NewsAPI error {r.status_code}", 'error')
        except Exception as e:
            log(f"NewsAPI excepción: {e}", 'error')
    log(f"NewsAPI.org: {len(n)} noticias", 'info')
    return n

# [Las demás funciones de fuentes se mantienen similares, aplicando limpiar_texto_mejorado]
# obtener_newsdata(), obtener_gnews(), obtener_apitube(), etc.
# (omitidas por brevedad, usar las originales con limpiar_texto_mejorado en lugar de limpiar_texto)

def resolver_redireccion_google(url):
    if not url or not url.startswith('https://news.google.com'): 
        return url
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
        u = r.url
        
        if 'google.com' in u and '/sorry' in u: 
            return None
        
        if u == url:
            u = requests.head(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True).url
        
        # Limpiar parámetros de tracking
        u = re.sub(r'\?.*$', '', re.sub(r'#.*$', '', u))
        
        return u if u != url else None
        
    except: 
        return None

def obtener_google_news():
    feeds = [
        'https://news.google.com/rss?hl=es&gl=US&ceid=US:es', 
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNRE55YXpBU0JXVnVMVWRDS0FBUAE?hl=es&gl=US&ceid=US:es',
    ]
    n = []
    for f in feeds:
        try:
            feed = feedparser.parse(f, request_headers={'User-Agent': 'Mozilla/5.0'})
            if not feed or not feed.entries: 
                continue
            
            for e in feed.entries[:10]:
                t = e.get('title', '')
                if not t or '[Removed]' in t: 
                    continue
                
                # Limpiar título (quitar nombre de fuente al final si existe)
                if ' - ' in t: 
                    t = t.rsplit(' - ', 1)[0]
                
                l = e.get('link', '')
                u = resolver_redireccion_google(l)
                
                if not u: 
                    continue
                
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                
                n.append({
                    'titulo': limpiar_texto_mejorado(t), 
                    'descripcion': limpiar_texto_mejorado(d), 
                    'url': u, 
                    'imagen': None, 
                    'fuente': 'Google News', 
                    'fecha': e.get('published'), 
                    'puntaje': calcular_puntaje(t, d)
                })
        except: 
            continue
    
    log(f"Google News: {len(n)} noticias", 'info')
    return n

# ============================================================================
# PROCESAMIENTO DE IMÁGENES Y PUBLICACIÓN (similares a originales)
# ============================================================================

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
                if src and src.startswith('http') and 'google' not in src.lower() and 'logo' not in src.lower():
                    return src
        
        return None
        
    except: 
        return None

def descargar_imagen(url):
    if not url: 
        return None
    
    for b in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon', 'favicon']:
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
        if w/h > 4 or w/h < 0.2: 
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
        l = texto.split('\n')
        tc = ""
        for ln in l:
            if len(tc + ln + "\n") < 1600: 
                tc += ln + "\n"
            else: 
                break
        m = f"{tc.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    
    m = re.sub(r'https?://\S+', '', m)
    
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
# FUNCIÓN PRINCIPAL CON MEJORAS
# ============================================================================

def recolectar_noticias_todas_fuentes():
    todas_noticias = []
    estadisticas_fuentes = {}
    
    fuentes = [
        ('NewsAPI', obtener_newsapi, NEWS_API_KEY),
        # Añadir aquí las demás fuentes...
        ('Google News', obtener_google_news, True),
    ]
    
    for nombre, funcion, tiene_credencial in fuentes:
        if not tiene_credencial:
            estadisticas_fuentes[nombre] = 0
            continue
            
        try:
            noticias = funcion()
            count = len(noticias)
            estadisticas_fuentes[nombre] = count
            if count > 0:
                todas_noticias.extend(noticias)
                log(f"✅ {nombre}: {count} noticias añadidas", 'exito')
            else:
                log(f"⚠️ {nombre}: Sin noticias", 'advertencia')
        except Exception as e:
            log(f"❌ {nombre}: Error - {e}", 'error')
            estadisticas_fuentes[nombre] = 0
    
    log(f"\n📊 RESUMEN FUENTES:", 'info')
    for fuente, count in estadisticas_fuentes.items():
        status = "✅" if count > 0 else "❌"
        log(f"   {status} {fuente}: {count} noticias", 'info')
    log(f"📰 TOTAL: {len(todas_noticias)} noticias de todas las fuentes\n", 'info')
    
    return todas_noticias

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V4.2 (CORREGIDO - LIMPIEZA MEJORADA)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    h = cargar_historial()
    log(f"📊 Historial: {len(h.get('urls', []))} URLs previas")
    
    n = recolectar_noticias_todas_fuentes()
    
    if not n:
        log("ERROR CRÍTICO: Ninguna fuente devolvió noticias", 'error')
        return False
    
    # Deduplicación
    urls_vistas = set()
    titulos_vistos = {}
    n_unicas = []
    
    for nt in n:
        url_n = normalizar_url_v3(nt.get('url', ''))
        if url_n in urls_vistas:
            continue
            
        duplicado_temp = False
        for t_existente in titulos_vistos.keys():
            if calcular_similitud_titulos(nt.get('titulo', ''), t_existente) > 0.8:
                duplicado_temp = True
                break
        
        if duplicado_temp:
            continue
            
        urls_vistas.add(url_n)
        titulos_vistos[nt.get('titulo', '')] = url_n
        n_unicas.append(nt)
    
    n = n_unicas
    log(f"📰 Únicas tras deduplicación: {len(n)} noticias")
    
    # Ordenar por puntaje
    n.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    
    # Buscar noticia válida
    sel = None
    cont = None
    cred = None
    
    for i, nt in enumerate(n[:50]):
        url = nt.get('url', '')
        t = nt.get('titulo', '')
        d = nt.get('descripcion', '')
        
        if not url or not t: 
            continue
        
        dup, rz = noticia_ya_publicada(h, url, t, d)
        if dup:
            log(f"   [{i+1}] ❌ Duplicada: {t[:50]}... ({rz})", 'debug')
            continue
        
        log(f"   [{i+1}] ✅ Candidata: {t[:50]}... (Puntaje: {nt.get('puntaje', 0)})")
        
        # USAR NUEVA FUNCIÓN MEJORADA
        cont, cred = extraer_contenido_mejorado(url, d)
        
        if cont and len(cont) >= 150:
            # Validar que el contenido no sea incoherente
            if not detectar_texto_incoherente(cont):
                sel = nt
                break
            else:
                log(f"   ⚠️ Contenido descartado por incoherencia", 'advertencia')
        elif d and len(d) >= 100:
            cont = limpiar_texto_mejorado(d)
            if not detectar_texto_incoherente(cont):
                sel = nt
                break
    
    if not sel:
        log("ERROR: No hay noticias válidas nuevas", 'error')
        return False
    
    # Construir y publicar
    pub = construir_publicacion(sel['titulo'], cont, cred, sel['fuente'])
    ht = generar_hashtags(sel['titulo'], cont)
    
    log("🖼️  Procesando imagen...")
    img_path = None
    
    if sel.get('imagen') and 'Google' not in sel.get('fuente', ''):
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
        h = guardar_historial(h, sel['url'], sel['titulo'], sel.get('descripcion', '') + ' ' + cont[:400])
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
