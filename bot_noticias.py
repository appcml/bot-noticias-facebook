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

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print("="*60)
print(f"🔍 NEWS_API_KEY: {'✅' if NEWS_API_KEY else '❌'}")
print(f"🔍 GNEWS_API_KEY: {'✅' if GNEWS_API_KEY else '❌'}")
print(f"🔍 OPENAI_API_KEY: {'✅' if OPENAI_API_KEY else '❌'}")
print(f"🔍 FB_PAGE_ID: {'✅' if FB_PAGE_ID else '❌'}")
print(f"🔍 FB_ACCESS_TOKEN: {'✅' if FB_ACCESS_TOKEN else '❌'}")
print(f"🔍 DEEPL_API_KEY: {'✅' if DEEPL_API_KEY else '❌'}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN]):
    raise ValueError("❌ Faltan credenciales de Facebook")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY es obligatorio")

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 2000  # Más grande para evitar pérdidas

RSS_FEEDS = [
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.reuters.com/rssFeed/worldNews',
    'https://feeds.npr.org/1001/rss.xml',
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.politico.com/politics/news.xml',
    'https://rss.cnn.com/rss/edition_world.rss',
    'https://feeds.huffpost.com/HuffPostWorld',
    'https://feeds.afr.com/rss/afr_markets.xml',
    'https://www.ft.com/?format=rss',
]

def normalizar_url(url):
    """Limpia URL para comparación"""
    if not url:
        return ""
    url = str(url).lower().strip()
    url, _ = urldefrag(url)
    
    # Quitar parámetros de tracking
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source', 'campaign', 'medium']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, nuevo_query, ''
        ))
    except:
        pass
    
    return url.rstrip('/')

def get_url_id(url):
    """Genera ID único para URL"""
    norm = normalizar_url(url)
    return hashlib.md5(norm.encode()).hexdigest()[:16]

def cargar_historial():
    """Carga historial con validación"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                urls = set(data.get('urls', []))
                ids = set(data.get('ids', []))
                titulos = set(data.get('titulos', []))  # Nuevo: guardar títulos también
                print(f"📚 Historial cargado: {len(urls)} URLs, {len(ids)} IDs, {len(titulos)} títulos")
                return urls, ids, titulos
        except Exception as e:
            print(f"⚠️ Error cargando historial: {e}")
    
    print("📚 Nuevo historial (primera ejecución o archivo corrupto)")
    return set(), set(), set()

def guardar_historial(urls, ids, titulos):
    """Guarda historial de múltiples formas para evitar duplicados"""
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'ids': list(ids)[-MAX_HISTORIAL:],
        'titulos': list(titulos)[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat(),
        'total_guardados': len(urls)
    }
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Historial guardado: {len(urls)} registros")
    except Exception as e:
        print(f"❌ Error guardando historial: {e}")

# Cargar historial global
HISTORIAL_URLS, HISTORIAL_IDS, HISTORIAL_TITULOS = cargar_historial()

def ya_publicada(noticia):
    """Verifica si noticia ya fue publicada por URL, ID o título similar"""
    url = noticia.get('url', '')
    titulo = noticia.get('title', '').lower().strip()
    
    # Verificar URL normalizada
    url_norm = normalizar_url(url)
    if url_norm in HISTORIAL_URLS:
        print(f"   ⛔ DUPLICADO (URL): {titulo[:50]}...")
        return True
    
    # Verificar ID
    url_id = get_url_id(url)
    if url_id in HISTORIAL_IDS:
        print(f"   ⛔ DUPLICADO (ID): {titulo[:50]}...")
        return True
    
    # Verificar título similar (para detectar misma noticia con URL diferente)
    titulo_limpio = re.sub(r'[^\w\s]', '', titulo)[:50]  # Primeros 50 chars limpios
    for t in HISTORIAL_TITULOS:
        if titulo_limpio in t or t in titulo_limpio:
            print(f"   ⛔ DUPLICADO (TÍTULO): {titulo[:50]}...")
            return True
    
    return False

def marcar_publicada(noticia):
    """Marca noticia como publicada en todas las formas"""
    url = noticia.get('url', '')
    titulo = noticia.get('title', '').lower().strip()
    
    HISTORIAL_URLS.add(normalizar_url(url))
    HISTORIAL_IDS.add(get_url_id(url))
    HISTORIAL_TITULOS.add(re.sub(r'[^\w\s]', '', titulo)[:50])

def traducir_deepl(texto):
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
            return response.json()['translations'][0]['text']
    except:
        pass
    return texto

def redactar_openai(titulo_en, desc_en, fuente, categoria):
    """Genera redacción profesional en español"""
    
    # Traducir primero para contexto
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    system_msg = "Eres un periodista profesional. ESCRIBE ÚNICAMENTE EN ESPAÑOL. Redacción periodística formal, objetiva, mínimo 200 palabras."
    
    user_msg = f"""REDACTA EN ESPAÑOL PROFESIONAL:

DATOS:
Título (EN): {titulo_en}
Descripción (EN): {desc_en}
Traducción título: {titulo_es}
Traducción desc: {desc_es}
Fuente: {fuente}
Categoría: {categoria}

REQUISITOS:
1. TITULAR: Máximo 90 caracteres, impactante, en español
2. CUERPO: 3-4 párrafos, 200-350 palabras totales
3. Incluye contexto, datos relevantes e implicaciones
4. Tono: serio, profesional, objetivo
5. Menciona fuente: {fuente}
6. NO uses frases genéricas tipo "según fuentes"

FORMATO EXACTO:
TITULAR: [titular en español]

PARRAFO1: [lead con datos clave]

PARRAFO2: [desarrollo con contexto]

PARRAFO3: [análisis o implicaciones]

FIN"""

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system_msg},
                    {'role': 'user', 'content': user_msg}
                ],
                'temperature': 0.5,
                'max_tokens': 800
            },
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"   ⚠️ OpenAI HTTP {response.status_code}")
            return None, None
        
        text = response.json()['choices'][0]['message']['content']
        
        # Parsear respuesta
        titular = None
        parrafos = []
        current_p = []
        
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('TITULAR:'):
                titular = line.replace('TITULAR:', '').strip()
            elif line.startswith('PARRAFO') or line.startswith('CUERPO'):
                if current_p:
                    parrafos.append(' '.join(current_p))
                    current_p = []
            elif line.startswith('FIN'):
                break
            elif line and not line.startswith('DATOS:') and not line.startswith('REQUISITOS:'):
                current_p.append(line)
        
        if current_p:
            parrafos.append(' '.join(current_p))
        
        if not titular or len(parrafos) < 2:
            print("   ⚠️ OpenAI respuesta mal formada")
            return None, None
        
        cuerpo = '\n\n'.join(parrafos)
        
        # Validar español básico
        palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'ser', 'se', 'no', 'por', 'con', 'su', 'para']
        if not any(p in cuerpo.lower() for p in palabras_es[:5]):
            print("   ⚠️ OpenAI no generó español")
            return None, None
        
        print(f"   ✅ Redacción: {len(cuerpo.split())} palabras")
        return titular, cuerpo
        
    except Exception as e:
        print(f"   ⚠️ OpenAI error: {e}")
        return None, None

def generar_hashtags(categoria, titular):
    base = {
        'crisis': ['#ÚltimaHora', '#CrisisInternacional', '#AlertaMundial', '#NoticiasEnDesarrollo', '#Internacional'],
        'tech': ['#Tecnología', '#Innovación', '#InteligenciaArtificial', '#TechNews', '#Digital'],
        'economia': ['#EconomíaGlobal', '#MercadosFinancieros', '#Negocios', '#Finanzas', '#Inversión'],
        'politica': ['#PolíticaInternacional', '#Diplomacia', '#GobiernoGlobal', '#ActualidadPolítica', '#Mundo'],
        'internacional': ['#NoticiasMundiales', '#ActualidadInternacional', '#WorldNews', '#Global', '#Hoy']
    }
    
    tags = base.get(categoria, base['internacional']).copy()
    
    # Hashtag del año
    tags.append(f"#{datetime.now().strftime('%Y')}")
    
    # Extraer palabra clave
    palabras = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b', titular)
    if palabras:
        tag = '#' + palabras[0]
        if tag not in tags and len(tag) > 4:
            tags.append(tag)
    
    return ' '.join(tags[:5])

def detectar_categoria(titulo, desc):
    texto = f"{titulo} {desc}".lower()
    if any(p in texto for p in ['war', 'attack', 'invasion', 'missile', 'bomb', 'conflict', 'crisis', 'guerra']):
        return 'crisis'
    elif any(p in texto for p in ['tech', 'ai', 'artificial', 'software', 'digital', 'technology']):
        return 'tech'
    elif any(p in texto for p in ['economy', 'market', 'stock', 'financial', 'trade', 'economic']):
        return 'economia'
    elif any(p in texto for p in ['politics', 'election', 'president', 'government', 'minister', 'political']):
        return 'politica'
    return 'internacional'

def buscar_newsapi():
    if not NEWS_API_KEY:
        return []
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'category': 'general',
            'language': 'en',
            'pageSize': 25,
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
            'max': 25,
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
    feeds = random.sample(RSS_FEEDS, min(4, len(RSS_FEEDS)))
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                img = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    img = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', entry.summary, re.I)
                    if m:
                        img = m.group(1)
                
                noticias.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', ''))[:500],
                    'url': entry.get('link', ''),
                    'urlToImage': img,
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
    
    # Recolectar de todas las fuentes
    n = buscar_newsapi()
    todas.extend(n)
    print(f"📡 NewsAPI: {len(n)} artículos")
    
    n = buscar_gnews()
    todas.extend(n)
    print(f"📡 GNews: {len(n)} artículos")
    
    n = buscar_rss()
    todas.extend(n)
    print(f"📡 RSS: {len(n)} artículos")
    
    print(f"\n📊 Total recopilado: {len(todas)}")
    
    # Filtrar y deduplicar
    validas = []
    vistos = set()  # Para evitar duplicados dentro de esta misma ejecución
    
    for art in todas:
        if not art.get('title') or len(art['title']) < 15:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url'):
            continue
        
        # Deduplicación intra-ejecución
        url_id = get_url_id(art['url'])
        if url_id in vistos:
            continue
        vistos.add(url_id)
        
        # Deduplicación con historial
        if ya_publicada(art):
            continue
        
        categoria = detectar_categoria(art['title'], art.get('description', ''))
        
        art.update({
            'categoria': categoria,
            'url_id': url_id
        })
        
        validas.append(art)
        print(f"   ✅ Nueva: {art['title'][:55]}...")
    
    print(f"\n📊 Válidas únicas: {len(validas)}")
    
    # Solo con imagen
    con_img = [a for a in validas if a.get('urlToImage') and str(a['urlToImage']).startswith('http')]
    print(f"📊 Con imagen: {len(con_img)}")
    
    return con_img[:5]

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
            path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(path, 'JPEG', quality=85)
            print(f"🖼️  Imagen: {os.path.getsize(path)/1024:.1f} KB")
            return path
    except Exception as e:
        print(f"⚠️ Error imagen: {e}")
    return None

def publicar_fb(img_path, mensaje):
    if not img_path or not os.path.exists(img_path):
        return False
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(img_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = response.json()
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO: {result['id']}")
                return True
            print(f"❌ FB error: {result.get('error', {}).get('message', result)}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return False

def crear_mensaje(noticia):
    titulo_orig = noticia['title']
    desc_orig = noticia.get('description', '')
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    categoria = noticia['categoria']
    
    print(f"\n✍️  Redactando: {titulo_orig[:50]}...")
    
    # Intentar OpenAI
    titular, cuerpo = redactar_openai(titulo_orig, desc_orig, fuente, categoria)
    
    if not titular or not cuerpo:
        print("   ⚠️ Fallback a traducción básica")
        titular = traducir_deepl(titulo_orig)
        cuerpo = traducir_deepl(desc_orig) + f"\n\n📡 Información de {fuente}."
    
    hashtags = generar_hashtags(categoria, titular)
    
    return f"""📰 {titular}

{cuerpo}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""

def main():
    print(f"\n{'='*60}")
    print("INICIANDO PROCESO DE PUBLICACIÓN")
    print(f"{'='*60}")
    
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas disponibles")
        guardar_historial(HISTORIAL_URLS, HISTORIAL_IDS, HISTORIAL_TITULOS)
        return False
    
    print(f"\n🎯 Intentando publicar {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 INTERTO {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        # Descargar imagen
        img = descargar_imagen(noticia.get('urlToImage'))
        if not img:
            print("⏭️ Sin imagen, saltando...")
            continue
        
        # Crear mensaje
        msg = crear_mensaje(noticia)
        print(f"\n📝 Mensaje ({len(msg)} chars):")
        print(msg[:250] + "..." if len(msg) > 250 else msg)
        
        # Publicar
        if publicar_fb(img, msg):
            # Marcar como publicada
            marcar_publicada(noticia)
            guardar_historial(HISTORIAL_URLS, HISTORIAL_IDS, HISTORIAL_TITULOS)
            
            # Limpiar
            if os.path.exists(img):
                os.remove(img)
            
            print(f"\n{'='*60}")
            print("✅ ÉXITO: Noticia publicada y registrada")
            print(f"{'='*60}")
            return True
        
        # Limpiar si falló
        if os.path.exists(img):
            os.remove(img)
        print("⏭️ Falló, intentando siguiente...")
    
    print(f"\n{'='*60}")
    print("❌ No se pudo publicar ninguna noticia")
    print(f"{'='*60}")
    guardar_historial(HISTORIAL_URLS, HISTORIAL_IDS, HISTORIAL_TITULOS)
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
