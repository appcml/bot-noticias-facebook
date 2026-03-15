#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V3.3
"""

import requests
import feedparser
import re
import hashlib
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Comment
from difflib import SequenceMatcher

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')
TIEMPO_ENTRE_PUBLICACIONES = 60
VENTANA_DUPLICADOS_HORAS = 72
UMBRAL_SIMILITUD_TITULO = 0.70
MAX_TITULOS_HISTORIA = 150

BLACKLIST_TITULOS = [r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$']
FRASES_PROHIBIDAS = ['cookies', 'política de privacidad', 'suscríbete', 'newsletter', 'redes sociales']
PALABRAS_ALTA_PRIORIDAD = ["guerra hoy", "conflicto armado", "dictadura", "sanciones", "ucrania", "rusia", "gaza", "israel", "hamas", "iran", "china", "taiwan", "otan", "brics", "economia mundial", "inflacion", "crisis humanitaria", "refugiados", "derechos humanos", "protestas", "coup", "minerales estrategicos", "tierras raras", "drones", "inteligencia artificial guerra", "ciberataque", "zelensky", "netanyahu", "trump", "biden", "putin"]
PALABRAS_MEDIA_PRIORIDAD = ['economía', 'mercados', 'FMI', 'China', 'EEUU', 'Alemania', 'petroleo', 'gas']

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None: default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.loads(f.read().strip()) if f.read().strip() else default.copy()
        except: pass
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except: return False

def generar_hash(texto):
    if not texto: return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url_v2(url):
    if not url: return ""
    url = url.lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^(www\.|m\.|mobile\.)', '', url)
    url = re.sub(r'\?.*$', '', url)
    url = re.sub(r'#.*$', '', url)
    return url.rstrip('/')

def calcular_similitud_titulos(t1, t2):
    if not t1 or not t2: return 0.0
    def n(t): return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', t.lower().strip()))
    return SequenceMatcher(None, n(t1), n(t2)).ratio()

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
    d = {'urls': [], 'hashes': [], 'timestamps': [], 'titulos': [], 'descripciones': [], 'hashes_contenido': [], 'hashes_permanentes': [], 'estadisticas': {'total_publicadas': 0}}
    h = cargar_json(HISTORIAL_PATH, d)
    for k in d: 
        if k not in h: h[k] = d[k]
    return h

def noticia_ya_publicada(h, url, titulo, desc=""):
    if not h: return False, "sin_historial"
    url_n = normalizar_url_v2(url)
    hash_t = generar_hash(titulo)
    log(f"   🔍 Verificando duplicados:", 'debug')
    if es_titulo_generico(titulo): return True, "titulo_generico"
    for uh in h.get('urls', []):
        if not isinstance(uh, str): continue
        if url_n == normalizar_url_v2(uh): return True, "url_exacta"
    todos_h = list(dict.fromkeys(h.get('hashes', []) + h.get('hashes_permanentes', [])))
    if hash_t in todos_h: return True, "hash_titulo_exacto"
    max_sim = 0.0
    for th in h.get('titulos', []):
        if not isinstance(th, str): continue
        sim = calcular_similitud_titulos(titulo, th)
        max_sim = max(max_sim, sim)
        if sim >= UMBRAL_SIMILITUD_TITULO: return True, f"similitud_{sim:.2f}"
    log(f"   ✅ NUEVO: Max similitud {max_sim:.1%}", 'debug')
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc=""):
    for k in ['urls','hashes','timestamps','titulos','descripciones','hashes_contenido','hashes_permanentes','estadisticas']:
        if k not in h: h[k] = [] if k != 'estadisticas' else {'total_publicadas': 0}
    h['urls'].append(normalizar_url_v2(url))
    h['hashes'].append(generar_hash(titulo))
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1
    h['hashes_permanentes'].append(generar_hash(titulo))
    if len(h['hashes_permanentes']) > 300: h['hashes_permanentes'] = h['hashes_permanentes'][-300:]
    for k in ['urls','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA: h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    guardar_json(HISTORIAL_PATH, h)
    return h

def verificar_tiempo():
    e = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u: return True
    try:
        m = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if m < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {m:.0f} min", 'info')
            return False
    except: pass
    return True

def obtener_newsapi():
    if not NEWS_API_KEY: return []
    n = []
    for q in ['war Ukraine Russia Gaza Israel', 'Trump Biden Putin', 'economy inflation IMF', 'NATO UN EU']:
        try:
            r = requests.get('https://newsapi.org/v2/everything', params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es', 'sortBy': 'publishedAt', 'pageSize': 10}, timeout=15).json()
            if r.get('status') == 'ok':
                for a in r.get('articles', []):
                    t = a.get('title', '')
                    if t and '[Removed]' not in t:
                        d = a.get('description', '')
                        n.append({'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 'url': a.get('url', ''), 'imagen': a.get('urlToImage'), 'fuente': f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}", 'fecha': a.get('publishedAt'), 'puntaje': calcular_puntaje(t, d)})
        except: continue
    log(f"NewsAPI: {len(n)} noticias", 'info')
    return n

def obtener_newsdata():
    if not NEWSDATA_API_KEY: return []
    try:
        r = requests.get('https://newsdata.io/api/1/news', params={'apikey': NEWSDATA_API_KEY, 'language': 'es', 'category': 'world,politics', 'size': 30}, timeout=15).json()
        n = []
        if r.get('status') == 'success':
            for a in r.get('results', []):
                t = a.get('title', '')
                if t:
                    d = a.get('description', '')
                    n.append({'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 'url': a.get('link', ''), 'imagen': a.get('image_url'), 'fuente': f"NewsData:{a.get('source_id', 'Unknown')}", 'fecha': a.get('pubDate'), 'puntaje': calcular_puntaje(t, d)})
        log(f"NewsData: {len(n)} noticias", 'info')
        return n
    except: return []

def obtener_gnews():
    if not GNEWS_API_KEY: return []
    try:
        r = requests.get('https://gnews.io/api/v4/top-headlines', params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 20, 'topic': 'world'}, timeout=15).json()
        n = []
        for a in r.get('articles', []):
            t = a.get('title', '')
            if t:
                d = a.get('description', '')
                n.append({'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 'url': a.get('url', ''), 'imagen': a.get('image'), 'fuente': f"GNews:{a.get('source', {}).get('name', 'Unknown')}", 'fecha': a.get('publishedAt'), 'puntaje': calcular_puntaje(t, d)})
        log(f"GNews: {len(n)} noticias", 'info')
        return n
    except: return []

def resolver_redireccion_google(url):
    if not url or not url.startswith('https://news.google.com'): return url
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
        u = r.url
        if 'google.com' in u and '/sorry' in u: return None
        if u == url:
            u = requests.head(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True).url
        return re.sub(r'\?.*$', '', re.sub(r'#.*$', '', u))
    except: return None

def obtener_google_news():
    feeds = ['https://news.google.com/rss?hl=es&gl=US&ceid=US:es', 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es']
    n = []
    for f in feeds:
        try:
            feed = feedparser.parse(f, request_headers={'User-Agent': 'Mozilla/5.0'})
            if not feed or not feed.entries: continue
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t or '[Removed]' in t: continue
                if ' - ' in t: t = t.rsplit(' - ', 1)[0]
                l = e.get('link', '')
                u = resolver_redireccion_google(l)
                if not u: continue
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                n.append({'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 'url': u, 'imagen': None, 'fuente': 'Google News', 'fecha': e.get('published'), 'puntaje': calcular_puntaje(t, d)})
        except: continue
    log(f"Google News: {len(n)} noticias", 'info')
    return n

def obtener_rss_alternativos():
    feeds = ['http://feeds.bbci.co.uk/mundo/rss.xml', 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada', 'https://www.infobae.com/arc/outboundfeeds/rss/mundo/']
    n = []
    for f in feeds:
        try:
            r = requests.get(f, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200: continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries: continue
            fn = feed.feed.get('title', 'RSS')[:20]
            for e in feed.entries[:5]:
                t = e.get('title', '')
                if not t: continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l: continue
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                img = None
                if 'media_content' in e: img = e.media_content[0].get('url')
                elif 'links' in e:
                    for ld in e.links:
                        if ld.get('type', '').startswith('image/'): img = ld.get('href'); break
                n.append({'titulo': limpiar_texto(t), 'descripcion': limpiar_texto(d), 'url': l, 'imagen': img, 'fuente': f"RSS:{fn}", 'fecha': e.get('published'), 'puntaje': calcular_puntaje(t, d)})
        except: continue
    log(f"RSS Alternativos: {len(n)} noticias", 'info')
    return n

def extraer_imagen_web(url):
    if not url: return None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for m in ['og:image', 'twitter:image']:
            t = s.find('meta', property=m) or s.find('meta', attrs={'name': m})
            if t:
                i = t.get('content', '').strip()
                if i and i.startswith('http') and 'google' not in i.lower(): return i
        art = s.find('article') or s.find('main')
        if art:
            for img in art.find_all('img'):
                src = img.get('data-src') or img.get('src', '')
                if src and src.startswith('http') and 'google' not in src.lower() and 'logo' not in src.lower():
                    return src
        return None
    except: return None

def descargar_imagen(url):
    if not url: return None
    for b in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon', 'favicon']:
        if b in url.lower(): return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200: return None
        if 'image' not in r.headers.get('content-type', ''): return None
        img = Image.open(BytesIO(r.content))
        w, h = img.size
        if w < 400 or h < 300: return None
        if w/h > 4 or w/h < 0.2: return None
        if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
        img.thumbnail((1200, 1200))
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=85)
        if os.path.getsize(p) < 5000:
            os.remove(p)
            return None
        return p
    except: return None

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
    except: return None

def generar_hashtags(t, c):
    txt = f"{t} {c}".lower()
    h = ['#NoticiasInternacionales', '#ÚltimaHora']
    temas = {'guerra|conflicto|ataque': '#ConflictoArmado', 'ucrania|rusia|putin': '#UcraniaRusia', 'gaza|israel|hamas': '#IsraelGaza', 'trump|biden': '#PolíticaGlobal', 'economía|inflación': '#EconomíaMundial', 'china|taiwan': '#ChinaTaiwán'}
    for p, tag in temas.items():
        if re.search(p, txt): h.append(tag); break
    h.append('#Mundo')
    return ' '.join(h)

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN: return False
    m = f"{texto}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    if len(m) > 2000:
        l = texto.split('\n')
        tc = ""
        for ln in l:
            if len(tc + ln + "\n") < 1600: tc += ln + "\n"
            else: break
        m = f"{tc.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    m = re.sub(r'https?://\S+', '', m)
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            r = requests.post(url, files={'file': ('imagen.jpg', f, 'image/jpeg')}, data={'message': m, 'access_token': FB_ACCESS_TOKEN}, timeout=60).json()
        if 'id' in r:
            log(f"✅ Publicado ID: {r['id']}", 'exito')
            return True
    except: pass
    return False

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V3.3")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    h = cargar_historial()
    log(f"📊 Historial: {len(h.get('urls', []))} URLs")
    
    n = []
    if NEWS_API_KEY: n.extend(obtener_newsapi())
    if NEWSDATA_API_KEY and len(n) < 15: n.extend(obtener_newsdata())
    if GNEWS_API_KEY and len(n) < 20: n.extend(obtener_gnews())
    if len(n) < 25:
        gn = obtener_google_news()
        if gn: n.extend(gn)
    if len(n) < 10:
        log("⚠️ Intentando RSS alternativos...", 'advertencia')
        alt = obtener_rss_alternativos()
        if alt: n.extend(alt)
    
    log(f"📰 Total: {len(n)} noticias")
    
    if not n:
        log("ERROR: No se encontraron noticias", 'error')
        return False
    
    n.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    
    sel = None
    cont = None
    cred = None
    
    for i, nt in enumerate(n):
        url = nt.get('url', '')
        t = nt.get('titulo', '')
        d = nt.get('descripcion', '')
        
        if not url or not t: continue
        
        log(f"   [{i+1}] Probando: {t[:50]}...", 'debug')
        
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
        
        if cont:
            log(f"   ✅ Contenido: {len(cont)} chars", 'exito')
            sel = nt
            break
        else:
            log("   ⚠️ Sin contenido, usando descripción", 'advertencia')
            cont = d
            if len(cont) >= 100:
                log(f"   ✅ Descripción: {len(cont)} chars", 'exito')
                sel = nt
                break
            else:
                log(f"   ❌ Descripción corta ({len(cont)}), siguiente...", 'advertencia')
                h = guardar_historial(h, url, t, d)
                continue
    
    if not sel:
        log("ERROR: No hay noticias válidas", 'error')
        return False
    
    pub = construir_publicacion(sel['titulo'], cont, cred, sel['fuente'])
    ht = generar_hashtags(sel['titulo'], cont)
    
    log("🖼️  Procesando imagen...")
    img_path = None
    
    if sel.get('imagen') and 'Google' not in sel.get('fuente', ''):
        img_path = descargar_imagen(sel['imagen'])
    
    if not img_path:
        iu = extraer_imagen_web(sel['url'])
        if iu: img_path = descargar_imagen(iu)
    
    if not img_path:
        img_path = crear_imagen_titulo(sel['titulo'])
    
    if not img_path:
        log("ERROR: Sin imagen", 'error')
        return False
    
    ok = publicar_facebook(sel['titulo'], pub, img_path, ht)
    
    try:
        if os.path.exists(img_path): os.remove(img_path)
    except: pass
    
    if ok:
        guardar_historial(h, sel['url'], sel['titulo'], sel.get('descripcion', '') + ' ' + cont[:400])
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log(f"✅ ÉXITO - Total: {cargar_historial().get('estadisticas', {}).get('total_publicadas', 0)} noticias", 'exito')
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
