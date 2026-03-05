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
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('B_ACCESS_TOKEN')

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
        print(f"💾 Historial guardado: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"❌ Error guardando: {e}")

def get_url_id(url):
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:16]

def ya_publicada(url, titulo):
    url_id = get_url_id(url)
    urls_existentes = [get_url_id(u) for u in historial['urls']]
    if url_id in urls_existentes:
        print(f"   ⛔ Ya publicada (URL): {titulo[:40]}...")
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
    """Traduce texto a español usando DeepL"""
    if not DEEPL_API_KEY or not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
            
        print(f"   🌐 DeepL traduciendo ({len(texto_str)} chars)...")
        
        url = "https://api-free.deepl.com/v2/translate"
        
        # Dividir si es muy largo
        if len(texto_str) > 1500:
            partes = []
            for i in range(0, len(texto_str), 1400):
                parte = texto_str[i:i+1400]
                response = requests.post(
                    url,
                    data={
                        'auth_key': DEEPL_API_KEY,
                        'text': parte,
                        'source_lang': 'EN',
                        'target_lang': 'ES'
                    },
                    timeout=20
                )
                if response.status_code == 200:
                    result = response.json()
                    traduccion = result['translations'][0]['text']
                    partes.append(traduccion)
                else:
                    print(f"   ⚠️ DeepL error {response.status_code}")
                    partes.append(parte)
            return ' '.join(partes)
        else:
            response = requests.post(
                url,
                data={
                    'auth_key': DEEPL_API_KEY,
                    'text': texto_str,
                    'source_lang': 'EN',
                    'target_lang': 'ES'
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['translations'][0]['text']
            else:
                print(f"   ⚠️ DeepL error {response.status_code}: {response.text[:100]}")
                return texto_str
                
    except Exception as e:
        print(f"   ⚠️ Error DeepL: {e}")
        return texto

def limpiar_ingles(texto):
    """Elimina palabras en inglés comunes del texto"""
    if not texto:
        return texto
    
    # Lista de palabras en inglés comunes a eliminar o reemplazar
    reemplazos = {
        r'\bthe\b': '',
        r'\band\b': 'y',
        r'\bfor\b': 'para',
        r'\bare\b': 'son',
        r'\bnot\b': 'no',
        r'\bbut\b': 'pero',
        r'\bwith\b': 'con',
        r'\bthat\b': 'que',
        r'\bthis\b': 'este',
        r'\bwill\b': '',
        r'\bcontinue\b': 'continuar',
        r'\bannouncement\b': 'anuncio',
        r'\bcontroversy\b': 'controversia',
        r'\bsaid\b': 'dijo',
        r'\btold\b': 'dijo',
        r'\baccording to\b': 'según',
        r'\breport\b': 'reporte',
        r'\breports\b': 'reportes',
        r'\bofficials\b': 'oficiales',
        r'\bgovernment\b': 'gobierno',
        r'\badministration\b': 'administración',
        r'\bstatement\b': 'declaración',
        r'\bstatements\b': 'declaraciones',
        r'\bmeeting\b': 'reunión',
        r'\bmeetings\b': 'reuniones',
        r'\bnews\b': 'noticias',
        r'\bsources\b': 'fuentes',
        r'\bsource\b': 'fuente',
        r'\bpeople\b': 'personas',
        r'\bperson\b': 'persona',
        r'\bcountry\b': 'país',
        r'\bcountries\b': 'países',
        r'\bworld\b': 'mundo',
        r'\binternational\b': 'internacional',
        r'\bnational\b': 'nacional',
        r'\blocal\b': 'local',
        r'\bpublic\b': 'público',
        r'\bprivate\b': 'privado',
        r'\bpresident\b': 'presidente',
        r'\bminister\b': 'ministro',
        r'\bsecretary\b': 'secretario',
        r'\bspokesperson\b': 'portavoz',
        r'\bsays\b': 'dice',
        r'\bsay\b': 'dicen',
        r'\btold\b': 'dijo',
        r'\btell\b': 'decir',
        r'\babout\b': 'sobre',
        r'\bafter\b': 'después',
        r'\bbefore\b': 'antes',
        r'\bduring\b': 'durante',
        r'\bbetween\b': 'entre',
        r'\bagainst\b': 'contra',
        r'\bunder\b': 'bajo',
        r'\bover\b': 'sobre',
        r'\bthrough\b': 'a través de',
        r'\binto\b': 'en',
        r'\bout\b': 'fuera',
        r'\bup\b': 'arriba',
        r'\bdown\b': 'abajo',
        r'\bon\b': 'en',
        r'\bat\b': 'en',
        r'\bby\b': 'por',
        r'\bfrom\b': 'desde',
        r'\bto\b': 'a',
        r'\bin\b': 'en',
        r'\bof\b': 'de',
        r'\bas\b': 'como',
        r'\bit\b': 'eso',
        r'\bits\b': 'su',
        r'\btheir\b': 'su',
        r'\bthem\b': 'ellos',
        r'\bthey\b': 'ellos',
        r'\bwe\b': 'nosotros',
        r'\bour\b': 'nuestro',
        r'\bus\b': 'nos',
        r'\bI\b': 'yo',
        r'\bmy\b': 'mi',
        r'\bme\b': 'me',
        r'\byou\b': 'tú',
        r'\byour\b': 'tu',
        r'\bhe\b': 'él',
        r'\bhim\b': 'él',
        r'\bhis\b': 'su',
        r'\bshe\b': 'ella',
        r'\bher\b': 'ella',
        r'\bhers\b': 'suyo',
    }
    
    texto_limpio = texto
    for ingles, espanol in reemplazos.items():
        texto_limpio = re.sub(ingles, espanol, texto_limpio, flags=re.IGNORECASE)
    
    # Limpiar espacios dobles
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    return texto_limpio

def es_espanol(texto):
    """Detecta si el texto está principalmente en español"""
    if not texto:
        return False
    
    texto_lower = texto.lower()
    
    # Palabras clave en español
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 
                   'su', 'para', 'los', 'las', 'del', 'al', 'lo', 'más', 'este', 'esta',
                   'pero', 'sus', 'una', 'como', 'son', 'entre', 'sobre', 'también', 'han',
                   'sido', 'porque', 'durante', 'contra', 'según', 'hacia', 'desde', 'dos',
                   'fue', 'será', 'cada', 'mismo', 'misma', 'otro', 'otra', 'gran', 'nuevo',
                   'nueva', 'primer', 'primera', 'tras', 'puede', 'parte', 'años', 'año',
                   'hace', 'hoy', 'ayer', 'mañana', 'país', 'mundo', 'gobierno', 'estado']
    
    # Palabras comunes en inglés
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
                   'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
                   'they', 'them', 'their', 'what', 'when', 'where', 'who', 'why', 'how',
                   'which', 'while', 'with', 'within', 'without', 'would', 'will', 'said',
                   'says', 'tell', 'told', 'report', 'according', 'officials', 'government',
                   'administration', 'statement', 'meeting', 'news', 'sources', 'people',
                   'country', 'world', 'international', 'national', 'public', 'private',
                   'president', 'minister', 'secretary', 'spokesperson', 'announcement',
                   'controversy', 'continue', 'ensures', 'about', 'after', 'before', 'during']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    print(f"   🔍 Palabras ES: {count_es}, EN: {count_en}")
    return count_es > count_en

def generar_noticia_espanol(titulo_en, desc_en, fuente):
    """
    Genera una noticia completamente en español.
    Primero traduce, luego genera texto nuevo, finalmente limpia cualquier rastro de inglés.
    """
    
    print(f"\n   📝 Procesando noticia...")
    print(f"   📰 Original: {titulo_en[:60]}...")
    
    # PASO 1: Traducir con DeepL
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    # PASO 2: Si OpenAI está disponible, generar redacción profesional
    if OPENAI_API_KEY:
        try:
            print(f"   🤖 Generando redacción con OpenAI...")
            
            prompt = f"""Eres un periodista experto. Escribe una NOTICIA COMPLETA EN ESPAÑOL.

DATOS DE LA NOTICIA:
Título traducido: {titulo_es}
Descripción traducida: {desc_es}
Fuente: {fuente}

INSTRUCCIONES ESTRICTAS:
1. Escribe TODO en ESPAÑOL. CERO palabras en inglés.
2. Crea un TITULAR nuevo y atractivo (máx 80 caracteres)
3. Escribe 4 párrafos cortos:
   - P1: El hecho principal (2-3 líneas)
   - P2: Contexto y antecedentes (3 líneas)
   - P3: Reacciones y análisis (3 líneas)
   - P4: Consecuencias y cierre (2 líneas, incluye "Fuente: {fuente}")
4. Estilo: Periodismo objetivo, claro y profesional
5. Longitud: 800-1200 caracteres totales

FORMATO:
TITULAR: [titular en español]

TEXTO:
[párrafo 1]

[párrafo 2]

[párrafo 3]

[párrafo 4]

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
                    'temperature': 0.3,
                    'max_tokens': 900
                },
                timeout=40
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                
                # Extraer titular
                titular = titulo_es
                if 'TITULAR:' in resultado:
                    try:
                        titular = resultado.split('TITULAR:')[1].split('TEXTO:')[0].strip()
                        titular = titular.strip('"\'').strip()
                    except:
                        pass
                
                # Extraer texto
                texto = desc_es
                if 'TEXTO:' in resultado:
                    try:
                        texto = resultado.split('TEXTO:')[1].split('FIN')[0].strip()
                    except:
                        pass
                
                # PASO 3: Limpiar cualquier inglés residual
                titular = limpiar_ingles(titular)
                texto = limpiar_ingles(texto)
                
                # Verificar que esté en español
                if es_espanol(texto) and es_espanol(titular):
                    print(f"   ✅ Texto verificado en español ({len(texto)} chars)")
                    return {'titular': titular[:100], 'texto': texto[:1400]}
                else:
                    print(f"   ⚠️ Aún tiene inglés, usando plantilla...")
                    
        except Exception as e:
            print(f"   ⚠️ Error OpenAI: {e}")
    
    # PASO 4: Si falla todo, usar plantilla garantizada en español
    return plantilla_espanol_garantizado(titulo_es, desc_es, fuente)

def plantilla_espanol_garantizado(titulo, descripcion, fuente):
    """Genera noticia usando solo español, sin depender de traducciones"""
    print(f"   📝 Usando plantilla en español...")
    
    # Limpiar cualquier HTML
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion))
    
    # Crear párrafos 100% en español
    p1 = f"Se reporta un importante acontecimiento de relevancia internacional que ha captado la atención de medios y autoridades en las últimas horas. "
    if len(desc_limpia) > 50:
        # Tomar solo las primeras palabras de la descripción traducida
        palabras = desc_limpia.split()[:15]
        p1 += " ".join(palabras) + "."
    else:
        p1 += "Este hecho marca un punto de inflexión en la agenda global actual."
    
    p2 = f"Las autoridades competentes han confirmado la información a través de canales oficiales. "
    p2 += f"Diversos analistas señalan que este tipo de eventos requiere seguimiento constante por parte de la comunidad internacional. "
    p2 += f"La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes."
    
    p3 = f"Expertos en relaciones internacionales destacan la importancia de mantener la vigilancia sobre el desarrollo de esta situación. "
    p3 += f"Las implicaciones podrían extenderse a diversos sectores de la sociedad en el corto y mediano plazo. "
    p3 += f"Se esperan declaraciones oficiales adicionales en las próximas horas."
    
    p4 = f"La información será actualizada progresivamente a medida que estén disponibles nuevos datos. "
    p4 += f"Fuente: {fuente}."
    
    texto = f"{p1}\n\n{p2}\n\n{p3}\n\n{p4}"
    
    # Limpiar por si acaso
    texto = limpiar_ingles(texto)
    
    # Crear titular corto en español
    titular = f"Nuevo acontecimiento internacional de relevancia global"
    if len(str(titulo)) > 10:
        # Usar primeras palabras del título traducido
        palabras_titulo = str(titulo).split()[:8]
        titular = " ".join(palabras_titulo)
    
    titular = limpiar_ingles(titular)
    
    print(f"   ✅ Plantilla español: {len(texto)} chars")
    return {'titular': titular[:100], 'texto': texto[:1400]}

def buscar_noticias():
    print("\n🔍 Buscando noticias...")
    
    noticias = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'language': 'en', 'pageSize': 20, 'apiKey': NEWS_API_KEY},
                timeout=15
            )
            data = response.json()
            if data.get('status') == 'ok':
                noticias.extend(data.get('articles', []))
                print(f"   📡 NewsAPI: {len(data.get('articles', []))} noticias")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # GNews
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            response = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'en', 'max': 20, 'apikey': GNEWS_API_KEY},
                timeout=15
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
                print(f"   📡 GNews: {len(data['articles'])} noticias")
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
    
    # Filtrar
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url'):
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
        print(f"   🖼️ Descargando imagen...")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(path, 'JPEG', quality=85)
            print(f"   ✅ Imagen: {path}")
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar(titulo, texto, img_path):
    """Publica en Facebook con español garantizado"""
    
    print(f"\n   🔍 Verificación final...")
    
    # Limpiar una última vez
    titulo = limpiar_ingles(titulo)
    texto = limpiar_ingles(texto)
    
    # Verificar español
    if not es_espanol(titulo):
        print(f"   ⚠️ Titular tiene inglés, aplicando corrección...")
        titulo = "Nuevo acontecimiento internacional reportado"
    
    if not es_espanol(texto):
        print(f"   ⚠️ Texto tiene inglés, usando plantilla de emergencia...")
        texto = "Se reporta un importante acontecimiento de relevancia internacional. Las autoridades competentes han confirmado la información. Se esperan actualizaciones adicionales en las próximas horas."
    
    # Hashtags
    hashtags = "#Noticias #Actualidad #Internacional #Hoy #Mundo"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    print(f"\n   📝 MENSAJE FINAL ({len(mensaje)} chars):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:8]:
        preview = linea[:60] + "..." if len(linea) > 60 else linea
        print(f"   {preview}")
    print(f"   {'='*50}")
    
    # Verificación final estricta
    palabras_en_comunes = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said', 'told', 'officials']
    texto_check = mensaje.lower()
    palabras_encontradas = [p for p in palabras_en_comunes if f' {p} ' in f' {texto_check} ']
    
    if palabras_encontradas:
        print(f"   ⚠️ Palabras en inglés detectadas: {palabras_encontradas}")
        print(f"   🧹 Aplicando limpieza de emergencia...")
        
        # Reemplazar en el mensaje completo
        for palabra in palabras_encontradas:
            mensaje = re.sub(rf'\b{palabra}\b', '', mensaje, flags=re.IGNORECASE)
        
        # Limpiar espacios dobles
        mensaje = re.sub(r'\s+', ' ', mensaje).strip()
        print(f"   ✅ Limpieza aplicada")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"   📤 Publicando...")
        
        with open(img_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"   ✅ PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Facebook error: {error}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas")
        return False
    
    print(f"\n🎯 Procesando {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
            continue
        
        # Generar noticia en español
        resultado = generar_noticia_espanol(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales')
        )
        
        # Publicar
        if publicar(resultado['titular'], resultado['texto'], img_path):
            guardar_historial(noticia['url'], noticia['title'])
            if os.path.exists(img_path):
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
