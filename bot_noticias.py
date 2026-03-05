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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"🔍 Configuración:")
print(f"   NEWS_API_KEY: {bool(NEWS_API_KEY)}")
print(f"   GNEWS_API_KEY: {bool(GNEWS_API_KEY)}")
print(f"   OPENAI_API_KEY: {bool(OPENAI_API_KEY)}")
print(f"   FB_PAGE_ID: {bool(FB_PAGE_ID)}")
print(f"   FB_ACCESS_TOKEN: {bool(FB_ACCESS_TOKEN)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN]):
    raise ValueError("❌ Faltan credenciales de Facebook")

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000

RSS_FEEDS = [
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.reuters.com/rssFeed/worldNews',
    'https://feeds.npr.org/1001/rss.xml',
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.politico.com/politics/news.xml',
    'https://rss.cnn.com/rss/edition_world.rss',
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
                print(f"📚 Historial cargado: {len(urls)} URLs")
                return urls, hashes
        except:
            pass
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

def traducir_deepl(texto):
    if not DEEPL_API_KEY or not texto:
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
    except:
        pass
    return texto

def redactar_openai(titulo, descripcion, fuente, categoria):
    if not OPENAI_API_KEY:
        return None
    
    prompt = f"""Redacta esta noticia en ESPAÑOL profesional para Facebook.

DATOS:
- Título: {titulo}
- Descripción: {descripcion}
- Fuente: {fuente}
- Categoría: {categoria}

REGLAS:
1. Español fluido y profesional
2. Titular llamativo (máx 100 caracteres)
3. 2-3 párrafos, 150-200 palabras totales
4. Tono periodístico objetivo
5. NO uses "según fuentes" genérico
6. Menciona la fuente al final

FORMATO:
TITULAR: [titular]

CUERPO: [texto redactado]

FUENTE: {fuente}"""

    try:
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': 'Eres un periodista experto.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 600
        }
        
        print("🤖 OpenAI redactando...")
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"⚠️ OpenAI error: {e}")
    return None

def generar_5_hashtags(categoria, titulo):
    tags_base = {
        'crisis': ['#ÚltimaHora', '#CrisisInternacional', '#AlertaMundial', '#NoticiasEnDesarrollo', '#Actualidad'],
        'tech': ['#Tecnología', '#Innovación', '#TechNews', '#InteligenciaArtificial', '#FuturoDigital'],
        'economia': ['#Economía', '#MercadosGlobales', '#Finanzas', '#NegociosInternacionales', '#Inversión'],
        'politica': ['#PolíticaInternacional', '#Diplomacia', '#GobiernoGlobal', '#ActualidadPolítica', '#Mundo'],
        'internacional': ['#NoticiasMundiales', '#Internacional', '#WorldNews', '#ActualidadGlobal', '#HoyEnElMundo']
    }
    
    tags = tags_base.get(categoria, tags_base['internacional']).copy()
    
    # Agregar hashtag del año
    tags.append(f"#{datetime.now().strftime('%Y')}")
    
    # Extraer palabra clave del título
    palabras = re.findall(r'\b[A-Z][a-z]{4,}\b', titulo)
    if palabras:
        tag = '#' + palabras[0]
        if tag not in tags:
            tags.append(tag)
    
    # Seleccionar 5 únicos
    return ' '.join(list(dict.fromkeys(tags))[:5])

def buscar_newsapi():
    if not NEWS_API_KEY:
        return []
    try:
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
            return data.get('articles', [])
    except:
        pass
    return []

def buscar_gnews():
    if not GNEWS_API_KEY:
        return []
    try:
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'lang': 'en',
            'max': 20,
            'apikey': GNEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if 'articles' in data:
            return [{
                'title': a.get('title', ''),
                'description': a.get('description', ''),
                'url': a.get('url', ''),
                'urlToImage': a.get('image', ''),
                'publishedAt': a.get('publishedAt', ''),
                'source': {'name': a.get('source', {}).get('name', 'GNews')}
            } for a in data['articles']]
    except:
        pass
    return []

def buscar_rss():
    noticias = []
    feeds = random.sample(RSS_FEEDS, min(3, len(RSS_FEEDS)))
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                imagen = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', entry.summary, re.I)
                    if match:
                        imagen = match.group(1)
                
                noticias.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', ''))[:300],
                    'url': entry.get('link', ''),
                    'urlToImage': imagen,
                    'publishedAt': entry.get('published', ''),
                    'source': {'name': feed.feed.get('title', 'RSS')}
                })
        except:
            pass
    return noticias

def buscar_noticias():
    print(f"\n{'='*60}")
    print(f"🔍 BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    todas = []
    
    noticias = buscar_newsapi()
    todas.extend(noticias)
    print(f"📡 NewsAPI: {len(noticias)}")
    
    if len(todas) < 5:
        noticias = buscar_gnews()
        todas.extend(noticias)
        print(f"📡 GNews: {len(noticias)}")
    
    if len(todas) < 3:
        noticias = buscar_rss()
        todas.extend(noticias)
        print(f"📡 RSS: {len(noticias)}")
    
    print(f"\n📊 Total: {len(todas)}")
    
    validas = []
    for art in todas:
        if not art.get('title') or "[Removed]" in art['title'] or len(art.get('title', '')) < 10:
            continue
        if not art.get('description') or len(art.get('description', '')) < 30:
            continue
        if not art.get('url') or not art['url'].startswith('http'):
            continue
        
        url_norm = normalizar_url(art['url'])
        url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
        
        if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
            print(f"⏭️  Ya publicada: {art['title'][:40]}")
            continue
        
        # Traducir
        titulo_es = traducir_deepl(art['title'])
        desc_es = traducir_deepl(art['description'])
        
        # Detectar categoría
        texto = f"{titulo_es} {desc_es}".lower()
        if any(p in texto for p in ['guerra', 'ataque', 'crisis', 'conflicto', 'bomba']):
            categoria = 'crisis'
        elif any(p in texto for p in ['tecnología', 'inteligencia artificial', 'software', 'digital', 'app']):
            categoria = 'tech'
        elif any(p in texto for p in ['economía', 'mercado', 'finanzas', 'dinero', 'bolsa']):
            categoria = 'economia'
        elif any(p in texto for p in ['política', 'gobierno', 'presidente', 'elección', 'ministro']):
            categoria = 'politica'
        else:
            categoria = 'internacional'
        
        art.update({
            'title': titulo_es,
            'description': desc_es,
            'url_normalizada': url_norm,
            'url_hash': url_hash,
            'categoria': categoria
        })
        
        validas.append(art)
        print(f"✅ Nueva: {titulo_es[:50]}...")
    
    print(f"📊 Válidas: {len(validas)}")
    
    con_imagen = [n for n in validas if n.get('urlToImage') and str(n['urlToImage']).startswith('http')]
    print(f"📊 Con imagen: {len(con_imagen)}")
    
    return con_imagen[:5]

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
            print("📤 Publicando en Facebook...")
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

def crear_mensaje(noticia):
    titulo = noticia['title']
    descripcion = noticia['description']
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    categoria = noticia['categoria']
    
    # Intentar redacción con OpenAI
    redaccion = redactar_openai(titulo, descripcion, fuente, categoria)
    
    if redaccion:
        # Extraer partes
        titular = titulo
        cuerpo = descripcion
        
        for linea in redaccion.split('\n'):
            if linea.startswith('TITULAR:'):
                titular = linea.replace('TITULAR:', '').strip()
            elif linea.startswith('CUERPO:'):
                continue
            elif not linea.startswith('FUENTE:') and linea.strip():
                cuerpo = linea.strip()
        
        mensaje = f"📰 {titular}\n\n{cuerpo}"
    else:
        # Fallback
        mensaje = f"📰 {titulo}\n\n{descripcion}\n\n📡 Fuente: {fuente}"
    
    # 5 hashtags
    hashtags = generar_5_hashtags(categoria, titulo)
    
    return f"""{mensaje}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""

def main():
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("🚀 BOT DE NOTICIAS - Español + OpenAI + 5 Hashtags")
    print("="*60)
    
    noticias = buscar_noticias()
    
    if not noticias:
        print("⚠️ Sin noticias disponibles")
        guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
        return False
    
    print(f"\n🎯 {len(noticias)} candidatas")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"Intento {i}/{len(noticias)}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("⏭️ Sin imagen")
            continue
        
        mensaje = crear_mensaje(noticia)
        print(f"\n📝 Preview:\n{mensaje[:150]}...")
        
        if publicar_facebook(img_path, mensaje):
            if os.path.exists(img_path):
                os.remove(img_path)
            
            HISTORIAL_URLS.add(noticia['url_normalizada'])
            HISTORIAL_HASHES.add(noticia['url_hash'])
            guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
            print("\n✅ ÉXITO")
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
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
