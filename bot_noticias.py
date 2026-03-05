import requests
import random
import re
import hashlib
import os
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, urldefrag, quote
from PIL import Image
from io import BytesIO

# Configuración desde variables de entorno
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('B_ACCESS_TOKEN')  # Corregido: era FB_ACCESS_TOKEN
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"🔍 DEBUG: NEWS_API_KEY presente: {bool(NEWS_API_KEY)}")
print(f"🔍 DEBUG: FB_PAGE_ID presente: {bool(FB_PAGE_ID)}")
print(f"🔍 DEBUG: FB_ACCESS_TOKEN presente: {bool(FB_ACCESS_TOKEN)}")

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    print("❌ ERROR: Faltan variables de entorno esenciales")
    raise ValueError("Faltan variables de entorno esenciales")

print("✅ Variables esenciales OK")

FUENTES_PREMIUM = {
    'internacional': ['bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'aljazeera.com', 'elpais.com', 'clarin.com', 'nytimes.com', 'washingtonpost.com'],
    'economia': ['bloomberg.com', 'forbes.com', 'eleconomista.es', 'expansion.com', 'ambito.com', 'ft.com', 'wsj.com'],
    'tecnologia': ['techcrunch.com', 'theverge.com', 'wired.com', 'xataka.com', 'fayerwayer.com', 'arstechnica.com'],
    'politica': ['politico.com', 'axios.com', 'infobae.com', 'animalpolitico.com', 'reforma.com']
}

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000

def normalizar_url(url):
    """Normaliza URL para evitar duplicados"""
    if not url:
        return ""
    url, _ = urldefrag(url)
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source', 'campaign']
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
    """Carga el historial de URLs publicadas"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                urls = set(data.get('urls', []))
                hashes = set(data.get('hashes', []))
                print(f"📚 Historial cargado: {len(urls)} URLs, {len(hashes)} hashes")
                return urls, hashes
        except Exception as e:
            print(f"⚠️ Error cargando historial: {e}")
            return set(), set()
    print("📚 No existe historial previo, creando nuevo")
    return set(), set()

def guardar_historial(urls, hashes):
    """Guarda el historial"""
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': list(hashes)[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat(),
        'total_guardadas': len(urls)
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Historial guardado: {len(urls)} URLs totales")

HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_texto(texto, idioma_origen='EN'):
    """Traduce usando DeepL"""
    if not DEEPL_API_KEY or idioma_origen.upper() != 'EN' or not texto:
        return texto
    
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto[:1000],
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
    except Exception as e:
        print(f"⚠️ Error traducción: {e}")
    
    return texto

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"🔍 BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    # CORREGIDO: Fechas para NewsAPI (formato ISO 8601)
    # NewsAPI free tier solo permite buscar hasta 1 mes atrás, pero para noticias frescas usamos últimas 48h
    fecha_hasta = datetime.now()
    fecha_desde = fecha_hasta - timedelta(hours=48)
    
    fecha_hasta_str = fecha_hasta.strftime('%Y-%m-%d')
    fecha_desde_str = fecha_desde.strftime('%Y-%m-%d')
    
    print(f"📅 Rango: {fecha_desde_str} a {fecha_hasta_str}")
    
    # CORREGIDO: Queries más simples y efectivas para NewsAPI
    busquedas = [
        # Internacional - queries simples
        ('breaking', 'internacional'),
        ('news', 'internacional'),
        ('world', 'internacional'),
        
        # Política
        ('politics', 'politica'),
        ('election', 'politica'),
        
        # Economía
        ('economy', 'economia'),
        ('market', 'economia'),
        
        # Tech
        ('technology', 'tech'),
        ('AI', 'tech'),
        
        # Crisis/Emergencias
        ('war', 'crisis'),
        ('conflict', 'crisis'),
    ]
    
    # Seleccionar 5 búsquedas aleatorias
    busquedas_hoy = random.sample(busquedas, min(5, len(busquedas)))
    todas_noticias = []
    
    for query, categoria in busquedas_hoy:
        try:
            print(f"\n📡 [{categoria.upper()}] Buscando: '{query}'")
            
            # CORREGIDO: Construcción correcta de URL
            params = {
                'q': query,
                'language': 'en',  # Empezar con inglés que tiene más contenido
                'from': fecha_desde_str,
                'to': fecha_hasta_str,
                'sortBy': 'publishedAt',
                'pageSize': '20',
                'apiKey': NEWS_API_KEY
            }
            
            url = "https://newsapi.org/v2/everything"
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            print(f"   Status API: {data.get('status', 'error')}")
            
            if data.get('status') == 'ok':
                articulos = data.get('articles', [])
                print(f"   Artículos encontrados: {len(articulos)}")
                
                if articulos:
                    for art in articulos:
                        if not es_noticia_valida(art):
                            continue
                        
                        url_norm = normalizar_url(art['url'])
                        url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
                        
                        # Verificar duplicado
                        if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
                            print(f"   ⏭️  YA PUBLICADA: {art['title'][:40]}...")
                            continue
                        
                        score = calcular_score(art, categoria)
                        art['categoria'] = categoria
                        art['score'] = score
                        art['url_hash'] = url_hash
                        art['url_normalizada'] = url_norm
                        art['idioma'] = 'EN'
                        
                        # Traducir
                        art['title'] = traducir_texto(art['title'], 'EN')
                        art['description'] = traducir_texto(art['description'], 'EN')
                        
                        todas_noticias.append(art)
                        print(f"   ✅ NUEVA: {art['title'][:50]}... (score: {score})")
                else:
                    print(f"   ⚠️ Sin artículos para esta query")
            else:
                error_msg = data.get('message', 'Error desconocido')
                print(f"   ❌ API Error: {error_msg}")
                
                # Si es error de autenticación, detener todo
                if 'apiKey' in error_msg.lower() or 'authentication' in error_msg.lower():
                    print("   🛑 Error de autenticación con NewsAPI")
                    break
                    
        except Exception as e:
            print(f"   ❌ Error en búsqueda: {e}")
    
    print(f"\n📊 Total noticias nuevas: {len(todas_noticias)}")
    
    # Filtrar con imagen
    con_imagen = [n for n in todas_noticias if n.get('urlToImage') and str(n['urlToImage']).startswith('http')]
    print(f"📊 Con imagen: {len(con_imagen)}")
    
    # Ordenar por score
    con_imagen.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return con_imagen[:5]

def es_noticia_valida(art):
    """Valida noticia"""
    if not art or not isinstance(art, dict):
        return False
    
    title = art.get('title', '')
    if not title or "[Removed]" in title or len(title) < 10:
        return False
    
    desc = art.get('description', '')
    if not desc or len(desc) < 30:
        return False
    
    url = art.get('url', '')
    if not url or not str(url).startswith('http'):
        return False
    
    # Excluir dominios no deseados
    dominios_excluir = ['news.google', 'google.com/news', 'facebook.com', 
                       'twitter.com', 'youtube.com', 'reddit.com']
    if any(d in str(url).lower() for d in dominios_excluir):
        return False
    
    return True

def calcular_score(art, categoria):
    """Calcula score viral"""
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    palabras_clave = {
        'breaking': 40, 'urgent': 35, 'alert': 30,
        'trump': 30, 'biden': 25, 'putin': 30, 'zelensky': 25,
        'war': 35, 'attack': 35, 'invasion': 35,
        'crash': 30, 'crisis': 25,
        'dead': 30, 'killed': 35,
        'earthquake': 30, 'tsunami': 35,
        'market': 20, 'economy': 20, 'inflation': 25,
        'ai': 25, 'artificial intelligence': 30,
        'scandal': 30, 'resigns': 25
    }
    
    for palabra, puntos in palabras_clave.items():
        if palabra in texto:
            score += puntos
    
    # Bonus fuente premium
    fuente = urlparse(str(art.get('url', ''))).netloc.lower()
    for cat, fuentes in FUENTES_PREMIUM.items():
        if any(f in fuente for f in fuentes):
            score += 20
            break
    
    # Bonus recencia
    try:
        fecha_pub = art.get('publishedAt', '')
        if fecha_pub:
            fecha_art = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00'))
            horas = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            if horas < 2: score += 40
            elif horas < 6: score += 30
            elif horas < 12: score += 20
            elif horas < 24: score += 10
    except:
        pass
    
    # Bonus imagen
    if art.get('urlToImage'):
        score += 15
    
    return score

def descargar_imagen(url_imagen):
    """Descarga imagen"""
    if not url_imagen or not str(url_imagen).startswith('http'):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url_imagen, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionar
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            
            temp_path = f'/tmp/noticia_{hashlib.md5(str(url_imagen).encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85, optimize=True)
            print(f"🖼️  Imagen: {temp_path} ({os.path.getsize(temp_path)/1024:.1f} KB)")
            return temp_path
    except Exception as e:
        print(f"⚠️ Error imagen: {e}")
    
    return None

def publicar_foto_con_texto(image_path, mensaje):
    """Publica en Facebook"""
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
            
            print(f"📤 Publicando en Facebook...")
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"❌ Error Facebook: {error}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def generar_mensaje(noticia, categoria):
    """Genera texto de publicación"""
    titulo = noticia.get('title', 'Noticia Internacional')
    descripcion = noticia.get('description', '')
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    
    # Limpiar descripción
    descripcion = descripcion.replace('\n', ' ').strip()
    if len(descripcion) > 300:
        descripcion = descripcion[:297] + "..."
    
    hashtags = f"#NoticiasMundiales #{categoria.capitalize()} #{datetime.now().strftime('%Y')}"
    
    mensaje = f"""📰 {titulo}

{descripcion}

📡 Fuente: {fuente}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    return mensaje

def publicar_en_facebook():
    """Función principal"""
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("🚀 Iniciando proceso...")
    
    noticias = buscar_noticias_frescas()
    
    if not noticias:
        print("⚠️ No hay noticias disponibles")
        guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
        return False
    
    print(f"\n🎯 {len(noticias)} noticia(s) candidata(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"📰 Intento {i}/{len(noticias)}")
        print(f"   {noticia['title'][:60]}...")
        
        if not noticia.get('urlToImage'):
            print("   ⏭️ Sin imagen")
            continue
        
        img_path = descargar_imagen(noticia['urlToImage'])
        if not img_path:
            print("   ⏭️ Error descargando imagen")
            continue
        
        mensaje = generar_mensaje(noticia, noticia['categoria'])
        
        exito = publicar_foto_con_texto(img_path, mensaje)
        
        if os.path.exists(img_path):
            os.remove(img_path)
        
        if exito:
            # Guardar en historial
            HISTORIAL_URLS.add(noticia['url_normalizada'])
            HISTORIAL_HASHES.add(noticia['url_hash'])
            guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
            print(f"\n✅ ÉXITO - Noticia publicada")
            return True
    
    print("\n❌ No se pudo publicar ninguna noticia")
    guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
    return False

if __name__ == "__main__":
    try:
        resultado = publicar_en_facebook()
        exit(0 if resultado else 1)
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
