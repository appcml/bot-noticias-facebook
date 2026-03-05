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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')  # ✅ CORREGIDO: era B_ACCESS_TOKEN

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# Verificar configuración crítica
print("\n📋 Verificación de configuración:")
if not FB_PAGE_ID:
    print("❌ ERROR: FB_PAGE_ID no configurado")
else:
    print(f"✅ FB_PAGE_ID: {FB_PAGE_ID[:10]}...")
if not FB_ACCESS_TOKEN:
    print("❌ ERROR: FB_ACCESS_TOKEN no configurado")
else:
    print(f"✅ FB_ACCESS_TOKEN: {FB_ACCESS_TOKEN[:20]}...")
if not DEEPL_API_KEY:
    print("⚠️ DEEPL_API_KEY no configurado")
else:
    print("✅ DEEPL_API_KEY configurado")

HISTORIAL_FILE = 'historial_publicaciones.json'

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"\n📚 Historial cargado: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"\n⚠️ Error cargando historial: {e}")

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
        print(f"❌ Error guardando historial: {e}")

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

def traducir_deepl(texto):
    """Traduce texto a español usando DeepL"""
    if not DEEPL_API_KEY or not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
            
        print(f"   🌐 Traduciendo con DeepL...")
        
        url = "https://api-free.deepl.com/v2/translate"
        
        if len(texto_str) > 1500:
            partes = []
            for i in range(0, len(texto_str), 1400):
                parte = texto_str[i:i+1400]
                response = requests.post(
                    url,
                    data={
                        'auth_key': DEEPL_API_KEY,
                        'text': parte,
                        'source_lang': 'EN',
                        'target_lang': 'ES'
                    },
                    timeout=20
                )
                if response.status_code == 200:
                    result = response.json()
                    partes.append(result['translations'][0]['text'])
                else:
                    partes.append(parte)
            return ' '.join(partes)
        else:
            response = requests.post(
                url,
                data={
                    'auth_key': DEEPL_API_KEY,
                    'text': texto_str,
                    'source_lang': 'EN',
                    'target_lang': 'ES'
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['translations'][0]['text']
            else:
                print(f"   ⚠️ DeepL error {response.status_code}")
                return texto_str
                
    except Exception as e:
        print(f"   ⚠️ Error DeepL: {e}")
        return texto

def limpiar_ingles(texto):
    """Elimina palabras en inglés comunes"""
    if not texto:
        return texto
    
    reemplazos = {
        r'\bthe\b': '', r'\band\b': 'y', r'\bfor\b': 'para', r'\bare\b': 'son',
        r'\bnot\b': 'no', r'\bbut\b': 'pero', r'\bwith\b': 'con', r'\bthat\b': 'que',
        r'\bthis\b': 'este', r'\bwill\b': '', r'\bsaid\b': 'dijo', r'\btold\b': 'dijo',
        r'\bon\b': 'en', r'\bat\b': 'en', r'\bby\b': 'por', r'\bfrom\b': 'desde',
        r'\bto\b': 'a', r'\bin\b': 'en', r'\bof\b': 'de', r'\bas\b': 'como',
        r'\bit\b': 'eso', r'\btheir\b': 'su', r'\bthem\b': 'ellos', r'\bthey\b': 'ellos',
        r'\bwe\b': 'nosotros', r'\bour\b': 'nuestro', r'\bus\b': 'nos', r'\bI\b': 'yo',
        r'\bmy\b': 'mi', r'\bme\b': 'me', r'\byou\b': 'tú', r'\byour\b': 'tu',
        r'\bhe\b': 'él', r'\bhim\b': 'él', r'\bhis\b': 'su', r'\bshe\b': 'ella',
        r'\bher\b': 'ella', r'\bwas\b': 'fue', r'\bhas\b': 'tiene', r'\bhave\b': 'tienen',
        r'\bhad\b': 'tuvo', r'\bbeen\b': 'sido', r'\bbeing\b': 'siendo', r'\bis\b': 'es',
        r'\bare\b': 'son', r'\bwas\b': 'era', r'\bwere\b': 'eran', r'\bdo\b': 'hacer',
        r'\bdoes\b': 'hace', r'\bdid\b': 'hizo', r'\bdone\b': 'hecho', r'\bdoing\b': 'haciendo',
        r'\bcan\b': 'poder', r'\bcould\b': 'podría', r'\bwould\b': 'haría', r'\bshould\b': 'debería',
        r'\bmay\b': 'puede', r'\bmight\b': 'podría', r'\bmust\b': 'debe', r'\bshall\b': 'deberá',
        r'\babout\b': 'sobre', r'\bafter\b': 'después', r'\bbefore\b': 'antes', r'\bduring\b': 'durante',
        r'\bbetween\b': 'entre', r'\bagainst\b': 'contra', r'\bunder\b': 'bajo', r'\bover\b': 'sobre',
        r'\bthrough\b': 'a través', r'\binto\b': 'en', r'\bout\b': 'fuera', r'\bup\b': 'arriba',
        r'\bdown\b': 'abajo', r'\boff\b': 'apagado', r'\bhere\b': 'aquí', r'\bthere\b': 'allí',
        r'\bwhere\b': 'donde', r'\bwhen\b': 'cuando', r'\bwhy\b': 'por qué', r'\bhow\b': 'cómo',
        r'\bwhat\b': 'qué', r'\bwhich\b': 'cuál', r'\bwho\b': 'quién', r'\bwhom\b': 'a quién',
        r'\bwhose\b': 'cuyo', r'\ball\b': 'todo', r'\beach\b': 'cada', r'\bevery\b': 'cada',
        r'\bboth\b': 'ambos', r'\bfew\b': 'pocos', r'\bmore\b': 'más', r'\bmost\b': 'la mayoría',
        r'\bother\b': 'otro', r'\bsome\b': 'algunos', r'\bsuch\b': 'tal', r'\bno\b': 'no',
        r'\bnone\b': 'ninguno', r'\bone\b': 'uno', r'\btwo\b': 'dos', r'\bthree\b': 'tres',
        r'\bfour\b': 'cuatro', r'\bfive\b': 'cinco', r'\bfirst\b': 'primero', r'\bsecond\b': 'segundo',
        r'\bthird\b': 'tercero', r'\blast\b': 'último', r'\bgood\b': 'bueno', r'\bnew\b': 'nuevo',
        r'\bfirst\b': 'primero', r'\blong\b': 'largo', r'\bgreat\b': 'gran', r'\blittle\b': 'pequeño',
        r'\bown\b': 'propio', r'\bother\b': 'otro', r'\bold\b': 'viejo', r'\bright\b': 'correcto',
        r'\bbig\b': 'grande', r'\bhigh\b': 'alto', r'\bdifferent\b': 'diferente', r'\bsmall\b': 'pequeño',
        r'\blarge\b': 'grande', r'\bnext\b': 'siguiente', r'\bearly\b': 'temprano', r'\byoung\b': 'joven',
        r'\bimportant\b': 'importante', r'\bfew\b': 'pocos', r'\bpublic\b': 'público', r'\bbad\b': 'malo',
        r'\bsame\b': 'mismo', r'\bable\b': 'capaz', r'\bofficials\b': 'oficiales', r'\bgovernment\b': 'gobierno',
        r'\bstatement\b': 'declaración', r'\breport\b': 'reporte', r'\breports\b': 'reportes',
        r'\bsources\b': 'fuentes', r'\bnews\b': 'noticias', r'\bmeeting\b': 'reunión', r'\bpeople\b': 'personas',
        r'\bcountry\b': 'país', r'\bworld\b': 'mundo', r'\binternational\b': 'internacional',
        r'\bnational\b': 'nacional', r'\bpublic\b': 'público', r'\bpresident\b': 'presidente',
        r'\bminister\b': 'ministro', r'\bsecretary\b': 'secretario', r'\bspokesperson\b': 'portavoz',
        r'\bannouncement\b': 'anuncio', r'\bcontroversy\b': 'controversia', r'\bcontinue\b': 'continuar',
        r'\baccording\b': 'según', r'\baccording to\b': 'según', r'\bfaces\b': 'enfrenta',
        r'\binvestigation\b': 'investigación', r'\ballegations\b': 'alegatos', r'\bethical\b': 'ético',
        r'\bethics\b': 'ética',
    }
    
    texto_limpio = texto
    for ingles, espanol in reemplazos.items():
        texto_limpio = re.sub(ingles, espanol, texto_limpio, flags=re.IGNORECASE)
    
    # Limpiar espacios dobles y puntuación extraña
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    texto_limpio = re.sub(r'\s+([.,;:!?])', r'\1', texto_limpio)
    
    return texto_limpio

def es_espanol(texto):
    """Detecta si el texto está en español"""
    if not texto:
        return False
    
    texto_lower = texto.lower()
    palabras_es = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'por', 'con', 
                   'su', 'para', 'los', 'las', 'del', 'al', 'lo', 'más', 'este', 'esta',
                   'pero', 'sus', 'una', 'como', 'son', 'entre', 'sobre', 'también', 'han',
                   'sido', 'porque', 'durante', 'contra', 'según', 'hacia', 'desde', 'dos',
                   'fue', 'será', 'cada', 'mismo', 'misma', 'otro', 'otra', 'gran', 'nuevo',
                   'nueva', 'primer', 'primera', 'tras', 'puede', 'parte', 'años', 'año',
                   'hace', 'hoy', 'país', 'mundo', 'gobierno', 'estado', 'nacional', 'internacional']
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said', 'told',
                   'officials', 'government', 'statement', 'report', 'reports', 'sources',
                   'news', 'meeting', 'people', 'country', 'world', 'international', 'national',
                   'public', 'president', 'minister', 'secretary', 'spokesperson', 'announcement',
                   'controversy', 'continue', 'according', 'faces', 'investigation', 'allegations',
                   'ethical', 'ethics']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    return count_es > count_en

def generar_noticia_espanol(titulo_en, desc_en, fuente):
    """Genera noticia completamente en español"""
    
    print(f"\n   📝 Procesando: {titulo_en[:50]}...")
    
    # Traducir
    titulo_es = traducir_deepl(titulo_en)
    desc_es = traducir_deepl(desc_en)
    
    # Limpiar
    titulo_es = limpiar_ingles(titulo_es)
    desc_es = limpiar_ingles(desc_es)
    
    # Si OpenAI disponible, mejorar redacción
    if OPENAI_API_KEY:
        try:
            print(f"   🤖 Mejorando con OpenAI...")
            
            prompt = f"""Escribe una NOTICIA PROFESIONAL EN ESPAÑOL.

DATOS:
Título: {titulo_es}
Descripción: {desc_es}
Fuente: {fuente}

REGLAS:
1. SOLO ESPAÑOL, cero inglés
2. TITULAR: Máx 80 caracteres, llamativo
3. TEXTO: 4 párrafos cortos (lead, contexto, desarrollo, cierre)
4. Incluye: "Fuente: {fuente}"
5. Longitud: 800-1200 caracteres

FORMATO:
TITULAR: [titular]

TEXTO:
[párrafos]

FIN"""

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 900
                },
                timeout=40
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                
                # Extraer
                titular = titulo_es
                texto = desc_es
                
                if 'TITULAR:' in resultado:
                    try:
                        titular = resultado.split('TITULAR:')[1].split('TEXTO:')[0].strip()
                        titular = titular.strip('"\'').strip()
                    except:
                        pass
                
                if 'TEXTO:' in resultado:
                    try:
                        texto = resultado.split('TEXTO:')[1].split('FIN')[0].strip()
                    except:
                        pass
                
                # Limpiar y verificar
                titular = limpiar_ingles(titular)
                texto = limpiar_ingles(texto)
                
                if es_espanol(texto):
                    print(f"   ✅ OpenAI OK ({len(texto)} chars)")
                    return {'titular': titular[:100], 'texto': texto[:1400]}
                else:
                    print(f"   ⚠️ OpenAI dejó inglés, usando plantilla")
                    
        except Exception as e:
            print(f"   ⚠️ OpenAI error: {e}")
    
    # Plantilla garantizada
    return plantilla_espanol(titulo_es, desc_es, fuente)

def plantilla_espanol(titulo, descripcion, fuente):
    """Plantilla 100% español"""
    print(f"   📝 Plantilla español...")
    
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion))
    if len(desc_limpia) < 20:
        desc_limpia = "Acontecimiento de relevancia internacional reportado en medios globales."
    
    p1 = f"{desc_limpia[:200]}. Este hecho ha generado atención significativa en la comunidad internacional."
    p2 = f"Las autoridades competentes han confirmado la información a través de canales oficiales. La cobertura mediática continúa ampliándose."
    p3 = f"Analistas señalan la importancia de este evento en el contexto global actual. Se esperan desarrollos adicionales en las próximas horas."
    p4 = f"La información será actualizada progresivamente. Fuente: {fuente}."
    
    texto = f"{p1}\n\n{p2}\n\n{p3}\n\n{p4}"
    texto = limpiar_ingles(texto)
    
    titular = limpiar_ingles(str(titulo))[:100]
    if len(titular) < 10:
        titular = "Nuevo acontecimiento internacional"
    
    print(f"   ✅ Plantilla ({len(texto)} chars)")
    return {'titular': titular, 'texto': texto[:1400]}

def buscar_noticias():
    print("\n🔍 Buscando noticias...")
    
    noticias = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'language': 'en', 'pageSize': 20, 'apiKey': NEWS_API_KEY},
                timeout=15
            )
            data = response.json()
            if data.get('status') == 'ok':
                noticias.extend(data.get('articles', []))
                print(f"   📡 NewsAPI: {len(data.get('articles', []))}")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # GNews
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            response = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'en', 'max': 20, 'apikey': GNEWS_API_KEY},
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
                print(f"   📡 GNews: {len(data['articles'])}")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # RSS
    if len(noticias) < 3:
        rss_feeds = [
            'http://feeds.bbci.co.uk/news/world/rss.xml',
            'https://www.reuters.com/rssFeed/worldNews',
            'https://rss.cnn.com/rss/edition_world.rss'
        ]
        for feed_url in random.sample(rss_feeds, min(2, len(rss_feeds))):
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
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
        if not art.get('url'):
            continue
        
        if ya_publicada(art['url'], art['title']):
            continue
        
        nuevas.append(art)
        print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Nuevas: {len(nuevas)}")
    return nuevas[:3]

def descargar_imagen(url):
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
            print(f"   ✅ Imagen OK")
            return path
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
    return None

def publicar(titulo, texto, img_path):
    """Publica en Facebook"""
    
    print(f"\n   🔍 Verificación final...")
    
    # Limpiar
    titulo = limpiar_ingles(titulo)
    texto = limpiar_ingles(texto)
    
    # Verificar español
    if not es_espanol(titulo):
        print(f"   ⚠️ Corrigiendo titular...")
        titulo = "Nuevo acontecimiento internacional"
    
    if not es_espanol(texto):
        print(f"   ⚠️ Corrigiendo texto...")
        texto = "Se reporta un importante acontecimiento de relevancia internacional. Las autoridades competentes han confirmado la información. Se esperan actualizaciones adicionales."
    
    # Hashtags
    hashtags = "#Noticias #Actualidad #Internacional #Hoy #Mundo"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    # Limpieza final
    mensaje = limpiar_ingles(mensaje)
    
    print(f"\n   📝 MENSAJE ({len(mensaje)} chars):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:6]:
        preview = linea[:60] + "..." if len(linea) > 60 else linea
        print(f"   {preview}")
    print(f"   {'='*50}")
    
    # Verificación final
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said', 'told']
    encontradas = [p for p in palabras_en if f' {p} ' in f' {mensaje.lower()} ']
    if encontradas:
        print(f"   🧹 Limpiando: {encontradas}")
        for palabra in encontradas:
            mensaje = re.sub(rf'\b{palabra}\b', '', mensaje, flags=re.IGNORECASE)
        mensaje = re.sub(r'\s+', ' ', mensaje).strip()
        print(f"   ✅ Limpieza aplicada")
    
    # Publicar
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"   📤 Publicando...")
        
        with open(img_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"   ✅ PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Facebook error: {error}")
                if '100' in str(error) or 'does not resolve' in str(error):
                    print(f"   💡 Verifica que FB_PAGE_ID esté correcto")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    # Verificar configuración
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("\n❌ ERROR: Faltan credenciales de Facebook")
        print(f"   FB_PAGE_ID: {'OK' if FB_PAGE_ID else 'FALTA'}")
        print(f"   FB_ACCESS_TOKEN: {'OK' if FB_ACCESS_TOKEN else 'FALTA'}")
        return False
    
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n⚠️ No hay noticias nuevas")
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
        
        resultado = generar_noticia_espanol(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales')
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
