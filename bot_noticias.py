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

# CATEGORÍAS Y PALABRAS CLAVE PRIORITARIAS (ACTUALIZADO)
CATEGORIAS = {
    'politica': {
        'keywords': [
            'presidente', 'gobierno', 'ministro', 'ministerio', 'congreso', 'senado', 
            'diputados', 'parlamento', 'elecciones', 'votación', 'candidato', 
            'partido político', 'oposición', 'reforma', 'ley', 'decreto', 'constitución',
            'gabinete', 'crisis política', 'escándalo político', 'corrupción', 
            'destitución', 'renuncia', 'debate político', 'coalición', 'alianza política',
            'protesta política', 'manifestación', 'reforma constitucional', 'referéndum',
            'plebiscito', 'agenda política', 'liderazgo político', 'relaciones diplomáticas',
            'cumbre política', 'política exterior', 'política interna'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada',
            'https://www.abc.es/rss/feeds/abc_Espana.xml',
        ]
    },
    'economia': {
        'keywords': [
            'economía', 'inflación', 'recesión', 'crecimiento económico', 'crisis económica',
            'mercado', 'mercado financiero', 'bolsa', 'acciones', 'inversión', 'inversionistas',
            'empresa', 'negocio', 'industria', 'emprendimiento', 'startup', 'exportaciones',
            'importaciones', 'comercio', 'comercio internacional', 'banco', 'banca', 'finanzas',
            'impuestos', 'reforma tributaria', 'salario', 'empleo', 'desempleo', 'precio',
            'costo de vida', 'dólar', 'tipo de cambio', 'moneda', 'presupuesto', 'gasto público',
            'deuda pública', 'subsidio', 'inversión extranjera'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml',
        ]
    },
    'internacional': {
        'keywords': [
            'conflicto internacional', 'crisis internacional', 'tensión internacional',
            'relaciones exteriores', 'diplomacia', 'sanciones internacionales', 'tratado',
            'acuerdo internacional', 'cumbre internacional', 'organismos internacionales',
            'migración', 'refugiados', 'crisis humanitaria', 'frontera', 'geopolítica',
            'alianza internacional', 'negociaciones', 'tensión diplomática', 'relaciones bilaterales'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/internacional.xml',
        ]
    },
    'guerra_defensa': {
        'keywords': [
            'guerra', 'conflicto armado', 'ataque', 'bombardeo', 'misil', 'defensa',
            'ejército', 'fuerzas armadas', 'militar', 'operación militar', 'batalla',
            'tensión militar', 'seguridad internacional', 'armamento', 'estrategia militar',
            'invasión', 'frente de batalla', 'alto al fuego', 'acuerdo de paz'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
            'https://www.20minutos.es/rss/internacional/',
        ]
    },
    'seguridad': {
        'keywords': [
            'crimen', 'delito', 'robo', 'asalto', 'homicidio', 'asesinato', 'detenido',
            'captura', 'investigación policial', 'operativo policial', 'allanamiento',
            'narcotráfico', 'tráfico de drogas', 'banda criminal', 'mafias', 'justicia',
            'tribunal', 'juicio', 'sentencia', 'condena', 'acusado', 'fiscalía',
            'carabineros', 'policía', 'seguridad ciudadana'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/sociedad/portada',
            'https://www.20minutos.es/rss/nacional/',
        ]
    },
    'tecnologia': {
        'keywords': [
            'tecnología', 'innovación', 'inteligencia artificial', 'IA', 'robótica',
            'automatización', 'software', 'hardware', 'internet', 'plataforma digital',
            'redes sociales', 'ciberseguridad', 'hackeo', 'datos', 'big data',
            'startup tecnológica', 'empresa tecnológica', 'aplicación móvil', 'app',
            'smartphone', 'computadora', 'dispositivo', 'realidad virtual', 'realidad aumentada',
            'blockchain', 'criptografía', 'tecnología emergente'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada',
            'https://www.xataka.com/feedburner.xml',
        ]
    },
    'ciencia': {
        'keywords': [
            'descubrimiento', 'científicos', 'investigación', 'estudio científico', 'experimento',
            'universidad', 'laboratorio', 'biología', 'genética', 'física', 'química',
            'astronomía', 'cosmos', 'universo', 'planeta', 'misión espacial', 'telescopio',
            'satélite', 'espacio', 'observatorio'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada',
        ]
    },
    'salud': {
        'keywords': [
            'salud', 'medicina', 'hospital', 'clínica', 'pacientes', 'enfermedad', 'virus',
            'bacteria', 'epidemia', 'pandemia', 'vacuna', 'tratamiento', 'terapia', 'diagnóstico',
            'investigación médica', 'salud pública', 'nutrición', 'alimentación saludable',
            'salud mental', 'bienestar', 'sistema de salud'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada',
        ]
    },
    'medio_ambiente': {
        'keywords': [
            'medio ambiente', 'cambio climático', 'crisis climática', 'temperatura global',
            'calentamiento global', 'sequía', 'inundación', 'incendio forestal', 'tormenta',
            'huracán', 'fenómeno climático', 'contaminación', 'polución', 'ecosistema',
            'biodiversidad', 'conservación', 'energía renovable', 'energía solar',
            'energía eólica', 'sostenibilidad'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/clima-medio-ambiente/portada',
        ]
    },
    'general': {
        'keywords': [
            'actualidad', 'noticias', 'última hora', 'urgente', 'confirmado', 'revelan',
            'histórico', 'importante', 'relevante', 'destacado'
        ],
        'feeds': [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml',
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

def generar_redaccion_completa(titulo, descripcion, fuente, categoria):
    """
    Genera redacción periodística COMPLETA sin cortes.
    Estructura: Titular + Lead (2-3 oraciones) + Cuerpo (3 párrafos) + Cierre
    """
    
    print(f"\n   📝 Procesando: {titulo[:50]}...")
    print(f"   🏷️ Categoría: {categoria}")
    
    # Limpiar descripción base
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion)).strip()
    if len(desc_limpia) < 20:
        desc_limpia = titulo
    
    # Si tenemos IA, usarla
    if OPENROUTER_API_KEY:
        resultado = generar_con_ia(titulo, desc_limpia, fuente, categoria)
        if resultado and len(resultado['texto']) > 800:
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
1. TITULAR: Máximo 90 caracteres, informativo, atractivo, estilo EFE
2. LEAD: 2-3 oraciones completas (máximo 200 caracteres), incluye: qué pasó, quién, cuándo, dónde
3. CUERPO: Exactamente 3 párrafos completos:
   - Párrafo 1: Contexto y antecedentes (quiénes están involucrados)
   - Párrafo 2: Desarrollo actual (datos, cifras, declaraciones específicas)
   - Párrafo 3: Análisis e implicaciones (qué significa, consecuencias futuras)
4. CIERRE: 1 línea con próximos pasos + "(Agencias) / Fuente: {fuente}"

REGLAS:
- ESPAÑOL NATIVO, no traducciones
- Oraciones COMPLETAS, no cortar palabras
- Longitud total: 1200-1800 caracteres
- Estilo periodístico NEUTRO
- Números y datos específicos si están en la descripción

FORMATO OBLIGATORIO:
TITULAR: [titular completo]

LEAD: [lead completo de 2-3 oraciones]

CUERPO:
[Párrafo 1 completo - contexto]

[Párrafo 2 completo - desarrollo]

[Párrafo 3 completo - análisis]

CIERRE: [cierre con fuente]

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
                        'max_tokens': 1500
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
                        
                        if not cierre:
                            cierre = f"Se esperan actualizaciones. (Agencias) / Fuente: {fuente}."
                        
                        # Construir texto completo
                        texto_completo = f"{lead}\n\n{cuerpo}\n\n{cierre}"
                        
                        # Verificar que no esté cortado
                        if len(texto_completo) > 600 and not texto_completo.endswith(('en ', 'de ', 'la ', 'el ', 'un ', 'una ')):
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

def extraer_campo(texto, inicio, fin):
    """Extrae campo entre dos marcadores"""
    try:
        if inicio in texto:
            parte = texto.split(inicio)[1]
            if fin in parte:
                return parte.split(fin)[0].strip()
            return parte.strip()[:500]
    except:
        pass
    return ""

def plantilla_mejorada(titulo, descripcion, fuente, categoria):
    """Plantilla periodística robusta sin cortes"""
    print(f"   📝 Usando plantilla mejorada...")
    
    # Crear lead completo (2-3 oraciones)
    oraciones_desc = [s.strip() for s in descripcion.split('.') if len(s.strip()) > 20]
    
    if len(oraciones_desc) >= 2:
        lead = f"{oraciones_desc[0]}. {oraciones_desc[1]}."
    elif len(oraciones_desc) == 1:
        lead = f"{oraciones_desc[0]}. Las autoridades competentes confirmaron la información en las últimas horas."
    else:
        lead = f"Se reporta un importante acontecimiento relacionado con {categoria}. Las autoridades competentes confirmaron la información en las últimas horas y se esperan actualizaciones."
    
    # Limitar lead a 200 caracteres pero sin cortar palabras
    if len(lead) > 200:
        lead = lead[:197].rsplit(' ', 1)[0] + "."
    
    # Párrafos completos según categoría (ACTUALIZADO CON NUEVAS CATEGORÍAS)
    templates_categoria = {
        'politica': {
            'p1': "El hecho político ha generado amplia repercusión en los círculos de poder y entre la ciudadanía. Las autoridades gubernamentales emitieron comunicados oficiales sobre el tema mientras diversos actores políticos posicionan sus posturas ante la opinión pública.",
            'p2': "Analistas políticos consultados señalan que este tipo de eventos requiere un seguimiento constante por parte de la sociedad. La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación y sus posibles implicaciones.",
            'p3': "Las implicaciones de este acontecimiento político podrían extenderse a diversos sectores de la administración pública. Expertos destacan la necesidad de mantener una postura informada ante los desarrollos que se presenten en las próximas horas."
        },
        'economia': {
            'p1': "El indicador económico ha captado la atención de analistas financieros y del sector empresarial. Las entidades bancarias y reguladoras monitorean de cerca la evolución de los datos para determinar posibles ajustes en sus proyecciones.",
            'p2': "Especialistas en economía señalan que este comportamiento del mercado requiere análisis detallado. La información disponible sugiere tendencias que podrían afectar a consumidores e inversionistas en el corto y mediano plazo.",
            'p3': "Las proyecciones económicas indican posibles ajustes en las políticas monetarias y fiscales. Los sectores productivos mantienen expectativa sobre las medidas que podrían implementarse para estabilizar los indicadores."
        },
        'internacional': {
            'p1': "El evento internacional ha generado reacciones en diversos países y organismos multilaterales. Las cancillerías involucradas mantienen comunicación constante para evaluar la situación y coordinar posibles respuestas diplomáticas.",
            'p2': "Observadores internacionales destacan la trascendencia de los hechos reportados en el contexto geopolítico actual. La comunidad global sigue con atención los desarrollos mientras se analizan las posibles consecuencias regionales.",
            'p3': "Las implicaciones de esta situación internacional podrían afectar las relaciones bilaterales y multilaterales. Se esperan declaraciones oficiales adicionales de los actores involucrados en las próximas horas."
        },
        'guerra_defensa': {
            'p1': "La situación militar ha escalado tensiones en la región afectada, movilizando fuerzas de defensa y generando alertas en organismos de seguridad. Los estados mayores evalúan constantemente la evolución del conflicto armado reportado.",
            'p2': "Analistas militares señalan que esta operación podría marcar un punto de inflexión en la estrategia de defensa. La comunidad internacional observa con preocupación el desarrollo de los enfrentamientos y sus implicaciones para la seguridad regional.",
            'p3': "Las autoridades de defensa mantienen comunicación constante con aliados estratégicos. Se esperan nuevos movimientos militares mientras persisten los esfuerzos diplomáticos para alcanzar un alto al fuego sostenible."
        },
        'seguridad': {
            'p1': "El hecho delictivo ha movilizado a las fuerzas del orden y generado preocupación en la comunidad afectada. Los equipos de investigación trabajan en la recopilación de evidencias y testimonios para esclarecer los hechos.",
            'p2': "Fuentes policiales confirmaron que el operativo se desarrolló según los protocolos establecidos. La fiscalía evalúa la evidencia recolectada para determinar las responsabilidades penales correspondientes.",
            'p3': "Las autoridades reforzaron la seguridad en la zona mientras continúan las investigaciones. Se esperan nuevas detenciones y avances judiciales conforme avance el proceso legal iniciado."
        },
        'tecnologia': {
            'p1': "El avance tecnológico reportado ha captado la atención de la industria digital y usuarios especializados. Las empresas del sector analizan las implicaciones de esta innovación para sus modelos de negocio.",
            'p2': "Expertos en tecnología señalan que este desarrollo representa un paso significativo en la evolución digital. La adopción de estas nuevas herramientas podría transformar prácticas establecidas en diversos sectores productivos.",
            'p3': "Las proyecciones indican que esta tecnología se integrará progresivamente en el mercado. Los reguladores evalúan marcos normativos para garantizar el uso responsable de estas capacidades."
        },
        'ciencia': {
            'p1': "El hallazgo científico ha generado expectativa en la comunidad académica internacional. Los investigadores del laboratorio publicaron sus resultados en revistas especializadas tras meses de trabajo experimental.",
            'p2': "Científicos independientes revisan la metodología empleada para validar los hallazgos presentados. La comunidad científica destaca la importancia de este descubrimiento para el avance del conocimiento en la disciplina.",
            'p3': "Las instituciones educativas planean incorporar estos hallazgos en sus programas académicos. Se esperan nuevas investigaciones que profundicen en las implicaciones prácticas de este descubrimiento."
        },
        'salud': {
            'p1': "La alerta sanitaria ha movilizado a las autoridades de salud y centros médicos especializados. Los equipos médicos trabajan en la atención de pacientes y la implementación de protocolos de prevención establecidos.",
            'p2': "Especialistas en salud pública analizan la evolución de los casos reportados. Los hospitales mantienen preparados sus sistemas de respuesta ante posibles incrementos en la demanda asistencial.",
            'p3': "Las autoridades sanitarias emitieron recomendaciones preventivas para la población. Se esperan nuevos informes epidemiológicos que determinen la efectividad de las medidas implementadas."
        },
        'medio_ambiente': {
            'p1': "El evento climático ha afectado significativamente la región reportada, movilizando servicios de emergencia. Los expertos ambientales evalúan el impacto en los ecosistemas locales y la biodiversidad.",
            'p2': "Observatorios meteorológicos registraron datos históricos relacionados con este fenómeno. Las organizaciones ecologistas llaman a la acción ante la frecuencia creciente de eventos extremos vinculados al cambio climático.",
            'p3': "Las autoridades ambientales coordinan esfuerzos de mitigación y adaptación. Se esperan nuevas políticas de sostenibilidad mientras la comunidad internacional refuerza compromisos de reducción de emisiones."
        }
    }
    
    # Usar template de categoría o genérico
    if categoria in templates_categoria:
        temps = templates_categoria[categoria]
    else:
        temps = {
            'p1': "El acontecimiento ha sido confirmado por fuentes oficiales y genera atención mediática. Las autoridades competentes emitieron comunicados sobre el tema mientras diversos sectores mantienen vigilancia sobre los desarrollos.",
            'p2': "Analistas señalan la trascendencia de los hechos reportados. La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación y sus posibles implicaciones.",
            'p3': "Las implicaciones podrían extenderse a diversos ámbitos de la sociedad. Expertos consultados destacan la necesidad de seguimiento mientras la situación continúa siendo objeto de análisis."
        }
    
    # Construir texto completo
    cierre = f"Se esperan actualizaciones oficiales. (Agencias) / Fuente: {fuente}."
    
    texto = f"{lead}\n\n{temps['p1']}\n\n{temps['p2']}\n\n{temps['p3']}\n\n{cierre}"
    
    # Asegurar longitud mínima sin cortar
    while len(texto) < 1000:
        texto = texto.replace(cierre, f"Los detalles adicionales serán proporcionados oportunamente. {cierre}")
    
    print(f"   ✅ Plantilla: {len(texto)} caracteres")
    return {
        'titular': titulo[:95],
        'texto': texto[:1950]
    }

def buscar_noticias_categorizadas():
    """Busca noticias priorizando las 10 categorías"""
    print("\n🔍 Buscando noticias por categorías...")
    noticias = []
    
    # 1. NewsAPI en español con palabras clave de categorías
    if NEWS_API_KEY:
        try:
            # Buscar con términos de alta relevancia (ACTUALIZADO)
            terminos_busqueda = [
                'presidente OR gobierno OR elecciones OR congreso',
                'economía OR inflación OR crisis OR mercado financiero',
                'guerra OR conflicto armado OR ataque OR defensa',
                'inteligencia artificial OR tecnología OR ciberseguridad',
                'crimen OR narcotráfico OR justicia OR tribunal',
                'cambio climático OR medio ambiente OR sostenibilidad',
                'pandemia OR vacuna OR salud pública',
                'descubrimiento científico OR espacio OR investigación'
            ]
            
            for termino in random.sample(terminos_busqueda, min(3, len(terminos_busqueda))):
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
    
    # 3. RSS por categorías (rotativas)
    todas_feeds = []
    for cat, datos in CATEGORIAS.items():
        for feed in datos['feeds']:
            todas_feeds.append((cat, feed))
    
    # Seleccionar 4 feeds aleatorios de diferentes categorías
    feeds_seleccionados = random.sample(todas_feeds, min(4, len(todas_feeds)))
    
    for categoria_feed, feed_url in feeds_seleccionados:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                # Buscar imagen
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
        
        # Priorizar ciertas categorías (ACTUALIZADO)
        cat = art.get('categoria_detectada', 'general')
        art['prioridad'] = 3 if cat in ['politica', 'economia', 'internacional', 'guerra_defensa'] else 2 if cat in ['seguridad', 'tecnologia'] else 1
        
        nuevas.append(art)
        print(f"   ✅ [{cat}] {art['title'][:45]}...")
    
    # Ordenar por prioridad
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
    """Publica en Facebook asegurando que no se corte el texto"""
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    # Hashtags según categoría (ACTUALIZADO)
    hashtags_cat = {
        'politica': '#Política #Gobierno #Congreso #ActualidadPolítica',
        'economia': '#Economía #Finanzas #Negocios #Mercados',
        'internacional': '#Internacional #Mundo #Diplomacia #Geopolítica',
        'guerra_defensa': '#Defensa #SeguridadNacional #Militar #Conflicto',
        'seguridad': '#Seguridad #Justicia #Policiales #OrdenPúblico',
        'tecnologia': '#Tecnología #Innovación #IA #Digital',
        'ciencia': '#Ciencia #Investigación #Descubrimiento #Saberes',
        'salud': '#Salud #Medicina #Bienestar #Sanidad',
        'medio_ambiente': '#MedioAmbiente #Clima #Sostenibilidad #Naturaleza',
        'general': '#Noticias #Actualidad #Hoy #Información'
    }
    
    hashtags = hashtags_cat.get(categoria, '#Noticias #Actualidad')
    
    # Asegurar que el texto no esté cortado al final
    texto_limpio = texto.strip()
    if texto_limpio.endswith(('en', 'de', 'la', 'el', 'un', 'una', 'a', 'con', 'por')):
        texto_limpio += "."
    
    mensaje = f"""📰 {titulo}

{texto_limpio}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Verificación final de longitud
    print(f"\n   📝 MENSAJE ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:6]:
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
