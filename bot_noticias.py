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

HISTORIAL_FILE = 'historial_publicaciones.json'

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

# def traducir_google(texto):
    """
    Traduce usando Google Translate (gratuito, sin API key)
    Usa el endpoint libre de Google Translate
    """
    if not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
        
        print(f"   🌐 Traduciendo con Google...")
        
        # Método 1: Usando MyMemory API (gratuito, 1000 palabras/día)
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': texto_str[:500],  # Límite gratuito
            'langpair': 'en|es'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'responseData' in data and 'translatedText' in data['responseData']:
                traduccion = data['responseData']['translatedText']
                # Verificar que no sea el mismo texto (a veces falla)
                if traduccion.lower() != texto_str.lower():
                    print(f"   ✅ MyMemory: {traduccion[:60]}...")
                    return traduccion
        
        # Método 2: Si falla, usar LibreTranslate
        return traducir_libretranslate(texto_str)
        
    except Exception as e:
        print(f"   ⚠️ Error MyMemory: {e}")
        return traducir_libretranslate(texto)

# def traducir_libretranslate(texto):
    """
    Traduce usando LibreTranslate (gratuito, sin API key)
    """
    if not texto:
        return texto
    
    try:
        texto_str = str(texto).strip()
        if len(texto_str) < 3:
            return texto_str
        
        print(f"   🌐 Intentando LibreTranslate...")
        
        # Lista de instancias públicas gratuitas
        servidores = [
            "https://libretranslate.de/translate",
            "https://translate.argosopentech.com/translate",
            "https://libretranslate.pussthecat.org/translate",
            "https://translate.terraprint.co/translate"
        ]
        
        for servidor in servidores:
            try:
                response = requests.post(
                    servidor,
                    headers={"Content-Type": "application/json"},
                    json={
                        "q": texto_str[:1000],  # Límite por solicitud
                        "source": "en",
                        "target": "es",
                        "format": "text"
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'translatedText' in result:
                        traduccion = result['translatedText']
                        print(f"   ✅ LibreTranslate: {traduccion[:60]}...")
                        return traduccion
                        
            except Exception as e:
                continue  # Intentar siguiente servidor
        
        print(f"   ⚠️ Todos los servidores fallaron")
        return texto_str
        
    except Exception as e:
        print(f"   ⚠️ Error LibreTranslate: {e}")
        return texto

# def traducir_con_openai(texto):
    """Traducción de respaldo usando OpenAI"""
    if not OPENAI_API_KEY or not texto:
        return texto
    
    try:
        print(f"   🌐 Traduciendo con OpenAI...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': 'Eres un traductor profesional de inglés a español. Traduce el texto manteniendo el sentido y estilo periodístico.'},
                    {'role': 'user', 'content': f'Traduce este texto al español:\n\n{texto}\n\nTraducción:'}
                ],
                'temperature': 0.3,
                'max_tokens': 1000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            traduccion = response.json()['choices'][0]['message']['content'].strip()
            print(f"   ✅ OpenAI: {traduccion[:60]}...")
            return traduccion
            
    except Exception as e:
        print(f"   ⚠️ Error OpenAI traducción: {e}")
    
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
        r'\bwere\b': 'eran', r'\bdo\b': 'hacer', r'\bdoes\b': 'hace', r'\bdid\b': 'hizo',
        r'\bdone\b': 'hecho', r'\bdoing\b': 'haciendo', r'\bcan\b': 'poder',
        r'\bcould\b': 'podría', r'\bwould\b': 'haría', r'\bshould\b': 'debería',
        r'\bmay\b': 'puede', r'\bmight\b': 'podría', r'\bmust\b': 'debe',
        r'\babout\b': 'sobre', r'\bafter\b': 'después', r'\bbefore\b': 'antes',
        r'\bduring\b': 'durante', r'\bbetween\b': 'entre', r'\bagainst\b': 'contra',
        r'\bunder\b': 'bajo', r'\bover\b': 'sobre', r'\bthrough\b': 'a través',
        r'\binto\b': 'en', r'\bout\b': 'fuera', r'\bup\b': 'arriba', r'\bdown\b': 'abajo',
        r'\bhere\b': 'aquí', r'\bthere\b': 'allí', r'\bwhere\b': 'donde',
        r'\bwhen\b': 'cuando', r'\bwhy\b': 'por qué', r'\bhow\b': 'cómo',
        r'\bwhat\b': 'qué', r'\bwhich\b': 'cuál', r'\bwho\b': 'quién',
        r'\ball\b': 'todo', r'\beach\b': 'cada', r'\bevery\b': 'cada',
        r'\bboth\b': 'ambos', r'\bfew\b': 'pocos', r'\bmore\b': 'más',
        r'\bmost\b': 'la mayoría', r'\bother\b': 'otro', r'\bsome\b': 'algunos',
        r'\bsuch\b': 'tal', r'\bno\b': 'no', r'\bnone\b': 'ninguno',
        r'\bone\b': 'uno', r'\btwo\b': 'dos', r'\bthree\b': 'tres',
        r'\bfour\b': 'cuatro', r'\bfive\b': 'cinco', r'\bfirst\b': 'primero',
        r'\bsecond\b': 'segundo', r'\bthird\b': 'tercero', r'\blast\b': 'último',
        r'\bgood\b': 'bueno', r'\bnew\b': 'nuevo', r'\blong\b': 'largo',
        r'\bgreat\b': 'gran', r'\blittle\b': 'pequeño', r'\bown\b': 'propio',
        r'\bold\b': 'viejo', r'\bright\b': 'correcto', r'\bbig\b': 'grande',
        r'\bhigh\b': 'alto', r'\bdifferent\b': 'diferente', r'\bsmall\b': 'pequeño',
        r'\blarge\b': 'grande', r'\bnext\b': 'siguiente', r'\bearly\b': 'temprano',
        r'\byoung\b': 'joven', r'\bimportant\b': 'importante', r'\bsame\b': 'mismo',
        r'\bable\b': 'capaz', r'\bofficials\b': 'oficiales', r'\bgovernment\b': 'gobierno',
        r'\bstatement\b': 'declaración', r'\breport\b': 'reporte', r'\breports\b': 'reportes',
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
        r'\bsold\b': 'vendido', r'\biran\b': 'Irán', r'\bwhite house\b': 'Casa Blanca',
        r'\breasoning\b': 'razonamiento', r'\bresonating\b': 'resonando',
        r'\bamericans\b': 'estadounidenses', r'\bamerican\b': 'estadounidense',
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
                   'internacional', 'relevancia', 'información', 'autoridades', 'importante']
    palabras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'said', 'told',
                   'officials', 'government', 'statement', 'report', 'reports', 'sources',
                   'news', 'meeting', 'people', 'country', 'world', 'international', 
                   'national', 'public', 'president', 'minister', 'secretary', 'spokesperson',
                   'announcement', 'controversy', 'continue', 'according', 'faces', 
                   'investigation', 'allegations', 'ethical', 'ethics', 'support', 'against',
                   'attack', 'attacks', 'poll', 'polls', 'sold', 'reasoning', 'resonating',
                   'americans', 'american', 'white house']
    
    count_es = sum(1 for p in palabras_es if f' {p} ' in f' {texto_lower} ')
    count_en = sum(1 for p in palabras_en if f' {p} ' in f' {texto_lower} ')
    
    return count_es > count_en

def generar_noticia_espanol(titulo_es, desc_es, fuente):
    """Genera noticia en español usando traductores gratuitos"""
    
    print(f"\n   📝 Procesando: {titulo_es[:50]}...")
    
    # PASO 3: Generar redacción profesional con OpenAI si está disponible
    if OPENAI_API_KEY:
        try:
            print(f"   🤖 Generando redacción con OpenAI...")
            
            prompt = f"""Eres un periodista experto. Escribe una NOTICIA COMPLETA EN ESPAÑOL.

DATOS TRADUCIDOS:
Título: {titulo_es}
Descripción: {desc_es}
Fuente original: {fuente}

INSTRUCCIONES ESTRICTAS:
1. Escribe TODO en ESPAÑOL. CERO palabras en inglés.
2. Crea un TITULAR nuevo y atractivo (máx 80 caracteres)
3. Escribe 4 párrafos cortos:
   - P1: El hecho principal (2-3 líneas)
   - P2: Contexto y antecedentes (3 líneas)
   - P3: Reacciones y análisis (3 líneas)
   - P4: Consecuencias y cierre con "Fuente: {fuente}"
4. Estilo: Periodismo objetivo, claro y profesional
5. Longitud: 1000-2000 caracteres totales

FORMATO:
TITULAR: [titular en español]

TEXTO:
[párrafo 1]

[párrafo 2]

[párrafo 3]

[párrafo 4]

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
                   max_tokens
	                }:
	                    1500imeout=40
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

                
                if len(texto) >= 1000:
                    print(f"   ✅ OpenAI OK ({len(texto)} chars)")
                    return {"titular": titular[:100], "texto": texto}
                else:
                    print(f"   ⚠️ OpenAI dejó inglés o texto corto, usando plantill
(Content truncated due to size limit. Use line ranges to read remaining content)
