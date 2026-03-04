import requests
import random
import re
import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse, quote
import json
import time
import feedparser
from bs4 import BeautifulSoup

# Variables de entorno
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')

print(f"DEBUG: FB_PAGE_ID={FB_PAGE_ID is not None}, FB_ACCESS_TOKEN={FB_ACCESS_TOKEN is not None}")
print(f"DEBUG: OPENAI_API_KEY={OPENAI_API_KEY is not None}, STABILITY_API_KEY={STABILITY_API_KEY is not None}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN, OPENAI_API_KEY]):
    raise ValueError("Faltan variables obligatorias")

# Fuentes RSS
FUENTES_RSS = {
    'bbc': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'reuters': 'http://feeds.reuters.com/reuters/worldnews',
    'cnn': 'http://rss.cnn.com/rss/edition_world.rss',
    'elpais': 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
    'clarin': 'https://www.clarin.com/rss/lo-ultimo/',
    'infobae': 'https://www.infobae.com/feeds/rss/',
}

HISTORIAL_URLS = set()
MAX_HISTORIAL = 100

def buscar_noticias_multiples_fuentes():
    print(f"\n{'='*60}")
    print(f"BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    todas_noticias = []
    
    # NewsAPI
    try:
        noticias_api = buscar_newsapi()
        todas_noticias.extend(noticias_api)
        print(f"[OK] NewsAPI: {len(noticias_api)} noticias")
    except Exception as e:
        print(f"[ERROR] NewsAPI: {e}")
    
    # RSS
    for fuente, url_rss in FUENTES_RSS.items():
        try:
            noticias_rss = parsear_rss(url_rss, fuente)
            todas_noticias.extend(noticias_rss)
            print(f"[OK] {fuente}: {len(noticias_rss)} noticias")
        except Exception as e:
            print(f"[ERROR] {fuente}: {e}")
    
    # Eliminar duplicados
    noticias_unicas = {}
    for noticia in todas_noticias:
        url_hash = hashlib.md5(noticia['url'].encode()).hexdigest()[:16]
        if url_hash not in noticias_unicas:
            noticia['url_hash'] = url_hash
            noticias_unicas[url_hash] = noticia
    
    noticias_lista = list(noticias_unicas.values())
    noticias_filtradas = [n for n in noticias_lista 
                         if n['url'] not in HISTORIAL_URLS 
                         and len(n.get('content', '')) > 200]
    noticias_filtradas.sort(key=lambda x: x.get('score', 50), reverse=True)
    
    print(f"\n[INFO] Total únicas: {len(noticias_lista)}, Disponibles: {len(noticias_filtradas)}")
    return noticias_filtradas[:5]

def buscar_newsapi():
    if not NEWS_API_KEY:
        return []
    
    url = f"https://newsapi.org/v2/top-headlines?category=general&language=es&pageSize=20&apiKey={NEWS_API_KEY}"
    response = requests.get(url, timeout=15)
    data = response.json()
    
    noticias = []
    if data.get('status') == 'ok':
        for art in data.get('articles', []):
            if art.get('title') and "[Removed]" not in art['title'] and len(art['title']) > 20:
                noticias.append({
                    'title': art['title'],
                    'description': art.get('description', ''),
                    'content': art.get('content', art.get('description', '')),
                    'url': art['url'],
                    'source': art.get('source', {}).get('name', 'NewsAPI'),
                    'image_url': art.get('urlToImage'),
                    'published': art.get('publishedAt', ''),
                    'score': 70
                })
    return noticias

def parsear_rss(url_rss, fuente_nombre):
    response = requests.get(url_rss, timeout=15, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; BotNoticias/1.0)'
    })
    
    feed = feedparser.parse(response.content)
    noticias = []
    
    for entry in feed.entries[:10]:
        image_url = None
        if 'media_content' in entry:
            image_url = entry.media_content[0].get('url')
        elif 'links' in entry:
            for link in entry.links:
                if link.get('type', '').startswith('image/'):
                    image_url = link.href
                    break
        
        descripcion = entry.get('summary', entry.get('description', ''))
        descripcion_limpia = BeautifulSoup(descripcion, 'html.parser').get_text()
        
        noticia = {
            'title': entry.title,
            'description': descripcion_limpia[:300],
            'content': entry.get('content', [{}])[0].get('value', descripcion_limpia),
            'url': entry.link,
            'source': fuente_nombre.upper(),
            'image_url': image_url,
            'published': entry.get('published', ''),
            'score': 60
        }
        
        if len(noticia['title']) > 20:
            noticias.append(noticia)
    
    return noticias

def reescribir_con_openai(titulo_original, contenido_original, fuente):
    print(f"\n[OPENAI] Reescribiendo noticia...")
    
    prompt = f"""Actúa como editor profesional. Reescribe esta noticia con estilo informativo, neutral y periodístico.

REGLAS:
- Mantén los hechos exactos
- Tono profesional y objetivo
- 3-4 párrafos
- NO inventes datos

NOTICIA:
Título: {titulo_original}
Contenido: {contenido_original[:800]}
Fuente: {fuente}

Responde SOLO en este formato JSON:
{{
    "titulo": "Título profesional",
    "contenido": "Texto reescrito",
    "resumen": "Resumen corto",
    "palabras_clave": ["kw1", "kw2", "kw3", "kw4", "kw5"],
    "categoria": "politica/economia/tecnologia/internacional"
}}"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1500
            },
            timeout=60
        )
        
        resultado = response.json()
        
        if response.status_code == 200 and 'choices' in resultado:
            texto = resultado['choices'][0]['message']['content']
            
            # Extraer JSON
            json_match = re.search(r'\{.*\}', texto, re.DOTALL)
            if json_match:
                datos = json.loads(json_match.group())
                print(f"[OPENAI] ✓ Título: {datos['titulo'][:50]}...")
                print(f"[OPENAI] ✓ Categoría: {datos['categoria']}")
                print(f"[OPENAI] ✓ Keywords: {', '.join(datos['palabras_clave'])}")
                return datos
                
    except Exception as e:
        print(f"[ERROR] OpenAI: {e}")
    
    # Fallback
    return {
        'titulo': titulo_original,
        'contenido': contenido_original[:500],
        'resumen': contenido_original[:200],
        'palabras_clave': ['noticias', 'actualidad', 'internacional', 'mundo', 'hoy'],
        'categoria': 'general'
    }

def descargar_imagen_a_archivo(url_imagen):
    """
    DESCARGA la imagen de la URL y la guarda como archivo local.
    Retorna la RUTA DEL ARCHIVO, nunca la URL.
    """
    if not url_imagen:
        print("[IMAGEN] No hay URL de imagen proporcionada")
        return None
    
    print(f"[IMAGEN] Descargando desde: {url_imagen[:60]}...")
    
    try:
        response = requests.get(url_imagen, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200 and len(response.content) > 1024:
            # Determinar extensión
            content_type = response.headers.get('content-type', '').lower()
            if 'png' in content_type:
                ext = 'png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            else:
                ext = 'jpg'
            
            # Crear nombre único
            nombre_archivo = f"img_{int(time.time())}_{hashlib.md5(url_imagen.encode()).hexdigest()[:8]}.{ext}"
            ruta_archivo = f"/tmp/{nombre_archivo}"
            
            # GUARDAR ARCHIVO
            with open(ruta_archivo, 'wb') as f:
                f.write(response.content)
            
            # VERIFICAR que se guardó correctamente
            if os.path.exists(ruta_archivo):
                tamano = os.path.getsize(ruta_archivo)
                print(f"[IMAGEN] ✓ DESCARGADA: {ruta_archivo} ({tamano} bytes)")
                return ruta_archivo
            else:
                print(f"[IMAGEN] ✗ Error: archivo no se creó")
                return None
        else:
            print(f"[IMAGEN] ✗ HTTP {response.status_code}, tamaño {len(response.content)}")
            
    except Exception as e:
        print(f"[IMAGEN] ✗ Error descargando: {e}")
    
    return None

def generar_imagen_stability(titulo, palabras_clave, categoria):
    if not STABILITY_API_KEY:
        print("[STABILITY] No hay API key")
        return None
    
    print(f"\n[STABILITY] Generando imagen...")
    
    keywords = ', '.join(palabras_clave[:3])
    estilos = {
        'politica': 'professional political news photography, documentary style',
        'economia': 'business news, professional corporate style',
        'tecnologia': 'futuristic tech, modern clean design',
        'internacional': 'global news photojournalism, Reuters style',
        'deportes': 'sports action photography, dynamic'
    }
    estilo = estilos.get(categoria, estilos['internacional'])
    
    prompt = f"News illustration: {titulo}. Keywords: {keywords}. Style: {estilo}. NO text, NO logos, professional, 4K."
    
    try:
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={"Authorization": f"Bearer {STABILITY_API_KEY}", "Accept": "image/*"},
            files={
                "prompt": (None, prompt[:500]),
                "output_format": (None, "png"),
                "aspect_ratio": (None, "16:9")
            },
            timeout=60
        )
        
        if response.status_code == 200:
            ruta = f"/tmp/stability_{int(time.time())}.png"
            with open(ruta, 'wb') as f:
                f.write(response.content)
            print(f"[STABILITY] ✓ Generada: {ruta} ({os.path.getsize(ruta)} bytes)")
            return ruta
        else:
            print(f"[STABILITY] ✗ Error HTTP {response.status_code}")
            
    except Exception as e:
        print(f"[STABILITY] ✗ Error: {e}")
    
    return None

def obtener_imagen_para_publicar(noticia, noticia_reescrita):
    """
    Obtiene imagen como ARCHIVO LOCAL para subir a Facebook.
    PRIORIDAD: 1) Descargar original, 2) Generar con Stability
    """
    print(f"\n[IMAGEN] Obteniendo imagen para publicar...")
    
    # OPCIÓN 1: Descargar imagen original
    if noticia.get('image_url'):
        print(f"[IMAGEN] Intentando descargar imagen original...")
        ruta_local = descargar_imagen_a_archivo(noticia['image_url'])
        if ruta_local:
            print(f"[IMAGEN] ✓ Usando imagen ORIGINAL descargada")
            return ruta_local
        else:
            print(f"[IMAGEN] ✗ Falló descarga de original")
    
    # OPCIÓN 2: Generar con Stability
    print(f"[IMAGEN] Intentando generar con IA...")
    ruta_ia = generar_imagen_stability(
        noticia_reescrita['titulo'],
        noticia_reescrita['palabras_clave'],
        noticia_reescrita['categoria']
    )
    
    if ruta_ia:
        print(f"[IMAGEN] ✓ Usando imagen IA generada")
        return ruta_ia
    
    print(f"[IMAGEN] ✗ No se pudo obtener ninguna imagen")
    return None

def publicar_en_facebook(titulo, contenido, palabras_clave, ruta_imagen_local, url_fuente, nombre_fuente):
    """
    Publica en Facebook. 
    ruta_imagen_local DEBE ser una ruta de archivo local, NUNCA una URL.
    """
    print(f"\n[FACEBOOK] Iniciando publicación...")
    print(f"[FACEBOOK] Imagen recibida: {ruta_imagen_local}")
    
    # Verificar que es archivo local
    if ruta_imagen_local:
        if not os.path.exists(ruta_imagen_local):
            print(f"[FACEBOOK] ⚠️ Archivo no existe: {ruta_imagen_local}")
            ruta_imagen_local = None
        elif not os.path.isfile(ruta_imagen_local):
            print(f"[FACEBOOK] ⚠️ No es archivo: {ruta_imagen_local}")
            ruta_imagen_local = None
        else:
            tamano = os.path.getsize(ruta_imagen_local)
            print(f"[FACEBOOK] ✓ Archivo válido: {tamano} bytes")
    
    # Preparar mensaje
    hashtags = ' '.join([f"#{kw.replace(' ', '')}" for kw in palabras_clave[:4]])
    mensaje = f"""📰 {titulo}

{contenido}

🏷️ {hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
    
    post_id = None
    
    try:
        # MÉTODO CON IMAGEN (subir archivo local)
        if ruta_imagen_local:
            print(f"\n[FACEBOOK] Subiendo FOTO con archivo local...")
            print(f"[FACEBOOK] Archivo: {ruta_imagen_local}")
            
            url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
            
            with open(ruta_imagen_local, 'rb') as img_file:
                files = {'file': ('imagen.png', img_file, 'image/png')}
                data = {
                    'message': mensaje,
                    'access_token': FB_ACCESS_TOKEN,
                    'published': 'true'
                }
                
                print(f"[FACEBOOK] Enviando POST a /photos...")
                response = requests.post(url, files=files, data=data, timeout=60)
                result = response.json()
                
                print(f"[FACEBOOK] Status: {response.status_code}")
                
                if response.status_code == 200 and 'id' in result:
                    post_id = result.get('post_id') or result['id']
                    print(f"[FACEBOOK] ✓ ÉXITO: Post ID {post_id}")
                else:
                    error = result.get('error', {}).get('message', 'Error desconocido')
                    print(f"[FACEBOOK] ✗ ERROR: {error}")
                    print(f"[DEBUG] Respuesta completa: {json.dumps(result)}")
                    post_id = None
        
        # MÉTODO SIN IMAGEN (fallback)
        if not post_id:
            print(f"\n[FACEBOOK] Publicando solo TEXTO...")
            url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
            
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN,
                'link': url_fuente
            }
            
            response = requests.post(url, data=data, timeout=60)
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                post_id = result['id']
                print(f"[FACEBOOK] ✓ ÉXITO (texto): {post_id}")
            else:
                print(f"[FACEBOOK] ✗ ERROR: {result}")
                return False
        
        # Agregar comentario con link
        if post_id:
            agregar_comentario(post_id, url_fuente, nombre_fuente)
            return True
            
    except Exception as e:
        print(f"[ERROR] Publicando: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def agregar_comentario(post_id, url_fuente, nombre_fuente):
    try:
        print(f"\n[FACEBOOK] Agregando comentario...")
        
        # Limpiar post_id
        post_id_limpio = post_id.split('_')[-1] if '_' in post_id else post_id
        
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}_{post_id_limpio}/comments"
        
        mensaje = f"""📎 Fuente: {nombre_fuente}

🔗 {url_fuente}

#Noticias #Actualidad"""
        
        data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN}
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            print(f"[FACEBOOK] ✓ Comentario agregado")
        else:
            print(f"[FACEBOOK] ✗ Error comentario: {response.json()}")
            
    except Exception as e:
        print(f"[ERROR] Comentario: {e}")

def limpiar_archivos():
    try:
        for archivo in os.listdir('/tmp'):
            if archivo.startswith(('img_', 'stability_')):
                try:
                    os.remove(f'/tmp/{archivo}')
                except:
                    pass
    except:
        pass

def main():
    global HISTORIAL_URLS
    
    print("="*60)
    print("🚀 VERDAD DE HOY - Bot de Noticias con IA")
    print("="*60)
    
    try:
        # 1. Buscar noticias
        noticias = buscar_noticias_multiples_fuentes()
        if not noticias:
            print("[AVISO] No hay noticias")
            return False
        
        # 2. Seleccionar
        noticia = noticias[0]
        HISTORIAL_URLS.add(noticia['url'])
        
        print(f"\n{'='*60}")
        print(f"[NOTICIA SELECCIONADA]")
        print(f"Título: {noticia['title'][:70]}")
        print(f"Fuente: {noticia['source']}")
        print(f"URL: {noticia['url'][:60]}...")
        print(f"Tiene imagen: {bool(noticia.get('image_url'))}")
        print(f"{'='*60}")
        
        # 3. Reescribir con OpenAI
        reescrita = reescribir_con_openai(
            noticia['title'],
            noticia.get('content') or noticia['description'],
            noticia['source']
        )
        
        # 4. Obtener imagen (SIEMPRE como archivo local)
        ruta_imagen = obtener_imagen_para_publicar(noticia, reescrita)
        
        # 5. Publicar
        exito = publicar_en_facebook(
            titulo=reescrita['titulo'],
            contenido=reescrita['contenido'],
            palabras_clave=reescrita['palabras_clave'],
            ruta_imagen_local=ruta_imagen,  # SIEMPRE es ruta local o None
            url_fuente=noticia['url'],
            nombre_fuente=noticia['source']
        )
        
        # 6. Limpiar
        if ruta_imagen and os.path.exists(ruta_imagen):
            try:
                os.remove(ruta_imagen)
                print(f"\n[LIMPIEZA] Archivo temporal eliminado")
            except:
                pass
        
        return exito
        
    except Exception as e:
        print(f"\n[ERROR CRÍTICO] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        limpiar_archivos()

if __name__ == "__main__":
    exito = main()
    print(f"\n{'='*60}")
    print(f"RESULTADO: {'ÉXITO' if exito else 'FALLO'}")
    print(f"{'='*60}")
    exit(0 if exito else 1)
