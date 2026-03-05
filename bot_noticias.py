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

# APIs
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # NUEVO: OpenAI
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"🔍 NEWS_API_KEY: {bool(NEWS_API_KEY)} | GNEWS_API_KEY: {bool(GNEWS_API_KEY)} | OPENAI: {bool(OPENAI_API_KEY)}")
print(f"🔍 FB: {bool(FB_PAGE_ID and FB_ACCESS_TOKEN)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN]):
    raise ValueError("❌ Faltan credenciales de Facebook")
if not OPENAI_API_KEY:
    print("⚠️ Sin OpenAI - se usará redacción básica")

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000

# RSS Feeds ILIMITADOS
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

def normalizar_url(url):
    if not url:
        return ""
    url, _ = urldefrag(url)
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url_limpia = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, nuevo_query, ''
        ))
        return url_limpia.lower().strip().rstrip('/')
    except:
        return url.lower().strip().rstrip('/')

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                urls = set(data.get('urls', []))
                hashes = set(data.get('hashes', []))
                print(f"📚 Historial: {len(urls)} URLs guardadas")
                return urls, hashes
        except Exception as e:
            print(f"⚠️ Error historial: {e}")
    print("📚 Nuevo historial")
    return set(), set()

def guardar_historial(urls, hashes):
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': list(hashes)[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat()
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Historial guardado: {len(urls)} URLs")

HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_deepl(texto, idioma='EN'):
    """Traduce usando DeepL si está disponible"""
    if not DEEPL_API_KEY or idioma != 'EN' or not texto:
        return texto
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto[:1000],
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"⚠️ DeepL error: {e}")
    return texto

def redactar_con_openai(titulo, descripcion, fuente, categoria):
    """Usa GPT-4o-mini para redactar la noticia en español profesional"""
    if not OPENAI_API_KEY:
        return None
    
    try:
        prompt = f"""Eres un redactor de noticias profesional. Redacta esta noticia en ESPAÑOL para publicar en Facebook.

DATOS:
- Título original: {titulo}
- Descripción: {descripcion}
- Fuente: {fuente}
- Categoría: {categoria}

INSTRUCCIONES:
1. Escribe en español fluido y profesional
2. Crea un titular llamativo (máx 100 caracteres)
3. Redacta 2-3 párrafos informativos (150-200 palabras total)
4. Tono: periodístico, objetivo, atractivo
5. NO uses frases genéricas como "según fuentes" o "se espera que"
6. Incluye el nombre de la fuente al final

FORMATO DE RESPUESTA:
TITULAR: [titular en español]

CUERPO: [texto redactado en español]

FUENTE: {fuente}"""

        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': 'Eres un periodista experto que redacta noticias en español.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 500
        }
        
        print("🤖 Solicitando redacción a OpenAI...")
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            resultado = response.json()['choices'][0]['message']['content']
            print("✅ Redacción OpenAI recibida")
            return resultado
        else:
            print(f"⚠️ OpenAI error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"⚠️ Error OpenAI: {e}")
        return None

def generar_hashtags(categoria, titulo):
    """Genera exactamente 5 hashtags relevantes"""
    base_tags = {
        'crisis': ['#ÚltimaHora', '#CrisisInternacional', '#AlertaMundial', '#NoticiasEnDesarrollo', '#Actualidad'],
        'tech': ['#Tecnología', '#Innovación', '#TechNews', '#FuturoDigital', '#IA'],
        'economia': ['#Economía', '#Mercados', '#Finanzas', '#Negocios', '#GlobalEconomy'],
        'politica': ['#Política', '#Internacional', '#Diplomacia', '#Gobierno', '#ActualidadPolítica'],
        'internacional': ['#NoticiasMundiales', '#Internacional', '#WorldNews', '#ActualidadGlobal', '#HoyEnElMundo']
    }
    
    tags = base_tags.get(categoria, base_tags['internacional']).copy()
    
    # Agregar hashtag del año siempre
    tags.append(f"#{datetime.now().strftime('%Y')}")
    
    # Extraer palabras clave del título para hashtag personalizado
    palabras = re.findall(r'\b[A-Z][a-z]{4,}\b', titulo)
    if palabras:
        tag_custom = '#' + palabras[0]
        if tag_custom not in tags:
            tags.append(tag_custom)
    
    # Seleccionar 5 únicos
    return ' '.join(list(dict.fromkeys(tags))[:5])

def buscar_newsapi():
    if not NEWS_API_KEY:
        return []
    try:
        print("\n📡 NewsAPI...")
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'category': 'general',
            'language': 'en',
            'pageSize': 20,
            'apiKey': NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get('status') == 'ok':
            print(f"✅ NewsAPI: {len(data.get('articles', []))}")
            return data.get('articles', [])
        return []
    except Exception as e:
        print(f"⚠️ NewsAPI: {e}")
        return []

def buscar_gnews():
    if not GNEWS_API_KEY:
        return []
    try:
        print("\n📡 GNews...")
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'lang': 'en',
            'max': 20,
            'apikey': GNEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if 'articles' in data:
            print(f"✅ GNews: {len(data['articles'])}")
            articulos = []
            for art in data['articles']:
                articulos.append({
                    'title': art.get('title', ''),
                    'description': art.get('description', ''),
                    'url': art.get('url', ''),
                    'urlToImage': art.get('image', ''),
                    'publishedAt': art.get('publishedAt', datetime.now().isoformat()),
                    'source': {'name': art.get('source', {}).get('name', 'GNews')}
                })
            return articulos
        return []
    except Exception as e:
        print(f"⚠️ GNews: {e}")
        return []

def buscar_rss():
    noticias = []
    feeds = random.sample(RSS_FEEDS, min(3, len(RSS_FEEDS)))
    
    for feed_url in feeds:
        try:
            print(f"\n📡 RSS: {feed_url.split('/')[2]}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:8]:
                imagen = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    img_match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', entry.summary, re.I)
                    if img_match:
                        imagen = img_match.group(1)
                
                noticias.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', ''))[:300],
                    'url': entry.get('link', ''),
                    'urlToImage': imagen,
                    'publishedAt': entry.get('published', datetime.now().isoformat()),
                    'source': {'name': feed.feed.get('title', 'RSS')}
                })
        except Exception as e:
            print(f"⚠️ RSS error: {e}")
    
    return noticias

def buscar_noticias():
    print(f"\n{'='*60}")
    print(f"🔍 BUSCANDO - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    todas = []
    
    # Intentar fuentes en orden
    noticias = buscar_newsapi()
    todas.extend(noticias)
    
    if len(todas) < 5:
        noticias = buscar_gnews()
        todas.extend(noticias)
    
    if len(todas) < 3:
        print("\n📡 Usando RSS...")
        noticias = buscar_rss()
        todas.extend(noticias)
    
    print(f"\n📊 Total: {len(todas)} noticias")
    
    # Procesar
    validas = []
    for art in todas:
        if not es_valida(art):
            continue
        
        url_norm = normalizar_url(art['url'])
        url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
        
        if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
            print(f"⏭️  Ya publicada: {art['title'][:40]}")
            continue
        
        # Traducir primero con DeepL
        titulo_es = traducir_deepl(art.get('title', ''), 'EN')
        desc_es = traducir_deepl(art.get('description', ''), 'EN')
        
        art['title_original'] = art.get('title', '')
        art['description_original'] = art.get('description', '')
        art['title'] = titulo_es
        art['description'] = desc_es
        art['url_normalizada'] = url_norm
        art['url_hash'] = url_hash
        art['categoria'] = detectar_categoria(art)
        art['score'] = calcular_score(art)
        
        validas.append(art)
        print(f"✅ Nueva: {titulo_es[:50]}...")
    
    print(f"📊 Válidas: {len(validas)}")
    
    # Filtrar con imagen
    con_imagen = [n for n in validas if n.get('urlToImage') and str(n['urlToImage']).startswith('http')]
    print(f"📊 Con imagen: {len(con_imagen)}")
    
    con_imagen.sort(key=lambda x: x['score'], reverse=True)
    return con_imagen[:5]

def es_valida(art):
    if not art or not isinstance(art, dict):
        return False
    title = str(art.get('title', ''))
    if not title or "[Removed]" in title or len(title) < 10:
        return False
    desc = str(art.get('description', ''))
    if not desc or len(desc) < 30:
        return False
    url = str(art.get('url', ''))
    if not url or not url.startswith('http'):
        return False
    return True

def detectar_categoria(art):
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    if any(p in texto for p in ['war', 'attack', 'invasion', 'missile', 'bomb', 'conflict', 'crisis']):
        return 'crisis'
    elif any(p in texto for p in ['tech', 'ai', 'artificial intelligence', 'software', 'app', 'digital']):
        return 'tech'
    elif any(p in texto for p in ['economy', 'market', 'stock', 'inflation', 'trade', 'financial']):
        return 'economia'
    elif any(p in texto for p in ['election', 'president', 'politics', 'government', 'vote', 'minister']):
        return 'politica'
    return 'internacional'

def calcular_score(art):
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    palabras = {
        'breaking': 40, 'urgent': 35, 'alert': 30,
        'trump': 30, 'biden': 25, 'putin': 30,
        'war': 35, 'attack': 35, 'invasion': 35,
        'crash': 30, 'crisis': 25,
        'dead': 30, 'killed': 35,
        'ai': 25, 'artificial intelligence': 30,
        'market': 20, 'economy': 20
    }
    
    for palabra, puntos in palabras.items():
        if palabra in texto:
            score += puntos
    
    # Recencia
    try:
        fecha = art.get('publishedAt', '')
        if fecha:
            fecha_art = datetime.fromisoformat(str(fecha).replace('Z', '+00:00'))
            horas = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            if horas < 2: score += 40
            elif horas < 6: score += 30
            elif horas < 12: score += 20
    except:
        pass
    
    if art.get('urlToImage'):
        score += 15
    
    return score

def descargar_imagen(url):
    if not url or not str(url).startswith('http'):
        return None
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            temp_path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85, optimize=True)
            print(f"🖼️  Imagen: {os.path.getsize(temp_path)/1024:.1f} KB")
            return temp_path
    except Exception as e:
        print(f"⚠️ Imagen error: {e}")
    return None

def publicar_facebook(image_path, mensaje):
    if not image_path or not os.path.exists(image_path):
        return False
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN}
            print("📤 Publicando...")
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO: {result['id']}")
                return True
            else:
                print(f"❌ FB error: {result.get('error', {}).get('message', result)}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def crear_publicacion(noticia):
    """Crea el mensaje final con OpenAI o fallback"""
    titulo = noticia['title']
    descripcion = noticia['description']
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    categoria = noticia['categoria']
    
    # Intentar redacción con OpenAI
    redaccion_openai = redactar_con_openai(titulo, descripcion, fuente, categoria)
    
    if redaccion_openai:
        # Parsear respuesta de OpenAI
        try:
            lines = redaccion_openai.split('\n')
            titular = ''
            cuerpo = ''
            en_cuerpo = False
            
            for line in lines:
                if line.startswith('TITULAR:'):
                    titular = line.replace('TITULAR:', '').strip()
                elif line.startswith('CUERPO:'):
                    en_cuerpo = True
                elif en_cuerpo and line.strip():
                    cuerpo += line + '\n'
            
            if titular and cuerpo:
                mensaje = f"📰 {titular}\n\n{cuerpo.strip()}"
            else:
                # Si no se parseó bien, usar todo
                mensaje = f"📰 {titulo}\n\n{redaccion_openai}"
        except:
            mensaje = f"📰 {titulo}\n\n{redaccion_openai}"
    else:
        # Fallback: usar traducción DeepL directa
        mensaje = f"""📰 {titulo}

{descripcion}

📡 Fuente: {fuente}"""
    
    # Agregar hashtags (exactamente 5)
    hashtags = generar_hashtags(categoria, titulo)
    
    mensaje_final = f"""{mensaje}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    return mensaje_final

def main():
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("🚀 BOT DE NOTICIAS - Modo OpenAI + Español")
    print("="*60)
    
    noticias = buscar_noticias()
    
    if not noticias:
        print("⚠️ Sin noticias")
        guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
        return False
    
    print(f"\n🎯 {len(noticias)} candidatas")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"Intento {i}/{len(noticias)}")
        print(f"Título: {noticia['title'][:60]}")
        
        if not noticia.get('urlToImage'):
            print("⏭️ Sin imagen")
            continue
        
        # Descargar imagen
        img_path = descargar_imagen(noticia['urlToImage'])
        if not img_path:
            print("⏭️ Error imagen")
            continue
        
        # Crear publicación con OpenAI
        mensaje = crear_publicacion(noticia)
        print(f"\n📝 Mensaje ({len(mensaje)} chars):")
        print(mensaje[:200] + "..." if len(mensaje) > 200 else mensaje)
        
        # Publicar
        exito = publicar_facebook(img_path, mensaje)
        
        # Limpiar
        if os.path.exists(img_path):
            os.remove(img_path)
        
        if exito:
            # Guardar en historial
            HISTORIAL_URLS.add(noticia['url_normalizada'])
            HISTORIAL_HASHES.add(noticia['url_hash'])
            guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
            print("\n✅ ÉXITO - Noticia publicada")
            return True
    
    print("\n❌ Falló todo")
    guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

