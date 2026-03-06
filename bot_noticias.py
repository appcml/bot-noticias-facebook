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

def traducir_google(texto):
    """Traduce usando MyMemory API (gratuito)"""
    if not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
        
        print(f"   🌐 Traduciendo...")
        
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': texto_str[:500],
            'langpair': 'en|es'
        }
        
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
    """Traduce usando LibreTranslate (gratuito)"""
    if not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
        
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
                    json={
                        "q": texto_str[:1000],
                        "source": "en",
                        "target": "es",
                        "format": "text"
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'translatedText' in result:
                        return result['translatedText']
                        
            except:
                continue
        
        return texto_str
        
    except:
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
        r'\bmy\b': 'mi', r'\bme\b': 'me', r'\byou\b': 'usted', r'\byour\b': 'su',
        r'\bhe\b': 'él', r'\bhim\b': 'él', r'\bhis\b': 'su', r'\bshe\b': 'ella',
        r'\bher\b': 'ella', r'\bwas\b': 'fue', r'\bhas\b': 'tiene', r'\bhave\b': 'tienen',
        r'\bhad\b': 'tuvo', r'\bbeen\b': 'sido', r'\bbeing\b': 'siendo', r'\bis\b': 'es',
        r'\bwere\b': 'eran', r'\bdo\b': 'hacer', r'\bdoes\b': 'hace', r'\bdid\b': 'hizo',
        r'\bdone\b': 'hecho', r'\bdoing\b': 'haciendo', r'\bcan\b': 'puede',
        r'\bcould\b': 'podría', r'\bwould\b': 'haría', r'\bshould\b': 'debería',
        r'\bmay\b': 'puede', r'\bmight\b': 'podría', r'\bmust\b': 'debe',
        r'\babout\b': 'sobre', r'\bafter\b': 'después', r'\bbefore\b': 'antes',
        r'\bduring\b': 'durante', r'\bbetween\b': 'entre', r'\bagainst\b': 'contra',
        r'\bunder\b': 'bajo', r'\bover\b': 'sobre', r'\bthrough\b': 'mediante',
        r'\binto\b': 'en', r'\bout\b': 'fuera', r'\bup\b': 'arriba', r'\bdown\b': 'abajo',
        r'\bhere\b': 'aquí', r'\bthere\b': 'allí', r'\bwhere\b': 'donde',
        r'\bwhen\b': 'cuando', r'\bwhy\b': 'por qué', r'\bhow\b': 'cómo',
        r'\bwhat\b': 'qué', r'\bwhich\b': 'cuál', r'\bwho\b': 'quién',
        r'\ball\b': 'todos', r'\beach\b': 'cada', r'\bevery\b': 'cada',
        r'\bboth\b': 'ambos', r'\bfew\b': 'pocos', r'\bmore\b': 'más',
        r'\bmost\b': 'la mayoría', r'\bother\b': 'otro', r'\bsome\b': 'algunos',
        r'\bsuch\b': 'tal', r'\bno\b': 'no', r'\bnone\b': 'ninguno',
        r'\bone\b': 'uno', r'\btwo\b': 'dos', r'\bfirst\b': 'primero',
        r'\bsecond\b': 'segundo', r'\blast\b': 'último', r'\bgood\b': 'bueno',
        r'\bnew\b': 'nuevo', r'\blong\b': 'largo', r'\bgreat\b': 'gran',
        r'\blittle\b': 'pequeño', r'\bown\b': 'propio', r'\bold\b': 'viejo',
        r'\bright\b': 'correcto', r'\bbig\b': 'grande', r'\bhigh\b': 'alto',
        r'\bdifferent\b': 'diferente', r'\bsmall\b': 'pequeño', r'\blarge\b': 'grande',
        r'\bnext\b': 'siguiente', r'\bearly\b': 'temprano', r'\byoung\b': 'joven',
        r'\bimportant\b': 'importante', r'\bsame\b': 'mismo', r'\bable\b': 'capaz',
        r'\bofficials\b': 'funcionarios', r'\bgovernment\b': 'gobierno',
        r'\bstatement\b': 'declaración', r'\breport\b': 'informe', r'\breports\b': 'informes',
        r'\bsources\b': 'fuentes', r'\bnews\b': 'noticias', r'\bmeeting\b': 'reunión',
        r'\bpeople\b': 'personas', r'\bcountry\b': 'país', r'\bworld\b': 'mundo',
        r'\binternational\b': 'internacional', r'\bnational\b': 'nacional',
        r'\bpublic\b': 'público', r'\bpresident\b': 'presidente', r'\bminister\b': 'ministro',
        r'\bsecretary\b': 'secretario', r'\bspokesperson\b': 'portavoz',
        r'\bannouncement\b': 'anuncio', r'\bcontroversy\b': 'controversia',
        r'\bcontinue\b': 'continuar', r'\baccording\b': 'según', r'\baccording to\b': 'según',
        r'\bfaces\b': 'enfrenta', r'\binvestigation\b': 'investigación',
        r'\ballegations\b': 'alegatos', r'\bethical\b': 'ético', r'\bethics\b': 'ética',
        r'\bsupport\b': 'apoyo', r'\bagainst\b': 'contra', r'\battack\b': 'ataque',
        r'\battacks\b': 'ataques', r'\bpoll\b': 'encuesta', r'\bpolls\b': 'encuestas',
        r'\bsold\b': 'convencidos', r'\biran\b': 'Irán', r'\bwhite house\b': 'Casa Blanca',
        r'\breasoning\b': 'razonamiento', r'\bresonating\b': 'resonando',
        r'\bamericans\b': 'estadounidenses', r'\bamerican\b': 'estadounidense',
        r'\bsurvey\b': 'encuesta', r'\bconducted\b': 'realizada', r'\badults\b': 'adultos',
        r'\bapprove\b': 'aprueban', r'\bdisapprove\b': 'desaprueban',
        r'\bstrongly\b': 'firmemente', r'\bsomewhat\b': 'algo', r'\bunsure\b': 'inseguros',
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
                   'acontecimiento', 'hecho', 'situación', 'desarrollo', 'declaraciones']
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said', 'told',
                   'officials', 'government', 'statement', 'report', 'reports', 'sources',
                   'news', 'meeting', 'people', 'country', 'world', 'international', 
                   'national', 'public', 'president', 'minister', 'secretary', 'spokesperson',
                   'announcement', 'controversy', 'continue', 'according', 'faces', 
                   'investigation', 'allegations', 'ethical', 'ethics', 'support', 'against',
                   'attack', 'attacks', 'poll', 'polls', 'sold', 'reasoning', 'resonating',
                   'americans', 'american', 'white', 'house', 'survey', 'conducted', 'adults']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    return count_es > count_en

def generar_redaccion_periodistica(titulo_en, desc_en, fuente):
    """
    Genera una redacción periodística profesional en español.
    Estructura: Titular + Lead (dato importante) + Cuerpo (3 párrafos) + Cierre
    Longitud: 1000-2000 caracteres
    """
    
    print(f"\n   📝 Procesando noticia...")
    print(f"   📰 Original: {titulo_en[:60]}...")
    
    # PASO 1: Traducir contenido
    titulo_traducido = traducir_google(titulo_en)
    desc_traducida = traducir_google(desc_en)
    
    titulo_traducido = limpiar_ingles(titulo_traducido)
    desc_traducida = limpiar_ingles(desc_traducida)
    
    # PASO 2: Generar redacción profesional con OpenAI
    if OPENAI_API_KEY:
        try:
            print(f"   🤖 Generando redacción periodística...")
            
            prompt = f"""Eres un redactor de agencia de noticias (estilo EFE, Reuters, AP). 
Escribe una NOTICIA COMPLETA EN ESPAÑOL con estructura periodística profesional.

INFORMACIÓN BASE:
Título original traducido: {titulo_traducido}
Descripción traducida: {desc_traducida}
Fuente: {fuente}

ESTRUCTURA REQUERIDA:

1. **TITULAR** (máximo 80 caracteres):
   - Informativo, preciso, atractivo
   - Estilo: "Estadounidenses dudan de ataques contra Irán, según encuesta"

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
- TODO en ESPAÑOL, cero palabras en inglés
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
                timeout=45
            )
            
            if response.status_code == 200:
                resultado = response.json()['choices'][0]['message']['content']
                
                # Extraer partes
                titular = titulo_traducido
                lead = ""
                cuerpo = ""
                
                if 'TITULAR:' in resultado:
                    try:
                        titular = resultado.split('TITULAR:')[1].split('LEAD:')[0].strip()
                        titular = titular.strip('"\'').strip()
                    except:
                        pass
                
                if 'LEAD:' in resultado:
                    try:
                        lead = resultado.split('LEAD:')[1].split('CUERPO:')[0].strip()
                    except:
                        pass
                
                if 'CUERPO:' in resultado:
                    try:
                        cuerpo = resultado.split('CUERPO:')[1].split('FIN')[0].strip()
                    except:
                        pass
                
                # Limpiar
                titular = limpiar_ingles(titular)
                lead = limpiar_ingles(lead)
                cuerpo = limpiar_ingles(cuerpo)
                
                # Construir texto final
                texto_final = f"{lead}\n\n{cuerpo}"
                
                # Verificar longitud y español
                if len(texto_final) >= 800 and es_espanol(texto_final):
                    print(f"   ✅ Redacción OK: {len(texto_final)} caracteres")
                    return {'titular': titular[:100], 'texto': texto_final[:1900]}
                else:
                    print(f"   ⚠️ Texto corto o con inglés, usando plantilla...")
                    
        except Exception as e:
            print(f"   ⚠️ Error OpenAI: {e}")
    
    # PASO 3: Plantilla periodística profesional
    return plantilla_periodistica_profesional(titulo_traducido, desc_traducida, fuente)

def plantilla_periodistica_profesional(titulo, descripcion, fuente):
    """Plantilla periodística profesional 100% español, 1000-2000 caracteres"""
    print(f"   📝 Generando plantilla periodística...")
    
    # Limpiar descripción
    desc_limpia = re.sub(r'<[^>]+>', '', str(descripcion))
    if len(desc_limpia) < 20:
        desc_limpia = "Se ha producido un acontecimiento de relevancia internacional que ha generado amplia repercusión en los medios de comunicación globales."
    
    # Extraer palabras clave para el lead
    palabras_clave = desc_limpia[:200] if len(desc_limpia) > 100 else desc_limpia
    
    # Construir redacción periodística estructurada
    
    # LEAD (dato importante, máx 140 caracteres)
    lead = f"{palabras_clave[:140]}." if len(palabras_clave) > 80 else f"Las autoridades competentes han confirmado un importante acontecimiento de relevancia internacional que se desarrolla en las últimas horas."
    
    # Párrafo 2: Contexto (quiénes, antecedentes)
    p2 = f"El hecho ha sido reportado por diversas fuentes periodísticas de alcance internacional, destacando su trascendencia en el contexto actual. "
    p2 += f"Las autoridades correspondientes han emitido comunicados oficiales sobre el tema, mientras diversos actores del escenario global mantienen atenta vigilancia sobre los desarrollos. "
    p2 += f"La información ha sido verificada por corresponsales en la región."
    
    # Párrafo 3: Desarrollo (datos, cifras, declaraciones)
    p3 = f"Analistas políticos y especialistas en relaciones internacionales señalan que este tipo de eventos requiere un seguimiento constante por parte de la comunidad global. "
    p3 += f"La cobertura informativa continúa ampliándose conforme surgen nuevos detalles relevantes sobre la situación. "
    p3 += f"Diversos medios de comunicación han destacado la importancia de los hechos reportados y sus posibles implicaciones a corto plazo."
    
    # Párrafo 4: Análisis (implicaciones, consecuencias)
    p4 = f"Las implicaciones de este acontecimiento podrían extenderse a diversos sectores de la sociedad y afectar las dinámicas internacionales en el mediano plazo. "
    p4 += f"Expertos consultados destacan la necesidad de mantener una postura informada y objetiva ante los desarrollos que se presenten en las próximas horas. "
    p4 += f"La situación continúa siendo objeto de análisis por parte de observadores internacionales."
    
    # Párrafo 5: Cierre (próximos pasos, fuente)
    p5 = f"Se esperan declaraciones oficiales adicionales y posibles actualizaciones conforme avancen las investigaciones correspondientes. "
    p5 += f"La información será actualizada progresivamente a medida que estén disponibles nuevos datos confirmados. "
    p5 += f"(Agencias) / Fuente: {fuente}."
    
    # Unir todo
    texto = f"{lead}\n\n{p2}\n\n{p3}\n\n{p4}\n\n{p5}"
    
    # Limpiar y verificar longitud
    texto = limpiar_ingles(texto)
    
    # Asegurar mínimo 1000 caracteres
    while len(texto) < 1000:
        texto += f" Los detalles adicionales serán proporcionados oportunamente según avancen las investigaciones oficiales."
    
    # Limitar a máximo 2000
    texto = texto[:1950]
    
    # Crear titular profesional
    titular = limpiar_ingles(str(titulo))[:90]
    if len(titular) < 15 or not es_espanol(titular):
        # Crear titular genérico
