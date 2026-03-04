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
                    'image': art.get('urlToImage'),
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
    
    for entry in feed.entries[:10]:  # Primeras 10 noticias
        # Extraer imagen si existe
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
            'image': image_url,
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
    Usa OpenAI para reescribir la noticia con estilo editorial profesional
    """
    print(f"[OPENAI] Reescribiendo noticia...")
    
    prompt = f"""Actúa como un editor profesional de un diario digital. Reescribe la siguiente noticia manteniendo los hechos pero con un estilo informativo, neutral y periodístico de alta calidad.

REGLAS:
- Mantén la información factual exacta
- Usa un tono profesional y objetivo
- Estructura: titular impactante, bajada (resumen), desarrollo con contexto, cierre
- NO inventes datos, solo reescribe con mejor estilo
- Longitud: 3-4 párrafos
- Incluye la fuente al final

NOTICIA ORIGINAL:
Título: {titulo_original}
Contenido: {contenido_original[:800]}
Fuente: {fuente}

Genera la respuesta en este formato JSON:
{{
    "titulo": "Título reescrito profesional",
    "contenido": "Texto completo reescrito en párrafos",
    "resumen": "Resumen de una línea para redes sociales",
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
                # Buscar JSON en la respuesta
                json_match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
                if json_match:
                    datos = json.loads(json_match.group())
                    print(f"[OPENAI] ✓ Noticia reescrita - Categoría: {datos.get('categoria', 'general')}")
                    print(f"[OPENAI] ✓ Palabras clave: {', '.join(datos.get('palabras_clave', []))}")
                    return datos
            except Exception as e:
                print(f"[OPENAI] Error parseando JSON: {e}")
                print(f"[OPENAI] Respuesta: {texto_respuesta[:200]}")
        
        # Fallback si falla el parsing
        return {
            'titulo': titulo_original,
            'contenido': contenido_original[:500],
            'resumen': contenido_original[:200],
            'palabras_clave': ['noticias', 'actualidad', 'internacional'],
            'categoria': 'general'
        }
        
    except Exception as e:
        print(f"[ERROR] OpenAI reescritura: {e}")
        return None

def generar_imagen_con_stability(titulo, palabras_clave, categoria):
    """
    Genera imagen usando Stability AI basada en el contexto
    """
    if not STABILITY_API_KEY:
        print("[IMAGEN] No hay API key de Stability")
        return None
    
    print(f"[IMAGEN] Generando imagen con Stability AI...")
    
    # Crear prompt optimizado
    keywords_str = ', '.join(palabras_clave[:3])
    
    estilos = {
        'politica': 'professional news photography, political scene, documentary style, serious tone',
        'economia': 'business news style, charts and city background, professional blue tones',
        'tecnologia': 'futuristic tech visualization, modern, clean design, innovation',
        'internacional': 'global news photojournalism, world events, professional Reuters style',
        'deportes': 'sports action photography, dynamic, energetic, stadium atmosphere'
    }
    
    estilo = estilos.get(categoria, estilos['internacional'])
    
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
            print(f"[IMAGEN] ✗ Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Stability: {e}")
        return None

def descargar_imagen_noticia(url_imagen):
    """Descarga imagen original de la noticia"""
    if not url_imagen:
        return None
    
    try:
        print(f"[DESCARGA] Descargando imagen original...")
        response = requests.get(url_imagen, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200 and len(response.content) > 1024:
            ext = 'jpg' if 'jpeg' in response.headers.get('content-type', '') else 'png'
            temp_path = f"/tmp/original_{int(time.time())}.{ext}"
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            print(f"[DESCARGA] ✓ Imagen guardada: {temp_path}")
            return temp_path
    except Exception as e:
        print(f"[DESCARGA] ✗ Error: {e}")
    
    return None

def publicar_en_facebook(titulo, contenido, palabras_clave, imagen_path, url_fuente, nombre_fuente):
    """
    Publica en Facebook: foto + mensaje, y comentario con link
    """
    print(f"\n[FACEBOOK] Iniciando publicación...")
    
    # 1. Preparar mensaje principal
    hashtags = ' '.join([f"#{kw.replace(' ', '')}" for kw in palabras_clave[:4]])
    
    mensaje = f"""📰 {titulo}

{contenido}

🏷️ {hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
    
    # 2. Publicar foto con mensaje
    post_id = None
    try:
        if imagen_path and os.path.exists(imagen_path):
            print(f"[FACEBOOK] Subiendo foto...")
            
            url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
            
            with open(imagen_path, 'rb') as img:
                files = {'file': (os.path.basename(imagen_path), img, 'image/png')}
                data = {
                    'message': mensaje,
                    'access_token': FB_ACCESS_TOKEN,
                    'published': 'true'
                }
                
                response = requests.post(url, files=files, data=data, timeout=60)
                result = response.json()
                
                if response.status_code == 200 and 'id' in result:
                    post_id = result.get('post_id') or result['id']
                    print(f"[FACEBOOK] ✓ Publicación creada: {post_id}")
                else:
                    error = result.get('error', {}).get('message', 'Error desconocido')
                    print(f"[FACEBOOK] ✗ Error: {error}")
                    return False
        else:
            # Sin imagen: publicar solo texto
            print(f"[FACEBOOK] Publicando solo texto...")
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
                print(f"[FACEBOOK] ✓ Publicación creada: {post_id}")
            else:
                print(f"[FACEBOOK] ✗ Error: {result}")
                return False
        
        # 3. Agregar comentario con link a la fuente
        if post_id:
            time.sleep(2)  # Esperar un momento
            agregar_comentario_link(post_id, url_fuente, nombre_fuente)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Publicando: {e}")
        import traceback
        traceback.print_exc()
        return False

def agregar_comentario_link(post_id, url_fuente, nombre_fuente):
    """Agrega un comentario con el link a la fuente original"""
    try:
        print(f"[FACEBOOK] Agregando comentario con link...")
        
        # Extraer solo el ID numérico del post si es necesario
        post_id_limpio = post_id.split('_')[-1] if '_' in post_id else post_id
        
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
            if archivo.startswith(('stability_', 'original_')):
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
        
        # 4. Obtener imagen (original o generada)
        imagen_path = None
        
        # Intentar descargar imagen original primero
        if noticia.get('image'):
            imagen_path = descargar_imagen_noticia(noticia['image'])
        
        # Si no hay imagen original, generar con Stability
        if not imagen_path and STABILITY_API_KEY:
            imagen_path = generar_imagen_con_stability(
                noticia_reescrita['titulo'],
                noticia_reescrita['palabras_clave'],
                noticia_reescrita['categoria']
            )
        
        # 5. Publicar en Facebook
        exito = publicar_en_facebook(
            titulo=noticia_reescrita['titulo'],
            contenido=noticia_reescrita['contenido'],
            palabras_clave=noticia_reescrita['palabras_clave'],
            imagen_path=imagen_path,
            url_fuente=noticia['url'],
            nombre_fuente=noticia['source']
        )
        
        # 6. Limpiar
        if imagen_path and os.path.exists(imagen_path):
            try:
                os.remove(imagen_path)
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
