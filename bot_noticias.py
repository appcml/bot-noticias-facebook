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

print(f"🔍 Configuración:")
print(f"   NEWS_API_KEY: {bool(NEWS_API_KEY)}")
print(f"   GNEWS_API_KEY: {bool(GNEWS_API_KEY)}")
print(f"   OPENAI_API_KEY: {bool(OPENAI_API_KEY)}")
print(f"   FB_PAGE_ID: {bool(FB_PAGE_ID)}")
print(f"   FB_ACCESS_TOKEN: {bool(FB_ACCESS_TOKEN)}")
print(f"   DEEPL_API_KEY: {bool(DEEPL_API_KEY)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN]):
    raise ValueError("❌ Faltan credenciales de Facebook")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY es obligatorio para la redacción")

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000

RSS_FEEDS = [
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.reuters.com/rssFeed/worldNews',
    'https://feeds.npr.org/1001/rss.xml',
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.politico.com/politics/news.xml',
    'https://rss.cnn.com/rss/edition_world.rss',
    'https://feeds.huffpost.com/HuffPostWorld',
]

def normalizar_url(url):
    if not url:
        return ""
    url, _ = urldefrag(url)
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url_limpia = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, nuevo_query, ''
        ))
        return url_limpia.lower().strip().rstrip('/')
    except:
        return url.lower().strip().rstrip('/')

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                urls = set(data.get('urls', []))
                hashes = set(data.get('hashes', []))
                print(f"📚 Historial cargado: {len(urls)} URLs")
                return urls, hashes
        except:
            pass
    print("📚 Nuevo historial")
    return set(), set()

def guardar_historial(urls, hashes):
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': list(hashes)[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat()
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Historial guardado: {len(urls)} URLs")

HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_deepl(texto):
    """Traducción con DeepL si está disponible"""
    if not DEEPL_API_KEY or not texto:
        return texto
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto[:1500],
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"⚠️ DeepL error: {e}")
    return texto

def redactar_noticia_profesional(titulo_ingles, descripcion_ingles, fuente, categoria):
    """
    Genera una redacción profesional en español usando OpenAI.
    Retorna: (titular, cuerpo) o (None, None) si falla
    """
    
    # Primero traducimos para dar contexto en español a OpenAI
    titulo_es = traducir_deepl(titulo_ingles)
    desc_es = traducir_deepl(descripcion_ingles)
    
    system_prompt = """Eres un periodista profesional de un medio de comunicación internacional reconocido. 
Tu trabajo es redactar noticias en ESPAÑOL con alto nivel periodístico.
REGLAS ESTRICTAS:
1. ESCRIBE ÚNICAMENTE EN ESPAÑOL
2. Tono: profesional, objetivo, informativo, serio
3. Estructura: titular impactante + lead (párrafo introductorio) + desarrollo (2-3 párrafos) + contexto
4. Longitud: mínimo 200 palabras, máximo 350 palabras
5. NO uses frases genéricas como "según fuentes" o "se espera que"
6. Incluye detalles específicos de la noticia
7. Cierra con una reflexión o proyección sobre el tema"""

    user_prompt = f"""REDACTA ESTA NOTICIA EN ESPAÑOL PROFESIONAL:

DATOS BRUTOS:
- Título original (EN): {titulo_ingles}
- Descripción original (EN): {descripcion_ingles}
- Traducción preliminar título: {titulo_es}
- Traducción preliminar descripción: {desc_es}
- Fuente: {fuente}
- Categoría: {categoria}

INSTRUCCIONES DE REDACCIÓN:
1. Crea un TITULAR impactante en español (máximo 90 caracteres)
2. Escribe un LEAD (primer párrafo) que resuma la noticia con los datos más importantes
3. Desarrolla 2-3 párrafos con información detallada, contexto e implicaciones
4. Incluye el nombre de la fuente: {fuente}
5. Mantiene objetividad periodística
6. Usa conectores lógicos (por su parte, en este contexto, según los datos, etc.)

FORMATO DE RESPUESTA OBLIGATORIO:
TITULAR_FINAL: [titular en español profesional]

CUERPO_NOTICIA: [texto completo redactado en español, mínimo 200 palabras, dividido en párrafos con saltos de línea]

FIN_NOTICIA"""

    try:
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': 0.6,
            'max_tokens': 800
        }
        
        print("🤖 OpenAI generando redacción profesional...")
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"❌ OpenAI HTTP {response.status_code}: {response.text[:300]}")
            return None, None
        
        resultado = response.json()['choices'][0]['message']['content']
        print("✅ Redacción recibida de OpenAI")
        
        # Parsear resultado
        titular_final = None
        cuerpo_noticia = None
        
        lines = resultado.split('\n')
        en_cuerpo = False
        lineas_cuerpo = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith('TITULAR_FINAL:'):
                titular_final = line_stripped.replace('TITULAR_FINAL:', '').strip()
                # Limpiar comillas si las hay
                titular_final = titular_final.strip('"\'')
                
            elif line_stripped.startswith('CUERPO_NOTICIA:'):
                en_cuerpo = True
                
            elif line_stripped.startswith('FIN_NOTICIA'):
                break
                
            elif en_cuerpo and line_stripped:
                lineas_cuerpo.append(line_stripped)
        
        # Unir líneas del cuerpo
        if lineas_cuerpo:
            cuerpo_noticia = '\n\n'.join(lineas_cuerpo)
        
        # Validar resultado
        if not titular_final or not cuerpo_noticia:
            print("⚠️ No se pudo parsear la respuesta de OpenAI correctamente")
            print(f"Respuesta cruda: {resultado[:500]}...")
            return None, None
            
        if len(cuerpo_noticia.split()) < 50:  # Muy corto
            print(f"⚠️ Texto muy corto ({len(cuerpo_noticia.split())} palabras)")
            return None, None
            
        print(f"✅ Titular: {titular_final[:60]}...")
        print(f"✅ Cuerpo: {len(cuerpo_noticia.split())} palabras")
        
        return titular_final, cuerpo_noticia
        
    except Exception as e:
        print(f"❌ Error en redacción OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def generar_5_hashtags(categoria, titular):
    """Genera exactamente 5 hashtags relevantes"""
    
    # Hashtags base por categoría
    base = {
        'crisis': ['#ÚltimaHora', '#CrisisInternacional', '#AlertaMundial', '#NoticiasEnDesarrollo'],
        'tech': ['#Tecnología', '#Innovación', '#InteligenciaArtificial', '#TechNews'],
        'economia': ['#EconomíaGlobal', '#MercadosFinancieros', '#NegociosInternacionales'],
        'politica': ['#PolíticaInternacional', '#DiplomaciaGlobal', '#ActualidadPolítica'],
        'internacional': ['#NoticiasMundiales', '#ActualidadInternacional', '#WorldNews']
    }
    
    tags = base.get(categoria, base['internacional']).copy()
    
    # Agregar hashtag del año siempre
    tags.append(f"#{datetime.now().strftime('%Y')}")
    
    # Extraer palabra clave del titular para hashtag personalizado
    palabras_clave = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b', titular)
    palabras_filtradas = [p for p in palabras_clave if p.lower() not in 
                         ['esta', 'este', 'para', 'con', 'los', 'las', 'del', 'por', 'una', 'noticia']]
    
    if palabras_filtradas:
        # Tomar la primera palabra clave significativa
        hashtag_custom = '#' + palabras_filtradas[0]
        if hashtag_custom not in tags:
            tags.append(hashtag_custom)
    
    # Si tenemos menos de 5, agregar genéricos
    genericos = ['#Internacional', '#Global', '#Actualidad', '#Mundo', '#Hoy']
    for gen in genericos:
        if len(tags) >= 5:
            break
        if gen not in tags:
            tags.append(gen)
    
    return ' '.join(tags[:5])

def buscar_newsapi():
    if not NEWS_API_KEY:
        return []
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'category': 'general',
            'language': 'en',
            'pageSize': 20,
            'apiKey': NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get('status') == 'ok':
            return data.get('articles', [])
    except Exception as e:
        print(f"⚠️ NewsAPI error: {e}")
    return []

def buscar_gnews():
    if not GNEWS_API_KEY:
        return []
    try:
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'lang': 'en',
            'max': 20,
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
    except Exception as e:
        print(f"⚠️ GNews error: {e}")
    return []

def buscar_rss():
    noticias = []
    feeds = random.sample(RSS_FEEDS, min(3, len(RSS_FEEDS)))
    
    for feed_url in feeds:
        try:
            print(f"📡 RSS: {feed_url.split('/')[2]}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:8]:
                imagen = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', entry.summary, re.I)
                    if match:
                        imagen = match.group(1)
                
                noticias.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', ''))[:400],
                    'url': entry.get('link', ''),
                    'urlToImage': imagen,
                    'publishedAt': entry.get('published', ''),
                    'source': {'name': feed.feed.get('title', 'RSS Feed')}
                })
        except Exception as e:
            print(f"⚠️ RSS error: {e}")
    return noticias

def detectar_categoria(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    
    if any(p in texto for p in ['war', 'attack', 'invasion', 'missile', 'bomb', 'conflict', 'crisis', 'war']):
        return 'crisis'
    elif any(p in texto for p in ['tech', 'ai', 'artificial intelligence', 'software', 'digital', 'app', 'technology']):
        return 'tech'
    elif any(p in texto for p in ['economy', 'market', 'stock', 'financial', 'trade', 'economic', 'inflation']):
        return 'economia'
    elif any(p in texto for p in ['politics', 'election', 'president', 'government', 'minister', 'vote', 'political']):
        return 'politica'
    return 'internacional'

def buscar_noticias():
    print(f"\n{'='*60}")
    print(f"🔍 BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    todas = []
    
    # Intentar NewsAPI
    noticias = buscar_newsapi()
    todas.extend(noticias)
    print(f"📡 NewsAPI: {len(noticias)} artículos")
    
    # Si no hay suficientes, GNews
    if len(todas) < 5:
        noticias = buscar_gnews()
        todas.extend(noticias)
        print(f"📡 GNews: {len(noticias)} artículos")
    
    # Si aún falta, RSS
    if len(todas) < 3:
        noticias = buscar_rss()
        todas.extend(noticias)
        print(f"📡 RSS: {len(noticias)} artículos")
    
    print(f"\n📊 Total recopilado: {len(todas)}")
    
    # Procesar y filtrar
    validas = []
    for art in todas:
        # Validaciones básicas
        if not art.get('title') or len(art['title']) < 15:
            continue
        if "[Removed]" in art['title']:
            continue
        if not art.get('description') or len(art['description']) < 50:
            continue
        if not art.get('url') or not art['url'].startswith('http'):
            continue
        
        # Verificar duplicados
        url_norm = normalizar_url(art['url'])
        url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
        
        if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
            print(f"⏭️  Ya publicada: {art['title'][:50]}...")
            continue
        
        # Detectar categoría en inglés primero
        categoria = detectar_categoria(art['title'], art['description'])
        
        art.update({
            'url_normalizada': url_norm,
            'url_hash': url_hash,
            'categoria': categoria,
            'titulo_original': art['title'],
            'descripcion_original': art['description']
        })
        
        validas.append(art)
        print(f"✅ Nueva candidata: {art['title'][:50]}... [{categoria}]")
    
    print(f"📊 Válidas: {len(validas)}")
    
    # Solo las que tienen imagen
    con_imagen = [n for n in validas if n.get('urlToImage') and str(n['urlToImage']).startswith('http')]
    print(f"📊 Con imagen: {len(con_imagen)}")
    
    return con_imagen[:5]

def descargar_imagen(url):
    if not url or not str(url).startswith('http'):
        return None
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            temp_path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85, optimize=True)
            print(f"🖼️  Imagen lista: {os.path.getsize(temp_path)/1024:.1f} KB")
            return temp_path
    except Exception as e:
        print(f"⚠️ Error imagen: {e}")
    return None

def publicar_facebook(image_path, mensaje):
    if not image_path or not os.path.exists(image_path):
        print("❌ No hay imagen")
        return False
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }
            print("📤 Enviando a Facebook...")
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"❌ Facebook error: {error}")
                return False
    except Exception as e:
        print(f"❌ Error publicando: {e}")
        return False

def crear_publicacion(noticia):
    """
    Crea la publicación completa con redacción profesional en español
    """
    titulo_original = noticia['titulo_original']
    descripcion_original = noticia['descripcion_original']
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    categoria = noticia['categoria']
    
    print(f"\n✍️  Redactando noticia profesional...")
    print(f"   Original: {titulo_original[:60]}...")
    
    # Generar redacción profesional con OpenAI
    titular, cuerpo = redactar_noticia_profesional(
        titulo_original, 
        descripcion_original, 
        fuente, 
        categoria
    )
    
    # Si OpenAI falló, usar traducción básica como fallback
    if not titular or not cuerpo:
        print("⚠️ Fallback a traducción básica")
        titular = traducir_deepl(titulo_original)
        cuerpo = traducir_deepl(descripcion_original)
        cuerpo += f"\n\n📡 Información proporcionada por {fuente}."
    
    # Generar 5 hashtags
    hashtags = generar_5_hashtags(categoria, titular)
    
    # Ensamblar mensaje final
    mensaje = f"""📰 {titular}

{cuerpo}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    return mensaje

def main():
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("🚀 BOT DE NOTICIAS - Redacción Profesional en Español")
    print("="*60)
    
    # Buscar noticias
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No se encontraron noticias nuevas")
        guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
        return False
    
    print(f"\n🎯 {len(noticias)} noticia(s) para procesar")
    
    # Intentar publicar cada noticia hasta lograrlo
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 PROCESANDO NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("⏭️ Saltando: sin imagen")
            continue
        
        # Crear publicación con redacción profesional
        mensaje = crear_publicacion(noticia)
        
        # Mostrar preview
        print(f"\n📝 PREVIEW ({len(mensaje)} caracteres):")
        print("-" * 40)
        print(mensaje[:300] + "..." if len(mensaje) > 300 else mensaje)
        print("-" * 40)
        
        # Publicar
        exito = publicar_facebook(img_path, mensaje)
        
        # Limpiar imagen
        if os.path.exists(img_path):
            os.remove(img_path)
        
        if exito:
            # Guardar en historial
            HISTORIAL_URLS.add(noticia['url_normalizada'])
            HISTORIAL_HASHES.add(noticia['url_hash'])
            guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
            print(f"\n{'='*60}")
            print("✅ ÉXITO: Noticia publicada y guardada")
            print(f"{'='*60}")
            return True
        else:
            print(f"\n⚠️ Falló publicación, intentando siguiente...")
    
    print(f"\n{'='*60}")
    print("❌ No se pudo publicar ninguna noticia")
    print(f"{'='*60}")
    guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
    return False

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0 if resultado else 1)
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
