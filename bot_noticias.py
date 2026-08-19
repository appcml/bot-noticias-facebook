#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias - V19.0.0
CAMBIOS V19:
  - PUBLICACION MIXTA: 4 directas (publish) + 2 evergreen (draft)
  - FOCO LATAM POR TIERS: Tier1=Chile/Argentina/Mexico (+15), Tier2=Colombia/Brasil (+10), Tier3=resto (+5)
  - RANK MATH 80+ SIN EDICION: keyword al inicio titulo, titulo nunca cortado, power word,
    numero en titulo, slug max 50 chars, keyword en parrafo 1 antes palabra 80,
    keyword en 2+ H2, densidad 1-1.5%, tabla de contenidos, parrafos cortos,
    2 enlaces internos, dofollow externo, alt=keyword, meta 150-160 chars keyword al inicio
  - AEO reforzado: entidad+cargo+dato verificable en primeros 2 parrafos
  - Parrafo nativo generado por IA con tono VerdadHoy
  - FIX titulo cortado: generar_titulo_seo_completo() nunca corta palabras
"""
VERSION_BOT = "V19.0.0"

import requests, feedparser, re, hashlib, json, os, random, time, unicodedata
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse

# ── PUBLICACION MIXTA ──────────────────────────────────────
MAX_POSTS_DIA_DIRECTOS   = 4
MAX_POSTS_DIA_BORRADORES = 2
MAX_POSTS_WP_DIA         = MAX_POSTS_DIA_DIRECTOS + MAX_POSTS_DIA_BORRADORES

# ── TIERS GEOGRAFICOS V19 ──────────────────────────────────
LATAM_TIER1 = ['chile', 'argentina', 'mexico']
LATAM_TIER2 = ['colombia', 'brasil']
LATAM_TIER3 = ['venezuela','peru','ecuador','bolivia','uruguay','paraguay',
               'cuba','el_salvador','guatemala','honduras','costa_rica',
               'panama','rep_dom','haiti','nicaragua','puerto_rico',
               'guyana','surinam','belice']
BONUS_TIER1, BONUS_TIER2, BONUS_TIER3 = 15, 10, 5

CUOTAS_CONTROL_PATH = 'estado_cuotas.json'

CUOTAS_CATEGORIA = {
    'latinoamerica':   {'cuota':0.25,'cpm_relativo':1.18,'brand_safe':True},
    'deportes':        {'cuota':0.18,'cpm_relativo':1.25,'brand_safe':True},
    'economia':        {'cuota':0.15,'cpm_relativo':1.55,'brand_safe':True},
    'tecnologia':      {'cuota':0.12,'cpm_relativo':1.45,'brand_safe':True},
    'entretenimiento': {'cuota':0.10,'cpm_relativo':1.20,'brand_safe':True},
    'politica':        {'cuota':0.05,'cpm_relativo':1.10,'brand_safe':False},
    'ciencia':         {'cuota':0.03,'cpm_relativo':1.40,'brand_safe':True},
    'salud':           {'cuota':0.03,'cpm_relativo':1.40,'brand_safe':True},
    'medio_ambiente':  {'cuota':0.03,'cpm_relativo':1.28,'brand_safe':True},
    'mundo':           {'cuota':0.03,'cpm_relativo':1.00,'brand_safe':True},
    'guerra':          {'cuota':0.01,'cpm_relativo':0.90,'brand_safe':False},
    'desastre':        {'cuota':0.01,'cpm_relativo':0.95,'brand_safe':False},
    'clima':           {'cuota':0.01,'cpm_relativo':1.30,'brand_safe':True},
    'crimen':          {'cuota':0.00,'cpm_relativo':0.85,'brand_safe':False},
    'educacion':       {'cuota':0.00,'cpm_relativo':1.35,'brand_safe':True},
    'religion':        {'cuota':0.00,'cpm_relativo':1.00,'brand_safe':True},
    'general':         {'cuota':0.00,'cpm_relativo':1.00,'brand_safe':True},
}

NEWS_API_KEY       = os.getenv('NEWS_API_KEY','')
NEWSDATA_API_KEY   = os.getenv('NEWSDATA_API_KEY','')
GNEWS_API_KEY      = os.getenv('GNEWS_API_KEY','')
FB_PAGE_ID         = os.getenv('FB_PAGE_ID','')
FB_ACCESS_TOKEN    = os.getenv('FB_ACCESS_TOKEN','')
WP_URL             = os.getenv('WP_URL','https://verdadhoy.com')
WP_USER            = os.getenv('WP_USER','verdadhoy_admin')
WP_APP_PASSWORD    = os.getenv('WP_APP_PASSWORD','')
PINTEREST_TOKEN    = os.getenv('PINTEREST_TOKEN','')
GROQ_API_KEY       = os.getenv('GROQ_API_KEY','')
GEMINI_API_KEY     = os.getenv('GEMINI_API_KEY','')
TAVILY_API_KEY     = os.getenv('TAVILY_API_KEY','')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY','')
OPENAI_API_KEY     = os.getenv('OPENAI_API_KEY','')
GITHUB_TOKEN       = os.getenv('GITHUB_TOKEN','')
GITHUB_REPO        = os.getenv('GITHUB_REPOSITORY','')

HISTORIAL_PATH      = os.getenv('HISTORIAL_PATH','historial_publicaciones.json')
ESTADO_WP_PATH      = 'estado_wp.json'
ESTADO_FB_PATH      = 'estado_fb.json'
PENDING_VIDEOS_DIR  = 'pending_videos'
ESTADO_PENDING_PATH = 'estado_pending_videos.json'
ESTADO_LATAM_PATH   = 'estado_cuotas_latam.json'

MODO_LATAM = os.getenv('MODO_LATAM','false').lower() == 'true'
TIEMPO_ENTRE_WP_MIN = 230
TIEMPO_ENTRE_FB_MIN = 90
MAX_POSTS_WP_DIA_CHILE  = 3
MAX_POSTS_WP_DIA_LATAM  = 3
MAX_POSTS_WP_DIA_TOTAL  = 6
REINTENTAR_CALIDAD_IA   = True
PUBLICAR_EN_FACEBOOK    = False
UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 300
DIAS_HISTORIAL             = 14

HORARIOS_PICO_UTC = [(0,4),(10,14),(18,22)]

CATEGORIA_WP = {
    'guerra':'internacional','desastre':'internacional','crimen':'internacional',
    'religion':'internacional','educacion':'internacional','general':'internacional',
    'politica':'politica','economia':'economia','tecnologia':'tecnologia',
    'ciencia':'ciencia-y-salud','salud':'ciencia-y-salud','deportes':'deportes',
    'entretenimiento':'entretenimiento','latinoamerica':'latinoamerica',
    'clima':'medio-ambiente','medio_ambiente':'medio-ambiente','mundo':'mundo',
}

CATEGORIAS_ROTACION_WP = [
    'politica','africa','asia','ciencia-y-salud','deportes','economia',
    'entretenimiento','europa','internacional','latinoamerica',
    'medio-ambiente','medio-oriente','mundo','oceania','tecnologia',
]

TABLEROS_PINTEREST = {
    'guerra':'Noticias del Mundo','politica':'Politica','economia':'Economia',
    'tecnologia':'Tecnologia','desastre':'Noticias del Mundo','deportes':'Noticias del Mundo',
    'ciencia':'Noticias del Mundo','salud':'Noticias del Mundo',
    'entretenimiento':'Noticias del Mundo','latinoamerica':'Latinoamerica',
    'clima':'Noticias del Mundo','medio_ambiente':'Noticias del Mundo',
    'educacion':'Noticias del Mundo','religion':'Noticias del Mundo',
    'crimen':'Noticias del Mundo','mundo':'Noticias del Mundo','general':'Noticias del Mundo',
}

_cache_tableros_pinterest = {}
_cache_categorias_wp      = {}
_cache_tags_wp            = {}

CTAS_POR_TEMA = {
    'guerra':["¿Crees que esto puede escalar? Dinos 👇"],
    'politica':["¿Estás de acuerdo? SÍ o NO 👇"],
    'economia':["¿Sientes esto en tu bolsillo? 👇"],
    'tecnologia':["¿La IA nos ayuda o nos amenaza? 👇"],
    'desastre':["Nuestros pensamientos con los afectados 🙏"],
    'deportes':["¿Qué opinas? Comenta 👇"],
    'ciencia':["¿Lo sabías? Dinos 👇"],
    'salud':["¿Cuidas tu salud? Comparte 👇"],
    'entretenimiento':["¿Lo viste? ¿Qué te pareció? 👇"],
    'latinoamerica':["¿Cómo afecta esto a tu país? 👇"],
    'clima':["¿Sientes el cambio climático? 👇"],
    'medio_ambiente':["¿Qué haces por el planeta? 👇"],
    'educacion':["¿La educación mejora el mundo? SÍ o NO 👇"],
    'religion':["¿Qué piensas? Comenta 👇"],
    'crimen':["¿La justicia actúa bien? 👇"],
    'mundo':["¿Qué piensas del mundo hoy? 👇"],
    'general':["¿Qué opinas? Comenta 👇"],
}

PALABRAS_ALTA_PRIORIDAD = [
    "copa libertadores","copa sudamericana","eliminatorias sudamericanas","conmebol",
    "mundial 2026","copa del mundo","boric","milei","lula","sheinbaum","petro",
    "maduro","bukele","litio chile","cobre chile","petroleo venezuela",
    "peso chileno","peso argentino","inflacion argentina","inflacion chile",
    "inflacion mexico","elecciones chile","elecciones argentina","elecciones colombia",
    "terremoto chile","sismo chile","festival de viña","seleccion chilena","la roja",
    "colo-colo","universidad de chile","guerra","conflicto armado","invasion",
    "ofensiva militar","bombardeo","misiles","ataque aereo","drones militares",
    "movilizacion militar","tropas","escalada de tension","amenaza nuclear",
    "armas nucleares","terrorismo","atentado","ataque terrorista",
    "ucrania","rusia","israel","gaza","iran","china","taiwan","corea del norte",
    "otan","nato","brics","medio oriente","crisis humanitaria","refugiados",
    "crisis de gobierno","golpe de estado","estado de emergencia","negociaciones de paz",
    "alto el fuego","sanciones internacionales","economia mundial","inflacion",
    "crisis economica","recesion","petroleo","gas","crisis energetica",
    "ciberataque","hackeo","inteligencia artificial","ultima hora","urgente","breaking",
    "putin","zelensky","trump","biden","netanyahu","xi jinping","kim jong un","macron",
    "hamas","hezbollah","isis","taliban","houthis","elon musk",
    "champions league","nba finals","super bowl","formula 1","grand prix",
    "olimpiadas","juegos olimpicos","fichaje","gol","campeon",
    "messi","mbappe","neymar","cristiano ronaldo","lebron james","verstappen",
    "djokovic","alcaraz","oscar 2026","grammy","emmy",
    "taylor swift","bad bunny","shakira","beyonce","karol g","maluma",
    "j balvin","rauw alejandro","rosalia","daddy yankee",
    "netflix estreno","disney plus","marvel","star wars",
]

PALABRAS_MEDIA_PRIORIDAD = [
    "economia","mercados","FMI","banco mundial","tecnologia","innovacion",
    "salud","educacion","medio ambiente","cambio climatico","comercio internacional",
]

BLACKLIST_TITULOS = [
    r'^\s*última hora\s*$',r'^\s*breaking news\s*$',
    r'^\s*noticias de hoy\s*$',r'^\s*\d+\s*$',
]

BLACKLIST_CONTENIDO_SPAM = [
    "rojabet","bet365","1xbet","betano","codere","tombola","sportingbet","bwin",
    "pokerstars","888casino","betfair","unibet","casino online","apuestas deportivas",
    "apuestas en linea","bono sin deposito","giros gratis casino","tragamonedas",
    "tragaperras","ruleta online","poker online","blackjack online","slots online",
    "juegos de azar","casa de apuestas","cuotas de apuestas","donde apostar",
    "para apostar","pronóstico deportivo","pronostico deportivo","picks deportivos",
    "predicciones deportivas","codigo promocional","cupon descuento",
    "oferta exclusiva para","top 10 mejores","como ganar dinero con",
    "prestamo rapido online","bitcoin gratis","cripto gratis","ganar criptomonedas",
]


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
        path   = parsed.path.lower().rstrip('/')
        path   = re.sub(r'/index\.(html|php|htm|asp)$','',path)
        path   = re.sub(r'\.html?$','',path)
        return f"{netloc}{path}"
    except:
        return url.lower().strip()

def extraer_dominio(url):
    try:
        parts = urlparse(url).netloc.lower().split('.')
        return '.'.join(parts[-2:]) if len(parts) > 2 else '.'.join(parts)
    except:
        return ""

def similitud_titulos(t1, t2):
    if not t1 or not t2: return 0.0
    stopwords = {'el','la','los','las','un','una','en','de','del','al','y','o',
                 'que','con','por','para','sobre','entre','the','of','and','to',
                 'in','is','a','an','it','as','at','by','from','not','or'}
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

_FUENTES_INCRUSTADAS = re.compile(
    r'\b(LISTIN DIARIO|EL PAÍS|El País|BBC|CNN|Reuters|AFP|AP News|INFOBAE|Infobae|'
    r'EFE|France 24|DW|Euronews|RT|Al Jazeera|The Guardian|NYT|New York Times|'
    r'Washington Post|Clarín|Clarin|El Mundo|La Nación|La Nacion|Milenio)\b[,.]?\s*',
    re.IGNORECASE
)
_FRASES_SUSCRIPCION = re.compile(
    r'(Recib[ií]\s+en\s+tu\s+mail[^.]*\.?|Suscr[ií]bete\s+[^.]*\.?|'
    r'Registrate\s+[^.]*\.?|Newsletter\s+[^.]*\.?|Descarga\s+la\s+app\s+[^.]*\.?|'
    r'Síguenos\s+en\s+[^.]*\.?|Leer\s+más[^.]*\.?|Lee\s+también[^.]*\.?|'
    r'Fuente:\s*[A-Z][^.]*\.?|Copyright\s+[^.]*\.?|©[^.]*\.?)',
    re.IGNORECASE
)

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
        if keyword.lower() in txt:
            return True, keyword
    return False, None


# ══════════════════════════════════════════════════════════
# DETECCIÓN DE TEMA Y REGIÓN
# ══════════════════════════════════════════════════════════
def detectar_tema(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(p in txt for p in ["terremoto","sismo","huracan","inundacion","tsunami","erupcion volcanica","tormenta tropical","derrumbe","aluvion","alerta de tsunami","catastrofe natural","incendio forestal masivo"]):
        return 'desastre'
    if any(p in txt for p in ["asesinato","homicidio","narcotrafico","cartel","crimen organizado","mafia","fraude millonario","banda criminal","sicario","feminicidio","masacre","narcotraficante"]):
        return 'crimen'
    if any(p in txt for p in ["guerra","bombardeo","misil balístico","conflicto armado","invasion","invasión","tropas rusas","tropas ucranianas","hamas","hezbollah","ataque aéreo","ataque aereo","ofensiva militar","drones militares","drones de combate","muertos en combate","bombardeado","ataque terrorista","atentado terrorista","alto el fuego","cese del fuego","zona de guerra","guerra civil","milicias armadas"]):
        return 'guerra'
    if any(p in txt for p in ["futbol","fútbol","copa libertadores","copa sudamericana","copa del mundo","mundial de futbol","mundial 2026","champions league","premier league","laliga","la liga","eliminatoria","gol","penalti","seleccion chilena","seleccion argentina","seleccion colombiana","seleccion brasileña","seleccion mexicana","la roja","colo-colo","universidad de chile","nba","baloncesto","tenis","djokovic","alcaraz","wimbledon","formula 1","f1","gran premio","olimpiadas","juegos olimpicos","atletismo","boxeo","ufc","messi","cristiano ronaldo","mbappe","neymar","lebron james","verstappen","medalla de oro"]):
        return 'deportes'
    if any(p in txt for p in ["pelicula estreno","estreno de pelicula","trailer oficial","oscar","grammy","emmy","golden globe","latin grammy","festival de cine","cannes","album musical","nuevo album","gira musical","concierto de","lanzamiento musical","videoclip","spotify charts","billboard charts","taylor swift","bad bunny","shakira","beyonce","rihanna","karol g","maluma","j balvin","rauw alejandro","rosalia","daddy yankee","netflix estrena","netflix serie","disney plus estreno","serie de tv","actor de cine","actriz premiada","reggaeton","celebrity","celebridad"]):
        return 'entretenimiento'
    if any(p in txt for p in ["inteligencia artificial","chatgpt","openai","gemini google","deepseek","llm ","modelo de lenguaje","ia generativa","robot","ciberataque","hackeo","ciberseguridad","ransomware","elon musk","spacex","starlink","samsung galaxy","apple iphone","chip semiconductor","nvidia gpu","quantum computing","startup tecnologica","fintech","blockchain","criptomoneda","5g","6g","metaverso","realidad virtual","software","app nueva","plataforma digital","red neuronal","machine learning","innovacion tecnologica"]):
        return 'tecnologia'
    if any(p in txt for p in ["inflacion","inflación","recesion","bolsa de valores","mercado financiero","dolar","dólar","euro cae","euro sube","tipo de cambio","fmi acuerdo","banco central","reserva federal","crisis economica","aranceles","exportaciones","importaciones","pib","producto interno bruto","desempleo","wall street","nasdaq","dow jones","petroleo precio","inversion extranjera","deficit fiscal","devaluacion","libre comercio"]):
        return 'economia'
    if any(p in txt for p in ["cambio climatico","cambio climático","calentamiento global","temperatura record","sequia","sequía","incendio forestal","contaminacion ambiental","co2 emisiones","medio ambiente","cop30","cop29","biodiversidad","extincion de especies","deforestacion","amazonia","reserva natural","energia renovable","energia solar","energia eolica","huella de carbono","glaciar","deshielo","nivel del mar"]):
        return 'medio_ambiente'
    if any(p in txt for p in ["cancer","cáncer","enfermedad","hospital","medico","pandemia","vacuna","virus","salud publica","oms","epidemia","brote infeccioso","medicamento","cirugia","cirugía","tratamiento médico","farmaco","fármaco","mortalidad","obesidad","diabetes","hipertension","salud mental","antibiotico","variante viral","oncologia","cardiologia"]):
        return 'salud'
    if any(p in txt for p in ["descubrimiento cientifico","descubrimiento científico","agencia espacial nasa","nasa lanza","cohete espacial","satelite lanzado","planeta","universo","agujero negro","exoplaneta","investigacion cientifica","astronomia","telescopio espacial","marte exploracion","particula subatomica","adn descubrimiento","premio nobel de","fisica cuantica"]):
        return 'ciencia'
    if any(p in txt for p in ["eleccion","elección","elecciones presidenciales","presidente anuncia","gobierno de","gabinete presidencial","golpe de estado","diplomacia","cumbre diplomatica","sancion diplomatica","g7","g20","onu debate","referendum","parlamento aprueba","congreso aprueba","primer ministro","canciller anuncia","politica exterior","campana electoral","partido politico","decreto presidencial","reforma legislativa","diputado","senador","macron","scholz","modi","xi jinping","putin","zelensky","erdogan","netanyahu","trump anuncia","sheinbaum anuncia","boric anuncia","milei anuncia","petro anuncia","lula anuncia","maduro anuncia"]):
        return 'politica'
    if any(p in txt for p in ["reforma educativa","sistema educativo","becas universitarias","universidad publica","escuelas publicas","maestros en huelga","profesores protestan","prueba pisa"]):
        return 'educacion'
    if any(p in txt for p in ["papa francisco","vaticano","iglesia católica","islam","judaismo","budismo","hinduismo","mezquita","sinagoga","catedral","pontifice","cardenal","encíclica","pastor evangelico","obispo"]):
        return 'religion'
    if any(p in txt for p in ["chile","chilena","chileno","boric","carabineros","codelco","mexico","mexicano","mexicana","cdmx","sheinbaum","pemex","argentina","argentino","buenos aires","milei","brasil","brazil","brasileño","lula","sao paulo","colombia","colombiano","bogota","petro","peru","peruano","boluarte","venezuela","venezolano","maduro","ecuador","ecuatoriano","noboa","bolivia","boliviano","uruguay","uruguayo","paraguay","paraguayo","cuba","cubano","nicaragua","guatemala","honduras","el salvador","bukele","panamá","costa rica","republica dominicana","dominicano","haiti","haitiano","america latina","latinoamerica","latinoamericano","latam","centroamerica","caribe","sudamerica"]):
        return 'latinoamerica'
    if any(p in txt for p in ["africa","asia pacifico","europa occidental","oriente medio","naciones unidas","onu cumbre","cumbre mundial","union europea","brics"]):
        return 'mundo'
    return 'general'

KEYWORDS_CHILE = [
    "chile","chilena","chileno","chilenas","chilenos","santiago","valparaíso",
    "valparaiso","concepción","concepcion","antofagasta","temuco","viña del mar",
    "vina del mar","la serena","rancagua","talca","arica","iquique","puerto montt",
    "gabriel boric","boric","gobierno de chile","congreso chileno","senado chileno",
    "carabineros","pdi chile","banco central de chile","peso chileno",
    "conaf","codelco","enap chile","metro de santiago","sernac","sii chile",
    "bolsa de santiago","ipsa","uf chilena","latam airlines chile","sky airline",
    "festival de viña","festival de viña del mar","selección chilena","la roja",
    "colo colo","universidad de chile","universidad católica","mapuche","araucanía",
]

KEYWORDS_LATAM_PAISES = {
    'mexico':     ["méxico","mexico","mexicano","mexicana","cdmx","ciudad de mexico","sheinbaum","pemex","guadalajara","monterrey","puebla"],
    'argentina':  ["argentina","argentino","buenos aires","milei","merval","peso argentino","rosario ar","córdoba ar"],
    'colombia':   ["colombia","colombiano","bogotá","bogota","petro","medellín","medellin","cali colombia","cartagena colombia","barranquilla"],
    'brasil':     ["brasil","brazil","brasileño","lula","sao paulo","río de janeiro","rio de janeiro","brasilia","real brasileiro"],
    'venezuela':  ["venezuela","venezolano","maduro","caracas","bolívar venezolano","maracaibo"],
    'peru':       ["perú","peru","peruano","lima perú","lima peru","boluarte","arequipa","cusco"],
    'ecuador':    ["ecuador","ecuatoriano","quito","noboa","guayaquil"],
    'bolivia':    ["bolivia","boliviano","la paz bolivia","santa cruz de la sierra"],
    'uruguay':    ["uruguay","uruguayo","montevideo","orsi"],
    'paraguay':   ["paraguay","paraguayo","asunción","asuncion"],
    'cuba':       ["cuba","cubano","la habana"],
    'nicaragua':  ["nicaragua","nicaragüense","ortega nicaragua","managua"],
    'guatemala':  ["guatemala","guatemalteco","ciudad de guatemala"],
    'honduras':   ["honduras","hondureño","tegucigalda"],
    'el_salvador':["el salvador","salvadoreño","bukele","san salvador"],
    'panama':     ["panamá","panama","panameño","ciudad de panamá"],
    'costa_rica': ["costa rica","costarricense","san josé cr"],
    'rep_dom':    ["república dominicana","dominicano","santo domingo"],
    'haiti':      ["haití","haiti","haitiano","puerto príncipe"],
    'puerto_rico':["puerto rico","puertorriqueño","san juan pr"],
    'guyana':     ["guyana","guyanés","georgetown guyana"],
    'surinam':    ["surinam","surinamés","paramaribo"],
    'belice':     ["belice","beliceño","belmopán"],
}

KEYWORDS_REGIONES = {
    'europa':["españa","espana","francia","alemania","italia","reino unido","inglaterra","escocia","gales","irlanda","portugal","países bajos","paises bajos","holanda","bélgica","belgica","suiza","austria","polonia","ucrania","rusia","kremlin","rumania","hungría","grecia","suecia","noruega","dinamarca","finlandia","bruselas","unión europea","union europea","otan","vaticano","madrid","París","paris","berlín","berlin","londres","roma","putin","zelenski"],
    'asia':["china","japón","japon","corea del sur","corea del norte","india","pakistán","indonesia","filipinas","vietnam","tailandia","malasia","singapur","taiwán","taiwan","mongolia","pekín","beijing","tokio","seúl","nueva delhi","xi jinping","kim jong"],
    'africa':["nigeria","sudáfrica","sudafrica","egipto","kenia","etiopía","marruecos","argelia","túnez","libia","sudán","congo","angola","mozambique","ghana","senegal","ruanda","somalia","zimbabue","tanzania","uganda","el cairo","lagos nigeria","johannesburgo","nairobi"],
    'medio_oriente':["israel","palestina","gaza","cisjordania","hamás","hamas","hezbolá","hezbola","irán","iran","teherán","teheran","irak","bagdad","siria","damasco","líbano","libano","beirut","arabia saudita","riad","yemen","jordania","qatar","catar","emiratos árabes","dubái","kuwait","turquía","turquia","ankara","estambul","netanyahu"],
    'oceania':["australia","nueva zelanda","fiyi","papua nueva guinea","canberra","sídney","sydney","wellington","auckland","melbourne"],
}

REGION_SLUG_WP = {
    'europa':'europa','asia':'asia','africa':'africa',
    'medio_oriente':'medio-oriente','oceania':'oceania','mundo':'mundo',
}

def detectar_region_internacional(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    puntajes = {region: sum(1 for kw in kws if kw in txt) for region, kws in KEYWORDS_REGIONES.items()}
    mejor_region, mejor_puntaje = max(puntajes.items(), key=lambda x: x[1])
    if mejor_puntaje == 0: return 'mundo'
    return mejor_region

KEYWORDS_ESPANA_DOMESTICO = [
    "ayuso","sánchez","pedro sanchez","psoe","vox"," pp ","sumar",
    "congreso de los diputados","senado español","moncloa","casa real española",
    "felipe vi","junta electoral central","madrid","barcelona","sevilla","valencia",
    "andalucía","cataluña","país vasco","galicia españa","comunidad de madrid",
    "generalitat","ayuntamiento de madrid","guardia civil","policía nacional española",
    "rtve","el corte inglés","renfe","adif",
]

def es_noticia_espana_domestica(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    tiene_espana = any(kw in txt for kw in KEYWORDS_ESPANA_DOMESTICO)
    if not tiene_espana: return False
    if any(kw in txt for pais_kws in KEYWORDS_LATAM_PAISES.values() for kw in pais_kws): return False
    if any(kw in txt for kw in KEYWORDS_CHILE): return False
    return True

def es_noticia_chile(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    return any(kw in txt for kw in KEYWORDS_CHILE)

def es_noticia_latam_sin_chile(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(kw in txt for kw in KEYWORDS_CHILE): return False, None
    for pais, keywords in KEYWORDS_LATAM_PAISES.items():
        if any(kw in txt for kw in keywords): return True, pais
    if any(kw in txt for kw in ["latinoamérica","latinoamerica","america latina","centroamerica","caribe","sudamerica"]):
        return True, 'latam_general'
    return False, None

def detectar_pais_latam(titulo, descripcion=""):
    """V19: detecta el tier del país para el bonus de puntaje."""
    txt = f"{titulo} {descripcion}".lower()
    if any(kw in txt for kw in KEYWORDS_CHILE): return 'chile', LATAM_TIER1
    for pais, keywords in KEYWORDS_LATAM_PAISES.items():
        if any(kw in txt for kw in keywords):
            if pais in LATAM_TIER1: return pais, LATAM_TIER1
            if pais in LATAM_TIER2: return pais, LATAM_TIER2
            return pais, LATAM_TIER3
    return None, None


# ══════════════════════════════════════════════════════════
# SEO: TÍTULO, SLUG, KEYWORDS V19
# ══════════════════════════════════════════════════════════

POWER_WORDS_ES = {
    'clave','crucial','decisivo','decisiva','histórico','histórica',
    'alerta','récord','record','oficial','confirmado','confirmada',
    'sorprendente','revolucionario','revolucionaria','explosivo','explosiva',
    'inesperado','inesperada','urgente','impactante','revelador','reveladora',
    'inédito','inédita','definitivo','definitiva','polémico','polémica',
    'esencial','crítico','crítica','exclusivo','exclusiva','extraordinario',
    'extraordinaria','primero','primera','único','única','máximo','mínimo',
    'grave','vital','nueva','nuevo','mejor','peor','mayor','menor',
    'real','verdad','secreto','secretos','brutal','radical','total','final',
    'absoluto','absoluta','masivo','masiva','sin precedentes','millones',
    'millonario','millonaria','logra','logró','conquista','histórico',
}

STOPWORDS_SLUG = {
    'de','del','la','las','el','los','un','una','unos','unas',
    'y','e','o','u','a','al','en','por','para','con','sin',
    'que','se','su','sus','es','son','ha','han','fue','era',
    'lo','le','les','me','te','nos','ante','bajo','desde',
    'hacia','hasta','sobre','tras','entre','como','pero',
    'si','no','ni','ya','aun','aunque','sino'
}

def generar_slug_seo(titulo, max_chars=50):
    """
    V19: genera slug SEO limpio con límite de CHARS (no palabras).
    Antes era max_palabras=8 sin límite de chars → URLs largas penalizadas.
    Ahora máx 50 chars sin cortar palabras a la mitad.
    """
    if not titulo: return ''
    nfkd = unicodedata.normalize('NFKD', titulo)
    sin_acentos = ''.join(c for c in nfkd if not unicodedata.combining(c))
    texto = sin_acentos.lower()
    texto = re.sub(r'[^a-z0-9\s]',' ',texto)
    palabras = [p for p in texto.split() if p not in STOPWORDS_SLUG and len(p) > 2]
    slug = ''
    for palabra in palabras:
        candidato = (slug + '-' + palabra) if slug else palabra
        if len(candidato) > max_chars:
            break
        slug = candidato
    slug = re.sub(r'-{2,}','-',slug).strip('-')
    return slug or 'noticia'

def generar_titulo_seo_completo(keyword, power_word, dato_concreto='', max_chars=55):
    """
    V19 FIX: construye título SEO en orden keyword→power_word→dato.
    NUNCA corta palabras a la mitad. Si no cabe, reduce el dato,
    luego la power_word. El resultado siempre es frase completa con sentido.
    El sufijo ' | Verdad Hoy' (12 chars) NO va en este campo — se agrega al vuelo.
    """
    # Intento 1: keyword + dato + power_word
    if dato_concreto:
        titulo = f"{keyword}: {dato_concreto} {power_word}".strip()
        if len(titulo) <= max_chars: return titulo
    # Intento 2: keyword + power_word + dato (más corto)
    if dato_concreto:
        titulo = f"{keyword} {power_word}: {dato_concreto}".strip()
        if len(titulo) <= max_chars: return titulo
    # Intento 3: keyword + power_word
    titulo = f"{keyword} {power_word}".strip()
    if len(titulo) <= max_chars: return titulo
    # Intento 4: solo keyword (recortada en palabra completa)
    palabras = keyword.split()
    titulo = ''
    for p in palabras:
        candidato = (titulo + ' ' + p).strip()
        if len(candidato) > max_chars: break
        titulo = candidato
    return titulo or keyword[:max_chars]

PALABRAS_TRANSICION = [
    'sin embargo','además','por otro lado','en consecuencia','a su vez',
    'no obstante','por ejemplo','en primer lugar','finalmente','asimismo',
    'por lo tanto','en efecto','por su parte','en tanto','de hecho',
    'en este sentido','como resultado','en cambio','cabe destacar',
    'mientras tanto','por consiguiente','en última instancia','en tal caso',
    'aunque','aun así','pese a','a pesar de','de esta manera','de este modo',
    'en ese sentido','en esa línea','en la misma línea','bajo este escenario',
    'en ese contexto','en este marco','eso sí','cabe mencionar','vale destacar',
    'a la vez','al mismo tiempo','dado que','ya que','debido a esto',
    'por su lado','de igual forma','de igual manera','en definitiva',
]

INICIOS_META_PROHIBIDOS = ('descubre','conoce','entérate','entera','sabías')
CATEGORIAS_EVERGREEN = {'ciencia','tecnologia','medio_ambiente','salud'}

KEYWORDS_SEO_CATEGORIA = {
    'latinoamerica': {'principal':'noticias Latinoamérica','secundarias':['América Latina hoy','últimas noticias LATAM','sucesos latinoamericanos'],'modificadores':['crece la tensión','anuncia','aprueba reforma','genera crisis','impacta la región']},
    'chile':         {'principal':'noticias Chile','secundarias':['últimas noticias Chile','actualidad Chile','sucesos Chile hoy'],'modificadores':['Gobierno de Chile','Boric anuncia','Congreso aprueba','impacta a los chilenos']},
    'economia':      {'principal':'economía','secundarias':['dólar hoy','inflación','mercados financieros','crisis económica'],'modificadores':['sube','cae','reforma económica','impacto económico','afecta el bolsillo']},
    'politica':      {'principal':'política','secundarias':['gobierno','elecciones','congreso','presidente anuncia'],'modificadores':['anuncia','aprueba','reforma','decreto presidencial','genera polémica']},
    'tecnologia':    {'principal':'tecnología','secundarias':['inteligencia artificial','innovación','startups','IA'],'modificadores':['revoluciona','lanza','presenta','cambia todo','transforma']},
    'deportes':      {'principal':'deportes','secundarias':['fútbol','Copa Libertadores','eliminatorias','Mundial 2026'],'modificadores':['gana','pierde','clasifica','sorprende','histórico']},
    'entretenimiento':{'principal':'entretenimiento','secundarias':['música latina','cine','series','artistas'],'modificadores':['lanza','estrena','conquista','sorprende','regresa']},
    'salud':         {'principal':'salud','secundarias':['medicina','vacuna','tratamiento','OMS'],'modificadores':['alerta','descubre','recomienda','advierte','avanza']},
    'ciencia':       {'principal':'ciencia','secundarias':['descubrimiento','investigación','espacio','NASA'],'modificadores':['descubre','confirma','revela','sorprende','avanza']},
    'medio_ambiente':{'principal':'medio ambiente','secundarias':['cambio climático','Amazonía','glaciares','energía renovable'],'modificadores':['alerta','amenaza','protege','destruye','impacta']},
    'guerra':        {'principal':'conflicto','secundarias':['guerra','bombardeo','tropas','crisis militar'],'modificadores':['escala','ataca','avanza','amenaza','cesan fuegos']},
    'mundo':         {'principal':'noticias internacionales','secundarias':['noticias del mundo','actualidad global','internacional'],'modificadores':['sacude al mundo','impacta globalmente','genera debate','histórico']},
}

def obtener_keyword_categoria(categoria):
    return KEYWORDS_SEO_CATEGORIA.get(categoria, {}).get('principal', '')


# ══════════════════════════════════════════════════════════
# VALIDACIÓN DE CALIDAD V19
# ══════════════════════════════════════════════════════════
def validar_calidad_articulo(contenido_html, meta_desc, titulo_seo='', categoria='', keyword=''):
    """
    V19: validación Rank Math 80+ reforzada.
    Nuevas reglas vs V18:
      - Keyword en primeros 80 palabras (antes 100)
      - Keyword en al menos 2 H2 (antes 1)
      - Densidad keyword 1-1.5% validada en código
      - Tabla de contenidos presente
      - Párrafos máx 3 líneas
      - Meta descripción empieza con keyword (no solo la contiene)
      - Título empieza con keyword (primeras 3 palabras)
    """
    problemas = []
    texto_plano = re.sub(r'<[^>]+>',' ', contenido_html or '')
    texto_plano = re.sub(r'\s+',' ', texto_plano).strip()
    n_palabras = len(texto_plano.split())

    # 1. Longitud mínima
    if n_palabras < 620:
        problemas.append(f"Solo {n_palabras} palabras — mínimo 620. Desarrolla más con antecedente histórico, cifras y contexto LATAM.")

    # 2. Blockquote obligatorio
    if '<blockquote' not in (contenido_html or ''):
        problemas.append("Falta <blockquote> (Dato destacado) — es obligatorio para Rank Math.")

    # 3. Al menos 4 H2
    n_h2 = len(re.findall(r'<h2', contenido_html or '', flags=re.IGNORECASE))
    if n_h2 < 4:
        problemas.append(f"Solo {n_h2} H2 — mínimo 4, cada uno con ángulo distinto.")

    # 4. Keyword en al menos 2 H2 (V19 nuevo)
    if keyword:
        kw_lower = keyword.lower()
        h2_textos = re.findall(r'<h2[^>]*>(.*?)</h2>', contenido_html or '', flags=re.IGNORECASE|re.DOTALL)
        h2_con_kw = sum(1 for h in h2_textos if kw_lower in re.sub(r'<[^>]+>','',h).lower())
        if h2_con_kw < 2:
            problemas.append(f"Keyword '{keyword}' en solo {h2_con_kw} H2 — debe aparecer en al menos 2.")

    # 5. Keyword en primeros 80 palabras (V19 más estricto)
    if keyword:
        primeras_80 = ' '.join(texto_plano.split()[:80]).lower()
        if keyword.lower() not in primeras_80:
            problemas.append(f"Keyword '{keyword}' no aparece en los primeros 80 palabras — crítico para Rank Math.")

    # 6. Densidad keyword 1-1.5% (V19 nuevo)
    if keyword and n_palabras > 0:
        kw_palabras = len(keyword.split())
        kw_ocurrencias = len(re.findall(re.escape(keyword.lower()), texto_plano.lower()))
        densidad = (kw_ocurrencias * kw_palabras / n_palabras) * 100 if n_palabras > 0 else 0
        if densidad < 0.8:
            problemas.append(f"Densidad keyword {densidad:.1f}% — muy baja. Objetivo: 1-1.5% (usa la keyword ~{max(3, int(n_palabras*0.01))} veces).")
        elif densidad > 2.5:
            problemas.append(f"Densidad keyword {densidad:.1f}% — muy alta (keyword stuffing). Objetivo máx 1.5%.")

    # 7. Tabla de contenidos (V19 nuevo)
    if '<nav' not in (contenido_html or '') and 'tabla-contenidos' not in (contenido_html or '') and 'table-of-contents' not in (contenido_html or ''):
        problemas.append("Falta tabla de contenidos — añade <nav class='tabla-contenidos'> con links a los H2.")

    # 8. Transiciones (mínimo 4)
    texto_lower = texto_plano.lower()
    n_transiciones = sum(1 for p in PALABRAS_TRANSICION if p in texto_lower)
    if n_transiciones < 4:
        problemas.append(f"Solo {n_transiciones} palabras de transición — mínimo 4 (sin embargo, además, por otro lado, en consecuencia...).")

    # 9. Meta descripción longitud
    len_meta = len(meta_desc or '')
    if len_meta < 150 or len_meta > 160:
        problemas.append(f"Meta descripción {len_meta} chars — debe ser 150-160 exacto.")

    # 10. Meta descripción empieza con keyword (V19 nuevo)
    if keyword and meta_desc:
        meta_inicio = meta_desc[:40].lower()
        if keyword.lower() not in meta_inicio:
            problemas.append(f"Meta descripción debe EMPEZAR con la keyword '{keyword}' (primeros 40 chars).")

    # 11. Meta descripción no empieza con palabras prohibidas
    if (meta_desc or '').strip().lower().startswith(INICIOS_META_PROHIBIDOS):
        problemas.append("Meta descripción empieza con palabra prohibida (descubre/conoce/entérate).")

    # 12. Power word en título
    if titulo_seo:
        titulo_lower = titulo_seo.lower()
        tiene_pw = any(pw in titulo_lower for pw in POWER_WORDS_ES)
        if not tiene_pw:
            problemas.append(f"Título '{titulo_seo}' sin power word — añade: clave, crucial, histórico, récord, urgente...")

    # 13. Título empieza con keyword (V19 nuevo)
    if keyword and titulo_seo:
        titulo_inicio = ' '.join(titulo_seo.lower().split()[:3])
        if keyword.lower().split()[0] not in titulo_inicio:
            problemas.append(f"Título debe EMPEZAR con la keyword '{keyword}' (primeras 3 palabras).")

    # 14. Título tiene número
    if titulo_seo and not re.search(r'\d', titulo_seo):
        problemas.append(f"Título sin número — añade cifra cuando el hecho lo permita (porcentaje, fecha, cantidad).")

    return (len(problemas) == 0, problemas)

def calcular_puntaje(titulo, desc):
    titulo = titulo or ""
    desc   = desc or ""
    txt = f"{titulo} {desc}".lower()
    p = 0
    for frase in PALABRAS_ALTA_PRIORIDAD:
        if frase.lower() in txt: p += 7
        else:
            for palabra in frase.lower().split():
                if len(palabra) >= 4 and palabra in txt:
                    p += 3; break
    for frase in PALABRAS_MEDIA_PRIORIDAD:
        for palabra in frase.lower().split():
            if len(palabra) >= 3 and palabra in txt:
                p += 1; break
    if 30 <= len(titulo) <= 150: p += 2
    if len(desc) >= 50: p += 2

    # V19: BONUS POR TIER GEOGRÁFICO (reemplaza el sistema de tiers anterior)
    pais, tier = detectar_pais_latam(titulo, desc)
    if tier == LATAM_TIER1:
        p += BONUS_TIER1
    elif tier == LATAM_TIER2:
        p += BONUS_TIER2
    elif tier == LATAM_TIER3:
        p += BONUS_TIER3

    # Señales regionales genéricas
    señales_regionales = ["latinoamerica","america latina","centroamerica","sudamerica","copa libertadores","copa sudamericana","conmebol","eliminatorias","amazonia","patagonia","atacama"]
    if any(kw in txt for kw in señales_regionales): p += 5

    # Penalización noticias EE.UU./Europa sin conexión LATAM
    if tier is None:
        keywords_no_latam = ["washington dc","white house","congress usa","senate usa","wall street","silicon valley","pentagon","kremlin","bundestag","westminster","downing street"]
        if sum(1 for kw in keywords_no_latam if kw in txt) >= 1: p -= 4
        if es_noticia_espana_domestica(titulo, desc): p -= 6

    # Bonus tema prioritario editorial
    temas_prioritarios = {"economia":["economía","economia","inflación","inflacion","dólar","dolar","mercados","pib","recesión","aranceles"],"tecnologia":["inteligencia artificial","tecnología","tecnologia","startup","fintech","ciberseguridad"],"politica":["elecciones","presidente","gobierno","congreso","senado"],"salud":["salud","vacuna","hospital","oms","enfermedad"],"medio_ambiente":["amazonía","amazonia","cambio climático","cambio climatico","glaciares","medio ambiente"],"deportes":["fútbol","futbol","mundial","libertadores","eliminatorias"]}
    for kws in temas_prioritarios.values():
        if any(kw in txt for kw in kws):
            p += 2; break

    # Bonus/penalización durabilidad SEO (evergreen vs efímero)
    tema_d = detectar_tema(titulo, desc)
    if tema_d in {'tecnologia','ciencia','salud','medio_ambiente'}: p += 10
    elif tema_d in {'economia','educacion'}: p += 5
    elif tema_d in {'guerra','desastre','crimen'}: p -= 4

    return p

def bonus_frescura(fecha_str):
    if not fecha_str: return 0
    try:
        fecha_str_norm = str(fecha_str).replace('Z','+00:00')
        fecha_pub = datetime.fromisoformat(fecha_str_norm)
        if fecha_pub.tzinfo is None: fecha_pub = fecha_pub.replace(tzinfo=timezone.utc)
        horas = (datetime.now(timezone.utc) - fecha_pub).total_seconds() / 3600
        if horas < 0: return 0
        if horas <= 6: return 8
        elif horas <= 24: return 5
        elif horas <= 48: return 2
        return 0
    except:
        return 0


# ══════════════════════════════════════════════════════════
# CUOTAS, HISTORIAL, ESTADO WP/FB
# ══════════════════════════════════════════════════════════
def cargar_cuotas_hoy():
    datos = cargar_json(CUOTAS_CONTROL_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy:
        return {'fecha': hoy, 'conteo': {}, 'directos': 0, 'borradores': 0}
    return datos

def registrar_cuota(categoria, es_borrador=False):
    datos = cargar_cuotas_hoy()
    datos['conteo'][categoria] = datos['conteo'].get(categoria, 0) + 1
    if es_borrador:
        datos['borradores'] = datos.get('borradores', 0) + 1
    else:
        datos['directos'] = datos.get('directos', 0) + 1
    guardar_json(CUOTAS_CONTROL_PATH, datos)

def categoria_disponible(categoria, total_dia=MAX_POSTS_WP_DIA):
    datos = cargar_cuotas_hoy()
    conteo = datos['conteo'].get(categoria, 0)
    maximo = max(1, int(total_dia * CUOTAS_CATEGORIA.get(categoria, {}).get('cuota', 0.10)))
    return conteo < maximo

def es_categoria_critica(categoria):
    return categoria in ('guerra','crimen','desastre')

def ajustar_categoria_por_cuota(categoria):
    if es_categoria_critica(categoria): return categoria
    if categoria_disponible(categoria): return categoria
    log(f"📊 Cuota llena para '{categoria}' — buscando alternativa brand-safe",'advertencia')
    alternativas = sorted(
        [(c,v) for c,v in CUOTAS_CATEGORIA.items() if v.get('brand_safe') and categoria_disponible(c) and not es_categoria_critica(c)],
        key=lambda x: -x[1]['cpm_relativo']
    )
    if alternativas:
        nueva = alternativas[0][0]
        log(f"   → Reasignado a '{nueva}'",'info')
        return nueva
    return categoria

def es_brand_safe(categoria):
    return CUOTAS_CATEGORIA.get(categoria, {}).get('brand_safe', True)

def categorias_usadas_hoy():
    datos = cargar_cuotas_hoy()
    return {c for c, n in datos.get('conteo', {}).items() if int(n) > 0 and c in CATEGORIAS_ROTACION_WP}

def puede_publicar_directo_hoy():
    """V19: ¿quedan cupos de publicación directa (visible)?"""
    datos = cargar_cuotas_hoy()
    return datos.get('directos', 0) < MAX_POSTS_DIA_DIRECTOS

def puede_publicar_borrador_hoy():
    """V19: ¿quedan cupos de borrador (evergreen)?"""
    datos = cargar_cuotas_hoy()
    return datos.get('borradores', 0) < MAX_POSTS_DIA_BORRADORES

HISTORIAL_DEFAULT = {
    'urls':[],'urls_normalizadas':[],'hashes':[],'timestamps':[],
    'titulos':[],'descripciones':[],'hashes_contenido':[],'hashes_permanentes':[],
    'estadisticas':{'total_publicadas':0,'total_wp':0,'total_fb':0,'total_pinterest':0,'total_borradores':0}
}

def cargar_historial():
    h = cargar_json(HISTORIAL_PATH, HISTORIAL_DEFAULT)
    for k, v in HISTORIAL_DEFAULT.items():
        if k not in h:
            h[k] = v if not isinstance(v, dict) else v.copy()
    _limpiar_historial_antiguo(h)
    return h

def _limpiar_historial_antiguo(h):
    ahora = datetime.now()
    indices_validos = []
    for i, ts in enumerate(h.get('timestamps', [])):
        try:
            if (ahora - datetime.fromisoformat(ts)).days < DIAS_HISTORIAL:
                indices_validos.append(i)
        except: continue
    for key in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if key in h and isinstance(h[key], list):
            h[key] = [h[key][i] for i in indices_validos if i < len(h[key])]
    if len(h.get('hashes_permanentes', [])) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]

def noticia_ya_publicada(h, url, titulo, desc=""):
    if es_titulo_generico(titulo): return True, "titulo_generico"
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)
    hash_d = generar_hash(desc) if desc else ""
    if url_n in h.get('urls_normalizadas', []): return True, "url_duplicada"
    todos_hashes = set(h.get('hashes', [])) | set(h.get('hashes_permanentes', []))
    if hash_t in todos_hashes: return True, "hash_titulo"
    if hash_d and hash_d in h.get('hashes_contenido', []): return True, "hash_contenido"
    for th in h.get('titulos', []):
        if not isinstance(th, str): continue
        if similitud_titulos(titulo, th) >= UMBRAL_SIMILITUD_TITULO: return True, "titulo_similar"
    if desc:
        for dh in h.get('descripciones', []):
            if isinstance(dh, str) and dh:
                if similitud_contenido(desc, dh, 150) >= UMBRAL_SIMILITUD_CONTENIDO: return True, "descripcion_similar"
    return False, "nuevo"

def guardar_en_historial(h, url, titulo, desc=""):
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)
    if url_n in h.get('urls_normalizadas', []): return h
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['hashes_permanentes'].append(hash_t)
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1
    for k in ['urls','urls_normalizadas','hashes','timestamps','titulos','descripciones','hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA: h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    if len(h['hashes_permanentes']) > 500: h['hashes_permanentes'] = h['hashes_permanentes'][-500:]
    guardar_json(HISTORIAL_PATH, h)
    return h

def puede_publicar_wp():
    if os.getenv('FORZAR_PUBLICACION','').lower() == 'true': return True
    cuotas_hoy = cargar_cuotas_hoy()
    total_hoy = sum(int(v) for v in cuotas_hoy.get('conteo', {}).values())
    if total_hoy >= MAX_POSTS_WP_DIA:
        log(f"🚫 WP: cuota diaria alcanzada ({total_hoy}/{MAX_POSTS_WP_DIA})",'advertencia')
        return False
    e = cargar_json(ESTADO_WP_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u: return True
    try:
        minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        margen = TIEMPO_ENTRE_WP_MIN - 15
        if minutos < margen:
            log(f"⏱️ WP: publicado hace {minutos:.0f} min — mínimo {margen} min",'info')
            return False
    except: pass
    return True

def puede_publicar_fb(h):
    if os.getenv('FORZAR_PUBLICACION','').lower() == 'true': return True
    hora_utc = datetime.utcnow().hour
    en_pico  = any(inicio <= hora_utc < fin for inicio, fin in HORARIOS_PICO_UTC)
    if not en_pico: return False
    hoy = datetime.now().date()
    posts_hoy = sum(1 for ts in h.get('timestamps', []) if ts and datetime.fromisoformat(ts).date() == hoy)
    if posts_hoy >= 4: return False
    e = cargar_json(ESTADO_FB_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if u:
        try:
            minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
            if minutos < TIEMPO_ENTRE_FB_MIN: return False
        except: pass
    return True

def guardar_estado_wp():
    guardar_json(ESTADO_WP_PATH, {'ultima_publicacion': datetime.now().isoformat()})

def guardar_estado_fb():
    guardar_json(ESTADO_FB_PATH, {'ultima_publicacion': datetime.now().isoformat()})


# ══════════════════════════════════════════════════════════
# BÚSQUEDA WEB (TAVILY) Y REESCRITURA CON IA V19
# ══════════════════════════════════════════════════════════
def buscar_contexto_web(titulo, max_resultados=3):
    if not TAVILY_API_KEY: return []
    try:
        resp = requests.post("https://api.tavily.com/search",
            json={"api_key":TAVILY_API_KEY,"query":titulo,"search_depth":"basic","max_results":max_resultados,"include_answer":False},
            timeout=15)
        data = resp.json()
        resultados = data.get("results", [])
        if not resultados: return []
        log(f"🔎 Tavily: {len(resultados)} fuente(s) para contexto",'info')
        return [{"title":r.get("title",""),"url":r.get("url",""),"content":(r.get("content","") or "")[:600]} for r in resultados]
    except Exception as e:
        log(f"⚠️ Tavily falló ({e}) — sin contexto adicional",'advertencia')
        return []

def reescribir_noticia_v19(titulo, contenido, categoria_sugerida='general', feedback_correccion=None, es_borrador=False):
    """
    V19: genera artículo con todos los requerimientos Rank Math 80+.
    Cambios vs V18:
      - Keyword al INICIO del título SEO
      - Keyword en 2+ H2
      - Densidad keyword 1-1.5% (instrucción explícita en prompt)
      - Tabla de contenidos HTML automática
      - Meta descripción EMPIEZA con keyword
      - Párrafo nativo con tono VerdadHoy (callejero pero no vulgar)
      - Campo 'slug' generado con max 50 chars
      - AEO reforzado: entidad+cargo+dato verificable en párrafo 1
      - Para borradores: instrucción adicional de profundidad evergreen
    """
    api_key = OPENAI_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY or GEMINI_API_KEY
    if not api_key: return None

    palabras_contenido = len(contenido.split())
    tiempo_lectura = max(2, round(palabras_contenido / 200))

    TITULOS_BOX_RESUMEN = [('⚡','Lo que debes saber'),('📌','Lo esencial'),('🔑','Puntos clave'),('📋','Resumen rápido')]
    emoji_box, texto_box = random.choice(TITULOS_BOX_RESUMEN)
    titulo_box_resumen = f"{emoji_box} {texto_box}"

    modo_borrador_txt = ""
    if es_borrador:
        modo_borrador_txt = """
⭐ MODO EVERGREEN (este artículo irá a BORRADOR para revisión manual):
- Profundidad histórica obligatoria: el lector debe entender el origen del tema, no solo la noticia de hoy
- Incluye al menos 3 cifras verificables (estadísticas, porcentajes, fechas clave)
- Proyección futura: ¿qué se espera que pase en los próximos 6-12 meses?
- El contenido debe ser útil para alguien que lo lea en 6 meses, no solo hoy
- Mínimo 750 palabras (más profundo que las noticias directas)"""

    bloque_feedback = ""
    if feedback_correccion:
        problemas_txt = '\n'.join(f'  - {p}' for p in feedback_correccion)
        hay_densidad = any('densidad' in p.lower() for p in feedback_correccion)
        hay_palabras = any('palabras — mínimo' in p for p in feedback_correccion)
        hay_h2kw = any('H2' in p for p in feedback_correccion)
        hay_inicio_titulo = any('EMPEZAR' in p and 'Título' in p for p in feedback_correccion)
        hay_inicio_meta = any('EMPEZAR' in p and 'Meta' in p for p in feedback_correccion)
        instrucciones_extra = ""
        if hay_densidad:
            instrucciones_extra += "\nDENSIDAD: usa la keyword_principal EXACTA al menos 6 veces distribuidas en todo el texto, una vez en cada H2."
        if hay_palabras:
            instrucciones_extra += "\nEXTENSIÓN: agrega párrafo de antecedente, párrafo de cifras, párrafo de impacto LATAM, y desarrolla cada dato en 2-3 oraciones."
        if hay_h2kw:
            instrucciones_extra += "\nH2: incluye la keyword_principal o variante directa en AL MENOS 2 de los 4 H2."
        if hay_inicio_titulo:
            instrucciones_extra += "\nTÍTULO: debe comenzar CON la keyword, ej: 'Keyword récord: dato concreto'."
        if hay_inicio_meta:
            instrucciones_extra += "\nMETA: primeras palabras = keyword exacta, ej: 'Keyword — lo que debes saber sobre...'"
        bloque_feedback = f"""⚠️ CORRECCIÓN OBLIGATORIA — reintento:
{problemas_txt}
{instrucciones_extra}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    bloque_contexto_web = ""
    if not feedback_correccion:
        fuentes_web = buscar_contexto_web(titulo)
        if fuentes_web:
            fuentes_txt = "\n\n".join(f"Fuente {i+1}: {f['title']}\n{f['content']}" for i, f in enumerate(fuentes_web))
            bloque_contexto_web = f"""📚 CONTEXTO ADICIONAL (fuentes reales — úsalo para agregar cifras y antecedentes verificables):
{fuentes_txt}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    prompt = f"""Eres el Editor Jefe Digital de VerdadHoy.com, medio de noticias en español para América Latina.
VerdadHoy tiene audiencia principal en Chile, Argentina y México (Tier 1), con presencia en Colombia y Brasil (Tier 2).
Tono editorial: directo y callejero pero no vulgar — similar a La Cuarta pero más serio. Nunca flaite puro.
{modo_borrador_txt}

⚠️ REGLA CRÍTICA DE EXTENSIÓN:
El artículo fuente puede ser corto. Tu trabajo es CREAR un artículo completo de 650-850 palabras.
Usa los datos de la fuente + conocimiento propio + contexto web. Siempre 650 palabras mínimo.

═══════════════════════════════════════
NOTICIA:
Título original: {titulo}
Contenido: {contenido[:3000]}
Categoría sugerida: {categoria_sugerida}
Tiempo de lectura: {tiempo_lectura} min
═══════════════════════════════════════
{bloque_contexto_web}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 1 — KEYWORD Y TÍTULO SEO (RANK MATH 80+):

La keyword_principal es la frase de búsqueda más probable para esta noticia (2-4 palabras).

REGLA TÍTULO — ORDEN OBLIGATORIO:
  [KEYWORD AL INICIO] + [: o verbo] + [DATO/POWER WORD]
  ✅ "Chile inflación récord: sube 4,7% en junio"  ← keyword primero
  ✅ "Inteligencia artificial revoluciona: Chile lidera en LATAM"
  ❌ "El gobierno de Chile enfrenta alza histórica"  ← keyword no al inicio
  ❌ "River Plate inscribe a Thiago Almada para la"  ← CORTADO

REGLAS TÍTULO:
  - Máximo 55 chars de texto (el bot agrega " | Verdad Hoy" — NO lo incluyas)
  - La keyword debe estar en las primeras 3 palabras
  - Power word obligatoria: récord, histórico, clave, urgente, decisivo, alerta, oficial, confirmado, revelador, crítico, explosivo, sorprendente
  - Número obligatorio si el hecho lo permite
  - FRASE COMPLETA — nunca cortar a la mitad

REGLA META DESCRIPCIÓN — EMPIEZA CON KEYWORD:
  ✅ "Chile inflación — los precios subieron 4,7% en junio afectando a 3 millones de familias. ¿Cuándo cederá la presión?"
  ❌ "Descubre por qué Chile enfrenta..."
  - Exactamente 150-160 chars
  - Keyword en los primeros 40 chars

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 2 — CLASIFICACIÓN DE CATEGORÍA:
  - "latinoamerica" SOLO si no hay categoría temática más específica
  - Inflación en Argentina → "economia" (NO latinoamerica)
  - Elecciones en Colombia → "politica" (NO latinoamerica)
  - Messi en Copa Libertadores → "deportes" (NO latinoamerica)
  - España, Francia, Alemania → "mundo"
  - Wearables, smartwatch → "tecnologia"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 3 — ESTRUCTURA COMPLETA DEL ARTÍCULO (RANK MATH 80+):

── TABLA DE CONTENIDOS (obligatoria para Rank Math) ──
<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este artículo</p>
<ol style="margin:0;padding-left:20px;color:#475569;font-size:0.9em;">
<li style="margin-bottom:4px;"><a href="#seccion-1" style="color:#1a56db;text-decoration:none;">[H2 #1 título]</a></li>
<li style="margin-bottom:4px;"><a href="#seccion-2" style="color:#1a56db;text-decoration:none;">[H2 #2 título]</a></li>
<li style="margin-bottom:4px;"><a href="#seccion-3" style="color:#1a56db;text-decoration:none;">[H2 #3 título]</a></li>
<li style="margin-bottom:0;"><a href="#seccion-4" style="color:#1a56db;text-decoration:none;">[H2 #4 título]</a></li>
</ol>
</nav>

── BOX RESUMEN (va después de la tabla de contenidos) ──
<div style="background:#f0f4ff;border-left:4px solid #1a56db;padding:16px 20px;margin:0 0 24px 0;border-radius:0 8px 8px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:#1a56db;font-size:0.95em;">{titulo_box_resumen}</p>
<ul style="margin:0;padding-left:20px;color:#374151;">
<li style="margin-bottom:6px;">[Punto clave 1 — hecho principal]</li>
<li style="margin-bottom:6px;">[Punto clave 2 — dato relevante]</li>
<li style="margin-bottom:6px;">[Punto clave 3 — consecuencia]</li>
<li style="margin-bottom:0;">[Punto clave 4 — quién/cuándo/dónde]</li>
</ul>
</div>

── APERTURA AEO (≤40 palabras, ENTIDAD COMPLETA + DATO VERIFICABLE) ──
<p>[Nombre completo + cargo + verbo activo + hecho concreto + fecha + consecuencia directa.
Ejemplo: "Gabriel Boric, presidente de Chile, anunció el 15 de agosto de 2026 una rebaja del IVA al 15%, medida que beneficia a 5 millones de familias de menores ingresos."]</p>

── H2 #1 (con keyword, id="seccion-1") — antes de palabra 80 ──
<h2 id="seccion-1">[Keyword principal + ángulo 1]</h2>
<p>[Contexto y antecedente. Máx 3 líneas, oraciones máx 20 palabras. Voz activa.]</p>
<p>[Desarrollo con <strong>términos clave</strong>. Dato concreto obligatorio. Máx 2 oraciones.]</p>

── H2 #2 (con keyword o variante, id="seccion-2") ──
<h2 id="seccion-2">[Variante keyword + ángulo 2]</h2>
<p>[Datos adicionales o perspectiva complementaria. Máx 3 líneas.]</p>

── PÁRRAFO NATIVO (tono VerdadHoy — insertar aquí, después del H2 #2) ──
<p style="border-left:3px solid #f59e0b;padding:10px 14px;margin:16px 0;background:#fffbeb;font-style:italic;color:#374151;">[Párrafo de 2-3 oraciones con el tono editorial de VerdadHoy: directo, callejero pero no vulgar. Una afirmación editorial concreta sobre por qué esta noticia importa HOY al lector chileno/latinoamericano. No hacer pregunta — hacer afirmación. Puede incluir un chilenismo moderado si corresponde. Ej: "Esto no es un dato más en el papel. Para millones de familias en Chile y Argentina, significa que el próximo mes van a tener que apretarse el cinturón una vez más."]</p>

── DATO DESTACADO (blockquote obligatorio) ──
<blockquote style="border-left:3px solid #e5e7eb;padding:12px 16px;margin:20px 0;background:#f9fafb;font-style:italic;color:#4b5563;">
[Cita textual o dato estadístico. Formato: "Según [fuente], [dato concreto con número]."]
</blockquote>

── H2 #3 (id="seccion-3") — consecuencias o impacto LATAM ──
<h2 id="seccion-3">[Ángulo 3 — consecuencias, reacciones o cifras]</h2>
<p>[Profundiza con datos verificables. Menciona Chile y al menos otro país LATAM si aplica. Máx 3 líneas.]</p>

── H2 #4 (id="seccion-4") — cierre según categoría ──
[Si deportes → "Análisis del encuentro"]
[Si ciencia/salud → "Lo que dicen los expertos"]  
[Si entretenimiento → "Por qué importa"]
[Si latinoamerica/economia/politica/tecnologia/medio_ambiente → "Qué significa para América Latina"]
<h2 id="seccion-4">[Título H2 #4]</h2>
<p>[Cierre con reflexión + pregunta genuina al lector. Pregunta específica al tema, no genérica. NO pedir comentarios directamente.]</p>

[ENLACES_INTERNOS]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGLAS CALIDAD RANK MATH 80+ (autovalidar antes de responder):
1. keyword_principal en título (primeras 3 palabras)
2. keyword_principal en meta descripción (primeros 40 chars)
3. keyword_principal en primer párrafo (antes palabra 80)
4. keyword_principal en AL MENOS 2 H2
5. Densidad keyword: 1-1.5% del texto total (usa la keyword ~6-8 veces en 650 palabras)
6. 4 H2 con id="seccion-N", cada uno ángulo distinto
7. Tabla de contenidos al inicio
8. Box resumen después de la tabla
9. Párrafo nativo con tono VerdadHoy (callejero pero no vulgar)
10. Blockquote con dato estadístico verificable
11. Párrafos máx 3 líneas — oraciones máx 20 palabras
12. Mínimo 4 palabras de transición
13. Meta descripción 150-160 chars exacto, empieza con keyword
14. Título: keyword al inicio, power word, número si aplica, máx 55 chars, FRASE COMPLETA
15. [ENLACES_INTERNOS] al final del contenido_html
16. NO copiar estructura del artículo fuente
17. Español neutro latinoamericano (sin "vosotros", "tío", "guay")
18. Enlace dofollow a la fuente en el texto cuando sea natural
19. Apertura AEO: Nombre completo + cargo + hecho + fecha + consecuencia

AEO — OPTIMIZACIÓN PARA IA (ChatGPT, Gemini, Perplexity):
- Responde explícitamente: QUÉ, QUIÉN (nombre completo + cargo), CUÁNDO, DÓNDE, POR QUÉ IMPORTA
- Al menos 1 cifra verificable en los primeros 2 párrafos
- Evita frases vagas: "los precios subieron" → "los precios subieron 4,7% en junio 2026 según el INE"
- Estructura pregunta→respuesta implícita para que las IAs puedan citarte

PROHIBICIONES:
- NO inventar datos, citas o cifras
- NO reproducir más de 5 palabras consecutivas del original
- NO empezar meta con: Descubre, Entérate, Conoce, Te contamos, Haz clic
- NO contenido gráfico en guerra/crimen
- NO keyword stuffing (máx 1.5% densidad)

{bloque_feedback}

RESPONDE ÚNICAMENTE con JSON sin markdown:
{{"titulo_seo":"keyword al inicio, máx 55 chars, power word, número si aplica","slug":"max-50-chars-sin-stopwords","meta_descripcion":"keyword primero, 150-160 chars exacto","contenido_html":"<nav...>[TABLA]</nav><div...>[BOX]</div><p>[APERTURA AEO]</p><h2 id=seccion-1>...</h2>...[ENLACES_INTERNOS]","keyword_principal":"2-4 palabras","keywords_secundarias":["kw2","kw3","kw4","kw5"],"categoria":"latinoamerica|deportes|economia|tecnologia|entretenimiento|politica|ciencia|salud|medio_ambiente|guerra|desastre|mundo|general","parrafo_nativo":"texto plano del párrafo nativo para referencia editorial"}}"""

    def _llamar_api_ia(url_api, headers, modelo, payload):
        try:
            resp = requests.post(url_api, headers=headers, json=payload, timeout=55)
        except Exception as e:
            log(f"❌ IA error de red ({url_api}): {e}",'error')
            return None, 'otro', None
        try: resp_json = resp.json()
        except:
            log(f"❌ IA respuesta no JSON (HTTP {resp.status_code})",'error')
            return None, 'otro', None
        if "choices" not in resp_json:
            err = resp_json.get("error", {})
            msg = err.get("message", str(resp_json)[:200]) if isinstance(err, dict) else str(err)[:200]
            code = err.get("code", resp.status_code) if isinstance(err, dict) else resp.status_code
            log(f"❌ IA error (HTTP {resp.status_code}): {msg}",'error')
            msg_lower = str(msg).lower()
            if "insufficient" in msg_lower or "quota" in msg_lower or "credit" in msg_lower: return None, 'credito', None
            elif "rate limit" in msg_lower or code == 429:
                espera_seg = None
                m = re.search(r'try again in ([\d.]+)\s*s', msg_lower)
                if m:
                    try: espera_seg = float(m.group(1))
                    except: pass
                return None, 'rate_limit', espera_seg
            elif ("invalid" in msg_lower and "key" in msg_lower) or code == 401: return None, 'auth', None
            return None, 'otro', None
        return resp_json, None, None

    try:
        proveedores = []
        if OPENAI_API_KEY:
            proveedores.append(("OpenAI","https://api.openai.com/v1/chat/completions",{"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},"gpt-4o-mini"))
        if OPENROUTER_API_KEY:
            proveedores.append(("OpenRouter","https://openrouter.ai/api/v1/chat/completions",{"Authorization":f"Bearer {OPENROUTER_API_KEY}","Content-Type":"application/json"},"meta-llama/llama-3.3-70b-instruct:free"))
        if GROQ_API_KEY:
            proveedores.append(("Groq","https://api.groq.com/openai/v1/chat/completions",{"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},"llama-3.3-70b-versatile"))
        if GEMINI_API_KEY:
            proveedores.append(("Gemini","https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",{"Authorization":f"Bearer {GEMINI_API_KEY}","Content-Type":"application/json"},"gemini-2.5-flash"))

        global _proveedores_ia_logueados
        try: _proveedores_ia_logueados
        except NameError: _proveedores_ia_logueados = False
        if not _proveedores_ia_logueados:
            nombres = [p[0] for p in proveedores]
            log(f"🔑 Proveedores IA: {', '.join(nombres) if nombres else 'NINGUNO — sin API keys'}", 'info' if nombres else 'error')
            _proveedores_ia_logueados = True

        resp_json = None
        url_api = headers = modelo = payload = None
        for i, (nombre, url_i, headers_i, modelo_i) in enumerate(proveedores):
            payload_i = {"model":modelo_i,"messages":[{"role":"user","content":prompt}],"temperature":0.35,"max_tokens":3500}
            if i > 0: log(f"   🔁 Reintentando con {nombre}...",'advertencia')
            resp_json, motivo, espera_seg = _llamar_api_ia(url_i, headers_i, modelo_i, payload_i)
            if resp_json is None and motivo == 'rate_limit' and espera_seg and espera_seg <= 45:
                time.sleep(espera_seg + 2)
                resp_json, motivo, espera_seg = _llamar_api_ia(url_i, headers_i, modelo_i, payload_i)
            if resp_json is not None:
                url_api, headers, modelo, payload = url_i, headers_i, modelo_i, payload_i
                if i > 0: log(f"   ✅ Fallback a {nombre} exitoso",'exito')
                break
        if resp_json is None: return None

        choice = resp_json["choices"][0]
        if choice.get("finish_reason") == "length":
            log("⚠️ IA cortó respuesta por longitud — reintentando con contenido más corto",'advertencia')
            prompt_corto = prompt.replace(contenido[:3000], contenido[:1500])
            payload["messages"] = [{"role":"user","content":prompt_corto}]
            resp2 = requests.post(url_api, headers=headers, json=payload, timeout=55)
            try:
                resp_json2 = resp2.json()
                if "choices" in resp_json2: choice = resp_json2["choices"][0]
                else: return None
            except: return None

        texto = choice["message"]["content"].strip()
        texto = re.sub(r'^```json\s*|```$','',texto,flags=re.MULTILINE).strip()
        if not texto.endswith('}'): 
            log("⚠️ JSON incompleto",'advertencia')
            return None

        resultado = json.loads(texto)
        categorias_validas = set(CATEGORIA_WP.keys())
        cat_ia = resultado.get('categoria','').strip().lower()
        if cat_ia not in categorias_validas:
            log(f"⚠️ Categoría inválida '{cat_ia}' — usando '{categoria_sugerida}'",'advertencia')
            resultado['categoria'] = categoria_sugerida if categoria_sugerida in categorias_validas else 'general'
        elif cat_ia != categoria_sugerida:
            log(f"🧠 IA corrigió categoría: '{categoria_sugerida}' → '{cat_ia}'",'info')

        # Verificar originalidad
        contenido_generado = resultado.get('contenido_html','')
        sim = similitud_contenido(contenido_generado, contenido[:3000], longitud=200)
        if sim > 0.42:
            log(f"⚠️ Contenido muy similar al original (sim={sim:.2f}) — reintentando",'advertencia')
            payload_retry = {"model":modelo,"messages":[{"role":"system","content":"Eres editor periodístico. NUNCA copies el texto fuente. Escribe artículos completamente originales."},{"role":"user","content":prompt}],"temperature":0.55,"max_tokens":3500}
            try:
                resp2 = requests.post(url_api, headers=headers, json=payload_retry, timeout=55)
                resp2_json = resp2.json()
                if "choices" in resp2_json:
                    texto2 = resp2_json["choices"][0]["message"]["content"].strip()
                    texto2 = re.sub(r'^```json\s*|```$','',texto2,flags=re.MULTILINE).strip()
                    if texto2.endswith('}'):
                        resultado2 = json.loads(texto2)
                        sim2 = similitud_contenido(resultado2.get('contenido_html',''), contenido[:3000], longitud=200)
                        if sim2 < sim:
                            resultado = resultado2
                            cat2 = resultado.get('categoria','').strip().lower()
                            if cat2 not in categorias_validas: resultado['categoria'] = categoria_sugerida if categoria_sugerida in categorias_validas else 'general'
                            log(f"✅ Reintento originalidad OK (sim={sim2:.2f})",'info')
            except Exception as e2:
                log(f"⚠️ Reintento originalidad falló: {e2}",'advertencia')
        else:
            log(f"✅ Originalidad OK (sim={sim:.2f})",'info')

        log(f"✅ IA — Título: {resultado.get('titulo_seo','')[:55]} | Cat: {resultado.get('categoria')}",'info')
        return resultado
    except Exception as e:
        log(f"⚠️ reescribir_noticia_v19 error: {e}",'advertencia')
        return None


# ══════════════════════════════════════════════════════════
# RESOLUCIÓN CATEGORÍA WP + ENLACES INTERNOS
# ══════════════════════════════════════════════════════════
def resolver_categoria_wp(categoria_editorial, titulo, texto_analisis):
    categorias_paraguas = {'desastre','guerra','crimen','religion','educacion','general','mundo'}
    if categoria_editorial in categorias_paraguas:
        texto_chk = f"{titulo} {texto_analisis}".lower()
        es_latam = (any(kw in texto_chk for kw in KEYWORDS_CHILE) or
                    any(kw in texto_chk for kws in KEYWORDS_LATAM_PAISES.values() for kw in kws))
        if es_latam: return 'latinoamerica'
        region = detectar_region_internacional(titulo, texto_analisis)
        return REGION_SLUG_WP.get(region, 'internacional')
    return CATEGORIA_WP.get(categoria_editorial, 'internacional')

def obtener_articulos_wp_recientes(num=3):
    if not WP_APP_PASSWORD: return []
    try:
        resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts",
            params={'per_page':num+1,'status':'publish','orderby':'date','order':'desc','_fields':'id,title,link'},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10)
        if resp.status_code == 200: return resp.json()[:num]
    except Exception as e:
        log(f"⚠️ No se pudieron obtener artículos relacionados: {e}",'debug')
    return []

def generar_seccion_relacionados(articulos):
    if not articulos: return ""
    items = ""
    for art in articulos:
        t = art.get('title',{}).get('rendered','')
        l = art.get('link','#')
        if t and l:
            items += f'<li><a href="{l}" style="color:#1a1a1a;text-decoration:none;">{t}</a></li>\n'
    if not items: return ""
    return ('\n<div class="vh-relacionadas" style="margin-top:24px;padding:16px;background:#f8f9fa;border-left:4px solid #cc0000;border-radius:4px;">\n'
            '<h3 style="margin:0 0 10px;font-size:1rem;color:#cc0000;">📰 Te puede interesar</h3>\n'
            f'<ul style="margin:0;padding-left:20px;">\n{items}</ul>\n</div>\n')

def insertar_enlaces_internos(contenido_html):
    articulos = obtener_articulos_wp_recientes(2)
    html_relacionados = generar_seccion_relacionados(articulos)
    if "[ENLACES_INTERNOS]" in contenido_html:
        return contenido_html.replace("[ENLACES_INTERNOS]", html_relacionados)
    return contenido_html + html_relacionados

# ══════════════════════════════════════════════════════════
# WORDPRESS — IMÁGENES Y TAGS
# ══════════════════════════════════════════════════════════
def obtener_id_categoria_wp(slug_categoria):
    global _cache_categorias_wp
    if slug_categoria in _cache_categorias_wp: return _cache_categorias_wp[slug_categoria]
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories",
            params={'slug':slug_categoria,'per_page':1},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=15).json()
        if r and isinstance(r, list) and len(r) > 0:
            cat_id = r[0]['id']
            _cache_categorias_wp[slug_categoria] = cat_id
            log(f"📂 Categoría WP '{slug_categoria}' → ID {cat_id}",'info')
            return cat_id
    except Exception as e:
        log(f"⚠️ Error obteniendo categoría '{slug_categoria}': {e}",'advertencia')
    return None

def obtener_crear_tag_wp(nombre_tag):
    global _cache_tags_wp
    tag_clean = nombre_tag.lower().strip()
    if not tag_clean or len(tag_clean) < 2: return None
    if tag_clean in _cache_tags_wp: return _cache_tags_wp[tag_clean]
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags",
            params={'search':tag_clean,'per_page':5},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10).json()
        if r and isinstance(r, list):
            for tag in r:
                if tag.get('name','').lower() == tag_clean:
                    _cache_tags_wp[tag_clean] = tag['id']
                    return tag['id']
        r_post = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
            json={'name':nombre_tag.strip()},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10).json()
        if 'id' in r_post:
            _cache_tags_wp[tag_clean] = r_post['id']
            return r_post['id']
    except Exception as e:
        log(f"⚠️ Error gestionando tag '{nombre_tag}': {e}",'debug')
    return None

def subir_imagen_wp(imagen_path, titulo, alt_text="", frase_clave="", meta_descripcion=""):
    if not imagen_path or not os.path.exists(imagen_path): return None
    try:
        nombre_archivo = f"noticia-{generar_hash(titulo)}.jpg"
        with open(imagen_path,'rb') as f:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/media",
                headers={'Content-Disposition':f'attachment; filename="{nombre_archivo}"','Content-Type':'image/jpeg'},
                data=f.read(), auth=(WP_USER, WP_APP_PASSWORD), timeout=60).json()
        if 'id' in r:
            media_id = r['id']
            log(f"🖼️ Imagen subida WP — ID: {media_id}",'exito')
            kw_imagen = (frase_clave or titulo)[:125]
            metadatos = {'title':kw_imagen,'alt_text':kw_imagen,
                         'caption':f"{titulo[:120]} — Fuente: Verdad Hoy",
                         'description':(f"{frase_clave}. {meta_descripcion}".strip()[:300] if meta_descripcion and frase_clave else (frase_clave or titulo)[:300])}
            try:
                requests.post(f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                    json=metadatos, auth=(WP_USER, WP_APP_PASSWORD), timeout=10)
            except Exception as e:
                log(f"⚠️ No se pudieron guardar metadatos imagen: {e}",'debug')
            return media_id
        else:
            log(f"⚠️ Error subiendo imagen: {r.get('message','desconocido')}",'advertencia')
    except Exception as e:
        log(f"⚠️ Excepción subiendo imagen: {e}",'advertencia')
    return None


# ══════════════════════════════════════════════════════════
# PUBLICAR EN WORDPRESS V19
# ══════════════════════════════════════════════════════════
def publicar_en_wordpress(titulo, contenido, tema, imagen_path, fuente_url,
                           fecha_fuente=None, fuente_noticia=None, es_borrador=False):
    """
    V19: agrega parámetro es_borrador.
    Si es_borrador=True → status='draft' (evergreen para revisión manual).
    Si es_borrador=False → status='publish' (noticia directa).
    Devuelve (url_articulo, slug_categoria_final).
    """
    if not WP_APP_PASSWORD:
        log("⚠️ WP_APP_PASSWORD no configurado",'advertencia')
        return None, None
    if not imagen_path or not os.path.exists(imagen_path):
        log("❌ Sin imagen — no se publica en WordPress",'error')
        return None, None

    def extraer_nombre_medio(url):
        try:
            dominio = urlparse(url).netloc.lower()
            dominio = re.sub(r'^(www\.|m\.)','',dominio)
            mapa = {'elpais.com':'El País','bbc.com':'BBC Mundo','cnn.com':'CNN en Español',
                    'infobae.com':'Infobae','reuters.com':'Reuters','france24.com':'France 24',
                    'efe.com':'EFE','dw.com':'Deutsche Welle','euronews.com':'Euronews',
                    'theguardian.com':'The Guardian'}
            for dom, nombre in mapa.items():
                if dom in dominio: return nombre
            partes = dominio.split('.')
            return partes[-2].capitalize() if len(partes) >= 2 else dominio
        except: return 'Fuente externa'

    nombre_medio = extraer_nombre_medio(fuente_url)
    resultado_ia = reescribir_noticia_v19(titulo, contenido, tema, es_borrador=es_borrador)

    if resultado_ia:
        keyword_para_validar = resultado_ia.get('keyword_principal','')
        es_valido, problemas = validar_calidad_articulo(
            resultado_ia.get('contenido_html',''), resultado_ia.get('meta_descripcion',''),
            resultado_ia.get('titulo_seo',''), resultado_ia.get('categoria',''), keyword_para_validar)
        if not es_valido:
            if not REINTENTAR_CALIDAD_IA:
                log(f"❌ No pasó calidad ({len(problemas)} problema(s)) — descartado",'error')
                for p in problemas: log(f"   - {p}",'error')
                return None, None
            log(f"⚠️ No pasó calidad ({len(problemas)} problema(s)) — reintentando",'advertencia')
            for p in problemas: log(f"   - {p}",'advertencia')
            resultado_reintento = reescribir_noticia_v19(titulo, contenido, tema, feedback_correccion=problemas, es_borrador=es_borrador)
            if resultado_reintento:
                kw_r = resultado_reintento.get('keyword_principal','')
                es_valido_2, problemas_2 = validar_calidad_articulo(
                    resultado_reintento.get('contenido_html',''), resultado_reintento.get('meta_descripcion',''),
                    resultado_reintento.get('titulo_seo',''), resultado_reintento.get('categoria',''), kw_r)
                if es_valido_2:
                    log("✅ Reintento corrigió los problemas",'exito')
                    resultado_ia = resultado_reintento
                else:
                    log(f"❌ Reintento tampoco pasó calidad ({len(problemas_2)} problema(s)) — descartado",'error')
                    for p in problemas_2: log(f"   - {p}",'error')
                    return None, None
            else:
                log("❌ IA no disponible para reintento — descartado",'error')
                return None, None
    else:
        log("❌ IA no disponible — no se publica sin IA",'error')
        return None, None

    # Extraer campos del resultado IA
    titulo_final_raw = resultado_ia.get('titulo_seo', titulo) or titulo
    categoria_ia     = resultado_ia.get('categoria', tema)
    meta_desc        = resultado_ia.get('meta_descripcion', '')
    frase_clave      = resultado_ia.get('keyword_principal', '')
    slug_ia          = resultado_ia.get('slug', '')
    contenido_html   = resultado_ia.get('contenido_html', '')

    # V19 FIX: validar y limpiar título (nunca cortado)
    titulo_final = titulo_final_raw.strip()
    if len(titulo_final) > 55:
        # Cortar en la última palabra completa antes de 55 chars
        palabras = titulo_final.split()
        titulo_reconstruido = ''
        for p in palabras:
            candidato = (titulo_reconstruido + ' ' + p).strip()
            if len(candidato) > 55: break
            titulo_reconstruido = candidato
        titulo_final = titulo_reconstruido or titulo_final[:55].rsplit(' ',1)[0]
    
    sufijo_seo = ' | Verdad Hoy'
    titulo_seo = titulo_final + sufijo_seo
    log(f"📰 titulo_seo: '{titulo_seo}' ({len(titulo_seo)} chars)",'debug')

    # Slug máx 50 chars (V19)
    if slug_ia and len(slug_ia) <= 50:
        slug_post = slug_ia
    else:
        slug_post = generar_slug_seo(titulo_final, max_chars=50)
    log(f"🔗 Slug ({len(slug_post)} chars): {slug_post}",'debug')

    # Meta descripción
    if not meta_desc or len(meta_desc) < 140:
        texto_limpio = ' '.join(contenido.split())
        oraciones = re.split(r'(?<=[.!?])\s+', texto_limpio)
        meta_desc_base = meta_desc.rstrip('.') if meta_desc else (oraciones[0][:80] if oraciones else titulo[:80])
        for oracion_extra in oraciones[1:4]:
            oracion_extra = oracion_extra.strip()
            if not oracion_extra: continue
            candidato = meta_desc_base + '. ' + oracion_extra
            if len(candidato) <= 160: meta_desc_base = candidato
            else:
                espacio = 157 - len(meta_desc_base) - 2
                if espacio > 20: meta_desc_base = meta_desc_base + '. ' + oracion_extra[:espacio].rsplit(' ',1)[0] + '...'
                break
            if len(meta_desc_base) >= 150: break
        meta_desc = meta_desc_base
    if len(meta_desc) > 160: meta_desc = meta_desc[:157].rsplit(' ',1)[0] + '...'
    log(f"📝 meta_desc: {len(meta_desc)} chars",'debug')

    # Verificar/insertar box resumen si la IA lo omitió
    _tiene_box = any(t in contenido_html for t in ['background:#f0f4ff','Lo esencial','Puntos clave','Resumen r','Lo que debes saber'])
    if not _tiene_box:
        log("⚠️ IA omitió box resumen — inyectando",'advertencia')
        texto_plano_box = re.sub(r'<[^>]+>',' ',contenido_html)
        oraciones_box = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto_plano_box) if len(o.strip()) > 40]
        puntos_box = []
        for o in oraciones_box[:10]:
            if any(skip in o.lower() for skip in ['verdad hoy','fuente:']): continue
            punto = o[:160] if len(o) <= 160 else o[:160].rsplit(' ',1)[0] + '...'
            puntos_box.append(punto if punto.endswith(('.','!','?')) else punto + '.')
            if len(puntos_box) == 4: break
        while len(puntos_box) < 3: puntos_box.append(f'Noticia: {titulo_final[:100]}.')
        items_box = '\n'.join(f'<li style="margin-bottom:6px;">{p}</li>' for p in puntos_box)
        box_inject = (f'<div style="background:#f0f4ff;border-left:4px solid #1a56db;padding:16px 20px;margin:0 0 24px 0;border-radius:0 8px 8px 0;">'
                      f'<p style="margin:0 0 8px 0;font-weight:700;color:#1a56db;font-size:0.95em;">⚡ Lo que debes saber</p>'
                      f'<ul style="margin:0;padding-left:20px;color:#374151;">{items_box}</ul></div>')
        contenido_html = box_inject + contenido_html

    # Verificar tabla de contenidos
    _tiene_toc = any(t in contenido_html for t in ['tabla-contenidos','table-of-contents','<nav'])
    if not _tiene_toc:
        log("⚠️ Sin tabla de contenidos — inyectando TOC básica",'advertencia')
        h2_textos = re.findall(r'<h2[^>]*id=["\']seccion-(\d+)["\'][^>]*>(.*?)</h2>', contenido_html, flags=re.IGNORECASE|re.DOTALL)
        if not h2_textos:
            h2_textos_raw = re.findall(r'<h2[^>]*>(.*?)</h2>', contenido_html, flags=re.IGNORECASE|re.DOTALL)
            h2_textos = [(str(i+1), re.sub(r'<[^>]+>','',t).strip()) for i, t in enumerate(h2_textos_raw)]
        items_toc = '\n'.join(f'<li style="margin-bottom:4px;"><a href="#seccion-{n}" style="color:#1a56db;text-decoration:none;">{re.sub(chr(60)+r"[^>]+>","",t).strip()}</a></li>' for n, t in h2_textos[:4])
        if items_toc:
            toc_html = (f'<nav class="tabla-contenidos" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:0 0 24px 0;">'
                        f'<p style="margin:0 0 8px 0;font-weight:700;color:#1e293b;font-size:0.9em;">📋 En este artículo</p>'
                        f'<ol style="margin:0;padding-left:20px;color:#475569;font-size:0.9em;">{items_toc}</ol></nav>')
            contenido_html = toc_html + contenido_html

    contenido_html = insertar_enlaces_internos(contenido_html)

    # Tags WP
    tags_ids = []
    for kw in resultado_ia.get('keywords_secundarias', [])[:5]:
        tag_id = obtener_crear_tag_wp(kw)
        if tag_id: tags_ids.append(tag_id)

    # Categoría WP final
    if categoria_ia not in CATEGORIA_WP:
        categoria_ia = tema if tema in CATEGORIA_WP else 'general'
    categorias_paraguas = {'desastre','guerra','crimen','religion','educacion','general','mundo'}
    slug_cat_secundario = None
    if categoria_ia in categorias_paraguas:
        slug_cat = resolver_categoria_wp(categoria_ia, titulo, contenido_html)
        if slug_cat in ('latinoamerica','europa','asia','africa','medio-oriente','oceania'):
            slug_cat_secundario = 'internacional'
    else:
        slug_cat = resolver_categoria_wp(categoria_ia, titulo, contenido_html)
    cat_id = obtener_id_categoria_wp(slug_cat)
    if not cat_id and slug_cat != 'internacional':
        cat_id = obtener_id_categoria_wp('internacional')
        slug_cat = 'internacional'
        slug_cat_secundario = None
    categorias_ids = [cat_id] if cat_id else []
    if slug_cat_secundario:
        cat_id_sec = obtener_id_categoria_wp(slug_cat_secundario)
        if cat_id_sec and cat_id_sec not in categorias_ids: categorias_ids.append(cat_id_sec)

    # Alt imagen = keyword exacta (Rank Math)
    alt_text_imagen = f"{frase_clave} - {titulo_final}"[:125] if frase_clave else titulo_final[:125]

    imagen_id = subir_imagen_wp(imagen_path, titulo_final, alt_text=alt_text_imagen,
                                 frase_clave=frase_clave, meta_descripcion=meta_desc)
    if not imagen_id:
        log("❌ No se pudo subir imagen — cancelando",'error')
        return None, None

    # Schema JSON-LD
    fecha_schema = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')
    if fecha_fuente:
        try:
            fecha_str = str(fecha_fuente).replace('Z','+00:00')
            datetime.fromisoformat(fecha_str)
            fecha_schema = fecha_str if ('+' in fecha_str or fecha_str.endswith('Z')) else fecha_str + '+00:00'
        except: pass
    titulo_schema = titulo_final.replace('"',"'").replace('\\','')
    meta_schema = (meta_desc or contenido[:155]).replace('"',"'").replace('\\\\','')
    LOGO_URL_FIJO = f"{WP_URL}/wp-content/uploads/favicon_512.png"
    schema_markup = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "{titulo_schema}",
  "datePublished": "{fecha_schema}",
  "dateModified": "{datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}",
  "description": "{meta_schema}",
  "inLanguage": "es",
  "isAccessibleForFree": "True",
  "author": {{"@type":"Organization","name":"Verdad Hoy","url":"{WP_URL}"}},
  "publisher": {{"@type":"Organization","name":"Verdad Hoy","url":"{WP_URL}","logo":{{"@type":"ImageObject","url":"{LOGO_URL_FIJO}","width":512,"height":512}}}},
  "mainEntityOfPage": {{"@type":"WebPage","@id":"{WP_URL}/"}}
}}
</script>"""

    palabras_art = len(re.sub(r'<[^>]+>','',contenido_html).split())
    minutos_lect = max(2, round(palabras_art / 200))
    barra_lectura = f'<p style="font-size:0.82em;color:#6b7280;margin:0 0 20px 0;">🕐 Tiempo de lectura: <strong>{minutos_lect} min</strong></p>'

    enlace_fuente_html = (f'<a href="{fuente_url}" target="_blank" rel="noopener">{nombre_medio}</a>' if fuente_url else nombre_medio)

    contenido_final = f"""
{barra_lectura}
{contenido_html}
<hr>
<p><strong>Fuente:</strong> {enlace_fuente_html}</p>
<p><em>Información verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
{schema_markup}
"""

    # Fecha WP
    fecha_wp = None
    if fecha_fuente:
        try:
            dt = datetime.fromisoformat(str(fecha_fuente).replace('Z','+00:00'))
            fecha_wp = dt.strftime('%Y-%m-%dT%H:%M:%S')
        except: pass

    # V19: status según es_borrador
    status_wp = 'draft' if es_borrador else 'publish'
    log(f"📤 Publicando como '{status_wp}' — {'BORRADOR evergreen' if es_borrador else 'VISIBLE al público'}",'info')

    post_data = {
        'title':          titulo_final,
        'slug':           slug_post,
        'content':        contenido_final,
        'excerpt':        meta_desc,
        'status':         status_wp,
        'featured_media': imagen_id,
        'categories':     categorias_ids,
        'tags':           tags_ids,
        'meta': {
            '_yoast_wpseo_title':    titulo_seo,
            '_yoast_wpseo_metadesc': meta_desc,
            '_yoast_wpseo_focuskw':  frase_clave,
        }
    }
    if fecha_wp: post_data['date'] = fecha_wp

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data, auth=(WP_USER, WP_APP_PASSWORD), timeout=30).json()
        if 'id' in r:
            post_id      = r['id']
            url_articulo = r.get('link', f"{WP_URL}/?p={post_id}")
            tipo_str = "BORRADOR" if es_borrador else "PUBLICADO"
            log(f"✅ {tipo_str} en WordPress: {url_articulo}",'exito')

            # Guardar SEO Rank Math
            seo_guardado = False
            try:
                rankmath_payload = {
                    'objectID':post_id,'objectType':'post',
                    'meta':{'rank_math_focus_keyword':frase_clave,'rank_math_title':titulo_seo,
                            'rank_math_description':meta_desc,'rank_math_robots':['index','follow']}
                }
                r_rm = requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta",
                    json=rankmath_payload, auth=(WP_USER, WP_APP_PASSWORD), timeout=10)
                if r_rm.status_code in (200,201):
                    log(f"✅ Rank Math SEO guardado (focuskw: {frase_clave[:40]})",'exito')
                    seo_guardado = True
            except Exception as e_rm:
                log(f"ℹ️ Rank Math no disponible ({e_rm})",'debug')

            if not seo_guardado:
                try:
                    meta_patch = {
                        'rank_math_focus_keyword':frase_clave,'rank_math_title':titulo_seo,'rank_math_description':meta_desc,
                        '_yoast_wpseo_focuskw':frase_clave,'_yoast_wpseo_title':titulo_seo,'_yoast_wpseo_metadesc':meta_desc,
                    }
                    r_patch = requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                        json={'meta':meta_patch}, auth=(WP_USER, WP_APP_PASSWORD), timeout=10)
                    if r_patch.status_code in (200,201):
                        log(f"✅ SEO guardado via PATCH REST",'exito')
                except Exception as e_patch:
                    log(f"⚠️ No se pudo guardar SEO meta: {e_patch}",'advertencia')

            if es_borrador:
                log(f"📝 Borrador listo para revisión manual en: {WP_URL}/wp-admin/post.php?post={post_id}&action=edit",'info')

            return url_articulo, slug_cat
        else:
            log(f"❌ Error WP: {r.get('message','desconocido')}",'error')
    except Exception as e:
        log(f"❌ Excepción WP: {e}",'error')
    return None, None


# ══════════════════════════════════════════════════════════
# FUENTES RSS, NEWSAPI, GNEWS, NEWSDATA
# (se mantienen igual que V18 — solo se copian las funciones principales)
# ══════════════════════════════════════════════════════════
def extraer_contenido(url):
    if not url: return None, None
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
                    if len(txt) > 200: return txt[:5000], None
        return None, None
    except: return None, None

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
        overlay_draw.rounded_rectangle([x-padding, y-padding, x+txt_w+padding, y+txt_h+padding], radius=6, fill=(0,0,0,180))
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((x+1, y+1), texto_wm, font=font_wm, fill=(0,0,0,200))
        draw.text((x, y), texto_wm, font=font_wm, fill='#f5c518')
        return img
    except Exception as e:
        log(f"⚠️ Watermark error: {e}",'debug')
        return img

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
        data = r.content
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 300 or h < 200: return None
        if img.mode in ('RGBA','P','LA'): img = img.convert('RGB')
        MIN_W, MAX_W = 1200, 1600
        if w < MIN_W:
            ratio = MIN_W / w
            img = img.resize((MIN_W, int(h*ratio)), Image.LANCZOS)
        elif w > MAX_W:
            ratio = MAX_W / w
            img = img.resize((MAX_W, int(h*ratio)), Image.LANCZOS)
        img = agregar_watermark(img)
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=92, optimize=True)
        if os.path.getsize(p) < 3000:
            os.remove(p)
            return None
        return p
    except Exception as e:
        log(f"⚠️ Error descargando imagen: {e}",'debug')
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
            r_c = int(15+(30-15)*ratio); g_c = int(23+(41-23)*ratio); b_c = int(42+(69-42)*ratio)
            draw.line([(0,i),(W,i)], fill=(r_c,g_c,b_c))
        draw.rectangle([(0,0),(W,10)], fill='#dc2626')
        colores_cat = {'guerra':'#dc2626','politica':'#7c3aed','economia':'#059669','tecnologia':'#2563eb',
                       'deportes':'#d97706','ciencia':'#0891b2','salud':'#16a34a','entretenimiento':'#db2777',
                       'latinoamerica':'#ea580c','clima':'#0284c7','medio_ambiente':'#15803d',
                       'crimen':'#9f1239','desastre':'#b45309','mundo':'#4338ca','general':'#475569'}
        nombres_cat = {'guerra':'CONFLICTO','politica':'POLÍTICA','economia':'ECONOMÍA','tecnologia':'TECNOLOGÍA',
                       'deportes':'DEPORTES','ciencia':'CIENCIA','salud':'SALUD','entretenimiento':'ENTRETENIMIENTO',
                       'latinoamerica':'LATINOAMÉRICA','clima':'CLIMA','medio_ambiente':'MEDIO AMBIENTE',
                       'crimen':'SEGURIDAD','desastre':'EMERGENCIA','mundo':'MUNDO','general':'NOTICIAS'}
        color_badge = colores_cat.get(categoria,'#475569')
        texto_badge = nombres_cat.get(categoria,'NOTICIAS')
        try:
            font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 62)
            font_marca  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
            font_sub    = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            font_badge = font_titulo = font_marca = font_sub = ImageFont.load_default()
        badge_x, badge_y = 70, 70
        try:
            bbox_b = draw.textbbox((0,0), texto_badge, font=font_badge)
            bw, bh = bbox_b[2]-bbox_b[0], bbox_b[3]-bbox_b[1]
        except: bw, bh = 160, 32
        draw.rounded_rectangle([badge_x, badge_y, badge_x+bw+28, badge_y+bh+16], radius=6, fill=color_badge)
        draw.text((badge_x+14, badge_y+8), texto_badge, font=font_badge, fill='white')
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
        draw.text((70,H-65), "🌍 VERDAD HOY", font=font_marca, fill='#f1f5f9')
        draw.text((W-420,H-60), "verdadhoy.com", font=font_sub, fill='#94a3b8')
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img = agregar_watermark(img)
        img.save(p, 'JPEG', quality=92, optimize=True)
        return p
    except Exception as e:
        log(f"⚠️ Error generando imagen fallback: {e}",'debug')
        return None

def deduplicar_batch(noticias):
    urls_vistas = set(); titulos_vistos = []; resultado = []
    for n in noticias:
        url_n = normalizar_url(n.get('url',''))
        titulo = n.get('titulo','')
        if not url_n or not titulo: continue
        if url_n in urls_vistas: continue
        if any(similitud_titulos(titulo, t) > 0.78 for t in titulos_vistos): continue
        urls_vistas.add(url_n); titulos_vistos.append(titulo); resultado.append(n)
    log(f"Dedup batch: {len(noticias)} → {len(resultado)} únicas",'info')
    return resultado

def obtener_rss():
    fuentes = [
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/','Infobae América'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/economia/','Infobae Economía'),
        ('https://www.eluniversal.com.mx/rss.xml','El Universal MX'),
        ('https://www.milenio.com/rss','Milenio MX'),
        ('https://www.lanacion.com.ar/arc/outboundfeeds/rss/','La Nación Argentina'),
        ('https://www.pagina12.com.ar/rss/portada','Página 12 AR'),
        ('https://www.clarin.com/rss/elmundo/','Clarín Mundo'),
        ('https://www.eltiempo.com/rss/portada.xml','El Tiempo Colombia'),
        ('https://www.semana.com/rss.xml','Semana Colombia'),
        ('https://elcomercio.pe/arcio/rss/','El Comercio Perú'),
        ('https://rpp.pe/rss/','RPP Perú'),
        ('https://efectococuyo.com/feed/','Efecto Cocuyo VE'),
        ('https://www.eluniverso.com/rss.xml','El Universo Ecuador'),
        ('https://www.elpais.com.uy/rss.xml','El País Uruguay'),
        ('http://feeds.bbci.co.uk/mundo/rss.xml','BBC Mundo'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada','El País Internacional'),
        ('https://www.dw.com/es/ultimas-noticias/s-30689792/rss','Deutsche Welle ES'),
        ('https://feeds.france24.com/es/','France 24 ES'),
        ('https://www.efe.com/efe/espana/1/rss','EFE'),
        ('https://www.espn.com.mx/rss/deportes.xml','ESPN Deportes'),
        ('https://e00-marca.uecdn.es/rss/portada.xml','Marca'),
        ('https://feeds.as.com/mrss-s/pages/as/site/as.com/portada/','AS Deportes'),
        ('https://feeds.xataka.com/xataka','Xataka'),
        ('https://hipertextual.com/feed','Hipertextual'),
    ]
    noticias = []
    for url_feed, nombre in fuentes:
        try:
            r = requests.get(url_feed, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200: continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries: continue
            for e in feed.entries[:8]:
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
                        if enc.get('type','').startswith('image'):
                            img = enc.get('href') or enc.get('url'); break
                if es_noticia_espana_domestica(t, d): continue
                noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),'url':l,'imagen':img,
                                 'fuente':f"RSS:{nombre}",'fecha':e.get('published'),'puntaje':calcular_puntaje(t,d)})
        except Exception as e:
            log(f"RSS error ({nombre}): {e}",'advertencia')
    log(f"RSS: {len(noticias)} noticias",'info')
    return noticias

def obtener_rss_chile():
    fuentes_chile = [
        ('https://www.emol.com/rss/','Emol'),
        ('https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml','Cooperativa'),
        ('https://www.cnnchile.com/feed/','CNN Chile'),
        ('https://www.lacuarta.com/feed/','La Cuarta'),
    ]
    noticias = []
    for url_feed, nombre in fuentes_chile:
        try:
            try: r = requests.get(url_feed, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            except: time.sleep(1.5); r = requests.get(url_feed, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
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
                        if enc.get('type','').startswith('image'):
                            img = enc.get('href') or enc.get('url'); break
                noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),'url':l,'imagen':img,
                                 'fuente':f"RSS_CL:{nombre}",'fecha':e.get('published'),
                                 'puntaje':calcular_puntaje(t,d)+5,'pais':'chile'})
        except Exception as ex:
            log(f"RSS Chile error ({nombre}): {ex}",'advertencia')
    log(f"RSS Chile: {len(noticias)} noticias",'info')
    return noticias

def obtener_rss_latam():
    fuentes_latam = [
        ('https://www.eluniversal.com.mx/rss.xml','El Universal MX','mexico'),
        ('https://www.milenio.com/rss','Milenio MX','mexico'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/','Infobae América','argentina'),
        ('https://www.lanacion.com.ar/arc/outboundfeeds/rss/','La Nación AR','argentina'),
        ('https://www.pagina12.com.ar/rss/portada','Página 12 AR','argentina'),
        ('https://www.eltiempo.com/rss/portada.xml','El Tiempo CO','colombia'),
        ('https://www.semana.com/rss.xml','Semana CO','colombia'),
        ('https://elcomercio.pe/arcio/rss/','El Comercio PE','peru'),
        ('https://rpp.pe/rss/','RPP Perú','peru'),
        ('https://efectococuyo.com/feed/','Efecto Cocuyo VE','venezuela'),
        ('https://www.paginasiete.bo/rss.xml','Página Siete BO','bolivia'),
        ('https://www.eluniverso.com/rss.xml','El Universo EC','ecuador'),
        ('https://www.elpais.com.uy/rss.xml','El País UY','uruguay'),
        ('https://www.clarin.com/rss/elmundo/','Clarín Mundo','latam'),
    ]
    noticias = []
    for url_feed, nombre, pais in fuentes_latam:
        try:
            r = requests.get(url_feed, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200: continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries: continue
            for e in feed.entries[:8]:
                t = e.get('title','')
                if not t: continue
                t = re.sub(r'\s*-\s*[^-]*$','',t)
                l = e.get('link','')
                if not l: continue
                d = re.sub(r'<[^>]+>','',e.get('summary','') or e.get('description',''))
                if es_noticia_chile(t, d): continue
                img = None
                if hasattr(e,'media_content') and e.media_content: img = e.media_content[0].get('url')
                if not img:
                    for enc in getattr(e,'enclosures',[]):
                        if enc.get('type','').startswith('image'):
                            img = enc.get('href') or enc.get('url'); break
                noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),'url':l,'imagen':img,
                                 'fuente':f"RSS_LATAM:{nombre}",'fecha':e.get('published'),
                                 'puntaje':calcular_puntaje(t,d)+3,'pais':pais})
        except Exception as ex:
            log(f"RSS LATAM error ({nombre}): {ex}",'advertencia')
    log(f"RSS LATAM: {len(noticias)} noticias",'info')
    return noticias

def obtener_newsapi():
    if not NEWS_API_KEY: return []
    queries = [
        'Chile noticias economía política hoy','Chile Argentina Colombia últimas noticias',
        'México Brasil Perú América Latina hoy','Venezuela Bolivia Ecuador Uruguay noticias',
        'Latinoamérica economía inversión noticias','Boric Milei Lula Sheinbaum política',
        'Copa Libertadores Sudamericana fútbol LATAM','eliminatorias Mundial 2026 Sudamérica',
        'dólar inflación Argentina Chile México','litio cobre minería Latinoamérica',
        'startups tecnología América Latina fintech','reggaeton música latina Bad Bunny Shakira',
        'economy inflation markets Latin America impact','technology artificial intelligence Spanish',
        'Trump tariffs trade Latin America','climate change South America environment',
        'football soccer Champions League goals','Copa del Mundo 2026 World Cup Messi',
        'NBA basketball playoffs finals','Formula 1 F1 Grand Prix race',
        'Netflix series premiere streaming español','music Grammy Billboard Latin',
        'Ukraine Russia war conflict','science space NASA discovery',
    ]
    noticias = []
    for q in queries:
        try:
            r = requests.get('https://newsapi.org/v2/everything',
                params={'apiKey':NEWS_API_KEY,'q':q,'language':'es','sortBy':'publishedAt','pageSize':5},
                timeout=15).json()
            if r.get('status') == 'ok':
                for a in r.get('articles',[]):
                    t = a.get('title',''); img = a.get('urlToImage')
                    if not t or '[Removed]' in t or not img: continue
                    d = a.get('description','')
                    if es_noticia_espana_domestica(t, d): continue
                    noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),
                                     'url':a.get('url',''),'imagen':img,'fuente':f"NewsAPI:{a.get('source',{}).get('name','')}",
                                     'fecha':a.get('publishedAt'),'puntaje':calcular_puntaje(t,d)})
        except Exception as e:
            log(f"NewsAPI error ({q[:20]}): {e}",'advertencia')
    log(f"NewsAPI: {len(noticias)} noticias",'info')
    return noticias

def obtener_newsdata():
    if not NEWSDATA_API_KEY: return []
    categorias = ['world','politics','business','technology','science','health','entertainment','sports']
    PAISES_NEWSDATA = 'cl,ar,mx,co,pe'
    noticias = []
    for cat in categorias:
        try:
            r = requests.get('https://newsdata.io/api/1/news',
                params={'apikey':NEWSDATA_API_KEY,'language':'es','country':PAISES_NEWSDATA,
                        'category':cat,'size':10,'image':1},
                timeout=15).json()
            if r.get('status') == 'success':
                for a in r.get('results',[]):
                    t = a.get('title') or ''; img = a.get('image_url')
                    if not t or not img: continue
                    d = a.get('description') or ''
                    if es_noticia_espana_domestica(t, d): continue
                    noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),
                                     'url':a.get('link',''),'imagen':img,'fuente':f"NewsData:{a.get('source_id','')}",
                                     'fecha':a.get('pubDate'),'puntaje':calcular_puntaje(t,d)})
        except Exception as e:
            log(f"NewsData error ({cat}): {e}",'advertencia')
    log(f"NewsData: {len(noticias)} noticias",'info')
    return noticias

def obtener_gnews():
    if not GNEWS_API_KEY: return []
    topicos_paises = [('world','mx'),('nation','cl'),('business','ar'),('technology','co'),
                      ('sports','mx'),('health','cl'),('science','ar'),('entertainment','co')]
    noticias = []
    for topic, pais in topicos_paises:
        try:
            r = requests.get('https://gnews.io/api/v4/top-headlines',
                params={'apikey':GNEWS_API_KEY,'lang':'es','max':10,'topic':topic,'country':pais},
                timeout=15).json()
            for a in r.get('articles',[]):
                t = a.get('title') or ''; img = a.get('image')
                if not t or not img: continue
                d = a.get('description') or ''
                if es_noticia_espana_domestica(t, d): continue
                noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),
                                 'url':a.get('url',''),'imagen':img,'fuente':f"GNews:{a.get('source',{}).get('name','')}",
                                 'fecha':a.get('publishedAt'),'puntaje':calcular_puntaje(t,d)})
        except Exception as e:
            log(f"GNews error ({topic}/{pais}): {e}",'advertencia')
    log(f"GNews: {len(noticias)} noticias",'info')
    return noticias

def obtener_newsapi_chile():
    if not NEWS_API_KEY: return []
    queries_chile = ['Chile noticias hoy Santiago','Chile economía dólar peso chileno inflación',
                     'Chile Boric gobierno política','Chile Carabineros seguridad',
                     'Chile fútbol Colo-Colo Universidad Chile La Roja','Chile terremoto sismo',
                     'Chile litio cobre minería Codelco','Chile salud hospital sistema público']
    noticias = []
    for q in queries_chile:
        try:
            r = requests.get('https://newsapi.org/v2/everything',
                params={'apiKey':NEWS_API_KEY,'q':q,'language':'es','sortBy':'publishedAt','pageSize':5},
                timeout=15).json()
            if r.get('status') == 'ok':
                for a in r.get('articles',[]):
                    t = a.get('title',''); img = a.get('urlToImage')
                    if not t or '[Removed]' in t or not img: continue
                    d = a.get('description','')
                    if not es_noticia_chile(t, d): continue
                    noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),
                                     'url':a.get('url',''),'imagen':img,'fuente':f"NewsAPI_CL:{a.get('source',{}).get('name','')}",
                                     'fecha':a.get('publishedAt'),'puntaje':calcular_puntaje(t,d),'pais':'chile'})
        except Exception as ex:
            log(f"NewsAPI Chile error ({q[:25]}): {ex}",'advertencia')
    log(f"NewsAPI Chile: {len(noticias)} noticias",'info')
    return noticias

def obtener_newsapi_latam():
    if not NEWS_API_KEY: return []
    queries_latam = ['México noticias CDMX Sheinbaum','Argentina Milei economía inflación',
                     'Colombia Petro Bogotá noticias','Brasil Lula sao paulo',
                     'Venezuela Maduro Caracas crisis','Perú Lima noticias gobierno',
                     'Ecuador Quito Noboa noticias','Bolivia La Paz gobierno',
                     'El Salvador Bukele noticias','América Latina economía política',
                     'Centroamérica migración crisis']
    noticias = []
    for q in queries_latam:
        try:
            r = requests.get('https://newsapi.org/v2/everything',
                params={'apiKey':NEWS_API_KEY,'q':q,'language':'es','sortBy':'publishedAt','pageSize':5},
                timeout=15).json()
            if r.get('status') == 'ok':
                for a in r.get('articles',[]):
                    t = a.get('title',''); img = a.get('urlToImage')
                    if not t or '[Removed]' in t or not img: continue
                    d = a.get('description','')
                    if es_noticia_chile(t, d): continue
                    noticias.append({'titulo':limpiar_texto(t),'descripcion':limpiar_texto(d),
                                     'url':a.get('url',''),'imagen':img,'fuente':f"NewsAPI_LATAM:{a.get('source',{}).get('name','')}",
                                     'fecha':a.get('publishedAt'),'puntaje':calcular_puntaje(t,d),'pais':'latam'})
        except Exception as ex:
            log(f"NewsAPI LATAM error ({q[:25]}): {ex}",'advertencia')
    log(f"NewsAPI LATAM: {len(noticias)} noticias",'info')
    return noticias


# ══════════════════════════════════════════════════════════
# MAIN V19 — FLUJO PRINCIPAL CON PUBLICACIÓN MIXTA
# ══════════════════════════════════════════════════════════
def es_candidata_evergreen(noticia):
    """V19: determina si una noticia debe ir a borrador (evergreen)."""
    tema = detectar_tema(noticia.get('titulo',''), noticia.get('descripcion',''))
    return tema in {'ciencia','tecnologia','salud','medio_ambiente'}

def main():
    print("\n" + "="*60)
    print(f"🌍 BOT DE NOTICIAS - {VERSION_BOT}")
    print(f"   Publicación mixta: {MAX_POSTS_DIA_DIRECTOS} directas + {MAX_POSTS_DIA_BORRADORES} borradores/día")
    print(f"   Foco LATAM: Tier1=Chile/Argentina/México (+{BONUS_TIER1})")
    print(f"              Tier2=Colombia/Brasil (+{BONUS_TIER2})")
    print(f"              Tier3=resto LATAM (+{BONUS_TIER3})")
    print(f"   Rank Math 80+ sin edición (noticias directas)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    if MODO_LATAM:
        log("ℹ️ MODO_LATAM detectado — desde V18/V19 se usa flujo único. Puedes quitar MODO_LATAM del .yml.",'advertencia')

    h = cargar_historial()
    publicar_wp = puede_publicar_wp()
    publicar_fb = PUBLICAR_EN_FACEBOOK and puede_publicar_fb(h)

    if not PUBLICAR_EN_FACEBOOK:
        log("📘 Facebook DESACTIVADO (intencional)",'info')

    if not publicar_wp and not publicar_fb:
        log("⏱️ Nada que publicar — esperando próximo ciclo",'info')
        return None

    exito_wp = False
    exito_fb = False

    if publicar_wp:
        cuotas_hoy = cargar_cuotas_hoy()
        directos_hoy   = cuotas_hoy.get('directos', 0)
        borradores_hoy = cuotas_hoy.get('borradores', 0)
        log(f"📊 Estado hoy: {directos_hoy}/{MAX_POSTS_DIA_DIRECTOS} directas | {borradores_hoy}/{MAX_POSTS_DIA_BORRADORES} borradores",'info')

        # Reunir todas las fuentes
        noticias = []
        if NEWS_API_KEY: noticias.extend(obtener_newsapi())
        if NEWSDATA_API_KEY: noticias.extend(obtener_newsdata())
        if GNEWS_API_KEY: noticias.extend(obtener_gnews())
        if len(noticias) < 15:
            log("⚠️ Pocas noticias — complementando con RSS",'advertencia')
            noticias.extend(obtener_rss())
        noticias.extend(obtener_rss_chile())
        noticias.extend(obtener_newsapi_chile())
        noticias.extend(obtener_rss_latam())
        noticias.extend(obtener_newsapi_latam())

        if not noticias:
            log("ERROR: Ninguna fuente devolvió noticias",'error')
            return None

        noticias = deduplicar_batch(noticias)
        for n in noticias:
            n['puntaje'] = n.get('puntaje',0) + bonus_frescura(n.get('fecha'))
        noticias.sort(key=lambda x: (x.get('puntaje',0), x.get('fecha','')), reverse=True)
        log(f"📰 Candidatas ordenadas: {len(noticias)}",'info')

        # Separar candidatas en directas y evergreen
        candidatas_directas   = []
        candidatas_evergreen  = []
        intentos = 0

        for i, nt in enumerate(noticias):
            if intentos >= 80: break
            total_recolectadas = len(candidatas_directas) + len(candidatas_evergreen)
            if total_recolectadas >= 8: break  # Suficientes candidatas para elegir

            url    = nt.get('url','')
            titulo = nt.get('titulo','')
            desc   = nt.get('descripcion','')
            if not url or not titulo: continue
            intentos += 1

            dup, razon = noticia_ya_publicada(h, url, titulo, desc)
            if dup:
                log(f"   ❌ {razon}",'debug')
                continue
            if nt.get('puntaje',0) < 3:
                log(f"   ❌ Puntaje bajo ({nt.get('puntaje',0)})",'debug')
                continue
            es_spam, kw_spam = es_contenido_spam(titulo, desc)
            if es_spam:
                log(f"   🚫 SPAM: '{kw_spam}'",'advertencia')
                continue

            cont_web, _ = extraer_contenido(url)
            if cont_web and len(cont_web) >= 500: contenido_ok = cont_web
            elif desc and len(desc) >= 400: contenido_ok = desc
            elif cont_web and len(cont_web) >= 250: contenido_ok = cont_web + ' ' + desc if desc else cont_web
            else:
                log("   ❌ Contenido insuficiente",'advertencia')
                continue

            es_spam2, kw_spam2 = es_contenido_spam(titulo, contenido_ok[:3000])
            if es_spam2:
                log(f"   🚫 SPAM en contenido: '{kw_spam2}'",'advertencia')
                continue

            imagen_encontrada = None
            if nt.get('imagen'): imagen_encontrada = descargar_imagen(nt['imagen'])
            if not imagen_encontrada:
                img_url = extraer_imagen_web(url)
                if img_url: imagen_encontrada = descargar_imagen(img_url)
            if not imagen_encontrada:
                tema_fb = detectar_tema(titulo, desc)
                imagen_encontrada = crear_imagen_titulo(titulo, tema_fb)
            if not imagen_encontrada:
                log("   ❌ Sin imagen",'advertencia')
                continue

            # V19: clasificar como evergreen o directa
            if es_candidata_evergreen(nt) and borradores_hoy < MAX_POSTS_DIA_BORRADORES and len(candidatas_evergreen) < MAX_POSTS_DIA_BORRADORES:
                candidatas_evergreen.append((nt, contenido_ok, imagen_encontrada))
                log(f"   ✅ Candidata EVERGREEN (borrador): {titulo[:55]}",'info')
            elif directos_hoy + len(candidatas_directas) < MAX_POSTS_DIA_DIRECTOS:
                candidatas_directas.append((nt, contenido_ok, imagen_encontrada))
                log(f"   ✅ Candidata DIRECTA: {titulo[:55]}",'info')
            else:
                # Si ya tenemos suficientes de ambos tipos, guardamos como directa de respaldo
                candidatas_directas.append((nt, contenido_ok, imagen_encontrada))

        # Rotación de categorías
        categorias_hoy = categorias_usadas_hoy()
        log(f"🔄 Categorías usadas hoy: {sorted(categorias_hoy) if categorias_hoy else '(ninguna)'}",'info')

        def _slug_estimado(item):
            nt_x, cont_x, _ = item
            tema_x = detectar_tema(nt_x.get('titulo',''), nt_x.get('descripcion',''))
            tema_x = ajustar_categoria_por_cuota(tema_x)
            return resolver_categoria_wp(tema_x, nt_x.get('titulo',''), cont_x[:1500])

        for lista in [candidatas_directas, candidatas_evergreen]:
            lista.sort(key=lambda item: (0 if _slug_estimado(item) not in categorias_hoy else 1, -item[0].get('puntaje',0)))

        # Publicar directas
        log(f"\n🚀 Publicando {len(candidatas_directas)} candidatas directas (visibles al público)...",'info')
        for idx, (nt_pub, cont_pub, img_pub) in enumerate(candidatas_directas):
            if directos_hoy >= MAX_POSTS_DIA_DIRECTOS:
                log(f"✅ Cupo directas completado ({MAX_POSTS_DIA_DIRECTOS}/{MAX_POSTS_DIA_DIRECTOS})",'info')
                break
            log(f"\n📝 DIRECTA ({idx+1}): {nt_pub['titulo'][:70]}")
            tema_s = detectar_tema(nt_pub['titulo'], nt_pub.get('descripcion',''))
            tema_s = ajustar_categoria_por_cuota(tema_s)
            url_wp, cat_final = publicar_en_wordpress(
                titulo=nt_pub['titulo'], contenido=cont_pub, tema=tema_s,
                imagen_path=img_pub, fuente_url=nt_pub['url'],
                fecha_fuente=nt_pub.get('fecha'), fuente_noticia=nt_pub.get('fuente',''),
                es_borrador=False
            )
            try:
                if img_pub and os.path.exists(img_pub): os.remove(img_pub)
            except: pass
            if url_wp:
                exito_wp = True
                directos_hoy += 1
                registrar_cuota(cat_final or tema_s, es_borrador=False)
                guardar_estado_wp()
                h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp',0) + 1
                desc_full = (nt_pub.get('descripcion','') + ' ' + cont_pub[:400]).strip()
                h = guardar_en_historial(h, nt_pub['url'], nt_pub['titulo'], desc_full)
            else:
                log("   ⚠️ No se pudo publicar — siguiente candidata",'advertencia')

        # Publicar borradores (evergreen)
        log(f"\n📝 Guardando {len(candidatas_evergreen)} candidatas evergreen como borradores...",'info')
        for idx, (nt_pub, cont_pub, img_pub) in enumerate(candidatas_evergreen):
            cuotas_recheck = cargar_cuotas_hoy()
            if cuotas_recheck.get('borradores',0) >= MAX_POSTS_DIA_BORRADORES:
                log(f"✅ Cupo borradores completado ({MAX_POSTS_DIA_BORRADORES}/{MAX_POSTS_DIA_BORRADORES})",'info')
                break
            log(f"\n📝 BORRADOR EVERGREEN ({idx+1}): {nt_pub['titulo'][:70]}")
            tema_s = detectar_tema(nt_pub['titulo'], nt_pub.get('descripcion',''))
            tema_s = ajustar_categoria_por_cuota(tema_s)
            url_wp, cat_final = publicar_en_wordpress(
                titulo=nt_pub['titulo'], contenido=cont_pub, tema=tema_s,
                imagen_path=img_pub, fuente_url=nt_pub['url'],
                fecha_fuente=nt_pub.get('fecha'), fuente_noticia=nt_pub.get('fuente',''),
                es_borrador=True
            )
            try:
                if img_pub and os.path.exists(img_pub): os.remove(img_pub)
            except: pass
            if url_wp:
                exito_wp = True
                registrar_cuota(cat_final or tema_s, es_borrador=True)
                guardar_estado_wp()
                h['estadisticas']['total_borradores'] = h['estadisticas'].get('total_borradores',0) + 1
                desc_full = (nt_pub.get('descripcion','') + ' ' + cont_pub[:400]).strip()
                h = guardar_en_historial(h, nt_pub['url'], nt_pub['titulo'], desc_full)
            else:
                log("   ⚠️ No se pudo guardar borrador — siguiente",'advertencia')

        # Limpiar imágenes sobrantes
        for lista in [candidatas_directas, candidatas_evergreen]:
            for _, _, img_s in lista:
                try:
                    if img_s and os.path.exists(img_s): os.remove(img_s)
                except: pass

    # Resumen final
    cuotas_fin = cargar_cuotas_hoy()
    stats = h.get('estadisticas',{})
    log(f"\n{'='*50}",'info')
    log(f"✅ RESUMEN {VERSION_BOT}:",'exito')
    log(f"   Directas hoy:   {cuotas_fin.get('directos',0)}/{MAX_POSTS_DIA_DIRECTOS}",'info')
    log(f"   Borradores hoy: {cuotas_fin.get('borradores',0)}/{MAX_POSTS_DIA_BORRADORES}",'info')
    log(f"   Total WP acumulado:        {stats.get('total_wp',0)}",'info')
    log(f"   Total borradores acumulados: {stats.get('total_borradores',0)}",'info')
    cats_hoy = cuotas_fin.get('conteo',{})
    if cats_hoy:
        log(f"   Categorías: {', '.join(f'{c}:{n}' for c,n in cats_hoy.items())}",'info')
    log(f"   Esta ejecución → WP={'✅' if exito_wp else '❌'}",'info')
    if exito_wp:
        log("💡 Hacer git push de los JSON de estado",'advertencia')
        return True
    return False

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0)
    except Exception as e:
        log(f"Error crítico: {e}",'error')
        import traceback
        traceback.print_exc()
        exit(1)
