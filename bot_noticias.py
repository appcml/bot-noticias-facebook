import requests
import random
import re
import hashlib
import os
import json
import feedparser
from datetime import datetime, timedelta
from urllib.parse import urlparse, urldefrag
from PIL import Image
from io import BytesIO

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 2000
MIN_PALABRAS_REDACCION = 150

RSS_FEEDS = [
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.reuters.com/rssFeed/worldNews',
    'https://feeds.npr.org/1001/rss.xml',
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.politico.com/politics/news.xml',
    'https://rss.cnn.com/rss/edition_world.rss',
    'https://feeds.huffpost.com/HuffPostWorld',
]

# ============================================================================
# FUNCIONES DE HISTORIAL (ANTI-DUPLICADOS)
# ============================================================================

def normalizar_url(url):
    """Limpia URL para comparación consistente"""
    if not url:
        return ""
    url = str(url).lower().strip()
    url, _ = urldefrag(url)
    
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        # Eliminar parámetros de tracking
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source', 'campaign', 
                        'medium', 'content', 'term', 'id', 'rss']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, nuevo_query, ''
        ))
    except Exception as e:
        print(f"   ⚠️ Error normalizando URL: {e}")
    
    return url.rstrip('/')

def get_url_id(url):
    """Genera ID único hash para URL"""
    return hashlib.md5(normalizar_url(url).encode()).hexdigest()

def get_titulo_id(titulo):
    """Genera ID del título para detectar duplicados por contenido"""
    if not titulo:
        return ""
    # Limpiar título: minúsculas, sin puntuación, primeras 60 chars
    limpio = re.sub(r'[^\w\s]', '', str(titulo).lower()).strip()
    # Eliminar palabras comunes
    stopwords = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
                 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him',
                 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two',
                 'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'many', 'oil',
                 'sit', 'set', 'run', 'eat', 'far', 'sea', 'eye', 'ago', 'off',
                 'too', 'any', 'say', 'man', 'try', 'ask', 'end', 'why', 'let',
                 'put', 'say', 'she', 'try', 'way', 'own', 'say', 'too', 'old',
                 'el', 'la', 'de', 'que', 'y', 'en', 'un', 'ser', 'se', 'no',
                 'por', 'con', 'su', 'para', 'una', 'lo', 'más', 'pero', 'sus']
    
    palabras = [p for p in limpio.split() if p not in stopwords and len(p) > 3]
    return ' '.join(palabras[:8])  # Primeras 8 palabras significativas

def cargar_historial():
    """Carga historial de publicaciones previas"""
    print("\n📚 CARGANDO HISTORIAL...")
    
    if not os.path.exists(HISTORIAL_FILE):
        print("   ℹ️ No existe archivo de historial - será creado")
        return {'urls': set(), 'ids': set(), 'titulos': set(), 'contenidos': set()}
    
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        historial = {
            'urls': set(data.get('urls', [])),
            'ids': set(data.get('ids', [])),
            'titulos': set(data.get('titulos', [])),
            'contenidos': set(data.get('contenidos', []))
        }
        
        print(f"   ✅ URLs guardadas: {len(historial['urls'])}")
        print(f"   ✅ IDs guardados: {len(historial['ids'])}")
        print(f"   ✅ Títulos guardados: {len(historial['titulos'])}")
        print(f"   ✅ Contenidos guardados: {len(historial['contenidos'])}")
        print(f"   🕐 Última actualización: {data.get('last_update', 'Desconocida')}")
        
        return historial
        
    except Exception as e:
        print(f"   ⚠️ Error cargando historial: {e}")
        print("   🔄 Creando historial nuevo...")
        return {'urls': set(), 'ids': set(), 'titulos': set(), 'contenidos': set()}

def guardar_historial(historial):
    """Guarda historial en archivo JSON"""
    print("\n💾 GUARDANDO HISTORIAL...")
    
    try:
        data = {
            'urls': list(historial['urls'])[-MAX_HISTORIAL:],
            'ids': list(historial['ids'])[-MAX_HISTORIAL:],
            'titulos': list(historial['titulos'])[-MAX_HISTORIAL:],
            'contenidos': list(historial['contenidos'])[-MAX_HISTORIAL:],
            'last_update': datetime.now().isoformat(),
            'total_registros': len(historial['urls'])
        }
        
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ Guardado: {len(historial['urls'])} registros totales")
        print(f"   📁 Archivo: {HISTORIAL_FILE}")
        print(f"   📊 Tamaño: {os.path.getsize(HISTORIAL_FILE)} bytes")
        
        # Verificar que se guardó correctamente
        if os.path.exists(HISTORIAL_FILE):
            print("   ✓ Archivo verificado en disco")
        else:
            print("   ❌ ERROR: Archivo no encontrado después de guardar")
            
    except Exception as e:
        print(f"   ❌ ERROR guardando: {e}")
        import traceback
        traceback.print_exc()

def ya_publicada(noticia, historial):
    """Verifica si noticia ya fue publicada por múltiples criterios"""
    url = noticia.get('url', '')
    titulo = noticia.get('title', '')
    
    # 1. Verificar URL normalizada
    url_norm = normalizar_url(url)
    if url_norm in historial['urls']:
        print(f"   ⛔ DUPLICADO (URL): {titulo[:50]}...")
        return True
    
    # 2. Verificar ID de URL
    url_id = get_url_id(url)
    if url_id in historial['ids']:
        print(f"   ⛔ DUPLICADO (ID URL): {titulo[:50]}...")
        return True
    
    # 3. Verificar título similar
    titulo_id = get_titulo_id(titulo)
    if titulo_id and titulo_id in historial['titulos']:
        print(f"   ⛔ DUPLICADO (TÍTULO): {titulo[:50]}...")
        return True
    
    # 4. Verificar contenido similar (primeras palabras de descripción)
    desc = noticia.get('description', '')
    desc_id = get_titulo_id(desc)
    if desc_id and desc_id in historial['contenidos']:
        print(f"   ⛔ DUPLICADO (CONTENIDO): {titulo[:50]}...")
        return True
    
    return False

def marcar_publicada(noticia, historial):
    """Marca noticia como publicada en todas las formas"""
    url = noticia.get('url', '')
    titulo = noticia.get('title', '')
    desc = noticia.get('description', '')
    
    historial['urls'].add(normalizar_url(url))
    historial['ids'].add(get_url_id(url))
    historial['titulos'].add(get_titulo_id(titulo))
    if desc:
        historial['contenidos'].add(get_titulo_id(desc))

# ============================================================================
# FUNCIONES DE TRADUCCIÓN Y REDACCIÓN
# ============================================================================

def traducir_deepl(texto):
    """Traduce texto usando DeepL"""
    if not DEEPL_API_KEY or not texto:
        return texto
    
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': str(texto)[:1500],
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            traduccion = response.json()['translations'][0]['text']
            print(f"   🌐 Traducido con DeepL ({len(traduccion)} chars)")
            return traduccion
    except Exception as e:
        print(f"   ⚠️ DeepL error: {e}")
    
    return texto

def redactar_openai(titulo_en, desc_en, fuente, categoria):
    """
    Genera redacción profesional en español usando OpenAI
    Retorna: (titular, cuerpo) o (None, None) si falla
    """
    
    # Primero traducimos para dar contexto en español
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    system_prompt = """Eres un periodista profesional de un medio internacional reconocido.
REGLAS ABSOLUTAS:
1. ESCRIBE ÚNICAMENTE EN ESPAÑOL (español de España o latinoamericano neutro)
2. Redacción periodística formal, objetiva y profesional
3. Mínimo 200 palabras, ideal 250-350 palabras
4. Estructura: Titular + Lead (párrafo introductorio) + 2-3 párrafos de desarrollo
5. Incluye contexto, datos relevantes e implicaciones del hecho noticioso
6. Tono: serio, informativo, autoritativo
7. NO uses frases genéricas como "según fuentes" o "se espera que"
8. Menciona la fuente de la información al final del texto"""

    user_prompt = f"""REDACTA ESTA NOTICIA EN ESPAÑOL PROFESIONAL:

DATOS DE ENTRADA:
- Título original (inglés): {titulo_en}
- Descripción original (inglés): {desc_en}
- Traducción preliminar título: {titulo_es}
- Traducción preliminar descripción: {desc_es}
- Fuente original: {fuente}
- Categoría temática: {categoria}

INSTRUCCIONES DE REDACCIÓN:
1. TITULAR: Crea un titular impactante en español (máximo 90 caracteres)
2. LEAD: Primer párrafo con los datos más importantes (quién, qué, cuándo, dónde)
3. DESARROLLO: 2-3 párrafos con contexto, antecedentes e implicaciones
4. CIERRE: Menciona explícitamente la fuente: "Información de {fuente}"

FORMATO OBLIGATORIO DE RESPUESTA:
TITULAR_FINAL: [titular en español - máx 90 caracteres]

CUERPO_NOTICIA: [texto completo en español, mínimo 200 palabras, dividido en párrafos con doble salto de línea entre ellos]

FIN_NOTICIA"""

    try:
        print("   🤖 Solicitando redacción a OpenAI...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.6,
                'max_tokens': 900,
                'top_p': 0.9
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"   ❌ OpenAI HTTP {response.status_code}: {response.text[:200]}")
            return None, None
        
        resultado = response.json()['choices'][0]['message']['content']
        
        # Parsear respuesta
        titular = None
        cuerpo_lineas = []
        en_cuerpo = False
        
        for linea in resultado.split('\n'):
            linea_stripped = linea.strip()
            
            if linea_stripped.startswith('TITULAR_FINAL:'):
                titular = linea_stripped.replace('TITULAR_FINAL:', '').strip()
                # Limpiar comillas si existen
                titular = titular.strip('"\'')
                
            elif linea_stripped.startswith('CUERPO_NOTICIA:'):
                en_cuerpo = True
                
            elif linea_stripped.startswith('FIN_NOTICIA'):
                break
                
            elif en_cuerpo and linea_stripped:
                cuerpo_lineas.append(linea_stripped)
        
        # Unir párrafos del cuerpo
        cuerpo = '\n\n'.join(cuerpo_lineas) if cuerpo_lineas else ''
        
        # Validaciones
        if not titular or not cuerpo:
            print("   ⚠️ No se pudo parsear la respuesta de OpenAI")
            print(f"   Respuesta cruda: {resultado[:400]}...")
            return None, None
        
        # Verificar que sea español
        palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'ser', 'se', 'no', 'por', 'con']
        texto_lower = cuerpo.lower()
        if not any(p in texto_lower for p in palabras_es[:5]):
            print("   ⚠️ OpenAI no generó texto en español")
            return None, None
        
        # Verificar longitud mínima
        num_palabras = len(cuerpo.split())
        if num_palabras < MIN_PALABRAS_REDACCION:
            print(f"   ⚠️ Texto muy corto: {num_palabras} palabras (mínimo {MIN_PALABRAS_REDACCION})")
            return None, None
        
        print(f"   ✅ Redacción exitosa: {num_palabras} palabras")
        print(f"   ✅ Titular: {titular[:60]}...")
        
        return titular, cuerpo
        
    except Exception as e:
        print(f"   ❌ Error en OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def generar_hashtags(categoria, titular):
    """Genera exactamente 5 hashtags relevantes"""
    
    hashtags_base = {
        'crisis': ['#ÚltimaHora', '#CrisisInternacional', '#AlertaMundial', '#NoticiasEnDesarrollo', '#Internacional'],
        'tech': ['#Tecnología', '#Innovación', '#InteligenciaArtificial', '#TechNews', '#Digital'],
        'economia': ['#EconomíaGlobal', '#MercadosFinancieros', '#Negocios', '#Finanzas', '#Inversión'],
        'politica': ['#PolíticaInternacional', '#Diplomacia', '#GobiernoGlobal', '#ActualidadPolítica', '#Mundo'],
        'internacional': ['#NoticiasMundiales', '#ActualidadInternacional', '#WorldNews', '#Global', '#Hoy']
    }
    
    # Base según categoría
    tags = hashtags_base.get(categoria, hashtags_base['internacional']).copy()
    
    # Agregar año actual
    tags.append(f"#{datetime.now().strftime('%Y')}")
    
    # Extraer palabra clave del titular para hashtag personalizado
    palabras = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{4,}\b', titular)
    if palabras:
        # Filtrar palabras muy comunes
        comunes = ['Este', 'Esta', 'Estos', 'Estas', 'Nuevo', 'Nueva', 'Gran', 'Primer']
        palabras_filtradas = [p for p in palabras if p not in comunes]
        if palabras_filtradas:
            tag_custom = '#' + palabras_filtradas[0]
            if tag_custom not in tags and len(tag_custom) > 4:
                tags.append(tag_custom)
    
    # Asegurar exactamente 5 hashtags únicos
    tags_unicos = []
    for tag in tags:
        if tag not in tags_unicos:
            tags_unicos.append(tag)
        if len(tags_unicos) >= 5:
            break
    
    return ' '.join(tags_unicos)

# ============================================================================
# FUNCIONES DE BÚSQUEDA DE NOTICIAS
# ============================================================================

def detectar_categoria(titulo, descripcion):
    """Detecta la categoría temática de la noticia"""
    texto = f"{titulo} {descripcion}".lower()
    
    if any(p in texto for p in ['war', 'attack', 'invasion', 'missile', 'bomb', 'conflict', 'crisis', 
                                'war', 'guerra', 'ataque', 'invasión', 'misil', 'bomba', 'conflicto']):
        return 'crisis'
    elif any(p in texto for p in ['tech', 'ai', 'artificial', 'software', 'digital', 'technology', 
                                  'tecnología', 'inteligencia artificial', 'software']):
        return 'tech'
    elif any(p in texto for p in ['economy', 'market', 'stock', 'financial', 'trade', 'economic', 
                                  'economía', 'mercado', 'bolsa', 'finanzas']):
        return 'economia'
    elif any(p in texto for p in ['politics', 'election', 'president', 'government', 'minister', 
                                  'política', 'elección', 'presidente', 'gobierno']):
        return 'politica'
    return 'internacional'

def buscar_newsapi():
    """Busca noticias en NewsAPI"""
    if not NEWS_API_KEY:
        return []
    
    try:
        print("   📡 Consultando NewsAPI...")
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'category': 'general',
            'language': 'en',
            'pageSize': 25,
            'apiKey': NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data.get('status') == 'ok':
            articulos = data.get('articles', [])
            print(f"   ✅ NewsAPI: {len(articulos)} artículos")
            return articulos
        else:
            print(f"   ⚠️ NewsAPI error: {data.get('message', 'Unknown')}")
            
    except Exception as e:
        print(f"   ⚠️ NewsAPI excepción: {e}")
    
    return []

def buscar_gnews():
    """Busca noticias en GNews"""
    if not GNEWS_API_KEY:
        return []
    
    try:
        print("   📡 Consultando GNews...")
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'lang': 'en',
            'max': 25,
            'apikey': GNEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if 'articles' in data:
            # Normalizar formato al de NewsAPI
            articulos = []
            for art in data['articles']:
                articulos.append({
                    'title': art.get('title', ''),
                    'description': art.get('description', ''),
                    'url': art.get('url', ''),
                    'urlToImage': art.get('image', ''),
                    'publishedAt': art.get('publishedAt', ''),
                    'source': {'name': art.get('source', {}).get('name', 'GNews')}
                })
            print(f"   ✅ GNews: {len(articulos)} artículos")
            return articulos
        else:
            print(f"   ⚠️ GNews error: {data.get('errors', data)}")
            
    except Exception as e:
        print(f"   ⚠️ GNews excepción: {e}")
    
    return []

def buscar_rss():
    """Busca noticias en feeds RSS"""
    noticias = []
    feeds = random.sample(RSS_FEEDS, min(4, len(RSS_FEEDS)))
    
    for feed_url in feeds:
        try:
            print(f"   📡 RSS: {feed_url.split('/')[2]}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:10]:
                # Extraer imagen
                imagen = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', 
                                    entry.summary, re.I)
                    if match:
                        imagen = match.group(1)
                
                noticias.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', ''))[:500],
                    'url': entry.get('link', ''),
                    'urlToImage': imagen,
                    'publishedAt': entry.get('published', datetime.now().isoformat()),
                    'source': {'name': feed.feed.get('title', 'RSS Feed')}
                })
            
        except Exception as e:
            print(f"   ⚠️ RSS error en {feed_url}: {e}")
    
    print(f"   ✅ RSS: {len(noticias)} artículos totales")
    return noticias

def buscar_noticias(historial):
    """
    Busca noticias de todas las fuentes y filtra duplicados
    """
    print(f"\n{'='*60}")
    print("🔍 FASE 1: BÚSQUEDA DE NOTICIAS")
    print(f"{'='*60}")
    
    todas = []
    
    # Recolectar de todas las fuentes
    n = buscar_newsapi()
    todas.extend(n)
    
    n = buscar_gnews()
    todas.extend(n)
    
    n = buscar_rss()
    todas.extend(n)
    
    print(f"\n📊 Total recolectado: {len(todas)} noticias")
    
    # Filtrar y deduplicar
    print(f"\n{'='*60}")
    print("🔍 FASE 2: FILTRADO Y DEDUPLICACIÓN")
    print(f"{'='*60}")
    
    validas = []
    vistos_esta_ejecucion = set()  # Para evitar duplicados intra-fuente
    
    for i, art in enumerate(todas, 1):
        # Validaciones básicas
        if not art.get('title') or len(art['title']) < 15:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url'):
            continue
        
        # Deduplicación intra-ejecución (misma noticia de diferentes fuentes)
        url_id = get_url_id(art['url'])
        if url_id in vistos_esta_ejecucion:
            continue
        vistos_esta_ejecucion.add(url_id)
        
        # Deduplicación con historial previo
        if ya_publicada(art, historial):
            continue
        
        # Detectar categoría
        categoria = detectar_categoria(art['title'], art.get('description', ''))
        
        # Agregar metadatos
        art['categoria'] = categoria
        art['url_id'] = url_id
        
        validas.append(art)
        print(f"   ✅ [{len(validas)}] {art['title'][:55]}... [{categoria}]")
    
    print(f"\n📊 Válidas únicas: {len(validas)}")
    
    # Filtrar solo con imagen
    con_imagen = [a for a in validas if a.get('urlToImage') and 
                  str(a['urlToImage']).startswith('http')]
    print(f"📊 Con imagen disponible: {len(con_imagen)}")
    
    return con_imagen[:5]

# ============================================================================
# FUNCIONES DE PUBLICACIÓN
# ============================================================================

def descargar_imagen(url):
    """Descarga y optimiza imagen para Facebook"""
    if not url or not str(url).startswith('http'):
        return None
    
    try:
        print(f"   🖼️  Descargando imagen...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"   ⚠️ HTTP {response.status_code} al descargar imagen")
            return None
        
        img = Image.open(BytesIO(response.content))
        
        # Convertir si es necesario
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Redimensionar manteniendo proporción
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        # Guardar temporal
        temp_path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:10]}.jpg'
        img.save(temp_path, 'JPEG', quality=85, optimize=True)
        
        tamaño = os.path.getsize(temp_path) / 1024
        print(f"   ✅ Imagen lista: {tamaño:.1f} KB")
        
        return temp_path
        
    except Exception as e:
        print(f"   ⚠️ Error descargando imagen: {e}")
        return None

def publicar_facebook(img_path, mensaje):
    """Publica foto con texto en Facebook"""
    if not img_path or not os.path.exists(img_path):
        print("   ❌ No hay imagen para publicar")
        return False
    
    try:
        print("   📤 Enviando a Facebook...")
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(img_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={
                    'message': mensaje,
                    'access_token': FB_ACCESS_TOKEN
                },
                timeout=60
            )
        
        result = response.json()
        
        if response.status_code == 200 and 'id' in result:
            post_id = result['id']
            print(f"   ✅ PUBLICADO EXITOSAMENTE")
            print(f"   📎 ID del post: {post_id}")
            return True
        else:
            error_msg = result.get('error', {}).get('message', str(result))
            print(f"   ❌ Error de Facebook: {error_msg}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error publicando: {e}")
        return False

def crear_mensaje_final(noticia):
    """
    Crea el mensaje final con redacción profesional
    """
    print(f"\n✍️  FASE 3: REDACCIÓN PROFESIONAL")
    
    titulo_orig = noticia['title']
    desc_orig = noticia.get('description', '')
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    categoria = noticia['categoria']
    
    print(f"   📝 Original: {titulo_orig[:60]}...")
    
    # Intentar redacción con OpenAI
    titular, cuerpo = redactar_openai(titulo_orig, desc_orig, fuente, categoria)
    
    # Fallback si OpenAI falla
    if not titular or not cuerpo:
        print("   ⚠️ Usando traducción básica (fallback)...")
        titular = traducir_deepl(titulo_orig)
        cuerpo = traducir_deepl(desc_orig)
        cuerpo += f"\n\n📡 Información proporcionada por {fuente}."
    
    # Generar hashtags
    hashtags = generar_hashtags(categoria, titular)
    print(f"   #️⃣  Hashtags: {hashtags}")
    
    # Ensamblar mensaje final
    mensaje = f"""📰 {titular}

{cuerpo}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    print(f"   📊 Longitud total: {len(mensaje)} caracteres")
    
    return mensaje

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Función principal del bot
    """
    print("="*60)
    print("🚀 BOT DE NOTICIAS - VERDAD HOY")
    print("="*60)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 Configuración:")
    print(f"   • NEWS_API_KEY: {'✅' if NEWS_API_KEY else '❌'}")
    print(f"   • GNEWS_API_KEY: {'✅' if GNEWS_API_KEY else '❌'}")
    print(f"   • OPENAI_API_KEY: {'✅' if OPENAI_API_KEY else '❌'}")
    print(f"   • FB_PAGE_ID: {'✅' if FB_PAGE_ID else '❌'}")
    print(f"   • FB_ACCESS_TOKEN: {'✅' if FB_ACCESS_TOKEN else '❌'}")
    print(f"   • DEEPL_API_KEY: {'✅' if DEEPL_API_KEY else '❌'}")
    
    # Validar configuración mínima
    if not all([FB_PAGE_ID, FB_ACCESS_TOKEN]):
        print("\n❌ ERROR: Faltan credenciales de Facebook obligatorias")
        return False
    
    if not OPENAI_API_KEY:
        print("\n❌ ERROR: OPENAI_API_KEY es obligatorio para la redacción")
        return False
    
    # Cargar historial
    historial = cargar_historial()
    
    # Buscar noticias
    noticias = buscar_noticias(historial)
    
    if not noticias:
        print(f"\n{'='*60}")
        print("⚠️ No se encontraron noticias nuevas para publicar")
        print(f"{'='*60}")
        guardar_historial(historial)
        return False
    
    print(f"\n🎯 FASE 4: INTENTO DE PUBLICACIÓN")
    print(f"   {len(noticias)} noticia(s) en cola")
    
    # Intentar publicar cada noticia hasta lograrlo
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 INTENTO {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Saltando: no se pudo obtener imagen")
            continue
        
        # Crear mensaje con redacción profesional
        mensaje = crear_mensaje_final(noticia)
        
        # Mostrar preview
        print(f"\n   📝 PREVIEW:")
        print(f"   {'-'*50}")
        preview = mensaje[:200] + "..." if len(mensaje) > 200 else mensaje
        for linea in preview.split('\n')[:5]:
            print(f"   {linea}")
        print(f"   {'-'*50}")
        
        # Publicar
        exito = publicar_facebook(img_path, mensaje)
        
        # Limpiar imagen temporal
        if os.path.exists(img_path):
            os.remove(img_path)
            print(f"   🗑️  Imagen temporal eliminada")
        
        if exito:
            # Marcar como publicada y guardar
            marcar_publicada(noticia, historial)
            guardar_historial(historial)
            
            print(f"\n{'='*60}")
            print("✅ ÉXITO: Noticia publicada y registrada")
            print(f"{'='*60}")
            print(f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        
        print(f"   ⏭️ Falló, intentando siguiente noticia...")
    
    # Si llegamos aquí, ninguna noticia se publicó
    print(f"\n{'='*60}")
    print("❌ No se pudo publicar ninguna noticia")
    print(f"{'='*60}")
    
    # Guardar historial igual (por si se encontraron nuevas URLs)
    guardar_historial(historial)
    
    print(f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return False

if __name__ == "__main__":
    try:
        resultado = main()
        exit_code = 0 if resultado else 1
        print(f"\n🏁 Exit code: {exit_code}")
        exit(exit_code)
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"💥 ERROR CRÍTICO NO MANEJADO")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
