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
    """Traduce texto completo a español"""
    if not DEEPL_API_KEY or not texto:
        return texto
    try:
        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                'auth_key': DEEPL_API_KEY,
                'text': str(texto)[:2000],
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

def redactar_espanol_completo(titulo_en, desc_en, fuente):
    """
    Genera redacción 100% en español con estructura periodística
    """
    
    # TRADUCIR TODO PRIMERO (garantiza español base)
    titulo_base = traducir_deepl(titulo_en)
    desc_base = traducir_deepl(desc_en)
    
    print(f"   🌐 Base traducida: {titulo_base[:50]}...")
    
    if not OPENAI_API_KEY:
        return crear_texto_espanol_manual(titulo_base, desc_base, fuente)
    
    # Prompt ultra específico para español completo
    prompt = f"""REDACTA UNA NOTICIA COMPLETA EN ESPAÑOL. TODO EL TEXTO DEBE ESTAR EN ESPAÑOL.

DATOS TRADUCIDOS:
- Título: {titulo_base}
- Descripción: {desc_base}
- Fuente: {fuente}

REGLAS ESTRICTAS:
1. TODO EL CONTENIDO DEBE ESTAR EN ESPAÑOL (título, texto, todo)
2. Estructura periodística:
   * TITULAR: Máximo 80 caracteres, contundente, en ESPAÑOL
   * Lead (párrafo 1): Dato más importante, máximo 3 líneas, en ESPAÑOL
   * Desarrollo (párrafo 2): Contexto, máximo 4 líneas, en ESPAÑOL  
   * Análisis (párrafo 3): Reacciones, máximo 4 líneas, en ESPAÑOL
   * Cierre (párrafo 4): Implicaciones, máximo 3 líneas, en ESPAÑOL
3. Longitud total: 800-1500 caracteres
4. Estilo: Periodístico neutral, objetivo, informativo
5. Al final: "Información de {fuente}" (sin link, solo el nombre)

FORMATO OBLIGATORIO:
TITULAR_ESPANOL=[titular completo en español]

TEXTO_ESPANOL=
[Lead en español - dato clave]

[Desarrollo en español - contexto]

[Análisis en español - reacciones]

[Cierre en español - implicaciones]

Información de {fuente}.

FIN"""

    try:
        print("   🤖 Generando redacción en español...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,  # Más bajo = más obediente al idioma
                'max_tokens': 600
            },
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"   ⚠️ OpenAI error, usando manual")
            return crear_texto_espanol_manual(titulo_base, desc_base, fuente)
        
        resultado = response.json()['choices'][0]['message']['content']
        
        # Extraer con precisión
        titular = None
        texto = None
        
        # Buscar TITULAR_ESPANOL
        if 'TITULAR_ESPANOL=' in resultado:
            titular_parte = resultado.split('TITULAR_ESPANOL=')[1].split('TEXTO_ESPANOL=')[0]
            titular = titular_parte.strip().strip('"\'[]')
        
        # Buscar TEXTO_ESPANOL
        if 'TEXTO_ESPANOL=' in resultado:
            texto_parte = resultado.split('TEXTO_ESPANOL=')[1]
            if 'FIN' in texto_parte:
                texto = texto_parte.split('FIN')[0].strip()
            else:
                texto = texto_parte.strip()
        
        # Validaciones estrictas
        if not titular or not texto:
            print("   ⚠️ Parseo falló, usando manual")
            return crear_texto_espanol_manual(titulo_base, desc_base, fuente)
        
        # Verificar que sea español (palabras clave)
        texto_completo = titular + " " + texto
        palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 'su', 'para']
        coincidencias = sum(1 for p in palabras_es if p in texto_completo.lower())
        
        if coincidencias < 3:  # Muy poco español detectado
            print(f"   ⚠️ Poco español detectado ({coincidencias} palabras), usando manual")
            return crear_texto_espanol_manual(titulo_base, desc_base, fuente)
        
        # Verificar longitud
        if len(texto) < 600:
            texto = expandir_texto_espanol(texto, fuente)
        
        # Asegurar que la fuente esté al final sin link
        if f"Información de {fuente}" not in texto:
            texto += f"\n\nInformación de {fuente}."
        
        print(f"   ✅ Español confirmado: {len(texto)} chars, {texto.count(chr(10))} párrafos")
        return {'titular': titular, 'texto': texto}
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        return crear_texto_espanol_manual(titulo_base, desc_base, fuente)

def crear_texto_espanol_manual(titulo, descripcion, fuente):
    """Crea texto 100% en español cuando OpenAI falla"""
    print("   📝 Creando texto español manual...")
    
    # Limpiar y preparar
    titulo = str(titulo).strip()
    desc = str(descripcion).strip()
    
    # Crear párrafos en español puro
    parrafo1 = desc[:280] if len(desc) > 200 else f"{desc} Este desarrollo ha generado amplia atención en los medios internacionales por su trascendencia inmediata."
    
    parrafo2 = "La información ha sido confirmada por diversas fuentes periodísticas, destacando la relevancia del hecho en el contexto internacional actual. Las autoridades competentes continúan evaluando la situación."
    
    parrafo3 = "Analistas políticos y expertos en la materia señalan que este tipo de eventos requiere seguimiento constante por parte de la comunidad global. La cobertura informativa se mantendrá actualizada conforme avancen los acontecimientos."
    
    parrafo4 = f"Los detalles adicionales serán proporcionados a medida que la información esté disponible. Información de {fuente}."
    
    texto = f"{parrafo1}\n\n{parrafo2}\n\n{parrafo3}\n\n{parrafo4}"
    
    # Asegurar longitud
    while len(texto) < 800:
        texto += f" La situación continúa en desarrollo según reportes de {fuente}."
    
    print(f"   ✅ Manual español: {len(texto)} caracteres")
    return {'titular': titulo[:80], 'texto': texto[:1500]}

def expandir_texto_espanol(texto, fuente):
    """Expande texto corto manteniendo español"""
    adicionales = [
        f"\n\nEste acontecimiento ha sido reportado por múltiples medios de comunicación internacionales, destacando su importancia en la agenda global actual.",
        f"\n\nLas reacciones no se han hecho esperar ante este desarrollo significativo que mantiene en alerta a la comunidad internacional.",
        f"\n\nLa cobertura periodística continuará actualizándose conforme se conozcan más detalles sobre esta situación."
    ]
    
    for adicional in adicionales:
        if len(texto) < 800:
            texto += adicional
    
    # Asegurar fuente al final
    if fuente not in texto:
        texto += f"\n\nInformación de {fuente}."
    
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
    """Publica en Facebook"""
    
    # Hashtags
    hashtags = f"#NoticiasMundiales #Actualidad #{datetime.now().strftime('%Y')} #Internacional #Hoy"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    print(f"\n   📝 MENSAJE COMPLETO ({len(mensaje)} caracteres):")
    print(f"   {'-'*50}")
    lineas = mensaje.split('\n')
    for i, linea in enumerate(lineas[:12]):
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
    if len(lineas) > 12:
        print(f"   ... ({len(lineas) - 12} líneas más)")
    print(f"   {'-'*50}")
    
    # Verificación final de español
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con']
    coincidencias = sum(1 for p in palabras_es if p in mensaje.lower())
    print(f"   🔍 Verificación español: {coincidencias}/11 palabras clave")
    
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
        
        # Crear redacción 100% español
        resultado = redactar_espanol_completo(
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
            print("✅ ÉXITO - Todo en español")
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
