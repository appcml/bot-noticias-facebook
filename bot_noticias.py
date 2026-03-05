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

# APIs de noticias
NEWS_API_KEY = os.getenv('NEWS_API_KEY')      # NewsAPI (casi agotado)
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')    # GNews (nuevo respaldo)
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"🔍 NEWS_API_KEY: {bool(NEWS_API_KEY)} | GNEWS_API_KEY: {bool(GNEWS_API_KEY)}")
print(f"🔍 FB_PAGE_ID: {bool(FB_PAGE_ID)} | FB_ACCESS_TOKEN: {bool(FB_ACCESS_TOKEN)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN]):
    raise ValueError("❌ Faltan credenciales de Facebook")
if not NEWS_API_KEY and not GNEWS_API_KEY:
    print("⚠️ Sin APIs de noticias configuradas, usando solo RSS")

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000

# RSS Feeds gratuitos (ILIMITADOS)
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
            print(f"⚠️ Error cargando historial: {e}")
    print("📚 Nuevo historial creado")
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

def traducir_texto(texto, idioma='EN'):
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
        print(f"⚠️ Error traducción: {e}")
    return texto

def buscar_newsapi():
    """NewsAPI - puede fallar por límite de requests"""
    if not NEWS_API_KEY:
        return []
    try:
        print("\n📡 Intentando NewsAPI...")
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
            print(f"✅ NewsAPI: {len(data.get('articles', []))} artículos")
            return data.get('articles', [])
        else:
            print(f"⚠️ NewsAPI: {data.get('message', 'Error')}")
            return []
    except Exception as e:
        print(f"⚠️ NewsAPI falló: {e}")
        return []

def buscar_gnews():
    """GNews - plan gratuito 100 req/día"""
    if not GNEWS_API_KEY:
        return []
    try:
        print("\n📡 Intentando GNews...")
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'lang': 'en',
            'max': 20,
            'apikey': GNEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'articles' in data:
            print(f"✅ GNews: {len(data['articles'])} artículos")
            # Normalizar formato al de NewsAPI
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
        else:
            print(f"⚠️ GNews: {data.get('errors', data)}")
            return []
    except Exception as e:
        print(f"⚠️ GNews falló: {e}")
        return []

def buscar_rss():
    """RSS Feeds - ILIMITADO"""
    noticias = []
    feeds = random.sample(RSS_FEEDS, min(3, len(RSS_FEEDS)))
    
    for feed_url in feeds:
        try:
            print(f"\n📡 RSS: {feed_url.split('/')[2]}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:8]:
                # Buscar imagen en el contenido
                imagen = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    # Extraer imagen del HTML summary
                    import re
                    img_match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', entry.summary, re.I)
                    if img_match:
                        imagen = img_match.group(1)
                
                noticia = {
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', ''))[:300],
                    'url': entry.get('link', ''),
                    'urlToImage': imagen,
                    'publishedAt': entry.get('published', datetime.now().isoformat()),
                    'source': {'name': feed.feed.get('title', 'RSS Feed')}
                }
                noticias.append(noticia)
            
            print(f"   ✅ {len(feed.entries[:8])} artículos")
        except Exception as e:
            print(f"   ⚠️ Error RSS: {e}")
    
    return noticias

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"🔍 BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    todas_noticias = []
    
    # 1. Intentar NewsAPI primero (si tiene requests disponibles)
    noticias = buscar_newsapi()
    todas_noticias.extend(noticias)
    
    # 2. Si NewsAPI falló o devolvió poco, usar GNews
    if len(todas_noticias) < 5:
        noticias = buscar_gnews()
        todas_noticias.extend(noticias)
    
    # 3. Si ambos fallaron, usar RSS (siempre funciona)
    if len(todas_noticias) < 3:
        print("\n📡 Usando RSS como respaldo final...")
        noticias = buscar_rss()
        todas_noticias.extend(noticias)
    
    print(f"\n📊 Total recopilado: {len(todas_noticias)} noticias")
    
    # Filtrar válidas y no duplicadas
    noticias_validas = []
    for art in todas_noticias:
        if not es_valida(art):
            continue
        
        url_norm = normalizar_url(art['url'])
        url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
        
        if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
            print(f"⏭️  Ya publicada: {art['title'][:40]}...")
            continue
        
        # Agregar metadatos
        art['url_normalizada'] = url_norm
        art['url_hash'] = url_hash
        art['score'] = calcular_score(art)
        art['categoria'] = detectar_categoria(art)
        art['idioma'] = 'EN'
        
        # Traducir
        art['title'] = traducir_texto(art['title'])
        art['description'] = traducir_texto(art['description'])
        
        noticias_validas.append(art)
        print(f"✅ Nueva: {art['title'][:50]}... (score: {art['score']})")
    
    print(f"📊 Válidas y nuevas: {len(noticias_validas)}")
    
    # Filtrar con imagen
    con_imagen = [n for n in noticias_validas if n.get('urlToImage') and str(n['urlToImage']).startswith('http')]
    print(f"📊 Con imagen: {len(con_imagen)}")
    
    # Ordenar por score
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
    fuente = str(art.get('source', {}).get('name', '')).lower()
    
    if any(p in texto for p in ['war', 'attack', 'invasion', 'missile', 'bomb', 'conflict']):
        return 'crisis'
    elif any(p in texto for p in ['tech', 'ai', 'artificial intelligence', 'software', 'app']):
        return 'tech'
    elif any(p in texto for p in ['economy', 'market', 'stock', 'inflation', 'trade']):
        return 'economia'
    elif any(p in texto for p in ['election', 'president', 'politics', 'government', 'vote']):
        return 'politica'
    else:
        return 'internacional'

def calcular_score(art):
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    palabras = {
        'breaking': 40, 'urgent': 35, 'alert': 30,
        'trump': 30, 'biden': 25, 'putin': 30,
        'war': 35, 'attack': 35, 'invasion': 35,
        'crash': 30, 'crisis': 25, 'emergency': 25,
        'dead': 30, 'killed': 35, 'dies': 30,
        'earthquake': 30, 'tsunami': 35,
        'ai': 25, 'artificial intelligence': 30,
        'market': 20, 'economy': 20, 'stock': 20
    }
    
    for palabra, puntos in palabras.items():
        if palabra in texto:
            score += puntos
    
    # Bonus recencia
    try:
        fecha = art.get('publishedAt', '')
        if fecha:
            fecha_art = datetime.fromisoformat(str(fecha).replace('Z', '+00:00'))
            horas = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            if horas < 2: score += 40
            elif horas < 6: score += 30
            elif horas < 12: score += 20
            elif horas < 24: score += 10
    except:
        pass
    
    if art.get('urlToImage'):
        score += 15
    
    return score

def descargar_imagen(url_imagen):
    if not url_imagen or not str(url_imagen).startswith('http'):
        return None
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url_imagen, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            temp_path = f'/tmp/noticia_{hashlib.md5(str(url_imagen).encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85, optimize=True)
            print(f"🖼️  Imagen: {os.path.getsize(temp_path)/1024:.1f} KB")
            return temp_path
    except Exception as e:
        print(f"⚠️ Error imagen: {e}")
    return None

def publicar_facebook(image_path, mensaje):
    if not image_path or not os.path.exists(image_path):
        print("❌ Sin imagen")
        return False
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN}
            print(f"📤 Publicando...")
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO: {result['id']}")
                return True
            else:
                print(f"❌ Facebook error: {result.get('error', {}).get('message', result)}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def generar_mensaje(noticia):
    titulo = noticia.get('title', 'Noticia Internacional')
    desc = noticia.get('description', '')[:280]
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    categoria = noticia.get('categoria', 'internacional')
    
    hashtags = f"#NoticiasMundiales #{categoria.capitalize()} #{datetime.now().strftime('%Y')}"
    
    return f"""📰 {titulo}

{desc}

📡 Fuente: {fuente}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""

def main():
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("🚀 INICIANDO BOT DE NOTICIAS")
    print("="*60)
    
    noticias = buscar_noticias_frescas()
    
    if not noticias:
        print("⚠️ No hay noticias disponibles")
        guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
        return False
    
    print(f"\n🎯 {len(noticias)} candidata(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"Intento {i}/{len(noticias)}: {noticia['title'][:50]}...")
        
        if not noticia.get('urlToImage'):
            print("⏭️ Sin imagen")
            continue
        
        img_path = descargar_imagen(noticia['urlToImage'])
        if not img_path:
            print("⏭️ Error imagen")
            continue
        
        mensaje = generar_mensaje(noticia)
        exito = publicar_facebook(img_path, mensaje)
        
        if os.path.exists(img_path):
            os.remove(img_path)
        
        if exito:
            HISTORIAL_URLS.add(noticia['url_normalizada'])
            HISTORIAL_HASHES.add(noticia['url_hash'])
            guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
            print("\n✅ ÉXITO TOTAL")
            return True
    
    print("\n❌ Ninguna noticia pudo publicarse")
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
