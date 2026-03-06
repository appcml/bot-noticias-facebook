import requests
import random
import re
import hashlib
import os
import json
import feedparser
import subprocess
from datetime import datetime
from PIL import Image
from io import BytesIO
import tempfile
import shutil

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
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
if OPENAI_API_KEY:
    print("✅ OPENAI_API_KEY configurado")
else:
    print("⚠️ OPENAI_API_KEY no configurado")

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None, 'videos': []}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"\n📚 Historial: {len(historial['urls'])} noticias, {len(historial.get('videos', []))} videos")
    except Exception as e:
        print(f"\n⚠️ Error historial: {e}")

def guardar_historial(url, titulo, es_video=False):
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['ultima_publicacion'] = datetime.now().isoformat()
    if es_video:
        historial['videos'].append(url)
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    historial['videos'] = historial.get('videos', [])[-100:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Historial guardado")
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

def traducir_google(texto):
    """Traduce usando servicios gratuitos"""
    if not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
        
        print(f"   🌐 Traduciendo...")
        
        # MyMemory API
        url = "https://api.mymemory.translated.net/get"
        params = {'q': texto_str[:500], 'langpair': 'en|es'}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'responseData' in data and 'translatedText' in data['responseData']:
                traduccion = data['responseData']['translatedText']
                if traduccion.lower() != texto_str.lower():
                    return traduccion
        
        return traducir_libretranslate(texto_str)
        
    except Exception as e:
        return traducir_libretranslate(texto)

def traducir_libretranslate(texto):
    """LibreTranslate como respaldo"""
    if not texto:
        return texto
    
    servidores = [
        "https://libretranslate.de/translate",
        "https://translate.argosopentech.com/translate",
        "https://libretranslate.pussthecat.org/translate"
    ]
    
    for servidor in servidores:
        try:
            response = requests.post(
                servidor,
                headers={"Content-Type": "application/json"},
                json={"q": texto[:1000], "source": "en", "target": "es", "format": "text"},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'translatedText' in result:
                    return result['translatedText']
        except:
            continue
    
    return texto

def limpiar_ingles(texto):
    """Elimina palabras en inglés"""
    if not texto:
        return texto
    
    # Diccionario de reemplazos - CORREGIDO con comas en todas las líneas
    reemplazos = {
        r'\bthe\b': '',
        r'\band\b': 'y',
        r'\bfor\b': 'para',
        r'\bare\b': 'son',
        r'\bnot\b': 'no',
        r'\bbut\b': 'pero',
        r'\bwith\b': 'con',
        r'\bthat\b': 'que',
        r'\bthis\b': 'este',
        r'\bwill\b': '',
        r'\bsaid\b': 'dijo',
        r'\btold\b': 'dijo',
        r'\bon\b': 'en',
        r'\bat\b': 'en',
        r'\bby\b': 'por',
        r'\bfrom\b': 'desde',
        r'\bto\b': 'a',
        r'\bin\b': 'en',
        r'\bof\b': 'de',
        r'\bas\b': 'como',
        r'\bit\b': 'eso',
        r'\btheir\b': 'su',
        r'\bthem\b': 'ellos',
        r'\bthey\b': 'ellos',
        r'\bwe\b': 'nosotros',
        r'\bour\b': 'nuestro',
        r'\bus\b': 'nos',
        r'\bI\b': 'yo',
        r'\bmy\b': 'mi',
        r'\bme\b': 'me',
        r'\byou\b': 'tú',
        r'\byour\b': 'tu',
        r'\bhe\b': 'él',
        r'\bhim\b': 'él',
        r'\bhis\b': 'su',
        r'\bshe\b': 'ella',
        r'\bher\b': 'ella',
        r'\bwas\b': 'fue',
        r'\bhas\b': 'tiene',
        r'\bhave\b': 'tienen',
        r'\bhad\b': 'tuvo',
        r'\bbeen\b': 'sido',
        r'\bbeing\b': 'siendo',
        r'\bis\b': 'es',
        r'\bwere\b': 'eran',
        r'\bdo\b': 'hacer',
        r'\bdoes\b': 'hace',
        r'\bdid\b': 'hizo',
        r'\bdone\b': 'hecho',
        r'\bdoing\b': 'haciendo',
        r'\bcan\b': 'poder',
        r'\bcould\b': 'podría',
        r'\bwould\b': 'haría',
        r'\bshould\b': 'debería',
        r'\bmay\b': 'puede',
        r'\bmight\b': 'podría',
        r'\bmust\b': 'debe',
        r'\babout\b': 'sobre',
        r'\bafter\b': 'después',
        r'\bbefore\b': 'antes',
        r'\bduring\b': 'durante',
        r'\bbetween\b': 'entre',
        r'\bagainst\b': 'contra',
        r'\bunder\b': 'bajo',
        r'\bover\b': 'sobre',
        r'\bthrough\b': 'a través',
        r'\binto\b': 'en',
        r'\bout\b': 'fuera',
        r'\bup\b': 'arriba',
        r'\bdown\b': 'abajo',
        r'\bhere\b': 'aquí',
        r'\bthere\b': 'allí',
        r'\bwhere\b': 'donde',
        r'\bwhen\b': 'cuando',
        r'\bwhy\b': 'por qué',
        r'\bhow\b': 'cómo',
        r'\bwhat\b': 'qué',
        r'\bwhich\b': 'cuál',
        r'\bwho\b': 'quién',
        r'\ball\b': 'todo',
        r'\beach\b': 'cada',
        r'\bevery\b': 'cada',
        r'\bboth\b': 'ambos',
        r'\bfew\b': 'pocos',
        r'\bmore\b': 'más',
        r'\bmost\b': 'la mayoría',
        r'\bother\b': 'otro',
        r'\bsome\b': 'algunos',
        r'\bsuch\b': 'tal',
        r'\bno\b': 'no',
        r'\bnone\b': 'ninguno',
        r'\bone\b': 'uno',
        r'\btwo\b': 'dos',
        r'\bthree\b': 'tres',
        r'\bfour\b': 'cuatro',
        r'\bfive\b': 'cinco',
        r'\bfirst\b': 'primero',
        r'\bsecond\b': 'segundo',
        r'\bthird\b': 'tercero',
        r'\blast\b': 'último',
        r'\bgood\b': 'bueno',
        r'\bnew\b': 'nuevo',
        r'\blong\b': 'largo',
        r'\bgreat\b': 'gran',
        r'\blittle\b': 'pequeño',
        r'\bown\b': 'propio',
        r'\bold\b': 'viejo',
        r'\bright\b': 'correcto',
        r'\bbig\b': 'grande',
        r'\bhigh\b': 'alto',
        r'\bdifferent\b': 'diferente',
        r'\bsmall\b': 'pequeño',
        r'\blarge\b': 'grande',
        r'\bnext\b': 'siguiente',
        r'\bearly\b': 'temprano',
        r'\byoung\b': 'joven',
        r'\bimportant\b': 'importante',
        r'\bsame\b': 'mismo',
        r'\bable\b': 'capaz',
        r'\bofficials\b': 'oficiales',
        r'\bgovernment\b': 'gobierno',
        r'\bstatement\b': 'declaración',
        r'\breport\b': 'reporte',
        r'\breports\b': 'reportes',
        r'\bsources\b': 'fuentes',
        r'\bnews\b': 'noticias',
        r'\bmeeting\b': 'reunión',
        r'\bpeople\b': 'personas',
        r'\bcountry\b': 'país',
        r'\bworld\b': 'mundo',
        r'\binternational\b': 'internacional',
        r'\bnational\b': 'nacional',
        r'\bpublic\b': 'público',
        r'\bpresident\b': 'presidente',
        r'\bminister\b': 'ministro',
        r'\bsecretary\b': 'secretario',
        r'\bspokesperson\b': 'portavoz',
        r'\bannouncement\b': 'anuncio',
        r'\bcontroversy\b': 'controversia',
        r'\bcontinue\b': 'continuar',
        r'\baccording\b': 'según',
        r'\baccording to\b': 'según',
        r'\bfaces\b': 'enfrenta',
        r'\binvestigation\b': 'investigación',
        r'\ballegations\b': 'alegatos',
        r'\bethical\b': 'ético',
        r'\bethics\b': 'ética',
        r'\bsupport\b': 'apoyo',
        r'\bagainst\b': 'contra',
        r'\battack\b': 'ataque',
        r'\battacks\b': 'ataques',
        r'\bpoll\b': 'encuesta',
        r'\bpolls\b': 'encuestas',
        r'\bsold\b': 'vendido',
        r'\biran\b': 'Irán',
        r'\bwhite house\b': 'Casa Blanca',
        r'\breasoning\b': 'razonamiento',
        r'\bresonating\b': 'resonando',
        r'\bamericans\b': 'estadounidenses',
        r'\bamerican\b': 'estadounidense',
        r'\bsurvey\b': 'encuesta',
        r'\badults\b': 'adultos',
        r'\bconducted\b': 'realizada',
        r'\bapprove\b': 'aprueban',
        r'\bdisapprove\b': 'desaprueban',
        r'\bsomewhat\b': 'algo',
        r'\bstrongly\b': 'fuertemente',
        r'\bsure\b': 'seguro',
        r'\bdon\'t\b': 'no',
        r'\baren't\b': 'no están',
        r'\bisn't\b': 'no está',
        r'\bwon't\b': 'no',
        r'\bcan't\b': 'no pueden',
        r'\bdidn't\b': 'no',
        r'\bwasn't\b': 'no era',
        r'\bweren't\b': 'no eran',
        r'\bhaven't\b': 'no han',
        r'\bhasn't\b': 'no ha',
        r'\bhadn't\b': 'no había',
        r'\bwouldn't\b': 'no',
        r'\bshouldn't\b': 'no deberían',
        r'\bcouldn't\b': 'no podían',
        r'\bmightn't\b': 'no podrían',
        r'\bmustn't\b': 'no deben',
    }
    
    texto_limpio = texto
    for ingles, espanol in reemplazos.items():
        texto_limpio = re.sub(ingles, espanol, texto_limpio, flags=re.IGNORECASE)
    
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
                   'hace', 'hoy', 'país', 'mundo', 'gobierno', 'estado', 'nacional', 
                   'internacional', 'relevancia', 'información', 'autoridades', 'importante',
                   'encuestas', 'estadounidenses', 'casa', 'blanca', 'razonamiento',
                   'resonando', 'contra', 'ataques', 'irán']
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said', 'told',
                   'officials', 'government', 'statement', 'report', 'reports', 'sources',
                   'news', 'meeting', 'people', 'country', 'world', 'international', 
                   'national', 'public', 'president', 'minister', 'secretary', 'spokesperson',
                   'announcement', 'controversy', 'continue', 'according', 'faces', 
                   'investigation', 'allegations', 'ethical', 'ethics', 'support', 'against',
                   'attack', 'attacks', 'poll', 'polls', 'sold', 'reasoning', 'resonating',
                   'americans', 'american', 'white', 'house', 'survey', 'adults', 'conducted',
                   'approve', 'disapprove', 'somewhat', 'strongly', 'sure']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    return count_es > count_en

def generar_redaccion_periodistica(titulo_en, desc_en, fuente, min_chars=1000, max_chars=2000):
    """
    Genera redacción periodística profesional con:
    - Lead informativo (dato importante al inicio)
    - Lenguaje periodístico neutral
    - 1000-2000 caracteres
    - Estructura: Lead, Contexto, Desarrollo, Reacciones, Cierre
    """
    
    print(f"\n   📝 Generando redacción periodística...")
    print(f"   📰 Original: {titulo_en[:60]}...")
    
    # Traducir
    titulo_es = traducir_google(titulo_en)
    desc_es = traducir_google(desc_en)
    titulo_es = limpiar_ingles(titulo_es)
    desc_es = limpiar_ingles(desc_es)
    
    if OPENAI_API_KEY:
        try:
            print(f"   🤖 OpenAI generando texto periodístico...")
            
            prompt = f"""Eres un redactor de noticias profesional con 20 años de experiencia.
Escribe una NOTICIA COMPLETA EN ESPAÑOL con estructura periodística formal.

DATOS DE LA NOTICIA:
Título original traducido: {titulo_es}
Descripción: {desc_es}
Fuente: {fuente}

ESTRUCTURA OBLIGATORIA (lenguaje periodístico neutral, informativo):

1. **LEAD** (párrafo 1): Comienza con el dato MÁS IMPORTANTE. Quién, qué, cuándo, dónde. Máximo 3 líneas. Informativo, no opinativo.

2. **CONTEXTO** (párrafo 2): Antecedentes relevantes. Por qué es importante este hecho. Máximo 4 líneas.

3. **DESARROLLO** (párrafo 3): Detalles específicos, cifras si las hay, hechos concretos. Máximo 4 líneas.

4. **REACCIONES** (párrafo 4): Qué dicen las partes involucradas, autoridades o expertos. Máximo 3 líneas.

5. **CIERRE** (párrafo 5): Implicaciones futuras o próximos pasos. Termina con "Fuente: {fuente}". Máximo 3 líneas.

REGLAS ESTRICTAS:
- TODO en ESPAÑOL, cero palabras en inglés
- Longitud TOTAL: {min_chars}-{max_chars} caracteres (incluye espacios)
- Estilo: Periodismo objetivo, informativo, neutral
- NO uses adjetivos valorativos (increíble, terrible, maravilloso)
- SÍ usa datos, cifras, hechos verificables
- TITULAR: Máximo 80 caracteres, estilo titular de periódico

FORMATO:
TITULAR: [titular conciso y preciso]

TEXTO:
[lead informativo]

[contexto]

[desarrollo con datos]

[reacciones]

[cierre con fuente]

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
                    'temperature': 0.2,
                    'max_tokens': 1200
                },
                timeout=50
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                
                # Extraer titular
                titular = titulo_es
                if 'TITULAR:' in resultado:
                    try:
                        titular = resultado.split('TITULAR:')[1].split('TEXTO:')[0].strip()
                        titular = titular.strip('"\'').strip()
                    except:
                        pass
                
                # Extraer texto
                texto = desc_es
                if 'TEXTO:' in resultado:
                    try:
                        texto = resultado.split('TEXTO:')[1].split('FIN')[0].strip()
                    except:
                        pass
                
                # Limpiar
                titular = limpiar_ingles(titular)
                texto = limpiar_ingles(texto)
                
                # Verificar longitud
                if len(texto) < min_chars:
                    print(f"   ⚠️ Texto muy corto ({len(texto)} chars), expandiendo...")
                    texto = expandir_texto(texto, fuente, min_chars)
                
                if len(texto) > max_chars:
                    texto = texto[:max_chars].rsplit('.', 1)[0] + '.'
                
                # Verificar español
                if es_espanol(texto) and len(texto) >= min_chars:
                    print(f"   ✅ Redacción OK: {len(texto)} caracteres")
                    return {'titular': titular[:100], 'texto': texto}
                else:
                    print(f"   ⚠️ No cumple requisitos, usando plantilla...")
                    
        except Exception as e:
            print(f"   ⚠️ Error OpenAI: {e}")
    
    # Plantilla periodística profesional
    return plantilla_periodistica(titulo_es, desc_es, fuente, min_chars, max_chars)

def expandir_texto(texto, fuente, min_chars):
    """Expande texto si es muy corto"""
    while len(texto) < min_chars:
        adicional = f" Las autoridades competentes continúan evaluando la situación y se esperan nuevos comunicados oficiales en las próximas horas. La cobertura informativa se mantendrá actualizada conforme se desarrollen los hechos. Fuente: {fuente}."
        texto += adicional
    return texto[:min_chars + 200]

def plantilla_periodistica(titulo, descripcion, fuente, min_chars=1000, max_chars=2000):
    """Plantilla periodística profesional garantizada"""
    print(f"   📝 Usando plantilla periodística...")
    
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion))
    if len(desc_limpia) < 30:
        desc_limpia = "Acontecimiento de relevancia internacional reportado por medios globales."
    
    # Lead informativo (dato importante primero)
    p1 = f"{desc_limpia[:300]}. Este hecho fue confirmado por fuentes oficiales en las últimas horas y ha generado atención significativa en el ámbito internacional."
    
    # Contexto
    p2 = f"El acontecimiento se enmarca dentro de una serie de eventos que han marcado la agenda global en los últimos días. Las autoridades competentes han iniciado los protocolos correspondientes para dar seguimiento a la situación. La información disponible hasta el momento indica que se trata de un desarrollo de trascendencia para los actores involucrados."
    
    # Desarrollo
    p3 = f"Según los datos proporcionados por {fuente}, el evento ha sido objeto de análisis por parte de especialistas y observadores internacionales. Las cifras preliminares sugieren un impacto significativo en el corto plazo. Los detalles específicos continúan siendo verificados por las fuentes correspondientes."
    
    # Reacciones
    p4 = f"Diversos portavoces oficiales han emitido declaraciones al respecto, destacando la importancia de mantener la calma y seguir las recomendaciones establecidas. La comunidad internacional mantiene atenta vigilancia sobre los próximos pasos a seguir."
    
    # Cierre
    p5 = f"Se espera que en las próximas horas se proporcionen actualizaciones adicionales conforme avancen las investigaciones correspondientes. La cobertura informativa continuará ampliándose. Fuente: {fuente}."
    
    texto = f"{p1}\n\n{p2}\n\n{p3}\n\n{p4}\n\n{p5}"
    texto = limpiar_ingles(texto)
    
    # Ajustar longitud
    if len(texto) < min_chars:
        texto = expandir_texto(texto, fuente, min_chars)
    if len(texto) > max_chars:
        texto = texto[:max_chars].rsplit('.', 1)[0] + '.'
    
    titular = limpiar_ingles(str(titulo))[:100]
    if len(titular) < 10:
        titular = "Nuevo acontecimiento internacional de trascendencia global"
    
    print(f"   ✅ Plantilla: {len(texto)} caracteres")
    return {'titular': titular, 'texto': texto}

def generar_redaccion_video(titulo_es, desc_es, fuente):
    """
    Redacción corta para videos (200-400 caracteres)
    """
    print(f"   🎬 Generando redacción para video...")
    
    # Lead directo
    texto = f"{desc_es[:200]} Este material audiovisual fue difundido por {fuente} y muestra hechos de relevancia informativa. Fuente: {fuente}."
    
    texto = limpiar_ingles(texto)
    
    # Ajustar a 200-400 caracteres
    if len(texto) < 200:
        texto += f" La información continúa en desarrollo."
    if len(texto) > 400:
        texto = texto[:400].rsplit('.', 1)[0] + '.'
    
    titular = limpiar_ingles(str(titulo_es))[:100]
    
    print(f"   ✅ Video: {len(texto)} caracteres")
    return {'titular': titular, 'texto': texto}

def buscar_noticias_imagen():
    """Busca noticias con imágenes"""
    print("\n🔍 Buscando noticias con imágenes...")
    
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
                noticias.extend([a for a in data.get('articles', []) if a.get('urlToImage')])
                print(f"   📡 NewsAPI: {len(noticias)} con imágenes")
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
                    if a.get('image'):
                        noticias.append({
                            'title': a.get('title'),
                            'description': a.get('description'),
                            'url': a.get('url'),
                            'urlToImage': a.get('image'),
                            'source': {'name': a.get('source', {}).get('name', 'GNews')},
                            'tipo': 'imagen'
                        })
                print(f"   📡 GNews: {len([n for n in noticias if n.get('tipo') == 'imagen'])} con imágenes")
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
                    
                    if img:
                        noticias.append({
                            'title': entry.get('title'),
                            'description': entry.get('summary', entry.get('description', ''))[:400],
                            'url': entry.get('link'),
                            'urlToImage': img,
                            'source': {'name': feed.feed.get('title', 'RSS')},
                            'tipo': 'imagen'
                        })
                print(f"   📡 RSS: {feed_url.split('/')[2]}")
            except:
                pass
    
    return noticias

def buscar_noticias_video():
    """
    Busca noticias con videos en español
    Fuentes: YouTube noticias, RTVE, El País video, etc.
    """
    print("\n🔍 Buscando noticias con videos en español...")
    
    videos = []
    
    # Buscar en RSS de medios hispanos que incluyen videos
    rss_videos_es = [
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/videos/portada',
        'https://www.rtve.es/noticias/rss/',
        'https://feeds.bbci.co.uk/mundo/rss.xml',
    ]
    
    for feed_url in rss_videos_es:
        try:
            print(f"   📡 Revisando: {feed_url.split('/')[2]}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:10]:
                # Buscar videos en el contenido
                video_url = None
                contenido = str(entry.get('summary', '')) + str(entry.get('description', ''))
                
                # Buscar URLs de video
                patrones_video = [
                    r'(https?://[^"\s]+\.(?:mp4|webm|ogg))',
                    r'src="(https?://[^"]+\.(?:mp4|webm|ogg))"',
                    r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)',
                    r'(https?://youtu\.be/[\w-]+)',
                    r'<video[^>]+src="(https?://[^"]+)"',
                    r'"url"\s*:\s*"(https?://[^"]+\.mp4)"',
                ]
                
                for patron in patrones_video:
                    match = re.search(patron, contenido, re.I)
                    if match:
                        video_url = match.group(1)
                        break
                
                # También buscar en media_content
                if not video_url and hasattr(entry, 'media_content'):
                    for media in entry.media_content:
                        if media.get('type', '').startswith('video/'):
                            video_url = media.get('url')
                            break
                
                if video_url and not ya_publicada(entry.get('link'), entry.get('title')):
                    videos.append({
                        'title': entry.get('title'),
                        'description': entry.get('summary', entry.get('description', ''))[:300],
                        'url': entry.get('link'),
                        'video_url': video_url,
                        'source': {'name': feed.feed.get('title', 'Video')},
                        'tipo': 'video'
                    })
                    print(f"   ✅ Video encontrado: {entry.get('title')[:50]}...")
                    
        except Exception as e:
            print(f"   ⚠️ Error RSS video: {e}")
    
    print(f"📊 Videos encontrados: {len(videos)}")
    return videos[:2]

def descargar_imagen(url):
    """Descarga imagen de noticia"""
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

def descargar_video(url):
    """
    Descarga video usando yt-dlp (debe estar instalado)
    """
    print(f"   📥 Descargando video...")
    
    try:
        # Crear archivo temporal
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, 'video.%(ext)s')
        
        # Intentar descargar con yt-dlp
        cmd = [
            'yt-dlp',
            '--no-playlist',
            '--format', 'mp4[height<=720]/mp4/best[height<=720]/best',
            '--output', output_path,
            '--max-filesize', '50M',
            '--no-warnings',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # Buscar el archivo descargado
            archivos = os.listdir(temp_dir)
            for archivo in archivos:
                if archivo.endswith(('.mp4', '.webm', '.mkv')):
                    video_path = os.path.join(temp_dir, archivo)
                    size_mb = os.path.getsize(video_path) / (1024 * 1024)
                    print(f"   ✅ Video descargado: {size_mb:.1f} MB")
                    return video_path
        else:
            print(f"   ⚠️ yt-dlp error: {result.stderr[:200]}")
            
    except subprocess.TimeoutExpired:
        print(f"   ⚠️ Timeout descargando video")
    except Exception as e:
        print(f"   ⚠️ Error descargando: {e}")
    
    return None

def publicar_imagen(titulo, texto, img_path):
    """Publica noticia con imagen en Facebook"""
    
    print(f"\n   📰 Publicando noticia con imagen...")
    
    # Verificaciones
    titulo = limpiar_ingles(titulo)
    texto = limpiar_ingles(texto)
    
    if not es_espanol(titulo):
        titulo = "Nuevo acontecimiento internacional"
    if not es_espanol(texto):
        texto = "Se reporta importante acontecimiento internacional. Las autoridades competentes han confirmado la información."
    
    # Verificar longitud
    if len(texto) < 1000:
        texto += f" La cobertura informativa se mantendrá actualizada conforme se desarrollen los hechos. Se esperan nuevas declaraciones oficiales en las próximas horas."
    if len(texto) > 2000:
        texto = texto[:2000].rsplit('.', 1)[0] + '.'
    
    hashtags = "#Noticias #Actualidad #Internacional #Hoy #Mundo #Periodismo"
    
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    mensaje = limpiar_ingles(mensaje)
    
    print(f"\n   📝 MENSAJE ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:8]:
        preview = linea[:60] + "..." if len(linea) > 60 else linea
        print(f"   {preview}")
    print(f"   {'='*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(img_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            )
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"   ✅ IMAGEN PUBLICADA: {result['id']}")
                return True
            else:
                print(f"   ❌ Error: {result.get('error', {}).get('message', result)}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def publicar_video(titulo, texto, video_path):
    """Publica noticia con video en Facebook"""
    
    print(f"\n   🎬 Publicando noticia con video...")
    
    # Verificaciones
    titulo = limpiar_ingles(titulo)
    texto = limpiar_ingles(texto)
    
    if not es_espanol(titulo):
        titulo = "Video: Acontecimiento internacional"
    if not es_espanol(texto):
        texto = "Material audiovisual de relevancia internacional."
    
    # Ajustar longitud para video (200-400)
    if len(texto) < 200:
        texto += " Información en desarrollo."
    if len(texto) > 400:
        texto = texto[:400].rsplit('.', 1)[0] + '.'
    
    hashtags = "#VideoNoticias #Actualidad #Internacional #Hoy #Mundo"
    
    mensaje = f"""🎬 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    mensaje = limpiar_ingles(mensaje)
    
    print(f"\n   📝 MENSAJE VIDEO ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    print(f"   {mensaje[:150]}...")
    print(f"   {'='*50}")
    
    try:
        # Subir video a Facebook
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
        
        file_size = os.path.getsize(video_path)
        print(f"   📤 Subiendo video ({file_size/(1024*1024):.1f} MB)...")
        
        with open(video_path, 'rb') as f:
            response = requests.post(
                url,
                files={'file': f},
                data={
                    'description': mensaje,
                    'access_token': FB_ACCESS_TOKEN
                },
                timeout=300
            )
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"   ✅ VIDEO PUBLICADO: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Error video: {error}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("\n❌ ERROR: Faltan credenciales de Facebook")
        return False
    
    # Estrategia: 70% imágenes, 30% videos
    tipo_contenido = random.choices(['imagen', 'video'], weights=[70, 30])[0]
    
    if tipo_contenido == 'video':
        print("\n🎲 Modo seleccionado: VIDEO")
        videos = buscar_noticias_video()
        
        if videos:
            for i, video in enumerate(videos, 1):
                print(f"\n{'='*60}")
                print(f"🎬 VIDEO {i}/{len(videos)}")
                print(f"{'='*60}")
                
                # Generar redacción corta
                resultado = generar_redaccion_video(
                    video['title'],
                    video.get('description', ''),
                    video.get('source', {}).get('name', 'Medios')
                )
                
                # Descargar video
                video_path = descargar_video(video['video_url'])
                
                if video_path:
                    if publicar_video(resultado['titular'], resultado['texto'], video_path):
                        guardar_historial(video['url'], video['title'], es_video=True)
                        # Limpiar
                        try:
                            shutil.rmtree(os.path.dirname(video_path))
                        except:
                            pass
                        print(f"\n{'='*60}")
                        print("✅ VIDEO PUBLICADO")
                        print(f"{'='*60}")
                        return True
                    
                    # Limpiar si falló
                    try:
                        shutil.rmtree(os.path.dirname(video_path))
                    except:
                        pass
                else:
                    print("   ⏭️ No se pudo descargar el video")
        
        print("\n⚠️ No se encontraron videos, cambiando a modo imagen...")
    
    # Modo imagen
    print("\n🖼️ Modo: IMAGEN")
    noticias = buscar_noticias_imagen()
    
    # Filtrar nuevas
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
    
    print(f"📊 Noticias nuevas con imagen: {len(nuevas)}")
    
    if not nuevas:
        print("\n⚠️ No hay noticias nuevas")
        return False
    
    for i, noticia in enumerate(nuevas[:3], 1):
        print(f"\n{'='*60}")
        print(f"📰 NOTICIA {i}/{min(len(nuevas), 3)}")
        print(f"{'='*60}")
        
        img_path = descargar_imagen(noticia.get('urlToImage'))
        if not img_path:
            print("   ⏭️ Sin imagen")
            continue
        
        # Generar redacción periodística profesional
        resultado = generar_redaccion_periodistica(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Medios Internacionales'),
            min_chars=1000,
            max_chars=2000
        )
        
        if publicar_imagen(resultado['titular'], resultado['texto'], img_path):
            guardar_historial(noticia['url'], noticia['title'])
            if os.path.exists(img_path):
                os.remove(img_path)
            print(f"\n{'='*60}")
            print("✅ NOTICIA PUBLICADA")
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
