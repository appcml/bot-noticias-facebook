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

print(f"DEBUG: Variables cargadas - FB: {bool(FB_ACCESS_TOKEN)}, OpenAI: {bool(OPENAI_API_KEY)}, Stability: {bool(STABILITY_API_KEY)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN, OPENAI_API_KEY]):
    raise ValueError("Faltan variables obligatorias: FB_PAGE_ID, FB_ACCESS_TOKEN, OPENAI_API_KEY")

# Fuentes RSS de medios importantes
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
    """
    Busca noticias en múltiples fuentes: NewsAPI + RSS de medios importantes
    """
    print(f"\n{'='*60}")
    print(f"BUSCANDO NOTICIAS EN MÚLTIPLES FUENTES - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    todas_noticias = []
    
    # 1. Buscar en NewsAPI
    try:
        noticias_api = buscar_newsapi()
        todas_noticias.extend(noticias_api)
    except Exception as e:
        print(f"[ERROR] NewsAPI: {e}")
    
    # 2. Buscar en RSS de medios
    for fuente, url_rss in FUENTES_RSS.items():
        try:
            print(f"[RSS] Consultando {fuente}...")
            noticias_rss = parsear_rss(url_rss, fuente)
            todas_noticias.extend(noticias_rss)
            print(f"  ✓ {len(noticias_rss)} noticias de {fuente}")
        except Exception as e:
            print(f"  ✗ Error en {fuente}: {e}")
    
    # Eliminar duplicados por URL
    noticias_unicas = {}
    for noticia in todas_noticias:
        url_hash = hashlib.md5(noticia['url'].encode()).hexdigest()[:16]
        if url_hash not in noticias_unicas:
            noticia['url_hash'] = url_hash
            noticias_unicas[url_hash] = noticia
    
    noticias_lista = list(noticias_unicas.values())
    print(f"\n[INFO] Total noticias únicas: {len(noticias_lista)}")
    
    # Filtrar las mejores (no publicadas antes, con contenido)
    noticias_filtradas = [n for n in noticias_lista 
                         if n['url'] not in HISTORIAL_URLS 
                         and len(n.get('content', '')) > 200]
    
    # Ordenar por relevancia (simulado por ahora)
    noticias_filtradas.sort(key=lambda x: x.get('score', 50), reverse=True)
    
    print(f"[INFO] Noticias disponibles: {len(noticias_filtradas)}")
    return noticias_filtradas[:5]

def buscar_newsapi():
    """Busca noticias en NewsAPI"""
    if not NEWS_API_KEY:
        return []
    
    url = f"https://newsapi.org/v2/top-headlines?category=general&language=es&pageSize=20&apiKey={NEWS_API_KEY}"
    response = requests.get(url, timeout=15)
    data = response.json()
    
    noticias = []
    if data.get('status') == 'ok':
        for art in data.get('articles', []):
            if es_noticia_valida(art):
                noticias.append({
                    'title': art['title'],
                    'description': art.get('description', ''),
                    'content': art.get('content', art.get('description', '')),
                    'url': art['url'],
                    'source': art.get('source', {}).get('name', 'NewsAPI'),
                    'image_url': art.get('urlToImage'),  # Solo para descargar, no para FB
                    'published': art.get('publishedAt', ''),
                    'score': 70
                })
    return noticias

def parsear_rss(url_rss, fuente_nombre):
    """Parsea feed RSS y extrae noticias"""
    response = requests.get(url_rss, timeout=15, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; BotNoticias/1.0)'
    })
    
    feed = feedparser.parse(response.content)
    noticias = []
    
    for entry in feed.entries[:10]:
        # Extraer imagen si existe en el RSS
        image_url = None
        if 'media_content' in entry:
            image_url = entry.media_content[0].get('url')
        elif 'links' in entry:
            for link in entry.links:
                if link.get('type', '').startswith('image/'):
                    image_url = link.href
                    break
        
        # Limpiar HTML de la descripción
        descripcion = entry.get('summary', entry.get('description', ''))
        descripcion_limpia = BeautifulSoup(descripcion, 'html.parser').get_text()
        
        noticia = {
            'title': entry.title,
            'description': descripcion_limpia[:300],
            'content': entry.get('content', [{}])[0].get('value', descripcion_limpia),
            'url': entry.link,
            'source': fuente_nombre.upper(),
            'image_url': image_url,  # Solo para descargar, NO para Facebook
            'published': entry.get('published', ''),
            'score': 60
        }
        
        if len(noticia['title']) > 20:
            noticias.append(noticia)
    
    return noticias

def es_noticia_valida(art):
    """Valida si una noticia tiene contenido suficiente"""
    if not art.get('title') or "[Removed]" in art['title']:
        return False
    if len(art['title']) < 20:
        return False
    return True

def reescribir_noticia_con_openai(titulo_original, contenido_original, fuente):
    """
    Usa OpenAI para reescribir la noticia con estilo editorial profesional y optimización SEO.
    """
    print(f"[OPENAI] Reescribiendo noticia...")
    
    prompt = f"""Actúa como un editor profesional de un diario digital y experto en SEO. Reescribe la siguiente noticia manteniendo los hechos pero con un estilo informativo, neutral y periodístico de alta calidad, optimizado para posicionamiento orgánico en redes sociales.

REGLAS:
- Mantén la información factual exacta.
- Usa un tono profesional y objetivo.
- Estructura: titular impactante, bajada (resumen), desarrollo con contexto, cierre.
- Incluye 3-5 palabras clave relevantes en el contenido de forma natural para SEO.
- NO inventes datos, solo reescribe con mejor estilo.
- Longitud: 3-4 párrafos.
- Incluye la fuente al final del contenido.

NOTICIA ORIGINAL:
Título: {titulo_original}
Contenido: {contenido_original[:800]}
Fuente: {fuente}

Genera la respuesta en este formato JSON:
{{
    "titulo": "Título reescrito profesional y SEO-friendly",
    "contenido": "Texto completo reescrito en párrafos, con palabras clave integradas",
    "resumen_seo": "Resumen corto y atractivo para redes sociales (max 200 caracteres), con palabras clave principales",
    "palabras_clave": ["palabra1", "palabra2", "palabra3", "palabra4", "palabra5"],
    "categoria": "politica/economia/tecnologia/internacional/deportes"
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
            texto_respuesta = resultado['choices'][0]['message']['content']
            
            # Extraer JSON de la respuesta
            try:
                json_match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
                if json_match:
                    datos = json.loads(json_match.group())
                    print(f"[OPENAI] ✓ Noticia reescrita - Categoría: {datos.get('categoria', 'general')}")
                    print(f"[OPENAI] ✓ Palabras clave: {', '.join(datos.get('palabras_clave', []))}")
                    return datos
            except Exception as e:
                print(f"[OPENAI] Error parseando JSON: {e}")
        
        # Fallback
        return {
            'titulo': titulo_original,
            'contenido': contenido_original[:500] + f"\nFuente: {fuente}",
            'resumen_seo': contenido_original[:200],
            'palabras_clave': ['noticias', 'actualidad', 'internacional'],
            'categoria': 'general'
        }
        
    except Exception as e:
        print(f"[ERROR] OpenAI reescritura: {e}")
        return None

def descargar_imagen(url_imagen, prefix="img"):
    """
    Descarga imagen desde URL y guarda como archivo local.
    NUNCA retorna la URL, siempre el path local o None.
    """
    if not url_imagen:
        return None
    
    try:
        print(f"[DESCARGA] Descargando imagen...")
        response = requests.get(url_imagen, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200 and len(response.content) > 1024:
            # Detectar extensión
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                ext = 'png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            else:
                ext = 'png'
            
            temp_path = f"/tmp/{prefix}_{int(time.time())}_{hashlib.md5(url_imagen.encode()).hexdigest()[:8]}.{ext}"
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            print(f"[DESCARGA] ✓ Imagen guardada: {temp_path} ({os.path.getsize(temp_path)} bytes)")
            return temp_path
        else:
            print(f"[DESCARGA] ✗ Respuesta inválida: {response.status_code}, {len(response.content)} bytes")
            
    except Exception as e:
        print(f"[DESCARGA] ✗ Error: {e}")
    
    return None

def generar_imagen_con_stability(titulo, palabras_clave, categoria):
    """
    Genera imagen usando Stability AI basada en el contexto.
    Retorna PATH LOCAL del archivo, NUNCA una URL.
    """
    if not STABILITY_API_KEY:
        print("[IMAGEN] No hay API key de Stability")
        return None
    
    keywords_str = ', '.join(palabras_clave[:3])
    
    estilos = {
        'politica': 'professional news photography, political scene, documentary style, serious tone',
        'economia': 'business news style, charts and city background, professional blue tones',
        'tecnologia': 'futuristic tech visualization, modern, clean design, innovation',
        'internacional': 'global news photojournalism, world events, professional Reuters style',
        'deportes': 'sports action photography, dynamic, energetic, stadium atmosphere',
        'general': 'general news photography, diverse subjects, neutral tone, high quality'
    }
    
    estilo = estilos.get(categoria, estilos['general'])
    
    prompt = f"News illustration about: {titulo}. Keywords: {keywords_str}. Style: {estilo}. High quality, 4K, photorealistic, NO text, NO logos, professional news media style."
    
    try:
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept": "image/*"
        }
        
        files = {
            "prompt": (None, prompt[:500]),
            "output_format": (None, "png"),
            "aspect_ratio": (None, "16:9")
        }
        
        response = requests.post(url, headers=headers, files=files, timeout=60)
        
        if response.status_code == 200:
            temp_path = f"/tmp/stability_{int(time.time())}.png"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            print(f"[IMAGEN] ✓ Generada: {temp_path} ({os.path.getsize(temp_path)} bytes)")
            return temp_path
        else:
            print(f"[IMAGEN] ✗ Error HTTP: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Stability: {e}")
        return None

def obtener_imagen_local(noticia, noticia_reescrita):
    """
    Obtiene una imagen SIEMPRE como archivo local.
    NUNCA retorna una URL.
    """
    imagen_path = None
    
    # 1. Intentar descargar imagen original
    if noticia.get('image_url'):
        imagen_path = descargar_imagen(noticia['image_url'], "original")
        if imagen_path:
            print(f"[IMAGEN] Usando imagen original descargada")
            return imagen_path
    
    # 2. Generar con Stability si no hay original
    if not imagen_path and STABILITY_API_KEY:
        print(f"[IMAGEN] Generando imagen con IA...")
        imagen_path = generar_imagen_con_stability(
            noticia_reescrita['titulo'],
            noticia_reescrita['palabras_clave'],
            noticia_reescrita['categoria']
        )
        if imagen_path:
            return imagen_path
    
    print(f"[IMAGEN] No se pudo obtener imagen")
    return None

def publicar_en_facebook(titulo, contenido, resumen_seo, palabras_clave, imagen_path, url_fuente, nombre_fuente):
    """
    Publica en Facebook: foto + mensaje, y comentario con link.
    imagen_path DEBE ser un archivo local, NUNCA una URL.
    """
    print(f"\n[FACEBOOK] Iniciando publicación...")
    
    # Preparar mensaje principal para la publicación con imagen
    hashtags = ' '.join([f"#{kw.replace(' ', '')}" for kw in palabras_clave[:4]])
    
    mensaje_principal = f"""📰 {titulo}

{resumen_seo}

{hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
    
    post_id = None
    
    try:
        # Verificar que imagen_path sea un archivo local válido
        if imagen_path and os.path.exists(imagen_path) and os.path.isfile(imagen_path):
            print(f"[FACEBOOK] Subiendo foto desde archivo local: {imagen_path}")
            
            url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
            
            with open(imagen_path, 'rb') as img:
                files = {
                    'file': (os.path.basename(imagen_path), img, 'image/png')
                }
                data = {
                    'message': mensaje_principal, # Solo el mensaje, sin URL externa
                    'access_token': FB_ACCESS_TOKEN,
                    'published': 'true'
                }
                
                response = requests.post(url, files=files, data=data, timeout=60)
                result = response.json()
                
                print(f"[DEBUG] Status: {response.status_code}")
                print(f"[DEBUG] Response: {json.dumps(result)[:300]}...")
                
                if response.status_code == 200 and 'id' in result:
                    post_id = result.get('post_id') or result['id']
                    print(f"[FACEBOOK] ✓ Publicación con imagen creada: {post_id}")
                else:
                    error = result.get('error', {}).get('message', 'Error desconocido')
                    print(f"[FACEBOOK] ✗ Error subiendo foto: {error}")
                    # Si falla la publicación con imagen, intentar solo texto como fallback
                    post_id = publicar_solo_texto(mensaje_principal, url_fuente)
        else:
            print(f"[FACEBOOK] No hay imagen local válida o no se pudo generar, publicando solo texto")
            post_id = publicar_solo_texto(mensaje_principal, url_fuente)
        
        # Agregar comentario con link si se pudo publicar algo
        if post_id and url_fuente:
            time.sleep(2)
            agregar_comentario_link(post_id, url_fuente, nombre_fuente)
            return True
        elif post_id:
            print(f"[FACEBOOK] Publicación exitosa, pero sin URL de fuente para comentario.")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"[ERROR] Publicando: {e}")
        import traceback
        traceback.print_exc()
        return False

def publicar_solo_texto(mensaje, url_fuente=None):
    """
    Publica solo texto con link como fallback. Si url_fuente es None, no se añade link.
    """
    try:
        print(f"[FACEBOOK] Publicando solo texto...")
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        
        data = {
            'message': mensaje,
            'access_token': FB_ACCESS_TOKEN,
        }
        if url_fuente:
            data['link'] = url_fuente # Esto creará un link preview si url_fuente no es None
        
        response = requests.post(url, data=data, timeout=60)
        result = response.json()
        
        if response.status_code == 200 and 'id' in result:
            post_id = result['id']
            print(f"[FACEBOOK] ✓ Publicación creada (solo texto): {post_id}")
            return post_id
        else:
            print(f"[FACEBOOK] ✗ Error: {result}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Publicando solo texto: {e}")
        return None

def agregar_comentario_link(post_id, url_fuente, nombre_fuente):
    """
    Agrega un comentario con el link a la fuente original.
    """
    try:
        print(f"[FACEBOOK] Agregando comentario con link...")
        
        # Limpiar post_id si es necesario
        if '_' in post_id:
            # Formato: pageid_postid, usar solo postid para comentarios
            post_id_limpio = post_id.split('_')[-1]
        else:
            post_id_limpio = post_id
        
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}_{post_id_limpio}/comments"
        
        mensaje_comentario = f"""📎 Fuente original: {nombre_fuente}

🔗 {url_fuente}

#Noticias #Actualidad"""
        
        data = {
            'message': mensaje_comentario,
            'access_token': FB_ACCESS_TOKEN
        }
        
        response = requests.post(url, data=data, timeout=30)
        result = response.json()
        
        if response.status_code == 200:
            print(f"[FACEBOOK] ✓ Comentario agregado")
        else:
            print(f"[FACEBOOK] ✗ Error en comentario: {result}")
            
    except Exception as e:
        print(f"[ERROR] Comentario: {e}")

def limpiar_temporales():
    """Limpia archivos temporales"""
    try:
        for archivo in os.listdir('/tmp'):
            if archivo.startswith(('stability_', 'original_', 'img_')):
                try:
                    os.remove(f'/tmp/{archivo}')
                except:
                    pass
    except:
        pass

def main():
    global HISTORIAL_URLS
    
    print("🚀 VERDAD DE HOY - Sistema de Noticias con IA")
    print("="*60)
    
    try:
        # 1. Buscar noticias
        noticias = buscar_noticias_multiples_fuentes()
        
        if not noticias:
            print("[AVISO] No se encontraron noticias")
            return False
        
        # 2. Seleccionar la mejor noticia
        noticia = noticias[0]
        HISTORIAL_URLS.add(noticia['url'])
        
        print(f"\n[SELECCIONADA] {noticia['title'][:70]}...")
        print(f"  Fuente: {noticia['source']}")
        
        # 3. Reescribir con OpenAI
        noticia_reescrita = reescribir_noticia_con_openai(
            noticia['title'],
            noticia['content'] or noticia['description'],
            noticia['source']
        )
        
        if not noticia_reescrita:
            print("[ERROR] No se pudo reescribir la noticia")
            return False
        
        # 4. Obtener imagen SIEMPRE como archivo local
        imagen_path = obtener_imagen_local(noticia, noticia_reescrita)
        
        # 5. Publicar en Facebook
        exito = publicar_en_facebook(
            titulo=noticia_reescrita['titulo'],
            contenido=noticia_reescrita['contenido'],
            resumen_seo=noticia_reescrita['resumen_seo'], # Nuevo campo para resumen SEO
            palabras_clave=noticia_reescrita['palabras_clave'],
            imagen_path=imagen_path,  # SIEMPRE es path local o None
            url_fuente=noticia['url'],
            nombre_fuente=noticia['source']
        )
        
        # 6. Limpiar archivos temporales
        if imagen_path and os.path.exists(imagen_path):
            try:
                os.remove(imagen_path)
                print(f"[LIMPIEZA] Archivo temporal eliminado")
            except:
                pass
        
        return exito
        
    except Exception as e:
        print(f"[ERROR CRÍTICO] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        limpiar_temporales()

if __name__ == "__main__":
    exito = main()
    exit(0 if exito else 1)
