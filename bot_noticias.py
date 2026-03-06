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
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"📚 Historial: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"⚠️ Error historial: {e}")

def guardar_historial(url, titulo):
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['ultima_publicacion'] = datetime.now().isoformat()
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Error guardando: {e}")

def get_url_id(url):
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:16]

def ya_publicada(url, titulo):
    url_id = get_url_id(url)
    if url_id in [get_url_id(u) for u in historial['urls']]:
        return True
    return False

def limpiar_texto(texto):
    """Limpia el texto de URLs y HTML"""
    if not texto:
        return ""
    texto = re.sub(r'http[s]?://\S+', '', texto)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def generar_articulo_periodistico(titulo, descripcion, fuente):
    """
    Genera un artículo periodístico con formato profesional.
    Estructura: Titular + Lead + 3 párrafos + Cierre
    Longitud: 500-1500 caracteres
    """
    
    print(f"\n   📝 Procesando: {titulo[:50]}...")
    
    # Limpiar entrada
    titulo_limpio = limpiar_texto(titulo)
    desc_limpia = limpiar_texto(descripcion)
    
    # Extraer información clave
    info = extraer_datos_clave(titulo_limpio, desc_limpia)
    
    # Generar con IA o manual
    if OPENROUTER_API_KEY:
        resultado = generar_con_ia_formato(titulo_limpio, desc_limpia, fuente, info)
        if resultado:
            return resultado
    
    return generar_manual_formato(titulo_limpio, desc_limpia, fuente, info)

def extraer_datos_clave(titulo, descripcion):
    """Extrae quién, qué, cuándo, dónde"""
    texto = f"{titulo} {descripcion}"
    
    # Detectar sujeto (organización/persona)
    sujetos = []
    palabras = texto.split()
    for i, palabra in enumerate(palabras):
        if palabra[0].isupper() and len(palabra) > 3:
            if i > 0 and palabras[i-1][0].isupper():
                sujetos.append(f"{palabras[i-1]} {palabra}")
            else:
                sujetos.append(palabra)
    
    actor = sujetos[0] if sujetos else "Las autoridades"
    
    # Detectar acción
    acciones = ['anuncian', 'confirman', 'reportan', 'acuerdan', 'destacan', 
                'indican', 'revelan', 'advierten', 'denuncian', 'anuncia', 
                'confirma', 'reporta', 'acuerda']
    accion = next((a for a in acciones if a in texto.lower()), "informan")
    
    # Detectar tema
    temas_clave = ['acuerdo', 'crisis', 'conflicto', 'reforma', 'inversión',
                   'elecciones', 'sanciones', 'tratado', 'investigación']
    tema = next((t for t in temas_clave if t in texto.lower()), "desarrollo importante")
    
    return {'actor': actor, 'accion': accion, 'tema': tema}

def generar_con_ia_formato(titulo, descripcion, fuente, info):
    """Genera artículo con IA con formato específico"""
    try:
        prompt = f"""Eres un redactor de agencia EFE. Escribe un ARTÍCULO PERIODÍSTICO en español.

DATOS:
Actor: {info['actor']}
Acción: {info['accion']}
Tema: {info['tema']}
Fuente: {fuente}

ESTRUCTURA OBLIGATORIA (5 bloques separados por líneas en blanco):

┌─ TITULAR (máx 80 caracteres, informativo)

┌─ LEAD (2-3 oraciones, máx 140 caracteres, el dato más importante)

┌─ PÁRRAFO 1 (2-3 oraciones, contexto/antecedentes)

┌─ PÁRRAFO 2 (2-3 oraciones, datos específicos/reacciones)

┌─ PÁRRAFO 3 (2-3 oraciones, análisis/implicaciones)

┌─ CIERRE (1 oración, fuente)

REGLAS ESTRICTAS:
- Cada bloque debe ser UN PÁRRAFO separado
- Usa doble salto de línea entre párrafos
- Cada oración termina en PUNTO
- Longitud total: 500-1500 caracteres
- Sin repeticiones de frases
- Lenguaje periodístico neutro

FORMATO DE SALIDA:
TITULAR: [titular]

LEAD: [lead]

P1: [párrafo 1]

P2: [párrafo 2]

P3: [párrafo 3]

CIERRE: [cierre]

FIN"""

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
                'temperature': 0.2,
                'max_tokens': 1200
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
                
                # Extraer secciones
                titular = extraer_bloque(content, 'TITULAR:', 'LEAD:')
                lead = extraer_bloque(content, 'LEAD:', 'P1:')
                p1 = extraer_bloque(content, 'P1:', 'P2:')
                p2 = extraer_bloque(content, 'P2:', 'P3:')
                p3 = extraer_bloque(content, 'P3:', 'CIERRE:')
                cierre = extraer_bloque(content, 'CIERRE:', 'FIN')
                
                # Limpiar
                titular = limpiar_bloque(titular) or titulo[:80]
                lead = limpiar_bloque(lead)
                p1 = limpiar_bloque(p1)
                p2 = limpiar_bloque(p2)
                p3 = limpiar_bloque(p3)
                cierre = limpiar_bloque(cierre) or f"Fuente: {fuente}."
                
                # Construir con saltos de línea dobles
                partes = [p for p in [lead, p1, p2, p3, cierre] if p and len(p) > 20]
                
                if len(partes) >= 4:
                    texto_final = '\n\n'.join(partes)
                    
                    if 500 <= len(texto_final) <= 1500:
                        print(f"   ✅ IA: {len(texto_final)} caracteres, {len(partes)} párrafos")
                        return {'titular': titular[:100], 'texto': texto_final}
                        
    except Exception as e:
        print(f"   ⚠️ Error IA: {e}")
    
    return None

def extraer_bloque(texto, inicio, fin):
    """Extrae un bloque de texto entre marcadores"""
    try:
        if inicio in texto:
            parte = texto.split(inicio)[1]
            if fin in parte:
                return parte.split(fin)[0].strip()
            return parte.strip()[:400]
    except:
        pass
    return ""

def limpiar_bloque(texto):
    """Limpia un bloque de texto"""
    if not texto:
        return ""
    # Eliminar prefijos como "P1:", "P2:", etc.
    texto = re.sub(r'^(P\d+|TITULAR|LEAD|CIERRE):\s*', '', texto, flags=re.IGNORECASE)
    texto = texto.strip()
    # Asegurar punto final
    if texto and not texto.endswith(('.', '!', '?')):
        texto += "."
    return texto

def generar_manual_formato(titulo, descripcion, fuente, info):
    """Genera artículo manual con formato profesional"""
    print(f"   📝 Generando formato manual...")
    
    # TITULAR
    titular = titulo[:80] if len(titulo) > 20 else f"{info['actor']} {info['accion']} {info['tema']}"
    
    # LEAD (2-3 oraciones)
    oraciones = [s.strip() for s in descripcion.split('.') if len(s.strip()) > 15]
    if len(oraciones) >= 2:
        lead = f"{oraciones[0]}. {oraciones[1]}."
    elif oraciones:
        lead = f"{oraciones[0]}. Las autoridades confirmaron la información oficialmente."
    else:
        lead = f"{info['actor']} {info['accion']} un importante {info['tema']}. El hecho fue confirmado por fuentes oficiales en las últimas horas."
    
    # Limitar lead
    if len(lead) > 140:
        lead = lead[:137].rsplit(' ', 1)[0] + "."
    
    # Párrafos de desarrollo (2-3 oraciones cada uno)
    p1 = f"El acontecimiento se produce en un contexto de desarrollos recientes en la materia. Las partes involucradas habían mostrado posiciones previas sobre este tema específico."
    
    p2 = f"Los detalles específicos del {info['tema']} se conocerán en los próximos días. Los involucrados preparan los pasos siguientes según lo establecido en el comunicado oficial."
    
    p3 = f"Los observadores destacan la trascendencia de este acontecimiento en el contexto actual. Las consecuencias a mediano plazo dependerán de los desarrollos siguientes."
    
    # CIERRE
    cierre = f"Las autoridades competentes continuarán informando sobre los avances. Fuente: {fuente}."
    
    # Ajustar longitud si es necesario
    partes = [lead, p1, p2, p3, cierre]
    texto = '\n\n'.join(partes)
    
    # Si es muy corto, expandir
    while len(texto) < 500:
        p_extra = f"Los expertos consultados destacan la relevancia de este {info['tema']} en el escenario actual."
        partes.insert(3, p_extra)
        texto = '\n\n'.join(partes)
        if len(texto) >= 500:
            break
    
    # Si es muy largo, recortar inteligentemente
    if len(texto) > 1500:
        texto_cortado = texto[:1497]
        ultimo_punto = texto_cortado.rfind('.')
        if ultimo_punto > 1000:
            texto = texto_cortado[:ultimo_punto+1] + f"\n\n{cierre}"
        else:
            texto = texto[:1500]
    
    print(f"   ✅ Manual: {len(texto)} caracteres")
    return {'titular': titular[:100], 'texto': texto}

def buscar_noticias():
    """Busca noticias de fuentes variadas"""
    print("\n🔍 Buscando noticias...")
    noticias = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'language': 'en', 'pageSize': 15, 'apiKey': NEWS_API_KEY},
                timeout=15
            )
            data = resp.json()
            if data.get('status') == 'ok':
                noticias.extend(data.get('articles', []))
                print(f"   📡 NewsAPI: {len(data.get('articles', []))}")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # GNews
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            resp = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'en', 'max': 15, 'apikey': GNEWS_API_KEY},
                timeout=15
            )
            data = resp.json()
            if 'articles' in data:
                for a in data['articles']:
                    noticias.append({
                        'title': a.get('title'),
                        'description': a.get('description'),
                        'url': a.get('url'),
                        'urlToImage': a.get('image'),
                        'source': {'name': a.get('source', {}).get('name', 'GNews')}
                    })
                print(f"   📡 GNews: {len(data['articles'])}")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # RSS
    rss_feeds = [
        'http://feeds.bbci.co.uk/news/world/rss.xml',
        'https://www.reuters.com/rssFeed/worldNews'
    ]
    
    for feed_url in random.sample(rss_feeds, min(2, len(rss_feeds))):
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
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
                    'source': {'name': feed.feed.get('title', 'RSS')}
                })
            print(f"   📡 RSS: {feed_url.split('/')[2]}")
        except:
            pass
    
    print(f"\n📊 Total: {len(noticias)}")
    
    # Filtrar
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title']:
            continue
        if ya_publicada(art['url'], art['title']):
            continue
        nuevas.append(art)
        print(f"   ✅ {art['title'][:50]}...")
    
    print(f"📊 Nuevas: {len(nuevas)}")
    return nuevas[:3]

def descargar_imagen(url):
    if not url or not str(url).startswith('http'):
        return None
    try:
        print(f"   🖼️ Descargando imagen...")
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            path = f'/tmp/noticia_{hashlib.md5(str(url).encode()).hexdigest()[:8]}.jpg'
            img.save(path, 'JPEG', quality=85)
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar(titulo, texto, img_path):
    """Publica en Facebook con formato limpio"""
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    # Limpiar
    titulo = limpiar_texto(titulo)
    
    # Preservar saltos de línea dobles en el texto
    # Facebook respeta \n\n como separación de párrafos
    
    mensaje = f"""📰 {titulo}

{texto}

#Noticias #Actualidad

— Verdad Hoy: Noticias al minuto"""
    
    # Preview visual con separación de párrafos
    print(f"\n   📝 VISTA PREVIA ({len(mensaje)} caracteres):")
    print(f"   {'═'*50}")
    
    lineas = mensaje.split('\n')
    for linea in lineas[:15]:
        if linea.strip() == '':
            print(f"   ☐ (espacio entre párrafos)")
        else:
            preview = linea[:60] + "..." if len(linea) > 60 else linea
            print(f"   {preview}")
    
    print(f"   {'═'*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"   📤 Publicando...")
        
        with open(img_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = resp.json()
            
            if resp.status_code == 200 and 'id' in result:
                print(f"   ✅ PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Error: {error}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales de Facebook")
        return False
    
    noticias = buscar_noticias()
    
    if not noticias:
        print("⚠️ No hay noticias nuevas")
        return False
    
    print(f"\n🎯 Procesando {len(noticias)} noticia(s)")
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*60}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
            continue
        
        resultado = generar_articulo_periodistico(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Agencias')
        )
        
        if publicar(resultado['titular'], resultado['texto'], img_path):
            guardar_historial(noticia['url'], noticia['title'])
            if os.path.exists(img_path):
                os.remove(img_path)
            print(f"\n{'='*60}")
            print("✅ ÉXITO")
            print(f"{'='*60}")
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    print("\n❌ No se pudo publicar")
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
