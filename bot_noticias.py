#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Automático para Facebook
- Redacción extensa e informativa con OpenAI
- Más hashtags para alcance orgánico
- Optimizado para público hispanohablante
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
# CONFIGURACIÓN - Variables de Entorno
# ============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
FB_PAGE_ID = os.getenv('FB_PAGE_ID', '')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN', '')  # ✅ CORREGIDO: era B_ACCESS_TOKEN
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY', '')

# Verificación detallada
print("="*60)
print("🔍 VERIFICANDO CONFIGURACIÓN")
print("="*60)

errores = []

if not FB_PAGE_ID or FB_PAGE_ID.strip() == '':
    errores.append("❌ FB_PAGE_ID: No configurado")
else:
    print(f"✓ FB_PAGE_ID: {FB_PAGE_ID[:10]}...")

if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN.strip() == '':
    errores.append("❌ FB_ACCESS_TOKEN: No configurado")
else:
    print(f"✓ FB_ACCESS_TOKEN: {FB_ACCESS_TOKEN[:15]}...")

if not OPENAI_API_KEY or OPENAI_API_KEY.strip() == '':
    errores.append("❌ OPENAI_API_KEY: No configurado")
else:
    print(f"✓ OPENAI_API_KEY: {OPENAI_API_KEY[:15]}...")

if errores:
    print("\n" + "="*60)
    print("❌ ERROR: Faltan variables obligatorias")
    print("="*60)
    for error in errores:
        print(error)
    print("\n💡 Configura los SECRETS en GitHub:")
    print("   Settings → Secrets and variables → Actions → New repository secret")
    sys.exit(1)

print("="*60)
print("✅ Configuración OK")
print("="*60)

# ============================================================================
# FUENTES RSS
# ============================================================================

FUENTES_RSS = {
    'BBC Mundo': 'http://feeds.bbci.co.uk/news/world/rss.xml ',
    'Reuters': 'http://feeds.reuters.com/reuters/worldnews ',
    'CNN World': 'http://rss.cnn.com/rss/edition_world.rss ',
    'El País': 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada ',
    'Clarín': 'https://www.clarin.com/rss/lo-ultimo/ ',
    'Infobae': 'https://www.infobae.com/feeds/rss/ ',
}

HISTORIAL_URLS = set()
MAX_HISTORIAL = 100

# ============================================================================
# 1. BÚSQUEDA DE NOTICIAS
# ============================================================================

def buscar_noticias():
    print("\n" + "="*60)
    print("🔍 BUSCANDO NOTICIAS DE ACTUALIDAD")
    print("="*60)
    
    todas = []
    
    if NEWS_API_KEY:
        try:
            n = buscar_newsapi()
            todas.extend(n)
            print(f"✓ NewsAPI: {len(n)} noticias")
        except Exception as e:
            print(f"✗ NewsAPI: {e}")
    
    for nombre, url in FUENTES_RSS.items():
        try:
            n = buscar_rss(url, nombre)
            todas.extend(n)
            print(f"✓ {nombre}: {len(n)} noticias")
        except Exception as e:
            print(f"✗ {nombre}: {str(e)[:50]}")
    
    unicas = {}
    for n in todas:
        if n['url'] not in HISTORIAL_URLS and len(n['titulo']) > 20:
            unicas[n['url']] = n
    
    resultado = list(unicas.values())
    print(f"\n📊 Total únicas disponibles: {len(resultado)}")
    return resultado

def buscar_newsapi():
    url = f"https://newsapi.org/v2/top-headlines?language=es&pageSize=30&apiKey= {NEWS_API_KEY}"
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
            'descripcion': desc[:500],
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
    
    prompt = f"""Eres editor de medio internacional en español. Selecciona la NOTICIA MÁS RELEVANTE para público hispanohablante:

{resumen}

Prioriza: impacto global, relevancia para Latinoamérica/España, actualidad.

Responde SOLO con el número (1-10):"""

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions ",
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
            print(f"✓ Seleccionada noticia #{numero + 1}")
            return noticias[numero]
            
    except Exception as e:
        print(f"⚠️ Error selección: {e}")
    
    return noticias[0]

# ============================================================================
# 3. REESCRITURA EXTENSA Y PROFESIONAL
# ============================================================================

def reescribir_noticia(noticia):
    print("\n" + "="*60)
    print("✍️ OPENAI: CREANDO ARTÍCULO EXTENSO")
    print("="*60)
    
    prompt = f"""Actúa como editor jefe de un medio digital internacional en ESPAÑOL. Crea un ARTÍCULO COMPLETO Y EXTENSO basado en esta noticia.

NOTICIA ORIGINAL:
Título: {noticia['titulo']}
Fuente: {noticia['fuente']}
Texto base: {noticia['descripcion'][:800]}

INSTRUCCIONES PARA EL ARTÍCULO:
1. EXTENSIÓN: Mínimo 5-6 párrafos desarrollados (400-600 palabras)
2. ESTRUCTURA PROFESIONAL:
   - Titular SEO: Impactante, 60-80 caracteres, palabras clave al inicio
   - Lead: Primer párrafo que responda qué, quién, cuándo, dónde, por qué
   - Desarrollo: Contexto histórico, implicaciones, análisis de impacto
   - Perspectivas: Qué sigue, posibles consecuencias
   - Cierre: Resumen de la importancia de la noticia

3. TONO: Periodístico serio, informativo, autoritario, pero accesible
4. SEO: Integrar naturalmente palabras clave en el texto
5. PÚBLICO: Hispanohablante de Latinoamérica y España
6. NO inventar hechos, solo expandir y contextualizar la información real

HASHTAGS: Generar 8-10 hashtags relevantes para alcance orgánico (mezcla de populares y específicos)

JSON DE SALIDA:
{{
    "titulo_seo": "Título optimizado para SEO y engagement",
    "articulo_completo": "Artículo extenso de 5-6 párrafos profesionales",
    "resumen_redes": "Resumen atractivo de 2-3 líneas para redes sociales",
    "palabras_clave": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "categoria": "politica/economia/tecnologia/salud/internacional/deportes/entretenimiento",
    "hashtags": "#Tag1 #Tag2 #Tag3 #Tag4 #Tag5 #Tag6 #Tag7 #Tag8"
}}"""

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions ",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2500
            },
            timeout=90
        )
        
        resultado = r.json()
        texto = resultado['choices'][0]['message']['content']
        
        json_match = re.search(r'\{.*\}', texto, re.DOTALL)
        if json_match:
            datos = json.loads(json_match.group())
            
            # Verificar que el artículo sea extenso
            palabras = len(datos['articulo_completo'].split())
            print(f"✓ Artículo generado: ~{palabras} palabras")
            print(f"✓ Título: {datos['titulo_seo'][:60]}...")
            print(f"✓ Categoría: {datos['categoria']}")
            print(f"✓ Hashtags: {datos['hashtags']}")
            
            return datos
            
    except Exception as e:
        print(f"⚠️ Error reescritura: {e}")
    
    # Fallback mejorado
    return {
        'titulo_seo': noticia['titulo'],
        'articulo_completo': noticia['descripcion'] + "\n\n" + noticia['contenido'][:500] + "\n\nEsta información de " + noticia['fuente'] + " es de relevancia internacional. Los expertos señalan que este tipo de acontecimientos tendrá repercusiones significativas en los próximos días. La comunidad internacional permanece atenta a los desarrollos posteriores. Se recomienda seguir las fuentes oficiales para obtener información actualizada.",
        'resumen_redes': noticia['descripcion'][:150],
        'palabras_clave': ['noticias', 'actualidad', 'internacional', 'mundo', 'hoy'],
        'categoria': 'general',
        'hashtags': '#Noticias #Actualidad #Internacional #Mundo #Hoy #News #ÚltimaHora #Información'
    }

# ============================================================================
# 4. GENERACIÓN DE IMÁGEN CON IA
# ============================================================================

def generar_imagen(titulo, keywords, categoria):
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
    try:
        import time
        kw_text = ', '.join(keywords[:3])
        
        estilos = {
            'politica': 'professional political photojournalism, documentary, serious, Reuters AP style',
            'economia': 'business news photography, corporate, financial district, professional',
            'tecnologia': 'futuristic tech visualization, innovation, clean modern design',
            'salud': 'medical healthcare photography, hospital, clinical professional',
            'internacional': 'global news photojournalism, world events, international affairs',
            'deportes': 'sports action photography, stadium, dynamic, energetic',
            'entretenimiento': 'entertainment news photography, media event, celebrity'
        }
        
        estilo = estilos.get(categoria, 'professional news photography, editorial')
        
        prompt = f"Editorial news image for Spanish-speaking audience: {titulo}. Visual themes: {kw_text}. Style: {estilo}. NO text, NO logos, NO watermarks, photorealistic, 4K quality."
        
        print(f"Prompt: {prompt[:100]}...")
        
        r = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core ",
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
            ruta = f"/tmp/stability_{int(time.time())}.png"
            with open(ruta, 'wb') as f:
                f.write(r.content)
            
            if os.path.exists(ruta) and os.path.getsize(ruta) > 1024:
                print(f"✓ Stability: {os.path.basename(ruta)}")
                return ruta
        else:
            print(f"✗ Stability HTTP {r.status_code}")
            
    except Exception as e:
        print(f"✗ Stability error: {e}")
    
    return None

def generar_dalle(titulo, keywords, categoria):
    try:
        import time
        kw_text = ', '.join(keywords[:3])
        
        estilos = {
            'politica': 'professional political photojournalism, documentary style, serious editorial',
            'economia': 'business news photography, corporate professional setting',
            'tecnologia': 'modern tech innovation, futuristic clean design',
            'salud': 'medical healthcare photography, professional clinical',
            'internacional': 'global news photojournalism, world affairs',
            'deportes': 'sports photography, stadium atmosphere, dynamic',
            'entretenimiento': 'entertainment news photography, media event'
        }
        
        estilo = estilos.get(categoria, 'professional news photography, editorial')
        
        prompt = f"Create a professional news editorial image for Spanish-speaking audience about: {titulo}. Visual elements: {kw_text}. Style: {estilo}. NO text, NO logos, NO watermarks, NO words. Photorealistic, high quality, suitable for international news publication."
        
        print(f"Prompt DALL-E: {prompt[:100]}...")
        
        r = requests.post(
            "https://api.openai.com/v1/images/generations ",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt[:1000],
                "size": "1792x1024",
                "quality": "standard",
                "n": 1
            },
            timeout=60
        )
        
        resultado = r.json()
        
        if r.status_code == 200 and 'data' in resultado:
            img_url = resultado['data'][0]['url']
            print(f"✓ DALL-E URL obtenida, descargando...")
            
            img_r = requests.get(img_url, timeout=30)
            if img_r.status_code == 200:
                ruta = f"/tmp/dalle_{int(time.time())}.png"
                with open(ruta, 'wb') as f:
                    f.write(img_r.content)
                
                if os.path.exists(ruta) and os.path.getsize(ruta) > 1024:
                    print(f"✓ DALL-E: {os.path.basename(ruta)}")
                    return ruta
        else:
            error = resultado.get('error', {}).get('message', 'Error')
            print(f"✗ DALL-E error: {error}")
            
    except Exception as e:
        print(f"✗ DALL-E error: {e}")
    
    return None

# ============================================================================
# 5. PUBLICACIÓN EN FACEBOOK
# ============================================================================

def publicar_facebook(titulo, articulo, resumen, hashtags, imagen_ruta, url_fuente, nombre_fuente):
    print("\n" + "="*60)
    print("📘 PUBLICANDO EN FACEBOOK")
    print("="*60)
    
    # Mensaje para foto (más corto)
    mensaje_foto = f"""📰 {titulo}

{resumen}

🔍 {hashtags}

✍️ Artículo completo en los comentarios ⬇️

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
    
    post_id = None
    
    # PUBLICAR CON IMAGEN
    if imagen_ruta and os.path.exists(imagen_ruta):
        print(f"Subiendo foto: {os.path.basename(imagen_ruta)}")
        
        try:
            url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}/photos"
            
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
    
    # SIN IMAGEN (fallback)
    if not post_id:
        print("Publicando solo texto...")
        
        try:
            url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}/feed"
            
            mensaje_texto = f"""📰 {titulo}

{articulo[:1500]}...

{hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
            
            data = {
                'message': mensaje_texto,
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
    
    # COMENTARIOS: Artículo completo + Fuente
    if post_id:
        import time
        time.sleep(3)
        
        # Comentario 1: Artículo completo
        comentario_articulo(post_id, articulo)
        time.sleep(2)
        
        # Comentario 2: Fuente
        comentario_fuente(post_id, url_fuente, nombre_fuente)
        
        return True
    
    return False

def comentario_articulo(post_id, articulo):
    """Agrega el artículo completo en comentarios"""
    try:
        print("Agregando artículo completo...")
        
        post_clean = post_id.split('_')[-1] if '_' in post_id else post_id
        url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}_{post_clean}/comments"
        
        # Si es muy largo, dividir
        max_len = 8000
        if len(articulo) > max_len:
            partes = [articulo[i:i+max_len] for i in range(0, len(articulo), max_len)]
            for i, parte in enumerate(partes, 1):
                mensaje = f"📄 Continuación ({i}/{len(partes)}):\n\n{parte}"
                requests.post(url, data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN}, timeout=30)
                time.sleep(1)
        else:
            mensaje = f"📄 ARTÍCULO COMPLETO:\n\n{articulo}\n\n_Fuente en siguiente comentario_ ⬇️"
            r = requests.post(url, data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN}, timeout=30)
            if r.status_code == 200:
                print("✓ Artículo agregado")
        
    except Exception as e:
        print(f"⚠️ Error artículo: {e}")

def comentario_fuente(post_id, url_fuente, nombre_fuente):
    """Agrega comentario con link a fuente"""
    try:
        print("Agregando fuente original...")
        
        post_clean = post_id.split('_')[-1] if '_' in post_id else post_id
        url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}_{post_clean}/comments"
        
        mensaje = f"""📎 FUENTE ORIGINAL: {nombre_fuente}

🔗 {url_fuente}

📲 Síguenos para más noticias internacionales en español

#Noticias #Actualidad #Internacional #MundoHoy #NewsEnEspañol"""
        
        r = requests.post(url, data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN}, timeout=30)
        if r.status_code == 200:
            print("✓ Fuente agregada")
        
    except Exception as e:
        print(f"⚠️ Error fuente: {e}")

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
    print("🚀 BOT DE NOTICIAS - REDACCIÓN EXTENSA")
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
        
        print(f"\n📌 Noticia seleccionada:")
        print(f"   {seleccionada['titulo'][:70]}")
        print(f"   Fuente: {seleccionada['fuente']}")
        
        # 3. Reescribir profesionalmente (ARTÍCULO EXTENSO)
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
            articulo=reescrita['articulo_completo'],
            resumen=reescrita['resumen_redes'],
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
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    exito = main()
    sys.exit(0 if exito else 1)
