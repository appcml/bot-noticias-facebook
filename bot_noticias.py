#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Automático para Facebook
- Busca noticias de actualidad
- Reescribe con OpenAI (estilo profesional, SEO)
- Genera imagen con IA (Stability o OpenAI)
- Publica en Facebook
"""

import os
import sys
import json
import re
import hashlib
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')

print(f"DEBUG: FB={bool(FB_PAGE_ID)}, OpenAI={bool(OPENAI_API_KEY)}, Stability={bool(STABILITY_API_KEY)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN, OPENAI_API_KEY]):
    raise ValueError("Faltan: FB_PAGE_ID, FB_ACCESS_TOKEN u OPENAI_API_KEY")

# ============================================================================
# FUENTES RSS (URLs corregidas sin espacios)
# ============================================================================

FUENTES_RSS = {
    'BBC Mundo': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Reuters': 'http://feeds.reuters.com/reuters/worldnews',
    'CNN World': 'http://rss.cnn.com/rss/edition_world.rss',
    'El País': 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
    'Clarín': 'https://www.clarin.com/rss/lo-ultimo/',
    'Infobae': 'https://www.infobae.com/feeds/rss/',
}

HISTORIAL_URLS = set()
MAX_HISTORIAL = 100

# ============================================================================
# 1. BÚSQUEDA DE NOTICIAS
# ============================================================================

def buscar_noticias():
    print("\n" + "="*60)
    print("🔍 BUSCANDO NOTICIAS")
    print("="*60)
    
    todas = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            n = buscar_newsapi()
            todas.extend(n)
            print(f"✓ NewsAPI: {len(n)}")
        except Exception as e:
            print(f"✗ NewsAPI: {e}")
    
    # RSS
    for nombre, url in FUENTES_RSS.items():
        try:
            n = buscar_rss(url, nombre)
            todas.extend(n)
            print(f"✓ {nombre}: {len(n)}")
        except Exception as e:
            print(f"✗ {nombre}: {str(e)[:50]}")
    
    # Filtrar duplicados y ya publicadas
    unicas = {}
    for n in todas:
        if n['url'] not in HISTORIAL_URLS and len(n['titulo']) > 20:
            unicas[n['url']] = n
    
    resultado = list(unicas.values())
    print(f"\n📊 Total únicas: {len(resultado)}")
    return resultado

def buscar_newsapi():
    url = f"https://newsapi.org/v2/top-headlines?language=es&pageSize=30&apiKey={NEWS_API_KEY}"
    r = requests.get(url, timeout=15)
    data = r.json()
    
    noticias = []
    for art in data.get('articles', []):
        if art.get('title') and '[Removed]' not in art['title']:
            noticias.append({
                'titulo': art['title'],
                'descripcion': art.get('description', ''),
                'contenido': art.get('content', art.get('description', '')),
                'url': art['url'],
                'fuente': art.get('source', {}).get('name', 'NewsAPI'),
                'fecha': art.get('publishedAt', '')
            })
    return noticias

def buscar_rss(url_rss, nombre_fuente):
    r = requests.get(url_rss, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    feed = feedparser.parse(r.content)
    
    noticias = []
    for entry in feed.entries[:15]:
        desc = entry.get('summary', entry.get('description', ''))
        if '<' in desc:
            desc = BeautifulSoup(desc, 'html.parser').get_text()
        
        noticias.append({
            'titulo': entry.title,
            'descripcion': desc[:300],
            'contenido': entry.get('content', [{}])[0].get('value', desc),
            'url': entry.link,
            'fuente': nombre_fuente,
            'fecha': entry.get('published', '')
        })
    
    return noticias

# ============================================================================
# 2. SELECCIÓN CON OPENAI
# ============================================================================

def seleccionar_mejor_noticia(noticias):
    print("\n" + "="*60)
    print("🤖 SELECCIONANDO MEJOR NOTICIA")
    print("="*60)
    
    if len(noticias) == 1:
        return noticias[0]
    
    resumen = ""
    for i, n in enumerate(noticias[:10], 1):
        resumen += f"{i}. {n['titulo'][:80]} ({n['fuente']})\n"
    
    prompt = f"""Selecciona la NOTICIA MÁS IMPORTANTE de actualidad mundial:

{resumen}

Responde SOLO con el número (1-10):"""

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 5
            },
            timeout=30
        )
        
        resultado = r.json()
        seleccion = resultado['choices'][0]['message']['content'].strip()
        numero = int(re.search(r'\d+', seleccion).group()) - 1
        
        if 0 <= numero < len(noticias):
            print(f"✓ Seleccionada: #{numero + 1}")
            return noticias[numero]
            
    except Exception as e:
        print(f"⚠️ Error selección: {e}")
    
    return noticias[0]

# ============================================================================
# 3. REESCRITURA PROFESIONAL
# ============================================================================

def reescribir_noticia(noticia):
    print("\n" + "="*60)
    print("✍️ REESCRIBIENDO NOTICIA")
    print("="*60)
    
    prompt = f"""Actúa como editor jefe de medio internacional. Reescribe profesionalmente:

TÍTULO ORIGINAL: {noticia['titulo']}
FUENTE: {noticia['fuente']}
TEXTO: {noticia['descripcion'][:600]}

REQUISITOS:
- Título SEO: 60-80 caracteres, impactante
- Redacción: Estilo periodístico profesional, 3-4 párrafos
- SEO: Incluir palabras clave naturales
- Tono: Serio, autoritario, neutral
- NO inventar hechos

JSON:
{{
    "titulo_seo": "Título optimizado",
    "contenido": "Texto profesional completo",
    "resumen": "Resumen corto redes sociales",
    "palabras_clave": ["kw1", "kw2", "kw3", "kw4", "kw5"],
    "categoria": "politica/economia/tecnologia/salud/internacional/deportes",
    "hashtags": "#Tag1 #Tag2 #Tag3"
}}"""

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=60
        )
        
        resultado = r.json()
        texto = resultado['choices'][0]['message']['content']
        
        json_match = re.search(r'\{.*\}', texto, re.DOTALL)
        if json_match:
            datos = json.loads(json_match.group())
            
            print(f"✓ Título: {datos['titulo_seo'][:60]}...")
            print(f"✓ Categoría: {datos['categoria']}")
            print(f"✓ Keywords: {', '.join(datos['palabras_clave'])}")
            
            return datos
            
    except Exception as e:
        print(f"⚠️ Error reescritura: {e}")
    
    # Fallback
    return {
        'titulo_seo': noticia['titulo'],
        'contenido': noticia['descripcion'],
        'resumen': noticia['descripcion'][:100],
        'palabras_clave': ['noticias', 'actualidad', 'internacional'],
        'categoria': 'general',
        'hashtags': '#Noticias #Actualidad'
    }

# ============================================================================
# 4. GENERACIÓN DE IMÁGEN CON IA (SOLO IA, NUNCA DESCARGA ORIGINAL)
# ============================================================================

def generar_imagen(titulo, keywords, categoria):
    """
    Genera imagen SOLO con IA (Stability primero, DALL-E fallback)
    NUNCA descarga imagen original de la noticia
    """
    print("\n" + "="*60)
    print("🎨 GENERANDO IMAGEN CON IA")
    print("="*60)
    
    # OPCIÓN 1: Stability AI
    if STABILITY_API_KEY:
        print("Intentando Stability AI...")
        ruta = generar_stability(titulo, keywords, categoria)
        if ruta:
            return ruta
    
    # OPCIÓN 2: OpenAI DALL-E (siempre disponible)
    print("Intentando OpenAI DALL-E...")
    ruta = generar_dalle(titulo, keywords, categoria)
    if ruta:
        return ruta
    
    print("❌ No se pudo generar imagen")
    return None

def generar_stability(titulo, keywords, categoria):
    """Genera imagen con Stability AI"""
    try:
        kw_text = ', '.join(keywords[:3])
        
        estilos = {
            'politica': 'professional political photojournalism, documentary, serious, Reuters style',
            'economia': 'business news photography, corporate, financial, blue professional',
            'tecnologia': 'futuristic tech visualization, modern innovation, clean design',
            'salud': 'medical healthcare photography, hospital, clinical professional',
            'internacional': 'global news photojournalism, world events, international affairs',
            'deportes': 'sports action photography, stadium, dynamic, energetic'
        }
        
        estilo = estilos.get(categoria, 'professional news photography, photojournalism')
        
        prompt = f"Editorial news image: {titulo}. Themes: {kw_text}. Style: {estilo}. NO text, NO logos, NO watermarks, photorealistic, 4K."
        
        print(f"Prompt: {prompt[:100]}...")
        
        r = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "Authorization": f"Bearer {STABILITY_API_KEY}",
                "Accept": "image/*"
            },
            files={
                "prompt": (None, prompt[:500]),
                "output_format": (None, "png"),
                "aspect_ratio": (None, "16:9")
            },
            timeout=60
        )
        
        if r.status_code == 200:
            import time
            ruta = f"/tmp/stability_{int(time.time())}.png"
            with open(ruta, 'wb') as f:
                f.write(r.content)
            
            if os.path.exists(ruta) and os.path.getsize(ruta) > 1024:
                print(f"✓ Stability: {os.path.basename(ruta)} ({os.path.getsize(ruta)} bytes)")
                return ruta
        else:
            print(f"✗ Stability HTTP {r.status_code}")
            
    except Exception as e:
        print(f"✗ Stability error: {e}")
    
    return None

def generar_dalle(titulo, keywords, categoria):
    """Genera imagen con OpenAI DALL-E 3"""
    try:
        import time
        
        kw_text = ', '.join(keywords[:3])
        
        estilos = {
            'politica': 'professional political photojournalism, documentary style',
            'economia': 'business news photography, corporate professional',
            'tecnologia': 'modern tech innovation, futuristic clean design',
            'salud': 'medical healthcare photography, professional clinical',
            'internacional': 'global news photojournalism, world affairs',
            'deportes': 'sports photography, stadium atmosphere, dynamic'
        }
        
        estilo = estilos.get(categoria, 'professional news photography, editorial')
        
        prompt = f"Create a professional news editorial image for: {titulo}. Visual themes: {kw_text}. Style: {estilo}. The image must have absolutely NO text, NO logos, NO watermarks, NO words, NO letters. Photorealistic, high quality, suitable for international news publication."
        
        print(f"Prompt DALL-E: {prompt[:100]}...")
        
        # Generar imagen
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt[:1000],
                "size": "1792x1024",  # Formato horizontal 16:9
                "quality": "standard",
                "n": 1
            },
            timeout=60
        )
        
        resultado = r.json()
        
        if r.status_code == 200 and 'data' in resultado:
            img_url = resultado['data'][0]['url']
            print(f"✓ DALL-E URL obtenida, descargando...")
            
            # Descargar imagen generada
            img_r = requests.get(img_url, timeout=30)
            if img_r.status_code == 200:
                ruta = f"/tmp/dalle_{int(time.time())}.png"
                with open(ruta, 'wb') as f:
                    f.write(img_r.content)
                
                if os.path.exists(ruta) and os.path.getsize(ruta) > 1024:
                    print(f"✓ DALL-E: {os.path.basename(ruta)} ({os.path.getsize(ruta)} bytes)")
                    return ruta
        else:
            error = resultado.get('error', {}).get('message', 'Error desconocido')
            print(f"✗ DALL-E error: {error}")
            
    except Exception as e:
        print(f"✗ DALL-E error: {e}")
    
    return None

# ============================================================================
# 5. PUBLICACIÓN EN FACEBOOK
# ============================================================================

def publicar_facebook(titulo, contenido, resumen, palabras_clave, hashtags, imagen_ruta, url_fuente, nombre_fuente):
    """
    Publica en Facebook con imagen generada por IA
    """
    print("\n" + "="*60)
    print("📘 PUBLICANDO EN FACEBOOK")
    print("="*60)
    
    # Mensaje principal (conciso para foto)
    mensaje_foto = f"""📰 {titulo}

{resumen}

{hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
    
    post_id = None
    
    # MÉTODO 1: Con imagen (subir archivo local)
    if imagen_ruta and os.path.exists(imagen_ruta):
        print(f"Subiendo foto: {os.path.basename(imagen_ruta)}")
        
        try:
            url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
            
            with open(imagen_ruta, 'rb') as foto:
                files = {'file': ('noticia.png', foto, 'image/png')}
                data = {
                    'message': mensaje_foto,
                    'access_token': FB_ACCESS_TOKEN,
                    'published': 'true'
                }
                
                r = requests.post(url, files=files, data=data, timeout=60)
                resultado = r.json()
                
                print(f"Status: {r.status_code}")
                
                if r.status_code == 200 and 'id' in resultado:
                    post_id = resultado.get('post_id') or resultado['id']
                    print(f"✓ PUBLICADO CON FOTO: {post_id}")
                else:
                    error = resultado.get('error', {}).get('message', 'Error')
                    print(f"✗ Error foto: {error}")
                    
        except Exception as e:
            print(f"✗ Error subiendo foto: {e}")
    
    # MÉTODO 2: Solo texto (fallback)
    if not post_id:
        print("Publicando solo texto...")
        
        try:
            url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
            
            mensaje_largo = f"""📰 {titulo}

{contenido}

{hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
            
            data = {
                'message': mensaje_largo,
                'access_token': FB_ACCESS_TOKEN,
                'link': url_fuente
            }
            
            r = requests.post(url, data=data, timeout=60)
            resultado = r.json()
            
            if r.status_code == 200 and 'id' in resultado:
                post_id = resultado['id']
                print(f"✓ PUBLICADO (texto): {post_id}")
            else:
                print(f"✗ Error: {resultado}")
                return False
                
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    # Agregar comentario con fuente
    if post_id:
        agregar_comentario(post_id, url_fuente, nombre_fuente)
        return True
    
    return False

def agregar_comentario(post_id, url_fuente, nombre_fuente):
    """Agrega comentario con link a fuente original"""
    try:
        import time
        time.sleep(2)  # Esperar a que se cree el post
        
        print("Agregando comentario con fuente...")
        
        post_clean = post_id.split('_')[-1] if '_' in post_id else post_id
        
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}_{post_clean}/comments"
        
        mensaje = f"""📎 Fuente original: {nombre_fuente}

🔗 {url_fuente}

_Síguenos para más noticias internacionales_"""
        
        r = requests.post(url, data={
            'message': mensaje,
            'access_token': FB_ACCESS_TOKEN
        }, timeout=30)
        
        if r.status_code == 200:
            print("✓ Comentario agregado")
        else:
            print(f"⚠️ Error comentario: {r.status_code}")
            
    except Exception as e:
        print(f"⚠️ Error comentario: {e}")

# ============================================================================
# LIMPIEZA
# ============================================================================

def limpiar():
    try:
        import time
        for archivo in os.listdir('/tmp'):
            if archivo.startswith(('stability_', 'dalle_')):
                try:
                    os.remove(f'/tmp/{archivo}')
                except:
                    pass
    except:
        pass

# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================

def main():
    print("\n" + "="*60)
    print("🚀 BOT DE NOTICIAS - IA GENERATIVA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 1. Buscar noticias
        noticias = buscar_noticias()
        if not noticias:
            print("❌ No hay noticias")
            return False
        
        # 2. Seleccionar la mejor
        seleccionada = seleccionar_mejor_noticia(noticias)
        HISTORIAL_URLS.add(seleccionada['url'])
        
        print(f"\n📌 Seleccionada: {seleccionada['titulo'][:70]}")
        print(f"   Fuente: {seleccionada['fuente']}")
        
        # 3. Reescribir profesionalmente
        reescrita = reescribir_noticia(seleccionada)
        
        # 4. Generar imagen con IA (SIEMPRE, nunca descarga original)
        imagen_ruta = generar_imagen(
            reescrita['titulo_seo'],
            reescrita['palabras_clave'],
            reescrita['categoria']
        )
        
        # 5. Publicar en Facebook
        exito = publicar_facebook(
            titulo=reescrita['titulo_seo'],
            contenido=reescrita['contenido'],
            resumen=reescrita['resumen'],
            palabras_clave=reescrita['palabras_clave'],
            hashtags=reescrita['hashtags'],
            imagen_ruta=imagen_ruta,
            url_fuente=seleccionada['url'],
            nombre_fuente=seleccionada['fuente']
        )
        
        # 6. Limpiar temporales
        if imagen_ruta and os.path.exists(imagen_ruta):
            try:
                os.remove(imagen_ruta)
            except:
                pass
        limpiar()
        
        print("\n" + "="*60)
        print(f"{'✅ ÉXITO' if exito else '❌ FALLO'}")
        print("="*60)
        
        return exito
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    exito = main()
    sys.exit(0 if exito else 1)
