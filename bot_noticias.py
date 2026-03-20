#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V3.7 (SIN GOOGLE NEWS)
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
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')
TIEMPO_ENTRE_PUBLICACIONES = 60
UMBRAL_SIMILITUD_TITULO = 0.75
UMBRAL_SIMILITUD_CONTENIDO = 0.65
MAX_TITULOS_HISTORIA = 150

BLACKLIST_TITULOS = [r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$']
PALABRAS_ALTA_PRIORIDAD = ["guerra", "guerra hoy", "conflicto armado", "invasion", "ofensiva militar",
"bombardeo", "misiles", "ataque aereo", "drones militares",
"movilizacion militar", "tropas", "escalada de tension",
"amenaza nuclear", "armas nucleares", "guerra nuclear",
"ciber guerra", "guerra hibrida", "intervencion militar",
"terrorismo", "atentado", "ataque terrorista""ucrania", "rusia", "israel", "gaza", "iran",
"china", "taiwan", "corea del norte",
"otan", "nato", "brics",
"medio oriente", "europa del este",
"siria", "yemen", "sudan",
"india pakistan""crisis humanitaria", "refugiados", "desplazados",
"victimas civiles", "bajas militares",
"destruccion", "infraestructura destruida",
"crisis energetica", "escasez alimentos",
"sanciones", "sanciones economicas",
"bloqueo economico", "impacto economico guerra",
"derechos humanos violaciones""crisis de gobierno", "caida de gobierno",
"dictadura", "golpe de estado", "coup",
"protestas", "disturbios", "estado de emergencia",
"ruptura diplomatica", "tensiones politicas",
"negociaciones de paz", "alto el fuego",
"sanciones internacionales""economia mundial", "inflacion", "crisis economica",
"recesion", "mercados en caida",
"petroleo", "gas", "crisis energetica",
"bloqueo financiero", "crisis alimentaria",
"subida de precios", "impacto economico global""ciberataque", "hackeo", "guerra cibernetica",
"inteligencia artificial guerra",
"drones", "armas autonomas",
"espionaje digital", "vigilancia",
"satelites militares", "deepfake""ultima hora", "urgente", "en desarrollo",
"breaking news", "latest",
"hoy", "ahora", "alerta"# 🇷🇺 Rusia / Ucrania
"putin", "vladimir putin",
"zelensky", "volodymyr zelensky",
"sergei shoigu", "lavrov",

# 🇺🇸 Estados Unidos
"biden", "joe biden",
"trump", "donald trump",
"kamala harris",
"antony blinken",
"lloyd austin",

# 🇮🇱 Israel
"netanyahu", "benjamin netanyahu",
"yoav gallant",
"herzi halevi",

# 🇮🇷 Irán
"khamenei", "ali khamenei",
"ebrahim raisi",
"iran lider supremo",

# 🇨🇳 China
"xi jinping",
"li qiang",
"china presidente",

# 🇰🇵 Corea del Norte
"kim jong un",

# 🇪🇺 Europa
"macron", "emmanuel macron",
"olaf scholz",
"ursula von der leyen",
"charles michel",

# 🇬🇧 Reino Unido
"rishi sunak",

# 🇮🇳 India
"narendra modi",

# 🇧🇷 Brasil
"lula", "lula da silva",
"bolsonaro",

# 🇦🇷 Argentina
"milei", "javier milei",

# 🇲🇽 México
"amlo", "lopez obrador",

# 🌍 OTAN / Internacional
"nato secretary general",
"jens stoltenberg",

# 🪖 MILITAR / SEGURIDAD
"general", "comandante militar",
"jefe del ejercito",
"ministro de defensa",

# 🧨 GRUPOS Y ACTORES NO ESTATALES
"hamas", "hezbollah",
"isis", "estado islamico",
"taliban",
"huties", "houthis",

# 💰 EMPRESARIOS INFLUYENTES (TECNOLOGÍA / GUERRA INDIRECTA)
"elon musk",
"jeff bezos",
"mark zuckerberg",]
PALABRAS_MEDIA_PRIORIDAD = ["economia", "mercados", "FMI", "banco mundial",
"china economia", "eeuu economia", "alemania economia",
"comercio internacional", "empresas",
"tecnologia", "innovacion",
"salud", "educacion",
"medio ambiente", "cambio climatico"]

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
    """
    V3: Normalización más agresiva para detectar URLs duplicadas
    """
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

def limpiar_texto(texto):
    if not texto: return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    t = t.strip()
    if t and t[-1] not in '.!?': t += '.'
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

def extraer_contenido(url):
    if not url: return None, None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        for e in s(['script','style','nav','header','footer']): e.decompose()
        art = s.find('article')
        if art:
            ps = art.find_all('p')
            if len(ps) >= 3:
                txt = ' '.join([limpiar_texto(p.get_text()) for p in ps if len(p.get_text()) > 40])
                if len(txt) > 300: return txt[:2000], None
        for c in ['article-content','entry-content','post-content']:
            e = s.find(class_=lambda x: x and c in x.lower())
            if e:
                ps = e.find_all('p')
                if len(ps) >= 2:
                    txt = ' '.join([limpiar_texto(p.get_text()) for p in ps if len(p.get_text()) > 40])
                    if len(txt) > 300: return txt[:2000], None
        return None, None
    except: return None, None

def dividir_parrafos(texto):
    if not texto: return []
    ors = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    if len(ors) < 3: return [texto] if len(texto) > 100 else []
    pars, actual, palabras = [], [], 0
    for i, o in enumerate(ors):
        actual.append(o)
        palabras += len(o.split())
        if palabras >= 40 or i == len(ors)-1:
            if len(' '.join(actual).split()) >= 15:
                pars.append(' '.join(actual))
            actual, palabras = [], 0
    return pars[:8]

def construir_publicacion(titulo, contenido, creditos, fuente):
    t = limpiar_texto(titulo)
    pars = dividir_parrafos(contenido)
    if len(pars) < 2:
        ors = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        pars = [' '.join(ors[i:i+2]) for i in range(0, len(ors), 2)][:8]
    lineas = [f"📰 ÚLTIMA HORA | {t}", ""]
    for i, p in enumerate(pars):
        lineas.append(p)
        if i < len(pars)-1: lineas.append("")
    lineas.extend(["", "──────────────────────────────", ""])
    if creditos: lineas.extend([f"✍️ {creditos}", ""])
    lineas.append(f"📎 {fuente}")
    return '\n'.join(lineas)

def cargar_historial():
    d = {
        'urls': [], 
        'urls_normalizadas': [],
        'hashes': [], 
        'timestamps': [], 
        'titulos': [], 
        'descripciones': [], 
        'hashes_contenido': [], 
        'hashes_permanentes': [],
        'estadisticas': {'total_publicadas': 0}
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
    if not h: return False, "sin_historial"

    url_n = normalizar_url_v3(url)
    hash_t = generar_hash(titulo)
    hash_d = generar_hash(desc) if desc else ""
    dominio = extraer_dominio_principal(url)

    log(f"   🔍 Verificando duplicados:", 'debug')
    log(f"      URL norm: {url_n[:80]}...", 'debug')
    log(f"      Dominio: {dominio}", 'debug')
    log(f"      Hash titulo: {hash_t[:16]}...", 'debug')

    if es_titulo_generico(titulo): 
        log(f"      ❌ Título genérico detectado", 'debug')
        return True, "titulo_generico"

    for uh in h.get('urls_normalizadas', []):
        if not isinstance(uh, str): 
            continue
        if url_n == uh: 
            log(f"      ❌ URL normalizada duplicada", 'debug')
            return True, "url_normalizada_exacta"

    for i, uh in enumerate(h.get('urls', [])):
        if not isinstance(uh, str):
            continue
        if extraer_dominio_principal(uh) == dominio:
            titulo_h = h.get('titulos', [])[i] if i < len(h.get('titulos', [])) else ""
            if titulo_h:
                sim = calcular_similitud_titulos(titulo, titulo_h)
                if sim >= 0.85:
                    log(f"      ❌ Misma noticia en {dominio} (sim {sim:.1%})", 'debug')
                    return True, f"misma_noticia_sitio_{sim:.2f}"

    todos_h = list(dict.fromkeys(h.get('hashes', []) + h.get('hashes_permanentes', [])))
    if hash_t in todos_h: 
        log(f"      ❌ Hash título duplicado", 'debug')
        return True, "hash_titulo_exacto"

    if hash_d and hash_d in h.get('hashes_contenido', []):
        log(f"      ❌ Hash contenido duplicado", 'debug')
        return True, "hash_contenido_exacto"

    max_sim = 0.0
    titulo_cercano = ""
    for th in h.get('titulos', []):
        if not isinstance(th, str): 
            continue
        sim = calcular_similitud_titulos(titulo, th)
        if sim > max_sim:
            max_sim = sim
            titulo_cercano = th[:50]
        if sim >= UMBRAL_SIMILITUD_TITULO: 
            log(f"      ❌ Similitud título {sim:.1%} con: {th[:50]}...", 'debug')
            return True, f"similitud_titulo_{sim:.2f}"

    if desc:
        for dh in h.get('descripciones', []):
            if not isinstance(dh, str) or not dh:
                continue
            sim_cont = calcular_similitud_contenido(desc, dh, 150)
            if sim_cont >= UMBRAL_SIMILITUD_CONTENIDO:
                log(f"      ❌ Similitud contenido {sim_cont:.1%} con noticia anterior", 'debug')
                return True, f"similitud_contenido_{sim_cont:.2f}"

    log(f"   ✅ NUEVO: Max similitud título {max_sim:.1%}", 'debug')
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

    if guardar_json(HISTORIAL_PATH, h):
        log(f"💾 Historial guardado: {len(h['urls'])} URLs totales", 'exito')
    else:
        log(f"❌ Error guardando historial", 'error')

    return h

def verificar_tiempo():
    e = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u: 
        return True
    try:
        m = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if m < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {m:.0f} min", 'info')
            return False
    except: 
        pass
    return True

def obtener_newsapi():
    if not NEWS_API_KEY: 
        return []
    n = []
    queries = [
        'Ukraine war Russia Putin Zelensky',
        'Israel Gaza Hamas Iran conflict',
        'China Taiwan US tensions',
        'Trump Biden US politics',
        'economy inflation recession',
        'NATO EU Europe',
        'India Pakistan Asia',
        'climate change COP',
        'cyberattack hacking',
        'coup dictatorship sanctions'
        # 🪖 GUERRAS Y CONFLICTOS
"guerra", "conflicto armado", "invasion", "ofensiva militar", "ataque aereo",
"bombardeo", "misiles", "drones militares", "tropas", "despliegue militar",
"movilizacion", "escalada de tension", "crisis internacional", "combate",
"guerra urbana", "guerra naval", "guerra aerea", "inteligencia militar",
"espionaje", "ciber guerra", "guerra hibrida", "amenaza nuclear",
"armas nucleares", "disuasion nuclear", "alianza militar", "OTAN",
"bases militares", "ejercicios militares", "defensa aerea", "sistema antimisiles",
"conflicto prolongado", "intervencion extranjera", "guerra proxy",
"insurgencia", "milicias", "paramilitares", "terrorismo", "atentado",
"ataque terrorista", "extremismo", "seguridad internacional",

# 🌍 REGIONES CLAVE
"ucrania rusia", "israel gaza", "israel iran", "medio oriente conflicto",
"china taiwan", "corea del norte misiles", "siria guerra", "yemen conflicto",
"sudan guerra", "africa conflicto armado", "india pakistan frontera",
"mar de china meridional", "europa del este tension", "balcanes conflicto",
"caucaso guerra",

# 💥 CONSECUENCIAS
"crisis humanitaria", "refugiados", "desplazados", "escasez alimentos",
"crisis energetica", "crisis combustible", "impacto economico guerra",
"sanciones economicas", "bloqueo comercial", "inflacion guerra",
"destruccion infraestructura", "victimas civiles", "bajas militares",
"hospital colapsado", "ayuda internacional", "misiones de paz",
"reconstruccion", "derechos humanos violaciones",

# 🏛️ POLÍTICA
"decisiones presidenciales", "estado de emergencia", "ruptura diplomatica",
"tensiones politicas", "sanciones internacionales", "cumbre internacional",
"negociaciones de paz", "alto el fuego", "acuerdo militar",
"crisis de gobierno", "caida de gobierno", "protestas", "disturbios",
"golpe de estado", "regimen autoritario", "intervencion extranjera",

# 💰 ECONOMÍA
"inflacion global", "crisis economica", "recesion", "mercados en caida",
"bolsa desplome", "precio del petroleo", "crisis energetica europa",
"escasez de gas", "bloqueo financiero", "comercio internacional crisis",
"cadenas de suministro", "crisis alimentaria", "subida de precios",
"desempleo", "impacto economico global",

# 🚨 SEGURIDAD
"crimen organizado", "narcotrafico", "cartel drogas", "operativo policial",
"red criminal", "trafico de armas", "violencia urbana", "homicidio",
"secuestro", "ataque armado", "explosion", "investigacion policial",
"juicio", "condena", "seguridad nacional",

# 💻 TECNOLOGÍA
"inteligencia artificial", "ciberataque", "hackeo", "guerra cibernetica",
"espionaje digital", "vigilancia masiva", "tecnologia militar",
"armas autonomas", "deepfake", "desinformacion", "satelites militares",

# 🦠 SALUD
"crisis sanitaria", "hospitales colapsados", "emergencia medica",
"pandemia", "brote enfermedad", "escasez medicamentos",
"salud mental crisis", "ayuda medica internacional",

# 🌪️ DESASTRES
"terremoto", "tsunami", "huracan", "inundaciones", "incendios forestales",
"desastre natural", "emergencia climatica", "evacuacion", "victimas desastre",

# ⚡ TRIGGERS (MUY IMPORTANTES)
"ultima hora", "urgente", "en desarrollo", "breaking news",
"latest update", "live", "hoy", "ahora", "alerta", "noticia mundial"
    ]
    for q in queries:
        try:
            r = requests.get('https://newsapi.org/v2/everything', 
                           params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es', 
                                  'sortBy': 'publishedAt', 'pageSize': 5}, 
                           timeout=15).json()
            if r.get('status') == 'ok':
                for a in r.get('articles', []):
                    t = a.get('title', '')
                    if t and '[Removed]' not in t:
                        d = a.get('description', '')
                        n.append({
                            'titulo': limpiar_texto(t), 
                            'descripcion': limpiar_texto(d), 
                            'url': a.get('url', ''), 
                            'imagen': a.get('urlToImage'), 
                            'fuente': f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}", 
                            'fecha': a.get('publishedAt'), 
                            'puntaje': calcular_puntaje(t, d)
                        })
        except: 
            continue
    log(f"NewsAPI: {len(n)} noticias", 'info')
    return n

def obtener_newsdata():
    if not NEWSDATA_API_KEY: 
        return []
    try:
        categorias = ['world', 'politics', 'business', 'technology']
        n = []
        for cat in categorias:
            r = requests.get('https://newsdata.io/api/1/news', 
                            params={'apikey': NEWSDATA_API_KEY, 'language': 'es', 
                                   'category': cat, 'size': 10}, 
                            timeout=15).json()
            if r.get('status') == 'success':
                for a in r.get('results', []):
                    t = a.get('title', '')
                    if t:
                        d = a.get('description', '')
                        n.append({
                            'titulo': limpiar_texto(t), 
                            'descripcion': limpiar_texto(d), 
                            'url': a.get('link', ''), 
                            'imagen': a.get('image_url'), 
                            'fuente': f"NewsData:{a.get('source_id', 'Unknown')}", 
                            'fecha': a.get('pubDate'), 
                            'puntaje': calcular_puntaje(t, d)
                        })
        log(f"NewsData: {len(n)} noticias", 'info')
        return n
    except: 
        return []

def obtener_gnews():
    if not GNEWS_API_KEY: 
        return []
    try:
        topicos = ['world', 'nation', 'business', 'technology']
        n = []
        for topic in topicos:
            r = requests.get('https://gnews.io/api/v4/top-headlines', 
                            params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 10, 'topic': topic}, 
                            timeout=15).json()
            for a in r.get('articles', []):
                t = a.get('title', '')
                if t:
                    d = a.get('description', '')
                    n.append({
                        'titulo': limpiar_texto(t), 
                        'descripcion': limpiar_texto(d), 
                        'url': a.get('url', ''), 
                        'imagen': a.get('image'), 
                        'fuente': f"GNews:{a.get('source', {}).get('name', 'Unknown')}", 
                        'fecha': a.get('publishedAt'), 
                        'puntaje': calcular_puntaje(t, d)
                    })
        log(f"GNews: {len(n)} noticias", 'info')
        return n
    except: 
        return []

definición obtener_rss_alternativos():
    fuentes = [
        'http://feeds.bbci.co.uk/mundo/rss.xml',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
        'https://www.infobae.com/arc/outboundfeeds/rss/mundo/',
        'https://feeds.reuters.com/reuters/hotnews',
        'https://feeds.france24.com/es/',
        'https://www.efe.com/efe/espana/1/rss',
    ]
    n = []
    for f in feeds:
        try:
            r = requests.get(f, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200: 
                continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries: 
                continue
            fn = feed.feed.get('title', 'RSS')[:20]
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t: 
                    continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l: 
                    continue
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                img = None
                if 'media_content' in e: 
                    img = e.media_content[0].get('url')
                elif 'links' in e:
                    for ld in e.links:
                        if ld.get('type', '').startswith('image/'): 
                            img = ld.get('href')
                            break
                n.append({
                    'titulo': limpiar_texto(t), 
                    'descripcion': limpiar_texto(d), 
                    'url': l, 
                    'imagen': img, 
                    'fuente': f"RSS:{fn}", 
                    'fecha': e.get('published'), 
                    'puntaje': calcular_puntaje(t, d)
                })
        except: 
            continue
    log(f"RSS Alternativos: {len(n)} noticias", 'info')
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

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V3.7 (SIN GOOGLE NEWS)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False

    if not verificar_tiempo():
        return False

    h = cargar_historial()
    log(f"📊 Historial cargado: {len(h.get('urls', []))} URLs, {len(h.get('urls_normalizadas', []))} URLs normalizadas")

    n = []
    if NEWS_API_KEY: 
        n.extend(obtener_newsapi())
    if NEWSDATA_API_KEY and len(n) < 20: 
        n.extend(obtener_newsdata())
    if GNEWS_API_KEY and len(n) < 30: 
        n.extend(obtener_gnews())
    # GOOGLE NEWS ELIMINADO - Solo se usan RSS alternativos si faltan noticias
    if len(n) < 15:
        log("⚠️ Intentando RSS alternativos...", 'advertencia')
        alt = obtener_rss_alternativos()
        if alt: 
            n.extend(alt)

    # Deduplicación fuerte antes de procesar
    urls_vistas = set()
    titulos_vistos = {}
    n_unicas = []

    for nt in n:
        url_n = normalizar_url_v3(nt.get('url', ''))
        titulo_norm = re.sub(r'[^\w]', '', nt.get('titulo', '').lower())

        if url_n in urls_vistas:
            continue

        duplicado_temp = False
        for t_existente, url_existente in titulos_vistos.items():
            if calcular_similitud_titulos(nt.get('titulo', ''), t_existente) > 0.8:
                log(f"   ⚠️ Duplicado temporal detectado: {nt.get('titulo', '')[:50]}...", 'debug')
                duplicado_temp = True
                break

        if duplicado_temp:
            continue

        urls_vistas.add(url_n)
        titulos_vistos[nt.get('titulo', '')] = url_n
        n_unicas.append(nt)

    n = n_unicas

    log(f"📰 Total únicas: {len(n)} noticias (después de deduplicar fuentes)")

    if not n:
        log("ERROR: No se encontraron noticias", 'error')
        return False

    n.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)

    sel = None
    cont = None
    cred = None
    intentos = 0
    max_intentos = 50

    for i, nt in enumerate(n):
        if intentos >= max_intentos:
            log(f"⚠️ Máximo de intentos alcanzado ({max_intentos})", 'advertencia')
            break

        url = nt.get('url', '')
        t = nt.get('titulo', '')
        d = nt.get('descripcion', '')

        if not url or not t: 
            continue

        intentos += 1
        log(f"   [{i+1}] Probando: {t[:50]}...", 'debug')

        if intentos % 10 == 0:
            h = cargar_historial()
            log(f"   🔄 Historial recargado: {len(h.get('urls', []))} URLs", 'debug')

        dup, rz = noticia_ya_publicada(h, url, t, d)
        if dup:
            log(f"      ❌ {rz}", 'debug')
            continue

        if nt.get('puntaje', 0) < 3:
            log(f"      ❌ Puntaje bajo ({nt.get('puntaje', 0)})", 'debug')
            continue

        log(f"      ✅ Aceptada", 'debug')
        log(f"\n📝 NOTICIA: {t[:60]}...")
        log(f"   Fuente: {nt['fuente']} | Puntaje: {nt.get('puntaje', 0)}")

        cont, cred = extraer_contenido(url)

        if cont and len(cont) >= 200:
            log(f"   ✅ Contenido: {len(cont)} chars", 'exito')
            sel = nt
            break
        else:
            log("   ⚠️ Sin contenido suficiente, probando descripción...", 'advertencia')
            cont = d
            if len(cont) >= 150:
                log(f"   ✅ Descripción: {len(cont)} chars", 'exito')
                sel = nt
                break
            else:
                log(f"   ❌ Descripción corta ({len(cont)}), siguiente...", 'advertencia')
                continue

    if not sel:
        log("ERROR: No hay noticias válidas después de revisar todas", 'error')
        return False

    pub = construir_publicacion(sel['titulo'], cont, cred, sel['fuente'])
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
        h = guardar_historial(h, sel['url'], sel['titulo'], sel.get('descripcion', '') + ' ' + cont[:400])
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log(f"✅ ÉXITO - Total histórico: {h.get('estadisticas', {}).get('total_publicadas', 0)} noticias publicadas", 'exito')
        return True
    else:
        log("❌ Publicación fallida, NO se guarda en historial", 'error')
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
