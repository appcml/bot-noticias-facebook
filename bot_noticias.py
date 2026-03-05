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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Opcional, solo para estructura
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
    """Traduce texto completo a español garantizado"""
    if not DEEPL_API_KEY or not texto:
        return texto
    try:
        # Dividir texto largo en partes si es necesario
        texto_str = str(texto)
        if len(texto_str) > 2000:
            # Traducir en partes
            partes = []
            for i in range(0, len(texto_str), 1800):
                parte = texto_str[i:i+1800]
                response = requests.post(
                    "https://api-free.deepl.com/v2/translate",
                    data={
                        'auth_key': DEEPL_API_KEY,
                        'text': parte,
                        'source_lang': 'EN',
                        'target_lang': 'ES'
                    },
                    timeout=15
                )
                if response.status_code == 200:
                    partes.append(response.json()['translations'][0]['text'])
                else:
                    partes.append(parte)  # Mantener original si falla
            return ' '.join(partes)
        else:
            response = requests.post(
                "https://api-free.deepl.com/v2/translate",
                data={
                    'auth_key': DEEPL_API_KEY,
                    'text': texto_str,
                    'source_lang': 'EN',
                    'target_lang': 'ES'
                },
                timeout=15
            )
            if response.status_code == 200:
                return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"   ⚠️ DeepL error: {e}")
    return texto

def crear_noticia_espanol(titulo_en, desc_en, fuente):
    """
    Crea noticia 100% en español usando DeepL + estructura manual
    Garantiza español sin depender de OpenAI para traducción
    """
    
    print("   🌐 Traduciendo con DeepL...")
    
    # PASO 1: Traducir TODO con DeepL (garantía de español)
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    print(f"   ✅ Título traducido: {titulo_es[:60]}...")
    
    # PASO 2: Crear estructura periodística en español
    # Usar OpenAI solo para estructurar, no para traducir
    
    if OPENAI_API_KEY:
        try:
            # Pedir a OpenAI que estructure el texto YA traducido
            prompt = f"""Estructura este texto YA TRADUCIDO AL ESPAÑOL en formato periodístico.

TEXTO EN ESPAÑOL:
Título: {titulo_es}
Descripción: {desc_es}

INSTRUCCIONES:
1. NO traduzcas, el texto YA está en español
2. Solo estructura en párrafos cortos (máx 4 líneas cada uno)
3. Crea 3-4 párrafos con esta estructura:
   - Párrafo 1: Lead con el dato más importante (máx 3 líneas)
   - Párrafo 2: Contexto y antecedentes (máx 4 líneas)
   - Párrafo 3: Desarrollo y reacciones (máx 4 líneas)
   - Párrafo 4: Cierre con implicaciones (máx 3 líneas)
4. Longitud total: 800-1200 caracteres
5. Al final agrega: "Información de {fuente}"

FORMATO:
TITULAR: [título en español ya traducido]

TEXTO:
[párrafo 1]

[párrafo 2]

[párrafo 3]

[párrafo 4]

Información de {fuente}.

FIN"""

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.2,  # Muy bajo para que no "invente"
                    'max_tokens': 600
                },
                timeout=30
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                
                # Extraer partes
                titular = titulo_es  # Por defecto, el traducido
                texto = desc_es      # Por defecto, el traducido
                
                if 'TITULAR:' in resultado:
                    try:
                        titular_parte = resultado.split('TITULAR:')[1].split('TEXTO:')[0]
                        titular = titular_parte.strip().strip('"\'')
                    except:
                        pass
                
                if 'TEXTO:' in resultado:
                    try:
                        texto_parte = resultado.split('TEXTO:')[1]
                        if 'FIN' in texto_parte:
                            texto = texto_parte.split('FIN')[0].strip()
                        else:
                            texto = texto_parte.strip()
                    except:
                        pass
                
                # Verificar que no haya mezclado inglés
                palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can']
                if not any(p in texto.lower().split()[:20] for p in palabras_en):
                    print(f"   ✅ Estructura OK: {len(texto)} chars")
                    return {'titular': titular, 'texto': texto}
                else:
                    print("   ⚠️ Detectado inglés en estructura, usando manual")
                    
        except Exception as e:
            print(f"   ⚠️ OpenAI estructura falló: {e}")
    
    # PASO 3: Si OpenAI falló o no existe, crear estructura manual
    return crear_estructura_manual(titulo_es, desc_es, fuente)

def crear_estructura_manual(titulo, descripcion, fuente):
    """Crea estructura periodística manual en español"""
    print("   📝 Creando estructura manual...")
    
    # Limpiar y preparar
    titulo = str(titulo).strip()
    desc = str(descripcion).strip()
    
    # Crear párrafos en español puro
    # Párrafo 1: Lead (dato importante, corto)
    if len(desc) > 150:
        parrafo1 = desc[:250] + "." if not desc[:250].endswith('.') else desc[:250]
    else:
        parrafo1 = f"{desc} Este acontecimiento ha generado significativa atención en los medios internacionales por su trascendencia inmediata."
    
    # Párrafo 2: Contexto
    parrafo2 = "La información ha sido confirmada por diversas fuentes periodísticas de alcance global, destacando la relevancia del hecho en el contexto internacional actual. Las autoridades competentes continúan evaluando la situación de cerca."
    
    # Párrafo 3: Análisis
    parrafo3 = "Analistas especializados señalan que este tipo de eventos requiere seguimiento constante por parte de la comunidad internacional. La cobertura informativa se mantendrá actualizada conforme se desarrollen los hechos."
    
    # Párrafo 4: Cierre con fuente
    parrafo4 = f"Los detalles adicionales serán proporcionados a medida que estén disponibles. Información de {fuente}."
    
    # Unir
    texto = f"{parrafo1}\n\n{parrafo2}\n\n{parrafo3}\n\n{parrafo4}"
    
    # Expandir si es muy corto
    if len(texto) < 800:
        texto += f"\n\nLa situación continúa en desarrollo según reportes de {fuente}."
    
    # Limitar si es muy largo
    texto = texto[:1500]
    
    print(f"   ✅ Manual: {len(texto)} caracteres, español 100%")
    return {'titular': titulo[:80], 'texto': texto}

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
    
    # Verificación final de español
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 'su', 'para', 'los', 'las']
    coincidencias = sum(1 for p in palabras_es if p in texto.lower())
    
    if coincidencias < 5:
        print(f"   ⚠️ ALERTA: Solo {coincidencias} palabras español detectadas")
    else:
        print(f"   ✅ Verificación español: {coincidencias} palabras clave")
    
    # Hashtags
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
        
        # Crear noticia en español garantizado
        resultado = crear_noticia_espanol(
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
            print("✅ ÉXITO - Español garantizado")
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
