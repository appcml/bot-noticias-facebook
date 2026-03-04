import requests
import random
import re
import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse, quote
import base64
import json
import time

# Variables de entorno
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')

print(f"DEBUG: NEWS_API_KEY presente: {bool(NEWS_API_KEY)}")
print(f"DEBUG: FB_PAGE_ID presente: {bool(FB_PAGE_ID)}")
print(f"DEBUG: FB_ACCESS_TOKEN presente: {bool(FB_ACCESS_TOKEN)}")
print(f"DEBUG: OPENAI_API_KEY presente: {bool(OPENAI_API_KEY)}")
print(f"DEBUG: STABILITY_API_KEY presente: {bool(STABILITY_API_KEY)}")

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    print("ERROR: Variables faltantes")
    raise ValueError("Faltan variables de entorno obligatorias")

print("DEBUG: Todas las variables obligatorias OK")

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
    Prioriza OpenAI (DALL-E 3), si falla usa Stability AI.
    """
    prompt = crear_prompt_imagen(titulo, descripcion, categoria)
    print(f"[IMAGEN] Prompt generado: {prompt[:80]}...")
    
    # Intentar OpenAI primero (mejor calidad)
    if OPENAI_API_KEY:
        try:
            print("[IMAGEN] Intentando con OpenAI DALL-E 3...")
            resultado = generar_imagen_openai(prompt)
            if resultado:
                return resultado
        except Exception as e:
            print(f"[IMAGEN] OpenAI falló: {e}")
    
    # Fallback a Stability AI
    if STABILITY_API_KEY:
        try:
            print("[IMAGEN] Intentando con Stability AI...")
            return generar_imagen_stability(prompt)
        except Exception as e:
            print(f"[IMAGEN] Stability AI falló: {e}")
    
    print("[IMAGEN] No se pudo generar imagen con IA")
    return None

def crear_prompt_imagen(titulo, descripcion, categoria):
    """Crea un prompt optimizado para generación de imágenes según la categoría."""
    
    estilos = {
        'crisis': "dramatic photojournalism, cinematic lighting, serious composition, dark tones, professional news photography",
        'economia': "modern business infographic style, elegant silver and blue palette, professional corporate aesthetic, clean design",
        'tecnologia': "futuristic tech visualization, neon accents, sleek modern design, blue and purple lighting, 3D render style",
        'politica': "professional political photojournalism, government buildings, documentary style, natural lighting, Reuters/AP style",
        'emergencia': "urgent action photojournalism, emergency response scene, dynamic composition, red and orange emergency lighting",
        'general': "professional news photography, balanced composition, natural lighting, high quality, Reuters style"
    }
    
    estilo = estilos.get(categoria, estilos['general'])
    
    # Limpiar texto para el prompt
    texto_base = f"{titulo}. {descripcion[:150]}"
    texto_limpio = re.sub(r'[^\w\s.,;:!?]', '', texto_base)
    
    prompt = f"News illustration about: {texto_limpio}. Style: {estilo}. High quality, 4K, professional, NO text, NO logos, NO watermarks, NO words, photorealistic."
    
    return prompt[:900]

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
        "n": 1,
        "response_format": "url"
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=60)
    result = response.json()
    
    if response.status_code == 200 and 'data' in result and len(result['data']) > 0:
        image_url = result['data'][0]['url']
        print(f"[IMAGEN] OpenAI: Imagen generada exitosamente")
        return descargar_imagen_temp(image_url, "openai")
    else:
        error = result.get('error', {}).get('message', 'Error desconocido')
        raise Exception(f"OpenAI error: {error}")

def generar_imagen_stability(prompt):
    """Genera imagen usando Stability AI."""
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }
    
    files = {
        "prompt": (None, prompt),
        "output_format": (None, "png"),
        "aspect_ratio": (None, "1:1")
    }
    
    response = requests.post(url, headers=headers, files=files, timeout=60)
    
    if response.status_code == 200:
        # Guardar imagen temporalmente
        temp_filename = f"stability_{int(time.time())}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}.png"
        temp_path = f"/tmp/{temp_filename}"
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[IMAGEN] Stability: Imagen guardada en {temp_path}")
        return temp_path
    else:
        try:
            error_data = response.json()
            error_msg = error_data.get('errors', [error_data.get('message', 'Unknown error')])[0]
        except:
            error_msg = f"HTTP {response.status_code}"
        raise Exception(f"Stability AI error: {error_msg}")

def descargar_imagen_temp(image_url, prefix="img"):
    """Descarga imagen desde URL y guarda temporalmente."""
    try:
        print(f"[DESCARGA] Descargando: {image_url[:60]}...")
        response = requests.get(image_url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            # Detectar extensión
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                ext = 'png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            else:
                ext = 'png'
            
            temp_filename = f"{prefix}_{int(time.time())}_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.{ext}"
            temp_path = f"/tmp/{temp_filename}"
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            print(f"[DESCARGA] Guardada en {temp_path} ({os.path.getsize(temp_path)} bytes)")
            return temp_path
        else:
            print(f"[DESCARGA] Error HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Descargando imagen: {e}")
    return None

def obtener_imagen_noticia(articulo):
    """
    Obtiene la mejor imagen disponible SIEMPRE como archivo local:
    1. Intenta descargar imagen original de la noticia
    2. Si no existe o falla, genera con IA
    """
    url_imagen = articulo.get('urlToImage')
    titulo = articulo.get('title', '')
    descripcion = articulo.get('description', '')
    categoria = articulo.get('categoria', 'general')
    
    # PASO 1: Intentar descargar imagen original
    if url_imagen:
        print(f"[IMAGEN] Intentando descargar imagen original...")
        temp_path = descargar_imagen_temp(url_imagen, "original")
        if temp_path and os.path.exists(temp_path) and os.path.getsize(temp_path) > 1024:
            print(f"[IMAGEN] Imagen original descargada exitosamente")
            return temp_path
        print(f"[IMAGEN] Falló descarga de imagen original")
    
    # PASO 2: Generar con IA si no hay original o falló
    print(f"[IMAGEN] Generando imagen con IA...")
    imagen_local = generar_imagen_ia(titulo, descripcion, categoria)
    return imagen_local

def publicar_foto_con_link(mensaje, image_path, link_url):
    """
    PUBLICACIÓN DIRECTA: Sube foto a Facebook con el mensaje que incluye el link.
    Esta es la forma más confiable de incluir imagen + link.
    """
    try:
        print(f"[PUBLICAR] Método: Foto directa con link en mensaje...")
        
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        
        # Preparar mensaje con el link incluido al final
        mensaje_completo = f"{mensaje}\n\n🔗 Lee la noticia completa: {link_url}"
        
        with open(image_path, 'rb') as img:
            files = {
                'file': (os.path.basename(image_path), img, 'image/jpeg')
            }
            data = {
                'message': mensaje_completo,
                'access_token': FB_ACCESS_TOKEN,
                'published': 'true'
            }
            
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            print(f"[DEBUG] Status: {response.status_code}")
            print(f"[DEBUG] Response: {json.dumps(result, indent=2)[:200]}...")
            
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO CON FOTO: {result['id']}")
                return True, result
            else:
                error_msg = result.get('error', {}).get('message', 'Error desconocido')
                print(f"❌ ERROR: {error_msg}")
                return False, result
                
    except Exception as e:
        print(f"❌ ERROR en publicar_foto_con_link: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def publicar_solo_texto(mensaje, link_url):
    """Método fallback: publicar solo texto con link."""
    try:
        print("[INFO] Publicando solo texto con link...")
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        
        payload = {
            'message': mensaje,
            'access_token': FB_ACCESS_TOKEN,
            'link': link_url
        }
        
        response = requests.post(url, data=payload, timeout=60)
        result = response.json()
        
        if response.status_code == 200 and 'id' in result:
            print(f"✅ PUBLICADO (solo texto): {result['id']}")
            return True, result
        else:
            error_msg = result.get('error', {}).get('message', 'Error desconocido')
            print(f"❌ ERROR: {error_msg}")
            return False, result
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, None

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
    
    # Obtener imagen SIEMPRE como archivo local
    print("[PROCESO] Obteniendo imagen...")
    imagen_path = obtener_imagen_noticia(noticia)
    
    mensaje = redactar_noticia(noticia, categoria)
    print(f"DEBUG: Mensaje generado, longitud: {len(mensaje)} caracteres")
    
    exito = False
    resultado = None
    
    try:
        if imagen_path and os.path.exists(imagen_path):
            # Publicar con foto (método directo)
            exito, resultado = publicar_foto_con_link(mensaje, imagen_path, noticia['url'])
            
            # Limpiar archivo temporal
            try:
                os.remove(imagen_path)
                print(f"[LIMPIEZA] Archivo temporal eliminado")
            except Exception as e:
                print(f"[AVISO] No se pudo eliminar archivo temporal: {e}")
        else:
            print("[AVISO] No hay imagen disponible")
        
        # Si falló o no hay imagen, publicar solo texto
        if not exito:
            print("[INFO] Intentando publicación solo texto...")
            exito, resultado = publicar_solo_texto(mensaje, noticia['url'])
        
        return exito
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        # Intentar fallback
        try:
            exito, _ = publicar_solo_texto(mensaje, noticia['url'])
            return exito
        except:
            return False

if __name__ == "__main__":
    print("🚀 VERDAD DE HOY - GitHub Actions")
    print("="*60)
    print(f"🤖 OpenAI disponible: {bool(OPENAI_API_KEY)}")
    print(f"🎨 Stability AI disponible: {bool(STABILITY_API_KEY)}")
    print("="*60)
    
    try:
        resultado = publicar_en_facebook()
        print(f"DEBUG: Resultado final: {resultado}")
        exit_code = 0 if resultado else 1
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    print(f"DEBUG: Saliendo con código {exit_code}")
    exit(exit_code)
