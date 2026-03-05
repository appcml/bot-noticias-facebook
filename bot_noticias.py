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
        print(f"📚 Historial: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"⚠️ Error historial: {e}")

def guardar_historial(url, titulo):
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['ultima_publicacion'] = datetime.now().isoformat()
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Historial: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"❌ Error guardando: {e}")

def get_url_id(url):
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:16]

def ya_publicada(url, titulo):
    url_id = get_url_id(url)
    if url_id in [get_url_id(u) for u in historial['urls']]:
        print(f"   ⛔ Ya publicada: {titulo[:40]}...")
        return True
    
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencia / max(len(titulo_simple), len(t_simple)) > 0.7:
                print(f"   ⛔ Título similar: {titulo[:40]}...")
                return True
    return False

def traducir_deepl(texto):
    """Traduce a español con DeepL"""
    if not DEEPL_API_KEY or not texto:
        return texto
    try:
        response = requests.post(
            "https://api-free.deepl.com/v2/translate ",
            data={
                'auth_key': DEEPL_API_KEY,
                'text': str(texto)[:2000],
                'source_lang': 'EN',
                'target_lang': 'ES'
            },
            timeout=15
        )
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"   ⚠️ DeepL: {e}")
    return texto

def crear_noticia_ia_espanol(titulo_en, desc_en, fuente):
    """
    DeepL traduce primero, luego OpenAI reescribe en español
    """
    
    # PASO 1: DeepL traduce TODO a español (garantía)
    titulo_base = traducir_deepl(titulo_en)
    desc_base = traducir_deepl(desc_en)
    
    print(f"   🌐 DeepL: {titulo_base[:50]}...")
    
    if not OPENAI_API_KEY:
        # Fallback sin OpenAI
        return crear_estructura_manual(titulo_base, desc_base, fuente)
    
    # PASO 2: OpenAI reescribe el texto YA EN ESPAÑOL
    prompt = f"""REESCRIBE ESTE TEXTO YA EN ESPAÑOL de forma periodística profesional.

TEXTO ORIGINAL (ya traducido al español):
Título: {titulo_base}
Descripción: {desc_base}
Fuente: {fuente}

INSTRUCCIONES OBLIGATORIAS:
1. El texto YA ESTÁ EN ESPAÑOL, solo reescríbelo mejor
2. Crea 3-4 párrafos periodísticos en ESPAÑOL PURO
3. TITULAR: Reescribe el título en español (máx 80 caracteres)
4. Párrafo 1 (Lead): Dato más importante, máx 3 líneas, ESPAÑOL
5. Párrafo 2 (Contexto): Antecedentes, máx 4 líneas, ESPAÑOL
6. Párrafo 3 (Análisis): Reacciones, máx 4 líneas, ESPAÑOL
7. Párrafo 4 (Cierre): Implicaciones + "Información de {fuente}", máx 3 líneas, ESPAÑOL
8. Longitud total: 800-1200 caracteres
9. NUNCA uses inglés, todo debe estar en ESPAÑOL

FORMATO EXACTO:
TITULAR_ES: [título reescrito en español]

TEXTO_ES:
[párrafo 1 en español]

[párrafo 2 en español]

[párrafo 3 en español]

[párrafo 4 en español]

FIN"""

    try:
        print("   🤖 OpenAI reescribiendo en español...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions ',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.4,  # Bajo para obedecer instrucciones
                'max_tokens': 700
            },
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"   ⚠️ OpenAI error, usando manual")
            return crear_estructura_manual(titulo_base, desc_base, fuente)
        
        resultado = response.json()['choices'][0]['message']['content']
        
        # Extraer partes
        titular = titulo_base  # Por defecto
        texto = desc_base      # Por defecto
        
        # Buscar TITULAR_ES
        if 'TITULAR_ES:' in resultado or 'TITULAR:' in resultado:
            try:
                # Intentar ambos formatos
                if 'TITULAR_ES:' in resultado:
                    partes = resultado.split('TITULAR_ES:')[1].split('TEXTO_ES:')
                else:
                    partes = resultado.split('TITULAR:')[1].split('TEXTO:')
                titular = partes[0].strip().strip('"\'[]')
            except:
                pass
        
        # Buscar TEXTO_ES
        if 'TEXTO_ES:' in resultado or 'TEXTO:' in resultado:
            try:
                if 'TEXTO_ES:' in resultado:
                    texto_parte = resultado.split('TEXTO_ES:')[1]
                else:
                    texto_parte = resultado.split('TEXTO:')[1]
                
                if 'FIN' in texto_parte:
                    texto = texto_parte.split('FIN')[0].strip()
                else:
                    texto = texto_parte.strip()
            except:
                pass
        
        # VERIFICACIÓN ESTRICTA DE ESPAÑOL
        texto_completo = titular + " " + texto
        
        # Contar palabras español vs inglés
        palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 'su', 'los', 'las', 'del', 'al']
        palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out']
        
        count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_completo.lower()} ')
        count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_completo.lower()} ')
        
        print(f"   🔍 Verificación: {count_es} palabras ES, {count_en} palabras EN")
        
        # Si hay mucho inglés, rechazar y usar manual
        if count_en > 3 or count_es < 5:
            print(f"   ⚠️ Mucho inglés detectado ({count_en} palabras), usando manual")
            return crear_estructura_manual(titulo_base, desc_base, fuente)
        
        # Verificar longitud
        if len(texto) < 600:
            texto = expandir_texto_espanol(texto, fuente)
        
        print(f"   ✅ IA español: {len(texto)} chars, {texto.count(chr(10))} párrafos")
        return {'titular': titular, 'texto': texto}
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        return crear_estructura_manual(titulo_base, desc_base, fuente)

def crear_estructura_manual(titulo, descripcion, fuente):
    """Fallback 100% español sin IA"""
    print("   📝 Creando estructura manual español...")
    
    # Párrafo 1: Descripción como lead
    if len(descripcion) > 100:
        oraciones = descripcion.split('.')
        parrafo1 = oraciones[0].strip() + "."
        if len(parrafo1) < 100 and len(oraciones) > 1:
            parrafo1 += " " + oraciones[1].strip() + "."
    else:
        parrafo1 = f"{descripcion}. Este acontecimiento ha generado atención internacional."
    
    # Párrafos 2-4: Plantillas fijas español
    parrafo2 = "La información ha sido confirmada por fuentes periodísticas globales. Las autoridades evalúan la situación."
    parrafo3 = "Analistas señalan que este evento requiere seguimiento constante por la comunidad internacional."
    parrafo4 = f"Los detalles adicionales se proporcionarán próximamente. Información de {fuente}."
    
    texto = f"{parrafo1}\n\n{parrafo2}\n\n{parrafo3}\n\n{parrafo4}"
    
    if len(texto) < 800:
        texto += f"\n\nLa cobertura continúa según {fuente}."
    
    print(f"   ✅ Manual español: {len(texto)} chars")
    return {'titular': titulo[:80], 'texto': texto[:1500]}

def expandir_texto_espanol(texto, fuente):
    """Expande manteniendo español"""
    adicionales = [
        f"\n\nEste desarrollo ha sido reportado por múltiples medios internacionales.",
        f"\n\nLa comunidad global mantiene atención sobre los próximos acontecimientos.",
        f"\n\nLa situación continúa en evolución según reportes de {fuente}."
    ]
    for adicional in adicionales:
        if len(texto) < 800:
            texto += adicional
    return texto[:1500]

def buscar_noticias():
    print("\n🔍 Buscando noticias...")
    
    noticias = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines ",
                params={'language': 'en', 'pageSize': 20, 'apiKey': NEWS_API_KEY},
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
                "https://gnews.io/api/v4/top-headlines ",
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
            'http://feeds.bbci.co.uk/news/world/rss.xml ',
            'https://www.reuters.com/rssFeed/worldNews ',
            'https://rss.cnn.com/rss/edition_world.rss '
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
                        'description': entry.get('summary', entry.get('description', ''))[:400],
                        'url': entry.get('link'),
                        'urlToImage': img,
                        'source': {'name': feed.feed.get('title', 'RSS')}
                    })
                print(f"   📡 RSS: {feed_url.split('/')[2]}")
            except:
                pass
    
    print(f"\n📊 Total: {len(noticias)}")
    
    # Filtrar nuevas
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url') or not art.get('urlToImage'):
            continue
        
        if ya_publicada(art['url'], art['title']):
            continue
        
        nuevas.append(art)
        print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Nuevas: {len(nuevas)}")
    return nuevas[:3]

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

def publicar(titulo, texto, img_path):
    """Publica en Facebook"""
    
    # Verificación español
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 'su', 'los', 'las']
    count_es = sum(1 for p in palabras_es if p in texto.lower())
    print(f"   ✅ Español: {count_es} palabras clave detectadas")
    
    hashtags = f"#NoticiasMundiales #Actualidad #{datetime.now().strftime('%Y')} #Internacional #Hoy"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    print(f"\n   📝 MENSAJE ({len(mensaje)} caracteres):")
    print(f"   {'-'*50}")
    for linea in mensaje.split('\n')[:10]:
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
    if len(mensaje.split('\n')) > 10:
        print(f"   ... ({len(mensaje.split(chr(10))) - 10} líneas más)")
    print(f"   {'-'*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/ {FB_PAGE_ID}/photos"
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
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas")
        return False
    
    print(f"\n🎯 Intentando publicar {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
            continue
        
        # Crear noticia con IA en español
        resultado = crear_noticia_ia_espanol(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales')
        )
        
        titulo = resultado['titular']
        texto = resultado['texto']
        
        # Publicar
        if publicar(titulo, texto, img_path):
            guardar_historial(noticia['url'], noticia['title'])
            os.remove(img_path)
            print(f"\n{'='*60}")
            print("✅ ÉXITO - IA en español")
            print(f"{'='*60}")
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\n❌ Falló todo")
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
