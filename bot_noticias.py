#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Automático para Facebook
- Redacción extensa y profunda con OpenAI
- Imagen estática generada con DALL-E (sin link)
- Fuente original en comentarios
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

NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
FB_PAGE_ID = os.getenv('FB_PAGE_ID', '')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

print("="*60)
print("🔍 VERIFICANDO CONFIGURACIÓN")
print("="*60)

errores = []
if not FB_PAGE_ID or FB_PAGE_ID.strip() == '':
    errores.append("❌ FB_PAGE_ID")
else:
    print(f"✓ FB_PAGE_ID: {FB_PAGE_ID[:10]}...")

if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN.strip() == '':
    errores.append("❌ FB_ACCESS_TOKEN")
else:
    print(f"✓ FB_ACCESS_TOKEN: {FB_ACCESS_TOKEN[:15]}...")

if not OPENAI_API_KEY or OPENAI_API_KEY.strip() == '':
    errores.append("❌ OPENAI_API_KEY")
else:
    print(f"✓ OPENAI_API_KEY: {OPENAI_API_KEY[:15]}...")

if errores:
    print("\n❌ Faltan variables:", ", ".join(errores))
    sys.exit(1)

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

# ============================================================================
# 1. BÚSQUEDA DE NOTICIAS
# ============================================================================

def buscar_noticias():
    print("\n" + "="*60)
    print("🔍 BUSCANDO NOTICIAS")
    print("="*60)
    
    todas = []
    
    if NEWS_API_KEY:
        try:
            n = buscar_newsapi()
            todas.extend(n)
            print(f"✓ NewsAPI: {len(n)}")
        except Exception as e:
            print(f"✗ NewsAPI: {e}")
    
    for nombre, url in FUENTES_RSS.items():
        try:
            n = buscar_rss(url, nombre)
            todas.extend(n)
            print(f"✓ {nombre}: {len(n)}")
        except Exception as e:
            print(f"✗ {nombre}: {str(e)[:50]}")
    
    unicas = {}
    for n in todas:
        if n['url'] not in HISTORIAL_URLS and len(n['titulo']) > 20:
            unicas[n['url']] = n
    
    resultado = list(unicas.values())
    print(f"\n📊 Total únicas: {len(resultado)}")
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
        
        # Obtener más contenido si está disponible
        contenido_completo = entry.get('content', [{}])[0].get('value', desc)
        
        noticias.append({
            'titulo': entry.title,
            'descripcion': desc[:500],
            'contenido': contenido_completo if len(contenido_completo) > 200 else desc,
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
        resumen += f"{i}. {n['titulo'][:80]} | {n['fuente']}\n"
    
    prompt = f"""Eres editor de medio internacional en español. Analiza y selecciona la NOTICIA MÁS IMPORTANTE:

{resumen}

Prioriza: impacto global, relevancia para Latinoamérica/España, actualidad, trascendencia política/económica.

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
            print(f"✓ Seleccionada #{numero + 1}: {noticias[numero]['titulo'][:60]}...")
            return noticias[numero]
            
    except Exception as e:
        print(f"⚠️ Error selección: {e}")
    
    return noticias[0]

# ============================================================================
# 3. REESCRITURA EXTENSA Y PROFUNDA CON OPENAI
# ============================================================================

def reescribir_noticia(noticia):
    print("\n" + "="*60)
    print("✍️ OPENAI: CREANDO ARTÍCULO PROFUNDO")
    print("="*60)
    
    # Combinar toda la información disponible
    texto_base = f"{noticia['titulo']}. {noticia['descripcion']}. {noticia['contenido']}"
    
    prompt = f"""Actúa como editor jefe de un medio digital internacional de prestigio. Crea un ARTÍCULO PERIODÍSTICO COMPLETO, PROFUNDO Y ANALÍTICO.

INFORMACIÓN BASE:
Fuente: {noticia['fuente']}
Texto original: {texto_base[:1500]}

REQUISITOS DEL ARTÍCULO (mínimo 600-800 palabras):

1. TÍTULO SEO (70-90 caracteres):
   - Impactante, claro, con palabra clave principal al inicio
   - Debe generar curiosidad informativa

2. LEAD (primer párrafo - 3-4 oraciones):
   - Responder: ¿Qué pasó? ¿Quién está involucrado? ¿Cuándo? ¿Dónde? ¿Por qué importa?
   - Gancho que capture la atención inmediatamente

3. DESARROLLO (3-4 párrafos extensos):
   - **Contexto histórico**: Antecedentes relevantes del tema
   - **Análisis de la situación actual**: Qué significa este evento en el presente
   - **Implicaciones políticas/económicas/sociales**: Impacto en diferentes ámbitos
   - **Reacciones internacionales**: Qué dicen otros países, organismos, expertos
   - **Datos y cifras relevantes**: Si aplica, incluir estadísticas o números importantes

4. PERSPECTIVAS (1-2 párrafos):
   - Qué se espera que pase próximamente
   - Posibles escenarios futuros
   - Desafíos pendientes

5. CIERRE (1 párrafo):
   - Resumen de la trascendencia del evento
   - Llamado a seguir la información

REGLAS:
- Tono: Periodístico serio, autoritario, pero accesible al público general
- NO inventar hechos. Si falta información, indicar "según reportes preliminares" o "se espera más información"
- Incluir transiciones fluidas entre párrafos
- SEO natural: integrar palabras clave sin forzar
- Público: Hispanohablante de Latinoamérica y España (22-55 años, interesados en actualidad)

HASHTAGS: 8-10 hashtags estratégicos para alcance orgánico (mezcla de trending y específicos)

FORMATO JSON:
{{
    "titulo_seo": "Título optimizado para SEO y engagement",
    "articulo_completo": "Artículo extenso de 600-800 palabras, bien estructurado",
    "resumen_para_foto": "Resumen corto 2-3 líneas para caption de foto",
    "palabras_clave": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6"],
    "categoria": "politica/economia/tecnologia/salud/internacional/deportes/entretenimiento",
    "hashtags": "#Tag1 #Tag2 #Tag3 #Tag4 #Tag5 #Tag6 #Tag7 #Tag8 #Tag9 #Tag10",
    "prompt_imagen": "Descripción detallada para generar imagen ilustrativa de la noticia, estilo fotoperiodismo profesional, sin texto ni logos"
}}"""

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions ",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",  # Modelo más potente para textos largos
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 3000
            },
            timeout=120
        )
        
        resultado = r.json()
        texto = resultado['choices'][0]['message']['content']
        
        json_match = re.search(r'\{.*\}', texto, re.DOTALL)
        if json_match:
            datos = json.loads(json_match.group())
            
            palabras = len(datos['articulo_completo'].split())
            print(f"✓ Artículo generado: ~{palabras} palabras")
            print(f"✓ Título: {datos['titulo_seo'][:70]}...")
            print(f"✓ Categoría: {datos['categoria']}")
            print(f"✓ Hashtags: {datos['hashtags']}")
            print(f"✓ Prompt imagen: {datos['prompt_imagen'][:80]}...")
            
            return datos
            
    except Exception as e:
        print(f"⚠️ Error reescritura: {e}")
        print(f"Respuesta: {texto[:500] if 'texto' in locals() else 'N/A'}")
    
    # Fallback mejorado
    return {
        'titulo_seo': noticia['titulo'],
        'articulo_completo': f"{noticia['descripcion']}\n\n{noticia['contenido'][:800]}\n\nEsta noticia de {noticia['fuente']} tiene implicaciones importantes en el ámbito internacional. Los analistas políticos y económicos están evaluando sus consecuencias a mediano plazo. La comunidad internacional permanece atenta a los desarrollos posteriores. Se recomienda consultar fuentes oficiales para actualizaciones.",
        'resumen_para_foto': noticia['descripcion'][:200],
        'palabras_clave': ['noticias', 'actualidad', 'internacional', 'mundo', 'hoy', 'información'],
        'categoria': 'general',
        'hashtags': '#Noticias #Actualidad #Internacional #Mundo #Hoy #News #ÚltimaHora #Información #Periodismo #MundoHoy',
        'prompt_imagen': f"Professional news photography about: {noticia['titulo']}. Editorial photojournalism style, serious, informative, high quality, NO text, NO logos"
    }

# ============================================================================
# 4. GENERACIÓN DE IMÁGEN CON DALL-E (OPENAI)
# ============================================================================

def generar_imagen_dalle(prompt_imagen, titulo):
    """
    Genera imagen con OpenAI DALL-E 3.
    Retorna ruta de archivo local (imagen estática, sin link externo)
    """
    print("\n" + "="*60)
    print("🎨 GENERANDO IMAGEN CON DALL-E 3 (OpenAI)")
    print("="*60)
    
    if not OPENAI_API_KEY:
        print("❌ No hay OPENAI_API_KEY")
        return None
    
    # Mejorar el prompt para calidad fotoperiodística
    prompt_mejorado = f"{prompt_imagen}. Professional photojournalism style, editorial news photography, high quality, cinematic lighting, photorealistic, NO text, NO logos, NO watermarks, NO words, NO letters, suitable for international news publication."
    
    print(f"Prompt: {prompt_mejorado[:100]}...")
    
    try:
        import time
        
        # Generar imagen con DALL-E 3
        r = requests.post(
            "https://api.openai.com/v1/images/generations ",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt_mejorado[:1000],
                "size": "1792x1024",  # Formato horizontal 16:9
                "quality": "standard",
                "n": 1
            },
            timeout=120
        )
        
        resultado = r.json()
        
        if r.status_code == 200 and 'data' in resultado and len(resultado['data']) > 0:
            image_url = resultado['data'][0]['url']
            revised_prompt = resultado['data'][0].get('revised_prompt', 'N/A')
            print(f"✓ DALL-E generó imagen")
            print(f"  Revised prompt: {revised_prompt[:80]}...")
            
            # Descargar la imagen generada
            print(f"  Descargando imagen...")
            img_response = requests.get(image_url, timeout=60)
            
            if img_response.status_code == 200 and len(img_response.content) > 1024:
                # Guardar como archivo local
                timestamp = int(time.time())
                hash_id = hashlib.md5(titulo.encode()).hexdigest()[:6]
                ruta = f"/tmp/dalle_{timestamp}_{hash_id}.png"
                
                with open(ruta, 'wb') as f:
                    f.write(img_response.content)
                
                # Verificar
                if os.path.exists(ruta) and os.path.getsize(ruta) > 1024:
                    print(f"✓ Imagen guardada: {os.path.basename(ruta)} ({os.path.getsize(ruta)} bytes)")
                    return ruta
            else:
                print(f"✗ Error descargando imagen: HTTP {img_response.status_code}")
        else:
            error = resultado.get('error', {}).get('message', 'Error desconocido')
            print(f"✗ DALL-E error: {error}")
            print(f"  Respuesta: {resultado}")
            
    except Exception as e:
        print(f"✗ Error generando imagen: {e}")
        import traceback
        traceback.print_exc()
    
    return None

# ============================================================================
# 5. PUBLICACIÓN EN FACEBOOK (IMAGEN ESTÁTICA, SIN LINK)
# ============================================================================

def publicar_facebook(titulo, articulo, resumen_foto, hashtags, imagen_ruta, url_fuente, nombre_fuente):
    """
    Publica en Facebook:
    - Imagen estática (subida directamente, no como link preview)
    - Texto con resumen
    - Link de fuente en comentarios (no en la publicación principal)
    """
    print("\n" + "="*60)
    print("📘 PUBLICANDO EN FACEBOOK")
    print("="*60)
    
    # Mensaje para la foto (SIN link, para que la imagen sea estática)
    mensaje_foto = f"""📰 {titulo}

{resumen_foto}

🔍 {hashtags}

💬 Link de la fuente original en el primer comentario ⬇️

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
    
    post_id = None
    
    # PUBLICAR CON IMAGEN (subida directa, estática, sin link)
    if imagen_ruta and os.path.exists(imagen_ruta):
        print(f"Subiendo imagen ESTÁTICA: {os.path.basename(imagen_ruta)}")
        print(f"  (La imagen NO tendrá link, será puramente ilustrativa)")
        
        try:
            # Endpoint /photos sube la imagen directamente a los servidores de Facebook
            # Esto crea una imagen ESTÁTICA sin link externo
            url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}/photos"
            
            with open(imagen_ruta, 'rb') as foto:
                files = {
                    'file': ('imagen_noticia.png', foto, 'image/png')
                }
                data = {
                    'message': mensaje_foto,
                    'access_token': FB_ACCESS_TOKEN,
                    'published': 'true'
                    # NO incluimos 'link' para que la imagen sea estática
                }
                
                r = requests.post(url, files=files, data=data, timeout=90)
                resultado = r.json()
                
                print(f"  Status: {r.status_code}")
                
                if r.status_code == 200 and 'id' in resultado:
                    # El post_id puede estar en 'post_id' o usar el id de la foto
                    post_id = resultado.get('post_id')
                    if not post_id and 'id' in resultado:
                        # Si no hay post_id, construirlo desde el id de la foto
                        photo_id = resultado['id']
                        post_id = f"{FB_PAGE_ID}_{photo_id}"
                    
                    print(f"✓ PUBLICADO CON IMAGEN ESTÁTICA: {post_id}")
                    print(f"  ✓ La imagen NO redirige a ningún link")
                    print(f"  ✓ Es una imagen ilustrativa pura")
                else:
                    error = resultado.get('error', {}).get('message', 'Error desconocido')
                    print(f"✗ Error: {error}")
                    print(f"  Respuesta: {resultado}")
                    post_id = None
                    
        except Exception as e:
            print(f"✗ Error subiendo imagen: {e}")
            import traceback
            traceback.print_exc()
            post_id = None
    
    # FALLBACK: Solo texto (si falló la imagen)
    if not post_id:
        print("⚠️ Fallback: Publicando solo texto con link preview...")
        
        try:
            url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}/feed"
            
            # En feed, el link crea un preview, pero no es lo ideal
            mensaje_texto = f"""📰 {titulo}

{articulo[:1200]}...

🔍 {hashtags}

📎 Fuente: {url_fuente}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""
            
            data = {
                'message': mensaje_texto,
                'access_token': FB_ACCESS_TOKEN,
                # Opcional: quitar 'link' para evitar preview, pero entonces no hay referencia
            }
            
            r = requests.post(url, data=data, timeout=60)
            resultado = r.json()
            
            if r.status_code == 200 and 'id' in resultado:
                post_id = resultado['id']
                print(f"✓ PUBLICADO (solo texto): {post_id}")
            else:
                print(f"✗ Error: {resultado}")
                return False
                
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    # AGREGAR COMENTARIOS: Artículo completo + Fuente original
    if post_id:
        import time
        
        # Pequeña pausa para asegurar que el post existe
        time.sleep(3)
        
        # Comentario 1: Artículo completo (dividido si es muy largo)
        print("\n📝 Agregando artículo completo en comentarios...")
        exito_articulo = agregar_articulo_comentarios(post_id, articulo)
        
        time.sleep(2)
        
        # Comentario 2: Link de fuente original
        print("\n🔗 Agregando link de fuente original...")
        exito_fuente = agregar_fuente_comentario(post_id, url_fuente, nombre_fuente)
        
        if exito_articulo and exito_fuente:
            print("\n✅ Todos los comentarios agregados correctamente")
        else:
            print("\n⚠️ Algunos comentarios fallaron, pero la publicación está activa")
        
        return True
    
    return False

def agregar_articulo_comentarios(post_id, articulo):
    """Agrega el artículo completo en uno o más comentarios"""
    try:
        post_clean = post_id.split('_')[-1] if '_' in post_id else post_id
        url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}_{post_clean}/comments"
        
        # Facebook tiene límite aproximado de 8000 caracteres por comentario
        MAX_CARACTERES = 7500
        
        if len(articulo) > MAX_CARACTERES:
            # Dividir en partes
            partes = []
            inicio = 0
            while inicio < len(articulo):
                # Buscar corte en párrafo
                fin = min(inicio + MAX_CARACTERES, len(articulo))
                if fin < len(articulo):
                    # Buscar último punto y aparte
                    corte = articulo.rfind('\n\n', inicio, fin)
                    if corte == -1:
                        corte = articulo.rfind('. ', inicio, fin)
                    if corte == -1:
                        corte = fin
                    fin = corte + 1 if corte > inicio else fin
                
                partes.append(articulo[inicio:fin].strip())
                inicio = fin
            
            print(f"  Artículo dividido en {len(partes)} partes")
            
            for i, parte in enumerate(partes, 1):
                if not parte:
                    continue
                    
                mensaje = f"📄 Continuación ({i}/{len(partes)}):\n\n{parte}"
                
                r = requests.post(url, data={
                    'message': mensaje,
                    'access_token': FB_ACCESS_TOKEN
                }, timeout=30)
                
                if r.status_code == 200:
                    print(f"    ✓ Parte {i} agregada")
                else:
                    print(f"    ✗ Parte {i} falló: {r.status_code}")
                
                # Pausa entre comentarios
                time.sleep(1)
        else:
            # Artículo cabe en un solo comentario
            mensaje = f"""📄 ARTÍCULO COMPLETO:

{articulo}

_Link de la fuente original en el siguiente comentario_ ⬇️"""
            
            r = requests.post(url, data={
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }, timeout=30)
            
            if r.status_code == 200:
                print(f"  ✓ Artículo completo agregado en un comentario")
            else:
                print(f"  ✗ Error: {r.status_code}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error agregando artículo: {e}")
        return False

def agregar_fuente_comentario(post_id, url_fuente, nombre_fuente):
    """Agrega comentario con el link de la fuente original"""
    try:
        post_clean = post_id.split('_')[-1] if '_' in post_id else post_id
        url = f"https://graph.facebook.com/v19.0/ {FB_PAGE_ID}_{post_clean}/comments"
        
        mensaje = f"""📎 FUENTE ORIGINAL: {nombre_fuente}

🔗 {url_fuente}

✅ Esta noticia fue verificada y reescrita por nuestro equipo editorial

📲 Síguenos para más noticias internacionales en español

#Noticias #Actualidad #Internacional #MundoHoy #NewsEnEspañol #Periodismo #Información #VerdadHoy"""
        
        r = requests.post(url, data={
            'message': mensaje,
            'access_token': FB_ACCESS_TOKEN
        }, timeout=30)
        
        if r.status_code == 200:
            print(f"  ✓ Link de fuente agregado")
            return True
        else:
            print(f"  ✗ Error: {r.status_code} - {r.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

# ============================================================================
# LIMPIEZA
# ============================================================================

def limpiar_temporales():
    """Elimina archivos de imagen temporales"""
    try:
        import time
        for archivo in os.listdir('/tmp'):
            if archivo.startswith('dalle_') and archivo.endswith('.png'):
                try:
                    ruta = f'/tmp/{archivo}'
                    os.remove(ruta)
                    print(f"🗑️ Eliminado: {archivo}")
                except:
                    pass
    except Exception as e:
        print(f"⚠️ Error limpiando: {e}")

# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================

def main():
    print("\n" + "="*60)
    print("🚀 BOT DE NOTICIAS - REDACCIÓN PROFUNDA + IMÁGEN ESTÁTICA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 1. Buscar noticias
        noticias = buscar_noticias()
        if not noticias:
            print("❌ No se encontraron noticias")
            return False
        
        # 2. Seleccionar la mejor
        seleccionada = seleccionar_mejor_noticia(noticias)
        HISTORIAL_URLS.add(seleccionada['url'])
        
        print(f"\n📌 NOTICIA SELECCIONADA:")
        print(f"   Título: {seleccionada['titulo'][:70]}")
        print(f"   Fuente: {seleccionada['fuente']}")
        print(f"   URL: {seleccionada['url'][:60]}...")
        
        # 3. Reescribir con OpenAI (ARTÍCULO PROFUNDO)
        reescrita = reescribir_noticia(seleccionada)
        
        # 4. Generar imagen con DALL-E (OpenAI) - IMAGEN ESTÁTICA
        imagen_ruta = generar_imagen_dalle(
            reescrita['prompt_imagen'],
            reescrita['titulo_seo']
        )
        
        # 5. Publicar en Facebook
        exito = publicar_facebook(
            titulo=reescrita['titulo_seo'],
            articulo=reescrita['articulo_completo'],
            resumen_foto=reescrita['resumen_para_foto'],
            hashtags=reescrita['hashtags'],
            imagen_ruta=imagen_ruta,
            url_fuente=seleccionada['url'],
            nombre_fuente=seleccionada['fuente']
        )
        
        # 6. Limpiar
        limpiar_temporales()
        
        print("\n" + "="*60)
        if exito:
            print("✅ PUBLICACIÓN COMPLETADA EXITOSAMENTE")
            print("   - Artículo extenso y profesional")
            print("   - Imagen estática generada con IA")
            print("   - Link de fuente en comentarios")
        else:
            print("❌ LA PUBLICACIÓN FALLÓ")
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
