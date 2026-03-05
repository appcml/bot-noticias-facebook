import requests
import random
import re
import hashlib
import os
import json
from datetime import datetime
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"DEBUG: NEWS_API_KEY presente: {bool(NEWS_API_KEY)}")
print(f"DEBUG: FB_PAGE_ID presente: {bool(FB_PAGE_ID)}")
print(f"DEBUG: FB_ACCESS_TOKEN presente: {bool(FB_ACCESS_TOKEN)}")

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    print("ERROR: Variables faltantes esenciales")
    raise ValueError("Faltan variables de entorno esenciales")

print("DEBUG: Variables esenciales OK")

FUENTES_PREMIUM = {
    'internacional': ['bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'aljazeera.com', 'elpais.com', 'clarin.com', 'nytimes.com', 'washingtonpost.com'],
    'economia': ['bloomberg.com', 'forbes.com', 'eleconomista.es', 'expansion.com', 'ambito.com', 'ft.com', 'wsj.com'],
    'tecnologia': ['techcrunch.com', 'theverge.com', 'wired.com', 'xataka.com', 'fayerwayer.com', 'arstechnica.com'],
    'politica': ['politico.com', 'axios.com', 'infobae.com', 'animalpolitico.com', 'reforma.com']
}

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 200

def cargar_historial():
    """Carga el historial de URLs publicadas desde archivo"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('urls', [])), data.get('hashes', [])
        except:
            return set(), []
    return set(), []

def guardar_historial(urls, hashes):
    """Guarda el historial de URLs publicadas"""
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': hashes[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat()
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_texto(texto, idioma_origen='EN'):
    """Traduce texto del inglés al español usando DeepL"""
    if not DEEPL_API_KEY or idioma_origen.upper() != 'EN':
        return texto
    
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto,
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"[TRADUCCIÓN] Error: {e}")
    
    return texto

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"BUSCANDO NOTICIAS VIRALES - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    fecha_ayer = (datetime.now().timestamp() - 86400)
    
    busquedas_virales = [
        ('breaking news OR "just now" OR "developing story"', 'internacional'),
        ('world news today OR international news', 'internacional'),
        ('politics crisis OR emergency OR urgent', 'politica'),
        ('economy markets crash OR surge OR record', 'economia'),
        ('technology AI artificial intelligence breakthrough', 'tech'),
        ('war conflict OR attack OR missile OR invasion', 'crisis'),
        ('disaster earthquake OR hurricane OR flood', 'emergencia')
    ]
    
    busquedas_hoy = random.sample(busquedas_virales, min(5, len(busquedas_virales)))
    todas_noticias = []
    
    for query, categoria in busquedas_hoy:
        url_es = f"https://newsapi.org/v2/everything?q={query}&language=es&from={datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')}&to={fecha_hoy}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        url_en = f"https://newsapi.org/v2/everything?q={query}&language=en&from={datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')}&to={fecha_hoy}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
        
        try:
            print(f"[BÚSQUEDA] {categoria}: {query[:40]}...")
            
            response = requests.get(url_es, timeout=15)
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                for art in data['articles']:
                    if es_noticia_valida(art):
                        score = calcular_score(art, categoria)
                        art['categoria'] = categoria
                        art['score'] = score
                        art['url_hash'] = hashlib.md5(art['url'].encode()).hexdigest()[:16]
                        art['idioma'] = 'ES'
                        art['titulo_original'] = art['title']
                        art['descripcion_original'] = art['description']
                        todas_noticias.append(art)
                        print(f"  [ES] {art['title'][:50]}... (score: {score})")
            
            if DEEPL_API_KEY:
                response_en = requests.get(url_en, timeout=15)
                data_en = response_en.json()
                
                if data_en.get('status') == 'ok' and data_en.get('articles'):
                    for art in data_en['articles']:
                        if es_noticia_valida(art):
                            score = calcular_score(art, categoria)
                            art['categoria'] = categoria
                            art['score'] = score
                            art['url_hash'] = hashlib.md5(art['url'].encode()).hexdigest()[:16]
                            art['idioma'] = 'EN'
                            art['titulo_original'] = art['title']
                            art['descripcion_original'] = art['description']
                            art['title'] = traducir_texto(art['title'], 'EN')
                            art['description'] = traducir_texto(art['description'], 'EN')
                            todas_noticias.append(art)
                            print(f"  [EN→ES] {art['title'][:50]}... (score: {score})")
                            
        except Exception as e:
            print(f"[ERROR] en búsqueda {categoria}: {e}")
    
    print(f"\n[INFO] Total noticias encontradas: {len(todas_noticias)}")
    
    noticias_unicas = {}
    for art in todas_noticias:
        if art['url_hash'] not in noticias_unicas:
            noticias_unicas[art['url_hash']] = art
    
    noticias_lista = list(noticias_unicas.values())
    print(f"[INFO] Noticias únicas: {len(noticias_lista)}")
    
    # Solo noticias con imagen disponible
    noticias_con_imagen = [n for n in noticias_lista if n.get('urlToImage') and n['urlToImage'].startswith('http')]
    print(f"[INFO] Noticias con imagen: {len(noticias_con_imagen)}")
    
    noticias_nuevas = [n for n in noticias_con_imagen if n['url'] not in HISTORIAL_URLS and n['url_hash'] not in HISTORIAL_HASHES]
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
    dominios_malos = ['news.google.com', 'google.com/news', 'facebook.com', 'twitter.com', 'youtube.com']
    if any(mal in url.lower() for mal in dominios_malos):
        return False
    return True

def calcular_score(art, categoria):
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    impacto_viral = {
        'breaking': 40, 'urgent': 35, 'alert': 30, 'just now': 35,
        'exclusive': 30, 'developing': 25, 'live': 25,
        'trump': 30, 'biden': 25, 'putin': 30, 'zelensky': 25,
        'war': 35, 'attack': 35, 'invasion': 35, 'missile': 30, 'bomb': 30,
        'crash': 30, 'collapse': 30, 'crisis': 25, 'emergency': 25,
        'dead': 30, 'killed': 35, 'dies': 30, 'death toll': 35,
        'earthquake': 30, 'tsunami': 35, 'hurricane': 30, 'flood': 25,
        'market': 20, 'stocks': 20, 'economy': 20, 'inflation': 25, 'recession': 30,
        'ai': 25, 'artificial intelligence': 30, 'chatgpt': 25, 'breakthrough': 25,
        'scandal': 30, 'resigns': 25, 'impeachment': 30, 'election': 20
    }
    
    for palabra, puntos in impacto_viral.items():
        if palabra in texto:
            score += puntos
    
    fuente = urlparse(art.get('url', '')).netloc.lower()
    for cat, fuentes in FUENTES_PREMIUM.items():
        if any(f in fuente for f in fuentes):
            score += 25
            break
    
    try:
        fecha_pub = art.get('publishedAt', '')
        if fecha_pub:
            fecha_art = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00'))
            horas_diferencia = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            if horas_diferencia < 1:
                score += 40
            elif horas_diferencia < 3:
                score += 30
            elif horas_diferencia < 6:
                score += 20
            elif horas_diferencia < 24:
                score += 10
            else:
                score -= 10
    except:
        pass
    
    if art.get('urlToImage') and art['urlToImage'].startswith('http'):
        score += 15
    
    if categoria in ['crisis', 'emergencia']:
        score += 20
    
    return score

def detectar_tono(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    graves = ['muerte', 'muertos', 'muerto', 'ataque', 'guerra', 'tragedia', 'desastre', 'crisis', 'urgente', 'breaking', 'emergency']
    positivas = ['avance', 'descubrimiento', 'innovacion', 'acuerdo', 'paz', 'logro', 'éxito', 'breakthrough', 'advance']
    neutrales = ['estudio', 'análisis', 'reporte', 'datos', 'encuesta', 'investigación', 'analysis', 'study']
    
    if any(p in texto for p in graves):
        return 'grave'
    elif any(p in texto for p in positivas):
        return 'positivo'
    elif any(p in texto for p in neutrales):
        return 'analitico'
    else:
        return 'neutral'

def descargar_imagen(url_imagen):
    """Descarga imagen de la noticia y la prepara para Facebook"""
    if not url_imagen or not url_imagen.startswith('http'):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url_imagen, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Guardar en directorio temporal del runner
            temp_path = f'/tmp/noticia_{hashlib.md5(url_imagen.encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85)
            print(f"[IMAGEN] Descargada y guardada: {temp_path}")
            return temp_path
    except Exception as e:
        print(f"[IMAGEN] Error descargando: {e}")
    
    return None

def publicar_foto_con_texto(image_path, mensaje):
    """Publica foto con texto en Facebook (sin link externo)"""
    if not image_path or not os.path.exists(image_path):
        print("[ERROR] No hay imagen para publicar")
        return False
    
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }
            
            print(f"[FACEBOOK] Subiendo foto con texto...")
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            print(f"[DEBUG] Status: {response.status_code}")
            
            if response.status_code == 200 and 'id' in result:
                print(f"✅ FOTO PUBLICADA EXITOSAMENTE: {result['id']}")
                return True
            else:
                error_msg = result.get('error', {}).get('message', 'Error desconocido')
                print(f"❌ ERROR DE FACEBOOK: {error_msg}")
                print(f"❌ RESPUESTA COMPLETA: {result}")
                return False
                
    except Exception as e:
        print(f"❌ ERROR publicando foto: {e}")
        import traceback
        traceback.print_exc()
        return False

def generar_redaccion_inteligente(noticia, categoria):
    titulo = noticia['title']
    descripcion = noticia['description']
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    tono = detectar_tono(titulo, descripcion)
    idioma_origen = noticia.get('idioma', 'ES')
    
    palabras_clave = [w for w in re.findall(r'\b[A-Za-zÁáÉéÍíÓóÚúÑñ]{5,}\b', titulo) 
                     if w.lower() not in ['como', 'para', 'pero', 'con', 'los', 'las', 'del', 'por', 'una', 'este', 'esta', 'desde', 'entre', 'sobre', 'hacia', 'after', 'before', 'during', 'through', 'between']]
    palabra_destacada = random.choice(palabras_clave) if palabras_clave else "este hecho"
    
    aperturas = {
        'internacional': {
            'grave': [
                f"La situación internacional en torno a {palabra_destacada} ha alcanzado un punto crítico que demanda atención inmediata.",
                f"Nuevos desarrollos confirman la gravedad de {palabra_destacada}, generando alerta entre los principales actores geopolíticos.",
                f"El escenario global de {palabra_destacada} se complica con información que revela la magnitud real de la crisis."
            ],
            'neutral': [
                f"Los acontecimientos recientes en el ámbito internacional respecto a {palabra_destacada} están redefiniendo el panorama global.",
                f"La evolución de {palabra_destacada} mantiene en vilo a observadores y autoridades por igual.",
                f"Analistas internacionales siguen de cerca {palabra_destacada} ante posibles repercusiones globales."
            ],
            'positivo': [
                f"Un avance significativo en {palabra_destacada} marca un hito en las relaciones internacionales contemporáneas.",
                f"El desarrollo positivo de {palabra_destacada} abre nuevas perspectivas de cooperación global.",
                f"Los avances en {palabra_destacada} superan las expectativas de la comunidad internacional."
            ]
        },
        'economia': {
            'grave': [
                f"Los mercados globales registran turbulencias significativas vinculadas a {palabra_destacada}, con proyecciones ajustadas a la baja.",
                f"La incertidumbre en torno a {palabra_destacada} ha activado señales de alerta en los principales centros financieros.",
                f"Inversores internacionales reevalúan estrategias ante el impacto potencial de {palabra_destacada}."
            ],
            'positivo': [
                f"Indicadores económicos recientes vinculados a {palabra_destacada} sugieren una recuperación más robusta de lo anticipado.",
                f"El desempeño de {palabra_destacada} supera expectativas, generando optimismo cauteloso entre analistas financieros.",
                f"Nuevos datos sobre {palabra_destacada} confirman tendencias positivas para el cierre del período."
            ],
            'neutral': [
                f"Los mercados financieros ajustan posiciones ante la última información disponible sobre {palabra_destacada}.",
                f"Especialistas económicos analizan el impacto a mediano plazo de {palabra_destacada} en diversos sectores productivos.",
                f"La evolución de {palabra_destacada} será determinante para las proyecciones económicas del próximo trimestre."
            ]
        },
        'tech': {
            'positivo': [
                f"El avance tecnológico en {palabra_destacada} marca un hito significativo en la trayectoria de innovación global.",
                f"Desarrollos recientes en {palabra_destacada} prometen transformar la experiencia de usuarios y empresas a nivel mundial.",
                f"La consolidación de {palabra_destacada} posiciona a los principales actores del sector tecnológico en una nueva fase competitiva."
            ],
            'analitico': [
                f"Un análisis profundo de {palabra_destacada} revela implicaciones que trascienden el ámbito tecnológico convencional.",
                f"Expertos evalúan el alcance real de {palabra_destacada} más allá de las primeras impresiones del mercado.",
                f"El estudio de {palabra_destacada} plantea interrogantes fundamentales sobre el rumbo de la industria tecnológica."
            ],
            'neutral': [
                f"La industria tecnológica global ajusta estrategias ante el creciente protagonismo de {palabra_destacada}.",
                f"Nuevas propuestas en torno a {palabra_destacada} generan debate entre desarrolladores y reguladores internacionales.",
                f"La adopción de {palabra_destacada} avanza a ritmo desigual según regiones y sectores económicos."
            ]
        },
        'politica': {
            'grave': [
                f"La polarización política en torno a {palabra_destacada} alcanza niveles que complican cualquier salida negociada.",
                f"La gravedad de {palabra_destacada} ha movilizado a actores políticos hasta ahora al margen del debate público.",
                f"La crisis política vinculada a {palabra_destacada} pone a prueba la estabilidad de alianzas tradicionales."
            ],
            'positivo': [
                f"Un acuerdo político inesperado en torno a {palabra_destacada} abre posibilidades de diálogo antes descartadas.",
                f"El consenso alcanzado sobre {palabra_destacada} representa un paso significativo en la agenda legislativa.",
                f"Los avances políticos en {palabra_destacada} superan las expectativas más optimistas de los negociadores."
            ],
            'neutral': [
                f"El debate político en torno a {palabra_destacada} continúa con posiciones que muestran escasa flexibilidad.",
                f"Los actores políticos redefinen estrategias ante la complejidad de {palabra_destacada}.",
                f"La discusión sobre {palabra_destacada} anticipa una negociación prolongada en los próximos meses."
            ]
        },
        'crisis': {
            'grave': [
                f"La magnitud de {palabra_destacada} supera las primeras estimaciones, ampliando la zona de afectación internacional.",
                f"Equipos de respuesta trabajan contra el tiempo ante la gravedad de {palabra_destacada}.",
                f"La comunidad internacional se moviliza ante el impacto devastador de {palabra_destacada}."
            ],
            'neutral': [
                f"Las autoridades internacionales coordinan respuesta integral ante {palabra_destacada} en múltiples frentes.",
                f"El monitoreo constante de {palabra_destacada} permite ajustar protocolos de seguridad en tiempo real.",
                f"La experiencia previa en situaciones similares a {palabra_destacada} orienta la respuesta actual."
            ]
        },
        'emergencia': {
            'grave': [
                f"Servicios de emergencia internacionales responden ante la gravedad de {palabra_destacada}.",
                f"La magnitud de {palabra_destacada} requiere movilización de recursos de ayuda humanitaria.",
                f"Autoridades declaran estado de emergencia ante el impacto de {palabra_destacada}."
            ],
            'neutral': [
                f"Protocolos internacionales de emergencia han sido activados ante {palabra_destacada}.",
                f"La coordinación global ante {palabra_destacada} involucra a múltiples organismos de ayuda.",
                f"Se establecen corredores de ayuda internacional ante la situación de {palabra_destacada}."
            ]
        }
    }
    
    cat_aperturas = aperturas.get(categoria, aperturas['internacional'])
    tono_aperturas = cat_aperturas.get(tono, cat_aperturas.get('neutral', cat_aperturas.get('grave')))
    apertura = random.choice(tono_aperturas)
    
    desarrollos = {
        'internacional': [
            f"Fuentes oficiales confirman que la situación evoluciona rápidamente, con actualizaciones cada pocas horas. Los análisis preliminares sugieren que los efectos podrían extenderse más allá de las fronteras inmediatas.",
            f"La comunidad internacional ha comenzado a articular una respuesta coordinada, aunque persisten diferencias sobre la estrategia más efectiva. Los organismos multilaterales mantienen reuniones de emergencia.",
            f"Especialistas en relaciones internacionales advierten que el escenario actual podría estabilizarse o deteriorarse en las próximas 48 horas, dependiendo de decisiones clave que aún están pendientes."
        ],
        'economia': [
            f"Los datos más recientes indican una volatilidad que podría mantenerse durante la semana. Los inversores institucionales recomiendan cautela y diversificación de carteras ante la incertidumbre global.",
            f"Las proyecciones de los principales bancos centrales muestran dispersión significativa, reflejando la dificultad de anticipar el desenlace de los factores económicos en juego.",
            f"El sector empresarial global ha manifestado preocupación por el impacto en cadenas de suministro internacionales y costos operativos, solicitando claridad en las políticas públicas."
        ],
        'tech': [
            f"Los competidores tecnológicos globales aceleran sus propios desarrollos en respuesta, anticipando una oleada de lanzamientos en el próximo trimestre. La presión por innovar se intensifica.",
            f"Expertos en ética tecnológica plantean interrogantes sobre las implicaciones sociales globales de estas capacidades, proponiendo marcos de regulación internacional.",
            f"La adopción temprana por parte de grandes corporaciones multinacionales sugiere una maduración más rápida de lo habitual, aunque la accesibilidad global podría demorar."
        ],
        'politica': [
            f"Los sondeos de opinión pública internacional muestran división acerca de la conveniencia de la medida, con diferencias marcadas según regiones y contextos políticos.",
            f"La agenda mediática global de las próximas semanas estará dominada por este tema, con audiencias parlamentarias y foros públicos donde se expondrán argumentos encontrados.",
            f"Analistas políticos internacionales anticipan que la resolución de este asunto definirá las coaliciones de poder globales para el período venidero."
        ],
        'crisis': [
            f"Los protocolos internacionales de seguridad han sido activados en coordinación con organismos multilaterales. Se establecen canales de comunicación de emergencia.",
            f"La evaluación de la crisis continúa, con cifras preliminares que probablemente se revisarán conforme avancen los equipos de análisis por zonas afectadas.",
            f"La solidaridad internacional se manifiesta mediante ofertas de asistencia técnica y recursos que serán canalizados a través de mecanismos establecidos de cooperación global."
        ],
        'emergencia': [
            f"Los equipos de respuesta internacional coordinan esfuerzos con autoridades locales. Se establecen centros de comando unificado en zonas afectadas.",
            f"La evaluación de daños continúa en tiempo real, permitiendo ajustar la asignación de recursos de ayuda humanitaria según las necesidades más urgentes.",
            f"Organismos internacionales de ayuda movilizan recursos financieros y materiales para atender la emergencia de {palabra_destacada}."
        ]
    }
    
    desarrollos_cat = desarrollos.get(categoria, desarrollos['internacional'])
    desarrollo = random.choice(desarrollos_cat)
    
    cierres = {
        'grave': [
            "La situación permanece fluida y requiere monitoreo constante por parte de la comunidad internacional.",
            "Se esperan desarrollos significativos en las próximas horas. Manténgase informado.",
            "La comunidad global mantiene alerta máxima ante posibles escaladas."
        ],
        'positivo': [
            "Los avances confirmados abren perspectivas prometedoras para el desarrollo posterior.",
            "El seguimiento de estos desarrollos continuará en próximas actualizaciones internacionales.",
            "Los actores involucrados expresan cauteloso optimismo ante los resultados obtenidos."
        ],
        'analitico': [
            "El análisis profundo de estos datos continuará en reportes posteriores de nuestro equipo.",
            "Las implicaciones completas se comprenderán mejor con el paso de los días y nueva información.",
            "Expertos internacionales convienen en que el estudio de este fenómeno apenas comienza."
        ],
        'neutral': [
            "Los detalles adicionales se conocerán conforme avancen las investigaciones oficiales.",
            "Nuestra cobertura internacional de este tema continuará con actualizaciones pertinentes.",
            "Se mantiene contacto con fuentes globales para ampliar esta información en desarrollo."
        ]
    }
    
    cierre = random.choice(cierres.get(tono, cierres['neutral']))
    
    indicador_traduccion = ""
    if idioma_origen == 'EN':
        indicador_traduccion = "🌐 Noticia internacional traducida al español.\n\n"
    
    # Agregar fuente al final del texto (no como link)
    texto_redactado = f"{indicador_traduccion}{apertura}\n\n{descripcion}\n\n{desarrollo}\n\n{cierre}\n\n📡 Fuente: {fuente}"
    return texto_redactado

def generar_titular_prensa(noticia):
    """Genera un titular estilo prensa profesional"""
    titulo_original = noticia['title']
    categoria = noticia.get('categoria', 'internacional')
    
    plantillas = {
        'crisis': [
            "URGENTE: {titulo}",
            "ÚLTIMA HORA: {titulo}",
            "ALERTA INTERNACIONAL: {titulo}",
            "CRISIS GLOBAL: {titulo}"
        ],
        'emergencia': [
            "EMERGENCIA MUNDIAL: {titulo}",
            "URGENTE - Desastre internacional: {titulo}",
            "ALERTA: {titulo}",
            "SITUACIÓN CRÍTICA: {titulo}"
        ],
        'politica': [
            "Giro político internacional: {titulo}",
            "Crisis diplomática: {titulo}",
            "Tensión global: {titulo}",
            "Decisión histórica: {titulo}"
        ],
        'economia': [
            "Impacto económico global: {titulo}",
            "Mercados internacionales: {titulo}",
            "Crisis financiera: {titulo}",
            "Alerta económica mundial: {titulo}"
        ],
        'tech': [
            "Avance tecnológico global: {titulo}",
            "Innovación internacional: {titulo}",
            "Revolución tech: {titulo}",
            "Futuro digital: {titulo}"
        ],
        'internacional': [
            "Actualidad mundial: {titulo}",
            "Noticia internacional: {titulo}",
            "Escenario global: {titulo}",
            "Desarrollo mundial: {titulo}"
        ]
    }
    
    plantillas_cat = plantillas.get(categoria, plantillas['internacional'])
    plantilla = random.choice(plantillas_cat)
    
    titulo_limpio = re.sub(r'^(URGENTE|BREAKING|ALERTA|ÚLTIMA HORA|EMERGENCIA):\s*', '', titulo_original, flags=re.IGNORECASE)
    
    return plantilla.format(titulo=titulo_limpio)

def generar_hashtags(titulo, categoria):
    tags_base = {
        'crisis': ['#ÚltimaHora', '#CrisisInternacional', '#ActualidadMundial'],
        'emergencia': ['#EmergenciaGlobal', '#AlertaInternacional', '#NoticiaUrgente'],
        'economia': ['#EconomíaGlobal', '#MercadosInternacionales', '#FinanzasMundiales'],
        'tech': ['#TecnologíaGlobal', '#InnovaciónInternacional', '#TechNews'],
        'politica': ['#PolíticaInternacional', '#DiplomaciaGlobal', '#GobiernoMundial'],
        'internacional': ['#NoticiasMundiales', '#ActualidadInternacional', '#WorldNews']
    }
    
    base = tags_base.get(categoria, ['#NoticiasInternacionales'])
    titulo_lower = titulo.lower()
    
    if any(p in titulo_lower for p in ['eeuu', 'estados unidos', 'biden', 'trump', 'washington']):
        base.append('#EEUU')
    elif 'mexico' in titulo_lower or 'méxico' in titulo_lower:
        base.append('#México')
    elif any(p in titulo_lower for p in ['iran', 'israel', 'palestina', 'gaza', 'medio oriente']):
        base.append('#MedioOriente')
    elif 'ucrania' in titulo_lower or 'ucrania' in titulo_lower or 'rusia' in titulo_lower:
        base.append('#Ucrania')
    elif 'china' in titulo_lower or 'beijing' in titulo_lower:
        base.append('#China')
    elif 'europa' in titulo_lower or 'ue' in titulo_lower or 'unión europea' in titulo_lower:
        base.append('#Europa')
    elif 'latinoamérica' in titulo_lower or 'latinoamerica' in titulo_lower or 'américa latina' in titulo_lower:
        base.append('#Latinoamérica')
    
    base.append(f"#{datetime.now().strftime('%Y')}")
    
    return ' '.join(base[:5])

def redactar_noticia(noticia, categoria):
    titular = generar_titular_prensa(noticia)
    cuerpo = generar_redaccion_inteligente(noticia, categoria)
    hashtags = generar_hashtags(noticia['title'], categoria)
    
    # Ya no incluimos el link URL aquí - solo texto + imagen adjunta
    mensaje = f"""📰 {titular}

{cuerpo}

{hashtags}

— Verdad Hoy: Noticias Internacionales Al Minuto"""
    return mensaje

def publicar_en_facebook():
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("DEBUG: Iniciando búsqueda de noticias virales...")
    noticias = buscar_noticias_frescas()
    print(f"DEBUG: Noticias candidatas encontradas: {len(noticias)}")
    
    if not noticias:
        print("[AVISO] No hay noticias nuevas disponibles para publicar")
        return False
    
    # Intentar publicar la mejor noticia disponible
    for noticia in noticias:
        try:
            categoria = noticia['categoria']
            
            print(f"\n[SELECCIONADA] {noticia['title'][:60]}...")
            print(f"  Score viral: {noticia['score']} | Categoría: {categoria} | Idioma: {noticia.get('idioma', 'ES')}")
            
            # Verificar que tenga imagen
            if not noticia.get('urlToImage'):
                print("[SALTAR] Noticia sin imagen, buscando siguiente...")
                continue
            
            # Descargar imagen
            print(f"[IMAGEN] Descargando: {noticia['urlToImage'][:60]}...")
            image_path = descargar_imagen(noticia['urlToImage'])
            
            if not image_path:
                print("[SALTAR] No se pudo descargar imagen, buscando siguiente...")
                continue
            
            # Generar mensaje (sin link)
            mensaje = redactar_noticia(noticia, categoria)
            print(f"DEBUG: Mensaje generado ({len(mensaje)} caracteres)")
            
            # Publicar foto con texto (sin link externo)
            exito = publicar_foto_con_texto(image_path, mensaje)
            
            if exito:
                # Guardar en historial solo si se publicó correctamente
                HISTORIAL_URLS.add(noticia['url'])
                HISTORIAL_HASHES.append(noticia['url_hash'])
                guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
                
                # Limpiar imagen temporal
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"[LIMPIEZA] Imagen temporal eliminada")
                
                return True
            else:
                # Si falló, limpiar imagen y continuar con siguiente noticia
                if os.path.exists(image_path):
                    os.remove(image_path)
                print("[REINTENTO] Buscando siguiente noticia...")
                continue
                
        except Exception as e:
            print(f"❌ ERROR procesando noticia: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("❌ No se pudo publicar ninguna noticia")
    return False

if __name__ == "__main__":
    print("🚀 VERDAD DE HOY - Sistema de Noticias Internacionales")
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

