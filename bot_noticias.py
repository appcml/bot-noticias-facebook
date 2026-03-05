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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

HISTORIAL_FILE = 'historial_publicaciones.json'

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"📚 Historial cargado: {len(historial['urls'])} noticias publicadas")
        if historial.get('ultima_publicacion'):
            print(f"   Última: {historial['ultima_publicacion']}")
    except Exception as e:
        print(f"⚠️ Error cargando historial: {e}")
else:
    print("📚 Nuevo historial (primera ejecución)")

def guardar_historial(url, titulo):
    """Guarda la noticia publicada en el historial"""
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])  # Guardar primeros 100 chars
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    # Mantener solo últimas 500
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Historial actualizado: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"❌ Error guardando historial: {e}")

def get_url_id(url):
    """ID único para URL"""
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:16]

def ya_publicada(url, titulo):
    """Verifica si ya se publicó esta noticia"""
    url_id = get_url_id(url)
    
    # Verificar por URL
    if url_id in [get_url_id(u) for u in historial['urls']]:
        print(f"   ⛔ Ya publicada (URL): {titulo[:40]}...")
        return True
    
    # Verificar por título similar
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        # Si coinciden más del 70%, es duplicado
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencia / max(len(titulo_simple), len(t_simple)) > 0.7:
                print(f"   ⛔ Ya publicada (título similar): {titulo[:40]}...")
                return True
    
    return False

def traducir_deepl(texto):
    """Traduce usando DeepL"""
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

def buscar_noticias():
    """Busca noticias de todas las fuentes"""
    print("\n🔍 Buscando noticias...")
    
    noticias = []
    
    # 1. NewsAPI
    if NEWS_API_KEY:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'language': 'en', 'pageSize': 20, 'apiKey': NEWS_API_KEY},
                timeout=10
            )
            data = response.json()
            if data.get('status') == 'ok':
                noticias.extend(data.get('articles', []))
                print(f"   📡 NewsAPI: {len(data.get('articles', []))}")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # 2. GNews
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
    
    # 3. RSS
    if len(noticias) < 3:
        rss_feeds = [
            'http://feeds.bbci.co.uk/news/world/rss.xml',
            'https://www.reuters.com/rssFeed/worldNews',
            'https://rss.cnn.com/rss/edition_world.rss'
        ]
        for feed_url in random.sample(rss_feeds, min(2, len(rss_feeds))):
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
                        'description': entry.get('summary', entry.get('description', ''))[:300],
                        'url': entry.get('link'),
                        'urlToImage': img,
                        'source': {'name': feed.feed.get('title', 'RSS')}
                    })
                print(f"   📡 RSS: {feed_url.split('/')[2]}")
            except:
                pass
    
    print(f"\n📊 Total encontradas: {len(noticias)}")
    
    # Filtrar nuevas
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url'):
            continue
        if not art.get('urlToImage'):
            continue
        
        if ya_publicada(art['url'], art['title']):
            continue
        
        nuevas.append(art)
        print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Nuevas disponibles: {len(nuevas)}")
    return nuevas[:3]

def descargar_imagen(url):
    """Descarga imagen"""
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

def crear_mensaje(titulo_en, desc_en, fuente):
    """Crea mensaje en español"""
    
    # Traducir con DeepL
    titulo = traducir_deepl(titulo_en)
    descripcion = traducir_deepl(desc_en)
    
    # Si tenemos OpenAI, mejorar redacción
    if OPENAI_API_KEY:
        try:
            prompt = f"""Escribe en ESPAÑOL una noticia profesional con:

TÍTULO: {titulo}
DESCRIPCIÓN: {descripcion}
FUENTE: {fuente}

REGLAS:
- 3 párrafos en español
- Tono periodístico
- Mínimo 150 palabras
- Menciona la fuente al final

Formato: TITULAR: (máx 80 chars) | TEXTO: (3 párrafos)"""

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
                    'max_tokens': 600
                },
                timeout=30
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                
                # Extraer partes
                if 'TITULAR:' in resultado and 'TEXTO:' in resultado:
                    partes = resultado.split('TITULAR:')[1].split('TEXTO:')
                    titulo = partes[0].strip()
                    texto = partes[1].strip()
                    
                    # Verificar español
                    if any(p in texto.lower() for p in ['el', 'la', 'de', 'que', 'y']):
                        print("   ✅ OpenAI generó español")
                        return titulo, texto
        except Exception as e:
            print(f"   ⚠️ OpenAI falló: {e}")
    
    # Fallback: usar traducción directa
    print("   🌐 Usando traducción DeepL")
    texto = f"{descripcion}\n\n📡 Fuente: {fuente}"
    return titulo, texto

def publicar_facebook(img_path, titulo, texto):
    """Publica en Facebook"""
    # Hashtags
    hashtags = f"#NoticiasMundiales #Actualidad #{datetime.now().strftime('%Y')} #Internacional #Hoy"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
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
        print("\n⚠️ No hay noticias nuevas disponibles")
        print("   (Todas las noticias encontradas ya fueron publicadas)")
        return False
    
    print(f"\n🎯 Intentando publicar {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"📰 Intento {i}/{len(noticias)}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
            continue
        
        # Crear mensaje
        titulo, texto = crear_mensaje(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales')
        )
        
        print(f"   📝 Titular: {titulo[:60]}...")
        
        # Publicar
        if publicar_facebook(img_path, titulo, texto):
            # Guardar en historial
            guardar_historial(noticia['url'], noticia['title'])
            
            # Limpiar
            os.remove(img_path)
            
            print(f"\n{'='*50}")
            print("✅ ÉXITO - Noticia nueva publicada")
            print(f"{'='*50}")
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\n❌ No se pudo publicar ninguna noticia")
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
