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
    if not DEEPL_API_KEY or not texto:
        return texto
    try:
        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                'auth_key': DEEPL_API_KEY,
                'text': str(texto)[:1500],
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

def redactar_profesional(titulo_en, desc_en, fuente):
    """
    Genera redacción periodística profesional en español
    Características: 800-1500 chars, párrafos cortos, dato importante al inicio
    """
    
    # Primero traducimos todo para asegurar español
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    print(f"   🌐 Traducción base: {titulo_es[:50]}...")
    
    if not OPENAI_API_KEY:
        # Fallback sin OpenAI
        return crear_texto_manual(titulo_es, desc_es, fuente)
    
    # Prompt optimizado para periodismo
    prompt = f"""ACTÚA COMO PERIODISTA PROFESIONAL. ESCRIBE EN ESPAÑOL.

DATOS DE LA NOTICIA:
Título: {titulo_es}
Descripción: {desc_es}
Fuente: {fuente}

INSTRUCCIONES OBLIGATORIAS:
1. ESCRIBE ÚNICAMENTE EN ESPAÑOL (español neutro o de Latinoamérica)
2. ESTRUCTURA DEL TEXTO:
   - Párrafo 1 (LEAD): Un dato importante y contundente al inicio. Máximo 3 líneas.
   - Párrafo 2: Contexto y antecedentes. Máximo 4 líneas.
   - Párrafo 3: Desarrollo y reacciones. Máximo 4 líneas.
   - Párrafo 4 (opcional): Implicaciones o proyección. Máximo 3 líneas.
3. LONGITUD: Entre 800 y 1200 caracteres (máximo 1500 si el tema lo amerita)
4. ESTILO: Periodístico neutral, objetivo, informativo
5. PÁRRAFOS CORTOS: Máximo 3-4 líneas por párrafo
6. DATO CLAVE: El primer párrafo debe tener el dato más importante
7. FUENTE: Mencionar "{fuente}" al final del texto

FORMATO EXACTO DE RESPUESTA:
TITULAR: [titular breve y contundente, máximo 80 caracteres]

TEXTO:
[Primer párrafo corto con dato clave]

[Segundo párrafo con contexto]

[Tercer párrafo con desarrollo]

[Cuarto párrafo opcional con cierre o implicaciones]

Información de {fuente}.

FIN"""

    try:
        print("   🤖 Generando redacción profesional...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.5,  # Más determinístico para periodismo
                'max_tokens': 500
            },
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"   ⚠️ OpenAI error HTTP {response.status_code}")
            return crear_texto_manual(titulo_es, desc_es, fuente)
        
        resultado = response.json()['choices'][0]['message']['content']
        
        # Parsear respuesta
        titular = None
        texto = None
        
        if 'TITULAR:' in resultado:
            # Extraer titular
            partes_titular = resultado.split('TITULAR:')[1].split('TEXTO:')
            titular = partes_titular[0].strip()
            titular = titular.strip('"\'').strip()
            
            # Extraer texto
            if 'FIN' in resultado:
                texto = partes_titular[1].split('FIN')[0].strip()
            else:
                texto = partes_titular[1].strip()
        
        if not titular or not texto:
            print("   ⚠️ No se pudo parsear, usando manual")
            return crear_texto_manual(titulo_es, desc_es, fuente)
        
        # Validar español
        palabras_clave = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 'su']
        if not any(p in texto.lower() for p in palabras_clave[:5]):
            print("   ⚠️ No detecta español, usando manual")
            return crear_texto_manual(titulo_es, desc_es, fuente)
        
        # Validar longitud
        longitud = len(texto)
        if longitud < 600:
            print(f"   ⚠️ Muy corto ({longitud} chars), expandiendo...")
            texto = expandir_texto(texto, fuente)
        
        print(f"   ✅ Redacción: {len(texto)} caracteres, {texto.count(chr(10))} párrafos")
        return {'titular': titular, 'texto': texto}
        
    except Exception as e:
        print(f"   ⚠️ Error OpenAI: {e}")
        return crear_texto_manual(titulo_es, desc_es, fuente)

def crear_texto_manual(titulo, descripcion, fuente):
    """Crea texto manualmente cuando OpenAI falla"""
    print("   📝 Creando texto manual...")
    
    # Expandir descripción para llegar a 800+ caracteres
    texto_base = descripcion if len(descripcion) > 200 else f"{descripcion} Esta información ha generado amplio interés en medios internacionales debido a su relevancia para la comunidad global. Los analistas destacan la importancia de seguir de cerca este desarrollo en las próximas horas."
    
    # Crear estructura periodística
    parrafo1 = texto_base[:250] if len(texto_base) > 250 else texto_base
    parrafo2 = "El hecho ha sido reportado por diversos medios de comunicación internacionales, destacando su trascendencia en el ámbito global. Las autoridades competentes continúan monitoreando la situación de cerca."
    parrafo3 = "Expertos en la materia señalan que este tipo de eventos requieren atención constante por parte de la comunidad internacional. La cobertura periodística continuará actualizándose conforme se desarrollen los hechos."
    
    texto = f"{parrafo1}\n\n{parrafo2}\n\n{parrafo3}\n\n📡 Información de {fuente}."
    
    # Asegurar longitud mínima
    while len(texto) < 800:
        texto += f" Los detalles adicionales serán proporcionados por {fuente} en próximas actualizaciones."
    
    print(f"   ✅ Texto manual: {len(texto)} caracteres")
    return {'titular': titulo, 'texto': texto[:1200]}

def expandir_texto(texto, fuente):
    """Expande texto corto para llegar a 800+ caracteres"""
    adicionales = [
        f"\n\nLos analistas internacionales continúan evaluando el impacto de esta información. La comunidad global mantiene atención sobre los próximos desarrollos.",
        f"\n\nEsta noticia ha generado reacciones en diferentes sectores de la sociedad. {fuente} continuará reportando actualizaciones.",
        f"\n\nLa cobertura periodística de este evento se extiende por múltiples regiones del mundo."
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
    """Publica en Facebook con formato optimizado"""
    
    # Hashtags
    hashtags = f"#NoticiasMundiales #Actualidad #{datetime.now().strftime('%Y')} #Internacional #Hoy"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    print(f"\n   📝 MENSAJE FINAL ({len(mensaje)} caracteres):")
    print(f"   {'-'*50}")
    for i, linea in enumerate(mensaje.split('\n')[:8]):
        print(f"   {linea[:60]}{'...' if len(linea) > 60 else ''}")
    if len(mensaje.split('\n')) > 8:
        print(f"   ... ({len(mensaje.split(chr(10))) - 8} líneas más)")
    print(f"   {'-'*50}")
    
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
        
        # Crear redacción profesional
        resultado = redactar_profesional(
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
            print("✅ ÉXITO")
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
