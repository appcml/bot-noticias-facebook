import requests
import feedparser
import re
import hashlib
import json
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# CONFIGURACIÓN
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
    'última hora', 'urgente', 'impactante', 'histórico', 'crisis', 'grave', 'alerta',
    'polémica', 'escándalo', 'revelan', 'confirmado', 'tensión', 'sorpresa', 'inesperado',
    'explota', 'controversia', 'acusación', 'investigación', 'denuncia', 'filtración',
    'advertencia', 'crisis política', 'caos', 'conflicto', 'tensión internacional',
    'enfrentamiento', 'protesta masiva', 'revuelta', 'disturbios', 'crisis de gobierno',
    'ataque', 'bombardeo', 'invasión', 'ofensiva', 'operación militar', 'misil', 'batalla',
    'conflicto armado', 'crisis económica', 'recesión', 'inflación récord', 'colapso',
    'quiebra', 'pérdidas millonarias', 'sube el dólar', 'crisis financiera', 'descubrimiento',
    'hallazgo', 'científicos revelan', 'nuevo estudio', 'innovación', 'inteligencia artificial',
    'avance tecnológico', 'ciberataque', 'hackeo', 'filtración de datos', 'pandemia',
    'epidemia', 'brote', 'alerta sanitaria', 'virus', 'vacuna', 'cambio climático',
    'huracán', 'incendio forestal', 'sequía', 'inundaciones', 'asesinato', 'crimen',
    'narcotráfico', 'detenido', 'operativo policial', 'elecciones', 'gobierno', 'presidente',
    'reforma', 'ley', 'empresa', 'inversión', 'economía', 'mercado', 'bolsa', 'banco',
    'estrategia', 'decisión clave', 'medida urgente', 'impacto global', 'debate internacional',
    'preocupación mundial'
]

# CATEGORÍAS CON PALABRAS CLAVE
CATEGORIAS = {
    'politica': ['gobierno', 'presidente', 'elecciones', 'congreso', 'senado', 'parlamento', 
                 'ministro', 'ley', 'reforma', 'oposición', 'partido', 'votación', 'candidato'],
    'economia': ['economía', 'mercado', 'bolsa', 'inversión', 'banco', 'inflación', 
                 'dólar', 'empresa', 'comercio', 'finanzas', 'pérdidas', 'quiebra', 'recesión'],
    'internacional': ['guerra', 'conflicto', 'ataque', 'bombardeo', 'invasión', 'misil', 
                      'tensión internacional', 'diplomacia', 'acuerdo', 'tratado', 'sanciones'],
    'seguridad': ['crimen', 'asesinato', 'narcotráfico', 'detenido', 'operativo', 'policía',
                  'investigación', 'homicidio', 'robo', 'banda criminal'],
    'tecnologia': ['inteligencia artificial', 'tecnología', 'innovación', 'ciberataque', 
                   'hackeo', 'digital', 'software', 'app', 'internet'],
    'salud': ['pandemia', 'epidemia', 'virus', 'vacuna', 'brote', 'hospital', 'medicina'],
    'medio_ambiente': ['cambio climático', 'huracán', 'incendio', 'sequía', 'inundación',
                       'temperatura', 'calentamiento global'],
    'ciencia': ['descubrimiento', 'hallazgo', 'científicos', 'estudio', 'espacio', 
                'astronomía', 'planeta', 'misión espacial']
}

# PAÍSES PARA HASHTAGS
PAISES = {
    'estados unidos': 'EstadosUnidos', 'usa': 'EstadosUnidos', 'ee.uu': 'EstadosUnidos',
    'españa': 'España', 'madrid': 'España', 'barcelona': 'España',
    'méxico': 'Mexico', 'cdmx': 'Mexico', 'ciudad de méxico': 'Mexico',
    'argentina': 'Argentina', 'buenos aires': 'Argentina',
    'chile': 'Chile', 'santiago': 'Chile',
    'colombia': 'Colombia', 'bogotá': 'Colombia',
    'perú': 'Peru', 'lima': 'Peru',
    'venezuela': 'Venezuela', 'caracas': 'Venezuela',
    'brasil': 'Brasil', 'brasilia': 'Brasil', 'sao paulo': 'Brasil',
    'francia': 'Francia', 'parís': 'Francia',
    'alemania': 'Alemania', 'berlín': 'Alemania',
    'italia': 'Italia', 'roma': 'Italia',
    'reino unido': 'ReinoUnido', 'londres': 'ReinoUnido', 'uk': 'ReinoUnido',
    'rusia': 'Rusia', 'moscú': 'Rusia', 'ucrania': 'Ucrania', 'kiev': 'Ucrania',
    'china': 'China', 'pekin': 'China', 'shanghai': 'China',
    'japón': 'Japon', 'tokio': 'Japon',
    'israel': 'Israel', 'gaza': 'Israel', 'palestina': 'Palestina',
    'irán': 'Iran', 'teherán': 'Iran',
    'corea del norte': 'CoreaDelNorte', 'corea del sur': 'CoreaDelSur',
    'india': 'India', 'nueva delhi': 'India',
    'australia': 'Australia', 'sídney': 'Australia',
    'canadá': 'Canada', 'toronto': 'Canada',
    'turquía': 'Turquia', 'estambul': 'Turquia',
    'siria': 'Siria', 'damasco': 'Siria',
    'libano': 'Libano', 'beirut': 'Libano',
    'arabia saudita': 'ArabiaSaudita', 'emiratos': 'EmiratosArabes',
    'qatar': 'Qatar', 'doha': 'Qatar',
    'egipto': 'Egipto', 'el cairo': 'Egipto',
    'sudáfrica': 'Sudafrica', 'ciudad del cabo': 'Sudafrica',
    'nigeria': 'Nigeria', 'lagos': 'Nigeria',
    'kenia': 'Kenia', 'nairobi': 'Kenia',
    'etiopía': 'Etiopia', 'adís abeba': 'Etiopia',
    'marruecos': 'Marruecos', 'casablanca': 'Marruecos',
    'argelia': 'Argelia', 'túnez': 'Tunez',
    'europa': 'Europa', 'asia': 'Asia', 'áfrica': 'Africa', 
    'américa latina': 'Latam', 'latinoamérica': 'Latam',
    'oriente medio': 'OrienteMedio', 'medio oriente': 'OrienteMedio'
}

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

def cargar_historial():
    """Carga el historial de publicaciones"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'urls': [], 'titulos': [], 'ultima_publicacion': None}

def guardar_historial(historial, url, titulo):
    """Guarda una noticia en el historial"""
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    # Mantener solo últimas 500
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Guardada en historial")
    except Exception as e:
        print(f"⚠️ Error guardando historial: {e}")

def es_duplicado(historial, url, titulo):
    """Verifica si una noticia ya fue publicada"""
    url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()[:16]
    urls_hashes = [hashlib.md5(u.lower().strip().encode()).hexdigest()[:16] for u in historial.get('urls', [])]
    
    if url_hash in urls_hashes:
        return True
    
    # Verificar por título similar
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial.get('titulos', []):
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencias = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencias / max(len(titulo_simple), len(t_simple)) > 0.75:
                return True
    
    return False

def detectar_pais(titulo, descripcion):
    """Detecta el país de la noticia para el hashtag"""
    texto = f"{titulo} {descripcion}".lower()
    
    for pais, hashtag in PAISES.items():
        if pais in texto:
            return hashtag
    
    # Detectar por contexto
    if any(x in texto for x in ['unión europea', 'ue', 'europeo', 'europea', 'bruselas']):
        return 'Europa'
    if any(x in texto for x in ['onu', 'naciones unidas', 'nueva york']):
        return 'ONU'
    if any(x in texto for x in ['otan', 'nato']):
        return 'OTAN'
    
    return 'Mundo'

def clasificar_categoria(titulo, descripcion):
    """Clasifica la noticia en una categoría"""
    texto = f"{titulo} {descripcion}".lower()
    
    puntuaciones = {}
    for cat, palabras in CATEGORIAS.items():
        score = sum(1 for p in palabras if p in texto)
        puntuaciones[cat] = score
    
    if max(puntuaciones.values()) > 0:
        return max(puntuaciones, key=puntuaciones.get)
    
    return 'general'

def calcular_puntaje_viral(titulo, descripcion):
    """Calcula qué tan viral es una noticia basado en palabras clave"""
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    for palabra in PALABRAS_VIRALES:
        if palabra in texto:
            # Palabras de alta prioridad valen más
            if palabra in ['urgente', 'última hora', 'crisis', 'alerta', 'guerra', 'ataque']:
                puntaje += 3
            else:
                puntaje += 1
    
    return puntaje

def limpiar_texto_extraccion(texto):
    """
    Limpia el texto extraído eliminando metadatos, fechas, horas y elementos no deseados
    """
    if not texto:
        return texto
    
    # Eliminar líneas que son puramente fechas/horas/metadatos
    lineas = texto.split('\n')
    lineas_limpias = []
    
    patrones_eliminar = [
        r'^\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}$',  # 7 de marzo de 2026
        r'^\d{1,2}/\d{1,2}/\d{2,4}$',  # 09/03/2026
        r'^\d{1,2}-\d{1,2}-\d{2,4}$',  # 09-03-2026
        r'^\d{2}:\d{2}\s*(h|hrs|horas)?$',  # 22:37 h
        r'^actualizado\s+(el|la)?',  # Actualizado el
        r'^\d+\s*$',  # Solo números (contadores, etc)
        r'^[A-Z][a-z]+?\s*/\s*[A-Z]+$',  # Nombre / Agencia (ej: Taherkareh / EFE)
        r'^ANÁLISIS$',  # Etiquetas de sección
        r'^OPINIÓN$',
        r'^REPORTAJE$',
        r'^ENTREVISTA$',
        r'^—\s*[A-Z]',  # Firma de autor — Nombre Apellido
        r'^[A-Z][a-zA-Z\s]+?\s*/\s*[A-Z][a-zA-Z\s]+?$',  # Nombre / Apellido
        r'^\d{1,2}\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)$',  # 7 marzo
    ]
    
    for linea in lineas:
        linea_strip = linea.strip()
        
        # Saltar líneas vacías muy cortas
        if len(linea_strip) < 3:
            continue
        
        # Verificar si coincide con algún patrón de metadato
        es_metadato = False
        for patron in patrones_eliminar:
            if re.match(patron, linea_strip, re.IGNORECASE):
                es_metadato = True
                break
        
        # Eliminar también líneas que parezcan menú o navegación
        palabras_menu = ['compartir', 'facebook', 'twitter', 'whatsapp', 'telegram', 
                        'imprimir', 'guardar', 'enviar', 'suscríbete', 'newsletter',
                        'cookie', 'aviso legal', 'política de privacidad', 'mapa web']
        if any(p in linea_strip.lower() for p in palabras_menu) and len(linea_strip) < 50:
            es_metadato = True
        
        if not es_metadato:
            lineas_limpias.append(linea_strip)
    
    # Unir y limpiar espacios múltiples
    texto_limpio = '\n'.join(lineas_limpias)
    texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_limpio)
    texto_limpio = re.sub(r'[ \t]+', ' ', texto_limpio)
    
    return texto_limpio.strip()

def extraer_texto_completo(url):
    """
    Extrae el texto completo de una noticia desde su URL de forma limpia y ordenada
    """
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
        
        # Eliminar TODOS los elementos no deseados
        for elemento in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                             'form', 'iframe', 'noscript', 'figure', 'figcaption',
                             'button', 'input', 'select', 'textarea']):
            elemento.decompose()
        
        # Eliminar elementos por clase común de metadatos
        for clase in ['date', 'time', 'author', 'byline', 'meta', 'tags', 'share',
                      'social', 'comments', 'related', 'sidebar', 'menu', 'breadcrumb']:
            for elem in soup.find_all(class_=re.compile(clase, re.I)):
                elem.decompose()
        
        # Buscar el contenedor principal del artículo
        contenido = None
        
        # Selectores específicos por sitio
        selectores_por_dominio = {
            'eldiario.es': ['.article-content', '.news-body', '[data-testid="article-body"]'],
            'elpais.com': ['.article_body', '.a_c', '.article-content'],
            'elmundo.es': ['.ue-c-article__body', '.article-body'],
            'bbc.com': ['.ssrcss-pv1rh6-ArticleWrapper', '.article-body'],
            'cnn.com': ['.article__content', '.zn-body__paragraph'],
            'reuters.com': ['.article-body__content__17Yit', '.ArticleBodyWrapper'],
        }
        
        dominio = urlparse(url).netloc.replace('www.', '')
        
        # Intentar selectores específicos del dominio
        if dominio in selectores_por_dominio:
            for selector in selectores_por_dominio[dominio]:
                try:
                    elem = soup.select_one(selector)
                    if elem and len(elem.get_text(strip=True)) > 300:
                        contenido = elem
                        print(f"   ✅ Usando selector específico para {dominio}")
                        break
                except:
                    continue
        
        # Selectores genéricos si no funcionó el específico
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
        
        # Si aún no hay contenido, buscar por densidad de párrafos
        if not contenido:
            # Encontrar el elemento con más párrafos <p>
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
            # Extraer solo párrafos de texto sustancial
            parrafos = []
            for elem in contenido.find_all(['p', 'h2', 'h3']):
                texto = elem.get_text(strip=True)
                
                # Filtrar párrafos muy cortos o que parezcan menú/publicidad
                if len(texto) < 40:
                    continue
                if any(x in texto.lower() for x in ['publicidad', 'anuncio', 'suscríbete', 
                                                     'comparte en', 'síguenos en', 'más información']):
                    continue
                # Evitar que sean puramente mayúsculas (suelen ser títulos de sección o menú)
                if texto.isupper() and len(texto) < 100:
                    continue
                
                parrafos.append(texto)
            
            # Unir párrafos con doble salto de línea para mejor legibilidad
            texto_final = '\n\n'.join(parrafos)
            
            # Limpiar metadatos residuales
            texto_final = limpiar_texto_extraccion(texto_final)
            
            # Limitar longitud razonable
            if len(texto_final) > 6000:
                texto_final = texto_final[:6000].rsplit('.', 1)[0] + '.'
            
            if len(texto_final) > 300:
                print(f"   ✅ Extraído: {len(texto_final)} caracteres, {len(parrafos)} párrafos")
                return texto_final
        
    except Exception as e:
        print(f"   ⚠️ Error: {str(e)[:60]}")
    
    return None

def generar_redaccion_profesional(titulo, texto_completo, descripcion_rss, fuente):
    """
    Genera redacción periodística profesional usando IA con el texto COMPLETO limpio
    """
    print(f"   🤖 Generando redacción profesional...")
    
    # Preparar texto para IA (limpio y ordenado)
    texto_para_ia = texto_completo[:5000] if len(texto_completo) > 5000 else texto_completo
    
    if not OPENROUTER_API_KEY:
        return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)
    
    prompt = f"""Eres un editor senior de agencia de noticias internacional.

REDACTA UNA NOTICIA PROFESIONAL para publicar en Facebook usando esta información:

TÍTULO ORIGINAL: {titulo}
FUENTE: {fuente}

TEXTO COMPLETO DE LA NOTICIA:
{texto_para_ia}

REGLAS DE REDACCIÓN:

1. Escribe en ESPAÑOL neutro y profesional
2. Estructura OBLIGATORIA:
   - PÁRRAFO 1 (Lead): Lo más importante (quién, qué, cuándo, dónde, por qué)
   - PÁRRAFO 2: Contexto y antecedentes
   - PÁRRAFO 3: Desarrollo y detalles clave
   - PÁRRAFO 4: Consecuencias o próximos pasos
3. Cada párrafo debe tener 2-4 oraciones máximo
4. Longitud total: 600-1200 caracteres
5. NO incluir: fechas de publicación, horas, nombres de fotógrafos, "ANÁLISIS", etiquetas de sección
6. NO usar corchetes ni texto entre [ ]
7. Terminar con: "Fuente: {fuente}"

FORMATO DE SALIDA (solo texto, sin etiquetas):

TÍTULO ATRACTIVO

Párrafo 1...

Párrafo 2...

Párrafo 3...

Párrafo 4...

Fuente: {fuente}"""

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
                    'temperature': 0.3,
                    'max_tokens': 1500
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    contenido = data['choices'][0]['message']['content']
                    
                    # Limpiar completamente
                    contenido = limpiar_salida_ia(contenido)
                    
                    # Verificar calidad
                    if len(contenido) > 500 and '\n\n' in contenido:
                        print(f"   ✅ Redacción: {len(contenido)} caracteres")
                        return contenido
                    else:
                        print(f"   ⚠️ Respuesta corta o mal formateada, probando otro modelo...")
                        
        except Exception as e:
            print(f"   ⚠️ Error: {str(e)[:40]}")
            continue
    
    # Fallback manual
    return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)

def limpiar_salida_ia(contenido):
    """Limpia la salida de la IA de cualquier elemento no deseado"""
    if not contenido:
        return contenido
    
    # Eliminar instrucciones y corchetes
    contenido = re.sub(r'\[.*?\]', '', contenido, flags=re.DOTALL)
    contenido = re.sub(r'\{.*?\}', '', contenido, flags=re.DOTALL)
    
    # Eliminar líneas de instrucción
    lineas_a_eliminar = [
        r'^TÍTULO ATRACTIVO$',
        r'^Párrafo \d+',
        r'^PÁRRAFO \d+',
        r'^\d+\.',
        r'^FORMATO',
        r'^REGLAS',
        r'^IMPORTANTE',
        r'^Nota:',
        r'^Notas?:',
    ]
    
    lineas = contenido.split('\n')
    lineas_limpias = []
    
    for linea in lineas:
        linea_strip = linea.strip()
        
        # Saltar líneas vacías al inicio
        if not linea_strip and not lineas_limpias:
            continue
        
        # Verificar si es línea de instrucción
        es_instruccion = False
        for patron in lineas_a_eliminar:
            if re.match(patron, linea_strip, re.IGNORECASE):
                es_instruccion = True
                break
        
        if not es_instruccion:
            lineas_limpias.append(linea_strip)
    
    # Unir y limpiar
    contenido = '\n'.join(lineas_limpias)
    contenido = re.sub(r'\n{3,}', '\n\n', contenido)
    contenido = re.sub(r'[ \t]+', ' ', contenido)
    
    # Asegurar que no termine con espacios o incompleto
    contenido = contenido.strip()
    
    return contenido

def generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente):
    """Genera redacción manual ordenada cuando la IA falla"""
    print(f"   📝 Redacción manual ordenada...")
    
    # Usar el texto ya limpio
    oraciones = [s.strip() for s in re.split(r'[.!?]+', texto_completo) 
                 if len(s.strip()) > 30 and len(s.strip()) < 300]
    
    # Si no hay suficientes, usar descripción
    if len(oraciones) < 4:
        oraciones = [s.strip() for s in re.split(r'[.!?]+', descripcion_rss) 
                     if len(s.strip()) > 20]
        oraciones.extend([s.strip() for s in re.split(r'[.!?]+', texto_completo) 
                          if len(s.strip()) > 30][:5])
    
    # Construir 4 párrafos ordenados
    parrafos = []
    
    # Párrafo 1: Lead (hecho principal)
    if len(oraciones) >= 2:
        parrafos.append(f"{oraciones[0]}. {oraciones[1]}.")
    else:
        parrafos.append(oraciones[0] if oraciones else f"Se reporta un importante acontecimiento de relevancia internacional.")
    
    # Párrafo 2: Contexto
    if len(oraciones) >= 4:
        parrafos.append(f"{oraciones[2]}. {oraciones[3]}.")
    else:
        parrafos.append("El hecho ha generado amplia repercusión en los medios de comunicación y entre la opinión pública.")
    
    # Párrafo 3: Desarrollo
    if len(oraciones) >= 6:
        parrafos.append(f"{oraciones[4]}. {oraciones[5]}.")
    else:
        parrafos.append("Las autoridades competentes continúan evaluando la situación mientras se desarrollan los hechos.")
    
    # Párrafo 4: Cierre
    if len(oraciones) >= 8:
        parrafos.append(f"{oraciones[6]}. {oraciones[7]}.")
    else:
        parrafos.append("Se esperan actualizaciones oficiales en las próximas horas sobre el desarrollo de esta información.")
    
    # Unir todo
    cuerpo = '\n\n'.join(parrafos)
    
    # Limpiar y formatear
    cuerpo = re.sub(r'\.\.+', '.', cuerpo)  # Puntos dobles
    cuerpo = re.sub(r'\s+', ' ', cuerpo)     # Espacios múltiples
    
    redaccion = f"{titulo}\n\n{cuerpo}\n\nFuente: {fuente}"
    
    print(f"   ✅ Manual: {len(redaccion)} caracteres, {len(parrafos)} párrafos")
    return redaccion

def generar_hashtags(categoria, pais, titulo):
    """Genera hashtags relevantes"""
    hashtags_categoria = {
        'politica': ['#Política', '#Gobierno'],
        'economia': ['#Economía', '#Finanzas'],
        'internacional': ['#Internacional', '#Mundo'],
        'seguridad': ['#Seguridad', '#Justicia'],
        'tecnologia': ['#Tecnología', '#Innovación'],
        'ciencia': ['#Ciencia', '#Investigación'],
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
    # Intentar media_content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('url'):
                return media['url']
    
    # Intentar enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('href') and any(x in enc.get('type', '') for x in ['image', 'jpg', 'png']):
                return enc['href']
    
    # Buscar en summary/description
    for campo in ['summary', 'description', 'content']:
        if hasattr(entry, campo):
            texto = getattr(entry, campo, '')
            if texto:
                match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', texto, re.I)
                if match:
                    return match.group(1)
    
    # Buscar en la URL de la noticia
    if url_noticia:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url_noticia, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Meta tags
            meta_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'})
            if meta_img:
                img_url = meta_img.get('content') or meta_img.get('value')
                if img_url:
                    return img_url
            
            # Imagen principal
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
    """Publica en Facebook con formato limpio y ordenado"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    # Construir mensaje final LIMPIO
    mensaje = f"""{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Verificar longitud
    if len(mensaje) > 2000:
        # Acortar manteniendo estructura
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
    
    # Preview en consola
    print(f"\n   📝 Publicación ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    lineas = mensaje.split('\n')
    for i, linea in enumerate(lineas[:8]):
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
    if len(lineas) > 8:
        print(f"   ... ({len(lineas) - 8} líneas más)")
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
    
    # NewsAPI
    if NEWS_API_KEY:
        try:
            terminos = random.sample([
                'urgente crisis', 'última hora', 'alerta internacional',
                'guerra conflicto', 'economía crisis', 'política elecciones'
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
    
    # RSS Feeds
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
    """Filtra y selecciona la mejor noticia"""
    print("\n🔎 Filtrando...")
    
    candidatas = []
    
    for noticia in noticias:
        if es_duplicado(historial, noticia['url'], noticia['titulo']):
            continue
        if len(noticia['titulo']) < 15 or "[Removed]" in noticia['titulo']:
            continue
        
        noticia['categoria'] = clasificar_categoria(noticia['titulo'], noticia['descripcion'])
        noticia['pais'] = detectar_pais(noticia['titulo'], noticia['descripcion'])
        
        candidatas.append(noticia)
        print(f"   ✅ [{noticia['categoria']}] {noticia['titulo'][:40]}... (viral: {noticia['puntaje_viral']})")
    
    if not candidatas:
        print("⚠️ No hay candidatas")
        return None
    
    candidatas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
    seleccionada = candidatas[0]
    
    print(f"\n🎯 Seleccionada: {seleccionada['titulo'][:50]}...")
    
    # Extraer texto completo limpio
    print(f"\n📄 Extrayendo contenido...")
    texto_completo = extraer_texto_completo(seleccionada['url'])
    
    if texto_completo:
        seleccionada['texto_completo'] = texto_completo
    else:
        # Limpiar descripción RSS como fallback
        desc_limpia = re.sub(r'<[^>]+>', '', seleccionada['descripcion'])
        seleccionada['texto_completo'] = limpiar_texto_extraccion(desc_limpia)
        print(f"   ⚠️ Usando descripción RSS: {len(seleccionada['texto_completo'])} caracteres")
    
    return seleccionada

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("INICIANDO PUBLICACIÓN")
    print("="*60)
    
    # 1. Cargar historial
    historial = cargar_historial()
    print(f"📚 Historial: {len(historial.get('urls', []))} noticias")
    
    # 2. Buscar noticias
    noticias = buscar_noticias()
    if not noticias:
        print("\n❌ Sin noticias")
        return False
    
    # 3. Seleccionar y extraer
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    if not seleccionada:
        print("\n❌ Sin noticias nuevas")
        return False
    
    # 4. Generar redacción profesional
    print(f"\n✍️ Redactando...")
    redaccion = generar_redaccion_profesional(
        seleccionada['titulo'],
        seleccionada['texto_completo'],
        seleccionada['descripcion'],
        seleccionada['fuente']
    )
    
    # 5. Generar hashtags
    hashtags = generar_hashtags(
        seleccionada['categoria'],
        seleccionada['pais'],
        seleccionada['titulo']
    )
    
    # 6. Descargar imagen
    print(f"\n🖼️ Descargando imagen...")
    imagen_path = descargar_imagen(seleccionada['imagen'])
    
    if not imagen_path and seleccionada.get('texto_completo'):
        # Buscar imágenes en el contenido
        urls_img = re.findall(r'https?://[^\s"\']+\.(?:jpg|jpeg|png)', seleccionada['texto_completo'])
        for url_img in urls_img[:2]:
            imagen_path = descargar_imagen(url_img)
            if imagen_path:
                break
    
    if not imagen_path:
        print("❌ Sin imagen")
        return False
    
    # 7. Publicar
    print(f"\n📤 Publicando...")
    exito = publicar_facebook(
        seleccionada['titulo'],
        redaccion,
        imagen_path,
        hashtags
    )
    
    # 8. Guardar y limpiar
    if exito:
        guardar_historial(historial, seleccionada['url'], seleccionada['titulo'])
        
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n" + "="*60)
        print("✅ ÉXITO")
        print("="*60)
        return True
    else:
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n❌ Falló")
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido")
        exit(1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
