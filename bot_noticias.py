import requests
import random
import re
import hashlib
import os
import json
import feedparser
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

# Países para hashtags
PAISES_HASHTAG = {
    'united states': '#EEUU', 'usa': '#EEUU', 'estados unidos': '#EEUU',
    'spain': '#España', 'españa': '#España',
    'mexico': '#México', 'méxico': '#México',
    'argentina': '#Argentina',
    'colombia': '#Colombia',
    'chile': '#Chile',
    'peru': '#Perú', 'perú': '#Perú',
    'venezuela': '#Venezuela',
    'brazil': '#Brasil', 'brasil': '#Brasil',
    'france': '#Francia', 'francia': '#Francia',
    'germany': '#Alemania', 'alemania': '#Alemania',
    'italy': '#Italia', 'italia': '#Italia',
    'uk': '#ReinoUnido', 'united kingdom': '#ReinoUnido',
    'china': '#China',
    'russia': '#Rusia', 'rusia': '#Rusia',
    'ukraine': '#Ucrania', 'ucrania': '#Ucrania',
    'israel': '#Israel',
    'iran': '#Irán', 'irán': '#Irán',
    'japan': '#Japón', 'japón': '#Japón',
    'india': '#India',
    'canada': '#Canadá',
    'australia': '#Australia',
    'south korea': '#CoreaDelSur',
    'north korea': '#CoreaDelNorte',
    'syria': '#Siria',
    'lebanon': '#Líbano', 'líbano': '#Líbano',
    'turkey': '#Turquía', 'turquía': '#Turquía',
    'poland': '#Polonia',
    'ukraine': '#Ucrania'
}

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'fechas': {}}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"📚 Historial: {len(historial['urls'])} noticias guardadas")
    except Exception as e:
        print(f"⚠️ Error cargando historial: {e}")

def guardar_historial(url, titulo):
    """Guarda la noticia en el historial"""
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['fechas'][url] = datetime.now().isoformat()
    
    # Mantener solo últimas 200
    historial['urls'] = historial['urls'][-200:]
    historial['titulos'] = historial['titulos'][-200:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Guardada en historial")
    except Exception as e:
        print(f"❌ Error guardando: {e}")

def get_url_id(url):
    """Genera ID único para URL"""
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:12]

def ya_publicada(url, titulo):
    """Verifica si la noticia ya fue publicada"""
    url_id = get_url_id(url)
    urls_existentes = [get_url_id(u) for u in historial['urls']]
    
    if url_id in urls_existentes:
        print(f"   ⛔ Ya publicada (URL)")
        return True
    
    # Verificar título similar
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:30]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:30]
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if len(titulo_simple) > 10 and coincidencia / len(titulo_simple) > 0.8:
                print(f"   ⛔ Título muy similar")
                return True
    
    return False

def detectar_pais(titulo, descripcion):
    """Detecta el país de la noticia para el hashtag"""
    texto = f"{titulo} {descripcion}".lower()
    
    for pais, hashtag in PAISES_HASHTAG.items():
        if pais in texto:
            return hashtag
    
    # Detectar por contexto
    if any(x in texto for x in ['washington', 'white house', 'pentagon', 'congress']):
        return '#EEUU'
    if any(x in texto for x in ['madrid', 'barcelona', 'sánchez', 'sanchez']):
        return '#España'
    if any(x in texto for x in ['london', 'uk parliament', 'downing street']):
        return '#ReinoUnido'
    
    return '#Internacional'

def limpiar_texto(texto):
    """Limpia texto de URLs y caracteres raros"""
    if not texto:
        return ""
    texto = re.sub(r'http[s]?://\S+', '', texto)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'[^\w\s.,;:!?áéíóúÁÉÍÓÚñÑüÜ\-]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def traducir_a_espanol(texto):
    """Traduce texto a español usando IA"""
    if not OPENROUTER_API_KEY:
        return texto
    
    try:
        prompt = f"""Traduce este texto al español de forma natural y periodística:

{texto[:800]}

Traducción profesional:"""

        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'HTTP-Referer': 'https://github.com',
                'X-Title': 'Bot Noticias',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'mistralai/mistral-7b-instruct:free',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 800
            },
            timeout=45
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data:
                traduccion = data['choices'][0]['message']['content'].strip()
                if len(traduccion) > 50:
                    return traduccion
                    
    except Exception as e:
        print(f"   ⚠️ Error traducción: {e}")
    
    return texto

def redactar_noticia_profesional(titulo_original, descripcion_original, fuente):
    """
    Redacta noticia con estilo periodístico profesional.
    Usa IA para crear texto completamente nuevo en español.
    """
    
    print(f"\n   📝 Redactando noticia profesional...")
    print(f"   📰 Original: {titulo_original[:60]}")
    
    # Traducir contenido a español primero
    titulo_es = traducir_a_espanol(titulo_original)
    descripcion_es = traducir_a_espanol(descripcion_original)
    
    # Detectar país para hashtag
    pais_hashtag = detectar_pais(titulo_original, descripcion_original)
    
    if OPENROUTER_API_KEY:
        # PROMPT PROFESIONAL PARA LA IA
        prompt = f"""Actúa como periodista profesional de un medio digital serio.

DATOS DE LA NOTICIA:
Título: {titulo_es}
Descripción: {descripcion_es}
Fuente: {fuente}

INSTRUCCIONES ESTRICTAS:

1. Escribe una NOTICIA COMPLETAMENTE NUEVA en español.
2. NO copies el texto original.
3. Redacta con estilo periodístico profesional.
4. Tono: neutral, informativo, claro y ordenado.
5. Longitud: entre 500 y 900 caracteres totales.

ESTRUCTURA OBLIGATORIA:

TÍTULO (máx 80 caracteres, llamativo e informativo)

PÁRRAFO ÚNICO (4-6 oraciones que expliquen los hechos principales):
- Primera oración: el dato más importante (quién, qué, cuándo)
- Oraciones siguientes: contexto, detalles y reacciones
- Última oración: implicación o próximo paso

HASHTAGS (exactamente 5 hashtags al final):
- 4 hashtags temáticos (#politica #economia #mundo #deportes #tecnologia #salud etc.)
- 1 hashtag del país: {pais_hashtag}

REGLAS:
- Español nativo, no traducción literal
- Oraciones completas con punto final
- Sin párrafos separados, solo UN párrafo de texto
- Sin frases genéricas como "se esperan actualizaciones"
- Sin repetir información

FORMATO DE SALIDA EXACTO:

TITULO: [título aquí]

TEXTO: [párrafo único aquí]

HASHTAGS: [5 hashtags separados por espacio]

FIN"""

        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'HTTP-Referer': 'https://github.com',
                    'X-Title': 'Bot Noticias',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'mistralai/mistral-7b-instruct:free',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.4,
                    'max_tokens': 1000
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    
                    # Extraer partes
                    titulo = extraer_seccion(content, 'TITULO:', 'TEXTO:')
                    texto = extraer_seccion(content, 'TEXTO:', 'HASHTAGS:')
                    hashtags = extraer_seccion(content, 'HASHTAGS:', 'FIN')
                    
                    # Limpiar
                    titulo = limpiar_texto(titulo)
                    texto = limpiar_texto(texto)
                    hashtags = limpiar_texto(hashtags)
                    
                    # Verificar calidad
                    if (titulo and texto and hashtags and 
                        500 <= len(texto) <= 900 and 
                        len(titulo) < 100):
                        
                        print(f"   ✅ IA redactó: {len(texto)} caracteres")
                        return {
                            'titulo': titulo,
                            'texto': texto,
                            'hashtags': hashtags,
                            'pais': pais_hashtag
                        }
                        
        except Exception as e:
            print(f"   ⚠️ Error IA: {e}")
    
    # Fallback: generar manualmente
    return redactar_manual(titulo_es, descripcion_es, fuente, pais_hashtag)

def extraer_seccion(texto, inicio, fin):
    """Extrae una sección del texto"""
    try:
        if inicio in texto:
            parte = texto.split(inicio)[1]
            if fin in parte:
                return parte.split(fin)[0].strip()
            return parte.strip()[:500]
    except:
        pass
    return ""

def redactar_manual(titulo, descripcion, fuente, pais_hashtag):
    """Genera noticia manualmente si la IA falla"""
    print(f"   📝 Redacción manual...")
    
    # Crear título
    titulo_final = titulo[:80] if len(titulo) > 20 else "Nuevo acontecimiento internacional"
    
    # Crear párrafo único
    oraciones = [s.strip() for s in descripcion.split('.') if len(s.strip()) > 20]
    
    if len(oraciones) >= 2:
        parrafo = f"{oraciones[0]}. {oraciones[1]}."
    elif oraciones:
        parrafo = f"{oraciones[0]}. Las autoridades competentes confirmaron la información oficialmente."
    else:
        parrafo = f"Se reporta un importante acontecimiento de relevancia internacional. Las autoridades competentes han confirmado la información en las últimas horas."
    
    # Expandir si es muy corto
    while len(parrafo) < 500:
        parrafo += " Los expertos consultados destacan la trascendencia de este hecho en el contexto actual."
        if len(parrafo) >= 500:
            break
    
    # Cortar si es muy largo
    if len(parrafo) > 900:
        parrafo = parrafo[:897].rsplit(' ', 1)[0] + "."
    
    # Hashtags por defecto
    hashtags = f"#Noticias #Actualidad #Mundo {pais_hashtag} #Hoy"
    
    print(f"   ✅ Manual: {len(parrafo)} caracteres")
    return {
        'titulo': titulo_final,
        'texto': parrafo,
        'hashtags': hashtags,
        'pais': pais_hashtag
    }

def buscar_noticias_recientes():
    """Busca noticias de las últimas 24 horas"""
    print("\n🔍 Buscando noticias recientes...")
    noticias = []
    
    fecha_limite = datetime.now() - timedelta(hours=24)
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    'language': 'en',
                    'pageSize': 20,
                    'apiKey': NEWS_API_KEY
                },
                timeout=15
            )
            data = response.json()
            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    # Verificar fecha
                    fecha_str = art.get('publishedAt', '')
                    try:
                        fecha_art = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                        if fecha_art >= fecha_limite:
                            noticias.append(art)
                    except:
                        noticias.append(art)  # Si no puede parsear, incluir igual
                print(f"   📡 NewsAPI: {len(noticias)} noticias")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # GNews
    if GNEWS_API_KEY and len(noticias) < 10:
        try:
            response = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={
                    'lang': 'en',
                    'max': 15,
                    'apikey': GNEWS_API_KEY
                },
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
                        'source': {'name': a.get('source', {}).get('name', 'GNews')},
                        'publishedAt': datetime.now().isoformat()
                    })
                print(f"   📡 GNews: {len(data['articles'])} noticias")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # RSS feeds
    rss_feeds = [
        'http://feeds.bbci.co.uk/news/world/rss.xml',
        'https://www.reuters.com/rssFeed/worldNews'
    ]
    
    for feed_url in random.sample(rss_feeds, min(2, len(rss_feeds))):
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                # Buscar imagen
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
                    'source': {'name': feed.feed.get('title', 'RSS')},
                    'publishedAt': datetime.now().isoformat()
                })
            print(f"   📡 RSS: {feed_url.split('/')[2]}")
        except:
            pass
    
    print(f"\n📊 Total encontradas: {len(noticias)}")
    
    # Filtrar nuevas y válidas
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 15:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('url'):
            continue
        
        if ya_publicada(art['url'], art['title']):
            continue
        
        nuevas.append(art)
        print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Nuevas válidas: {len(nuevas)}")
    return nuevas[:3]

def descargar_imagen(url):
    """Descarga imagen de la noticia"""
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
            print(f"   ✅ Imagen descargada")
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar_en_facebook(titulo, texto, hashtags, img_path):
    """Publica en Facebook con formato profesional"""
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales de Facebook")
        return False
    
    # Construir mensaje final
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Verificar longitud
    if len(mensaje) > 2200:
        texto_cortado = texto[:1800]
        mensaje = f"""📰 {titulo}

{texto_cortado}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Preview
    print(f"\n   📝 VISTA PREVIA ({len(mensaje)} caracteres):")
    print(f"   {'═'*55}")
    lineas = mensaje.split('\n')
    for i, linea in enumerate(lineas[:10]):
        if i == 0:
            print(f"   🎯 {linea[:50]}")
        elif linea.strip() == '':
            print(f"   ")
        else:
            preview = linea[:52] + "..." if len(linea) > 52 else linea
            print(f"   {preview}")
    print(f"   {'═'*55}")
    
    # Publicar
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
                print(f"   ✅ PUBLICADO EXITOSAMENTE")
                print(f"   🆔 ID: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Error Facebook: {error}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    """Función principal del bot"""
    
    # Verificar configuración
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ ERROR: Faltan credenciales de Facebook")
        print("   Configura FB_PAGE_ID y FB_ACCESS_TOKEN")
        return False
    
    if not OPENROUTER_API_KEY and not (NEWS_API_KEY or GNEWS_API_KEY):
        print("❌ ERROR: Se necesita al menos una API de noticias o OpenRouter")
        return False
    
    # Buscar noticias
    noticias = buscar_noticias_recientes()
    
    if not noticias:
        print("\n⚠️ No se encontraron noticias nuevas")
        return False
    
    print(f"\n🎯 Intentando publicar {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 PROCESANDO NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen disponible, saltando...")
            continue
        
        # Redactar noticia profesional
        resultado = redactar_noticia_profesional(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Agencias')
        )
        
        # Publicar
        exito = publicar_en_facebook(
            resultado['titulo'],
            resultado['texto'],
            resultado['hashtags'],
            img_path
        )
        
        if exito:
            # Guardar en historial
            guardar_historial(noticia['url'], noticia['title'])
            
            # Limpiar imagen
            if os.path.exists(img_path):
                os.remove(img_path)
            
            print(f"\n{'='*60}")
            print("✅ PUBLICACIÓN COMPLETADA")
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
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
