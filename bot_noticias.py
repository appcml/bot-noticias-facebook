#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - V4.0 (MEJORADO)
Versión mejorada con sistema avanzado de detección de duplicados
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

# CONFIGURACIÓN DE DUPLICADOS (MEJORADA)
TIEMPO_ENTRE_PUBLICACIONES = 30  # Cambiado a 30 minutos como solicitaste
VENTANA_DUPLICADOS_DIAS = 5  # Mantener historial por 5 días (más corto para permitir republished)
UMBRAL_SIMILITUD_TITULO = 0.65  # Un poco más estricto
UMBRAL_SIMILITUD_CONTENIDO = 0.50  # Nuevo: similitud de contenido
MAX_TITULOS_HISTORIA = 200
MAX_TITULOS_POR_CATEGORIA = 15  # NUEVO: Máximo por categoría en ventana reciente
VENTANA_CATEGORIA_HORAS = 48  # NUEVO: Ventana de tiempo por categoría

# Blacklist y filtros
BLACKLIST_TITULOS = [r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$',
                     r'^\s*breaking\s*$', r'^\s*developing story\s*$']
FRASES_PROHIBIDAS = ['cookies', 'política de privacidad', 'suscríbete', 'newsletter',
                     'redes sociales', 'publicidad', 'suscripción', 'email', 'newsletter']
PALABRAS_ALTA_PRIORIDAD = ["guerra", "conflicto armado", "dictadura", "sanciones", "ucrania",
                          "rusia", "gaza", "israel", "hamas", "iran", "china", "taiwan",
                          "otan", "brics", "economia mundial", "inflacion", "crisis humanitaria",
                          "refugiados", "derechos humanos", "protestas", "coup", "minerales",
                          "tierras raras", "drones", "inteligencia artificial", "ciberataque",
                          "zelensky", "netanyahu", "trump", "biden", "putin", "terrorismo",
                          "atentado", "explosión", "muerte", "fallece", "asesinato"]
PALABRAS_MEDIA_PRIORIDAD = ['economía', 'mercados', 'FMI', 'China', 'EEUU', 'Alemania',
                           'petroleo', 'gas', 'bolsa', 'acciones', 'divisas', 'banco central']

# NUEVO: Categorías para clasificación de noticias
CATEGORIAS = {
    'conflicto': ['guerra', 'conflicto', 'ataque', 'bombardeo', 'combate', 'militar', 'ejercito'],
    'ucrania': ['ucrania', 'rusia', 'putin', 'kiev', 'moscú', 'zelensky'],
    'medio_oriente': ['gaza', 'israel', 'hamas', 'netanyahu', 'palestina', 'iran', 'libano', 'hezbollah'],
    'eeuu': ['estados unidos', 'eeuu', 'trump', 'biden', 'congreso', 'washington', 'casa blanca'],
    'china': ['china', 'chino', 'taiwan', 'pekin', 'xi jinping'],
    'europa': ['europa', 'ue', 'union europea', 'francia', 'alemania', 'reino unido', 'brexit'],
    'economia': ['economía', 'inflacion', 'recesion', 'mercado', 'bolsa', 'dolar', 'euro', 'bcr'],
    'energia': ['petroleo', 'gas', 'energia', 'opep', 'petroleo', 'gnl'],
    'tecnologia': ['tecnologia', 'inteligencia artificial', 'ia', 'tech', 'silicon valley', 'chip'],
    'clima': ['clima', 'calentamiento', 'inundacion', 'terremoto', 'huracan', 'tornado']
}

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
    """Genera hash MD5 normalizado del texto"""
    if not texto: return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def generar_hash_contenido(texto, longitud=500):
    """NUEVO: Genera hash de los primeros N caracteres del contenido"""
    if not texto: return ""
    contenido = texto[:longitud].lower().strip()
    contenido = re.sub(r'\s+', ' ', contenido)
    return hashlib.md5(contenido.encode()).hexdigest()

def normalizar_url_v2(url):
    """Normaliza URL para comparación"""
    if not url: return ""
    url = url.lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^(www\.|m\.|mobile\.)', '', url)
    url = re.sub(r'\?.*$', '', url)
    url = re.sub(r'#.*$', '', url)
    return url.rstrip('/')

def calcular_similitud_titulos(t1, t2):
    """Calcula similitud entre dos títulos"""
    if not t1 or not t2: return 0.0
    def n(t): return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', t.lower().strip()))
    return SequenceMatcher(None, n(t1), n(t2)).ratio()

def calcular_similitud_contenido(c1, c2):
    """NUEVO: Calcula similitud entre contenidos usando n-grams"""
    if not c1 or not c2: return 0.0
    # Tomar primeros 300 caracteres para comparación rápida
    c1 = c1[:300].lower()
    c2 = c2[:300].lower()
    # Crear conjuntos de bigrams
    def get_bigrams(s):
        s = re.sub(r'[^\w\s]', '', s)
        return set(s[i:i+2] for i in range(len(s)-1))
    bg1 = get_bigrams(c1)
    bg2 = get_bigrams(c2)
    if not bg1 or not bg2: return 0.0
   -intersection = len(bg1 & bg2)
    union = len(bg1 | bg2)
    return intersection / union if union > 0 else 0.0

def es_titulo_generico(titulo):
    """Detecta títulos genéricos que deben evitarse"""
    if not titulo: return True
    tl = titulo.lower().strip()
    for p in BLACKLIST_TITULOS:
        if re.match(p, tl): return True
    stop = {'el','la','de','y','en','the','of','to','hoy','que','es','por','con'}
    pal = [p for p in re.findall(r'\b\w+\b', tl) if p not in stop and len(p)>3]
    return len(set(pal)) < 4

def contiene_frase_prohibida(texto):
    """NUEVO: Verifica si el texto contiene frases prohibidas"""
    if not texto: return False
    texto_lower = texto.lower()
    for frase in FRASES_PROHIBIDAS:
        if frase.lower() in texto_lower:
            return True
    return False

def clasificar_categoria(titulo, descripcion=""):
    """NUEVO: Clasifica la noticia en categorías"""
    texto = f"{titulo} {descripcion}".lower()
    categorias_encontradas = []

    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if palabra in texto:
                if categoria not in categorias_encontradas:
                    categorias_encontradas.append(categoria)
                break

    return categorias_encontradas if categorias_encontradas else ['otros']

def limpiar_texto(texto):
    """Limpia texto HTML y caracteres especiales"""
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
    """Calcula puntaje de prioridad de la noticia"""
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
    # NUEVO: Bonus por categorías de alta prioridad
    cats = clasificar_categoria(titulo, desc)
    if 'conflicto' in cats: p += 5
    if 'ucrania' in cats or 'medio_oriente' in cats: p += 4
    return p

def extraer_contenido(url):
    """Extrae contenido principal de la URL"""
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
    """Divide el contenido en párrafos apropiados para Facebook"""
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
    """Construye el formato de publicación para Facebook"""
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
    """Carga el historial de publicaciones"""
    d = {
        'urls': [],
        'hashes': [],
        'timestamps': [],
        'titulos': [],
        'descripciones': [],
        'hashes_contenido': [],
        'hashes_permanentes': [],
        'categorias': [],  # NUEVO: Guardar categorías
        'contenidos_primeros_parrafos': [],  # NUEVO: Hash de primeros párrafos
        'temas_recientes': {},  # NUEVO: Temas recientes por categoría
        'estadisticas': {'total_publicadas': 0}
    }
    h = cargar_json(HISTORIAL_PATH, d)
    for k in d:
        if k not in h: h[k] = d[k]

    # Limpiar entradas antiguas
    limpiar_historial_antiguo(h)
    return h

def limpiar_historial_antiguo(h):
    """Elimina entradas antiguas y mantiene el historial limpio"""
    try:
        ahora = datetime.now()
        indices_a_mantener = []

        for i, ts in enumerate(h.get('timestamps', [])):
            try:
                fecha = datetime.fromisoformat(ts)
                if (ahora - fecha).days < VENTANA_DUPLICADOS_DIAS:
                    indices_a_mantener.append(i)
            except:
                continue

        # Reconstruir listas manteniendo solo índices válidos
        for key in ['urls', 'hashes', 'timestamps', 'titulos', 'descripciones',
                    'hashes_contenido', 'categorias', 'contenidos_primeros_parrafos']:
            if key in h and isinstance(h[key], list):
                h[key] = [h[key][i] for i in indices_a_mantener if i < len(h[key])]

        # Limitar hashes_permanentes
        if len(h.get('hashes_permanentes', [])) > 150:
            h['hashes_permanentes'] = h['hashes_permanentes'][-150:]

        # Limpiar temas_recientes obsoletos
        if 'temas_recientes' in h:
            temas_a_borrar = []
            for tema, ultima_fecha in h['temas_recientes'].items():
                try:
                    fecha = datetime.fromisoformat(ultima_fecha)
                    if (ahora - fecha).hours > VENTANA_CATEGORIA_HORAS:
                        temas_a_borrar.append(tema)
                except:
                    temas_a_borrar.append(tema)
            for tema in temas_a_borrar:
                del h['temas_recientes'][tema]

    except Exception as e:
        log(f"Error limpiando historial: {e}", 'error')

def verificar_tema_reciente(h, categorias):
    """NUEVO: Verifica si alguna categoría ya fue publicada recientemente"""
    ahora = datetime.now().isoformat()
    temas_recientes = h.get('temas_recientes', {})

    for cat in categorias:
        if cat in temas_recientes:
            try:
                ultima_fecha = datetime.fromisoformat(temas_recientes[cat])
                horas_diff = (datetime.now() - ultima_fecha).total_seconds() / 3600
                if horas_diff < VENTANA_CATEGORIA_HORAS:
                    log(f"   ⚠️ Categoría '{cat}' publicada hace {horas_diff:.1f}h", 'debug')
                    return True, cat
            except:
                pass
    return False, None

def noticia_ya_publicada(h, url, titulo, desc="", contenido=""):
    """Función mejorada de verificación de duplicados"""
    if not h: return False, "sin_historial"

    url_n = normalizar_url_v2(url)
    hash_t = generar_hash(titulo)
    hash_d = generar_hash(desc) if desc else ""
    hash_cont = generar_hash_contenido(contenido) if contenido else ""
    categorias = clasificar_categoria(titulo, desc)

    log(f"   🔍 Verificando duplicados para:", 'debug')
    log(f"      Título: {titulo[:50]}...", 'debug')
    log(f"      Categorías: {categorias}", 'debug')

    # 1. Verificar si es título genérico
    if es_titulo_generico(titulo):
        log(f"      ❌ Título genérico detectado", 'debug')
        return True, "titulo_generico"

    # 2. Verificar frases prohibidas
    if contiene_frase_prohibida(titulo) or contiene_frase_prohibida(desc):
        log(f"      ❌ Contiene frase prohibida", 'debug')
        return True, "frase_prohibida"

    # 3. Verificar URL exacta
    for uh in h.get('urls', []):
        if not isinstance(uh, str):
            continue
        if url_n == normalizar_url_v2(uh):
            log(f"      ❌ URL duplicada", 'debug')
            return True, "url_exacta"

    # 4. Verificar hash de título exacto
    todos_h = list(dict.fromkeys(h.get('hashes', []) + h.get('hashes_permanentes', [])))
    if hash_t in todos_h:
        log(f"      ❌ Hash título duplicado", 'debug')
        return True, "hash_titulo_exacto"

    # 5. Verificar hash de contenido
    if hash_cont and hash_cont in h.get('contenidos_primeros_parrafos', []):
        log(f"      ❌ Contenido (primeros chars) duplicado", 'debug')
        return True, "hash_contenido_exacto"

    # 6. Verificar similitud de títulos
    max_sim_titulo = 0.0
    titulo_cercano = ""
    for th in h.get('titulos', []):
        if not isinstance(th, str):
            continue
        sim = calcular_similitud_titulos(titulo, th)
        if sim > max_sim_titulo:
            max_sim_titulo = sim
            titulo_cercano = th[:50]
        if sim >= UMBRAL_SIMILITUD_TITULO:
            log(f"      ❌ Similitud título {sim:.1%} con: {th[:40]}...", 'debug')
            return True, f"similitud_titulo_{sim:.2f}"

    # 7. NUEVO: Verificar similitud de contenido si hay contenido
    if contenido and len(contenido) > 100:
        max_sim_cont = 0.0
        for cont_prev in h.get('contenidos_primeros_parrafos', [])[:50]:  # Solo últimos 50
            if cont_prev and len(cont_prev) > 10:
                # Nota: aquí comparamos hashes, no contenidos completos
                # Pero podemos usar los títulos como proxy
                pass

        # Verificación alternativa: si el contenido empieza igual
        contenido_inicio = contenido[:200].lower().strip()
        for desc_prev in h.get('descripciones', [])[:30]:
            if desc_prev and len(desc_prev) > 50:
                if contenido_inicio.startswith(desc_prev[:100].lower().strip()):
                    log(f"      ❌ Contenido muy similar al anterior", 'debug')
                    return True, "contenido_similar"

    # 8. NUEVO: Verificar tema/categoría reciente
    tema_reciente, cat_reciente = verificar_tema_reciente(h, categorias)
    if tema_reciente:
        # Solo rechazamos si además tiene baja prioridad
        puntaje = calcular_puntaje(titulo, desc)
        if puntaje < 8:  # Requiere puntaje alto para publicar tema reciente
            log(f"      ❌ Tema '{cat_reciente}' publicado recientemente (baja prioridad)", 'debug')
            return True, f"tema_reciente_{cat_reciente}"
        else:
            log(f"      ⚠️ Tema '{cat_reciente}' reciente pero alta prioridad - PERMITIDO", 'debug')

    # 9. NUEVO: Contar publicaciones por categoría en ventana reciente
    for cat in categorias:
        count = sum(1 for c in h.get('categorias', []) if cat in c)
        if count >= MAX_TITULOS_POR_CATEGORIA:
            log(f"      ❌ Demasiadas publicaciones de '{cat}' ({count}/{MAX_TITULOS_POR_CATEGORIA})", 'debug')
            return True, f"categoria_saturada_{cat}"

    log(f"   ✅ NUEVO: Similitud máx título {max_sim_titulo:.1%}", 'debug')
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc="", contenido="", categorias=None):
    """Guarda la noticia en historial SOLO después de publicar exitosamente"""
    for k in ['urls','hashes','timestamps','titulos','descripciones','hashes_contenido',
              'hashes_permanentes','categorias','contenidos_primeros_parrafos','temas_recientes','estadisticas']:
        if k not in h:
            if k == 'temas_recientes':
                h[k] = {}
            elif k == 'estadisticas':
                h[k] = {'total_publicadas': 0}
            else:
                h[k] = []

    # Verificar duplicado antes de guardar
    url_n = normalizar_url_v2(url)
    hash_t = generar_hash(titulo)

    for uh in h.get('urls', []):
        if isinstance(uh, str) and normalizar_url_v2(uh) == url_n:
            log(f"⚠️ Intento de duplicado detectado en guardar_historial", 'advertencia')
            return h

    # Agregar datos
    h['urls'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['contenidos_primeros_parrafos'].append(generar_hash_contenido(contenido) if contenido else "")
    h['categorias'].append(categorias if categorias else ['otros'])
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1
    h['hashes_permanentes'].append(hash_t)

    # Actualizar temas recientes
    ahora = datetime.now().isoformat()
    if categorias:
        for cat in categorias:
            h['temas_recientes'][cat] = ahora

    # Limitar tamaño
    if len(h['hashes_permanentes']) > 150:
        h['hashes_permanentes'] = h['hashes_permanentes'][-150:]

    for k in ['urls','hashes','timestamps','titulos','descripciones','hashes_contenido',
              'categorias','contenidos_primeros_parrafos']:
        if len(h[k]) > MAX_TITULOS_HISTORIA:
            h[k] = h[k][-MAX_TITULOS_HISTORIA:]

    if guardar_json(HISTORIAL_PATH, h):
        log(f"💾 Historial guardado: {len(h['urls'])} URLs, {len(h['temas_recientes'])} temas activos", 'exito')
    else:
        log(f"❌ Error guardando historial", 'error')

    return h

def verificar_tiempo():
    """Verifica si ha pasado suficiente tiempo desde la última publicación"""
    e = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u:
        return True
    try:
        m = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if m < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última publicación hace {m:.0f} min (mínimo: {TIEMPO_ENTRE_PUBLICACIONES} min)", 'info')
            return False
    except:
        pass
    return True

def obtener_newsapi():
    """Obtiene noticias de NewsAPI"""
    if not NEWS_API_KEY:
        return []
    n = []
    for q in ['war Ukraine Russia Gaza Israel', 'Trump Biden Putin', 'economy inflation IMF', 'NATO UN EU',
              'China Taiwan', 'Iran nuclear', 'climate change']:
        try:
            r = requests.get('https://newsapi.org/v2/everything',
                           params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es',
                                  'sortBy': 'publishedAt', 'pageSize': 10},
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
    """Obtiene noticias de NewsData.io"""
    if not NEWSDATA_API_KEY:
        return []
    try:
        r = requests.get('https://newsdata.io/api/1/news',
                        params={'apikey': NEWSDATA_API_KEY, 'language': 'es',
                               'category': 'world,politics', 'size': 30},
                        timeout=15).json()
        n = []
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
    """Obtiene noticias de GNews"""
    if not GNEWS_API_KEY:
        return []
    try:
        r = requests.get('https://gnews.io/api/v4/top-headlines',
                        params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 20, 'topic': 'world'},
                        timeout=15).json()
        n = []
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

def resolver_redireccion_google(url):
    """Resuelve redirecciones de Google News"""
    if not url or not url.startswith('https://news.google.com'):
        return url
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
        u = r.url
        if 'google.com' in u and '/sorry' in u:
            return None
        if u == url:
            u = requests.head(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True).url
        return re.sub(r'\?.*$', '', re.sub(r'#.*$', '', u))
    except:
        return None

def obtener_google_news():
    """Obtiene noticias de Google News RSS"""
    feeds = [
        'https://news.google.com/rss?hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es'
    ]
    n = []
    for f in feeds:
        try:
            feed = feedparser.parse(f, request_headers={'User-Agent': 'Mozilla/5.0'})
            if not feed or not feed.entries:
                continue
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t or '[Removed]' in t:
                    continue
                if ' - ' in t:
                    t = t.rsplit(' - ', 1)[0]
                l = e.get('link', '')
                u = resolver_redireccion_google(l)
                if not u:
                    continue
                d = e.get('summary', '') or e.get('description', '')
                d = re.sub(r'<[^>]+>', '', d)
                n.append({
                    'titulo': limpiar_texto(t),
                    'descripcion': limpiar_texto(d),
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

def obtener_rss_alternativos():
    """Obtiene noticias de fuentes RSS alternativas"""
    feeds = [
        'http://feeds.bbci.co.uk/mundo/rss.xml',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
        'https://www.infobae.com/arc/outboundfeeds/rss/mundo/'
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
            for e in feed.entries[:5]:
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
    """Extrae imagen de la página web"""
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
    """Descarga y procesa imagen para Facebook"""
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
    """Crea imagen con el título si no hay imagen disponible"""
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

def generar_hashtags(titulo, contenido):
    """Genera hashtags relevantes para la noticia"""
    txt = f"{titulo} {contenido}".lower()
    h = ['#NoticiasInternacionales', '#ÚltimaHora']
    temas = {
        'guerra|conflicto|ataque|bombardeo': '#ConflictoArmado',
        'ucrania|rusia|putin|kiev': '#UcraniaRusia',
        'gaza|israel|hamas|palestina': '#IsraelGaza',
        'iran|nuclear|revolucion': '#Irán',
        'trump|biden|congreso': '#PolíticaEUA',
        'china|taiwan|pekin': '#ChinaTaiwán',
        'economía|inflacion|bolsa|mercado': '#EconomíaMundial',
        'tecnologia|inteligencia artificial|chip': '#Tecnología',
        'clima|calentamiento|inundacion': '#CambioClimático'
    }
    for p, tag in temas.items():
        if re.search(p, txt):
            h.append(tag)
    h.append('#Mundo')
    return ' '.join(h)

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook"""
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
            log(f"✅Publicado en Facebook - ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook: {r.get('error', {}).get('message', 'Unknown')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando: {e}", 'error')
    return False

def main():
    """Función principal del bot"""
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS - V4.0 (MEJORADO)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ Intervalo: {TIEMPO_ENTRE_PUBLICACIONES} minutos")
    print("="*60)

    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False

    if not verificar_tiempo():
        return False

    # Cargar historial fresco
    h = cargar_historial()
    log(f"📊 Historial: {len(h.get('urls', []))} URLs, {len(h.get('temas_recientes', {}))} temas activos")

    # Obtener noticias de múltiples fuentes
    n = []
    if NEWS_API_KEY:
        n.extend(obtener_newsapi())
    if NEWSDATA_API_KEY and len(n) < 15:
        n.extend(obtener_newsdata())
    if GNEWS_API_KEY and len(n) < 20:
        n.extend(obtener_gnews())
    if len(n) < 25:
        gn = obtener_google_news()
        if gn:
            n.extend(gn)
    if len(n) < 10:
        log("⚠️ Usando fuentes RSS alternativas...", 'advertencia')
        alt = obtener_rss_alternativos()
        if alt:
            n.extend(alt)

    # Eliminar duplicados de la lista antes de procesar
    urls_vistas = set()
    n_unicas = []
    for nt in n:
        url_n = normalizar_url_v2(nt.get('url', ''))
        if url_n and url_n not in urls_vistas:
            urls_vistas.add(url_n)
            n_unicas.append(nt)
    n = n_unicas

    log(f"📰 Total únicas: {len(n)} noticias")

    if not n:
        log("ERROR: No se encontraron noticias", 'error')
        return False

    # Ordenar por puntaje
    n.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)

    # Buscar noticia válida para publicar
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
        log(f"   [{intentos}] Verificando: {t[:45]}...", 'debug')

        # Recargar historial periódicamente
        if intentos % 10 == 0:
            h = cargar_historial()

        # Extraer contenido para verificación mejorada
        contenido_temp, _ = extraer_contenido(url)

        dup, rz = noticia_ya_publicada(h, url, t, d, contenido_temp or "")
        if dup:
            log(f"      ❌ {rz}", 'debug')
            continue

        if nt.get('puntaje', 0) < 3:
            log(f"      ❌ Puntaje bajo ({nt.get('puntaje', 0)})", 'debug')
            continue

        log(f"      ✅ Aceptada - Categorías: {clasificar_categoria(t, d)}", 'debug')
        log(f"\n📝 NOTICIA SELECCIONADA:")
        log(f"   Título: {t[:60]}...")
        log(f"   Fuente: {nt['fuente']} | Puntaje: {nt.get('puntaje', 0)}")

        cont, cred = extraer_contenido(url)

        if cont and len(cont) >= 200:
            log(f"   ✅ Contenido extraído: {len(cont)} chars", 'exito')
            sel = nt
            break
        else:
            log(f"   ⚠️ Sin contenido, usando descripción ({len(d)} chars)", 'advertencia')
            cont = d
            if len(cont) >= 150:
                log(f"   ✅ Descripción aceptable", 'exito')
                sel = nt
                break
            else:
                log(f"   ❌ Contenido insuficiente, continuando...", 'debug')
                continue

    if not sel:
        log("ERROR: No hay noticias válidas después de revisar todas", 'error')
        return False

    # Construir publicación
    pub = construir_publicacion(sel['titulo'], cont, cred, sel['fuente'])
    ht = generar_hashtags(sel['titulo'], cont)
    categorias = clasificar_categoria(sel['titulo'], sel.get('descripcion', ''))

    # Procesar imagen
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
        log("ERROR: No se pudo obtener imagen", 'error')
        return False

    # Publicar en Facebook
    log("📤 Publicando en Facebook...")
    ok = publicar_facebook(sel['titulo'], pub, img_path, ht)

    # Limpiar imagen temporal
    try:
        if os.path.exists(img_path):
            os.remove(img_path)
    except:
        pass

    if ok:
        # Guardar en historial SOLO si la publicación fue exitosa
        h = guardar_historial(h, sel['url'], sel['titulo'],
                             sel.get('descripcion', '') + ' ' + cont[:400],
                             cont, categorias)
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log(f"✅ ÉXITO - Total publicado: {h.get('estadisticas', {}).get('total_publicadas', 0)}", 'exito')
        log(f"   Categorías activadas: {categorias}", 'info')
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
