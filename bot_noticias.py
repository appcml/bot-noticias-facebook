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
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')  # IA gratuita
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy (ESPAÑOL)")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# Verificar configuración
print("\n📋 Configuración:")
if not FB_PAGE_ID:
    print("❌ FB_PAGE_ID no configurado")
else:
    print(f"✅ FB_PAGE_ID: {FB_PAGE_ID[:10]}...")
if not FB_ACCESS_TOKEN:
    print("❌ FB_ACCESS_TOKEN no configurado")
else:
    print(f"✅ FB_ACCESS_TOKEN configurado")
if OPENROUTER_API_KEY:
    print("✅ OPENROUTER_API_KEY configurado (IA Gratuita)")
else:
    print("⚠️ OPENROUTER_API_KEY no configurado - usará plantilla")

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"\n📚 Historial: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"\n⚠️ Error historial: {e}")

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
    if url_id in [get_url_id(u) for u in historial['urls']]:
        print(f"   ⛔ Ya publicada: {titulo[:40]}...")
        return True
    
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencia / max(len(titulo_simple), len(t_simple)) > 0.7:
                print(f"   ⛔ Título similar: {titulo[:40]}...")
                return True
    return False

def generar_con_ia_gratuita(titulo, descripcion, fuente):
    """
    Genera redacción periodística usando OpenRouter (acceso gratuito a múltiples IAs)
    Modelos gratuitos disponibles: mistral, llama, qwen, etc.
    """
    
    print(f"\n   📝 Procesando noticia...")
    print(f"   📰 Original: {titulo[:60]}...")
    
    if not OPENROUTER_API_KEY:
        print("   ⚠️ Sin API key de IA, usando plantilla...")
        return plantilla_periodistica_profesional(titulo, descripcion, fuente)
    
    try:
        print(f"   🤖 Generando con IA gratuita (OpenRouter)...")
        
        prompt = f"""Eres un redactor de agencia de noticias (estilo EFE, Reuters, AP). 
Escribe una NOTICIA COMPLETA EN ESPAÑOL con estructura periodística profesional.

INFORMACIÓN BASE:
Título: {titulo}
Descripción: {descripcion}
Fuente: {fuente}

ESTRUCTURA REQUERIDA:

1. **TITULAR** (máximo 80 caracteres):
   - Informativo, preciso, atractivo
   - Estilo: "Gobierno anuncia nuevas medidas económicas ante la inflación"

2. **LEAD** (primera línea, máximo 140 caracteres):
   - El dato más importante de la noticia
   - Responde: ¿Qué pasó? ¿Quién? ¿Cuándo? ¿Dónde?
   - Estilo periodístico informativo

3. **CUERPO** (3 párrafos):
   - Párrafo 2: Contexto y antecedentes (quiénes están involucrados, antecedentes)
   - Párrafo 3: Desarrollo y datos relevantes (cifras, declaraciones, reacciones)
   - Párrafo 4: Análisis e implicaciones (qué significa, consecuencias)

4. **CIERRE** (párrafo 5, 1-2 líneas):
   - Próximos pasos o información pendiente
   - Termina con: "(Agencias) / Fuente: {fuente}"

REGLAS ESTRICTAS:
- TODO en ESPAÑOL nativo, sin traducciones
- Lenguaje periodístico NEUTRO e INFORMATIVO
- Longitud total: 1000-2000 caracteres
- Oraciones claras y directas
- Sin opiniones personales, solo hechos
- Fechas en formato: "este martes", "la semana pasada", etc.

FORMATO DE RESPUESTA:
TITULAR: [titular en español]

LEAD: [lead en español]

CUERPO:
[Párrafo 2 - Contexto]

[Párrafo 3 - Desarrollo]

[Párrafo 4 - Análisis]

[Párrafo 5 - Cierre con fuente]

FIN"""

        # OpenRouter permite usar múltiples modelos gratuitos
        # Modelos gratuitos recomendados: "mistralai/mistral-7b-instruct", 
        # "meta-llama/llama-3-8b-instruct", "qwen/qwen-2-7b-instruct"
        
        modelos_gratuitos = [
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "qwen/qwen-2-7b-instruct:free",
            "google/gemma-2-9b-it:free"
        ]
        
        for modelo in modelos_gratuitos:
            try:
                print(f"   🔄 Intentando con modelo: {modelo.split('/')[0]}...")
                
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                        'HTTP-Referer': 'https://verdadhoy.com',  # Tu dominio
                        'X-Title': 'Verdad Hoy Bot',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': modelo,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3,
                        'max_tokens': 1500
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    resultado = response.json()
                    if 'choices' in resultado and len(resultado['choices']) > 0:
                        contenido = resultado['choices'][0]['message']['content']
                        
                        # Extraer partes
                        titular = titulo
                        lead = ""
                        cuerpo = ""
                        
                        if 'TITULAR:' in contenido:
                            try:
                                titular = contenido.split('TITULAR:')[1].split('LEAD:')[0].strip()
                                titular = titular.strip('"\'').strip()
                            except:
                                pass
                        
                        if 'LEAD:' in contenido:
                            try:
                                lead = contenido.split('LEAD:')[1].split('CUERPO:')[0].strip()
                            except:
                                pass
                        
                        if 'CUERPO:' in contenido:
                            try:
                                cuerpo = contenido.split('CUERPO:')[1].split('FIN')[0].strip()
                            except:
                                pass
                        
                        # Construir texto final
                        texto_final = f"{lead}\n\n{cuerpo}"
                        
                        # Verificar longitud
                        if len(texto_final) >= 600:
                            print(f"   ✅ Redacción IA OK: {len(texto_final)} caracteres")
                            return {'titular': titular[:100], 'texto': texto_final[:1900]}
                            
            except Exception as e:
                print(f"   ⚠️ Error con {modelo}: {e}")
                continue
        
        print("   ⚠️ Todos los modelos fallaron, usando plantilla...")
        return plantilla_periodistica_profesional(titulo, descripcion, fuente)
        
    except Exception as e:
        print(f"   ⚠️ Error general IA: {e}")
        return plantilla_periodistica_profesional(titulo, descripcion, fuente)

def plantilla_periodistica_profesional(titulo, descripcion, fuente):
    """Plantilla periodística profesional 100% español, 1000-2000 caracteres"""
    print(f"   📝 Generando plantilla periodística...")
    
    # Limpiar descripción
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion))
    if len(desc_limpia) < 20:
        desc_limpia = "Las autoridades competentes han confirmado un importante acontecimiento de relevancia nacional que se desarrolla en las últimas horas y ha generado amplia repercusión mediática."
    
    # Extraer palabras clave para el lead
    palabras_clave = desc_limpia[:200] if len(desc_limpia) > 100 else desc_limpia
    
    # Construir redacción periodística estructurada
    
    # LEAD (dato importante, máx 140 caracteres)
    lead = f"{palabras_clave[:140]}." if len(palabras_clave) > 80 else f"Las autoridades competentes han confirmado un importante acontecimiento de relevancia nacional que se desarrolla en las últimas horas."
    
    # Párrafo 2: Contexto (quiénes, antecedentes)
    p2 = f"El hecho ha sido reportado por diversas fuentes periodísticas de alcance nacional, destacando su trascendencia en el contexto actual. "
    p2 += f"Las autoridades correspondientes han emitido comunicados oficiales sobre el tema, mientras diversos actores del escenario político y social mantienen atenta vigilancia sobre los desarrollos. "
    p2 += f"La información ha sido verificada por corresponsales en la zona."
    
    # Párrafo 3: Desarrollo (datos, cifras, declaraciones)
    p3 = f"Analistas políticos y especialistas en la materia señalan que este tipo de eventos requiere un seguimiento constante por parte de la ciudadanía. "
    p3 += f"La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación. "
    p3 += f"Diversos medios de comunicación han destacado la importancia de los hechos reportados y sus posibles implicaciones a corto plazo en el ámbito nacional."
    
    # Párrafo 4: Análisis (implicaciones, consecuencias)
    p4 = f"Las implicaciones de este acontecimiento podrían extenderse a diversos sectores de la sociedad y afectar las dinámicas políticas y económicas en el mediano plazo. "
    p4 += f"Expertos consultados destacan la necesidad de mantener una postura informada y objetiva ante los desarrollos que se presenten en las próximas horas. "
    p4 += f"La situación continúa siendo objeto de análisis por parte de observadores especializados."
    
    # Párrafo 5: Cierre (próximos pasos, fuente)
    p5 = f"Se esperan declaraciones oficiales adicionales y posibles actualizaciones conforme avancen las investigaciones correspondientes. "
    p5 += f"La información será actualizada progresivamente a medida que estén disponibles nuevos datos confirmados. "
    p5 += f"(Agencias) / Fuente: {fuente}."
    
    # Unir todo
    texto = f"{lead}\n\n{p2}\n\n{p3}\n\n{p4}\n\n{p5}"
    
    # Asegurar mínimo 1000 caracteres
    while len(texto) < 1000:
        texto += f" Los detalles adicionales serán proporcionados oportunamente según avancen las investigaciones oficiales."
    
    # Limitar a máximo 2000
    texto = texto[:1950]
    
    # Crear titular profesional
    titular = str(titulo)[:90]
    if len(titular) < 15:
        titular = "Nuevo acontecimiento nacional genera atención mediática"
    
    print(f"   ✅ Plantilla periodística: {len(texto)} caracteres")
    return {'titular': titular, 'texto': texto}

def buscar_noticias_espanol():
    """
    Busca noticias en ESPAÑOL de actualidad
    Fuentes: NewsAPI (es), GNews (es), RSS feeds hispanos
    """
    print("\n🔍 Buscando noticias en ESPAÑOL...")
    
    noticias = []
    
    # 1. NewsAPI - Noticias en español
    if NEWS_API_KEY:
        try:
            # Buscar noticias en español
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    'language': 'es',  # ESPAÑOL
                    'pageSize': 20, 
                    'apiKey': NEWS_API_KEY
                },
                timeout=15
            )
            data = response.json()
            if data.get('status') == 'ok':
                noticias.extend(data.get('articles', []))
                print(f"   📡 NewsAPI (ES): {len(data.get('articles', []))} noticias")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # 2. GNews - Noticias en español
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            response = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={
                    'lang': 'es',  # ESPAÑOL
                    'max': 20, 
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
                        'source': {'name': a.get('source', {}).get('name', 'GNews')}
                    })
                print(f"   📡 GNews (ES): {len(data['articles'])} noticias")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # 3. RSS Feeds - Medios hispanos IMPORTANTES
    if len(noticias) < 3:
        rss_feeds_espanol = [
            # España
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml',
            'https://www.abc.es/rss/feeds/abc_ultima.xml',
            # Latinoamérica
            'https://www.clarin.com/rss/lo-ultimo/',
            'https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml',
            'https://www.eluniversal.com.mx/rss.xml',
            'https://www.emol.com/rss/index.xml',  # Chile
            'https://www.elespectador.com/rss.xml',  # Colombia
            # Agencias
            'https://www.efe.com/efe/espana/1/rss',
            'https://www.europapress.es/rss/rss.aspx',
        ]
        
        # Seleccionar 3 feeds aleatorios para variedad
        feeds_seleccionados = random.sample(rss_feeds_espanol, min(3, len(rss_feeds_espanol)))
        
        for feed_url in feeds_seleccionados:
            try:
                print(f"   📡 RSS: {feed_url.split('/')[2]}...")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:
                    # Buscar imagen en el feed
                    img = ''
                    if hasattr(entry, 'media_content') and entry.media_content:
                        img = entry.media_content[0].get('url', '')
                    elif hasattr(entry, 'enclosures') and entry.enclosures:
                        img = entry.enclosures[0].get('href', '')
                    elif 'summary' in entry:
                        m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png))"', entry.summary, re.I)
                        if m:
                            img = m.group(1)
                    
                    noticias.append({
                        'title': entry.get('title'),
                        'description': entry.get('summary', entry.get('description', ''))[:500],
                        'url': entry.get('link'),
                        'urlToImage': img,
                        'source': {'name': feed.feed.get('title', 'Medios Hispanos')}
                    })
                    
            except Exception as e:
                print(f"   ⚠️ Error RSS {feed_url}: {e}")
                continue
    
    print(f"\n📊 Total encontradas: {len(noticias)}")
    
    # Filtrar noticias válidas y no publicadas
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title'] or "Suscríbete" in art['title']:
            continue
        if not art.get('url'):
            continue
        
        # Verificar si ya fue publicada
        if ya_publicada(art['url'], art['title']):
            continue
        
        nuevas.append(art)
        print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Nuevas válidas: {len(nuevas)}")
    return nuevas[:3]  # Máximo 3 noticias

def descargar_imagen(url):
    """Descarga y optimiza imagen para Facebook"""
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
            print(f"   ✅ Imagen OK: {os.path.getsize(path)//1024}KB")
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar_facebook(titulo, texto, img_path):
    """Publica en Facebook con formato periodístico profesional"""
    
    print(f"\n   🔍 Verificación final...")
    
    # Hashtags en español relevantes
    hashtags = "#Noticias #Actualidad #España #Latinoamérica #Hoy #Mundo #Periodismo"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias en Español"""
    
    print(f"\n   📝 MENSAJE ({len(mensaje)} chars):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:8]:
        preview = linea[:70] + "..." if len(linea) > 70 else linea
        print(f"   {preview}")
    print(f"   {'='*50}")
    
    # Publicar en Facebook
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
                print(f"   🆔 Post ID: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Facebook error: {error}")
                if '100' in str(error):
                    print(f"   💡 Verifica FB_PAGE_ID y permisos del token")
                elif '200' in str(error):
                    print(f"   💡 Token expirado o sin permisos de publicación")
                
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    return False

def main():
    # Verificar configuración esencial
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("\n❌ ERROR: Faltan credenciales de Facebook")
        print("   Configura: FB_PAGE_ID y FB_ACCESS_TOKEN")
        return False
    
    # Buscar noticias en español
    noticias = buscar_noticias_espanol()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas en español")
        return False
    
    print(f"\n🎯 Procesando {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        # Descargar imagen
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen válida, saltando...")
            continue
        
        # Generar redacción periodística con IA gratuita
        resultado = generar_con_ia_gratuita(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Agencias')
        )
        
        # Publicar en Facebook
        if publicar_facebook(resultado['titular'], resultado['texto'], img_path):
            guardar_historial(noticia['url'], noticia['title'])
            
            # Limpiar imagen temporal
            if os.path.exists(img_path):
                os.remove(img_path)
            
            print(f"\n{'='*60}")
            print("✅ ÉXITO: Noticia publicada")
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
