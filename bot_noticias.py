#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias - V21.0.0
CAMBIOS VS V20:
  - MAX_BORRADORES_DIA = 1 (1 por corrida, 3 corridas/dia via workflow)
  - Títulos MIXTOS: mitad preguntas (¿Por qué...? ¿Cómo...?) + mitad afirmaciones con número
  - Imagen destacada = descargada de fuente + watermark (generada como fallback)
  - Imágenes adicionales dentro del artículo (hasta 3 temáticas via DuckDuckGo)
  - Horarios workflow: 07:00, 13:00, 19:00 UTC (optimizado LATAM)
  - Pinterest manejado por bot_pinterest_diferido.py
"""
VERSION_BOT = "V21.0.0"

import requests, feedparser, re, hashlib, json, os, random, time, unicodedata
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse

MAX_BORRADORES_DIA = 1   # 1 por corrida — el workflow corre 3 veces al día
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
    r'^\s*ultima hora\s*$', r'^\s*breaking news\s*$',
    r'^\s*noticias de hoy\s*$', r'^\s*\d+\s*$',
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

_cache_categorias_wp    = {}
_cache_tags_wp          = {}
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
# TÍTULOS MIXTOS V21 — preguntas + afirmaciones con número
# ══════════════════════════════════════════════════════════
# El turno (par/impar según hora UTC) decide el formato
def es_turno_pregunta():
    """Par = pregunta, impar = afirmación con número."""
    return datetime.now(timezone.utc).hour % 2 == 0

PREFIJOS_PREGUNTA = [
    '¿Por qué', '¿Cómo funciona', '¿Qué es', '¿Cuál es',
    '¿Por qué existe', '¿Cómo afecta', '¿Qué pasa con',
]
SUFIJOS_AFIRMACION = [
    '{n} razones clave para entender',
    '{n} datos que revelan',
    '{n} cosas que no sabías sobre',
    '{n} hechos históricos sobre',
    '{n} causas reales de',
    '{n} consecuencias de',
    '{n} verdades sobre',
]

def formato_titulo_pregunta(keyword, categoria):
    prefijo = random.choice(PREFIJOS_PREGUNTA)
    complementos = {
        'salud':         'y cómo proteger tu salud',
        'tecnologia':    'y cómo cambia tu vida',
        'historia':      'y qué nos dejó',
        'misterios':     'y qué dice la ciencia',
        'economia':      'y cómo te afecta en LATAM',
        'geopolitica':   'y por qué importa en América Latina',
        'medio_ambiente':'y qué podemos hacer',
        'ciencia':       'y qué significa para el futuro',
        'innovacion':    'y cuál es su impacto real',
        'cultura':       'y por qué es importante',
        'latinoamerica': 'en América Latina hoy',
        'politica':      'y qué cambia para los ciudadanos',
    }
    comp = complementos.get(categoria, 'en América Latina')
    return f"{prefijo} {keyword} {comp}"

def formato_titulo_afirmacion(keyword, categoria):
    n = random.choice([3, 5, 7, 10])
    sufijo = random.choice(SUFIJOS_AFIRMACION).format(n=n)
    año = datetime.now().year
    power = random.choice(['clave', 'que debes saber', 'reveladores', 'históricos', 'esenciales'])
    return f"{sufijo} {keyword}: {n} {power} en {año}"

def generar_titulo_mixto(keyword, categoria):
    """Alterna entre pregunta y afirmación con número según la hora."""
    if es_turno_pregunta():
        return formato_titulo_pregunta(keyword, categoria)
    else:
        return formato_titulo_afirmacion(keyword, categoria)

# ══════════════════════════════════════════════════════════
# ROTACION DE PAISES V21
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

def seleccionar_paises_ciclo(rotacion, n=1):
    usados_hoy = set(rotacion.get('paises_usados_hoy',[]))
    conteo = rotacion.get('conteo_por_pais',{})
    todos = list(POOL_PAISES.keys())
    candidatos = [p for p in todos if p not in usados_hoy]
    if not candidatos: candidatos = todos
    def score(pais):
        veces = conteo.get(pais, 0)
        peso  = POOL_PAISES[pais]['peso']
        return (peso / (veces + 1)) * random.uniform(0.8, 1.2)
    candidatos_ord = sorted(candidatos, key=score, reverse=True)
    return candidatos_ord[:n]

def registrar_paises_usados(rotacion, paises):
    rotacion['paises_usados_hoy'] = list(set(rotacion.get('paises_usados_hoy',[]))|set(paises))
    rotacion['ciclo'] = rotacion.get('ciclo',0) + 1
    conteo = rotacion.get('conteo_por_pais',{})
    for p in paises: conteo[p] = conteo.get(p,0) + 1
    rotacion['conteo_por_pais'] = conteo
    guardar_json(ROTACION_PAISES_PATH, rotacion)

# ══════════════════════════════════════════════════════════
# DETECCION DE TEMA
# ══════════════════════════════════════════════════════════
def detectar_tema(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(p in txt for p in ["terremoto","sismo","huracan","inundacion","tsunami","erupcion"]): return 'desastre'
    if any(p in txt for p in ["asesinato","homicidio","narcotrafico","cartel","crimen organizado","feminicidio","masacre"]): return 'crimen'
    if any(p in txt for p in ["guerra","bombardeo","misil","conflicto armado","invasion","tropas","ofensiva militar"]): return 'guerra'
    if any(p in txt for p in ["misterio","arqueologia","civilizacion perdida","artefacto antiguo","oopart","manuscrito",
                               "enigma historico","historia antigua","tumba","piramide","ruinas antiguas","fosil","mayas","incas","aztecas"]): return 'misterios'
    if any(p in txt for p in ["historia de","siglo xix","siglo xx","segunda guerra","primera guerra","revolucion",
                               "colonia","independencia","dictadura","operacion condor","guerra fria","archivo historico"]): return 'historia'
    if any(p in txt for p in ["geopolitica","brics","otan","nato","g7","g20","acuerdo comercial","tratado internacional",
                               "diplomacia","relaciones internacionales","potencia mundial"]): return 'geopolitica'
    if any(p in txt for p in ["innovacion","startup","emprendimiento","fintech","biotech","nanotecnologia",
                               "biotecnologia","fusion nuclear","computacion cuantica","quantum"]): return 'innovacion'
    if any(p in txt for p in ["inteligencia artificial","chatgpt","openai","gemini","robot","ciberataque","hackeo",
                               "elon musk","spacex","starlink","nvidia","blockchain","criptomoneda","machine learning"]): return 'tecnologia'
    if any(p in txt for p in ["inflacion","recesion","bolsa de valores","mercado financiero","dolar","fmi",
                               "banco central","crisis economica","aranceles","pib","wall street","deficit fiscal"]): return 'economia'
    if any(p in txt for p in ["cambio climatico","calentamiento global","sequia","incendio forestal",
                               "contaminacion","medio ambiente","biodiversidad","extincion","amazonia","glaciar"]): return 'medio_ambiente'
    if any(p in txt for p in ["cancer","enfermedad","pandemia","vacuna","virus","salud publica","oms","epidemia",
                               "medicamento","alzheimer","diabetes","salud mental","longevidad"]): return 'salud'
    if any(p in txt for p in ["descubrimiento cientifico","nasa","espacio","agujero negro","exoplaneta",
                               "astronomia","telescopio","marte","luna","fisica cuantica","adn","premio nobel"]): return 'ciencia'
    if any(p in txt for p in ["futbol","copa libertadores","champions league","mundial","olimpiadas",
                               "nba","formula 1","messi","cristiano ronaldo","seleccion"]): return 'deportes'
    if any(p in txt for p in ["pelicula","oscar","grammy","netflix","disney","marvel","anime","musica",
                               "concierto","taylor swift","bad bunny","shakira","cultura pop"]): return 'entretenimiento'
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
        log(f"Cuota corrida alcanzada ({total}/{MAX_BORRADORES_DIA}) — próxima corrida en siguiente horario",'advertencia')
        return False
    return True

def registrar_borrador():
    datos = cargar_json(CUOTAS_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    # IMPORTANTE: No resetear por fecha — cada corrida es independiente
    # El reset lo hace el workflow al correr en nueva hora
    datos['fecha'] = hoy
    datos['borradores'] = datos.get('borradores', 0) + 1
    datos['ultima_corrida'] = datetime.now(timezone.utc).isoformat()
    guardar_json(CUOTAS_PATH, datos)

def ya_corrio_esta_hora():
    """Evita doble publicación si el workflow se ejecuta dos veces en la misma hora."""
    datos = cargar_json(CUOTAS_PATH, {})
    ultima = datos.get('ultima_corrida','')
    if not ultima: return False
    try:
        dt_ultima = datetime.fromisoformat(ultima)
        if dt_ultima.tzinfo is None: dt_ultima = dt_ultima.replace(tzinfo=timezone.utc)
        ahora = datetime.now(timezone.utc)
        # Si corrió hace menos de 50 minutos en la misma hora UTC = ya corrió
        diff = ahora - dt_ultima
        if diff.total_seconds() < 3000 and dt_ultima.hour == ahora.hour:
            return True
    except: pass
    return False

# ══════════════════════════════════════════════════════════
# IMÁGENES V21 — descarga + múltiples imágenes en artículo
# ══════════════════════════════════════════════════════════
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
        from PIL import Image as PILImage
        overlay = PILImage.new('RGBA', img.size, (0,0,0,0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([x-padding,y-padding,x+txt_w+padding,y+txt_h+padding],radius=6,fill=(0,0,0,180))
        img = img.convert('RGBA')
        img = PILImage.alpha_composite(img, overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((x+1,y+1), texto_wm, font=font_wm, fill=(0,0,0,200))
        draw.text((x,y), texto_wm, font=font_wm, fill='#f5c518')
        return img
    except: return img

def descargar_imagen(url, min_w=400, min_h=250):
    """Descarga y procesa una imagen. Retorna path local o None."""
    if not url: return None
    for bloqueo in ['google.com','gstatic.com','facebook.com','logo','icon','favicon','1x1','pixel','blank']:
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
        if w < min_w or h < min_h: return None
        if img.mode in ('RGBA','P','LA'): img = img.convert('RGB')
        if w < 1200: img = img.resize((1200, int(h*(1200/w))), Image.LANCZOS)
        elif w > 1600: img = img.resize((1600, int(h*(1600/w))), Image.LANCZOS)
        img = agregar_watermark(img)
        p = f'/tmp/img_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=92, optimize=True)
        if os.path.getsize(p) < 3000: os.remove(p); return None
        return p
    except: return None

def extraer_imagen_og(url):
    """Extrae og:image o twitter:image de la página fuente."""
    if not url: return None
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for prop in ['og:image','twitter:image','og:image:secure_url']:
            tag = s.find('meta', property=prop) or s.find('meta', attrs={'name':prop})
            if tag:
                img = tag.get('content','').strip()
                if img and img.startswith('http') and not any(b in img.lower() for b in ['google','logo','icon']):
                    return img
        # Buscar primera imagen grande en el artículo
        for img_tag in s.find_all('img', src=True)[:10]:
            src = img_tag.get('src','')
            if src.startswith('http') and not any(b in src.lower() for b in ['logo','icon','avatar']):
                return src
    except: pass
    return None

def buscar_imagenes_duckduckgo(query, max_resultados=5):
    """Busca imágenes en DuckDuckGo. Retorna lista de URLs."""
    urls = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp_init = requests.get('https://duckduckgo.com/', params={'q': query}, headers=headers, timeout=10)
        vqd_match = re.search(r'vqd=([\d-]+)', resp_init.text)
        if not vqd_match: return urls
        vqd = vqd_match.group(1)
        resp_img = requests.get('https://duckduckgo.com/i.js',
                                params={'q': query, 'vqd': vqd, 'f': ',,,,,', 'p': '1', 'v7exp': 'a'},
                                headers=headers, timeout=10)
        data = resp_img.json()
        for r in data.get('results', [])[:max_resultados * 3]:
            img_url = r.get('image', '')
            w = r.get('width', 0)
            h = r.get('height', 0)
            if not img_url: continue
            if w < 400 or h < 280: continue
            if any(b in img_url.lower() for b in ['logo','icon','avatar','thumb','favicon','1x1']): continue
            urls.append(img_url)
            if len(urls) >= max_resultados: break
    except Exception as e:
        log(f"DuckDuckGo imagen fallo: {e}",'debug')
    return urls

def obtener_imagenes_articulo(fuente_url, titulo, keyword, categoria, n_extra=2):
    """
    Obtiene la imagen destacada + imágenes adicionales para el artículo.
    
    Orden de prioridad imagen destacada:
    1. og:image de la fuente (descargada + watermark)
    2. Imagen generada con título + categoría

    Para imágenes adicionales (dentro del artículo):
    - Búsqueda DuckDuckGo por keyword + categoría
    
    Retorna: (img_destacada_path, [img_adicional_path1, img_adicional_path2, ...])
    """
    # ── 1. Imagen destacada ──────────────────────────────
    img_destacada = None
    log("Buscando imagen destacada de la fuente...",'info')
    
    og_url = extraer_imagen_og(fuente_url)
    if og_url:
        log(f"og:image encontrada: {og_url[:60]}",'info')
        img_destacada = descargar_imagen(og_url)
    
    if not img_destacada:
        log("Sin og:image — generando imagen con título",'advertencia')
        img_destacada = crear_imagen_titulo(titulo, categoria)

    # ── 2. Imágenes adicionales vía DuckDuckGo ───────────
    imagenes_adicionales = []
    queries_por_cat = {
        'salud':         [f"{keyword} salud medicina", f"enfermedad tratamiento medico"],
        'ciencia':       [f"{keyword} ciencia descubrimiento", f"investigacion cientifica laboratorio"],
        'historia':      [f"{keyword} historia antigua civilizacion", f"arqueologia hallazgo historico"],
        'misterios':     [f"{keyword} misterio arqueologia", f"fenomeno inexplicable ciencia"],
        'tecnologia':    [f"{keyword} tecnologia inteligencia artificial", f"innovacion digital futuro"],
        'innovacion':    [f"{keyword} innovacion startup tecnologia", f"futuro tecnologico"],
        'economia':      [f"{keyword} economia finanzas latinoamerica", f"mercado dinero inversion"],
        'geopolitica':   [f"{keyword} geopolitica mapa conflicto", f"diplomacia relaciones internacionales"],
        'medio_ambiente':[f"{keyword} naturaleza medio ambiente", f"cambio climatico ecosistema"],
        'cultura':       [f"{keyword} cultura latinoamerica arte", f"tradicion patrimonio"],
        'latinoamerica': [f"{keyword} america latina pais", f"latinoamerica ciudad"],
        'politica':      [f"{keyword} politica gobierno", f"democracia ciudadanos"],
        'deportes':      [f"{keyword} deporte competencia", f"atletismo campeonato"],
        'entretenimiento':[f"{keyword} entretenimiento cultura pop", f"cine musica latinoamerica"],
    }
    queries = queries_por_cat.get(categoria, [f"{keyword} {categoria}", f"{keyword} ilustracion"])
    
    urls_encontradas = []
    for q in queries[:2]:
        urls_encontradas.extend(buscar_imagenes_duckduckgo(q, max_resultados=3))
    
    urls_encontradas = list(dict.fromkeys(urls_encontradas))  # deduplicar

    for img_url in urls_encontradas[:n_extra * 2]:
        if len(imagenes_adicionales) >= n_extra: break
        if og_url and img_url == og_url: continue  # no repetir la destacada
        path = descargar_imagen(img_url, min_w=350, min_h=220)
        if path:
            imagenes_adicionales.append(path)
            log(f"Imagen adicional {len(imagenes_adicionales)}: OK",'info')

    log(f"Imágenes: 1 destacada + {len(imagenes_adicionales)} adicionales",'exito')
    return img_destacada, imagenes_adicionales

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
# IA V21 — PROMPT EVERGREEN + TÍTULOS MIXTOS
# ══════════════════════════════════════════════════════════
def reescribir_noticia_v21(titulo, contenido, categoria='general', pais_foco='global',
                            feedback_correccion=None, titulo_sugerido=None):
    api_key = OPENAI_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY or GEMINI_API_KEY
    if not api_key: return None

    TITULOS_BOX = [
        ('⚡','Lo que debes saber','#ff6b35','#fff3e0'),
        ('📋','Resumen rápido','#0891b2','#e0f2fe'),
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

    # Instrucción de formato de título según turno
    if es_turno_pregunta():
        instruccion_titulo = (
            "FORMATO TÍTULO (turno PREGUNTA): El título debe ser una pregunta directa. "
            "Ejemplos: '¿Por qué el alzheimer afecta más a las mujeres en LATAM?', "
            "'¿Cómo funciona la IA que reemplaza médicos en 2026?', "
            "'¿Qué es el litio y por qué Chile lo necesita proteger?'. "
            "Siempre debe tener signos de pregunta ¿? y ser max 60 chars."
        )
    else:
        instruccion_titulo = (
            "FORMATO TÍTULO (turno AFIRMACIÓN): El título debe ser una afirmación con número. "
            "Ejemplos: '5 causas reales del alzheimer que debes conocer en 2026', "
            "'7 verdades sobre la IA que cambiarán América Latina este año', "
            "'3 razones clave por las que el litio define el futuro de Chile'. "
            "Siempre debe tener un número y una power word. Max 60 chars."
        )

    titulo_hint = f"\nSUGERENCIA DE TÍTULO BASE: {titulo_sugerido}" if titulo_sugerido else ""

    bloque_feedback = ""
    if feedback_correccion:
        problemas_txt = '\n'.join(f'  - {p}' for p in feedback_correccion)
        bloque_feedback = f"CORRECCIÓN OBLIGATORIA:\n{problemas_txt}\n"

    bloque_contexto_web = ""
    if not feedback_correccion:
        fuentes_web = buscar_contexto_web(titulo)
        if fuentes_web:
            fuentes_txt = "\n\n".join(f"Fuente {i+1}: {f['title']}\n{f['content']}" for i,f in enumerate(fuentes_web))
            bloque_contexto_web = f"CONTEXTO ADICIONAL:\n{fuentes_txt}\n"

    prompt = f"""Eres Editor Jefe Digital de VerdadHoy.com. Tono: directo, claro, periodístico. Audiencia: Chile, Argentina, México.
PAÍS/REGIÓN DE FOCO: {nombre_pais} — ángulo de impacto en {nombre_pais} y América Latina.

MISIÓN: contenido EVERGREEN. Útil hoy y en 6 meses. NO es noticia del día. ES artículo de fondo.

{instruccion_titulo}
{titulo_hint}

REGLA CLAVE — IGNORAR EL ÁNGULO NOTICIOSO:
Si la fuente es una noticia del día, IGNORA la coyuntura y usa el TEMA SUBYACENTE.
Ejemplo: "EEUU pausa visas" → "¿Cómo funciona el sistema de visas de EEUU para latinoamericanos?"
Ejemplo: "Sube el dólar en Argentina" → "5 formas de proteger tus ahorros cuando sube el dólar"
Ejemplo: "Nuevo tratamiento contra cáncer" → "¿Qué avances existen contra el cáncer en 2026?"

EXTENSIÓN MÍNIMA: 700 palabras. Incluye SIEMPRE:
- Explicación de fondo (no solo la noticia)
- Al menos 3 cifras o datos verificables
- Ángulo específico para América Latina
- Sección de qué esperar o qué hacer al respecto

FUENTE/TEMA BASE:
Título: {titulo}
Contenido: {contenido[:2500]}
Categoría: {categoria}

{bloque_contexto_web}

REGLAS SEO:
META: "[KEYWORD] — [dato con número]. [consecuencia]. [cierre]" — 150-160 chars exacto

ESTRUCTURA HTML:
<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este artículo</p>
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

<p>[párrafo introductorio — keyword en primeras 40 palabras]</p>

<h2 id="seccion-1">[H2 con keyword]</h2>
<p>[desarrollo con dato]</p>
[IMAGEN_ADICIONAL_1]

<h2 id="seccion-2">[H2 con dato numérico]</h2>
<p>[desarrollo con cifra]</p>

<p style="border-left:3px solid #f59e0b;padding:10px 14px;margin:16px 0;background:#fffbeb;font-style:italic;color:#374151;">[editorial 2-3 oraciones con keyword]</p>

<blockquote style="border-left:3px solid #e5e7eb;padding:12px 16px;margin:20px 0;background:#f9fafb;font-style:italic;color:#4b5563;">
"[cita o dato estadístico verificable con número y fuente]"
</blockquote>

<h2 id="seccion-3">[H2: impacto en América Latina]</h2>
<p>[impacto LATAM con 2 países]</p>
[IMAGEN_ADICIONAL_2]

<h2 id="seccion-4">[H2: futuro / conclusión]</h2>
<p>[proyección futura con año. Pregunta al lector al final.]</p>

[ENLACES_INTERNOS]

CHECKLIST:
- Keyword en título (primeras 3 palabras o en pregunta)
- 4 H2 con id="seccion-N"
- Tabla de contenidos
- Box resumen
- Blockquote con dato numérico
- 4 transiciones: sin embargo, además, por otro lado, en consecuencia
- Meta 150-160 chars
- Placeholders [IMAGEN_ADICIONAL_1] y [IMAGEN_ADICIONAL_2] en el HTML donde corresponde
- Mínimo 750 palabras

{bloque_feedback}

RESPONDE SOLO JSON sin markdown:
{{"titulo_seo":"según formato del turno max 60 chars","slug":"max-50-chars","meta_descripcion":"keyword primero 150-160 chars","contenido_html":"HTML completo con placeholders [IMAGEN_ADICIONAL_1] y [IMAGEN_ADICIONAL_2]","keyword_principal":"2-3 palabras","keywords_secundarias":["kw2","kw3","kw4","kw5"],"categoria":"tecnologia|ciencia|salud|historia|misterios|geopolitica|economia|politica|medio_ambiente|innovacion|cultura|entretenimiento|deportes|latinoamerica|mundo|general","parrafo_nativo":"texto plano parrafo nativo","descripcion_pinterest":"100-150 chars con hashtags"}}"""

    def _llamar_api(url_api, headers, modelo, payload):
        try:
            resp = requests.post(url_api, headers=headers, json=payload, timeout=60)
        except Exception as e:
            log(f"IA error de red: {e}",'error'); return None
        try: resp_json = resp.json()
        except: log(f"IA respuesta no JSON (HTTP {resp.status_code})",'error'); return None
        if "choices" not in resp_json:
            err = resp_json.get("error",{})
            msg = err.get("message",str(resp_json)[:200]) if isinstance(err,dict) else str(err)[:200]
            log(f"IA error: {msg}",'error'); return None
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
        if cat_ia not in categorias_validas:
            resultado['categoria'] = categoria if categoria in categorias_validas else 'general'
        log(f"IA OK — Título: {resultado.get('titulo_seo','')[:60]} | Cat: {resultado.get('categoria')}",'info')
        return resultado
    except Exception as e:
        log(f"reescribir_noticia_v21 error: {e}",'advertencia')
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
            ' Toda la información actualizada sobre este tema en Verdad Hoy.',
            ' Lo que necesitas saber en Verdad Hoy.',
            ' Análisis completo y actualizado en Verdad Hoy.',
        ]
        for ext in extensiones:
            candidato = meta_base + ext
            if 150 <= len(candidato) <= 160: meta = candidato; break
        if len(meta) < 150: meta = (meta.rstrip('.') + ' — Análisis completo en Verdad Hoy.')[:160]
    resultado_ia['meta_descripcion'] = meta
    return resultado_ia

def postprocesar_titulo(resultado_ia):
    titulo = resultado_ia.get('titulo_seo','').strip()
    if not titulo: return resultado_ia
    # Para preguntas: verificar que tenga ¿?
    if es_turno_pregunta():
        if not titulo.startswith('¿'):
            titulo = '¿' + titulo
        if not titulo.endswith('?'):
            titulo = titulo.rstrip('.') + '?'
    else:
        # Para afirmaciones: verificar número y power word
        if not re.search(r'\d', titulo) and len(titulo) <= 45:
            titulo = f"{titulo}: {datetime.now().year}"
        if not any(pw in titulo.lower() for pw in POWER_WORDS_LISTA) and len(titulo) <= 47:
            titulo = f"{titulo}, clave"
    resultado_ia['titulo_seo'] = titulo[:60]
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
    limite_alto = 3.0 if kw_palabras == 1 else 5.0
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
    html_nuevo = contenido_html
    for i, pos in enumerate(reversed(candidatas[1:])):
        if i >= sobran: break
        sinonimo = sinonimos[i % len(sinonimos)]
        if html_nuevo[pos:pos+1].isupper(): sinonimo = sinonimo.capitalize()
        fin = pos + len(keyword)
        html_nuevo = html_nuevo[:pos] + sinonimo + html_nuevo[fin:]
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
            font_badge  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
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
        p = f'/tmp/gen_{generar_hash(titulo)}.jpg'
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

def subir_imagen_adicional_wp(imagen_path, titulo, keyword, numero):
    """Sube una imagen adicional a WP y retorna (media_id, source_url)."""
    if not imagen_path or not os.path.exists(imagen_path): return None, None
    try:
        nombre = f"verdadhoy-sec{numero}-{generar_hash(titulo+keyword)}.jpg"
        with open(imagen_path,'rb') as f:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/media",
                headers={'Content-Disposition':f'attachment; filename="{nombre}"','Content-Type':'image/jpeg'},
                data=f.read(), auth=(WP_USER,WP_APP_PASSWORD), timeout=60).json()
        if 'id' in r:
            media_id  = r['id']
            media_url = r.get('source_url','')
            alt_text  = f"{keyword} — {titulo[:80]}"[:125]
            try:
                requests.post(f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                    json={'title':alt_text,'alt_text':alt_text,
                          'caption':f"{titulo[:100]} — Verdad Hoy"},
                    auth=(WP_USER,WP_APP_PASSWORD), timeout=10)
            except: pass
            log(f"Imagen adicional {numero} subida WP: {media_url[:60]}",'info')
            return media_id, media_url
    except Exception as e:
        log(f"Error subiendo imagen adicional {numero}: {e}",'advertencia')
    return None, None

def html_imagen_adicional(media_url, alt_text, caption=""):
    """Genera bloque HTML para imagen adicional dentro del artículo."""
    if not media_url: return ""
    caption_html = f'<figcaption style="text-align:center;font-size:0.82em;color:#6b7280;margin-top:6px;">{caption}</figcaption>' if caption else ''
    return (f'<figure style="margin:28px 0;text-align:center;">'
            f'<img src="{media_url}" alt="{alt_text}" '
            f'style="max-width:100%;height:auto;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.12);" loading="lazy"/>'
            f'{caption_html}</figure>')

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

def publicar_borrador_wordpress(titulo, contenido, categoria, imagen_destacada_path,
                                 imagenes_adicionales, fuente_url, pais_foco='global',
                                 feedback_correccion=None):
    if not WP_APP_PASSWORD: return None, None
    if not imagen_destacada_path or not os.path.exists(imagen_destacada_path): return None, None

    # Generar título mixto sugerido
    titulo_sugerido = generar_titulo_mixto(titulo, categoria)

    resultado_ia = reescribir_noticia_v21(
        titulo, contenido, categoria, pais_foco,
        feedback_correccion, titulo_sugerido
    )
    if not resultado_ia: return None, None
    resultado_ia = postprocesar_resultado(resultado_ia)

    keyword        = resultado_ia.get('keyword_principal','')
    texto_check    = _texto_plano(resultado_ia.get('contenido_html',''))
    n_palabras     = len(texto_check.split())
    log(f"Borrador generado: {n_palabras} palabras | keyword: '{keyword}'",'info')
    if n_palabras < 200:
        log("Contenido demasiado corto (<200 palabras) — descartando",'advertencia')
        return None, None

    titulo_final       = resultado_ia.get('titulo_seo', titulo).strip()[:60]
    titulo_seo         = titulo_final + ' | Verdad Hoy'
    meta_desc          = resultado_ia.get('meta_descripcion','')
    frase_clave        = resultado_ia.get('keyword_principal','')
    slug_ia            = resultado_ia.get('slug','')
    contenido_html     = resultado_ia.get('contenido_html','')
    categoria_ia       = resultado_ia.get('categoria', categoria)
    slug_post          = slug_ia if (slug_ia and len(slug_ia) <= 50) else generar_slug_seo(titulo_final)

    # ── Tabla de contenidos si falta ────────────────────
    if '<nav' not in contenido_html and 'tabla-contenidos' not in contenido_html:
        h2_raw = re.findall(r'<h2[^>]*>(.*?)</h2>', contenido_html, flags=re.IGNORECASE|re.DOTALL)
        h2_textos = [(str(i+1), re.sub(r'<[^>]+>','',t).strip()) for i,t in enumerate(h2_raw)]
        items_toc = '\n'.join(f'<li style="margin-bottom:4px;"><a href="#seccion-{n}" style="color:#1a56db;text-decoration:none;">{t}</a></li>' for n,t in h2_textos[:4])
        if items_toc:
            toc_html = (f'<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">'
                        f'<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este artículo</p>'
                        f'<ol style="margin:0;padding-left:20px;color:#475569;font-size:0.9em;">{items_toc}</ol></nav>')
            contenido_html = toc_html + contenido_html

    # ── Subir imágenes adicionales e inyectar en HTML ───
    for i, img_path in enumerate(imagenes_adicionales[:2], start=1):
        placeholder = f"[IMAGEN_ADICIONAL_{i}]"
        if placeholder in contenido_html:
            _, media_url = subir_imagen_adicional_wp(img_path, titulo_final, frase_clave, i)
            if media_url:
                html_img = html_imagen_adicional(
                    media_url,
                    f"{frase_clave} — imagen {i}",
                    caption=f"{titulo_final[:80]} — Verdad Hoy"
                )
                contenido_html = contenido_html.replace(placeholder, html_img)
            else:
                contenido_html = contenido_html.replace(placeholder, "")
        else:
            contenido_html = contenido_html.replace(placeholder, "")
    # Limpiar placeholders sobrantes
    contenido_html = re.sub(r'\[IMAGEN_ADICIONAL_\d+\]', '', contenido_html)

    contenido_html = insertar_enlaces_internos(contenido_html)

    # ── Tags ─────────────────────────────────────────────
    tags_ids = []
    for kw in resultado_ia.get('keywords_secundarias',[])[:5]:
        tag_id = obtener_crear_tag_wp(kw)
        if tag_id: tags_ids.append(tag_id)

    slug_cat = CATEGORIAS_EVERGREEN.get(categoria_ia,{}).get('slug','mundo')
    cat_id = obtener_id_categoria_wp(slug_cat)
    if not cat_id: cat_id = obtener_id_categoria_wp('mundo'); slug_cat = 'mundo'
    categorias_ids = [cat_id] if cat_id else []

    # ── Imagen destacada ─────────────────────────────────
    imagen_id = subir_imagen_wp(imagen_destacada_path, titulo_final,
        alt_text=f"{frase_clave} - {titulo_final}"[:125],
        frase_clave=frase_clave, meta_descripcion=meta_desc)
    if not imagen_id: return None, None

    # ── Barra de lectura ─────────────────────────────────
    palabras_art = len(_texto_plano(contenido_html).split())
    minutos_lect = max(2, round(palabras_art / 200))
    barra_lectura = f'<p style="font-size:0.82em;color:#6b7280;margin:0 0 20px 0;">🕐 Tiempo de lectura: <strong>{minutos_lect} min</strong></p>'

    nombre_medio = 'Fuente externa'
    try:
        dominio = re.sub(r'^(www\.|m\.)','', urlparse(fuente_url).netloc.lower())
        mapa = {'infobae.com':'Infobae','bbc.com':'BBC Mundo','cnn.com':'CNN','reuters.com':'Reuters','elpais.com':'El País','dw.com':'DW'}
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
<p style="font-size:0.9em;color:#374151;">
  <strong>Investigación y redacción:</strong> Equipo Editorial Verdad Hoy<br>
  <strong>Fuente consultada:</strong> <a href="{fuente_url}" target="_blank" rel="noopener" style="color:#1a56db;">{nombre_medio}</a>
</p>
<p style="font-size:0.9em;color:#6b7280;font-style:italic;border-left:3px solid #e5e7eb;padding:8px 12px;margin:12px 0;">
  En Verdad Hoy encontrarás análisis, contexto y la información que realmente importa sobre América Latina y el mundo.
</p>
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
                if r_rm.status_code in (200,201): log("Rank Math SEO guardado",'exito')
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
        ('https://www.infobae.com/arc/outboundfeeds/rss/salud/','Infobae Salud'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada','El Pais Ciencia'),
        ('https://www.bbc.com/mundo/topics/cidjknjekjxt/rss.xml','BBC Salud Ciencia'),
        ('https://www.nationalgeographicla.com/rss.xml','National Geographic ES'),
        ('https://feeds.xataka.com/xataka','Xataka'),
        ('https://hipertextual.com/feed','Hipertextual'),
        ('https://www.technologyreview.com/feed/','MIT Tech Review'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada','El Pais Tecnologia'),
        ('https://www.nationalgeographic.com.es/rss/all','NatGeo ES'),
        ('https://arqueologiamexicana.mx/feed','Arqueologia Mexicana'),
        ('https://www.muyinteresante.es/rss','Muy Interesante'),
        ('https://www.muyhistoria.es/rss','Muy Historia'),
        ('https://www.cientifica.online/feed','Cientifica Online'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/economia/','Infobae Economia'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada','El Pais Economia'),
        ('https://www.dw.com/es/ciencia-y-tecnologia/s-30688/rss','DW Ciencia'),
        ('http://feeds.bbci.co.uk/mundo/rss.xml','BBC Mundo'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/','Infobae America'),
        ('https://www.eltiempo.com/rss/portada.xml','El Tiempo CO'),
        ('https://www.emol.com/rss/','Emol Chile'),
        ('https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml','Cooperativa CL'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada','El Pais Internacional'),
        ('https://www.dw.com/es/mundo/s-30684/rss','DW Mundo'),
        ('http://feeds.bbci.co.uk/mundo/internacional/rss.xml','BBC Internacional'),
        ('https://feeds.france24.com/es/','France 24 ES'),
        ('https://www.lavanguardia.com/historiayvida/rss','Historia y Vida'),
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
                noticias.append({'titulo':titulo_limpio,'descripcion':desc_limpia,'url':l,
                                 'imagen_rss':img,  # guardamos URL, no descargamos aún
                                 'fuente':f"RSS:{nombre}",'fecha':e.get('published'),
                                 'relevancia':relevancia,'tema':detectar_tema(titulo_limpio,desc_limpia)})
        except Exception as e: log(f"RSS error ({nombre}): {e}",'advertencia')
    log(f"RSS: {len(noticias)} noticias",'info')
    return noticias

def obtener_newsapi_evergreen():
    if not NEWS_API_KEY: return []
    queries = [
        'cancer causas prevencion America Latina investigacion',
        'alzheimer diabetes tratamiento cientifico 2026',
        'inteligencia artificial que es como funciona explicacion',
        'IA empleos trabajo futuro America Latina impacto',
        'historia antigua civilizaciones precolombinas secretos',
        'mayas incas aztecas descubrimiento arqueologico reciente',
        'misterio cientifico sin resolver descubrimiento',
        'inflacion por que sube dolar America Latina explicacion',
        'criptomoneda bitcoin como funciona para principiantes',
        'geopolitica latinoamerica poder influencia historia',
        'por que existe conflicto origen historia explicacion',
        'espacio NASA descubrimiento planeta universo 2026',
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
                                     'url':a.get('url',''),'imagen_rss':a.get('urlToImage'),
                                     'fuente':f"NewsAPI:{a.get('source',{}).get('name','')}",
                                     'fecha':a.get('publishedAt'),'relevancia':relevancia,
                                     'tema':detectar_tema(titulo_limpio,desc_limpia)})
        except Exception as e: log(f"NewsAPI error: {e}",'advertencia')
    log(f"NewsAPI: {len(noticias)} noticias",'info')
    return noticias

# ══════════════════════════════════════════════════════════
# MAIN V21
# ══════════════════════════════════════════════════════════
def main():
    print("\n" + "="*60)
    print(f"VERDAD HOY BOT - {VERSION_BOT}")
    print(f"  Modo: 1 borrador por corrida | 3 corridas/día")
    print(f"  Horarios: 07:00, 13:00, 19:00 UTC")
    print(f"  Títulos: MIXTOS (preguntas + afirmaciones con número)")
    print(f"  Imágenes: destacada (fuente/generada) + adicionales en artículo")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*60)

    # Evitar doble publicación en la misma hora
    if ya_corrio_esta_hora():
        log("Ya se ejecutó en esta hora UTC — saltando para evitar duplicados",'advertencia')
        return None

    if not puede_publicar_wp():
        return None

    h = cargar_historial()
    rotacion = cargar_rotacion()
    paises_ciclo = seleccionar_paises_ciclo(rotacion, n=1)
    pais = paises_ciclo[0]
    log(f"País de esta corrida: {pais}",'info')
    log(f"Turno título: {'PREGUNTA' if es_turno_pregunta() else 'AFIRMACIÓN CON NÚMERO'}",'info')

    noticias = []
    noticias.extend(obtener_rss_ampliado())
    if NEWS_API_KEY: noticias.extend(obtener_newsapi_evergreen())
    if not noticias: log("Sin noticias disponibles",'error'); return None

    # Filtrar evergreen y spam
    noticias_filtradas = []
    for n in noticias:
        tema = n.get('tema') or detectar_tema(n.get('titulo',''), n.get('descripcion',''))
        if not es_evergreen(tema): continue
        es_spam, _ = es_contenido_spam(n.get('titulo',''), n.get('descripcion',''))
        if es_spam: continue
        n['tema'] = tema
        noticias_filtradas.append(n)

    log(f"Noticias evergreen disponibles: {len(noticias_filtradas)}",'info')
    noticias_filtradas = deduplicar_batch(noticias_filtradas)
    noticias_filtradas.sort(key=lambda x: x.get('relevancia',0), reverse=True)

    # Buscar candidata para el país asignado
    candidata = None
    for n in noticias_filtradas:
        url = n.get('url','')
        titulo = n.get('titulo','')
        if noticia_es_de_pais(titulo, n.get('descripcion',''), pais):
            dup, _ = noticia_ya_publicada(h, url, titulo, n.get('descripcion',''))
            if not dup:
                candidata = n
                break

    # Fallback: cualquier noticia evergreen no publicada
    if not candidata:
        log(f"Sin candidata específica para '{pais}' — usando pool general",'advertencia')
        for n in noticias_filtradas:
            url = n.get('url','')
            titulo = n.get('titulo','')
            dup, _ = noticia_ya_publicada(h, url, titulo, n.get('descripcion',''))
            if not dup:
                candidata = n
                break

    if not candidata:
        log("Sin noticias nuevas disponibles — todas ya publicadas",'advertencia')
        return None

    titulo  = candidata.get('titulo','')
    url     = candidata.get('url','')
    desc    = candidata.get('descripcion','')
    tema    = candidata.get('tema','general')

    log(f"\n[{pais.upper()}] {titulo[:70]}",'info')
    log(f"  Tema: {tema} | Relevancia: {candidata.get('relevancia',0)}",'info')

    # Contenido
    cont_web = extraer_contenido(url)
    if cont_web and len(cont_web) >= 200: contenido_ok = cont_web
    elif desc and len(desc) >= 150: contenido_ok = desc
    elif cont_web: contenido_ok = (cont_web + ' ' + (desc or ''))
    elif desc: contenido_ok = desc
    else: log("Contenido insuficiente",'advertencia'); return None

    # ── IMÁGENES V21 ──────────────────────────────────────
    # Imagen destacada: og:image de fuente → generada
    # Imágenes adicionales: DuckDuckGo por keyword+categoría
    keyword_base = titulo.split()[:3]
    keyword_str  = ' '.join(keyword_base)
    img_destacada, imagenes_adicionales = obtener_imagenes_articulo(
        fuente_url=url,
        titulo=titulo,
        keyword=keyword_str,
        categoria=tema,
        n_extra=2
    )

    if not img_destacada:
        log("Sin imagen destacada — abortando",'advertencia')
        return None

    # Publicar borrador
    url_wp, slug_cat = publicar_borrador_wordpress(
        titulo=titulo,
        contenido=contenido_ok,
        categoria=tema,
        imagen_destacada_path=img_destacada,
        imagenes_adicionales=imagenes_adicionales,
        fuente_url=url,
        pais_foco=pais
    )

    # Limpiar archivos temporales
    for img_path in [img_destacada] + imagenes_adicionales:
        try:
            if img_path and os.path.exists(img_path): os.remove(img_path)
        except: pass

    if url_wp:
        registrar_borrador()
        h['estadisticas']['total_borradores'] = h['estadisticas'].get('total_borradores',0) + 1
        h = guardar_en_historial(h, url, titulo, (desc+' '+contenido_ok[:400]).strip())
        registrar_paises_usados(rotacion, [pais])
        log(f"\n✅ BORRADOR PUBLICADO — {url_wp}",'exito')
        log(f"   País: {pais} | Tema: {tema} | Turno: {'pregunta' if es_turno_pregunta() else 'afirmación'}",'info')
        return True
    else:
        log("No se pudo crear el borrador",'error')
        return None

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0)
    except Exception as e:
        log(f"Error crítico: {e}",'error')
        import traceback
        traceback.print_exc()
        exit(1)
