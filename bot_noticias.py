#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias - V20.0.0
CAMBIOS VS V19:
  - TODO va a BORRADOR (sin publicacion directa automatica)
  - Enfoque 100% EVERGREEN
  - Rotacion equitativa por paises
  - Prioridad por calidad e interes del tema
  - Pinterest manejado por bot_pinterest_diferido.py (sin duplicar logica)
  - Categorias expandidas: misterios, historia, geopolitica, innovacion
"""
VERSION_BOT = "V20.0.0"

import requests, feedparser, re, hashlib, json, os, random, time, unicodedata
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse

MAX_BORRADORES_DIA = 3
MAX_POSTS_WP_DIA   = MAX_BORRADORES_DIA
ROTACION_PAISES_PATH = 'estado_rotacion_paises.json'

POOL_PAISES = {
    'chile':          {'peso': 10, 'region': 'latinoamerica'},
    'argentina':      {'peso': 9,  'region': 'latinoamerica'},
    'mexico':         {'peso': 9,  'region': 'latinoamerica'},
    'colombia':       {'peso': 7,  'region': 'latinoamerica'},
    'brasil':         {'peso': 7,  'region': 'latinoamerica'},
    'venezuela':      {'peso': 6,  'region': 'latinoamerica'},
    'peru':           {'peso': 5,  'region': 'latinoamerica'},
    'ecuador':        {'peso': 4,  'region': 'latinoamerica'},
    'bolivia':        {'peso': 3,  'region': 'latinoamerica'},
    'uruguay':        {'peso': 3,  'region': 'latinoamerica'},
    'estados_unidos': {'peso': 8,  'region': 'mundo'},
    'europa':         {'peso': 7,  'region': 'mundo'},
    'asia':           {'peso': 6,  'region': 'mundo'},
    'global':         {'peso': 8,  'region': 'mundo'},
}

CATEGORIAS_EVERGREEN = {
    'tecnologia':     {'slug': 'tecnologia',     'cpm': 1.45, 'evergreen': True},
    'ciencia':        {'slug': 'ciencia-y-salud', 'cpm': 1.40, 'evergreen': True},
    'salud':          {'slug': 'ciencia-y-salud', 'cpm': 1.40, 'evergreen': True},
    'historia':       {'slug': 'mundo',           'cpm': 1.20, 'evergreen': True},
    'misterios':      {'slug': 'mundo',           'cpm': 1.25, 'evergreen': True},
    'geopolitica':    {'slug': 'mundo',           'cpm': 1.15, 'evergreen': True},
    'economia':       {'slug': 'economia',        'cpm': 1.55, 'evergreen': True},
    'politica':       {'slug': 'politica',        'cpm': 1.10, 'evergreen': True},
    'medio_ambiente': {'slug': 'medio-ambiente',  'cpm': 1.28, 'evergreen': True},
    'innovacion':     {'slug': 'tecnologia',      'cpm': 1.45, 'evergreen': True},
    'cultura':        {'slug': 'entretenimiento', 'cpm': 1.20, 'evergreen': True},
    'entretenimiento':{'slug': 'entretenimiento', 'cpm': 1.20, 'evergreen': True},
    'deportes':       {'slug': 'deportes',        'cpm': 1.25, 'evergreen': True},
    'latinoamerica':  {'slug': 'latinoamerica',   'cpm': 1.18, 'evergreen': True},
    'mundo':          {'slug': 'mundo',           'cpm': 1.00, 'evergreen': True},
    'guerra':         {'slug': 'internacional',   'cpm': 0.90, 'evergreen': False},
    'crimen':         {'slug': 'internacional',   'cpm': 0.85, 'evergreen': False},
    'desastre':       {'slug': 'internacional',   'cpm': 0.95, 'evergreen': False},
    'general':        {'slug': 'mundo',           'cpm': 1.00, 'evergreen': True},
}

TABLEROS_PINTEREST = {
    'tecnologia':     'tecnologia',
    'innovacion':     'tecnologia',
    'ciencia':        'noticias-del-mundo',
    'salud':          'noticias-del-mundo',
    'historia':       'noticias-del-mundo',
    'misterios':      'noticias-del-mundo',
    'geopolitica':    'noticias-del-mundo',
    'economia':       'economia',
    'politica':       'politica',
    'medio_ambiente': 'noticias-del-mundo',
    'cultura':        'noticias-del-mundo',
    'entretenimiento':'noticias-del-mundo',
    'deportes':       'deportes',
    'latinoamerica':  'latinoamerica',
    'mundo':          'noticias-del-mundo',
    'general':        'noticias-del-mundo',
}

TEMAS_ALTA_RELEVANCIA = [
    'inteligencia artificial','nasa','espacio','descubrimiento cientifico',
    'fisica cuantica','genetica','cambio climatico','energia renovable',
    'civilizacion perdida','arqueologia','historia antigua','misterio historico',
    'mayas','incas','aztecas','egipto antiguo','manuscrito','artefacto inexplicable',
    'robot','quantum','deepfake','neuralink','elon musk','openai','biotecnologia',
    'cancer tratamiento','vacuna','longevidad','medicina del futuro','alzheimer',
    'brics','geopolitica','litio','cobre','recursos naturales','acuerdo comercial',
    'inflacion','criptomoneda','bitcoin','fintech','economia mundial',
    'oscar','grammy','netflix','cultura pop','anime','cine latinoamericano',
]

NEWS_API_KEY       = os.getenv('NEWS_API_KEY','')
NEWSDATA_API_KEY   = os.getenv('NEWSDATA_API_KEY','')
GNEWS_API_KEY      = os.getenv('GNEWS_API_KEY','')
WP_URL             = os.getenv('WP_URL','https://verdadhoy.com')
WP_USER            = os.getenv('WP_USER','verdadhoy_admin')
WP_APP_PASSWORD    = os.getenv('WP_APP_PASSWORD','')
PINTEREST_TOKEN    = os.getenv('PINTEREST_TOKEN','')
GROQ_API_KEY       = os.getenv('GROQ_API_KEY','')
GEMINI_API_KEY     = os.getenv('GEMINI_API_KEY','')
TAVILY_API_KEY     = os.getenv('TAVILY_API_KEY','')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY','')
OPENAI_API_KEY     = os.getenv('OPENAI_API_KEY','')

HISTORIAL_PATH  = os.getenv('HISTORIAL_PATH','historial_publicaciones.json')
ESTADO_WP_PATH  = 'estado_wp.json'
CUOTAS_PATH     = 'estado_cuotas.json'

REINTENTAR_CALIDAD_IA      = True
UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 300
DIAS_HISTORIAL             = 14

PALABRAS_TRANSICION = [
    'sin embargo','ademas','por otro lado','en consecuencia','a su vez',
    'no obstante','por ejemplo','en primer lugar','finalmente','asimismo',
    'por lo tanto','en efecto','de hecho','en este sentido','como resultado',
    'en cambio','cabe destacar','mientras tanto','aunque','pese a',
    'de esta manera','dado que','ya que','en definitiva',
]

POWER_WORDS_ES = {
    'clave','crucial','decisivo','decisiva','historico','historica',
    'alerta','record','oficial','confirmado','confirmada','sorprendente',
    'revolucionario','revolucionaria','impactante','revelador','reveladora',
    'inedito','inedita','definitivo','esencial','critico','critica',
    'extraordinario','unico','unica','real','secreto','secretos',
    'radical','masivo','masiva','sin precedentes','millones',
}

POWER_WORDS_LISTA = list(POWER_WORDS_ES)

STOPWORDS_SLUG = {
    'de','del','la','las','el','los','un','una','unos','unas',
    'y','e','o','u','a','al','en','por','para','con','sin',
    'que','se','su','sus','es','son','ha','han','fue','era',
    'lo','le','les','me','te','nos','ante','bajo','desde',
    'hacia','hasta','sobre','tras','entre','como','pero','si','no','ni',
}

SINONIMOS_KEYWORD = {
    'tecnologia':    ['la empresa','el sistema','la plataforma','el servicio','la herramienta'],
    'economia':      ['el mercado','la situacion','el contexto','el escenario','la medida'],
    'politica':      ['la situacion','el proceso','la decision','el hecho','la coyuntura'],
    'deportes':      ['el evento','la competencia','el encuentro','el partido','la jornada'],
    'salud':         ['la condicion','el fenomeno','el caso','la situacion','el problema'],
    'ciencia':       ['el descubrimiento','el fenomeno','el hallazgo','el avance','el estudio'],
    'historia':      ['el periodo','la epoca','el evento','el hecho','el hallazgo'],
    'misterios':     ['el fenomeno','el caso','el hallazgo','el enigma','el evento'],
    'geopolitica':   ['la situacion','el contexto','el escenario','el conflicto','la crisis'],
    'innovacion':    ['el avance','el desarrollo','la solucion','el proyecto','la propuesta'],
    'cultura':       ['el evento','el lanzamiento','la propuesta','el trabajo','la obra'],
    'medio_ambiente':['el fenomeno','la situacion','el problema','el impacto','el escenario'],
    'general':       ['el tema','la situacion','el asunto','el caso','el hecho'],
}

TRANSICIONES_INYECTABLES = [
    'Sin embargo, vale destacar que ',
    'Ademas, es importante señalar que ',
    'Por otro lado, cabe mencionar que ',
    'En consecuencia, ',
    'De hecho, ',
    'Asimismo, ',
    'Por lo tanto, ',
    'Cabe destacar que ',
]

BLACKLIST_CONTENIDO_SPAM = [
    'rojabet','bet365','1xbet','betano','casino online',
    'apuestas deportivas','apuestas en linea','bono sin deposito',
    'giros gratis casino','tragamonedas','ruleta online',
    'prestamo rapido','bitcoin gratis','ganar criptomonedas',
]

BLACKLIST_TITULOS = [
    r'^\s*ultima hora\s*$',r'^\s*breaking news\s*$',
    r'^\s*noticias de hoy\s*$',r'^\s*\d+\s*$',
]

_FUENTES_INCRUSTADAS = re.compile(
    r'\b(LISTIN DIARIO|EL PAIS|El Pais|BBC|CNN|Reuters|AFP|AP News|INFOBAE|Infobae|'
    r'EFE|France 24|DW|Euronews|RT|Al Jazeera|The Guardian|NYT|New York Times|'
    r'Washington Post|Clarin|El Mundo|La Nacion|Milenio)\b[,.]?\s*',
    re.IGNORECASE
)
_FRASES_SUSCRIPCION = re.compile(
    r'(Recib[ii]\s+en\s+tu\s+mail[^.]*\.?|Suscr[ii]bete\s+[^.]*\.?|'
    r'Registrate\s+[^.]*\.?|Newsletter\s+[^.]*\.?|Siguenos\s+en\s+[^.]*\.?|'
    r'Leer\s+mas[^.]*\.?|Lee\s+tambien[^.]*\.?|Fuente:\s*[A-Z][^.]*\.?|'
    r'Copyright\s+[^.]*\.?)',
    re.IGNORECASE
)

_cache_categorias_wp  = {}
_cache_tags_wp        = {}
_cache_boards_pinterest = {}

# ══════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════
def log(mensaje, tipo='info'):
    iconos = {'info':'ℹ️','exito':'✅','error':'❌','advertencia':'⚠️','debug':'🔍'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo,'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None: default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta,'r',encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default.copy()
        except Exception as e:
            log(f"Error cargando JSON {ruta}: {e}",'error')
    return default.copy()

def guardar_json(ruta, datos):
    try:
        directorio = os.path.dirname(ruta)
        if directorio: os.makedirs(directorio, exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path,'w',encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON {ruta}: {e}",'error')
        return False

def generar_hash(texto):
    if not texto: return ""
    t = re.sub(r'[^\w\s]','',texto.lower().strip())
    t = re.sub(r'\s+',' ',t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url(url):
    if not url: return ""
    try:
        parsed = urlparse(url)
        netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)','',parsed.netloc.lower())
        path = parsed.path.lower().rstrip('/')
        path = re.sub(r'/index\.(html|php|htm|asp)$','',path)
        path = re.sub(r'\.html?$','',path)
        return f"{netloc}{path}"
    except: return url.lower().strip()

def similitud_titulos(t1, t2):
    if not t1 or not t2: return 0.0
    stopwords = {'el','la','los','las','un','una','en','de','del','al','y','o','que'}
    def normalizar(t):
        t = re.sub(r'[^\w\s]','',t.lower().strip())
        t = re.sub(r'\s+',' ',t)
        palabras = [p for p in t.split() if p not in stopwords and len(p) > 3]
        return ' '.join(palabras)
    return SequenceMatcher(None, normalizar(t1), normalizar(t2)).ratio()

def similitud_contenido(c1, c2, longitud=120):
    if not c1 or not c2: return 0.0
    def n(c):
        c = re.sub(r'[^\w\s]','',c.lower().strip())
        return re.sub(r'\s+',' ',c)[:longitud]
    return SequenceMatcher(None, n(c1), n(c2)).ratio()

def es_titulo_generico(titulo):
    if not titulo: return True
    tl = titulo.lower().strip()
    for patron in BLACKLIST_TITULOS:
        if re.match(patron, tl): return True
    stop = {'el','la','de','y','en','the','of','to','hoy','los','las'}
    palabras = [p for p in re.findall(r'\b\w+\b',tl) if p not in stop and len(p) > 3]
    return len(set(palabras)) < 4

def limpiar_texto(texto):
    if not texto: return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>',' ',t)
    t = re.sub(r'\s+',' ',t)
    t = re.sub(r'https?://\S*','',t)
    t = _FUENTES_INCRUSTADAS.sub('',t)
    t = _FRASES_SUSCRIPCION.sub('',t)
    t = re.sub(r'\s+',' ',t).strip()
    if t and t[-1] not in '.!?': t += '.'
    return t.strip()

def es_contenido_spam(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    for keyword in BLACKLIST_CONTENIDO_SPAM:
        if keyword.lower() in txt: return True, keyword
    return False, None

def _texto_plano(html_content):
    t = re.sub(r'<[^>]+>',' ', html_content or '')
    return re.sub(r'\s+',' ',t).strip()

def generar_slug_seo(titulo, max_chars=50):
    if not titulo: return ''
    nfkd = unicodedata.normalize('NFKD', titulo)
    sin_acentos = ''.join(c for c in nfkd if not unicodedata.combining(c))
    texto = sin_acentos.lower()
    texto = re.sub(r'[^a-z0-9\s]',' ',texto)
    palabras = [p for p in texto.split() if p not in STOPWORDS_SLUG and len(p) > 2]
    slug = ''
    for palabra in palabras:
        candidato = (slug + '-' + palabra) if slug else palabra
        if len(candidato) > max_chars: break
        slug = candidato
    slug = re.sub(r'-{2,}','-',slug).strip('-')
    return slug or 'articulo'

# ══════════════════════════════════════════════════════════
# ROTACION DE PAISES V20
# ══════════════════════════════════════════════════════════
def cargar_rotacion():
    datos = cargar_json(ROTACION_PAISES_PATH, {
        'fecha':'','ciclo':0,'paises_usados_hoy':[],'conteo_por_pais':{}
    })
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy:
        datos['fecha'] = hoy
        datos['paises_usados_hoy'] = []
    return datos

def seleccionar_paises_ciclo(rotacion, n=3):
    usados_hoy = set(rotacion.get('paises_usados_hoy',[]))
    conteo = rotacion.get('conteo_por_pais',{})
    todos = list(POOL_PAISES.keys())
    candidatos = [p for p in todos if p not in usados_hoy]
    if len(candidatos) < n: candidatos = todos
    def score(pais):
        veces = conteo.get(pais, 0)
        peso  = POOL_PAISES[pais]['peso']
        return (peso / (veces + 1)) * random.uniform(0.8, 1.2)
    candidatos_ord = sorted(candidatos, key=score, reverse=True)
    seleccionados = []
    regiones_usadas = {}
    for pais in candidatos_ord:
        if len(seleccionados) >= n: break
        region = POOL_PAISES[pais]['region']
        if regiones_usadas.get(region, 0) >= 2: continue
        seleccionados.append(pais)
        regiones_usadas[region] = regiones_usadas.get(region, 0) + 1
    for pais in candidatos_ord:
        if len(seleccionados) >= n: break
        if pais not in seleccionados: seleccionados.append(pais)
    return seleccionados[:n]

def registrar_paises_usados(rotacion, paises):
    rotacion['paises_usados_hoy'] = list(set(rotacion.get('paises_usados_hoy',[])) | set(paises))
    rotacion['ciclo'] = rotacion.get('ciclo',0) + 1
    conteo = rotacion.get('conteo_por_pais',{})
    for p in paises: conteo[p] = conteo.get(p,0) + 1
    rotacion['conteo_por_pais'] = conteo
    guardar_json(ROTACION_PAISES_PATH, rotacion)

# ══════════════════════════════════════════════════════════
# DETECCION DE TEMA V20
# ══════════════════════════════════════════════════════════
def detectar_tema(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(p in txt for p in ["terremoto","sismo","huracan","inundacion","tsunami","erupcion"]): return 'desastre'
    if any(p in txt for p in ["asesinato","homicidio","narcotrafico","cartel","crimen organizado","feminicidio","masacre"]): return 'crimen'
    if any(p in txt for p in ["guerra","bombardeo","misil","conflicto armado","invasion","tropas","ofensiva militar","drones de combate"]): return 'guerra'
    if any(p in txt for p in ["misterio","arqueologia","civilizacion perdida","artefacto antiguo","oopart","manuscrito",
                               "enigma historico","historia antigua","tumba","piramide","ruinas antiguas","fosil","mayas","incas","aztecas"]): return 'misterios'
    if any(p in txt for p in ["historia de","siglo xix","siglo xx","segunda guerra","primera guerra","revolucion",
                               "colonia","independencia","dictadura","operacion condor","guerra fria","archivo historico"]): return 'historia'
    if any(p in txt for p in ["geopolitica","brics","otan","g7","g20","acuerdo comercial","tratado internacional",
                               "diplomacia","relaciones internacionales","potencia mundial","hegemonia","orden mundial"]): return 'geopolitica'
    if any(p in txt for p in ["innovacion","startup","emprendimiento","fintech","biotech","nanotecnologia",
                               "biotecnologia","fusion nuclear","computacion cuantica","quantum"]): return 'innovacion'
    if any(p in txt for p in ["inteligencia artificial","chatgpt","openai","gemini","robot","ciberataque","hackeo",
                               "elon musk","spacex","starlink","nvidia","blockchain","criptomoneda","machine learning"]): return 'tecnologia'
    if any(p in txt for p in ["inflacion","recesion","bolsa de valores","mercado financiero","dolar","fmi",
                               "banco central","crisis economica","aranceles","pib","wall street","deficit fiscal"]): return 'economia'
    if any(p in txt for p in ["cambio climatico","calentamiento global","sequia","incendio forestal",
                               "contaminacion","medio ambiente","biodiversidad","extincion","amazonia","glaciar","energia renovable"]): return 'medio_ambiente'
    if any(p in txt for p in ["cancer","enfermedad","pandemia","vacuna","virus","salud publica","oms","epidemia",
                               "medicamento","alzheimer","diabetes","salud mental","longevidad","medicina del futuro"]): return 'salud'
    if any(p in txt for p in ["descubrimiento cientifico","nasa","espacio","agujero negro","exoplaneta",
                               "astronomia","telescopio","marte","luna","fisica cuantica","adn","premio nobel"]): return 'ciencia'
    if any(p in txt for p in ["futbol","copa libertadores","champions league","mundial","olimpiadas",
                               "nba","formula 1","messi","cristiano ronaldo","seleccion"]): return 'deportes'
    if any(p in txt for p in ["pelicula","oscar","grammy","netflix","disney","marvel","anime","musica",
                               "concierto","taylor swift","bad bunny","shakira","cultura pop","serie de tv"]): return 'entretenimiento'
    if any(p in txt for p in ["eleccion","presidente","gobierno","congreso","senado","reforma","decreto","parlamento"]): return 'politica'
    if any(p in txt for p in ["chile","argentina","mexico","colombia","brasil","venezuela","peru","ecuador",
                               "bolivia","uruguay","latinoamerica","america latina","latam"]): return 'latinoamerica'
    return 'general'

def es_evergreen(tema):
    return CATEGORIAS_EVERGREEN.get(tema, {}).get('evergreen', True)

def calcular_relevancia_evergreen(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    score = 0
    for tema_r in TEMAS_ALTA_RELEVANCIA:
        if tema_r in txt: score += 8
    tema = detectar_tema(titulo, descripcion)
    cpm = CATEGORIAS_EVERGREEN.get(tema, {}).get('cpm', 1.0)
    score += int(cpm * 10)
    palabras_efimeras = ['hoy','ayer','esta manana','ultimas horas','breaking','urgente','ultima hora']
    for p in palabras_efimeras:
        if p in txt: score -= 5
    palabras_profundidad = ['historia','investigacion','estudio','descubrimiento','analisis',
                             'datos','cifras','expertos','cientificos','investigadores','por que','como funciona']
    for p in palabras_profundidad:
        if p in txt: score += 3
    palabras_titulo = len(titulo.split())
    if 6 <= palabras_titulo <= 12: score += 5
    return max(0, score)

KEYWORDS_POR_PAIS = {
    'chile':          ['chile','chilena','chileno','santiago','boric','codelco'],
    'argentina':      ['argentina','argentino','buenos aires','milei','cordoba'],
    'mexico':         ['mexico','mexicano','cdmx','sheinbaum','pemex','guadalajara'],
    'colombia':       ['colombia','colombiano','bogota','petro','medellin'],
    'brasil':         ['brasil','brasileno','lula','sao paulo','rio de janeiro'],
    'venezuela':      ['venezuela','venezolano','maduro','caracas','maracaibo'],
    'peru':           ['peru','peruano','lima','boluarte','arequipa'],
    'ecuador':        ['ecuador','ecuatoriano','quito','noboa','guayaquil'],
    'bolivia':        ['bolivia','boliviano','la paz','santa cruz'],
    'uruguay':        ['uruguay','uruguayo','montevideo'],
    'estados_unidos': ['estados unidos','eeuu','trump','washington','wall street','silicon valley','nasa'],
    'europa':         ['europa','union europea','alemania','francia','reino unido','espana','italia'],
    'asia':           ['china','japon','corea','india','xi jinping','taiwan','tokio'],
    'global':         [],
}

def noticia_es_de_pais(titulo, descripcion, pais):
    if pais == 'global': return True
    txt = f"{titulo} {descripcion}".lower()
    return any(kw in txt for kw in KEYWORDS_POR_PAIS.get(pais, []))


# ══════════════════════════════════════════════════════════
# HISTORIAL Y CUOTAS
# ══════════════════════════════════════════════════════════
HISTORIAL_DEFAULT = {
    'urls':[],'urls_normalizadas':[],'hashes':[],'timestamps':[],
    'titulos':[],'descripciones':[],'hashes_contenido':[],'hashes_permanentes':[],
    'estadisticas':{'total_publicadas':0,'total_wp':0,'total_borradores':0,'total_pinterest':0}
}

def cargar_historial():
    h = cargar_json(HISTORIAL_PATH, HISTORIAL_DEFAULT)
    for k,v in HISTORIAL_DEFAULT.items():
        if k not in h: h[k] = v if not isinstance(v,dict) else v.copy()
    _limpiar_historial_antiguo(h)
    return h

def _limpiar_historial_antiguo(h):
    ahora = datetime.now()
    indices_validos = []
    for i,ts in enumerate(h.get('timestamps',[])):
        try:
            if (ahora - datetime.fromisoformat(ts)).days < DIAS_HISTORIAL: indices_validos.append(i)
        except: continue
    for key in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if key in h and isinstance(h[key], list):
            h[key] = [h[key][i] for i in indices_validos if i < len(h[key])]
    if len(h.get('hashes_permanentes',[])) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]

def noticia_ya_publicada(h, url, titulo, desc=""):
    if es_titulo_generico(titulo): return True, "titulo_generico"
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)
    hash_d = generar_hash(desc) if desc else ""
    if url_n in h.get('urls_normalizadas',[]): return True, "url_duplicada"
    todos_hashes = set(h.get('hashes',[])) | set(h.get('hashes_permanentes',[]))
    if hash_t in todos_hashes: return True, "hash_titulo"
    if hash_d and hash_d in h.get('hashes_contenido',[]): return True, "hash_contenido"
    for th in h.get('titulos',[]):
        if not isinstance(th,str): continue
        if similitud_titulos(titulo,th) >= UMBRAL_SIMILITUD_TITULO: return True, "titulo_similar"
    if desc:
        for dh in h.get('descripciones',[]):
            if isinstance(dh,str) and dh:
                if similitud_contenido(desc,dh,150) >= UMBRAL_SIMILITUD_CONTENIDO: return True, "descripcion_similar"
    return False, "nuevo"

def guardar_en_historial(h, url, titulo, desc=""):
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)
    if url_n in h.get('urls_normalizadas',[]): return h
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['hashes_permanentes'].append(hash_t)
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas',0) + 1
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA: h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    if len(h['hashes_permanentes']) > 500: h['hashes_permanentes'] = h['hashes_permanentes'][-500:]
    guardar_json(HISTORIAL_PATH, h)
    return h

def puede_publicar_wp():
    if os.getenv('FORZAR_PUBLICACION','').lower() == 'true': return True
    datos = cargar_json(CUOTAS_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy: return True
    total = datos.get('borradores', 0)
    if total >= MAX_BORRADORES_DIA:
        log(f"Cuota diaria alcanzada ({total}/{MAX_BORRADORES_DIA})",'advertencia')
        return False
    return True

def registrar_borrador():
    datos = cargar_json(CUOTAS_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy: datos = {'fecha':hoy,'borradores':0}
    datos['borradores'] = datos.get('borradores',0) + 1
    guardar_json(CUOTAS_PATH, datos)

def borradores_hoy():
    datos = cargar_json(CUOTAS_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy: return 0
    return datos.get('borradores', 0)

# ══════════════════════════════════════════════════════════
# TAVILY
# ══════════════════════════════════════════════════════════
def buscar_contexto_web(titulo, max_resultados=3):
    if not TAVILY_API_KEY: return []
    try:
        resp = requests.post("https://api.tavily.com/search",
            json={"api_key":TAVILY_API_KEY,"query":titulo,"search_depth":"basic",
                  "max_results":max_resultados,"include_answer":False}, timeout=15)
        data = resp.json()
        resultados = data.get("results",[])
        if not resultados: return []
        return [{"title":r.get("title",""),"url":r.get("url",""),
                 "content":(r.get("content","") or "")[:600]} for r in resultados]
    except Exception as e:
        log(f"Tavily fallo ({e})",'advertencia')
        return []

# ══════════════════════════════════════════════════════════
# IA V20 — PROMPT EVERGREEN
# ══════════════════════════════════════════════════════════
def reescribir_noticia_v20(titulo, contenido, categoria='general', pais_foco='global', feedback_correccion=None):
    api_key = OPENAI_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY or GEMINI_API_KEY
    if not api_key: return None

    TITULOS_BOX = [
        ('⚡','Lo que debes saber','#ff6b35','#fff3e0'),
        ('📋','Resumen rapido','#0891b2','#e0f2fe'),
        ('🔑','Puntos clave','#a855f7','#ede9fe'),
        ('📌','Lo esencial','#1a56db','#eff6ff'),
    ]
    emoji_box, texto_box, color_titulo, color_fondo = random.choice(TITULOS_BOX)

    nombres_paises = {
        'chile':'Chile','argentina':'Argentina','mexico':'Mexico','colombia':'Colombia',
        'brasil':'Brasil','venezuela':'Venezuela','peru':'Peru','ecuador':'Ecuador',
        'bolivia':'Bolivia','uruguay':'Uruguay','estados_unidos':'Estados Unidos',
        'europa':'Europa','asia':'Asia','global':'America Latina',
    }
    nombre_pais = nombres_paises.get(pais_foco, 'America Latina')
    pais_contexto = f"\nPAIS/REGION DE FOCO: {nombre_pais} — angulo de impacto en {nombre_pais} y America Latina."

    bloque_feedback = ""
    if feedback_correccion:
        problemas_txt = '\n'.join(f'  - {p}' for p in feedback_correccion)
        bloque_feedback = f"CORRECCION OBLIGATORIA:\n{problemas_txt}\n"

    bloque_contexto_web = ""
    if not feedback_correccion:
        fuentes_web = buscar_contexto_web(titulo)
        if fuentes_web:
            fuentes_txt = "\n\n".join(f"Fuente {i+1}: {f['title']}\n{f['content']}" for i,f in enumerate(fuentes_web))
            bloque_contexto_web = f"CONTEXTO ADICIONAL:\n{fuentes_txt}\n"

    prompt = f"""Eres Editor Jefe Digital de VerdadHoy.com. Tono: directo, claro, periodistico. Audiencia: Chile, Argentina, Mexico.
{pais_contexto}

MISION: contenido EVERGREEN. Util hoy y en 6 meses. NO es noticia del dia. ES articulo de fondo.

TIPOS VALIDOS:
- "Por que [tema] importa para America Latina"
- "La historia detras de [tema]: lo que nadie te conto"
- "[N] datos sorprendentes sobre [tema]"
- "Que es [tema] y por que deberias prestarle atencion"

EXTENSION MINIMA: 750 palabras. Incluye SIEMPRE:
- Antecedentes historicos o cientificos
- Al menos 3 cifras o datos verificables
- Impacto en America Latina
- Proyeccion a futuro

FUENTE/TEMA BASE:
Titulo: {titulo}
Contenido: {contenido[:2500]}
Categoria: {categoria}

{bloque_contexto_web}

REGLAS SEO:
TITULO: [KEYWORD INICIO]: [dato] [power word] — max 55 chars, numero obligatorio
Power words: historico, clave, revelador, sorprendente, esencial, record, definitivo
META: "[KEYWORD] — [dato con numero]. [consecuencia]. [cierre]" — 150-160 chars exacto

ESTRUCTURA HTML:
<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este articulo</p>
<ol style="margin:0;padding-left:20px;color:#475569;font-size:0.9em;">
<li><a href="#seccion-1" style="color:#1a56db;text-decoration:none;">[H2 #1]</a></li>
<li><a href="#seccion-2" style="color:#1a56db;text-decoration:none;">[H2 #2]</a></li>
<li><a href="#seccion-3" style="color:#1a56db;text-decoration:none;">[H2 #3]</a></li>
<li><a href="#seccion-4" style="color:#1a56db;text-decoration:none;">[H2 #4]</a></li>
</ol></nav>

<div style="background:{color_fondo};border-left:4px solid {color_titulo};padding:16px 20px;margin:0 0 24px 0;border-radius:0 8px 8px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:{color_titulo};font-size:0.95em;">{emoji_box} {texto_box}</p>
<ul style="margin:0;padding-left:20px;color:#374151;">
<li style="margin-bottom:6px;">[Punto 1]</li><li style="margin-bottom:6px;">[Punto 2]</li>
<li style="margin-bottom:6px;">[Punto 3]</li><li style="margin-bottom:0;">[Punto 4]</li>
</ul></div>

<p>[KEYWORD] es/fue/representa... [hecho + dato + relevancia LATAM — max 40 palabras]</p>

<h2 id="seccion-1">[KEYWORD]: [historia o que es]</h2>
<p>[Antecedentes. Sin embargo, [dato historico]...]</p>
<p>[Desarrollo. Ademas, [cifra]...]</p>

<h2 id="seccion-2">[Datos que revelan importancia de KEYWORD]</h2>
<p>[Por otro lado, [dato con numero]...]</p>

<p style="border-left:3px solid #f59e0b;padding:10px 14px;margin:16px 0;background:#fffbeb;font-style:italic;color:#374151;">[2-3 oraciones editoriales. Directo. Contiene KEYWORD exacta.]</p>

<blockquote style="border-left:3px solid #e5e7eb;padding:12px 16px;margin:20px 0;background:#f9fafb;font-style:italic;color:#4b5563;">
"[Cita o dato estadistico verificable con numero y fuente]"
</blockquote>

<h2 id="seccion-3">[KEYWORD] en America Latina: [impacto]</h2>
<p>[En consecuencia, [impacto en LATAM con 2 paises]...]</p>

<h2 id="seccion-4">[El futuro de KEYWORD / Por que define la proxima decada]</h2>
<p>[Cabe destacar, [proyeccion futura con año]. Pregunta al lector al final.]</p>

[ENLACES_INTERNOS]

CHECKLIST:
- Keyword en titulo (primeras 3 palabras)
- Keyword en meta (primeros 40 chars)
- Keyword en apertura (antes palabra 80)
- Keyword en H2 #1 y #2
- Keyword minimo 6 veces total
- 4 H2 con id="seccion-N"
- Tabla de contenidos
- Box resumen
- Blockquote con dato numerico
- 4 transiciones: sin embargo, ademas, por otro lado, en consecuencia
- Meta 150-160 chars
- Titulo max 55 chars con numero y power word
- Minimo 750 palabras

PROHIBIDO: NO noticias efimeras. NO inventar datos. NO copiar texto original.

{bloque_feedback}

RESPONDE SOLO JSON sin markdown:
{{"titulo_seo":"keyword inicio+numero+power word max 55 chars","slug":"max-50-chars","meta_descripcion":"keyword primero 150-160 chars","contenido_html":"HTML completo","keyword_principal":"2-3 palabras","keywords_secundarias":["kw2","kw3","kw4","kw5"],"categoria":"tecnologia|ciencia|salud|historia|misterios|geopolitica|economia|politica|medio_ambiente|innovacion|cultura|entretenimiento|deportes|latinoamerica|mundo|general","parrafo_nativo":"texto plano parrafo nativo","descripcion_pinterest":"100-150 chars con hashtags para Pinterest"}}"""

    def _llamar_api(url_api, headers, modelo, payload):
        try:
            resp = requests.post(url_api, headers=headers, json=payload, timeout=60)
        except Exception as e:
            log(f"IA error de red: {e}",'error')
            return None
        try: resp_json = resp.json()
        except:
            log(f"IA respuesta no JSON (HTTP {resp.status_code})",'error')
            return None
        if "choices" not in resp_json:
            err = resp_json.get("error",{})
            msg = err.get("message",str(resp_json)[:200]) if isinstance(err,dict) else str(err)[:200]
            log(f"IA error: {msg}",'error')
            return None
        return resp_json

    try:
        proveedores = []
        if OPENAI_API_KEY:
            proveedores.append(("OpenAI","https://api.openai.com/v1/chat/completions",
                                {"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                                "gpt-4o-mini"))
        if OPENROUTER_API_KEY:
            proveedores.append(("OpenRouter","https://openrouter.ai/api/v1/chat/completions",
                                {"Authorization":f"Bearer {OPENROUTER_API_KEY}","Content-Type":"application/json"},
                                "meta-llama/llama-3.3-70b-instruct:free"))
        if GROQ_API_KEY:
            proveedores.append(("Groq","https://api.groq.com/openai/v1/chat/completions",
                                {"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                                "llama-3.3-70b-versatile"))
        if GEMINI_API_KEY:
            proveedores.append(("Gemini","https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                                {"Authorization":f"Bearer {GEMINI_API_KEY}","Content-Type":"application/json"},
                                "gemini-2.5-flash"))

        resp_json = None
        for i,(nombre,url_i,headers_i,modelo_i) in enumerate(proveedores):
            payload_i = {"model":modelo_i,"messages":[{"role":"user","content":prompt}],"temperature":0.35,"max_tokens":4000}
            if i > 0: log(f"Reintentando con {nombre}...",'advertencia')
            resp_json = _llamar_api(url_i, headers_i, modelo_i, payload_i)
            if resp_json: break

        if not resp_json: return None

        texto = resp_json["choices"][0]["message"]["content"].strip()
        texto = re.sub(r'^```json\s*|```$','',texto,flags=re.MULTILINE).strip()
        if not texto.endswith('}'): return None

        resultado = json.loads(texto)
        categorias_validas = set(CATEGORIAS_EVERGREEN.keys())
        cat_ia = resultado.get('categoria','').strip().lower()
        if cat_ia not in categorias_validas: resultado['categoria'] = categoria if categoria in categorias_validas else 'general'
        log(f"IA OK — Titulo: {resultado.get('titulo_seo','')[:55]} | Cat: {resultado.get('categoria')}",'info')
        return resultado
    except Exception as e:
        log(f"reescribir_noticia_v20 error: {e}",'advertencia')
        return None


# ══════════════════════════════════════════════════════════
# POST-PROCESAMIENTO
# ══════════════════════════════════════════════════════════
def postprocesar_meta(resultado_ia):
    meta = resultado_ia.get('meta_descripcion','').strip()
    if not meta: return resultado_ia
    if len(meta) > 160: meta = meta[:157].rsplit(' ',1)[0].rstrip('.,;') + '...'
    if len(meta) < 150:
        meta_base = meta.rstrip('.')
        extensiones = [
            ' Toda la informacion actualizada sobre este tema en Verdad Hoy.',
            ' Lo que necesitas saber sobre este tema en Verdad Hoy.',
            ' Analisis completo y actualizado en Verdad Hoy.',
            ' Mas detalles en Verdad Hoy.',
        ]
        for ext in extensiones:
            candidato = meta_base + ext
            if 150 <= len(candidato) <= 160: meta = candidato; break
            elif len(candidato) > 160:
                espacio = 160 - len(meta_base)
                trozo = ext[:espacio].rsplit(' ',1)[0]
                candidato2 = meta_base + trozo
                if len(candidato2) >= 150: meta = candidato2; break
        if len(meta) < 150: meta = (meta.rstrip('.') + ' — Analisis completo en Verdad Hoy.')[:160]
    resultado_ia['meta_descripcion'] = meta
    return resultado_ia

def postprocesar_titulo(resultado_ia):
    titulo = resultado_ia.get('titulo_seo','').strip()
    if not titulo: return resultado_ia
    titulo_lower = titulo.lower()
    tiene_pw = any(pw in titulo_lower for pw in POWER_WORDS_LISTA)
    tiene_numero = bool(re.search(r'\d', titulo))
    año_actual = datetime.now().year
    if not tiene_numero and len(titulo) <= 45:
        candidato = f"{titulo}: {año_actual}"
        if len(candidato) <= 55: titulo = candidato
    if not tiene_pw and len(titulo) <= 47:
        for pw in ['clave','historico','revelador','esencial','sorprendente']:
            candidato = f"{titulo}, {pw}"
            if len(candidato) <= 55: titulo = candidato; break
    resultado_ia['titulo_seo'] = titulo
    return resultado_ia

def postprocesar_densidad(resultado_ia):
    contenido_html = resultado_ia.get('contenido_html','')
    keyword = resultado_ia.get('keyword_principal','').strip()
    categoria = resultado_ia.get('categoria','general')
    if not keyword or not contenido_html: return resultado_ia
    texto = _texto_plano(contenido_html)
    n_palabras = len(texto.split())
    if n_palabras == 0: return resultado_ia
    kw_lower = keyword.lower()
    kw_palabras = len(keyword.split())
    ocurrencias = len(re.findall(re.escape(kw_lower), texto.lower()))
    densidad = (ocurrencias * kw_palabras / n_palabras) * 100
    limite_alto = 3.0 if kw_palabras == 1 else (5.0 if kw_palabras == 2 else 6.0)
    if ocurrencias <= 12 or densidad <= limite_alto: return resultado_ia
    objetivo = min(12, max(4, int(n_palabras * (limite_alto * 0.7) / 100 / kw_palabras)))
    sobran = ocurrencias - objetivo
    sinonimos = SINONIMOS_KEYWORD.get(categoria, SINONIMOS_KEYWORD['general'])
    html_lower = contenido_html.lower()
    posiciones = [m.start() for m in re.finditer(re.escape(kw_lower), html_lower)]
    h2_rangos = [(m.start(),m.end()) for m in re.finditer(r'<h2[^>]*>.*?</h2>',contenido_html,flags=re.IGNORECASE|re.DOTALL)]
    def _en_h2(pos): return any(inicio <= pos <= fin for inicio,fin in h2_rangos)
    def _en_tag(pos):
        fragmento = html_lower[max(0,pos-200):pos]
        return fragmento.rfind('<') > fragmento.rfind('>')
    candidatas = [p for p in posiciones if not _en_h2(p) and not _en_tag(p)]
    candidatas_reemplazar = candidatas[1:]
    reemplazos = 0
    html_nuevo = contenido_html
    for pos in reversed(candidatas_reemplazar):
        if reemplazos >= sobran: break
        sinonimo = sinonimos[reemplazos % len(sinonimos)]
        if html_nuevo[pos:pos+1].isupper(): sinonimo = sinonimo.capitalize()
        fin = pos + len(keyword)
        html_nuevo = html_nuevo[:pos] + sinonimo + html_nuevo[fin:]
        reemplazos += 1
    resultado_ia['contenido_html'] = html_nuevo
    return resultado_ia

def postprocesar_transiciones(resultado_ia):
    contenido_html = resultado_ia.get('contenido_html','')
    texto_lower = _texto_plano(contenido_html).lower()
    n_trans = sum(1 for p in PALABRAS_TRANSICION if p in texto_lower)
    if n_trans >= 4: return resultado_ia
    faltan = 4 - n_trans
    transiciones_usadas = [t for t in PALABRAS_TRANSICION if t in texto_lower]
    disponibles = [t for t in TRANSICIONES_INYECTABLES
                   if not any(t.strip().lower().startswith(u) for u in transiciones_usadas)]
    inyectadas = 0
    def inyectar(match_p):
        nonlocal inyectadas
        if inyectadas >= faltan: return match_p.group(0)
        parrafo = match_p.group(0)
        texto_p = _texto_plano(parrafo)
        if len(texto_p) < 40 or any(t.lower() in texto_p.lower() for t in PALABRAS_TRANSICION): return parrafo
        if inyectadas == 0: return parrafo
        trans = disponibles[inyectadas % len(disponibles)]
        parrafo_nuevo = re.sub(r'(<p[^>]*>)(\s*)',lambda m:m.group(1)+m.group(2)+trans,parrafo,count=1,flags=re.IGNORECASE)
        inyectadas += 1
        return parrafo_nuevo
    contenido_nuevo = re.sub(r'<p[^>]*>.*?</p>',inyectar,contenido_html,flags=re.IGNORECASE|re.DOTALL)
    resultado_ia['contenido_html'] = contenido_nuevo
    return resultado_ia

def postprocesar_resultado(resultado_ia):
    resultado_ia = postprocesar_densidad(resultado_ia)
    resultado_ia = postprocesar_transiciones(resultado_ia)
    resultado_ia = postprocesar_meta(resultado_ia)
    resultado_ia = postprocesar_titulo(resultado_ia)
    return resultado_ia

INICIOS_META_PROHIBIDOS = ('descubre','conoce','enterate','sabias')

def validar_calidad_articulo(contenido_html, meta_desc, titulo_seo='', categoria='', keyword=''):
    problemas = []
    texto_plano = _texto_plano(contenido_html or '')
    n_palabras = len(texto_plano.split())
    if n_palabras < 620: problemas.append(f"Solo {n_palabras} palabras — minimo 620.")
    if '<blockquote' not in (contenido_html or ''): problemas.append("Falta blockquote.")
    n_h2 = len(re.findall(r'<h2',contenido_html or '',flags=re.IGNORECASE))
    if n_h2 < 4: problemas.append(f"Solo {n_h2} H2 — minimo 4.")
    if keyword:
        kw_lower = keyword.lower()
        primeras_80 = ' '.join(texto_plano.split()[:80]).lower()
        if kw_lower not in primeras_80: problemas.append(f"Keyword '{keyword}' no en primeras 80 palabras.")
        if n_palabras > 0:
            kw_palabras = len(keyword.split())
            kw_oc = len(re.findall(re.escape(kw_lower), texto_plano.lower()))
            densidad = (kw_oc * kw_palabras / n_palabras) * 100
            if densidad < 0.2: problemas.append(f"Densidad keyword {densidad:.1f}% — muy baja.")
    if '<nav' not in (contenido_html or '') and 'tabla-contenidos' not in (contenido_html or ''):
        problemas.append("Falta tabla de contenidos.")
    n_trans = sum(1 for p in PALABRAS_TRANSICION if p in texto_plano.lower())
    if n_trans < 4: problemas.append(f"Solo {n_trans} transiciones — minimo 4.")
    len_meta = len(meta_desc or '')
    if len_meta < 150 or len_meta > 160: problemas.append(f"Meta {len_meta} chars — debe ser 150-160.")
    if keyword and meta_desc:
        if keyword.lower() not in meta_desc[:40].lower(): problemas.append(f"Meta debe empezar con '{keyword}'.")
    if (meta_desc or '').strip().lower().startswith(INICIOS_META_PROHIBIDOS): problemas.append("Meta empieza con palabra prohibida.")
    if titulo_seo:
        if not any(pw in titulo_seo.lower() for pw in POWER_WORDS_ES): problemas.append("Titulo sin power word.")
        if not re.search(r'\d', titulo_seo): problemas.append("Titulo sin numero.")
    return (len(problemas) == 0, problemas)

# ══════════════════════════════════════════════════════════
# PINTEREST V20
# ══════════════════════════════════════════════════════════
def obtener_board_id_pinterest(slug_tablero):
    global _cache_boards_pinterest
    if slug_tablero in _cache_boards_pinterest: return _cache_boards_pinterest[slug_tablero]
    if not PINTEREST_TOKEN: return None
    try:
        headers = {'Authorization':f'Bearer {PINTEREST_TOKEN}','Content-Type':'application/json'}
        resp = requests.get('https://api.pinterest.com/v5/boards',headers=headers,params={'page_size':50},timeout=15)
        if resp.status_code == 200:
            boards = resp.json().get('items',[])
            for board in boards:
                board_name = board.get('name','').lower()
                board_id   = board.get('id','')
                nfkd = unicodedata.normalize('NFKD', board_name)
                sin_ac = ''.join(c for c in nfkd if not unicodedata.combining(c))
                slug = re.sub(r'[^a-z0-9]+','-',sin_ac).strip('-')
                _cache_boards_pinterest[slug] = board_id
                _cache_boards_pinterest[re.sub(r'[^a-z0-9]+','-',board_name).strip('-')] = board_id
            resultado = _cache_boards_pinterest.get(slug_tablero)
            if not resultado:
                log(f"Board '{slug_tablero}' no encontrado. Disponibles: {list(_cache_boards_pinterest.keys())}",'advertencia')
            return resultado
        else:
            log(f"Pinterest boards error: {resp.status_code}",'advertencia')
    except Exception as e:
        log(f"Error obteniendo boards Pinterest: {e}",'advertencia')
    return None

def publicar_en_pinterest(titulo, url_articulo, imagen_path, categoria, descripcion_pinterest="", meta_desc=""):
    if not PINTEREST_TOKEN:
        log("PINTEREST_TOKEN no configurado",'advertencia')
        return False
    if not imagen_path or not os.path.exists(imagen_path):
        log("Sin imagen para Pinterest",'advertencia')
        return False
    slug_tablero = TABLEROS_PINTEREST.get(categoria,'noticias-del-mundo')
    board_id = obtener_board_id_pinterest(slug_tablero)
    if not board_id: board_id = obtener_board_id_pinterest('noticias-del-mundo')
    if not board_id:
        log(f"Pinterest: no se encontro board para '{slug_tablero}'",'error')
        return False
    if descripcion_pinterest:
        desc_pin = descripcion_pinterest
    else:
        hashtags_cat = {
            'tecnologia':'#Tecnologia #IA #Innovacion','ciencia':'#Ciencia #Descubrimiento',
            'salud':'#Salud #Bienestar #Medicina','historia':'#Historia #CulturaLatina',
            'misterios':'#Misterios #Historia','geopolitica':'#Geopolitica #Internacional',
            'economia':'#Economia #Finanzas #LATAM','politica':'#Politica #AméricaLatina',
            'medio_ambiente':'#MedioAmbiente #CambioClimatico','innovacion':'#Innovacion #Futuro',
            'cultura':'#Cultura #AméricaLatina','entretenimiento':'#Entretenimiento #Cine',
            'deportes':'#Deportes #Futbol','latinoamerica':'#Latinoamerica #AméricaLatina',
            'mundo':'#Mundo #Internacional',
        }
        hashtags = hashtags_cat.get(categoria,'#Noticias #AméricaLatina #VerdadHoy')
        desc_pin = f"{(meta_desc or titulo)[:200]} {hashtags}"
    headers = {'Authorization':f'Bearer {PINTEREST_TOKEN}','Content-Type':'application/json'}
    try:
        import base64
        with open(imagen_path,'rb') as f: imagen_b64 = base64.b64encode(f.read()).decode('utf-8')
        pin_data = {
            "board_id": board_id,
            "title": titulo[:100],
            "description": desc_pin[:500],
            "link": url_articulo,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/jpeg",
                "data": imagen_b64
            }
        }
        resp = requests.post('https://api.pinterest.com/v5/pins',headers=headers,json=pin_data,timeout=30)
        if resp.status_code in (200,201):
            pin_id = resp.json().get('id','unknown')
            log(f"Pinterest: pin creado ID {pin_id} en '{slug_tablero}'",'exito')
            return True
        else:
            log(f"Pinterest error: {resp.status_code} — {resp.text[:300]}",'advertencia')
            # Fallback sin imagen base64
            pin_fallback = {"board_id":board_id,"title":titulo[:100],"description":desc_pin[:500],"link":url_articulo}
            resp2 = requests.post('https://api.pinterest.com/v5/pins',headers=headers,json=pin_fallback,timeout=30)
            if resp2.status_code in (200,201):
                log(f"Pinterest fallback OK: pin creado",'exito')
                return True
            log(f"Pinterest fallback fallo: {resp2.status_code}",'error')
            return False
    except Exception as e:
        log(f"Pinterest excepcion: {e}",'error')
        return False


# ══════════════════════════════════════════════════════════
# WORDPRESS
# ══════════════════════════════════════════════════════════
def obtener_id_categoria_wp(slug_categoria):
    global _cache_categorias_wp
    if slug_categoria in _cache_categorias_wp: return _cache_categorias_wp[slug_categoria]
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories",
            params={'slug':slug_categoria,'per_page':1},
            auth=(WP_USER,WP_APP_PASSWORD),timeout=15).json()
        if r and isinstance(r,list) and len(r) > 0:
            cat_id = r[0]['id']
            _cache_categorias_wp[slug_categoria] = cat_id
            return cat_id
    except Exception as e:
        log(f"Error categoria '{slug_categoria}': {e}",'advertencia')
    return None

def obtener_crear_tag_wp(nombre_tag):
    global _cache_tags_wp
    tag_clean = nombre_tag.lower().strip()
    if not tag_clean or len(tag_clean) < 2: return None
    if tag_clean in _cache_tags_wp: return _cache_tags_wp[tag_clean]
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags",params={'search':tag_clean,'per_page':5},auth=(WP_USER,WP_APP_PASSWORD),timeout=10).json()
        if r and isinstance(r,list):
            for tag in r:
                if tag.get('name','').lower() == tag_clean:
                    _cache_tags_wp[tag_clean] = tag['id']
                    return tag['id']
        r_post = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",json={'name':nombre_tag.strip()},auth=(WP_USER,WP_APP_PASSWORD),timeout=10).json()
        if 'id' in r_post:
            _cache_tags_wp[tag_clean] = r_post['id']
            return r_post['id']
    except: pass
    return None

def agregar_watermark(img):
    try:
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        ancho, alto = img.size
        font_size = max(20, int(ancho * 0.018))
        try: font_wm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except: font_wm = ImageFont.load_default()
        texto_wm = "verdadhoy.com"
        try:
            bbox = draw.textbbox((0,0), texto_wm, font=font_wm)
            txt_w, txt_h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        except: txt_w, txt_h = 150, font_size
        margen, padding = 18, 8
        x = ancho - txt_w - margen - padding*2
        y = alto - txt_h - margen - padding*2
        overlay = Image.new('RGBA', img.size, (0,0,0,0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([x-padding,y-padding,x+txt_w+padding,y+txt_h+padding],radius=6,fill=(0,0,0,180))
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((x+1,y+1), texto_wm, font=font_wm, fill=(0,0,0,200))
        draw.text((x,y), texto_wm, font=font_wm, fill='#f5c518')
        return img
    except: return img

def descargar_imagen(url):
    if not url: return None
    for bloqueo in ['google.com','gstatic.com','facebook.com','logo','icon','favicon']:
        if bloqueo in url.lower(): return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200: return None
        ct = r.headers.get('content-type','')
        if 'image' not in ct and 'octet' not in ct: return None
        img = Image.open(BytesIO(r.content))
        w, h = img.size
        if w < 300 or h < 200: return None
        if img.mode in ('RGBA','P','LA'): img = img.convert('RGB')
        if w < 1200: img = img.resize((1200, int(h*(1200/w))), Image.LANCZOS)
        elif w > 1600: img = img.resize((1600, int(h*(1600/w))), Image.LANCZOS)
        img = agregar_watermark(img)
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=92, optimize=True)
        if os.path.getsize(p) < 3000: os.remove(p); return None
        return p
    except: return None

def extraer_imagen_web(url):
    if not url: return None
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for prop in ['og:image','twitter:image']:
            tag = s.find('meta', property=prop) or s.find('meta', attrs={'name':prop})
            if tag:
                img = tag.get('content','').strip()
                if img and img.startswith('http') and 'google' not in img.lower(): return img
        return None
    except: return None

def crear_imagen_titulo(titulo, categoria='general'):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        W, H = 1600, 900
        img = Image.new('RGB', (W,H), color='#0f172a')
        draw = ImageDraw.Draw(img)
        for i in range(H):
            ratio = i/H
            draw.line([(0,i),(W,i)], fill=(int(15+(30-15)*ratio),int(23+(41-23)*ratio),int(42+(69-42)*ratio)))
        draw.rectangle([(0,0),(W,10)], fill='#dc2626')
        colores_cat = {
            'misterios':'#6d28d9','historia':'#92400e','geopolitica':'#1e40af',
            'innovacion':'#0891b2','tecnologia':'#2563eb','ciencia':'#0891b2',
            'salud':'#16a34a','economia':'#059669','politica':'#7c3aed',
            'deportes':'#d97706','entretenimiento':'#db2777','cultura':'#db2777',
            'medio_ambiente':'#15803d','latinoamerica':'#ea580c','mundo':'#4338ca','general':'#475569',
        }
        nombres_cat = {
            'misterios':'MISTERIOS','historia':'HISTORIA','geopolitica':'GEOPOLITICA',
            'innovacion':'INNOVACION','tecnologia':'TECNOLOGIA','ciencia':'CIENCIA',
            'salud':'SALUD','economia':'ECONOMIA','politica':'POLITICA',
            'deportes':'DEPORTES','entretenimiento':'ENTRETENIMIENTO','cultura':'CULTURA',
            'medio_ambiente':'MEDIO AMBIENTE','latinoamerica':'LATINOAMERICA','mundo':'MUNDO','general':'NOTICIAS',
        }
        color_badge = colores_cat.get(categoria,'#475569')
        texto_badge = nombres_cat.get(categoria,'NOTICIAS')
        try:
            font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 62)
            font_marca  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
            font_sub    = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except: font_badge = font_titulo = font_marca = font_sub = ImageFont.load_default()
        badge_x, badge_y = 70, 70
        try:
            bbox_b = draw.textbbox((0,0), texto_badge, font=font_badge)
            bw, bh = bbox_b[2]-bbox_b[0], bbox_b[3]-bbox_b[1]
        except: bw, bh = 160, 32
        draw.rounded_rectangle([badge_x,badge_y,badge_x+bw+28,badge_y+bh+16],radius=6,fill=color_badge)
        draw.text((badge_x+14,badge_y+8), texto_badge, font=font_badge, fill='white')
        chars_pl = 38 if len(titulo) > 80 else 44
        font_size_t = 52 if len(titulo) > 100 else 62
        try: font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_t)
        except: pass
        tt = textwrap.fill(titulo[:160], width=chars_pl)
        lineas = tt.split('\n')
        alto_total = len(lineas) * (font_size_t+14)
        y_texto = max(160, (H-alto_total)//2-40)
        for linea in lineas:
            draw.text((72,y_texto+2), linea, font=font_titulo, fill=(0,0,0,120))
            y_texto += font_size_t+14
        y_texto = max(160, (H-alto_total)//2-40)
        for linea in lineas:
            draw.text((70,y_texto), linea, font=font_titulo, fill='#f1f5f9')
            y_texto += font_size_t+14
        draw.rectangle([(0,H-90),(W,H)], fill='#1e293b')
        draw.rectangle([(0,H-90),(W,H-87)], fill=color_badge)
        draw.text((70,H-65), "VERDAD HOY", font=font_marca, fill='#f1f5f9')
        draw.text((W-420,H-60), "verdadhoy.com", font=font_sub, fill='#94a3b8')
        img = agregar_watermark(img)
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img.save(p, 'JPEG', quality=92, optimize=True)
        return p
    except: return None

def subir_imagen_wp(imagen_path, titulo, alt_text="", frase_clave="", meta_descripcion=""):
    if not imagen_path or not os.path.exists(imagen_path): return None
    try:
        nombre = f"verdadhoy-{generar_hash(titulo)}.jpg"
        with open(imagen_path,'rb') as f:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/media",
                headers={'Content-Disposition':f'attachment; filename="{nombre}"','Content-Type':'image/jpeg'},
                data=f.read(), auth=(WP_USER,WP_APP_PASSWORD), timeout=60).json()
        if 'id' in r:
            media_id = r['id']
            kw_imagen = (frase_clave or titulo)[:125]
            try:
                requests.post(f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                    json={'title':kw_imagen,'alt_text':kw_imagen,
                          'caption':f"{titulo[:120]} — Fuente: Verdad Hoy",
                          'description':(frase_clave or titulo)[:300]},
                    auth=(WP_USER,WP_APP_PASSWORD), timeout=10)
            except: pass
            return media_id
    except Exception as e:
        log(f"Excepcion subiendo imagen: {e}",'advertencia')
    return None

def obtener_articulos_wp_recientes(num=3):
    if not WP_APP_PASSWORD: return []
    try:
        resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts",
            params={'per_page':num+1,'status':'publish','orderby':'date','order':'desc','_fields':'id,title,link'},
            auth=(WP_USER,WP_APP_PASSWORD), timeout=10)
        if resp.status_code == 200: return resp.json()[:num]
    except: pass
    return []

def insertar_enlaces_internos(contenido_html):
    articulos = obtener_articulos_wp_recientes(2)
    if not articulos: return contenido_html.replace("[ENLACES_INTERNOS]","")
    items = ""
    for art in articulos:
        t = art.get('title',{}).get('rendered','')
        l = art.get('link','#')
        if t and l: items += f'<li><a href="{l}" style="color:#1a1a1a;text-decoration:none;">{t}</a></li>\n'
    html_rel = ""
    if items:
        html_rel = (f'\n<div class="vh-relacionadas" style="margin-top:24px;padding:16px;background:#f8f9fa;border-left:4px solid #cc0000;border-radius:4px;">\n'
                    f'<h3 style="margin:0 0 10px;font-size:1rem;color:#cc0000;">📰 Te puede interesar</h3>\n'
                    f'<ul style="margin:0;padding-left:20px;">\n{items}</ul>\n</div>\n')
    if "[ENLACES_INTERNOS]" in contenido_html: return contenido_html.replace("[ENLACES_INTERNOS]", html_rel)
    return contenido_html + html_rel

def publicar_borrador_wordpress(titulo, contenido, categoria, imagen_path, fuente_url, pais_foco='global', feedback_correccion=None):
    if not WP_APP_PASSWORD: return None, None, None
    if not imagen_path or not os.path.exists(imagen_path): return None, None, None

    resultado_ia = reescribir_noticia_v20(titulo, contenido, categoria, pais_foco, feedback_correccion)
    if not resultado_ia: return None, None, None
    resultado_ia = postprocesar_resultado(resultado_ia)

    keyword = resultado_ia.get('keyword_principal','')
    es_valido, problemas = validar_calidad_articulo(
        resultado_ia.get('contenido_html',''), resultado_ia.get('meta_descripcion',''),
        resultado_ia.get('titulo_seo',''), resultado_ia.get('categoria',''), keyword)

    if not es_valido:
        if not REINTENTAR_CALIDAD_IA: return None, None, None
        log(f"Reintentando ({len(problemas)} problemas)",'advertencia')
        for p in problemas: log(f"   - {p}",'advertencia')
        resultado_reintento = reescribir_noticia_v20(titulo, contenido, categoria, pais_foco, feedback_correccion=problemas)
        if resultado_reintento:
            resultado_reintento = postprocesar_resultado(resultado_reintento)
            es_valido_2, _ = validar_calidad_articulo(
                resultado_reintento.get('contenido_html',''), resultado_reintento.get('meta_descripcion',''),
                resultado_reintento.get('titulo_seo',''), resultado_reintento.get('categoria',''),
                resultado_reintento.get('keyword_principal',''))
            if es_valido_2: resultado_ia = resultado_reintento
            else: return None, None, None
        else: return None, None, None

    titulo_final  = resultado_ia.get('titulo_seo', titulo).strip()
    if len(titulo_final) > 55:
        t = ''
        for p in titulo_final.split():
            c = (t+' '+p).strip()
            if len(c) > 55: break
            t = c
        titulo_final = t or titulo_final[:55]

    titulo_seo         = titulo_final + ' | Verdad Hoy'
    meta_desc          = resultado_ia.get('meta_descripcion','')
    frase_clave        = resultado_ia.get('keyword_principal','')
    slug_ia            = resultado_ia.get('slug','')
    contenido_html     = resultado_ia.get('contenido_html','')
    categoria_ia       = resultado_ia.get('categoria', categoria)
    desc_pinterest     = resultado_ia.get('descripcion_pinterest','')

    slug_post = slug_ia if (slug_ia and len(slug_ia) <= 50) else generar_slug_seo(titulo_final)

    if '<nav' not in contenido_html and 'tabla-contenidos' not in contenido_html:
        h2_raw = re.findall(r'<h2[^>]*>(.*?)</h2>', contenido_html, flags=re.IGNORECASE|re.DOTALL)
        h2_textos = [(str(i+1), re.sub(r'<[^>]+>','',t).strip()) for i,t in enumerate(h2_raw)]
        items_toc = '\n'.join(f'<li style="margin-bottom:4px;"><a href="#seccion-{n}" style="color:#1a56db;text-decoration:none;">{t}</a></li>' for n,t in h2_textos[:4])
        if items_toc:
            toc_html = (f'<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">'
                        f'<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este articulo</p>'
                        f'<ol style="margin:0;padding-left:20px;color:#475569;font-size:0.9em;">{items_toc}</ol></nav>')
            contenido_html = toc_html + contenido_html

    contenido_html = insertar_enlaces_internos(contenido_html)

    tags_ids = []
    for kw in resultado_ia.get('keywords_secundarias',[])[:5]:
        tag_id = obtener_crear_tag_wp(kw)
        if tag_id: tags_ids.append(tag_id)

    slug_cat = CATEGORIAS_EVERGREEN.get(categoria_ia,{}).get('slug','mundo')
    cat_id = obtener_id_categoria_wp(slug_cat)
    if not cat_id: cat_id = obtener_id_categoria_wp('mundo'); slug_cat = 'mundo'
    categorias_ids = [cat_id] if cat_id else []

    imagen_id = subir_imagen_wp(imagen_path, titulo_final,
        alt_text=f"{frase_clave} - {titulo_final}"[:125],
        frase_clave=frase_clave, meta_descripcion=meta_desc)
    if not imagen_id: return None, None, None

    palabras_art = len(_texto_plano(contenido_html).split())
    minutos_lect = max(2, round(palabras_art / 200))
    barra_lectura = f'<p style="font-size:0.82em;color:#6b7280;margin:0 0 20px 0;">🕐 Tiempo de lectura: <strong>{minutos_lect} min</strong></p>'

    nombre_medio = 'Fuente externa'
    try:
        dominio = re.sub(r'^(www\.|m\.)','', urlparse(fuente_url).netloc.lower())
        mapa = {'infobae.com':'Infobae','bbc.com':'BBC Mundo','cnn.com':'CNN','reuters.com':'Reuters','elpais.com':'El Pais','dw.com':'DW'}
        for dom,nombre in mapa.items():
            if dom in dominio: nombre_medio = nombre; break
        else:
            partes = dominio.split('.')
            nombre_medio = partes[-2].capitalize() if len(partes) >= 2 else dominio
    except: pass

    contenido_final = f"""
{barra_lectura}
{contenido_html}
<hr>
<p><strong>Fuente:</strong> <a href="{fuente_url}" target="_blank" rel="noopener">{nombre_medio}</a></p>
<p><em>Informacion verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
"""

    post_data = {
        'title':          titulo_final,
        'slug':           slug_post,
        'content':        contenido_final,
        'excerpt':        meta_desc,
        'status':         'draft',
        'featured_media': imagen_id,
        'categories':     categorias_ids,
        'tags':           tags_ids,
    }

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",json=post_data,auth=(WP_USER,WP_APP_PASSWORD),timeout=30).json()
        if 'id' in r:
            post_id = r['id']
            url_articulo = r.get('link', f"{WP_URL}/?p={post_id}")
            log(f"BORRADOR creado: {WP_URL}/wp-admin/post.php?post={post_id}&action=edit",'exito')
            try:
                rm_payload = {'objectID':post_id,'objectType':'post',
                    'meta':{'rank_math_focus_keyword':frase_clave,'rank_math_title':titulo_seo,
                            'rank_math_description':meta_desc,'rank_math_robots':['index','follow']}}
                r_rm = requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta",json=rm_payload,auth=(WP_USER,WP_APP_PASSWORD),timeout=10)
                if r_rm.status_code in (200,201): log(f"Rank Math SEO guardado",'exito')
            except: pass
            return url_articulo, slug_cat
        else: log(f"Error WP: {r.get('message','desconocido')}",'error')
    except Exception as e: log(f"Excepcion WP: {e}",'error')
    return None, None

# ══════════════════════════════════════════════════════════
# FUENTES
# ══════════════════════════════════════════════════════════
def extraer_contenido(url):
    if not url: return None
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        for e in s(['script','style','nav','header','footer']): e.decompose()
        for selector in ['article','[class*="article-content"]','[class*="entry-content"]','[class*="post-content"]']:
            art = s.select_one(selector)
            if art:
                ps = [p for p in art.find_all('p') if len(p.get_text()) > 40]
                if len(ps) >= 2:
                    txt = ' '.join([limpiar_texto(p.get_text()) for p in ps])
                    if len(txt) > 200: return txt[:5000]
        return None
    except: return None

def deduplicar_batch(noticias):
    urls_vistas = set(); titulos_vistos = []; resultado = []
    for n in noticias:
        url_n = normalizar_url(n.get('url',''))
        titulo = n.get('titulo','')
        if not url_n or not titulo: continue
        if url_n in urls_vistas: continue
        if any(similitud_titulos(titulo,t) > 0.78 for t in titulos_vistos): continue
        urls_vistas.add(url_n); titulos_vistos.append(titulo); resultado.append(n)
    return resultado

def obtener_rss_ampliado():
    fuentes = [
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/','Infobae America'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/economia/','Infobae Economia'),
        ('https://www.eluniversal.com.mx/rss.xml','El Universal MX'),
        ('https://www.lanacion.com.ar/arc/outboundfeeds/rss/','La Nacion AR'),
        ('https://www.clarin.com/rss/elmundo/','Clarin Mundo'),
        ('https://www.eltiempo.com/rss/portada.xml','El Tiempo CO'),
        ('https://elcomercio.pe/arcio/rss/','El Comercio PE'),
        ('https://efectococuyo.com/feed/','Efecto Cocuyo VE'),
        ('https://feeds.xataka.com/xataka','Xataka'),
        ('https://hipertextual.com/feed','Hipertextual'),
        ('http://feeds.bbci.co.uk/mundo/rss.xml','BBC Mundo'),
        ('https://www.dw.com/es/ultimas-noticias/s-30689792/rss','DW ES'),
        ('https://feeds.france24.com/es/','France 24 ES'),
        ('https://www.espn.com.mx/rss/deportes.xml','ESPN Deportes'),
        ('https://e00-marca.uecdn.es/rss/portada.xml','Marca'),
        ('https://www.emol.com/rss/','Emol Chile'),
        ('https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml','Cooperativa CL'),
        ('https://www.cnnchile.com/feed/','CNN Chile'),
    ]
    noticias = []
    for url_feed, nombre in fuentes:
        try:
            r = requests.get(url_feed, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200: continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries: continue
            for e in feed.entries[:10]:
                t = e.get('title','')
                if not t: continue
                t = re.sub(r'\s*-\s*[^-]*$','',t)
                l = e.get('link','')
                if not l: continue
                d = re.sub(r'<[^>]+>','',e.get('summary','') or e.get('description',''))
                img = None
                if hasattr(e,'media_content') and e.media_content: img = e.media_content[0].get('url')
                if not img:
                    for enc in getattr(e,'enclosures',[]):
                        if enc.get('type','').startswith('image'): img = enc.get('href') or enc.get('url'); break
                titulo_limpio = limpiar_texto(t)
                desc_limpia = limpiar_texto(d)
                relevancia = calcular_relevancia_evergreen(titulo_limpio, desc_limpia)
                noticias.append({'titulo':titulo_limpio,'descripcion':desc_limpia,'url':l,'imagen':img,
                                 'fuente':f"RSS:{nombre}",'fecha':e.get('published'),
                                 'relevancia':relevancia,'tema':detectar_tema(titulo_limpio,desc_limpia)})
        except Exception as e: log(f"RSS error ({nombre}): {e}",'advertencia')
    log(f"RSS: {len(noticias)} noticias",'info')
    return noticias

def obtener_newsapi_evergreen():
    if not NEWS_API_KEY: return []
    queries = [
        'descubrimiento arqueologico America Latina 2026',
        'civilizacion antigua misterio hallazgo cientifico',
        'NASA espacio descubrimiento 2026',
        'inteligencia artificial impacto America Latina',
        'innovacion tecnologica Chile Argentina Mexico 2026',
        'economia LATAM tendencias inflacion inversion',
        'litio cobre recursos naturales Sudamerica',
        'avance medico cancer tratamiento 2026',
        'salud publica America Latina investigacion',
        'longevidad ciencia antienvejecimiento',
        'BRICS geopolitica America Latina',
        'acuerdo comercial tratado Latinoamerica',
        'cultura latinoamericana cine musica 2026',
        'Amazonia cambio climatico glaciares',
        'energia renovable solar eolica LATAM',
        'criptomoneda fintech America Latina regulacion',
    ]
    noticias = []
    for q in queries:
        try:
            r = requests.get('https://newsapi.org/v2/everything',
                params={'apiKey':NEWS_API_KEY,'q':q,'language':'es','sortBy':'relevancy','pageSize':5},
                timeout=15).json()
            if r.get('status') == 'ok':
                for a in r.get('articles',[]):
                    t = a.get('title','')
                    if not t or '[Removed]' in t: continue
                    d = a.get('description','')
                    titulo_limpio = limpiar_texto(t)
                    desc_limpia = limpiar_texto(d)
                    relevancia = calcular_relevancia_evergreen(titulo_limpio, desc_limpia)
                    noticias.append({'titulo':titulo_limpio,'descripcion':desc_limpia,
                                     'url':a.get('url',''),'imagen':a.get('urlToImage'),
                                     'fuente':f"NewsAPI:{a.get('source',{}).get('name','')}",
                                     'fecha':a.get('publishedAt'),'relevancia':relevancia,
                                     'tema':detectar_tema(titulo_limpio,desc_limpia)})
        except Exception as e: log(f"NewsAPI evergreen error: {e}",'advertencia')
    log(f"NewsAPI evergreen: {len(noticias)} noticias",'info')
    return noticias

# ══════════════════════════════════════════════════════════
# MAIN V20
# ══════════════════════════════════════════════════════════
def main():
    print("\n" + "="*60)
    print(f"VERDAD HOY BOT - {VERSION_BOT}")
    print(f"  Modo: 100% EVERGREEN — todo en BORRADOR")
    print(f"  Borradores/dia: {MAX_BORRADORES_DIA}")
    print(f"  Rotacion equitativa por paises")
    print(f"  Pinterest: {'ACTIVO' if PINTEREST_TOKEN else 'SIN TOKEN'}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    if not puede_publicar_wp():
        log("Cuota diaria completada",'info')
        return None

    h = cargar_historial()
    rotacion = cargar_rotacion()
    paises_ciclo = seleccionar_paises_ciclo(rotacion, n=MAX_BORRADORES_DIA)
    log(f"Paises de este ciclo: {', '.join(paises_ciclo)}",'info')

    noticias = []
    noticias.extend(obtener_rss_ampliado())
    if NEWS_API_KEY: noticias.extend(obtener_newsapi_evergreen())
    if not noticias: log("ERROR: Sin noticias",'error'); return None

    noticias_filtradas = []
    for n in noticias:
        tema = n.get('tema') or detectar_tema(n.get('titulo',''), n.get('descripcion',''))
        if not es_evergreen(tema): continue
        es_spam, _ = es_contenido_spam(n.get('titulo',''), n.get('descripcion',''))
        if es_spam: continue
        n['tema'] = tema
        noticias_filtradas.append(n)

    log(f"Noticias evergreen filtradas: {len(noticias_filtradas)}",'info')
    noticias_filtradas = deduplicar_batch(noticias_filtradas)
    noticias_filtradas.sort(key=lambda x: x.get('relevancia',0), reverse=True)

    candidatas_por_pais = {pais: [] for pais in paises_ciclo}
    asignadas = set()

    for pais in paises_ciclo:
        for n in noticias_filtradas:
            url = n.get('url','')
            titulo = n.get('titulo','')
            if url in asignadas: continue
            if not noticia_es_de_pais(titulo, n.get('descripcion',''), pais): continue
            dup, _ = noticia_ya_publicada(h, url, titulo, n.get('descripcion',''))
            if dup: continue
            candidatas_por_pais[pais].append(n)
            asignadas.add(url)
            if len(candidatas_por_pais[pais]) >= 3: break

    for pais in paises_ciclo:
        if not candidatas_por_pais[pais]:
            log(f"Sin candidatas para '{pais}' — usando pool general",'advertencia')
            for n in noticias_filtradas:
                url = n.get('url','')
                if url in asignadas: continue
                dup, _ = noticia_ya_publicada(h, url, n.get('titulo',''), n.get('descripcion',''))
                if dup: continue
                candidatas_por_pais[pais].append(n)
                asignadas.add(url)
                break

    borradores_publicados = 0
    paises_publicados = []

    for pais in paises_ciclo:
        if borradores_publicados >= MAX_BORRADORES_DIA: break
        candidatas = candidatas_por_pais.get(pais, [])
        if not candidatas: log(f"Sin candidata para '{pais}'",'advertencia'); continue

        nt = candidatas[0]
        titulo = nt.get('titulo','')
        url    = nt.get('url','')
        desc   = nt.get('descripcion','')
        tema   = nt.get('tema','general')

        log(f"\n[{pais.upper()}] {titulo[:70]}",'info')
        log(f"  Tema: {tema} | Relevancia: {nt.get('relevancia',0)}",'info')

        cont_web = extraer_contenido(url)
        if cont_web and len(cont_web) >= 500: contenido_ok = cont_web
        elif desc and len(desc) >= 300: contenido_ok = desc
        elif cont_web and len(cont_web) >= 200: contenido_ok = (cont_web + ' ' + (desc or ''))
        else: log("  Contenido insuficiente",'advertencia'); continue

        imagen = None
        if nt.get('imagen'): imagen = descargar_imagen(nt['imagen'])
        if not imagen:
            img_url = extraer_imagen_web(url)
            if img_url: imagen = descargar_imagen(img_url)
        if not imagen: imagen = crear_imagen_titulo(titulo, tema)
        if not imagen: log("  Sin imagen",'advertencia'); continue

        url_wp, slug_cat = publicar_borrador_wordpress(
            titulo=titulo, contenido=contenido_ok, categoria=tema,
            imagen_path=imagen, fuente_url=url, pais_foco=pais)

        try:
            if imagen and os.path.exists(imagen): os.remove(imagen)
        except: pass

        if url_wp:
            borradores_publicados += 1
            paises_publicados.append(pais)

            # Pinterest lo maneja bot_pinterest_diferido.py — no se publica aqui
            registrar_borrador()
            h['estadisticas']['total_borradores'] = h['estadisticas'].get('total_borradores',0) + 1
            h = guardar_en_historial(h, url, titulo, (desc+' '+contenido_ok[:400]).strip())
        else:
            log(f"  No se pudo publicar para '{pais}'",'advertencia')

    if paises_publicados:
        registrar_paises_usados(rotacion, paises_publicados)

    datos_cuotas = cargar_json(CUOTAS_PATH, {})
    stats = h.get('estadisticas',{})
    print(f"\n{'='*50}")
    log(f"RESUMEN {VERSION_BOT}:",'exito')
    log(f"  Borradores hoy:    {datos_cuotas.get('borradores',0)}/{MAX_BORRADORES_DIA}",'info')
    log(f"  Paises publicados: {', '.join(paises_publicados) if paises_publicados else 'ninguno'}",'info')
    log(f"  Total borradores:  {stats.get('total_borradores',0)}",'info')
    log(f"  Total Pinterest:   {stats.get('total_pinterest',0)}",'info')
    log(f"  Ciclo rotacion:    #{rotacion.get('ciclo',0)}",'info')

    if borradores_publicados > 0:
        log("Hacer git push de los JSON de estado",'advertencia')
        return True
    return False

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0)
    except Exception as e:
        log(f"Error critico: {e}",'error')
        import traceback
        traceback.print_exc()
        exit(1)
