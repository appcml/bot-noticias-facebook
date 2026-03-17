#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V4.5 (VERIFICACIÓN PREVIA ANTES DE PUBLICAR)
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

FUENTES_MEDIOS = [
    'cnn', 'bbc', 'fox news', 'msnbc', 'abc news', 'cbs news', 'nbc news', 
    'reuters', 'associated press', 'ap news', 'bloomberg', 'the guardian', 
    'the new york times', 'new york times', 'the washington post', 'washington post',
    'los angeles times', 'la times', 'el país', 'el mundo', 'el diario', 
    'univision', 'telemundo', 'caracol', 'rcn', 'clarín', 'infobae', 
    'cnn en español', 'cnn español', 'el nuevo día', 'el nuevo dia', 
    'la nación', 'la nacion', 'financial times', 'the wall street journal', 
    'wall street journal', 'al jazeera', 'rt', 'russia today', 'france 24', 
    'deutsche welle', 'dw', 'china daily', 'xinhua', 'tass', 'agenzia nova', 
    'ansa', 'efe', ' Europa Press', 'meneame', 'meneame.net'
]

# Patrones de truncamiento/corte
PATRONES_CORTE = [
    r'…$',           # Termina con ellipsis
    r'\.\.\.$',      # Termina con tres puntos
    r'\.\s*\.\s*\.$', # Puntos separados por espacios al final
    r'\s+de…$',      # "de..." al final (cortado)
    r'\s+de\.\.\.$', # "de..." al final variante
    r'\s+a…$',       # "a..." al final
    r'\s+en…$',      # "en..." al final
    r'\s+que…$',     # "que..." al final
    r'\s+con…$',     # "con..." al final
    r'\s+por…$',     # "por..." al final
    r'\s+para…$',    # "para..." al final
    r'\s+un…$',      # "un..." al final
    r'\s+una…$',     # "una..." al final
    r'\s+los…$',     # "los..." al final
    r'\s+las…$',     # "las..." al final
    r'\s+del…$',     # "del..." al final
    r'\s+al…$',      # "al..." al final
    r'[a-záéíóúñ]\…$', # Termina con letra minúscula + ellipsis (palabra cortada)
    r'[a-záéíóúñ]\.\.\.$', # Termina con letra minúscula + puntos (palabra cortada)
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
# SISTEMA DE VERIFICACIÓN PREVIA ANTES DE PUBLICAR
# ============================================================================

def verificar_contenido_completo(texto, titulo=""):
    """
    Verifica que el contenido esté completo y no tenga cortes/truncamientos.
    Retorna: (es_valido, problema_detectado, texto_corregido)
    """
    if not texto:
        return False, "texto_vacio", ""
    
    problemas = []
    texto_corregido = texto
    
    # Verificación 1: Detectar puntos suspensivos al final de párrafos (indica corte)
    parrafos = [p.strip() for p in texto.split('\n\n') if p.strip()]
    
    parrafos_con_corte = 0
    for i, parrafo in enumerate(parrafos):
        # Verificar si termina con patrón de corte
        for patron in PATRONES_CORTE:
            if re.search(patron, parrafo):
                parrafos_con_corte += 1
                # Intentar reparar: eliminar el corte y buscar punto final anterior
                if parrafo.endswith('…') or parrafo.endswith('...'):
                    # Buscar si hay un punto antes para cerrar la oración
                    ultimo_punto = max(parrafo.rfind('.'), parrafo.rfind('!'), parrafo.rfind('?'))
                    if ultimo_punto > len(parrafo) * 0.5:  # Si hay punto antes del 50%
                        texto_corregido = texto_corregido.replace(parrafo, parrafo[:ultimo_punto+1])
                        parrafos[i] = parrafo[:ultimo_punto+1]
                break
    
    if parrafos_con_corte > 0:
        problemas.append(f"{parrafos_con_corte} párrafos con cortes detectados")
    
    # Verificación 2: Detectar palabras partidas (patrones como "expert os")
    # Buscar palabras de 2-3 letras que parezcan fragmentos
    palabras_sueltas = re.findall(r'\b\w{1,3}\b', texto)
    palabras_comunes_cortas = {'el', 'la', 'de', 'y', 'en', 'un', 'al', 'del', 'con', 'por', 'que', 'los', 'las', 'una', 'su', 'se', 'me', 'te', 'lo', 'le', 'ya', 'no', 'si', 'es', 'as', 'os', 'ha', 'he', 'mi', 'tu', 'yo'}
    
    palabras_raras = [p for p in palabras_sueltas if p.lower() not in palabras_comunes_cortas and len(p) <= 2]
    if len(palabras_raras) > 3:
        problemas.append(f"Posibles palabras partidas: {palabras_raras[:3]}")
    
    # Verificación 3: Verificar que el último párrafo termine en punto (oración completa)
    if parrafos:
        ultimo = parrafos[-1]
        if not re.search(r'[.!?]$', ultimo):
            # Intentar arreglar: buscar el último punto válido
            ultimo_punto = max(ultimo.rfind('.'), ultimo.rfind('!'), ultimo.rfind('?'))
            if ultimo_punto > len(ultimo) * 0.6:
                # Podemos cortar aquí y terminar el párrafo
                nuevo_ultimo = ultimo[:ultimo_punto+1]
                texto_corregido = texto_corregido.replace(ultimo, nuevo_ultimo)
                problemas.append("Último párrafo sin terminación, corregido")
            else:
                problemas.append("Último párrafo incompleto sin punto final claro")
    
    # Verificación 4: Detectar si es solo una descripción corta (menos de 2 párrafos sustanciales)
    parrafos_sustanciales = [p for p in parrafos if len(p.split()) > 20]
    if len(parrafos_sustanciales) < 2 and len(texto.split()) < 80:
        problemas.append("Contenido muy corto, posible descripción no artículo completo")
    
    # Verificación 5: Detectar múltiples fuentes mezcladas (indica agregador)
    fuentes_encontradas = []
    texto_lower = texto.lower()
    for fuente in FUENTES_MEDIOS:
        if fuente.lower() in texto_lower:
            fuentes_encontradas.append(fuente)
    
    if len(fuentes_encontradas) >= 4:
        problemas.append(f"Mezcla de {len(fuentes_encontradas)} fuentes diferentes")
    
    # Decisión final
    es_valido = len(problemas) <= 1  # Permitir 1 problema menor si se pudo corregir
    
    # Si hay problemas graves de corte, intentar reparación más agresiva
    if parrafos_con_corte > 0:
        # Reconstruir texto solo con párrafos completos
        parrafos_validos = []
        for parrafo in parrafos:
            # Solo incluir si no termina con corte o si podemos cerrarlo
            if not any(re.search(p, parrafo) for p in PATRONES_CORTE):
                parrafos_validos.append(parrafo)
            else:
                # Intentar cerrar el párrafo en el último punto válido
                ultimo_punto = max(parrafo.rfind('.'), parrafo.rfind('!'), parrafo.rfind('?'))
                if ultimo_punto > len(parrafo) * 0.5:
                    cerrado = parrafo[:ultimo_punto+1].strip()
                    if len(cerrado.split()) > 10:
                        parrafos_validos.append(cerrado)
        
        if len(parrafos_validos) >= 2:
            texto_corregido = '\n\n'.join(parrafos_validos)
            log(f"   🔧 Texto reconstruido con {len(parrafos_validos)} párrafos válidos", 'debug')
            es_valido = True
        else:
            es_valido = False
    
    problema_str = "; ".join(problemas) if problemas else "ninguno"
    return es_valido, problema_str, texto_corregido

def limpiar_texto_mejorado(texto):
    """
    Limpieza completa que preserva la estructura de párrafos.
    """
    if not texto: 
        return ""
    
    import html
    t = html.unescape(texto)
    
    # Preservar estructura de párrafos
    t = re.sub(r'<br\s*/?>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<p>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'</p>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<[^>]+>', ' ', t)
    
    # Eliminar URLs
    t = re.sub(r'https?://\S*', '', t)
    
    # Normalizar espacios pero preservar saltos de línea
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n+', '\n', t)
    
    # Separar palabras pegadas por cambio de caso (camelCase)
    patron = r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])'
    t = re.sub(patron, r'\1 \2', t)
    
    # Limpiar espacios al inicio/final de líneas
    lineas = [linea.strip() for linea in t.split('\n') if linea.strip()]
    t = '\n'.join(lineas)
    
    return t.strip()

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
# EXTRACCIÓN DE CONTENIDO CON VERIFICACIÓN
# ============================================================================

def extraer_contenido_verificado(url, descripcion_original="", max_intentos=3):
    """
    Extrae contenido y lo verifica antes de retornar.
    Si no pasa la verificación, intenta extraer de nuevo con estrategias diferentes.
    """
    if not url: 
        return None, None
    
    intento = 0
    while intento < max_intentos:
        intento += 1
        log(f"   🔍 Intento {intento}/{max_intentos}: {url[:50]}...", 'debug')
        
        contenido, cred = extraer_contenido_raw(url, descripcion_original, estrategia=intento)
        
        if not contenido:
            continue
        
        # VERIFICACIÓN PREVIA ANTES DE RETORNAR
        es_valido, problema, contenido_corregido = verificar_contenido_completo(contenido)
        
        if es_valido:
            log(f"   ✅ Verificación exitosa: {len(contenido_corregido.split())} palabras", 'exito')
            return contenido_corregido, cred
        else:
            log(f"   ⚠️ Verificación fallida: {problema}", 'advertencia')
            if contenido_corregido and len(contenido_corregido.split()) > 40:
                # Si tenemos una corrección aceptable, usarla
                log(f"   🔧 Usando versión corregida", 'debug')
                return contenido_corregido, cred + " (corregido)"
        
        # Si es Google News, intentar con URL alternativa
        if 'news.google.com' in url and intento == 1:
            url_resuelto = resolver_redireccion_google(url)
            if url_resuelto:
                url = url_resuelto
                log(f"   🔀 Intentando con URL resuelta: {url[:50]}...", 'debug')
    
    # Si todos los intentos fallaron, usar descripción expandida como último recurso
    if descripcion_original and len(descripcion_original) > 80:
        log("   ⚠️ Usando descripción expandida como último recurso", 'advertencia')
        desc_expandida = expandir_descripcion(descripcion_original)
        es_valido, problema, desc_corregida = verificar_contenido_completo(desc_expandida)
        if es_valido or len(desc_corregida.split()) > 30:
            return desc_corregida, "Resumen de la noticia"
    
    return None, None

def extraer_contenido_raw(url, descripcion_original="", estrategia=1):
    """
    Extracción básica sin verificación.
    Estrategia 1: Artículo y clases estándar
    Estrategia 2: Body completo con filtros estrictos
    Estrategia 3: Meta descripción y estructura alternativa
    """
    if not url:
        return None, None
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
        s = BeautifulSoup(r.content, 'html.parser')
        
        for e in s(['script','style','nav','header','footer','aside','form','button','iframe','noscript']): 
            e.decompose()
        
        contenido_parrafos = []
        
        if estrategia == 1:
            # Estrategia 1: Artículo y clases comunes
            art = s.find('article')
            if art:
                ps = art.find_all('p')
                for p in ps:
                    texto_p = p.get_text().strip()
                    if 60 < len(texto_p) < 600:
                        if not any(nav in texto_p.lower() for nav in ['cookie', 'términos', 'privacidad', 'suscribir']):
                            limpio = limpiar_texto_mejorado(texto_p)
                            if limpio and limpio not in contenido_parrafos:
                                contenido_parrafos.append(limpio)
            
            if len(contenido_parrafos) < 3:
                for clase in ['article-content', 'entry-content', 'post-content', 'content-body', 'story-body']:
                    div = s.find(['div', 'section'], class_=lambda x: x and clase in str(x).lower())
                    if div:
                        ps = div.find_all('p')
                        for p in ps:
                            texto_p = p.get_text().strip()
                            if 60 < len(texto_p) < 600:
                                limpio = limpiar_texto_mejorado(texto_p)
                                if limpio and limpio not in contenido_parrafos:
                                    contenido_parrafos.append(limpio)
                        if len(contenido_parrafos) >= 3:
                            break
        
        elif estrategia == 2:
            # Estrategia 2: Body con filtros estrictos
            body = s.find('body')
            if body:
                ps = body.find_all('p')
                for p in ps:
                    texto_p = p.get_text().strip()
                    # Filtros más estrictos para evitar menús y navegación
                    if 100 < len(texto_p) < 500:
                        if any(c in texto_p for c in ['.', ',', ';']) and len(texto_p.split()) > 15:
                            if not any(nav in texto_p.lower() for nav in ['cookie', 'suscribir', 'newsletter', 'compartir', 'facebook', 'twitter']):
                                limpio = limpiar_texto_mejorado(texto_p)
                                if limpio and limpio not in contenido_parrafos:
                                    contenido_parrafos.append(limpio)
        
        elif estrategia == 3:
            # Estrategia 3: Meta descripción + párrafos del header/hero
            meta_desc = s.find('meta', attrs={'name': 'description'}) or s.find('meta', property='og:description')
            if meta_desc:
                desc = meta_desc.get('content', '')
                if desc and len(desc) > 100:
                    contenido_parrafos.append(limpiar_texto_mejorado(desc))
            
            # Buscar párrafos destacados
            for clase in ['lead', 'summary', 'excerpt', 'subtitle', 'intro']:
                elem = s.find(['p', 'div', 'h2'], class_=lambda x: x and clase in str(x).lower())
                if elem:
                    texto = elem.get_text().strip()
                    if len(texto) > 80:
                        contenido_parrafos.append(limpiar_texto_mejorado(texto))
        
        # Unir párrafos
        if len(contenido_parrafos) >= 2:
            texto_completo = '\n\n'.join(contenido_parrafos[:8])
            return texto_completo, None
        
        return None, None
        
    except Exception as e:
        log(f"   Error en extracción: {str(e)[:80]}", 'error')
        return None, None

def expandir_descripcion(descripcion):
    """
    Convierte descripción en párrafos estructurados.
    """
    if not descripcion:
        return ""
    
    limpia = limpiar_texto_mejorado(descripcion)
    if not limpia:
        return ""
    
    # Si ya es larga, devolver formateada
    if len(limpia.split()) > 60:
        return limpia
    
    # Dividir en oraciones y crear párrafos
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', limpia) if len(o.strip()) > 20]
    
    if len(oraciones) <= 1:
        return limpia
    
    # Crear 2 párrafos balanceados
    mitad = len(oraciones) // 2
    parrafo1 = ' '.join(oraciones[:mitad])
    parrafo2 = ' '.join(oraciones[mitad:])
    
    return f"{parrafo1}\n\n{parrafo2}"

def dividir_en_parrafos_presentacion(texto):
    """
    Divide texto en párrafos para presentación final.
    """
    if not texto:
        return []
    
    # Si ya tiene doble salto, usarlo
    if '\n\n' in texto:
        return [p.strip() for p in texto.split('\n\n') if len(p.strip()) > 20][:6]
    
    # Si tiene saltos simples
    if '\n' in texto:
        pars = [p.strip() for p in texto.split('\n') if len(p.strip()) > 20]
        if len(pars) >= 2:
            return pars[:6]
    
    # Dividir por oraciones
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
    """
    Construye publicación final con párrafos completos.
    """
    t = limpiar_texto_mejorado(titulo)
    pars = dividir_en_parrafos_presentacion(contenido)
    
    if not pars:
        pars = [contenido[:700]] if contenido else []
    
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
# FUENTES DE NOTICIAS
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

# [Otras fuentes...]

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
# FUNCIÓN PRINCIPAL CON VERIFICACIÓN ESTRICTA
# ============================================================================

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V4.5 (VERIFICACIÓN PREVIA ANTES DE PUBLICAR)")
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
    
    # Buscar noticia válida con verificación previa
    sel = None
    cont = None
    cred = None
    
    for i, nt in enumerate(n[:25]):  # Aumentado a 25 intentos
        url = nt.get('url', '')
        t = nt.get('titulo', '')
        d = nt.get('descripcion', '')
        
        if not url or not t: 
            continue
        
        dup, rz = noticia_ya_publicada(h, url, t, d)
        if dup:
            log(f"   [{i+1}] ❌ Duplicada: {t[:50]}...", 'debug')
            continue
        
        log(f"   [{i+1}] ✅ Candidata: {t[:50]}...")
        
        # EXTRAER CON VERIFICACIÓN PREVIA (3 intentos automáticos)
        cont, cred = extraer_contenido_verificado(url, d, max_intentos=3)
        
        if cont and len(cont.split()) >= 30:
            # Verificación final antes de aceptar
            es_valido, problema, cont_corregido = verificar_contenido_completo(cont)
            
            if es_valido:
                sel = nt
                cont = cont_corregido  # Usar versión corregida si hubo mejoras
                log(f"   ✅ Contenido verificado: {len(cont.split())} palabras, {len(cont.split(chr(10)))} párrafos", 'exito')
                break
            else:
                log(f"   ❌ Falló verificación final: {problema}", 'error')
                # Continuar con siguiente noticia
        else:
            log(f"   ❌ Sin contenido suficiente ({len(cont.split()) if cont else 0} palabras)", 'error')
    
    if not sel:
        log("ERROR: No se encontró ninguna noticia que pase la verificación de calidad", 'error')
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
