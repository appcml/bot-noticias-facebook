# -*- coding: utf-8 -*-
import requests
import feedparser
import re
import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# ============================================================================
# CONFIGURACION
# ============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

# FUENTES RSS INTERNACIONALES
RSS_FEEDS = [
    'https://rss.cnn.com/rss/edition.rss',
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.france24.com/es/rss',
    'https://www.dw.com/es/actualidad/s-30684/rss',
    'https://www.eltiempo.com/rss/mundo.xml',
    'https://www.clarin.com/rss/mundo/',
    'https://www.latercera.com/feed/',
    'https://www.infobae.com/feeds/rss/',
    'https://www.20minutos.es/rss/',
    'https://www.elconfidencial.com/rss/',
    'https://www.rtve.es/api/rss/noticias/',
    'https://www.eldiario.es/rss/',
    'https://feeds.skynews.com/feeds/rss/world.xml',
    'https://www.reutersagency.com/feed/?best-topics=world',
]

# PALABRAS CLAVE VIRALES
PALABRAS_VIRALES = [
    'ultima hora', 'urgente', 'impactante', 'historico', 'crisis', 'grave', 'alerta',
    'polemica', 'escandalo', 'revelan', 'confirmado', 'tension', 'sorpresa', 'inesperado',
    'explota', 'controversia', 'acusacion', 'investigacion', 'denuncia', 'filtracion',
    'advertencia', 'crisis politica', 'caos', 'conflicto', 'tension internacional',
    'enfrentamiento', 'protesta masiva', 'revuelta', 'disturbios', 'crisis de gobierno',
    'ataque', 'bombardeo', 'invasion', 'ofensiva', 'operacion militar', 'misil', 'batalla',
    'conflicto armado', 'crisis economica', 'recesion', 'inflacion record', 'colapso',
    'quiebra', 'perdidas millonarias', 'sube el dolar', 'crisis financiera', 'descubrimiento',
    'hallazgo', 'cientificos revelan', 'nuevo estudio', 'innovacion', 'inteligencia artificial',
    'avance tecnologico', 'ciberataque', 'hackeo', 'filtracion de datos', 'pandemia',
    'epidemia', 'brote', 'alerta sanitaria', 'virus', 'vacuna', 'cambio climatico',
    'huracan', 'incendio forestal', 'sequia', 'inundaciones', 'asesinato', 'crimen',
    'narcotrafico', 'detenido', 'operativo policial', 'elecciones', 'gobierno', 'presidente',
    'reforma', 'ley', 'empresa', 'inversion', 'economia', 'mercado', 'bolsa', 'banco',
    'estrategia', 'decision clave', 'medida urgente', 'impacto global', 'debate internacional',
    'preocupacion mundial'
]

# CATEGORIAS CON PALABRAS CLAVE
CATEGORIAS = {
    'politica': ['gobierno', 'presidente', 'elecciones', 'congreso', 'senado', 'parlamento', 
                 'ministro', 'ley', 'reforma', 'oposicion', 'partido', 'votacion', 'candidato'],
    'economia': ['economia', 'mercado', 'bolsa', 'inversion', 'banco', 'inflacion', 
                 'dolar', 'empresa', 'comercio', 'finanzas', 'perdidas', 'quiebra', 'recesion'],
    'internacional': ['guerra', 'conflicto', 'ataque', 'bombardeo', 'invasion', 'misil', 
                      'tension internacional', 'diplomacia', 'acuerdo', 'tratado', 'sanciones'],
    'seguridad': ['crimen', 'asesinato', 'narcotrafico', 'detenido', 'operativo', 'policia',
                  'investigacion', 'homicidio', 'robo', 'banda criminal'],
    'tecnologia': ['inteligencia artificial', 'tecnologia', 'innovacion', 'ciberataque', 
                   'hackeo', 'digital', 'software', 'app', 'internet'],
    'salud': ['pandemia', 'epidemia', 'virus', 'vacuna', 'brote', 'hospital', 'medicina'],
    'medio_ambiente': ['cambio climatico', 'huracan', 'incendio', 'sequia', 'inundacion',
                       'temperatura', 'calentamiento global'],
    'ciencia': ['descubrimiento', 'hallazgo', 'cientificos', 'estudio', 'espacio', 
                'astronomia', 'planeta', 'mision espacial']
}

# PAISES PARA HASHTAGS
PAISES = {
    'estados unidos': 'EstadosUnidos', 'usa': 'EstadosUnidos', 'ee.uu': 'EstadosUnidos',
    'espana': 'Espana', 'madrid': 'Espana', 'barcelona': 'Espana',
    'mexico': 'Mexico', 'cdmx': 'Mexico', 'ciudad de mexico': 'Mexico',
    'argentina': 'Argentina', 'buenos aires': 'Argentina',
    'chile': 'Chile', 'santiago': 'Chile',
    'colombia': 'Colombia', 'bogota': 'Colombia',
    'peru': 'Peru', 'lima': 'Peru',
    'venezuela': 'Venezuela', 'caracas': 'Venezuela',
    'brasil': 'Brasil', 'brasilia': 'Brasil', 'sao paulo': 'Brasil',
    'francia': 'Francia', 'paris': 'Francia',
    'alemania': 'Alemania', 'berlin': 'Alemania',
    'italia': 'Italia', 'roma': 'Italia',
    'reino unido': 'ReinoUnido', 'londres': 'ReinoUnido', 'uk': 'ReinoUnido',
    'rusia': 'Rusia', 'moscu': 'Rusia', 'ucrania': 'Ucrania', 'kiev': 'Ucrania',
    'china': 'China', 'pekin': 'China', 'shanghai': 'China',
    'japon': 'Japon', 'tokio': 'Japon',
    'israel': 'Israel', 'gaza': 'Israel', 'palestina': 'Palestina',
    'iran': 'Iran', 'teheran': 'Iran',
    'corea del norte': 'CoreaDelNorte', 'corea del sur': 'CoreaDelSur',
    'india': 'India', 'nueva delhi': 'India',
    'australia': 'Australia', 'sidney': 'Australia',
    'canada': 'Canada', 'toronto': 'Canada',
    'turquia': 'Turquia', 'estambul': 'Turquia',
    'siria': 'Siria', 'damasco': 'Siria',
    'libano': 'Libano', 'beirut': 'Libano',
    'arabia saudita': 'ArabiaSaudita', 'emiratos': 'EmiratosArabes',
    'qatar': 'Qatar', 'doha': 'Qatar',
    'egipto': 'Egipto', 'el cairo': 'Egipto',
    'sudafrica': 'Sudafrica', 'ciudad del cabo': 'Sudafrica',
    'nigeria': 'Nigeria', 'lagos': 'Nigeria',
    'kenia': 'Kenia', 'nairobi': 'Kenia',
    'etiopia': 'Etiopia', 'adis abeba': 'Etiopia',
    'marruecos': 'Marruecos', 'casablanca': 'Marruecos',
    'argelia': 'Argelia', 'tunez': 'Tunez',
    'europa': 'Europa', 'asia': 'Asia', 'africa': 'Africa', 
    'america latina': 'Latam', 'latinoamerica': 'Latam',
    'oriente medio': 'OrienteMedio', 'medio oriente': 'OrienteMedio'
}

def cargar_historial():
    """Carga el historial de publicaciones con manejo seguro de todas las claves"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                historial = json.load(f)
                historial.setdefault('urls', [])
                historial.setdefault('titulos', [])
                historial.setdefault('hashes', [])
                historial.setdefault('ultima_publicacion', None)
                return historial
        except Exception as e:
            print(f"⚠️ Error cargando historial: {e}")
    
    return {'urls': [], 'titulos': [], 'hashes': [], 'ultima_publicacion': None}

def guardar_historial(historial, url, titulo):
    """Guarda una noticia en el historial"""
    if 'urls' not in historial:
        historial['urls'] = []
    if 'titulos' not in historial:
        historial['titulos'] = []
    if 'hashes' not in historial:
        historial['hashes'] = []
    
    url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()
    
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['hashes'].append(url_hash)
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    historial['hashes'] = historial['hashes'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Guardada en historial")
    except Exception as e:
        print(f"⚠️ Error guardando historial: {e}")

def es_duplicado(historial, url, titulo):
    """Verifica si una noticia ya fue publicada"""
    url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()
    
    if url_hash in historial.get('hashes', []):
        return True
    
    if url in historial.get('urls', []):
        return True
    
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial.get('titulos', []):
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencias = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencias / max(len(titulo_simple), len(t_simple)) > 0.75:
                return True
    
    return False

def detectar_pais(titulo, descripcion):
    """Detecta el pais de la noticia para el hashtag"""
    texto = f"{titulo} {descripcion}".lower()
    
    for pais, hashtag in PAISES.items():
        if pais in texto:
            return hashtag
    
    if any(x in texto for x in ['union europea', 'ue', 'europeo', 'europea', 'bruselas']):
        return 'Europa'
    if any(x in texto for x in ['onu', 'naciones unidas', 'nueva york']):
        return 'ONU'
    if any(x in texto for x in ['otan', 'nato']):
        return 'OTAN'
    
    return 'Mundo'

def clasificar_categoria(titulo, descripcion):
    """Clasifica la noticia en una categoria"""
    texto = f"{titulo} {descripcion}".lower()
    
    puntuaciones = {}
    for cat, palabras in CATEGORIAS.items():
        score = sum(1 for p in palabras if p in texto)
        puntuaciones[cat] = score
    
    if max(puntuaciones.values()) > 0:
        return max(puntuaciones, key=puntuaciones.get)
    
    return 'general'

def calcular_puntaje_viral(titulo, descripcion):
    """Calcula que tan viral es una noticia basado en palabras clave"""
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    for palabra in PALABRAS_VIRALES:
        if palabra in texto:
            if palabra in ['urgente', 'ultima hora', 'crisis', 'alerta', 'guerra', 'ataque']:
                puntaje += 3
            else:
                puntaje += 1
    
    return puntaje

def asegurar_puntuacion(texto):
    """Asegura que el texto termine con punto final y tenga puntuacion correcta"""
    if not texto:
        return texto
    
    texto = texto.strip()
    texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
    
    if not texto.endswith(('.', '!', '?')):
        texto += '.'
    
    texto = re.sub(r'\.{2,}', '.', texto)
    texto = re.sub(r'\.([A-ZÁÉÍÓÚÑ])', r'. \1', texto)
    
    return texto

def limpiar_texto_extraccion(texto):
    """Limpia el texto extraido eliminando metadatos, fechas, horas y elementos no deseados"""
    if not texto:
        return texto
    
    lineas = texto.split('\n')
    lineas_limpias = []
    
    patrones_eliminar = [
        r'^\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}$',
        r'^\d{1,2}/\d{1,2}/\d{2,4}$',
        r'^\d{1,2}-\d{1,2}-\d{2,4}$',
        r'^\d{2}:\d{2}\s*(h|hrs|horas)?$',
        r'^actualizado\s+(el|la)?',
        r'^\d+\s*$',
        r'^[A-Z][a-z]+?\s*/\s*[A-Z]+$',
        r'^ANALISIS$',
        r'^OPINION$',
        r'^REPORTAJE$',
        r'^ENTREVISTA$',
        r'^—\s*[A-Z]',
        r'^[A-Z][a-zA-Z\s]+?\s*/\s*[A-Z][a-zA-Z\s]+?$',
        r'^\d{1,2}\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)$',
    ]
    
    for linea in lineas:
        linea_strip = linea.strip()
        
        if len(linea_strip) < 3:
            continue
        
        es_metadato = False
        for patron in patrones_eliminar:
            if re.match(patron, linea_strip, re.IGNORECASE):
                es_metadato = True
                break
        
        palabras_menu = ['compartir', 'facebook', 'twitter', 'whatsapp', 'telegram', 
                        'imprimir', 'guardar', 'enviar', 'suscribete', 'newsletter',
                        'cookie', 'aviso legal', 'politica de privacidad', 'mapa web']
        if any(p in linea_strip.lower() for p in palabras_menu) and len(linea_strip) < 50:
            es_metadato = True
        
        if not es_metadato:
            lineas_limpias.append(linea_strip)
    
    texto_limpio = '\n'.join(lineas_limpias)
    texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_limpio)
    texto_limpio = re.sub(r'[ \t]+', ' ', texto_limpio)
    
    return texto_limpio.strip()

def extraer_texto_completo(url):
    """Extrae el texto completo de una noticia desde su URL de forma limpia y ordenada"""
    print(f"   🔍 Extrayendo texto de: {url[:50]}...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for elemento in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                             'form', 'iframe', 'noscript', 'figure', 'figcaption',
                             'button', 'input', 'select', 'textarea']):
            elemento.decompose()
        
        for clase in ['date', 'time', 'author', 'byline', 'meta', 'tags', 'share',
                      'social', 'comments', 'related', 'sidebar', 'menu', 'breadcrumb']:
            for elem in soup.find_all(class_=re.compile(clase, re.I)):
                elem.decompose()
        
        contenido = None
        
        selectores_por_dominio = {
            'eldiario.es': ['.article-content', '.news-body', '[data-testid="article-body"]'],
            'elpais.com': ['.article_body', '.a_c', '.article-content'],
            'elmundo.es': ['.ue-c-article__body', '.article-body'],
            'bbc.com': ['.ssrcss-pv1rh6-ArticleWrapper', '.article-body'],
            'cnn.com': ['.article__content', '.zn-body__paragraph'],
            'reuters.com': ['.article-body__content__17Yit', '.ArticleBodyWrapper'],
            '20minutos.es': ['.article-body', '.content'],
        }
        
        dominio = urlparse(url).netloc.replace('www.', '')
        
        if dominio in selectores_por_dominio:
            for selector in selectores_por_dominio[dominio]:
                try:
                    elem = soup.select_one(selector)
                    if elem and len(elem.get_text(strip=True)) > 300:
                        contenido = elem
                        print(f"   ✅ Selector especifico para {dominio}")
                        break
                except:
                    continue
        
        if not contenido:
            selectores_genericos = [
                'article',
                '[class*="article-body"]',
                '[class*="article_content"]',
                '[class*="entry-content"]',
                '[class*="post-content"]',
                '[class*="news-body"]',
                '[class*="story-body"]',
                '[class*="text-content"]',
                'main article',
                '[role="main"]',
                '.content-body',
                '#article-body',
                '.body-text',
            ]
            
            for selector in selectores_genericos:
                try:
                    elem = soup.select_one(selector)
                    if elem and len(elem.get_text(strip=True)) > 400:
                        contenido = elem
                        break
                except:
                    continue
        
        if not contenido:
            candidatos = {}
            for p in soup.find_all('p'):
                padre = p.find_parent(['div', 'article', 'section'])
                if padre:
                    pid = id(padre)
                    candidatos[pid] = candidatos.get(pid, {'elem': padre, 'count': 0})
                    candidatos[pid]['count'] += 1
            
            if candidatos:
                mejor = max(candidatos.values(), key=lambda x: x['count'])
                if mejor['count'] >= 3:
                    contenido = mejor['elem']
        
        if contenido:
            parrafos = []
            for elem in contenido.find_all(['p', 'h2', 'h3']):
                texto = elem.get_text(strip=True)
                
                if len(texto) < 40:
                    continue
                if any(x in texto.lower() for x in ['publicidad', 'anuncio', 'suscribete', 
                                                     'comparte en', 'siguenos en', 'mas informacion']):
                    continue
                if texto.isupper() and len(texto) < 100:
                    continue
                
                texto = asegurar_puntuacion(texto)
                parrafos.append(texto)
            
            texto_final = '\n\n'.join(parrafos)
            texto_final = limpiar_texto_extraccion(texto_final)
            
            if len(texto_final) > 6000:
                texto_final = texto_final[:6000].rsplit('.', 1)[0] + '.'
            
            if len(texto_final) > 300:
                print(f"   ✅ Extraido: {len(texto_final)} caracteres, {len(parrafos)} parrafos")
                return texto_final
        
    except Exception as e:
        print(f"   ⚠️ Error: {str(e)[:60]}")
    
    return None

def generar_redaccion_profesional(titulo, texto_completo, descripcion_rss, fuente):
    """Genera redaccion periodistica profesional usando IA con el texto COMPLETO limpio"""
    print(f"   🤖 Generando redaccion profesional...")
    
    texto_para_ia = texto_completo[:5000] if len(texto_completo) > 5000 else texto_completo
    
    if not OPENROUTER_API_KEY:
        return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)
    
    prompt = f"""Eres un editor senior de agencia de noticias internacional.

REDACTA UNA NOTICIA PROFESIONAL para publicar en Facebook usando esta informacion:

TITULO ORIGINAL: {titulo}
FUENTE: {fuente}

TEXTO COMPLETO DE LA NOTICIA:
{texto_para_ia}

REGLAS DE REDACCION OBLIGATORIAS:

1. Escribe en ESPANOL neutro y profesional
2. Estructura EXACTA con parrafos separados por lineas en blanco:

PARRAFO 1 (Lead): Lo mas importante (quien, que, cuando, donde, por que). Minimo 2 oraciones, maximo 3. Debe terminar con PUNTO.

PARRAFO 2: Contexto y antecedentes. Minimo 2 oraciones, maximo 3. Debe terminar con PUNTO.

PARRAFO 3: Desarrollo y detalles clave. Minimo 2 oraciones, maximo 3. Debe terminar con PUNTO.

PARRAFO 4: Consecuencias o proximos pasos. Minimo 2 oraciones, maximo 3. Debe terminar con PUNTO.

3. CADA parrafo DEBE terminar con punto (.)
4. Entre parrafo y parrafo deja UNA linea en blanco exactamente
5. Longitud total: 600-1200 caracteres
6. NO incluir: fechas de publicacion, horas, nombres de fotografos, "ANALISIS", etiquetas de seccion
7. NO usar corchetes ni texto entre [ ]
8. Terminar con: "Fuente: {fuente}."

EJEMPLO DE FORMATO CORRECTO:

El gobierno de Iran anuncio nuevas medidas de defensa ante los ataques recibidos. Las autoridades confirmaron que se reforzaran las instalaciones militares en todo el territorio.

La tension en la region ha escalado desde el inicio del conflicto hace dos semanas. Diversos paises han expresado su preocupacion por la situacion y llamado al dialogo.

Los bombardeos han afectado principalmente zonas industriales y militares. Se reportan danos significativos en infraestructura critica del pais.

Las autoridades internacionales continuan monitoreando la situacion. Se esperan declaraciones oficiales en las proximas horas.

Fuente: {fuente}

AHORA ESCRIBE LA NOTICIA:"""

    modelos = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'HTTP-Referer': 'https://github.com',
        'X-Title': 'Bot Noticias',
        'Content-Type': 'application/json'
    }
    
    for modelo in modelos:
        try:
            print(f"   🔄 Modelo: {modelo.split('/')[-1]}...")
            
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={
                    'model': modelo,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.2,
                    'max_tokens': 1500
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    contenido = data['choices'][0]['message']['content']
                    
                    contenido = limpiar_salida_ia(contenido)
                    contenido = asegurar_puntuacion_parrafos(contenido)
                    
                    if len(contenido) > 500 and '\n\n' in contenido:
                        print(f"   ✅ Redaccion: {len(contenido)} caracteres")
                        return contenido
                    else:
                        print(f"   ⚠️ Respuesta corta, probando otro modelo...")
                        
        except Exception as e:
            print(f"   ⚠️ Error: {str(e)[:40]}")
            continue
    
    return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)

def asegurar_puntuacion_parrafos(texto):
    """Asegura que cada parrafo termine con punto final y esten separados por lineas en blanco"""
    if not texto:
        return texto
    
    parrafos = re.split(r'\n\s*\n', texto.strip())
    parrafos_corregidos = []
    
    for parrafo in parrafos:
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        
        parrafo = parrafo.replace('\n', ' ')
        parrafo = re.sub(r'\s+', ' ', parrafo)
        parrafo = asegurar_puntuacion(parrafo)
        
        parrafos_corregidos.append(parrafo)
    
    return '\n\n'.join(parrafos_corregidos)

def limpiar_salida_ia(contenido):
    """Limpia la salida de la IA de cualquier elemento no deseado"""
    if not contenido:
        return contenido
    
    contenido = re.sub(r'\[.*?\]', '', contenido, flags=re.DOTALL)
    contenido = re.sub(r'\{.*?\}', '', contenido, flags=re.DOTALL)
    
    lineas_a_eliminar = [
        r'^TITULO ATRACTIVO$',
        r'^Parrafo \d+',
        r'^PARRAFO \d+',
        r'^\d+\.',
        r'^FORMATO',
        r'^REGLAS',
        r'^IMPORTANTE',
        r'^Nota:',
        r'^Notas?:',
        r'^EJEMPLO',
        r'^AHORA ESCRIBE',
    ]
    
    lineas = contenido.split('\n')
    lineas_limpias = []
    
    for linea in lineas:
        linea_strip = linea.strip()
        
        if not linea_strip and not lineas_limpias:
            continue
        
        es_instruccion = False
        for patron in lineas_a_eliminar:
            if re.match(patron, linea_strip, re.IGNORECASE):
                es_instruccion = True
                break
        
        if not es_instruccion:
            lineas_limpias.append(linea_strip)
    
    contenido = '\n'.join(lineas_limpias)
    contenido = re.sub(r'\n{3,}', '\n\n', contenido)
    contenido = re.sub(r'[ \t]+', ' ', contenido)
    contenido = contenido.strip()
    
    return contenido

def generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente):
    """Genera redaccion manual ordenada con puntacion correcta y parrafos separados"""
    print(f"   📝 Redaccion manual ordenada...")
    
    oraciones = [s.strip() for s in re.split(r'[.!?]+', texto_completo) 
                 if len(s.strip()) > 30 and len(s.strip()) < 300]
    
    if len(oraciones) < 4:
        oraciones = [s.strip() for s in re.split(r'[.!?]+', descripcion_rss) 
                     if len(s.strip()) > 20]
        oraciones.extend([s.strip() for s in re.split(r'[.!?]+', texto_completo) 
                          if len(s.strip()) > 30][:5])
    
    parrafos = []
    
    if len(oraciones) >= 2:
        p = f"{oraciones[0]}. {oraciones[1]}."
    else:
        p = oraciones[0] if oraciones else f"Se reporta un importante acontecimiento de relevancia internacional."
    parrafos.append(asegurar_puntuacion(p))
    
    if len(oraciones) >= 4:
        p = f"{oraciones[2]}. {oraciones[3]}."
    else:
        p = "El hecho ha generado amplia repercusion en los medios de comunicacion y entre la opinion publica."
    parrafos.append(asegurar_puntuacion(p))
    
    if len(oraciones) >= 6:
        p = f"{oraciones[4]}. {oraciones[5]}."
    else:
        p = "Las autoridades competentes continuan evaluando la situacion mientras se desarrollan los hechos."
    parrafos.append(asegurar_puntuacion(p))
    
    if len(oraciones) >= 8:
        p = f"{oraciones[6]}. {oraciones[7]}."
    else:
        p = "Se esperan actualizaciones oficiales en las proximas horas sobre el desarrollo de esta informacion."
    parrafos.append(asegurar_puntuacion(p))
    
    cuerpo = '\n\n'.join(parrafos)
    cuerpo = re.sub(r'\.+', '.', cuerpo)
    cuerpo = re.sub(r'\s+', ' ', cuerpo)
    
    parrafos_finales = cuerpo.split('. ')
    if len(parrafos_finales) >= 4:
        cuerpo = '\n\n'.join([
            f"{parrafos_finales[0]}. {parrafos_finales[1]}.",
            f"{parrafos_finales[2]}. {parrafos_finales[3]}.",
            f"{parrafos_finales[4]}. {parrafos_finales[5]}.",
            f"{parrafos_finales[6]}. {parrafos_finales[7]}."
        ])
    
    redaccion = f"{cuerpo}\n\nFuente: {fuente}."
    
    print(f"   ✅ Manual: {len(redaccion)} caracteres")
    return redaccion

def generar_hashtags(categoria, pais, titulo):
    """Genera hashtags relevantes"""
    hashtags_categoria = {
        'politica': ['#Politica', '#Gobierno'],
        'economia': ['#Economia', '#Finanzas'],
        'internacional': ['#Internacional', '#Mundo'],
        'seguridad': ['#Seguridad', '#Justicia'],
        'tecnologia': ['#Tecnologia', '#Innovacion'],
        'ciencia': ['#Ciencia', '#Investigacion'],
        'salud': ['#Salud', '#Medicina'],
        'medio_ambiente': ['#MedioAmbiente', '#Clima'],
        'general': ['#Actualidad', '#Noticias']
    }
    
    tags = hashtags_categoria.get(categoria, hashtags_categoria['general'])[:2]
    tags.append(f"#{pais}")
    
    titulo_lower = titulo.lower()
    if any(x in titulo_lower for x in ['urgente', 'alerta', 'crisis']):
        tags.append('#Urgente')
    else:
        tags.append('#UltimaHora')
    
    return ' '.join(tags)

def extraer_imagen(entry, url_noticia=None):
    """Extrae la imagen de la noticia"""
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('url'):
                return media['url']
    
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('href') and any(x in enc.get('type', '') for x in ['image', 'jpg', 'png']):
                return enc['href']
    
    for campo in ['summary', 'description', 'content']:
        if hasattr(entry, campo):
            texto = getattr(entry, campo, '')
            if texto:
                match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', texto, re.I)
                if match:
                    return match.group(1)
    
    if url_noticia:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url_noticia, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            meta_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'})
            if meta_img:
                img_url = meta_img.get('content') or meta_img.get('value')
                if img_url:
                    return img_url
            
            img = soup.find('img', class_=re.compile(r'article|main|featured|hero', re.I))
            if img and img.get('src'):
                return img['src']
                
        except:
            pass
    
    return None

def descargar_imagen(url):
    """Descarga imagen temporalmente"""
    if not url or not url.startswith('http'):
        return None
    
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(resp.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            img.thumbnail((1200, 1200))
            
            temp_path = f'/tmp/noticia_{hashlib.md5(url.encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85)
            return temp_path
            
    except Exception as e:
        print(f"   ⚠️ Error imagen: {str(e)[:40]}")
    
    return None

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook con formato limpio, parrafos separados y ordenado"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    texto = asegurar_puntuacion_parrafos(texto)
    
    mensaje = f"""{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    if len(mensaje) > 2000:
        exceso = len(mensaje) - 1950
        parrafos = texto.split('\n\n')
        texto_corto = ''
        for p in parrafos[:-1]:
            if len(texto_corto) + len(p) < (len(texto) - exceso - 100):
                texto_corto += p + '\n\n'
        
        texto_corto = texto_corto.strip().rsplit('.', 1)[0] + "."
        mensaje = f"""{texto_corto}

[Ver noticia completa en fuente original]

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    print(f"\n   📝 Publicacion ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    lineas = mensaje.split('\n')
    for i, linea in enumerate(lineas[:12]):
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
    if len(lineas) > 12:
        print(f"   ... ({len(lineas) - 12} lineas mas)")
    print(f"   {'='*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={
                    'message': mensaje,
                    'access_token': FB_ACCESS_TOKEN
                },
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

def buscar_noticias():
    """Busca noticias en fuentes RSS"""
    print("\n🔍 Buscando noticias...")
    noticias = []
    
    if NEWS_API_KEY:
        try:
            terminos = random.sample([
                'urgente crisis', 'ultima hora', 'alerta internacional',
                'guerra conflicto', 'economia crisis', 'politica elecciones'
            ], 2)
            
            for termino in terminos:
                try:
                    resp = requests.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            'q': termino,
                            'language': 'es',
                            'sortBy': 'publishedAt',
                            'pageSize': 5,
                            'apiKey': NEWS_API_KEY
                        },
                        timeout=15
                    )
                    data = resp.json()
                    if data.get('status') == 'ok':
                        for art in data.get('articles', []):
                            noticias.append({
                                'titulo': art.get('title', ''),
                                'descripcion': art.get('description', ''),
                                'url': art.get('url', ''),
                                'imagen': art.get('urlToImage', ''),
                                'fuente': art.get('source', {}).get('name', 'Agencias'),
                                'fecha': art.get('publishedAt', ''),
                                'puntaje_viral': calcular_puntaje_viral(art.get('title', ''), art.get('description', '')),
                                'texto_completo': None
                            })
                except:
                    continue
        except:
            pass
    
    random.shuffle(RSS_FEEDS)
    
    for feed_url in RSS_FEEDS[:10]:
        try:
            feed = feedparser.parse(feed_url)
            fuente_nombre = feed.feed.get('title', feed_url.split('/')[2])
            
            for entry in feed.entries[:3]:
                titulo = entry.get('title', '')
                descripcion = entry.get('summary', entry.get('description', ''))
                url = entry.get('link', '')
                
                imagen = extraer_imagen(entry, url)
                puntaje = calcular_puntaje_viral(titulo, descripcion)
                
                if puntaje > 0:
                    noticias.append({
                        'titulo': titulo,
                        'descripcion': descripcion,
                        'url': url,
                        'imagen': imagen,
                        'fuente': fuente_nombre,
                        'fecha': entry.get('published', ''),
                        'puntaje_viral': puntaje,
                        'texto_completo': None
                    })
            
            print(f"   📡 {fuente_nombre[:25]}: {len(feed.entries)} entradas")
            
        except Exception as e:
            print(f"   ⚠️ Error feed: {str(e)[:40]}")
            continue
    
    print(f"\n📊 Total: {len(noticias)} noticias")
    return noticias

def filtrar_y_seleccionar(noticias, historial):
    """Filtra y selecciona la mejor noticia que NO haya sido publicada antes"""
    print("\n🔎 Filtrando noticias no publicadas...")
    
    candidatas = []
    
    for noticia in noticias:
        if es_duplicado(historial, noticia['url'], noticia['titulo']):
            print(f"   ⏭️ Ya publicada: {noticia['titulo'][:40]}...")
            continue
            
        if len(noticia['titulo']) < 15 or "[Removed]" in noticia['titulo']:
            continue
        
        noticia['categoria'] = clasificar_categoria(noticia['titulo'], noticia['descripcion'])
        noticia['pais'] = detectar_pais(noticia['titulo'], noticia['descripcion'])
        
        candidatas.append(noticia)
        print(f"   ✅ [{noticia['categoria']}] {noticia['titulo'][:40]}... (viral: {noticia['puntaje_viral']})")
    
    if not candidatas:
        print("⚠️ No hay noticias nuevas disponibles")
        return None
    
    candidatas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
    seleccionada = candidatas[0]
    
    print(f"\n🎯 Seleccionada: {seleccionada['titulo'][:50]}...")
    
    print(f"\n📄 Extrayendo contenido...")
    texto_completo = extraer_texto_completo(seleccionada['url'])
    
    if texto_completo:
        seleccionada['texto_completo'] = texto_completo
    else:
        desc_limpia = re.sub(r'<[^>]+>', '', seleccionada['descripcion'])
        seleccionada['texto_completo'] = limpiar_texto_extraccion(desc_limpia)
        print(f"   ⚠️ Usando descripcion RSS: {len(seleccionada['texto_completo'])} caracteres")
    
    return seleccionada

def main():
    """Funcion principal que publica UNA noticia nueva"""
    print("\n" + "="*60)
    print("INICIANDO PUBLICACION")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)
    
    historial = cargar_historial()
    print(f"📚 Historial: {len(historial.get('urls', []))} noticias previas")
    
    noticias = buscar_noticias()
    if not noticias:
        print("\n❌ Sin noticias disponibles")
        return False
    
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    if not seleccionada:
        print("\n❌ No se encontraron noticias nuevas para publicar")
        return False
    
    print(f"\n✍️ Redactando noticia...")
    redaccion = generar_redaccion_profesional(
        seleccionada['titulo'],
        seleccionada['texto_completo'],
        seleccionada['descripcion'],
        seleccionada['fuente']
    )
    
    hashtags = generar_hashtags(
        seleccionada['categoria'],
        seleccionada['pais'],
        seleccionada['titulo']
    )
    
    print(f"\n🖼️ Descargando imagen...")
    imagen_path = descargar_imagen(seleccionada['imagen'])
    
    if not imagen_path and seleccionada.get('texto_completo'):
        urls_img = re.findall(r'https?://[^\s"\']+\.(?:jpg|jpeg|png)', seleccionada['texto_completo'])
        for url_img in urls_img[:2]:
            imagen_path = descargar_imagen(url_img)
            if imagen_path:
                break
    
    if not imagen_path:
        print("❌ Sin imagen disponible")
        return False
    
    print(f"\n📤 Publicando en Facebook...")
    exito = publicar_facebook(
        seleccionada['titulo'],
        redaccion,
        imagen_path,
        hashtags
    )
    
    if exito:
        guardar_historial(historial, seleccionada['url'], seleccionada['titulo'])
        
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n" + "="*60)
        print("✅ PUBLICACION EXITOSA")
        print("="*60)
        return True
    else:
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n❌ Fallo la publicacion")
        return False

# ============================================================================
# EJECUCION PARA GITHUB ACTIONS (sin bucle infinito)
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 BOT DE NOTICIAS - EJECUCION UNICA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        exito = main()
        if exito:
            print("\n" + "="*60)
            print("✅ PUBLICACION EXITOSA")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("⚠️ NO SE PUBLICO (sin noticias nuevas o error)")
            print("="*60)
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
