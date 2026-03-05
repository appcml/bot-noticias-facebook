import requests
import random
import re
import hashlib
import os
import json
import feedparser
from datetime import datetime
from urllib.parse import urlparse, urldefrag
from PIL import Image
from io import BytesIO

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

HISTORIAL_FILE = 'historial_publicaciones.json'

print("="*60)
print("🚀 BOT DE NOTICIAS")
print("="*60)

# Cargar historial
historial_urls = set()
historial_titulos = set()

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r') as f:
            data = json.load(f)
            historial_urls = set(data.get('urls', []))
            historial_titulos = set(data.get('titulos', []))
        print(f"📚 Historial cargado: {len(historial_urls)} noticias")
    except:
        pass
else:
    print("📚 Nuevo historial")

def guardar_historial():
    with open(HISTORIAL_FILE, 'w') as f:
        json.dump({
            'urls': list(historial_urls),
            'titulos': list(historial_titulos),
            'last_update': datetime.now().isoformat()
        }, f)
    print(f"💾 Historial guardado: {len(historial_urls)} noticias")

def normalizar_url(url):
    if not url:
        return ""
    url = str(url).lower().strip()
    url, _ = urldefrag(url)
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                         parsed.params, nuevo_query, ''))
    except:
        pass
    return url.rstrip('/')

def get_url_hash(url):
    return hashlib.md5(normalizar_url(url).encode()).hexdigest()[:16]

def traducir_deepl(texto):
    if not DEEPL_API_KEY or not texto:
        return texto
    try:
        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                'auth_key': DEEPL_API_KEY,
                'text': str(texto)[:1000],
                'source_lang': 'EN',
                'target_lang': 'ES'
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except:
        pass
    return texto

def redactar_openai(titulo_en, desc_en, fuente):
    """
    Genera redacción profesional en español usando OpenAI
    """
    if not OPENAI_API_KEY:
        return None
    
    # Traducir primero para dar contexto
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    print(f"   🌐 Traducción DeepL: {titulo_es[:50]}...")
    
    prompt = f"""Eres un periodista profesional. Escribe esta noticia en ESPAÑOL.

TÍTULO ORIGINAL (inglés): {titulo_en}
DESCRIPCIÓN ORIGINAL (inglés): {desc_en}

TRADUCCIÓN PREVIA:
Título: {titulo_es}
Descripción: {desc_es}

FUENTE: {fuente}

INSTRUCCIONES:
1. Escribe ÚNICAMENTE en español
2. Crea un titular impactante (máx 90 caracteres)
3. Redacta 3 párrafos profesionales (mínimo 200 palabras totales):
   - Párrafo 1: Lead con datos clave
   - Párrafo 2: Contexto y desarrollo  
   - Párrafo 3: Implicaciones y cierre
4. Tono: serio, periodístico, objetivo
5. Menciona la fuente al final

FORMATO DE RESPUESTA:
TITULAR: [titular en español]

TEXTO: [texto completo en español, 3 párrafos separados por líneas en blanco]

FIN"""

    try:
        print("   🤖 Pidiendo redacción a OpenAI...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 700
            },
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"   ❌ OpenAI error HTTP {response.status_code}")
            return None
        
        resultado = response.json()['choices'][0]['message']['content']
        
        # Extraer titular y texto
        titular = None
        texto = None
        
        if 'TITULAR:' in resultado and 'TEXTO:' in resultado:
            partes = resultado.split('TITULAR:')[1].split('TEXTO:')
            titular = partes[0].strip()
            texto = partes[1].split('FIN')[0].strip() if 'FIN' in partes[1] else partes[1].strip()
        
        if not titular or not texto:
            print("   ⚠️ No se pudo parsear respuesta")
            return None
        
        # Verificar que sea español
        if len(texto) < 100:
            print(f"   ⚠️ Texto muy corto: {len(texto)} chars")
            return None
        
        palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por']
        if not any(p in texto.lower() for p in palabras_es[:3]):
            print("   ⚠️ No parece estar en español")
            return None
        
        print(f"   ✅ Redacción OK: {len(texto.split())} palabras")
        return {'titular': titular, 'texto': texto}
        
    except Exception as e:
        print(f"   ❌ Error OpenAI: {e}")
        return None

def generar_hashtags(titular):
    # 5 hashtags fijos + dinámico
    tags = ['#NoticiasMundiales', '#ActualidadInternacional', '#WorldNews', 
            f"#{datetime.now().strftime('%Y')}", '#Hoy']
    
    # Extraer palabra clave del titular
    palabras = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{4,}\b', titular)
    if palabras:
        tag = '#' + palabras[0]
        if tag not in tags:
            tags[3] = tag  # Reemplazar el del año si hay palabra clave
    
    return ' '.join(tags[:5])

def buscar_noticias():
    print("\n🔍 Buscando noticias...")
    
    noticias = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'category': 'general', 'language': 'en', 'pageSize': 20, 
                       'apiKey': NEWS_API_KEY},
                timeout=10
            )
            data = response.json()
            if data.get('status') == 'ok':
                noticias.extend(data.get('articles', []))
                print(f"   📡 NewsAPI: {len(data.get('articles', []))}")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # GNews
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            response = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'en', 'max': 20, 'apikey': GNEWS_API_KEY},
                timeout=10
            )
            data = response.json()
            if 'articles' in data:
                for a in data['articles']:
                    noticias.append({
                        'title': a.get('title'),
                        'description': a.get('description'),
                        'url': a.get('url'),
                        'urlToImage': a.get('image'),
                        'source': {'name': a.get('source', {}).get('name', 'GNews')}
                    })
                print(f"   📡 GNews: {len(data['articles'])}")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # RSS
    if len(noticias) < 3:
        rss_feeds = [
            'http://feeds.bbci.co.uk/news/world/rss.xml',
            'https://www.reuters.com/rssFeed/worldNews',
            'https://rss.cnn.com/rss/edition_world.rss'
        ]
        for feed_url in random.sample(rss_feeds, 2):
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    img = ''
                    if hasattr(entry, 'media_content') and entry.media_content:
                        img = entry.media_content[0].get('url', '')
                    elif 'summary' in entry:
                        m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png))"', entry.summary, re.I)
                        if m:
                            img = m.group(1)
                    
                    noticias.append({
                        'title': entry.get('title'),
                        'description': entry.get('summary', entry.get('description', ''))[:400],
                        'url': entry.get('link'),
                        'urlToImage': img,
                        'source': {'name': feed.feed.get('title', 'RSS')}
                    })
                print(f"   📡 RSS {feed_url.split('/')[2]}: {len(feed.entries[:5])}")
            except:
                pass
    
    print(f"\n📊 Total encontradas: {len(noticias)}")
    
    # Filtrar válidas y nuevas
    validas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 15:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url'):
            continue
        
        url_hash = get_url_hash(art['url'])
        if url_hash in historial_urls:
            print(f"   ⏭️ Ya publicada: {art['title'][:40]}...")
            continue
        
        # Verificar título similar
        titulo_simple = re.sub(r'[^\w]', '', art['title'].lower())[:30]
        if titulo_simple in historial_titulos:
            print(f"   ⏭️ Título similar: {art['title'][:40]}...")
            continue
        
        if art.get('urlToImage') and str(art['urlToImage']).startswith('http'):
            validas.append(art)
            print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Nuevas con imagen: {len(validas)}")
    return validas[:3]

def descargar_imagen(url):
    if not url or not str(url).startswith('http'):
        return None
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(path, 'JPEG', quality=85)
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar_facebook(img_path, mensaje):
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
                print(f"   ✅ Publicado: {result['id']}")
                return True
            print(f"   ❌ FB error: {result.get('error', {}).get('message', result)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return False

def main():
    # Buscar noticias
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas")
        guardar_historial()
        return False
    
    print(f"\n🎯 Intentando publicar {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"📰 Noticia {i}/{len(noticias)}")
        print(f"{'='*50}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
            continue
        
        # Crear redacción
        print("   ✍️  Redactando...")
        redaccion = redactar_openai(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales')
        )
        
        if redaccion:
            titular = redaccion['titular']
            cuerpo = redaccion['texto']
        else:
            # Fallback: traducción básica
            print("   ⚠️ Usando traducción básica")
            titular = traducir_deepl(noticia['title'])
            cuerpo = traducir_deepl(noticia.get('description', ''))
            cuerpo += f"\n\n📡 Fuente: {noticia.get('source', {}).get('name', 'Medios')}"
        
        # Hashtags
        hashtags = generar_hashtags(titular)
        
        # Mensaje final
        mensaje = f"""📰 {titular}

{cuerpo}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
        
        print(f"\n   📝 Preview:")
        print(f"   {mensaje[:200]}...")
        
        # Publicar
        if publicar_facebook(img_path, mensaje):
            # Marcar como publicada
            historial_urls.add(get_url_hash(noticia['url']))
            historial_titulos.add(re.sub(r'[^\w]', '', noticia['title'].lower())[:30])
            guardar_historial()
            
            # Limpiar
            os.remove(img_path)
            
            print(f"\n{'='*50}")
            print("✅ ÉXITO")
            print(f"{'='*50}")
            return True
        
        # Limpiar si falló
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\n❌ No se pudo publicar")
    guardar_historial()
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
