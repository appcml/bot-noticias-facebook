
# Código corregido del bot de noticias - SIN instrucciones internas y SIN links

codigo_corregido = '''
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

# CATEGORÍAS Y PALABRAS CLAVE
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
print("🚀 BOT DE NOTICIAS - Verdad Hoy (VERSIÓN LIMPIA)")
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
    
    titulo_simple = re.sub(r'[^\\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\\w]', '', t.lower())[:40]
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
    
    if max(puntuaciones.values()) > 0:
        return max(puntuaciones, key=puntuaciones.get)
    return 'general'

def limpiar_texto_final(texto):
    """Limpia el texto de instrucciones internas y corchetes"""
    if not texto:
        return texto
    
    # Eliminar líneas que contienen instrucciones entre corchetes
    lineas = texto.split('\\n')
    lineas_limpias = []
    
    for linea in lineas:
        linea = linea.strip()
        # Saltar líneas vacías o que son solo instrucciones
        if not linea:
            continue
        if re.match(r'^\\[.*?\\]$', linea):  # [Algo entre corchetes]
            continue
        if 'Párrafo' in linea and ':' in linea and len(linea) < 50:  # Instrucciones de párrafo
            continue
        if linea.startswith('[') and linea.endswith(']'):
            continue
        lineas_limpias.append(linea)
    
    texto_limpio = '\\n\\n'.join(lineas_limpias)
    
    # Eliminar corchetes sueltos que puedan quedar
    texto_limpio = re.sub(r'\\[.*?\\]', '', texto_limpio)
    
    # Limpiar espacios múltiples
    texto_limpio = re.sub(r'\\s+', ' ', texto_limpio)
    
    # Asegurar que no termine cortado
    texto_limpio = texto_limpio.strip()
    if texto_limpio.endswith(('en', 'de', 'la', 'el', 'un', 'una', 'a', 'con', 'por', 'para')):
        # Buscar último punto completo
        ultimo_punto = max(texto_limpio.rfind('.'), texto_limpio.rfind('!'), texto_limpio.rfind('?'))
        if ultimo_punto > len(texto_limpio) * 0.7:  # Si hay un punto después del 70% del texto
            texto_limpio = texto_limpio[:ultimo_punto+1]
    
    return texto_limpio.strip()

def generar_redaccion_completa(titulo, descripcion, fuente, categoria):
    """Genera redacción periodística COMPLETA usando IA gratuita."""
    print(f"\\n   📝 Procesando: {titulo[:50]}...")
    print(f"   🏷️ Categoría: {categoria}")
    
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion)).strip()
    if len(desc_limpia) < 20:
        desc_limpia = titulo
    
    if OPENROUTER_API_KEY:
        print("   🤖 Generando con IA...")
        resultado = generar_con_ia(titulo, desc_limpia, fuente, categoria)
        if resultado and len(resultado['texto']) > 500:
            return resultado
        print("   ⚠️ IA falló, usando plantilla...")
    
    return plantilla_mejorada(titulo, desc_limpia, fuente, categoria)

def generar_con_ia(titulo, descripcion, fuente, categoria):
    """Genera usando OpenRouter - SIN INSTRUCCIONES EN SALIDA"""
    try:
        prompt = f"""Eres un redactor senior de agencia EFE. Escribe una NOTICIA COMPLETA en español neutro.

DATOS:
Título: {titulo}
Descripción: {descripcion}
Fuente: {fuente}
Categoría: {categoria}

REGLAS IMPORTANTES:
1. Escribe en ESPAÑOL NATIVO
2. Estructura: Lead (2-3 oraciones) + 3 párrafos de desarrollo + Cierre corto
3. Longitud TOTAL: 1200-1600 caracteres
4. Usa datos específicos de la descripción si existen
5. Estilo periodístico objetivo

FORMATO DE SALIDA (solo texto, sin etiquetas ni corchetes):

Primero escribe un TITULAR corto y atractivo (máx 90 caracteres).

Luego escribe el LEAD: 2-3 oraciones con lo esencial (qué, quién, cuándo, dónde).

Después escribe 3 párrafos de desarrollo:
- Primer párrafo: contexto y antecedentes
- Segundo párrafo: detalles actuales y datos específicos  
- Tercer párrafo: análisis e implicaciones

Finalmente un cierre corto con la fuente.

IMPORTANTE: NO uses corchetes [ ] en el texto. NO escribas "Párrafo 1:" ni nada similar. Solo el texto de la noticia."""

        modelos = [
            "google/gemma-2-9b-it:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "openrouter/free"
        ]
        
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'HTTP-Referer': 'https://github.com',
            'X-Title': 'Bot Noticias',
            'Content-Type': 'application/json'
        }
        
        for modelo in modelos:
            try:
                print(f"   🔄 Probando {modelo.split('/')[-1]}...")
                
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers=headers,
                    json={
                        'model': modelo,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3,
                        'max_tokens': 1800
                    },
                    timeout=90
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        
                        # Extraer titular (primera línea no vacía)
                        lineas = [l.strip() for l in content.split('\\n') if l.strip()]
                        titular = lineas[0] if lineas else titulo[:90]
                        
                        # El resto es el cuerpo
                        cuerpo = '\\n\\n'.join(lineas[1:]) if len(lineas) > 1 else content
                        
                        # Limpiar instrucciones residuales
                        cuerpo = limpiar_texto_final(cuerpo)
                        titular = limpiar_texto_final(titular)
                        
                        # Si no hay fuente al final, agregarla
                        if fuente.lower() not in cuerpo.lower()[-200:]:
                            cuerpo += f"\\n\\nFuente: {fuente}."
                        
                        if len(cuerpo) > 400:
                            print(f"   ✅ Éxito: {len(cuerpo)} caracteres")
                            return {
                                'titular': titular[:95],
                                'texto': cuerpo[:1800]
                            }
                            
            except Exception as e:
                print(f"   ⚠️ Error {modelo}: {str(e)[:40]}")
                continue
                
    except Exception as e:
        print(f"   ⚠️ Error IA: {e}")
    
    return None

def plantilla_mejorada(titulo, descripcion, fuente, categoria):
    """Plantilla periodística limpia SIN instrucciones internas"""
    print(f"   📝 Usando plantilla...")
    
    # Crear lead natural
    oraciones = [s.strip() for s in descripcion.split('.') if len(s.strip()) > 15]
    
    if len(oraciones) >= 2:
        lead = f"{oraciones[0]}. {oraciones[1]}."
    elif len(oraciones) == 1:
        lead = f"{oraciones[0]}. Las autoridades confirmaron la información en las últimas horas."
    else:
        lead = f"Se reporta un importante acontecimiento. Las autoridades confirmaron la información."
    
    if len(lead) > 200:
        lead = lead[:197].rsplit(' ', 1)[0] + "."
    
    # Textos naturales por categoría (SIN corchetes ni instrucciones)
    desarrollos = {
        'politica': """El hecho ha generado amplia repercusión en los círculos de poder y entre la ciudadanía. Las autoridades gubernamentales emitieron comunicados oficiales sobre el tema mientras diversos actores políticos posicionan sus posturas ante la opinión pública.

Analistas políticos consultados señalan que este tipo de eventos requiere un seguimiento constante por parte de la sociedad. La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación.

Las implicaciones de este acontecimiento podrían extenderse a diversos sectores de la administración pública. Expertos destacan la necesidad de mantener una postura informada ante los desarrollos que se presenten en las próximas horas.""",
        
        'economia': """El indicador económico ha captado la atención de analistas financieros y del sector empresarial. Las entidades bancarias y reguladoras monitorean de cerca la evolución de los datos para determinar posibles ajustes en sus proyecciones.

Especialistas en economía señalan que este comportamiento del mercado requiere análisis detallado. La información disponible sugiere tendencias que podrían afectar a consumidores e inversionistas en el corto y mediano plazo.

Las proyecciones económicas indican posibles ajustes en las políticas monetarias y fiscales. Los sectores productivos mantienen expectativa sobre las medidas que podrían implementarse.""",
        
        'internacional': """El evento internacional ha generado reacciones en diversos países y organismos multilaterales. Las cancillerías involucradas mantienen comunicación constante para evaluar la situación y coordinar posibles respuestas diplomáticas.

Observadores internacionales destacan la trascendencia de los hechos reportados en el contexto geopolítico actual. La comunidad global sigue con atención los desarrollos mientras se analizan las posibles consecuencias regionales.

Las implicaciones de esta situación podrían afectar las relaciones bilaterales y multilaterales. Se esperan declaraciones oficiales adicionales de los actores involucrados.""",
        
        'guerra_defensa': """La situación ha escalado tensiones en la región afectada, movilizando fuerzas de defensa y generando alertas en organismos de seguridad. Los estados mayores evalúan constantemente la evolución del conflicto reportado.

Analistas militares señalan que esta operación podría marcar un punto de inflexión en la estrategia de defensa. La comunidad internacional observa con preocupación el desarrollo de los enfrentamientos y sus implicaciones para la seguridad regional.

Las autoridades de defensa mantienen comunicación constante con aliados estratégicos. Se esperan nuevos movimientos mientras persisten los esfuerzos diplomáticos para alcanzar un alto al fuego.""",
        
        'seguridad': """El hecho ha movilizado a las fuerzas del orden y generado preocupación en la comunidad afectada. Los equipos de investigación trabajan en la recopilación de evidencias y testimonios para esclarecer lo sucedido.

Fuentes policiales confirmaron que el operativo se desarrolló según los protocolos establecidos. La fiscalía evalúa la evidencia recolectada para determinar las responsabilidades penales correspondientes.

Las autoridades reforzaron la seguridad en la zona mientras continúan las investigaciones. Se esperan nuevas detenciones y avances judiciales conforme avance el proceso legal.""",
        
        'tecnologia': """El avance tecnológico reportado ha captado la atención de la industria digital y usuarios especializados. Las empresas del sector analizan las implicaciones de esta innovación para sus modelos de negocio actuales.

Expertos en tecnología señalan que este desarrollo representa un paso significativo en la evolución digital. La adopción de estas nuevas herramientas podría transformar prácticas establecidas en diversos sectores productivos.

Las proyecciones indican que esta tecnología se integrará progresivamente en el mercado. Los reguladores evalúan marcos normativos para garantizar el uso responsable de estas capacidades.""",
        
        'ciencia': """El hallazgo científico ha generado expectativa en la comunidad académica internacional. Los investigadores publicaron sus resultados en revistas especializadas tras meses de trabajo experimental riguroso.

Científicos independientes revisan la metodología empleada para validar los hallazgos presentados. La comunidad científica destaca la importancia de este descubrimiento para el avance del conocimiento en la disciplina.

Las instituciones educativas planean incorporar estos hallazgos en sus programas académicos. Se esperan nuevas investigaciones que profundicen en las implicaciones prácticas del descubrimiento.""",
        
        'salud': """La alerta sanitaria ha movilizado a las autoridades de salud y centros médicos especializados. Los equipos médicos trabajan en la atención de pacientes y la implementación de protocolos de prevención establecidos.

Especialistas en salud pública analizan la evolución de los casos reportados. Los hospitales mantienen preparados sus sistemas de respuesta ante posibles incrementos en la demanda asistencial.

Las autoridades sanitarias emitieron recomendaciones preventivas para la población. Se esperan nuevos informes epidemiológicos que determinen la efectividad de las medidas implementadas.""",
        
        'medio_ambiente': """El evento climático ha afectado significativamente la región reportada, movilizando servicios de emergencia. Los expertos ambientales evalúan el impacto en los ecosistemas locales y la biodiversidad regional.

Observatorios meteorológicos registraron datos históricos relacionados con este fenómeno. Las organizaciones ecologistas llaman a la acción ante la frecuencia creciente de eventos extremos vinculados al cambio climático.

Las autoridades ambientales coordinan esfuerzos de mitigación y adaptación. Se esperan nuevas políticas de sostenibilidad mientras la comunidad internacional refuerza compromisos de reducción de emisiones."""
    }
    
    desarrollo = desarrollos.get(categoria, """El acontecimiento ha sido confirmado por fuentes oficiales y genera atención mediática. Las autoridades competentes emitieron comunicados sobre el tema mientras diversos sectores mantienen vigilancia sobre los desarrollos.

Analistas señalan la trascendencia de los hechos reportados. La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación y sus posibles implicaciones.

Las consecuencias podrían extenderse a diversos ámbitos de la sociedad. Expertos consultados destacan la necesidad de seguimiento mientras la situación continúa siendo objeto de análisis detallado.""")
    
    cierre = f"Se esperan actualizaciones oficiales. Fuente: {fuente}."
    
    texto_final = f"{lead}\\n\\n{desarrollo}\\n\\n{cierre}"
    
    print(f"   ✅ Plantilla: {len(texto_final)} caracteres")
    return {
        'titular': titulo[:95],
        'texto': texto_final[:1800]
    }

def buscar_noticias_categorizadas():
    """Busca noticias sin incluir links en el contenido"""
    print("\\n🔍 Buscando noticias...")
    noticias = []
    
    if NEWS_API_KEY:
        try:
            terminos = [
                'presidente gobierno elecciones',
                'economía inflación crisis',
                'guerra conflicto militar',
                'inteligencia artificial tecnología'
            ]
            
            for termino in random.sample(terminos, min(2, len(terminos))):
                try:
                    resp = requests.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            'q': termino,
                            'language': 'es',
                            'sortBy': 'publishedAt',
                            'pageSize': 8,
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
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            resp = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'es', 'max': 15, 'apikey': GNEWS_API_KEY},
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
                        'source': {'name': a.get('source', {}).get('name', 'Agencias')},
                        'categoria_detectada': cat
                    })
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # RSS
    todas_feeds = []
    for cat, datos in CATEGORIAS.items():
        for feed in datos['feeds']:
            todas_feeds.append((cat, feed))
    
    feeds_sel = random.sample(todas_feeds, min(3, len(todas_feeds)))
    
    for cat_feed, feed_url in feeds_sel:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                img = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    img = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    m = re.search(r'src="(https?://[^"]+\\.(?:jpg|jpeg|png))"', entry.summary, re.I)
                    if m:
                        img = m.group(1)
                
                noticias.append({
                    'title': entry.get('title'),
                    'description': entry.get('summary', entry.get('description', ''))[:400],
                    'url': entry.get('link'),
                    'urlToImage': img,
                    'source': {'name': feed.feed.get('title', cat_feed)},
                    'categoria_detectada': cat_feed
                })
        except:
            pass
    
    # Filtrar
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title']:
            continue
        if ya_publicada(art['url'], art['title']):
            continue
        
        cat = art.get('categoria_detectada', 'general')
        art['prioridad'] = 3 if cat in ['politica', 'economia', 'internacional'] else 2
        nuevas.append(art)
    
    nuevas.sort(key=lambda x: x.get('prioridad', 0), reverse=True)
    return nuevas[:3]

def descargar_imagen(url):
    if not url or not str(url).startswith('http'):
        return None
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(path, 'JPEG', quality=85)
            return path
    except:
        pass
    return None

def publicar_completo(titulo, texto, img_path, categoria):
    """Publica en Facebook SIN links y SIN instrucciones"""
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    hashtags = {
        'politica': '#Política #Gobierno #Actualidad',
        'economia': '#Economía #Finanzas #Negocios',
        'internacional': '#Internacional #Mundo',
        'guerra_defensa': '#Defensa #Seguridad',
        'seguridad': '#Seguridad #Justicia',
        'tecnologia': '#Tecnología #Innovación',
        'ciencia': '#Ciencia #Investigación',
        'salud': '#Salud #Medicina',
        'medio_ambiente': '#MedioAmbiente #Clima',
        'general': '#Noticias #Actualidad'
    }
    
    hashtag = hashtags.get(categoria, '#Noticias')
    
    # Limpiar cualquier URL residual del texto
    texto_limpio = re.sub(r'https?://\\S+', '', texto)
    texto_limpio = limpiar_texto_final(texto_limpio)
    
    mensaje = f"""📰 {titulo}

{texto_limpio}

{hashtag}

— Verdad Hoy"""
    
    # Verificar longitud
    if len(mensaje) > 2000:
        disponible = 2000 - len(titulo) - len(hashtag) - 30
        texto_limpio = texto_limpio[:disponible].rsplit(' ', 1)[0] + "."
        mensaje = f"""📰 {titulo}

{texto_limpio}

{hashtag}

— Verdad Hoy"""
    
    print(f"\\n   📝 MENSAJE ({len(mensaje)} chars):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\\n')[:6]:
        print(f"   {linea[:60]}{'...' if len(linea) > 60 else ''}")
    print(f"   {'='*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
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
    
    print(f"\\n🎯 Procesando {len(noticias)} noticia(s)...")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
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
            print(f"\\n{'='*60}")
            print("✅ ÉXITO")
            print(f"{'='*60}")
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\\n❌ No se pudo publicar")
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
'''

print("Código corregido generado exitosamente")
print(f"Longitud: {len(codigo_corregido)} caracteres")
