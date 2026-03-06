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
print("🚀 BOT DE NOTICIAS - Verdad Hoy (ESPAÑOL)")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"📚 Historial cargado: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"⚠️ Error cargando historial: {e}")

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
    urls_existentes = [get_url_id(u) for u in historial['urls']]
    if url_id in urls_existentes:
        return True
    
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencia / max(len(titulo_simple), len(t_simple)) > 0.7:
                return True
    return False

def generar_con_ia(titulo, descripcion, fuente):
    """Genera redacción usando OpenRouter (IA gratuita)"""
    
    if not OPENROUTER_API_KEY:
        return plantilla_periodistica(titulo, descripcion, fuente)
    
    try:
        prompt = f"""Eres un redactor de agencia EFE. Escribe una NOTICIA en ESPAÑOL.

Título: {titulo}
Descripción: {descripcion}
Fuente: {fuente}

ESTRUCTURA:
TITULAR: (máx 80 chars, estilo periodístico)
LEAD: (primera línea, máx 140 chars, lo más importante)
CUERPO: (3 párrafos: contexto, desarrollo, análisis)
CIERRE: (1 línea, próximos pasos + fuente)

REGLAS:
- ESPAÑOL nativo, no traducción
- 1000-1800 caracteres totales
- Estilo: Agencia EFE/Reuters/AP
- Termina con: (Agencias) / Fuente: {fuente}

FORMATO:
TITULAR: [titular]
LEAD: [lead]
CUERPO: [cuerpo]
FIN"""

        modelos = [
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "qwen/qwen-2-7b-instruct:free"
        ]
        
        for modelo in modelos:
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                        'HTTP-Referer': 'https://github.com',
                        'X-Title': 'Bot Noticias',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': modelo,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3,
                        'max_tokens': 1200
                    },
                    timeout=45
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data:
                        content = data['choices'][0]['message']['content']
                        
                        # Extraer partes
                        titular = titulo[:90]
                        lead = ""
                        cuerpo = ""
                        
                        if 'TITULAR:' in content:
                            titular = content.split('TITULAR:')[1].split('LEAD:')[0].strip()[:90]
                        if 'LEAD:' in content:
                            lead = content.split('LEAD:')[1].split('CUERPO:')[0].strip()
                        if 'CUERPO:' in content:
                            cuerpo = content.split('CUERPO:')[1].split('FIN')[0].strip()
                        
                        texto_final = f"{lead}\n\n{cuerpo}".strip()
                        
                        if len(texto_final) > 500:
                            return {'titular': titular, 'texto': texto_final[:1900]}
                            
            except Exception as e:
                print(f"⚠️ Error con {modelo}: {e}")
                continue
                
    except Exception as e:
        print(f"⚠️ Error IA: {e}")
    
    return plantilla_periodistica(titulo, descripcion, fuente)

def plantilla_periodistica(titulo, descripcion, fuente):
    """Plantilla profesional en español"""
    desc = re.sub(r'<[^>]+>', '', str(descripcion))
    if len(desc) < 20:
        desc = "Las autoridades confirmaron un importante acontecimiento de relevancia nacional."
    
    lead = desc[:140] if len(desc) > 100 else "Se reporta un hecho de importancia nacional en desarrollo."
    
    p2 = "El acontecimiento ha sido confirmado por fuentes oficiales y genera atención mediática. "
    p2 += "Las autoridades competentes emitieron comunicados sobre el tema. "
    p2 += "Diversos sectores mantienen vigilancia sobre los desarrollos."
    
    p3 = "Analistas señalan la trascendencia de los hechos reportados. "
    p3 += "La cobertura informativa continúa ampliándose conforme surgen nuevos detalles. "
    p3 += "Medios de comunicación destacan la relevancia del caso."
    
    p4 = "Las implicaciones podrían extenderse a diversos ámbitos de la sociedad. "
    p4 += "Expertos consultados destacan la necesidad de seguimiento. "
    p4 += "La situación continúa siendo objeto de análisis."
    
    p5 = f"Se esperan actualizaciones oficiales. (Agencias) / Fuente: {fuente}."
    
    texto = f"{lead}\n\n{p2}\n\n{p3}\n\n{p4}\n\n{p5}"
    
    while len(texto) < 1000:
        texto += " Los detalles serán proporcionados oportunamente."
    
    return {'titular': titulo[:90], 'texto': texto[:1950]}

def buscar_noticias():
    """Busca noticias en español"""
    print("\n🔍 Buscando noticias en ESPAÑOL...")
    noticias = []
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'language': 'es', 'pageSize': 15, 'apiKey': NEWS_API_KEY},
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
                params={'lang': 'es', 'max': 15, 'apikey': GNEWS_API_KEY},
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
    
    # RSS Español
    if len(noticias) < 3:
        feeds = [
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
            'https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml',
            'https://www.clarin.com/rss/lo-ultimo/',
            'https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml',
        ]
        
        for feed_url in random.sample(feeds, min(2, len(feeds))):
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:4]:
                    img = ''
                    if hasattr(entry, 'media_content') and entry.media_content:
                        img = entry.media_content[0].get('url', '')
                    elif 'summary' in entry:
                        m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png))"', entry.summary, re.I)
                        if m:
                            img = m.group(1)
                    
                    noticias.append({
                        'title': entry.get('title'),
                        'description': entry.get('summary', '')[:400],
                        'url': entry.get('link'),
                        'urlToImage': img,
                        'source': {'name': feed.feed.get('title', 'Medios')}
                    })
                print(f"   📡 RSS: {feed_url.split('/')[2]}")
            except:
                pass
    
    # Filtrar
    nuevas = []
    for art in noticias:
        if not art.get('title') or len(art['title']) < 10:
            continue
        if "[Removed]" in art['title'] or ya_publicada(art['url'], art['title']):
            continue
        
        nuevas.append(art)
        print(f"   ✅ Nueva: {art['title'][:50]}...")
    
    print(f"📊 Total nuevas: {len(nuevas)}")
    return nuevas[:2]

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
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    mensaje = f"""📰 {titulo}

{texto}

#Noticias #Actualidad #Español #Hoy

— Verdad Hoy"""
    
    print(f"\n📝 Publicando ({len(mensaje)} chars)...")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(img_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = resp.json()
            
            if resp.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO: {result['id']}")
                return True
            else:
                print(f"❌ Error: {result.get('error', {}).get('message', result)}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def main():
    noticias = buscar_noticias()
    
    if not noticias:
        print("⚠️ No hay noticias nuevas")
        return False
    
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"📰 NOTICIA {i}/{len(noticias)}")
        print(f"{'='*50}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            continue
        
        resultado = generar_con_ia(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Agencias')
        )
        
        if publicar(resultado['titular'], resultado['texto'], img_path):
            guardar_historial(noticia['url'], noticia['title'])
            if os.path.exists(img_path):
                os.remove(img_path)
            return True
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
