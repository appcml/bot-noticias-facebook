import requests
import random
import re
import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse, quote
import base64
import json

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Para generación de imágenes
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')  # Alternativa para imágenes

print(f"DEBUG: NEWS_API_KEY presente: {bool(NEWS_API_KEY)}")
print(f"DEBUG: FB_PAGE_ID presente: {bool(FB_PAGE_ID)}")
print(f"DEBUG: FB_ACCESS_TOKEN presente: {bool(FB_ACCESS_TOKEN)}")
print(f"DEBUG: OPENAI_API_KEY presente: {bool(OPENAI_API_KEY)}")

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    print("ERROR: Variables faltantes")
    raise ValueError("Faltan variables de entorno")

print("DEBUG: Todas las variables OK")

FUENTES_PREMIUM = {
    'internacional': ['bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'aljazeera.com', 'elpais.com', 'clarin.com'],
    'economia': ['bloomberg.com', 'forbes.com', 'eleconomista.es', 'expansion.com', 'ambito.com'],
    'tecnologia': ['techcrunch.com', 'theverge.com', 'wired.com', 'xataka.com', 'fayerwayer.com'],
    'politica': ['politico.com', 'axios.com', 'infobae.com', 'animalpolitico.com', 'reforma.com']
}

HISTORIAL_URLS = set()
MAX_HISTORIAL = 100

def generar_imagen_ia(titulo, descripcion, categoria):
    """
    Genera una imagen usando IA basada en el contexto de la noticia.
    Soporta OpenAI DALL-E o Stability AI como fallback.
    """
    # Crear prompt optimizado para la imagen
    prompt = crear_prompt_imagen(titulo, descripcion, categoria)
    print(f"[IMAGEN] Generando imagen con prompt: {prompt[:100]}...")
    
    try:
        # Intentar con OpenAI DALL-E primero
        if OPENAI_API_KEY:
            return generar_imagen_openai(prompt)
        # Fallback a Stability AI
        elif STABILITY_API_KEY:
            return generar_imagen_stability(prompt)
        else:
            print("[IMAGEN] No hay API keys configuradas para generación de imágenes")
            return None
    except Exception as e:
        print(f"[ERROR] Generando imagen: {e}")
        return None

def crear_prompt_imagen(titulo, descripcion, categoria):
    """Crea un prompt optimizado para generación de imágenes."""
    # Extraer palabras clave
    texto = f"{titulo} {descripcion}".lower()
    
    # Estilos según categoría
    estilos = {
        'crisis': "fotoperiodismo dramático, iluminación cinematográfica, tonos oscuros, composición seria",
        'economia': "infografía moderna, gráficos elegantes, paleta azul y plateada, estilo corporativo profesional",
        'tech': "futurista, neon, alta tecnología, diseño limpio, iluminación azul y morada, render 3D",
        'politica': "fotoperiodismo, edificios gubernamentales, banderas, estilo documental, iluminación natural",
        'emergencia': "fotoperiodismo de acción, luces de emergencia, composición dinámica, tonos rojos y naranjas",
        'general': "fotoperiodismo profesional, iluminación natural, composición equilibrada, estilo Reuters/AP"
    }
    
    estilo = estilos.get(categoria, estilos['general'])
    
    # Limpiar y optimizar el prompt
    prompt_limpio = f"{titulo}. {descripcion[:200]}"
    prompt_final = f"Noticia: {prompt_limpio}. Estilo: {estilo}. Alta calidad, 4K, profesional, sin texto, sin logos, sin marcas de agua."
    
    return prompt_final[:1000]  # Limitar longitud

def generar_imagen_openai(prompt):
    """Genera imagen usando OpenAI DALL-E 3."""
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "standard",
        "n": 1
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=60)
    result = response.json()
    
    if response.status_code == 200 and 'data' in result:
        image_url = result['data'][0]['url']
        # Descargar la imagen temporalmente
        return descargar_imagen_temp(image_url)
    else:
        print(f"[ERROR] OpenAI: {result.get('error', {}).get('message', 'Error desconocido')}")
        return None

def generar_imagen_stability(prompt):
    """Genera imagen usando Stability AI como alternativa."""
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }
    files = {
        "prompt": (None, prompt),
        "output_format": (None, "png")
    }
    
    response = requests.post(url, headers=headers, files=files, timeout=60)
    
    if response.status_code == 200:
        # Guardar imagen temporalmente
        temp_path = f"/tmp/stability_{hashlib.md5(prompt.encode()).hexdigest()[:8]}.png"
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        return temp_path
    else:
        print(f"[ERROR] Stability AI: {response.status_code}")
        return None

def descargar_imagen_temp(image_url):
    """Descarga imagen desde URL y guarda temporalmente."""
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            temp_path = f"/tmp/openai_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.png"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            return temp_path
    except Exception as e:
        print(f"[ERROR] Descargando imagen: {e}")
    return None

def obtener_imagen_noticia(articulo):
    """
    Obtiene imagen de la noticia: 
    1. Primero intenta usar la imagen original de la noticia
    2. Si no hay o es de baja calidad, genera una con IA
    """
    url_imagen = articulo.get('urlToImage')
    titulo = articulo.get('title', '')
    descripcion = articulo.get('description', '')
    categoria = articulo.get('categoria', 'general')
    
    # Verificar si la imagen original es válida
    if url_imagen and verificar_imagen_valida(url_imagen):
        print(f"[IMAGEN] Usando imagen original: {url_imagen[:60]}...")
        return url_imagen
    
    # Generar imagen con IA
    print("[IMAGEN] Generando imagen con IA...")
    imagen_local = generar_imagen_ia(titulo, descripcion, categoria)
    
    if imagen_local:
        # Subir imagen a Facebook para obtener URL pública
        return subir_imagen_a_facebook(imagen_local)
    
    return None

def verificar_imagen_valida(url):
    """Verifica si la URL de imagen es accesible y válida."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            return 'image' in content_type
    except:
        pass
    return False

def subir_imagen_a_facebook(image_path):
    """Sube imagen temporal a Facebook y retorna URL pública."""
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        
        with open(image_path, 'rb') as img:
            files = {'file': img}
            data = {
                'access_token': FB_ACCESS_TOKEN,
                'published': 'false'  # No publicar, solo subir
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                # Obtener URL de la imagen subida
                photo_id = result['id']
                url_photo = f"https://graph.facebook.com/v19.0/{photo_id}?access_token={FB_ACCESS_TOKEN}&fields=images"
                response_photo = requests.get(url_photo, timeout=10)
                data_photo = response_photo.json()
                
                if 'images' in data_photo and len(data_photo['images']) > 0:
                    return data_photo['images'][0]['source']
    except Exception as e:
        print(f"[ERROR] Subiendo imagen a Facebook: {e}")
    return None

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    fecha_ayer = (datetime.now().timestamp() - 86400)
    
    busquedas_todas = [
        ('noticias', 'general'),
        ('actualidad', 'general'),
        ('mundo', 'general'),
        ('internacional', 'general'),
        ('politica', 'politica')
    ]
    
    busquedas_hoy = random.sample(busquedas_todas, min(5, len(busquedas_todas)))
    todas_noticias = []
    
    for query, categoria in busquedas_hoy:
        url = f"https://newsapi.org/v2/everything?q={quote(query)}&language=es&from={datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')}&to={fecha_hoy}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        
        try:
            print(f"[BÚSQUEDA] {categoria}: {query[:40]}...")
            response = requests.get(url, timeout=15)
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                for art in data['articles']:
                    if es_noticia_valida(art):
                        score = calcular_score(art, categoria)
                        art['categoria'] = categoria
                        art['score'] = score
                        art['url_hash'] = hashlib.md5(art['url'].encode()).hexdigest()[:16]
                        todas_noticias.append(art)
                        print(f"  Encontrada: {art['title'][:50]}... (score: {score})")
        except Exception as e:
            print(f"[ERROR] en búsqueda {categoria}: {e}")
    
    print(f"\n[INFO] Total noticias encontradas: {len(todas_noticias)}")
    
    noticias_unicas = {}
    for art in todas_noticias:
        if art['url_hash'] not in noticias_unicas:
            noticias_unicas[art['url_hash']] = art
    
    noticias_lista = list(noticias_unicas.values())
    print(f"[INFO] Noticias únicas: {len(noticias_lista)}")
    
    noticias_nuevas = [n for n in noticias_lista if n['url'] not in HISTORIAL_URLS]
    print(f"[INFO] Noticias no publicadas antes: {len(noticias_nuevas)}")
    
    noticias_nuevas.sort(key=lambda x: x['score'], reverse=True)
    return noticias_nuevas[:5]

def es_noticia_valida(art):
    if not art.get('title'):
        return False
    if "[Removed]" in art.get('title', ''):
        return False
    if len(art.get('title', '')) < 20:
        return False
    if not art.get('description'):
        return False
    if len(art.get('description', '')) < 80:
        return False
    url = art.get('url', '')
    if not url or not url.startswith('http'):
        return False
    dominios_malos = ['news.google.com', 'google.com/news', 'facebook.com', 'twitter.com']
    if any(mal in url.lower() for mal in dominios_malos):
        return False
    return True

def calcular_score(art, categoria):
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    impacto_muy_alto = {
        'guerra': 30, 'ataque': 30, 'muertos': 30, 'heridos': 25,
        'trump': 25, 'biden': 25, 'elecciones': 20,
        'crisis': 20, 'urgente': 20, 'alerta': 20, 'breaking': 20,
        'invasion': 25, 'misil': 25, 'bomba': 25,
        'economia': 15, 'inflacion': 20, 'dolar': 15,
        'ia': 15, 'inteligencia artificial': 20, 'chatgpt': 15
    }
    
    for palabra, puntos in impacto_muy_alto.items():
        if palabra in texto:
            score += puntos
    
    fuente = urlparse(art.get('url', '')).netloc.lower()
    for cat, fuentes in FUENTES_PREMIUM.items():
        if any(f in fuente for f in fuentes):
            score += 20
            break
    
    try:
        fecha_pub = art.get('publishedAt', '')
        if fecha_pub:
            fecha_art = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00'))
            horas_diferencia = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            if horas_diferencia < 1:
                score += 30
            elif horas_diferencia < 6:
                score += 20
            elif horas_diferencia < 24:
                score += 10
    except:
        pass
    
    if categoria in ['crisis', 'emergencia']:
        score += 15
    
    # Bonus si tiene imagen
    if art.get('urlToImage'):
        score += 5
    
    return score

def detectar_tono(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    graves = ['muerte', 'muertos', 'ataque', 'guerra', 'tragedia', 'desastre', 'crisis', 'urgente']
    positivas = ['avance', 'descubrimiento', 'innovacion', 'acuerdo', 'paz', 'logro', 'éxito']
    neutrales = ['estudio', 'análisis', 'reporte', 'datos', 'encuesta', 'investigación']
    
    if any(p in texto for p in graves):
        return 'grave'
    elif any(p in texto for p in positivas):
        return 'positivo'
    elif any(p in texto for p in neutrales):
        return 'analitico'
    else:
        return 'neutral'

def generar_redaccion_inteligente(noticia, categoria):
    titulo = noticia['title']
    descripcion = noticia['description']
    fuente = noticia.get('source', {}).get('name', 'Medios internacionales')
    tono = detectar_tono(titulo, descripcion)
    
    palabras_clave = [w for w in re.findall(r'\b[A-Za-zÁáÉéÍíÓóÚúÑñ]{4,}\b', titulo) 
                     if w.lower() not in ['como', 'para', 'pero', 'con', 'los', 'las', 'del', 'por', 'una', 'este', 'esta', 'desde', 'entre', 'sobre', 'hacia']]
    palabra_destacada = random.choice(palabras_clave) if palabras_clave else "este hecho"
    
    aperturas = {
        'crisis': {
            'grave': [
                f"La situación en torno a {palabra_destacada} ha alcanzado un punto crítico que demanda atención inmediata de la comunidad internacional.",
                f"Nuevos desarrollos confirman la gravedad de {palabra_destacada}, generando alerta entre los principales actores geopolíticos.",
                f"El escenario de {palabra_destacada} se complica con información que revela la magnitud real de la crisis."
            ],
            'neutral': [
                f"Los acontecimientos recientes en torno a {palabra_destacada} están redefiniendo el panorama de seguridad internacional.",
                f"La evolución de {palabra_destacada} mantiene en vilo a observadores y autoridades por igual.",
                f"Analistas internacionales siguen de cerca {palabra_destacada} ante posibles repercusiones regionales."
            ]
        },
        'economia': {
            'grave': [
                f"Los mercados registran turbulencias significativas vinculadas a {palabra_destacada}, con proyecciones ajustadas a la baja.",
                f"La incertidumbre en torno a {palabra_destacada} ha activado señales de alerta en los principales centros financieros.",
                f"Inversores reevalúan estrategias ante el impacto potencial de {palabra_destacada} en la economía global."
            ],
            'positivo': [
                f"Indicadores recientes vinculados a {palabra_destacada} sugieren una recuperación más robusta de lo anticipado.",
                f"El desempeño de {palabra_destacada} supera expectativas, generando optimismo cauteloso entre analistas.",
                f"Nuevos datos sobre {palabra_destacada} confirman tendencias positivas para el cierre del período."
            ],
            'neutral': [
                f"Los mercados ajustan posiciones ante la última información disponible sobre {palabra_destacada}.",
                f"Especialistas financieros analizan el impacto a mediano plazo de {palabra_destacada} en diversos sectores.",
                f"La evolución de {palabra_destacada} será determinante para las proyecciones del próximo trimestre."
            ]
        },
        'tech': {
            'positivo': [
                f"El avance de {palabra_destacada} marca un hito significativo en la trayectoria de innovación tecnológica.",
                f"Desarrollos recientes en {palabra_destacada} prometen transformar la experiencia de usuarios y empresas.",
                f"La consolidación de {palabra_destacada} posiciona a los principales actores del sector en nueva fase competitiva."
            ],
            'analitico': [
                f"Un análisis profundo de {palabra_destacada} revela implicaciones que trascienden el ámbito tecnológico convencional.",
                f"Expertos evalúan el alcance real de {palabra_destacada} más allá de las primeras impresiones.",
                f"El estudio de {palabra_destacada} plantea interrogantes fundamentales sobre el rumbo de la industria."
            ],
            'neutral': [
                f"La industria tecnológica ajusta estrategias ante el creciente protagonismo de {palabra_destacada}.",
                f"Nuevas propuestas en torno a {palabra_destacada} generan debate entre desarrolladores y reguladores.",
                f"La adopción de {palabra_destacada} avanza a ritmo desigual según regiones y sectores."
            ]
        },
        'politica': {
            'grave': [
                f"La polarización en torno a {palabra_destacada} alcanza niveles que complican cualquier salida negociada.",
                f"La gravedad de {palabra_destacada} ha movilizado a actores hasta ahora al margen del debate público.",
                f"La crisis vinculada a {palabra_destacada} pone a prueba la estabilidad de alianzas tradicionales."
            ],
            'positivo': [
                f"Un acuerdo inesperado en torno a {palabra_destacada} abre posibilidades de diálogo antes descartadas.",
                f"El consenso alcanzado sobre {palabra_destacada} representa un paso significativo en la agenda legislativa.",
                f"Los avances en {palabra_destacada} superan las expectativas más optimistas de los negociadores."
            ],
            'neutral': [
                f"El debate en torno a {palabra_destacada} continúa con posiciones que muestran escasa flexibilidad.",
                f"Los actores políticos redefinen estrategias ante la complejidad de {palabra_destacada}.",
                f"La discusión sobre {palabra_destacada} anticipa una negociación prolongada en los próximos meses."
            ]
        },
        'emergencia': {
            'grave': [
                f"La magnitud de {palabra_destacada} supera las primeras estimaciones, ampliando la zona de afectación.",
                f"Equipos de rescate trabajan contra el tiempo ante la gravedad de {palabra_destacada}.",
                f"La comunidad se moviliza ante el impacto devastador de {palabra_destacada} en zonas pobladas."
            ],
            'neutral': [
                f"Las autoridades coordinan respuesta integral ante {palabra_destacada} en múltiples frentes.",
                f"El monitoreo constante de {palabra_destacada} permite ajustar protocolos en tiempo real.",
                f"La experiencia previa en situaciones similares a {palabra_destacada} orienta la respuesta actual."
            ]
        }
    }
    
    cat_aperturas = aperturas.get(categoria, aperturas['crisis'])
    tono_aperturas = cat_aperturas.get(tono, cat_aperturas.get('neutral', cat_aperturas.get('grave')))
    apertura = random.choice(tono_aperturas)
    
    desarrollos = {
        'crisis': [
            f"Fuentes oficiales confirman que la situación evoluciona rápidamente, con actualizaciones cada pocas horas. Los análisis preliminares sugieren que los efectos podrían extenderse más allá de las fronteras inmediatas.",
            f"La comunidad internacional ha comenzado a articular una respuesta coordinada, aunque persisten diferencias sobre la estrategia más efectiva. Los organismos multilaterales mantienen reuniones de emergencia.",
            f"Especialistas en seguridad advierten que el escenario actual podría estabilizarse o deteriorarse en las próximas 48 horas, dependiendo de decisiones clave que aún están pendientes."
        ],
        'economia': [
            f"Los datos más recientes indican una volatilidad que podría mantenerse durante la semana. Los inversores institucionales recomiendan cautela y diversificación de carteras ante la incertidumbre.",
            f"Las proyecciones de los principales bancos de inversión muestran dispersión significativa, reflejando la dificultad de anticipar el desenlace de los factores en juego.",
            f"El sector empresarial ha manifestado preocupación por el impacto en cadenas de suministro y costos operativos, solicitando claridad en las políticas públicas a implementar."
        ],
        'tech': [
            f"Los competidores directos aceleran sus propios desarrollos en respuesta, anticipando una oleada de lanzamientos en el próximo trimestre. La presión por innovar se intensifica en todo el sector.",
            f"Expertos en ética tecnológica plantean interrogantes sobre las implicaciones sociales de estas capacidades, proponiendo marcos de regulación que aún no existen en la mayoría de jurisdicciones.",
            f"La adopción temprana por parte de grandes corporaciones sugiere una maduración más rápida de lo habitual, aunque la accesibilidad para usuarios individuales podría demorar varios meses."
        ],
        'politica': [
            f"Los sondeos de opinión pública muestran división acerca de la conveniencia de la medida, con diferencias marcadas según edad, región y nivel educativo de los consultados.",
            f"La agenda mediática de las próximas semanas estará dominada por este tema, con audiencias parlamentarias y foros públicos donde se expondrán argumentos encontrados.",
            f"Analistas políticos anticipan que la resolución de este asunto definirá las coaliciones de poder para el período legislativo venidero, con consecuencias que se extenderán por años."
        ],
        'emergencia': [
            f"Los protocolos de atención a damnificados han sido activados en coordinación con organizaciones de la sociedad civil. Se establecen centros de acopio y albergues temporales en puntos estratégicos.",
            f"La evaluación de daños materiales continúa, con cifras preliminares que probablemente se revisarán al alza conforme avancen los equipos de inspección por zonas de difícil acceso.",
            f"La solidaridad internacional se manifiesta mediante ofertas de asistencia técnica y recursos que serán canalizados a través de los mecanismos establecidos de cooperación."
        ]
    }
    
    desarrollos_cat = desarrollos.get(categoria, desarrollos['crisis'])
    desarrollo = random.choice(desarrollos_cat)
    
    cierres = {
        'grave': [
            "La situación permanece fluida y requiere monitoreo constante.",
            "Se esperan desarrollos significativos en las próximas horas.",
            "La comunidad internacional mantiene alerta máxima."
        ],
        'positivo': [
            "Los avances confirmados abren perspectivas prometedoras.",
            "El seguimiento de estos desarrollos continuará en próximas actualizaciones.",
            "Los actores involucrados expresan cauteloso optimismo."
        ],
        'analitico': [
            "El análisis profundo de estos datos continuará en reportes posteriores.",
            "Las implicaciones completas se comprenderán mejor con el paso de los días.",
            "Expertos convienen en que el estudio de este fenómeno apenas comienza."
        ],
        'neutral': [
            "Los detalles adicionales se conocerán conforme avancen las investigaciones.",
            "La cobertura de este tema continuará con actualizaciones pertinentes.",
            "Se mantiene contacto con fuentes para ampliar esta información."
        ]
    }
    
    cierre = random.choice(cierres.get(tono, cierres['neutral']))
    texto_redactado = f"{apertura}\n\n{descripcion}\n\n{desarrollo}\n\n{cierre}"
    return texto_redactado

def redactar_noticia(noticia, categoria):
    titulo = noticia['title']
    url = noticia['url']
    fuente = noticia.get('source', {}).get('name', 'Medios internacionales')
    cuerpo = generar_redaccion_inteligente(noticia, categoria)
    hashtags = generar_hashtags(titulo, categoria)
    
    mensaje = f"""📰 {titulo}

{cuerpo}

📡 Fuente: {fuente}
🔗 {url}

{hashtags}

— Verdad Hoy: Noticias Al Minuto"""
    return mensaje

def generar_hashtags(titulo, categoria):
    tags_base = {
        'crisis': ['#ActualidadInternacional', '#CrisisGlobal'],
        'economia': ['#Economía', '#Mercados'],
        'tech': ['#Tecnología', '#Innovación'],
        'politica': ['#Política', '#Gobierno'],
        'emergencia': ['#ÚltimaHora', '#Emergencia']
    }
    
    base = tags_base.get(categoria, ['#Noticias'])
    titulo_lower = titulo.lower()
    
    if any(p in titulo_lower for p in ['eeuu', 'estados unidos', 'biden', 'trump']):
        base.append('#EEUU')
    elif 'mexico' in titulo_lower:
        base.append('#México')
    elif any(p in titulo_lower for p in ['iran', 'israel', 'palestina', 'gaza']):
        base.append('#MedioOriente')
    elif 'ucrania' in titulo_lower or 'rusia' in titulo_lower:
        base.append('#Ucrania')
    
    base.append(f"#{datetime.now().strftime('%Y')}")
    return ' '.join(base[:4])

def publicar_en_facebook():
    global HISTORIAL_URLS
    
    print("DEBUG: Iniciando buscar_noticias_frescas()...")
    noticias = buscar_noticias_frescas()
    print(f"DEBUG: Noticias encontradas: {len(noticias)}")
    
    if not noticias:
        print("[AVISO] No hay noticias nuevas disponibles")
        return False
    
    noticia = noticias[0]
    categoria = noticia['categoria']
    
    HISTORIAL_URLS.add(noticia['url'])
    if len(HISTORIAL_URLS) > MAX_HISTORIAL:
        HISTORIAL_URLS.pop()
    
    print(f"\n[SELECCIONADA] {noticia['title'][:60]}...")
    print(f"  Score: {noticia['score']} | Categoría: {categoria}")
    
    # Obtener o generar imagen
    imagen_url = obtener_imagen_noticia(noticia)
    
    mensaje = redactar_noticia(noticia, categoria)
    print(f"DEBUG: Mensaje generado, longitud: {len(mensaje)} caracteres")
    
    try:
        print("[INFO] Publicando en Facebook...")
        
        if imagen_url:
            # Publicación CON imagen que redirige al enlace de la noticia
            print(f"[IMAGEN] Adjuntando imagen: {imagen_url[:60]}...")
            url_fb = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
            
            payload = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN,
                'link': noticia['url'],  # Esto hace que la imagen sea clickeable
                'picture': imagen_url,   # URL de la imagen a mostrar
                'name': noticia['title'][:100],  # Título del link
                'description': noticia['description'][:200],  # Descripción del link
            }
        else:
            # Publicación SIN imagen (modo texto como antes)
            url_fb = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
            payload = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN,
                'link': noticia['url']
            }
        
        print(f"DEBUG: Enviando request a Facebook...")
        response = requests.post(url_fb, data=payload, timeout=30)
        result = response.json()
        
        print(f"[DEBUG] Status: {response.status_code}")
        print(f"[DEBUG] Response: {result}")
        
        if response.status_code == 200 and 'id' in result:
            print(f"✅ PUBLICADO CON ÉXITO: {result['id']}")
            if imagen_url:
                print(f"   📷 Incluye imagen generada/adjunta")
            return True
        else:
            error_msg = result.get('error', {}).get('message', 'Error desconocido')
            print(f"❌ ERROR DE FACEBOOK: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 VERDAD DE HOY - GitHub Actions")
    print("="*60)
    try:
        resultado = publicar_en_facebook()
        print(f"DEBUG: Resultado: {resultado}")
        exit_code = 0 if resultado else 1
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    print(f"DEBUG: Saliendo con código {exit_code}")
    exit(exit_code)
