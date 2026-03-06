import requests
import random
import re
import hashlib
import os
import json
import feedparser
from datetime import datetime
from PIL import Image
from io import BytesIO

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

# CATEGORÍAS Y PALABRAS CLAVE PRIORITARIAS
CATEGORIAS = {
    'politica': {
        'keywords': ['presidente', 'gobierno', 'ministro', 'congreso', 'senado', 'elecciones', 
                    'reforma', 'ley', 'constitución', 'corrupción', 'destitución', 'parlamento',
                    'oposición', 'debate político', 'coalición', 'protesta', 'referéndum'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada',
            'https://www.abc.es/rss/feeds/abc_Espana.xml',
        ]
    },
    'economia': {
        'keywords': ['inflación', 'economía', 'crisis económica', 'mercado financiero', 'bolsa',
                    'inversión', 'banco', 'impuestos', 'empleo', 'desempleo', 'dólar', 'precio',
                    'recesión', 'crecimiento económico', 'deuda pública', 'subsidio'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml',
        ]
    },
    'mundo': {
        'keywords': ['conflicto internacional', 'crisis internacional', 'diplomacia', 'sanciones',
                    'tratado', 'migración', 'refugiados', 'geopolítica', 'guerra', 'tensión',
                    'ataque', 'bombardeo', 'misil', 'ejército', 'operación militar', 'invasión'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/internacional.xml',
        ]
    },
    'seguridad': {
        'keywords': ['crimen', 'delito', 'robo', 'homicidio', 'detenido', 'narcotráfico', 
                    'banda criminal', 'justicia', 'tribunal', 'juicio', 'condena', 'fiscalía',
                    'operativo policial', 'seguridad ciudadana', 'investigación'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/sociedad/portada',
        ]
    },
    'tecnologia': {
        'keywords': ['inteligencia artificial', 'IA', 'tecnología', 'ciberseguridad', 'hackeo',
                    'redes sociales', 'smartphone', 'innovación', 'startup', 'aplicación',
                    'robótica', 'internet', 'plataforma digital', 'big data'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada',
            'https://www.xataka.com/feedburner.xml',
        ]
    },
    'salud': {
        'keywords': ['pandemia', 'vacuna', 'enfermedad', 'hospital', 'salud', 'medicina',
                    'tratamiento', 'virus', 'epidemia', 'salud mental', 'investigación médica',
                    'sistema de salud', 'nutrición'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada',
        ]
    },
    'medio_ambiente': {
        'keywords': ['cambio climático', 'calentamiento global', 'sequía', 'inundación',
                    'incendio forestal', 'contaminación', 'energía renovable', 'sostenibilidad',
                    'biodiversidad', 'crisis climática', 'fenómeno climático'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/clima-medio-ambiente/portada',
        ]
    },
    'ciencia': {
        'keywords': ['descubrimiento', 'científicos', 'investigación', 'espacio', 'astronomía',
                    'misión espacial', 'planeta', 'universo', 'genética', 'física', 'biología'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada',
        ]
    },
    'deportes': {
        'keywords': ['fútbol', 'liga', 'campeonato', 'mundial', 'copa', 'partido', 'resultado',
                    'jugador', 'equipo', 'entrenador', 'fichaje', 'victoria', 'derrota',
                    'competición', 'olimpiadas', 'deportes'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada',
            'https://www.clarin.com/rss/deportes/',
            'https://e00-elmundo.uecdn.es/elmundo/rss/deportes.xml',
        ]
    },
    'tendencias': {
        'keywords': ['viral', 'tendencia', 'video viral', 'redes sociales', 'fenómeno viral',
                    'reto viral', 'curiosidad', 'sorprendente', 'impactante', 'polémica',
                    'última hora', 'urgente', 'confirmado', 'revelan', 'histórico'],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/gente/portada',
        ]
    }
}

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy (CATEGORIZADO)")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None, 'categorias': {}}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"📚 Historial: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"⚠️ Error historial: {e}")

def guardar_historial(url, titulo, categoria='general'):
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    if 'categorias' not in historial:
        historial['categorias'] = {}
    if categoria not in historial['categorias']:
        historial['categorias'][categoria] = []
    historial['categorias'][categoria].append(url)
    
    # Mantener solo últimas 500
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Historial guardado ({categoria})")
    except Exception as e:
        print(f"❌ Error guardando: {e}")

def get_url_id(url):
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:16]

def ya_publicada(url, titulo):
    url_id = get_url_id(url)
    if url_id in [get_url_id(u) for u in historial['urls']]:
        return True
    
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencia / max(len(titulo_simple), len(t_simple)) > 0.7:
                return True
    return False

def detectar_categoria(titulo, descripcion):
    """Detecta la categoría de la noticia basada en palabras clave"""
    texto = f"{titulo} {descripcion}".lower()
    
    puntuaciones = {}
    for cat, datos in CATEGORIAS.items():
        score = 0
        for keyword in datos['keywords']:
            if keyword.lower() in texto:
                score += 1
        puntuaciones[cat] = score
    
    # Devolver categoría con mayor puntuación
    if max(puntuaciones.values()) > 0:
        return max(puntuaciones, key=puntuaciones.get)
    return 'general'

def eliminar_urls(texto):
    """Elimina todas las URLs del texto"""
    if not texto:
        return texto
    # Patrón para detectar URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    texto_sin_urls = re.sub(url_pattern, '', texto)
    # Limpiar espacios dobles que quedan
    texto_sin_urls = re.sub(r'\s+', ' ', texto_sin_urls).strip()
    return texto_sin_urls

def generar_redaccion_completa(titulo, descripcion, fuente, categoria):
    """
    Genera redacción periodística COMPLETA sin cortes.
    Estructura: Titular + Lead (2-3 oraciones completas) + Cuerpo (3 párrafos completos) + Cierre
    """
    
    print(f"\n   📝 Procesando: {titulo[:50]}...")
    print(f"   🏷️ Categoría: {categoria}")
    
    # Limpiar descripción base y eliminar URLs
    desc_limpia = eliminar_urls(descripcion)
    desc_limpia = re.sub(r'<[^>]+>', '', str(desc_limpia)).strip()
    
    # Asegurar que la descripción tenga suficiente contenido
    if len(desc_limpia) < 30:
        desc_limpia = f"Se reporta un importante acontecimiento de relevancia internacional relacionado con {categoria}. Las autoridades competentes han confirmado la información."
    
    # Si tenemos IA, usarla
    if OPENROUTER_API_KEY:
        resultado = generar_con_ia(titulo, desc_limpia, fuente, categoria)
        if resultado and len(resultado['texto']) > 800:
            # Eliminar URLs del resultado
            resultado['texto'] = eliminar_urls(resultado['texto'])
            resultado['titular'] = eliminar_urls(resultado['titular'])
            return resultado
    
    # Plantilla mejorada sin cortes
    return plantilla_mejorada(titulo, desc_limpia, fuente, categoria)

def generar_con_ia(titulo, descripcion, fuente, categoria):
    """Genera usando OpenRouter"""
    try:
        prompt = f"""Eres un redactor senior de agencia EFE. Escribe una NOTICIA COMPLETA en español.

DATOS:
Título original: {titulo}
Descripción: {descripcion}
Fuente: {fuente}
Categoría: {categoria}

INSTRUCCIONES ESTRICTAS:
1. TITULAR: Máximo 90 caracteres, informativo, atractivo, estilo EFE. NO incluir URLs.
2. LEAD: Exactamente 2-3 oraciones COMPLETAS (mínimo 150, máximo 250 caracteres), incluye: qué pasó, quién, cuándo, dónde. Terminar con punto.
3. CUERPO: Exactamente 3 párrafos COMPLETOS, cada uno con 3-4 oraciones terminadas en punto:
   - Párrafo 1: Contexto y antecedentes (quiénes están involucrados)
   - Párrafo 2: Desarrollo actual (datos, cifras, declaraciones específicas)
   - Párrafo 3: Análisis e implicaciones (qué significa, consecuencias futuras)
4. CIERRE: 1 oración completa con próximos pasos + "(Agencias) / Fuente: {fuente}"
5. IMPORTANTE: NO incluir links, URLs, ni referencias a sitios web. Solo texto informativo.

REGLAS:
- ESPAÑOL NATIVO, no traducciones literales
- Oraciones COMPLETAS terminadas en punto
- NUNCA cortar una oración a la mitad
- Longitud total: 1400-1900 caracteres
- Estilo periodístico NEUTRO e informativo

FORMATO OBLIGATORIO:
TITULAR: [titular completo sin URLs]

LEAD: [lead de 2-3 oraciones completas terminadas en punto]

CUERPO:
[Párrafo 1 de 3-4 oraciones completas.]

[Párrafo 2 de 3-4 oraciones completas.]

[Párrafo 3 de 3-4 oraciones completas.]

CIERRE: [cierre de 1 oración completa con fuente]

FIN"""

        modelos = [
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "qwen/qwen-2-7b-instruct:free"
        ]
        
        for modelo in modelos:
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                        'HTTP-Referer': 'https://github.com',
                        'X-Title': 'Bot Noticias',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': modelo,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3,
                        'max_tokens': 1800
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        
                        # Extraer con manejo de errores mejorado
                        titular = extraer_campo(content, 'TITULAR:', 'LEAD:') or titulo[:90]
                        lead = extraer_campo(content, 'LEAD:', 'CUERPO:')
                        cuerpo = extraer_campo(content, 'CUERPO:', 'CIERRE:')
                        cierre = extraer_campo(content, 'CIERRE:', 'FIN')
                        
                        # Asegurar que no haya URLs
                        titular = eliminar_urls(titular)
                        lead = eliminar_urls(lead)
                        cuerpo = eliminar_urls(cuerpo)
                        cierre = eliminar_urls(cierre)
                        
                        if not cierre:
                            cierre = f"Se esperan actualizaciones oficiales. (Agencias) / Fuente: {fuente}."
                        
                        # Verificar que las oraciones estén completas (terminen en punto)
                        lead = asegurar_oraciones_completas(lead)
                        cuerpo = asegurar_oraciones_completas(cuerpo)
                        cierre = asegurar_oraciones_completas(cierre)
                        
                        # Construir texto completo
                        texto_completo = f"{lead}\n\n{cuerpo}\n\n{cierre}"
                        
                        # Verificar longitud y que no esté cortado
                        if len(texto_completo) > 1000:
                            print(f"   ✅ IA generó: {len(texto_completo)} caracteres")
                            return {
                                'titular': titular.strip()[:100],
                                'texto': texto_completo[:1950]
                            }
                            
            except Exception as e:
                print(f"   ⚠️ Error {modelo}: {e}")
                continue
                
    except Exception as e:
        print(f"   ⚠️ Error IA general: {e}")
    
    return None

def asegurar_oraciones_completas(texto):
    """Asegura que el texto termine con una oración completa"""
    if not texto:
        return texto
    
    texto = texto.strip()
    
    # Si termina con palabra incompleta (sin punto), buscar el último punto
    if not texto.endswith(('.', '!', '?')):
        # Buscar el último punto seguido de espacio o final
        last_period = max(texto.rfind('. '), texto.rfind('.'), texto.rfind('!'), texto.rfind('?'))
        if last_period > 50:  # Asegurar que no sea muy corto
            texto = texto[:last_period+1]
        else:
            texto += "."
    
    # Eliminar espacios antes de puntuación
    texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
    
    return texto.strip()

def extraer_campo(texto, inicio, fin):
    """Extrae campo entre dos marcadores de forma segura"""
    try:
        if inicio in texto:
            parte = texto.split(inicio)[1]
            if fin in parte:
                resultado = parte.split(fin)[0].strip()
                return resultado
            # Si no encuentra el fin, tomar hasta 800 caracteres o el primer punto seguido de espacio
            parte_limitada = parte[:800]
            # Buscar último punto completo
            ultimo_punto = parte_limitada.rfind('. ')
            if ultimo_punto > 100:
                return parte_limitada[:ultimo_punto+1]
            return parte_limitada
    except:
        pass
    return ""

def plantilla_mejorada(titulo, descripcion, fuente, categoria):
    """Plantilla periodística robusta sin cortes y sin URLs"""
    print(f"   📝 Usando plantilla mejorada...")
    
    # Eliminar URLs de la descripción
    descripcion = eliminar_urls(descripcion)
    
    # Crear lead completo (2-3 oraciones completas)
    oraciones_desc = [s.strip() for s in descripcion.split('.') if len(s.strip()) > 20]
    
    if len(oraciones_desc) >= 2:
        lead = f"{oraciones_desc[0]}. {oraciones_desc[1]}."
    elif len(oraciones_desc) == 1:
        lead = f"{oraciones_desc[0]}. Las autoridades competentes confirmaron la información en las últimas horas y continúan evaluando la situación."
    else:
        lead = f"Se reporta un importante acontecimiento relacionado con {categoria} que ha generado atención mediática. Las autoridades competentes han confirmado la información en las últimas horas y se esperan actualizaciones oficiales."
    
    # Asegurar que el lead termine en punto y no esté cortado
    lead = asegurar_oraciones_completas(lead)
    
    # Limitar lead pero sin cortar palabras (máximo 280 caracteres)
    if len(lead) > 280:
        lead = lead[:277].rsplit(' ', 1)[0] + "."
    
    # Párrafos completos según categoría
    templates_categoria = {
        'politica': {
            'p1': "El hecho político ha generado amplia repercusión en los círculos de poder y entre la ciudadanía. Las autoridades gubernamentales emitieron comunicados oficiales sobre el tema mientras diversos actores políticos posicionan sus posturas ante la opinión pública. Los analistas esperan definiciones claras en las próximas horas.",
            'p2': "Analistas políticos consultados señalan que este tipo de eventos requiere un seguimiento constante por parte de la sociedad. La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación y sus posibles implicaciones para el escenario nacional.",
            'p3': "Las implicaciones de este acontecimiento político podrían extenderse a diversos sectores de la administración pública. Expertos destacan la necesidad de mantener una postura informada ante los desarrollos que se presenten en los próximos días."
        },
        'economia': {
            'p1': "El indicador económico ha captado la atención de analistas financieros y del sector empresarial. Las entidades bancarias y reguladoras monitorean de cerca la evolución de los datos para determinar posibles ajustes en sus proyecciones trimestrales.",
            'p2': "Especialistas en economía señalan que este comportamiento del mercado requiere análisis detallado. La información disponible sugiere tendencias que podrían afectar a consumidores e inversionistas en el corto y mediano plazo.",
            'p3': "Las proyecciones económicas indican posibles ajustes en las políticas monetarias y fiscales. Los sectores productivos mantienen expectativa sobre las medidas que podrían implementarse para estabilizar los indicadores financieros."
        },
        'mundo': {
            'p1': "El evento internacional ha generado reacciones en diversos países y organismos multilaterales. Las cancillerías involucradas mantienen comunicación constante para evaluar la situación y coordinar posibles respuestas diplomáticas ante la comunidad global.",
            'p2': "Observadores internacionales destacan la trascendencia de los hechos reportados en el contexto geopolítico actual. La comunidad global sigue con atención los desarrollos mientras se analizan las posibles consecuencias regionales.",
            'p3': "Las implicaciones de esta situación internacional podrían afectar las relaciones bilaterales y multilaterales. Se esperan declaraciones oficiales adicionales de los actores involucrados en las próximas horas."
        },
        'deportes': {
            'p1': "El acontecimiento deportivo ha generado gran expectativa entre aficionados y especialistas del sector. Los protagonistas del hecho deportivo han sido centro de atención en medios especializados y plataformas de redes sociales durante las últimas horas.",
            'p2': "Analistas deportivos señalan la importancia de este resultado para las competiciones en curso. Las estadísticas reflejan un momento clave en la temporada que podría definir posiciones en las tablas de clasificación general.",
            'p3': "Las repercusiones de este evento deportivo se extienden a las estrategias de los equipos para próximos encuentros. Los entrenadores y jugadores preparan ajustes mientras la afición espera nuevos desafíos en la competición."
        },
        'tecnologia': {
            'p1': "El avance tecnológico reportado ha captado la atención de la industria digital y usuarios especializados. Las empresas del sector analizan las implicaciones de esta innovación para sus modelos de negocio actuales y futuros.",
            'p2': "Expertos en tecnología señalan que este desarrollo representa un paso significativo en la evolución digital. La adopción de estas nuevas herramientas podría transformar prácticas establecidas en diversos sectores productivos.",
            'p3': "Las proyecciones indican que esta tecnología se integrará progresivamente en el mercado global. Los reguladores evalúan marcos normativos para garantizar el uso responsable de estas capacidades tecnológicas."
        }
    }
    
    # Usar template de categoría o genérico
    if categoria in templates_categoria:
        temps = templates_categoria[categoria]
    else:
        temps = {
            'p1': "El acontecimiento ha sido confirmado por fuentes oficiales y genera atención mediática en el ámbito internacional. Las autoridades competentes emitieron comunicados sobre el tema mientras diversos sectores mantienen vigilancia sobre los desarrollos.",
            'p2': "Analistas especializados señalan la trascendencia de los hechos reportados en el contexto actual. La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación y sus posibles implicaciones.",
            'p3': "Las implicaciones de este acontecimiento podrían extenderse a diversos ámbitos de la sociedad en el mediano plazo. Expertos consultados destacan la necesidad de seguimiento constante mientras la situación continúa siendo objeto de análisis."
        }
    
    # Construir texto completo
    cierre = f"Se esperan actualizaciones oficiales conforme avancen las investigaciones correspondientes. (Agencias) / Fuente: {fuente}."
    
    # Asegurar que cada párrafo esté completo
    p1_completo = asegurar_oraciones_completas(temps['p1'])
    p2_completo = asegurar_oraciones_completas(temps['p2'])
    p3_completo = asegurar_oraciones_completas(temps['p3'])
    
    texto = f"{lead}\n\n{p1_completo}\n\n{p2_completo}\n\n{p3_completo}\n\n{cierre}"
    
    # Asegurar longitud mínima sin cortar
    while len(texto) < 1200:
        texto = texto.replace(cierre, f"Los detalles adicionales serán proporcionados oportunamente según avancen las investigaciones. {cierre}")
        if len(texto) >= 1200:
            break
    
    # Limitar a máximo 1950 pero sin cortar oración
    if len(texto) > 1950:
        texto_cortado = texto[:1947]
        # Buscar último punto completo
        ultimo_punto = texto_cortado.rfind('. ')
        if ultimo_punto > 1000:
            texto = texto_cortado[:ultimo_punto+1] + f"\n\n{cierre}"
        else:
            texto = texto[:1950]
    
    # Crear titular profesional sin URLs
    titular = eliminar_urls(str(titulo))[:95]
    if len(titular) < 15 or not es_espanol(titular):
        titular = f"Nuevo acontecimiento en {categoria} genera atención internacional"
    
    print(f"   ✅ Plantilla periodística: {len(texto)} caracteres")
    return {
        'titular': titular,
        'texto': texto
    }

def es_espanol(texto):
    """Detecta si el texto está en español"""
    if not texto:
        return False
    
    texto_lower = texto.lower()
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 
                   'su', 'para', 'los', 'las', 'del', 'al', 'lo', 'más', 'este', 'esta',
                   'pero', 'sus', 'una', 'como', 'son', 'entre', 'sobre', 'han', 'sido']
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    return count_es > count_en

def buscar_noticias_categorizadas():
    """Busca noticias priorizando las 10 categorías"""
    print("\n🔍 Buscando noticias por categorías...")
    noticias = []
    
    # 1. NewsAPI en español
    if NEWS_API_KEY:
        try:
            terminos_busqueda = [
                'presidente OR gobierno OR elecciones',
                'economía OR inflación OR crisis',
                'guerra OR conflicto OR ataque',
                'tecnología OR inteligencia artificial',
                'deportes OR fútbol OR campeonato'
            ]
            
            for termino in random.sample(terminos_busqueda, min(2, len(terminos_busqueda))):
                try:
                    resp = requests.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            'q': termino,
                            'language': 'es',
                            'sortBy': 'publishedAt',
                            'pageSize': 10,
                            'apiKey': NEWS_API_KEY
                        },
                        timeout=15
                    )
                    data = resp.json()
                    if data.get('status') == 'ok':
                        for art in data.get('articles', []):
                            cat = detectar_categoria(art.get('title', ''), art.get('description', ''))
                            art['categoria_detectada'] = cat
                            noticias.append(art)
                        print(f"   📡 NewsAPI '{termino[:20]}...': {len(data.get('articles', []))}")
                except:
                    continue
                    
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # 2. GNews español
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            resp = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'es', 'max': 20, 'apikey': GNEWS_API_KEY},
                timeout=15
            )
            data = resp.json()
            if 'articles' in data:
                for a in data['articles']:
                    cat = detectar_categoria(a.get('title', ''), a.get('description', ''))
                    noticias.append({
                        'title': a.get('title'),
                        'description': a.get('description'),
                        'url': a.get('url'),
                        'urlToImage': a.get('image'),
                        'source': {'name': a.get('source', {}).get('name', 'GNews')},
                        'categoria_detectada': cat
                    })
                print(f"   📡 GNews: {len(data['articles'])}")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # 3. RSS por categorías
    todas_feeds = []
    for cat, datos in CATEGORIAS.items():
        for feed in datos['feeds']:
            todas_feeds.append((cat, feed))
    
    feeds_seleccionados = random.sample(todas_feeds, min(4, len(todas_feeds)))
    
    for categoria_feed, feed_url in feeds_seleccionados:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                img = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    img = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png))"', entry.summary, re.I)
                    if m:
                        img = m.group(1)
                
                noticias.append({
                    'title': entry.get('title'),
                    'description': entry.get('summary', entry.get('description', ''))[:500],
                    'url': entry.get('link'),
                    'urlToImage': img,
                    'source': {'name': feed.feed.get('title', categoria_feed)},
                    'categoria_detectada': categoria_feed
                })
            print(f"   📡 RSS {categoria_feed}: {feed_url.split('/')[2]}")
        except:
            pass
    
    print(f"\n📊 Total: {len(noticias)} noticias")
    
    # Filtrar y priorizar
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title']:
            continue
        if ya_publicada(art['url'], art['title']):
            continue
        
        cat = art.get('categoria_detectada', 'general')
        art['prioridad'] = 2 if cat in ['politica', 'economia', 'mundo', 'deportes'] else 1
        
        nuevas.append(art)
        print(f"   ✅ [{cat}] {art['title'][:45]}...")
    
    nuevas.sort(key=lambda x: x.get('prioridad', 0), reverse=True)
    
    print(f"📊 Nuevas válidas: {len(nuevas)}")
    return nuevas[:3]

def descargar_imagen(url):
    if not url or not str(url).startswith('http'):
        return None
    try:
        print(f"   🖼️ Descargando imagen...")
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(path, 'JPEG', quality=85)
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar_completo(titulo, texto, img_path, categoria):
    """Publica en Facebook asegurando que no se corte el texto y sin URLs"""
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    # Eliminar cualquier URL residual
    titulo = eliminar_urls(titulo)
    texto = eliminar_urls(texto)
    
    # Hashtags según categoría
    hashtags_cat = {
        'politica': '#Política #Gobierno #Actualidad',
        'economia': '#Economía #Finanzas #Negocios',
        'mundo': '#Internacional #Mundo #Geopolítica',
        'seguridad': '#Seguridad #Justicia #Policiales',
        'tecnologia': '#Tecnología #Innovación #IA',
        'salud': '#Salud #Medicina #Bienestar',
        'medio_ambiente': '#MedioAmbiente #Clima #Sostenibilidad',
        'ciencia': '#Ciencia #Investigación #Descubrimiento',
        'deportes': '#Deportes #Fútbol #Competición',
        'tendencias': '#Viral #Tendencias #RedesSociales'
    }
    
    hashtags = hashtags_cat.get(categoria, '#Noticias #Actualidad #Hoy')
    
    # Asegurar que el texto no esté cortado al final
    texto_limpio = texto.strip()
    texto_limpio = asegurar_oraciones_completas(texto_limpio)
    
    # Verificar que no haya URLs ocultas
    texto_limpio = eliminar_urls(texto_limpio)
    titulo = eliminar_urls(titulo)
    
    mensaje = f"""📰 {titulo}

{texto_limpio}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Verificación final de longitud
    print(f"\n   📝 MENSAJE ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:8]:
        preview = linea[:65] + "..." if len(linea) > 65 else linea
        print(f"   {preview}")
    print(f"   {'='*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"   📤 Publicando...")
        
        with open(img_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = resp.json()
            
            if resp.status_code == 200 and 'id' in result:
                print(f"   ✅ PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Error: {error}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales de Facebook")
        return False
    
    noticias = buscar_noticias_categorizadas()
    
    if not noticias:
        print("⚠️ No hay noticias nuevas")
        return False
    
    print(f"\n🎯 Procesando {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen, saltando...")
            continue
        
        categoria = noticia.get('categoria_detectada', 'general')
        
        resultado = generar_redaccion_completa(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Agencias'),
            categoria
        )
        
        if publicar_completo(resultado['titular'], resultado['texto'], img_path, categoria):
            guardar_historial(noticia['url'], noticia['title'], categoria)
            if os.path.exists(img_path):
                os.remove(img_path)
            print(f"\n{'='*60}")
            print("✅ ÉXITO")
            print(f"{'='*60}")
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\n❌ No se pudo publicar")
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
