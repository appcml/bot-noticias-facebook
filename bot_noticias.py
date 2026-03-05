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
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

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
    
    # Verificar título similar
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
        print(f"   ⚠️ DeepL no configurado o texto vacío")
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
            
        print(f"   🌐 Traduciendo con DeepL ({len(texto_str)} chars)...")
        
        # DeepL Free API endpoint
        url = "https://api-free.deepl.com/v2/translate"
        
        # Si el texto es muy largo, dividirlo
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
                    print(f"   ✅ Parte traducida: {traduccion[:50]}...")
                else:
                    print(f"   ❌ DeepL error {response.status_code}: {response.text[:200]}")
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
                traduccion = result['translations'][0]['text']
                print(f"   ✅ Traducido: {traduccion[:60]}...")
                return traduccion
            else:
                print(f"   ❌ DeepL error {response.status_code}: {response.text[:200]}")
                return texto_str
                
    except Exception as e:
        print(f"   ❌ Error DeepL: {e}")
        return texto

def es_espanol(texto):
    """Detecta si el texto está en español"""
    if not texto:
        return False
    
    texto_lower = texto.lower()
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 
                   'su', 'para', 'los', 'las', 'del', 'al', 'lo', 'más', 'este', 'esta',
                   'pero', 'sus', 'una', 'como', 'son', 'entre', 'sobre', 'también', 'han',
                   'sido', 'porque', 'durante', 'contra', 'según', 'hacia', 'desde']
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
                   'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
                   'they', 'them', 'their', 'what', 'when', 'where', 'who', 'why', 'how']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    print(f"   🔍 Detección idioma: ES={count_es}, EN={count_en}")
    return count_es > count_en

def crear_noticia_original(titulo_en, desc_en, fuente):
    """
    Crea una noticia COMPLETAMENTE NUEVA redactada en español.
    NO traduce, CREA contenido nuevo basado en la noticia original.
    """
    
    print(f"\n   📝 Creando noticia original en español...")
    print(f"   📰 Título original: {titulo_en[:60]}")
    
    # PASO 1: Traducir para entender el contenido (solo para procesamiento interno)
    titulo_traducido = traducir_deepl(titulo_en)
    desc_traducida = traducir_deepl(desc_en)
    
    # Verificar que DeepL funcionó
    if not es_espanol(titulo_traducido):
        print(f"   ⚠️ DeepL falló en título, usando traducción alternativa...")
        # Intentar con OpenAI si está disponible
        if OPENAI_API_KEY:
            titulo_traducido = traducir_con_openai(titulo_en)
    
    if not es_espanol(desc_traducida):
        print(f"   ⚠️ DeepL falló en descripción...")
        if OPENAI_API_KEY:
            desc_traducida = traducir_con_openai(desc_en)
    
    # PASO 2: Crear redacción periodística original en español
    if OPENAI_API_KEY:
        try:
            print(f"   🤖 Generando redacción con OpenAI...")
            
            prompt = f"""Eres un redactor de noticias profesional. DEBES escribir en ESPAÑOL.

INFORMACIÓN DE LA NOTICIA (traducida al español):
Título: {titulo_traducido}
Descripción: {desc_traducida}
Fuente original: {fuente}

TU TAREA:
Escribe una NOTICIA COMPLETA Y ORIGINAL en ESPAÑOL. NO copies el texto anterior.
Crea una redacción periodística profesional con:

1. UN TITULAR NUEVO en español (máximo 80 caracteres, llamativo)
2. CUATRO PÁRRAFOS en español:
   - Lead: El hecho más importante (2-3 líneas)
   - Contexto: Antecedentes relevantes (3-4 líneas)
   - Desarrollo: Detalles y reacciones (3-4 líneas)
   - Cierre: Consecuencias o próximos pasos (2-3 líneas)

REGLAS ESTRICTAS:
- TODO el texto debe estar en ESPAÑOL
- NO uses palabras en inglés
- Longitud total: 900-1300 caracteres
- Estilo: Periodismo objetivo e informativo
- Al final agrega: "Fuente: {fuente}"

FORMATO DE RESPUESTA:
TITULAR: [titular en español]

TEXTO:
[párrafo 1]

[párrafo 2]

[párrafo 3]

[párrafo 4]

Fuente: {fuente}.

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
                    'temperature': 0.4,
                    'max_tokens': 1000
                },
                timeout=45
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                print(f"   ✅ OpenAI respondió ({len(resultado)} chars)")
                
                # Extraer titular
                titular = titulo_traducido  # fallback
                if 'TITULAR:' in resultado:
                    try:
                        titular = resultado.split('TITULAR:')[1].split('TEXTO:')[0].strip()
                        titular = titular.strip('"\'').strip()
                        # Verificar que no esté en inglés
                        if not es_espanol(titular):
                            print(f"   ⚠️ Titular en inglés detectado, usando traducido")
                            titular = titulo_traducido
                    except Exception as e:
                        print(f"   ⚠️ Error extrayendo titular: {e}")
                
                # Extraer texto
                texto = desc_traducida  # fallback
                if 'TEXTO:' in resultado:
                    try:
                        texto_parte = resultado.split('TEXTO:')[1]
                        if 'FIN' in texto_parte:
                            texto = texto_parte.split('FIN')[0].strip()
                        else:
                            texto = texto_parte.strip()
                        
                        # Verificar español
                        if not es_espanol(texto):
                            print(f"   ⚠️ Texto tiene inglés, usando generación manual")
                            return redaccion_manual(titulo_traducido, desc_traducida, fuente)
                            
                    except Exception as e:
                        print(f"   ⚠️ Error extrayendo texto: {e}")
                
                print(f"   ✅ Redacción OK: {len(texto)} chars")
                return {'titular': titular[:100], 'texto': texto[:1500]}
            else:
                print(f"   ❌ OpenAI error {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Error OpenAI: {e}")
    
    # Si OpenAI no está disponible o falló, usar redacción manual
    return redaccion_manual(titulo_traducido, desc_traducida, fuente)

def traducir_con_openai(texto):
    """Traducción de respaldo usando OpenAI"""
    try:
        prompt = f"""Traduce este texto al ESPAÑOL. Solo devuelve la traducción, nada más:

Texto: {texto}

Traducción en español:"""

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 500
            },
            timeout=20
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except:
        pass
    return texto

def redaccion_manual(titulo, descripcion, fuente):
    """Crea redacción manual garantizada en español"""
    print(f"   📝 Creando redacción manual...")
    
    # Limpiar
    titulo = str(titulo).strip()
    desc = re.sub(r'<[^>]+>', '', str(descripcion)).strip()
    
    # Extraer palabras clave del título para hacerlo más informativo
    palabras_clave = titulo.replace(':', ' ').replace('-', ' ').replace(',', ' ')
    
    # Crear párrafos variados basados en el contenido
    parrafo1 = f"{desc[:300] if len(desc) > 200 else desc} Este acontecimiento ha generado considerable repercusión en los ámbitos político y social a nivel internacional."
    
    parrafo2 = f"Las autoridades competentes y diversos actores del escenario global han manifestado su posición respecto a estos hechos. La comunidad internacional mantiene atenta vigilancia sobre el desarrollo de la situación."
    
    parrafo3 = f"Analistas políticos señalan que este tipo de acontecimientos podría tener implicaciones significativas en las relaciones bilaterales y multilaterales. La cobertura mediática continúa ampliándose conforme surgen nuevos detalles."
    
    parrafo4 = f"Se espera que en las próximas horas se proporcionen actualizaciones adicionales sobre este tema de relevancia internacional. Fuente: {fuente}."
    
    texto = f"{parrafo1}\n\n{parrafo2}\n\n{parrafo3}\n\n{parrafo4}"
    
    # Asegurar longitud
    if len(texto) < 800:
        texto += f"\n\nLa información será actualizada progresivamente según reportes de {fuente}."
    
    print(f"   ✅ Manual: {len(texto)} chars")
    return {'titular': titulo[:100], 'texto': texto[:1500]}

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
            print(f"   ⚠️ NewsAPI error: {e}")
    
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
            print(f"   ⚠️ GNews error: {e}")
    
    # RSS Feeds
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
            except Exception as e:
                print(f"   ⚠️ RSS error: {e}")
    
    print(f"\n📊 Total noticias encontradas: {len(noticias)}")
    
    # Filtrar nuevas y válidas
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
    
    print(f"📊 Noticias nuevas: {len(nuevas)}")
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
            print(f"   ✅ Imagen guardada: {path}")
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar(titulo, texto, img_path):
    """Publica en Facebook con verificación final"""
    
    print(f"\n   🔍 Verificación final de idioma...")
    
    # Verificación estricta
    if not es_espanol(titulo):
        print(f"   ❌ ALERTA: Titular en inglés detectado: {titulo[:50]}")
        titulo = traducir_deepl(titulo)
        if not es_espanol(titulo):
            titulo = "Noticia Internacional"  # Último recurso
    
    if not es_espanol(texto):
        print(f"   ❌ ALERTA: Texto contiene inglés")
        # Intentar traducir párrafos con inglés
        lineas = texto.split('\n')
        lineas_traducidas = []
        for linea in lineas:
            if linea.strip() and not es_espanol(linea):
                linea = traducir_deepl(linea)
            lineas_traducidas.append(linea)
        texto = '\n'.join(lineas_traducidas)
    
    # Hashtags en español
    hashtags = "#Noticias #Actualidad #Internacional #Hoy #Mundo #NoticiasDelDía"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    print(f"\n   📝 PREVIEW ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    for i, linea in enumerate(mensaje.split('\n')[:6]):
        preview = linea[:60] + "..." if len(linea) > 60 else linea
        print(f"   {preview}")
    if len(mensaje.split('\n')) > 6:
        print(f"   ... ({len(mensaje.split(chr(10))) - 6} líneas más)")
    print(f"   {'='*50}")
    
    # Verificación final
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'polls', 'attacks', 'sold']
    texto_lower = mensaje.lower()
    encontradas = [p for p in palabras_en if p in texto_lower]
    if encontradas:
        print(f"   ⚠️ Palabras en inglés detectadas: {encontradas}")
        print(f"   ❌ PUBLICACIÓN CANCELADA - Requiere revisión")
        return False
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"   📤 Publicando en Facebook...")
        
        with open(img_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"   ✅ PUBLICADO EXITOSAMENTE: {result['id']}")
                return True
            else:
                error_msg = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Facebook error: {error_msg}")
                
    except Exception as e:
        print(f"   ❌ Error publicando: {e}")
    
    return False

def main():
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas disponibles")
        return False
    
    print(f"\n🎯 Procesando {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Saltando: Sin imagen válida")
            continue
        
        # Crear noticia en español (redacción original, no traducción literal)
        resultado = crear_noticia_original(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales')
        )
        
        titulo = resultado['titular']
        texto = resultado['texto']
        
        # Publicar
        if publicar(titulo, texto, img_path):
            guardar_historial(noticia['url'], noticia['title'])
            if os.path.exists(img_path):
                os.remove(img_path)
            print(f"\n{'='*60}")
            print("✅ ÉXITO: Noticia publicada en español")
            print(f"{'='*60}")
            return True
        
        # Limpiar si falló
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\n❌ No se pudo publicar ninguna noticia")
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
