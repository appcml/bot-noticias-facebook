#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias - V22.0.1
CAMBIOS VS V22:
  - MAX_BORRADORES_DIA = 2 (2 borradores por corrida)
  - Fix: SyntaxError en exit(1)v
"""
VERSION_BOT = "V22.0.1"

import requests, feedparser, re, hashlib, json, os, random, time, unicodedata
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse

MAX_BORRADORES_DIA = 2   # 2 borradores por corrida
ROTACION_TEMAS_PATH = 'estado_rotacion_temas.json'
ROTACION_PAISES_PATH = 'estado_rotacion_paises.json'

POOL_EVERGREEN = [
    {'tema': 'Los secretos de los mayas que aún no se han descifrado', 'categoria': 'historia', 'pais': 'mexico', 'keyword': 'mayas'},
    {'tema': 'Por qué los incas construyeron Machu Picchu y qué pasó con ellos', 'categoria': 'historia', 'pais': 'peru', 'keyword': 'incas Machu Picchu'},
    {'tema': 'Los aztecas y Tenochtitlán: la ciudad más grande del mundo medieval', 'categoria': 'historia', 'pais': 'mexico', 'keyword': 'aztecas Tenochtitlán'},
    {'tema': 'La conquista española de América Latina: causas y consecuencias reales', 'categoria': 'historia', 'pais': 'global', 'keyword': 'conquista española América Latina'},
    {'tema': 'Dictaduras en América Latina en el siglo XX: qué pasó y qué dejaron', 'categoria': 'historia', 'pais': 'global', 'keyword': 'dictaduras América Latina'},
    {'tema': 'La Operación Cóndor: el plan secreto que unió dictaduras en Sudamérica', 'categoria': 'historia', 'pais': 'global', 'keyword': 'Operación Cóndor'},
    {'tema': 'Por qué cayó el Imperio Inca tan rápido ante los españoles', 'categoria': 'historia', 'pais': 'peru', 'keyword': 'caída Imperio Inca'},
    {'tema': 'Simón Bolívar: quién fue realmente y qué logró en América Latina', 'categoria': 'historia', 'pais': 'global', 'keyword': 'Simón Bolívar'},
    {'tema': 'La historia del Canal de Panamá y por qué cambió al mundo', 'categoria': 'historia', 'pais': 'global', 'keyword': 'Canal de Panamá historia'},
    {'tema': 'Civilizaciones precolombinas que existían antes de que llegaran los europeos', 'categoria': 'historia', 'pais': 'global', 'keyword': 'civilizaciones precolombinas'},
    {'tema': 'Las líneas de Nazca: qué son, cómo se hicieron y para qué servían', 'categoria': 'misterios', 'pais': 'peru', 'keyword': 'líneas de Nazca'},
    {'tema': 'El misterio de la ciudad perdida de El Dorado y dónde podría estar', 'categoria': 'misterios', 'pais': 'global', 'keyword': 'El Dorado ciudad perdida'},
    {'tema': 'Hallazgos arqueológicos recientes que cambian la historia de América Latina', 'categoria': 'misterios', 'pais': 'global', 'keyword': 'hallazgos arqueológicos América Latina'},
    {'tema': 'Los moais de la Isla de Pascua: cómo los movieron y qué significan', 'categoria': 'misterios', 'pais': 'chile', 'keyword': 'moais Isla de Pascua'},
    {'tema': 'Fenómenos inexplicables en América Latina que la ciencia no ha resuelto', 'categoria': 'misterios', 'pais': 'global', 'keyword': 'fenómenos inexplicables América Latina'},
    {'tema': 'Por qué el cáncer sigue siendo tan difícil de curar y qué avances hay', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'cáncer tratamiento avances'},
    {'tema': 'Qué es el Alzheimer y cómo afecta a las familias latinoamericanas', 'categoria': 'salud', 'pais': 'global', 'keyword': 'Alzheimer América Latina'},
    {'tema': 'La diabetes en América Latina: por qué somos de los más afectados del mundo', 'categoria': 'salud', 'pais': 'global', 'keyword': 'diabetes América Latina'},
    {'tema': 'Qué sabemos sobre la longevidad y cómo vivir más años con calidad', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'longevidad ciencia'},
    {'tema': 'Cómo funciona el cerebro humano y por qué aún no lo entendemos del todo', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'cerebro humano funcionamiento'},
    {'tema': 'El microbioma intestinal: por qué los bacterias en tu barriga importan', 'categoria': 'salud', 'pais': 'global', 'keyword': 'microbioma intestinal salud'},
    {'tema': 'Medicamentos más importantes descubiertos en América Latina', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'medicamentos descubrimientos América Latina'},
    {'tema': 'Por qué América Latina tiene tasas altas de hipertensión y qué hacer', 'categoria': 'salud', 'pais': 'global', 'keyword': 'hipertensión América Latina'},
    {'tema': 'Qué es la inteligencia artificial y cómo cambia tu trabajo en LATAM', 'categoria': 'tecnologia', 'pais': 'global', 'keyword': 'inteligencia artificial trabajo LATAM'},
    {'tema': 'Cómo la IA está reemplazando empleos en América Latina y cuáles sobrevivirán', 'categoria': 'tecnologia', 'pais': 'global', 'keyword': 'IA empleos América Latina'},
    {'tema': 'Qué es el bitcoin y por qué algunos países de LATAM lo adoptaron', 'categoria': 'tecnologia', 'pais': 'global', 'keyword': 'bitcoin América Latina'},
    {'tema': 'Por qué América Latina se está quedando atrás en tecnología y cómo cambiar eso', 'categoria': 'tecnologia', 'pais': 'global', 'keyword': 'brecha tecnológica América Latina'},
    {'tema': 'Deepfakes: qué son, cómo detectarlos y por qué son peligrosos en política LATAM', 'categoria': 'tecnologia', 'pais': 'global', 'keyword': 'deepfakes política LATAM'},
    {'tema': 'Startups latinoamericanas que cambiaron la región: los casos de éxito', 'categoria': 'innovacion', 'pais': 'global', 'keyword': 'startups latinoamericanas éxito'},
    {'tema': 'Cómo funciona la computación cuántica y qué significa para el futuro', 'categoria': 'tecnologia', 'pais': 'global', 'keyword': 'computación cuántica futuro'},
    {'tema': 'Por qué el litio de Chile y Bolivia es clave para el futuro del mundo', 'categoria': 'economia', 'pais': 'chile', 'keyword': 'litio Chile Bolivia'},
    {'tema': 'Qué es la inflación y por qué destroza los ahorros en América Latina', 'categoria': 'economia', 'pais': 'global', 'keyword': 'inflación América Latina'},
    {'tema': 'El cobre chileno: cuánto vale, quién lo compra y por qué importa', 'categoria': 'economia', 'pais': 'chile', 'keyword': 'cobre Chile economía'},
    {'tema': 'Por qué el dólar domina América Latina y qué pasa cuando sube', 'categoria': 'economia', 'pais': 'global', 'keyword': 'dólar América Latina'},
    {'tema': 'Narcoeconomía en LATAM: cuánto mueve el narcotráfico y cómo lo blanquean', 'categoria': 'economia', 'pais': 'global', 'keyword': 'narcoeconomía América Latina'},
    {'tema': 'El petróleo venezolano: por qué siendo tan rico Venezuela está en crisis', 'categoria': 'economia', 'pais': 'venezuela', 'keyword': 'petróleo Venezuela crisis'},
    {'tema': 'Qué es el BRICS y por qué varios países de LATAM quieren entrar', 'categoria': 'geopolitica', 'pais': 'global', 'keyword': 'BRICS América Latina'},
    {'tema': 'La soya brasileña y cómo Brasil se convirtió en potencia agrícola mundial', 'categoria': 'economia', 'pais': 'brasil', 'keyword': 'soya Brasil agrícola'},
    {'tema': 'Por qué América Latina es la región más violenta del mundo', 'categoria': 'geopolitica', 'pais': 'global', 'keyword': 'violencia América Latina'},
    {'tema': 'El Tren de Aragua: origen, expansión y por qué llegó a Chile y EEUU', 'categoria': 'geopolitica', 'pais': 'global', 'keyword': 'Tren de Aragua'},
    {'tema': 'Cárteles mexicanos: cómo operan y por qué controlan tantos países', 'categoria': 'geopolitica', 'pais': 'mexico', 'keyword': 'cárteles mexicanos expansión'},
    {'tema': 'La crisis de Venezuela: qué pasó, por qué emigran y adónde van', 'categoria': 'geopolitica', 'pais': 'venezuela', 'keyword': 'crisis Venezuela emigración'},
    {'tema': 'Nayib Bukele y El Salvador: cómo bajó el crimen y qué costo tuvo', 'categoria': 'geopolitica', 'pais': 'global', 'keyword': 'Bukele El Salvador seguridad'},
    {'tema': 'Influencia de China en América Latina: inversiones, deudas y poder', 'categoria': 'geopolitica', 'pais': 'global', 'keyword': 'China América Latina inversión'},
    {'tema': 'La migración latinoamericana a EEUU: causas, riesgos y datos reales', 'categoria': 'geopolitica', 'pais': 'global', 'keyword': 'migración latinoamericana EEUU'},
    {'tema': 'Por qué Colombia no ha podido acabar con las FARC en décadas', 'categoria': 'geopolitica', 'pais': 'colombia', 'keyword': 'FARC Colombia conflicto'},
    {'tema': 'La Amazonía en peligro: cuánta selva se pierde cada año y qué significa', 'categoria': 'medio_ambiente', 'pais': 'brasil', 'keyword': 'Amazonía deforestación'},
    {'tema': 'Cambio climático en Chile: glaciares que desaparecen y sequías históricas', 'categoria': 'medio_ambiente', 'pais': 'chile', 'keyword': 'cambio climático Chile glaciares'},
    {'tema': 'Por qué América Latina sufre más el cambio climático que otras regiones', 'categoria': 'medio_ambiente', 'pais': 'global', 'keyword': 'cambio climático América Latina'},
    {'tema': 'La minería de litio en el desierto de Atacama y su impacto ambiental', 'categoria': 'medio_ambiente', 'pais': 'chile', 'keyword': 'minería litio Atacama impacto'},
    {'tema': 'Especies en extinción en América Latina que puedes perder en tu vida', 'categoria': 'medio_ambiente', 'pais': 'global', 'keyword': 'extinción especies América Latina'},
    {'tema': 'Por qué la cumbia se extendió por toda América Latina y el mundo', 'categoria': 'cultura', 'pais': 'global', 'keyword': 'cumbia América Latina historia'},
    {'tema': 'El fútbol en América Latina: por qué es más que un deporte', 'categoria': 'deportes', 'pais': 'global', 'keyword': 'fútbol América Latina cultura'},
    {'tema': 'Machismo en América Latina: origen histórico y cómo está cambiando', 'categoria': 'cultura', 'pais': 'global', 'keyword': 'machismo América Latina'},
    {'tema': 'Boom del anime en América Latina: por qué somos de los mayores consumidores', 'categoria': 'entretenimiento', 'pais': 'global', 'keyword': 'anime América Latina'},
    {'tema': 'La brecha educativa en América Latina: por qué nuestros hijos aprenden menos', 'categoria': 'cultura', 'pais': 'global', 'keyword': 'educación brecha América Latina'},
    {'tema': 'Qué hay más allá del universo observable y qué dice la ciencia', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'universo observable límites'},
    {'tema': 'NASA y la carrera espacial 2026: qué misiones están activas ahora', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'NASA misiones espaciales 2026'},
    {'tema': 'Agujeros negros: qué son, cómo se forman y qué pasaría si te cae uno encima', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'agujeros negros ciencia'},
    {'tema': 'Vida en otros planetas: qué ha encontrado la NASA y qué falta por descubrir', 'categoria': 'ciencia', 'pais': 'global', 'keyword': 'vida extraterrestre NASA'},
]

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
    'general':        {'slug': 'mundo',           'cpm': 1.00, 'evergreen': True},
}

NEWS_API_KEY       = os.getenv('NEWS_API_KEY','')
NEWSDATA_API_KEY   = os.getenv('NEWSDATA_API_KEY','')
WP_URL             = os.getenv('WP_URL','https://verdadhoy.com')
WP_USER            = os.getenv('WP_USER','verdadhoy_admin')
WP_APP_PASSWORD    = os.getenv('WP_APP_PASSWORD','')
GROQ_API_KEY       = os.getenv('GROQ_API_KEY','')
GEMINI_API_KEY     = os.getenv('GEMINI_API_KEY','')
TAVILY_API_KEY     = os.getenv('TAVILY_API_KEY','')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY','')
OPENAI_API_KEY     = os.getenv('OPENAI_API_KEY','')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH','historial_publicaciones.json')
CUOTAS_PATH    = 'estado_cuotas.json'

UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 500
DIAS_HISTORIAL             = 60

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

_cache_categorias_wp = {}
_cache_tags_wp       = {}

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
# ROTACIÓN DE TEMAS EVERGREEN
# ══════════════════════════════════════════════════════════
def cargar_rotacion_temas():
    datos = cargar_json(ROTACION_TEMAS_PATH, {
        'temas_publicados': [],
        'fecha_ultimo_reset': '',
        'conteo_por_categoria': {}
    })
    return datos

def seleccionar_temas_dia(rotacion, n=2):
    publicados = set(rotacion.get('temas_publicados', []))
    conteo_cat = rotacion.get('conteo_por_categoria', {})
    disponibles = [t for t in POOL_EVERGREEN if t['keyword'] not in publicados]
    if len(disponibles) < len(POOL_EVERGREEN) * 0.2:
        log(f"Pool evergreen casi agotado ({len(disponibles)} restantes) — reseteando ciclo", 'advertencia')
        rotacion['temas_publicados'] = []
        rotacion['conteo_por_categoria'] = {}
        guardar_json(ROTACION_TEMAS_PATH, rotacion)
        disponibles = list(POOL_EVERGREEN)
    if not disponibles:
        return []
    def score_tema(t):
        cat_count = conteo_cat.get(t['categoria'], 0)
        return cat_count + random.uniform(0, 2)
    disponibles_ordenados = sorted(disponibles, key=score_tema)
    seleccionados = []
    categorias_usadas = set()
    for tema in disponibles_ordenados:
        if len(seleccionados) >= n:
            break
        if tema['categoria'] not in categorias_usadas or len(seleccionados) < n:
            seleccionados.append(tema)
            categorias_usadas.add(tema['categoria'])
    if len(seleccionados) < n:
        for tema in disponibles_ordenados:
            if tema not in seleccionados:
                seleccionados.append(tema)
            if len(seleccionados) >= n:
                break
    return seleccionados[:n]

def registrar_tema_publicado(rotacion, tema):
    publicados = rotacion.get('temas_publicados', [])
    if tema['keyword'] not in publicados:
        publicados.append(tema['keyword'])
    rotacion['temas_publicados'] = publicados
    conteo = rotacion.get('conteo_por_categoria', {})
    conteo[tema['categoria']] = conteo.get(tema['categoria'], 0) + 1
    rotacion['conteo_por_categoria'] = conteo
    guardar_json(ROTACION_TEMAS_PATH, rotacion)

# ══════════════════════════════════════════════════════════
# TÍTULOS MIXTOS
# ══════════════════════════════════════════════════════════
def es_turno_pregunta(indice=0):
    return indice % 2 == 0

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

def generar_titulo_mixto(keyword, categoria, indice=0):
    if es_turno_pregunta(indice):
        return formato_titulo_pregunta(keyword, categoria)
    else:
        return formato_titulo_afirmacion(keyword, categoria)

# ══════════════════════════════════════════════════════════
# HISTORIAL Y CUOTAS
# ══════════════════════════════════════════════════════════
HISTORIAL_DEFAULT = {
    'urls':[],'urls_normalizadas':[],'hashes':[],'timestamps':[],
    'titulos':[],'descripciones':[],'hashes_contenido':[],'hashes_permanentes':[],
    'estadisticas':{'total_publicadas':0,'total_wp':0,'total_borradores':0}
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
    if len(h.get('hashes_permanentes',[])) > 800:
        h['hashes_permanentes'] = h['hashes_permanentes'][-800:]

def tema_ya_publicado(h, keyword, tema_titulo):
    hash_t = generar_hash(keyword)
    todos_hashes = set(h.get('hashes',[])) | set(h.get('hashes_permanentes',[]))
    if hash_t in todos_hashes: return True, "keyword_duplicado"
    for th in h.get('titulos',[]):
        if not isinstance(th,str): continue
        if similitud_titulos(tema_titulo, th) >= UMBRAL_SIMILITUD_TITULO:
            return True, "titulo_similar"
    return False, "nuevo"

def guardar_en_historial(h, url_fuente, titulo, keyword, desc=""):
    hash_t = generar_hash(keyword)
    h['urls'].append(url_fuente or '')
    h['urls_normalizadas'].append(normalizar_url(url_fuente or ''))
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['hashes_permanentes'].append(hash_t)
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas',0) + 1
    h['estadisticas']['total_borradores'] = h['estadisticas'].get('total_borradores',0) + 1
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA: h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    if len(h['hashes_permanentes']) > 800: h['hashes_permanentes'] = h['hashes_permanentes'][-800:]
    guardar_json(HISTORIAL_PATH, h)
    return h

def puede_publicar_wp(borradores_esta_corrida):
    if os.getenv('FORZAR_PUBLICACION','').lower() == 'true': return True
    return borradores_esta_corrida < MAX_BORRADORES_DIA

# ══════════════════════════════════════════════════════════
# TAVILY
# ══════════════════════════════════════════════════════════
def buscar_contexto_evergreen(tema_titulo, keyword, n_resultados=5):
    if not TAVILY_API_KEY:
        log("Sin TAVILY_API_KEY — sin contexto web", 'advertencia')
        return [], ""
    try:
        query = f"{keyword} historia explicación datos América Latina"
        resp = requests.post("https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY,
                  "query": query,
                  "search_depth": "advanced",
                  "max_results": n_resultados,
                  "include_answer": True,
                  "include_raw_content": False},
            timeout=20)
        data = resp.json()
        answer = data.get("answer", "")
        resultados = data.get("results", [])
        if not resultados:
            log(f"Tavily sin resultados para '{keyword}'", 'advertencia')
            return [], answer
        fuentes = [{"title": r.get("title",""),
                    "url":   r.get("url",""),
                    "content": (r.get("content","") or "")[:800]}
                   for r in resultados]
        log(f"Tavily: {len(fuentes)} fuentes para '{keyword}'", 'info')
        return fuentes, answer
    except Exception as e:
        log(f"Tavily error: {e}", 'advertencia')
        return [], ""

# ══════════════════════════════════════════════════════════
# IMÁGENES
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
        for img_tag in s.find_all('img', src=True)[:10]:
            src = img_tag.get('src','')
            if src.startswith('http') and not any(b in src.lower() for b in ['logo','icon','avatar']):
                return src
    except: pass
    return None

def buscar_imagenes_duckduckgo(query, max_resultados=4):
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
            'misterios':'MISTERIOS','historia':'HISTORIA','geopolitica':'GEOPOLÍTICA',
            'innovacion':'INNOVACIÓN','tecnologia':'TECNOLOGÍA','ciencia':'CIENCIA',
            'salud':'SALUD','economia':'ECONOMÍA','politica':'POLÍTICA',
            'deportes':'DEPORTES','entretenimiento':'ENTRETENIMIENTO','cultura':'CULTURA',
            'medio_ambiente':'MEDIO AMBIENTE','latinoamerica':'LATINOAMÉRICA','mundo':'MUNDO','general':'NOTICIAS',
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

def obtener_imagenes_articulo(fuentes_tavily, keyword, categoria, titulo):
    img_destacada = None
    for fuente in fuentes_tavily[:3]:
        url_fuente = fuente.get('url','')
        if not url_fuente: continue
        og_url = extraer_imagen_og(url_fuente)
        if og_url:
            img_destacada = descargar_imagen(og_url)
            if img_destacada:
                log(f"Imagen destacada desde Tavily fuente: OK",'info')
                break
    if not img_destacada:
        log("Sin og:image — generando imagen con título",'advertencia')
        img_destacada = crear_imagen_titulo(titulo, categoria)
    imagenes_adicionales = []
    queries_cat = {
        'historia':      [f"{keyword} historia", f"civilización latinoamericana"],
        'misterios':     [f"{keyword} misterio arqueología", f"descubrimiento inexplicable"],
        'ciencia':       [f"{keyword} ciencia investigación", f"laboratorio científico"],
        'salud':         [f"{keyword} salud medicina", f"tratamiento médico"],
        'tecnologia':    [f"{keyword} tecnología", f"innovación digital futuro"],
        'economia':      [f"{keyword} economía finanzas", f"mercado dinero"],
        'geopolitica':   [f"{keyword} política mundo", f"mapa conflicto"],
        'medio_ambiente':[f"{keyword} naturaleza", f"cambio climático ecosistema"],
        'cultura':       [f"{keyword} cultura latinoamérica", f"tradición arte"],
        'deportes':      [f"{keyword} deporte", f"competencia deportiva"],
        'innovacion':    [f"{keyword} innovación startup", f"tecnología futuro"],
        'entretenimiento':[f"{keyword} entretenimiento", f"cultura pop latina"],
    }
    queries = queries_cat.get(categoria, [f"{keyword}", f"{keyword} América Latina"])
    urls_imgs = []
    for q in queries[:2]:
        urls_imgs.extend(buscar_imagenes_duckduckgo(q, max_resultados=3))
    urls_imgs = list(dict.fromkeys(urls_imgs))
    for img_url in urls_imgs[:6]:
        if len(imagenes_adicionales) >= 2: break
        path = descargar_imagen(img_url, min_w=350, min_h=220)
        if path:
            imagenes_adicionales.append(path)
    log(f"Imágenes: 1 destacada + {len(imagenes_adicionales)} adicionales",'info')
    return img_destacada, imagenes_adicionales

# ══════════════════════════════════════════════════════════
# IA — GENERACIÓN EVERGREEN
# ══════════════════════════════════════════════════════════
def generar_articulo_evergreen(tema_config, fuentes_tavily, answer_tavily, indice=0):
    api_key = OPENAI_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY or GEMINI_API_KEY
    if not api_key: return None

    tema_titulo  = tema_config['tema']
    categoria    = tema_config['categoria']
    keyword      = tema_config['keyword']
    pais         = tema_config.get('pais', 'global')

    TITULOS_BOX = [
        ('⚡','Lo que debes saber','#ff6b35','#fff3e0'),
        ('📋','Resumen rápido','#0891b2','#e0f2fe'),
        ('🔑','Puntos clave','#a855f7','#ede9fe'),
        ('📌','Lo esencial','#1a56db','#eff6ff'),
    ]
    emoji_box, texto_box, color_titulo, color_fondo = random.choice(TITULOS_BOX)

    nombre_pais_mapa = {
        'chile':'Chile','argentina':'Argentina','mexico':'México','colombia':'Colombia',
        'brasil':'Brasil','venezuela':'Venezuela','peru':'Perú','ecuador':'Ecuador',
        'bolivia':'Bolivia','uruguay':'Uruguay','estados_unidos':'Estados Unidos',
        'europa':'Europa','asia':'Asia','global':'América Latina',
    }
    nombre_pais = nombre_pais_mapa.get(pais, 'América Latina')

    if es_turno_pregunta(indice):
        instruccion_titulo = (
            "FORMATO TÍTULO (turno PREGUNTA): El título DEBE ser una pregunta directa. "
            "Siempre debe comenzar con ¿ y terminar con ?. Max 65 chars. "
            f"Ejemplos válidos: '¿Por qué los mayas desaparecieron realmente?', "
            f"'¿Cómo funciona el bitcoin y por qué LATAM lo adoptó?'."
        )
    else:
        instruccion_titulo = (
            "FORMATO TÍTULO (turno AFIRMACIÓN): El título DEBE tener un número. "
            f"Max 65 chars. "
            f"Ejemplos válidos: '5 secretos de los mayas que la historia no cuenta', "
            f"'7 verdades sobre el bitcoin que debes saber en 2026'."
        )

    contexto_fuentes = ""
    if fuentes_tavily:
        partes = []
        for i, f in enumerate(fuentes_tavily[:4]):
            partes.append(f"[Fuente {i+1}] {f['title']}\n{f['content']}")
        contexto_fuentes = "CONTEXTO DE FUENTES WEB:\n" + "\n\n".join(partes)
    if answer_tavily:
        contexto_fuentes += f"\n\nRESPUESTA SÍNTESIS WEB:\n{answer_tavily}"

    año = datetime.now().year

    prompt = f"""Eres Editor Jefe Digital de VerdadHoy.com. Tono: directo, claro, periodístico. Audiencia: Chile, Argentina, México.

MISIÓN EVERGREEN: Crear un artículo de FONDO que sea útil HOY y dentro de 6 meses.
NO es noticia del día. ES artículo explicativo, educativo, de contexto profundo.

TEMA A DESARROLLAR: {tema_titulo}
KEYWORD PRINCIPAL: {keyword}
CATEGORÍA: {categoria}
PAÍS/REGIÓN: {nombre_pais}
AÑO: {año}

{instruccion_titulo}

{contexto_fuentes}

ESTRUCTURA OBLIGATORIA (mínimo 800 palabras):
- Párrafo introductorio con keyword en primeras 40 palabras
- Al menos 4 secciones H2 con id="seccion-N"
- Al menos 3 datos numéricos o estadísticas verificables
- Un ángulo específico para América Latina / {nombre_pais}
- Sección "Qué esperar" o "Qué hacer al respecto"
- Conclusión con pregunta al lector

REGLAS SEO:
- Meta descripción: "[KEYWORD] — [dato con número]. [consecuencia]." — 150-160 chars exacto
- Slug: max 50 chars en minúsculas con guiones
- 4 palabras de transición mínimo (sin embargo, además, por otro lado, en consecuencia)
- Densidad keyword: 1-1.5%

HTML COMPLETO A GENERAR:

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
<blockquote style="border-left:3px solid #e5e7eb;padding:12px 16px;margin:20px 0;background:#f9fafb;font-style:italic;color:#4b5563;">"[dato estadístico o cita verificable con número y fuente]"</blockquote>
<h2 id="seccion-3">[H2: impacto en {nombre_pais} / América Latina]</h2>
<p>[impacto LATAM con datos de 2 países]</p>
[IMAGEN_ADICIONAL_2]
<h2 id="seccion-4">[H2: futuro / qué hacer]</h2>
<p>[proyección {año+1}. Pregunta al lector al final.]</p>
[ENLACES_INTERNOS]

RESPONDE SOLO JSON sin markdown:
{{"titulo_seo":"según formato del turno max 65 chars","slug":"max-50-chars","meta_descripcion":"keyword primero 150-160 chars","contenido_html":"HTML completo con placeholders","keyword_principal":"2-3 palabras","keywords_secundarias":["kw2","kw3","kw4","kw5"],"categoria":"{categoria}","parrafo_nativo":"texto plano 2-3 oraciones","descripcion_pinterest":"100-150 chars con hashtags"}}"""

    def _llamar_api(url_api, headers, modelo, payload):
        try:
            resp = requests.post(url_api, headers=headers, json=payload, timeout=90)
        except Exception as e:
            log(f"IA error de red: {e}",'error'); return None
        try: resp_json = resp.json()
        except: log(f"IA respuesta no JSON (HTTP {resp.status_code})",'error'); return None
        if "choices" not in resp_json:
            err = resp_json.get("error",{})
            msg = err.get("message",str(resp_json)[:200]) if isinstance(err,dict) else str(err)[:200]
            log(f"IA error: {msg}",'error'); return None
        return resp_json

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
        payload_i = {"model":modelo_i,"messages":[{"role":"user","content":prompt}],"temperature":0.35,"max_tokens":4500}
        if i > 0: log(f"Reintentando con {nombre}...",'advertencia')
        resp_json = _llamar_api(url_i, headers_i, modelo_i, payload_i)
        if resp_json: break

    if not resp_json: return None

    try:
        texto = resp_json["choices"][0]["message"]["content"].strip()
        texto = re.sub(r'^```json\s*|```$','',texto,flags=re.MULTILINE).strip()
        if not texto.endswith('}'): return None
        resultado = json.loads(texto)
        resultado['categoria'] = categoria
        log(f"IA OK — '{resultado.get('titulo_seo','')[:60]}' | {resultado.get('categoria')}",'info')
        return resultado
    except Exception as e:
        log(f"generar_articulo_evergreen parse error: {e}",'advertencia')
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

def postprocesar_titulo(resultado_ia, indice=0):
    titulo = resultado_ia.get('titulo_seo','').strip()
    if not titulo: return resultado_ia
    if es_turno_pregunta(indice):
        if not titulo.startswith('¿'): titulo = '¿' + titulo
        if not titulo.endswith('?'): titulo = titulo.rstrip('.') + '?'
    else:
        if not re.search(r'\d', titulo) and len(titulo) <= 45:
            titulo = f"{titulo}: {datetime.now().year}"
        if not any(pw in titulo.lower() for pw in POWER_WORDS_LISTA) and len(titulo) <= 47:
            titulo = f"{titulo}, clave"
    resultado_ia['titulo_seo'] = titulo[:65]
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

def postprocesar_resultado(resultado_ia, indice=0):
    resultado_ia = postprocesar_densidad(resultado_ia)
    resultado_ia = postprocesar_transiciones(resultado_ia)
    resultado_ia = postprocesar_meta(resultado_ia)
    resultado_ia = postprocesar_titulo(resultado_ia, indice)
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
            return media_id, media_url
    except Exception as e:
        log(f"Error subiendo imagen adicional {numero}: {e}",'advertencia')
    return None, None

def html_imagen_adicional(media_url, alt_text, caption=""):
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

def publicar_borrador_evergreen(tema_config, fuentes_tavily, answer_tavily,
                                 img_destacada_path, imagenes_adicionales, indice=0):
    if not WP_APP_PASSWORD: return None, None
    if not img_destacada_path or not os.path.exists(img_destacada_path): return None, None

    resultado_ia = generar_articulo_evergreen(tema_config, fuentes_tavily, answer_tavily, indice)
    if not resultado_ia: return None, None
    resultado_ia = postprocesar_resultado(resultado_ia, indice)

    keyword    = resultado_ia.get('keyword_principal','')
    texto_check = _texto_plano(resultado_ia.get('contenido_html',''))
    n_palabras = len(texto_check.split())
    log(f"Borrador {indice+1}: {n_palabras} palabras | keyword: '{keyword}'",'info')
    if n_palabras < 200:
        log("Contenido demasiado corto (<200 palabras) — descartando",'advertencia')
        return None, None

    titulo_final   = resultado_ia.get('titulo_seo', tema_config['tema']).strip()[:65]
    titulo_seo     = titulo_final + ' | Verdad Hoy'
    meta_desc      = resultado_ia.get('meta_descripcion','')
    frase_clave    = resultado_ia.get('keyword_principal','')
    slug_ia        = resultado_ia.get('slug','')
    contenido_html = resultado_ia.get('contenido_html','')
    categoria_ia   = resultado_ia.get('categoria', tema_config['categoria'])
    slug_post      = slug_ia if (slug_ia and len(slug_ia) <= 50) else generar_slug_seo(titulo_final)

    if '<nav' not in contenido_html and 'tabla-contenidos' not in contenido_html:
        h2_raw = re.findall(r'<h2[^>]*>(.*?)</h2>', contenido_html, flags=re.IGNORECASE|re.DOTALL)
        h2_textos = [(str(i+1), re.sub(r'<[^>]+>','',t).strip()) for i,t in enumerate(h2_raw)]
        items_toc = '\n'.join(f'<li style="margin-bottom:4px;"><a href="#seccion-{n}" style="color:#1a56db;text-decoration:none;">{t}</a></li>' for n,t in h2_textos[:4])
        if items_toc:
            toc_html = (f'<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">'
                        f'<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este artículo</p>'
                        f'<ol style="margin:0;padding-left:20px;color:#475569;font-size:0.9em;">{items_toc}</ol></nav>')
            contenido_html = toc_html + contenido_html

    for i, img_path in enumerate(imagenes_adicionales[:2], start=1):
        placeholder = f"[IMAGEN_ADICIONAL_{i}]"
        if placeholder in contenido_html:
            _, media_url = subir_imagen_adicional_wp(img_path, titulo_final, frase_clave, i)
            if media_url:
                html_img = html_imagen_adicional(media_url, f"{frase_clave} — imagen {i}",
                                                  caption=f"{titulo_final[:80]} — Verdad Hoy")
                contenido_html = contenido_html.replace(placeholder, html_img)
            else:
                contenido_html = contenido_html.replace(placeholder, "")
        else:
            contenido_html = contenido_html.replace(placeholder, "")
    contenido_html = re.sub(r'\[IMAGEN_ADICIONAL_\d+\]', '', contenido_html)
    contenido_html = insertar_enlaces_internos(contenido_html)

    tags_ids = []
    for kw in resultado_ia.get('keywords_secundarias',[])[:5]:
        tag_id = obtener_crear_tag_wp(kw)
        if tag_id: tags_ids.append(tag_id)

    slug_cat = CATEGORIAS_EVERGREEN.get(categoria_ia,{}).get('slug','mundo')
    cat_id = obtener_id_categoria_wp(slug_cat)
    if not cat_id: cat_id = obtener_id_categoria_wp('mundo'); slug_cat = 'mundo'
    categorias_ids = [cat_id] if cat_id else []

    imagen_id = subir_imagen_wp(img_destacada_path, titulo_final,
        alt_text=f"{frase_clave} - {titulo_final}"[:125],
        frase_clave=frase_clave, meta_descripcion=meta_desc)
    if not imagen_id: return None, None

    palabras_art = len(_texto_plano(contenido_html).split())
    minutos_lect = max(2, round(palabras_art / 200))
    barra_lectura = f'<p style="font-size:0.82em;color:#6b7280;margin:0 0 20px 0;">🕐 Tiempo de lectura: <strong>{minutos_lect} min</strong></p>'

    fuentes_credito = ""
    if fuentes_tavily:
        links = [f'<a href="{f["url"]}" target="_blank" rel="noopener" style="color:#1a56db;">{f["title"][:60]}</a>'
                 for f in fuentes_tavily[:3] if f.get('url')]
        if links:
            fuentes_credito = f'<p style="font-size:0.85em;color:#6b7280;">Fuentes consultadas: {" · ".join(links)}</p>'

    contenido_final = f"""
{barra_lectura}
{contenido_html}
<hr>
{fuentes_credito}
<p style="font-size:0.9em;color:#374151;">
  <strong>Investigación y redacción:</strong> Equipo Editorial Verdad Hoy
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
            log(f"BORRADOR {indice+1} creado: {WP_URL}/wp-admin/post.php?post={post_id}&action=edit",'exito')
            try:
                rm_payload = {'objectID':post_id,'objectType':'post',
                    'meta':{'rank_math_focus_keyword':frase_clave,'rank_math_title':titulo_seo,
                            'rank_math_description':meta_desc,'rank_math_robots':['index','follow']}}
                r_rm = requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta",json=rm_payload,auth=(WP_USER,WP_APP_PASSWORD),timeout=10)
                if r_rm.status_code in (200,201): log("Rank Math SEO guardado",'exito')
            except: pass
            return url_articulo, slug_cat
        else:
            log(f"Error WP: {r.get('message','desconocido')}",'error')
    except Exception as e:
        log(f"Excepcion WP: {e}",'error')
    return None, None

# ══════════════════════════════════════════════════════════
# MAIN V22.0.1
# ══════════════════════════════════════════════════════════
def main():
    print("\n" + "="*60)
    print(f"VERDAD HOY BOT - {VERSION_BOT}")
    print(f"  Modo: {MAX_BORRADORES_DIA} borradores por corrida")
    print(f"  Workflow: 1 corrida/día (recomendado 10:00 UTC)")
    print(f"  Temas: pool evergreen predefinido ({len(POOL_EVERGREEN)} temas)")
    print(f"  Títulos: MIXTOS (preguntas + afirmaciones con número)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*60)

    h = cargar_historial()
    rotacion = cargar_rotacion_temas()

    temas_dia = seleccionar_temas_dia(rotacion, n=MAX_BORRADORES_DIA)
    if not temas_dia:
        log("Sin temas disponibles en el pool", 'error')
        return None

    log(f"Temas seleccionados para hoy:", 'info')
    for i, t in enumerate(temas_dia):
        log(f"  [{i+1}] {t['tema']} ({t['categoria']})", 'info')

    borradores_ok = 0
    urls_publicadas = []

    for indice, tema_config in enumerate(temas_dia):
        log(f"\n{'='*50}", 'info')
        log(f"PROCESANDO TEMA {indice+1}/{len(temas_dia)}: {tema_config['tema'][:60]}", 'info')
        log(f"  Categoría: {tema_config['categoria']} | Keyword: {tema_config['keyword']}", 'info')

        dup, razon = tema_ya_publicado(h, tema_config['keyword'], tema_config['tema'])
        if dup:
            log(f"Tema ya publicado ({razon}) — saltando", 'advertencia')
            registrar_tema_publicado(rotacion, tema_config)
            continue

        fuentes_tavily, answer_tavily = buscar_contexto_evergreen(
            tema_config['tema'], tema_config['keyword'], n_resultados=5
        )

        img_destacada, imagenes_adicionales = obtener_imagenes_articulo(
            fuentes_tavily=fuentes_tavily,
            keyword=tema_config['keyword'],
            categoria=tema_config['categoria'],
            titulo=tema_config['tema']
        )

        if not img_destacada:
            log("Sin imagen destacada — usando generada", 'advertencia')
            img_destacada = crear_imagen_titulo(tema_config['tema'], tema_config['categoria'])

        if not img_destacada:
            log("No se pudo obtener imagen — saltando tema", 'error')
            continue

        url_wp, slug_cat = publicar_borrador_evergreen(
            tema_config=tema_config,
            fuentes_tavily=fuentes_tavily,
            answer_tavily=answer_tavily,
            img_destacada_path=img_destacada,
            imagenes_adicionales=imagenes_adicionales,
            indice=indice
        )

        for img_path in [img_destacada] + imagenes_adicionales:
            try:
                if img_path and os.path.exists(img_path): os.remove(img_path)
            except: pass

        if url_wp:
            borradores_ok += 1
            urls_publicadas.append(url_wp)
            h = guardar_en_historial(h, url_wp, tema_config['tema'],
                                      tema_config['keyword'], tema_config['tema'])
            registrar_tema_publicado(rotacion, tema_config)
            log(f"✅ Borrador {borradores_ok}/{MAX_BORRADORES_DIA} — {url_wp}", 'exito')
        else:
            log(f"No se pudo crear borrador para tema {indice+1}", 'error')
            registrar_tema_publicado(rotacion, tema_config)

        if indice < len(temas_dia) - 1:
            log("Esperando 10s antes del siguiente tema...", 'info')
            time.sleep(10)

    print("\n" + "="*60)
    log(f"CORRIDA COMPLETADA: {borradores_ok}/{MAX_BORRADORES_DIA} borradores creados",
        'exito' if borradores_ok > 0 else 'advertencia')
    for i, url in enumerate(urls_publicadas):
        log(f"  [{i+1}] {url}", 'info')
    print("="*60)

    return borradores_ok > 0

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0)
    except Exception as e:
        log(f"Error crítico: {e}",'error')
        import traceback
        traceback.print_exc()
        exit(1)
