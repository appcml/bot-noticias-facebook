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

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = os.getenv('HISTORIAL_PATH', 'historial_publicaciones.json')
ESTADO_FILE = os.getenv('ESTADO_PATH', 'estado_bot.json')  # Nuevo: control de estado

# FUENTES RSS INTERNACIONALES - EXPANDIDAS
RSS_FEEDS = [
    # Español - General
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://rss.cnn.com/rss/edition.rss',
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
    'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
    'https://elmundo.es/rss/portada.xml',
    'https://www.lavanguardia.com/mvc/feed/rss/home',
    'https://www.abc.es/rss/feeds/abc_ultima.xml',
    'https://www.publico.es/rss/',
    'https://www.europapress.es/rss/',
    # Tecnología
    'https://www.xataka.com/rss.xml',
    'https://feeds.weblogssl.com/genbeta',
    'https://www.muycomputer.com/feed/',
    # Economía
    'https://www.expansion.com/rss/portada.xml',
    'https://cincodias.elpais.com/rss/cincodias/portada.xml',
    # Deportes
    'https://as.com/rss/tags/ultimas_noticias.xml',
    'https://www.marca.com/rss/portada.xml',
    # Ciencia y Salud
    'https://www.abc.es/rss/feeds/abc_Ciencia.xml',
    'https://www.abc.es/rss/feeds/abc_Salud.xml',
]

# PALABRAS CLAVE VIRALES - EXPANDIDAS
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
    'preocupación mundial', 'breaking', 'exclusiva', 'urgente', 'alerts', 'robo', 'fraude',
    'corrupción', 'dimisión', 'renuncia', 'muere', 'fallece', 'accidente', 'tragedia',
    'rescate', 'milagro', 'récord', 'histórico', 'sin precedentes', 'bomba', 'amenaza',
    'secuestro', 'terrorismo', 'golpe de estado', 'manifestación', 'huelga', 'paro',
    'desempleo', 'subida', 'bajada', 'sube', 'baja', 'aumento', 'disminución',
]

# CATEGORÍAS CON PALABRAS CLAVE
CATEGORIAS = {
    'politica': ['gobierno', 'presidente', 'elecciones', 'congreso', 'senado', 'parlamento', 
                 'ministro', 'ley', 'reforma', 'oposición', 'partido', 'votación', 'candidato',
                 'política', 'político', 'política', 'diputado', 'senador'],
    'economia': ['economía', 'mercado', 'bolsa', 'inversión', 'banco', 'inflación', 
                 'dólar', 'empresa', 'comercio', 'finanzas', 'pérdidas', 'quiebra', 'recesión',
                 'euro', 'dinero', 'precio', 'costo', 'gasto', 'ahorro', 'crédito'],
    'internacional': ['guerra', 'conflicto', 'ataque', 'bombardeo', 'invasión', 'misil', 
                      'tensión internacional', 'diplomacia', 'acuerdo', 'tratado', 'sanciones',
                      'país', 'nación', 'extranjero', 'global', 'mundo'],
    'seguridad': ['crimen', 'asesinato', 'narcotráfico', 'detenido', 'operativo', 'policía',
                  'investigación', 'homicidio', 'robo', 'banda criminal', 'delito', 'violencia'],
    'tecnologia': ['inteligencia artificial', 'tecnología', 'innovación', 'ciberataque', 
                   'hackeo', 'digital', 'software', 'app', 'internet', 'móvil', 'ordenador'],
    'salud': ['pandemia', 'epidemia', 'virus', 'vacuna', 'brote', 'hospital', 'medicina',
              'salud', 'enfermedad', 'tratamiento', 'médico', 'sanitario'],
    'medio_ambiente': ['cambio climático', 'huracán', 'incendio', 'sequía', 'inundación',
                       'temperatura', 'calentamiento global', 'naturaleza', 'ecología'],
    'ciencia': ['descubrimiento', 'hallazgo', 'científicos', 'estudio', 'espacio', 
                'astronomía', 'planeta', 'misión espacial', 'investigación', 'ciencia'],
    'deportes': ['fútbol', 'baloncesto', 'tenis', 'deporte', 'equipo', 'jugador', 'partido',
                 'competición', 'olimpiadas', 'mundial', 'liga', 'copa'],
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

def cargar_estado():
    """Carga el estado del bot (última ejecución, contadores, etc.)"""
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'ultima_publicacion': None,
        'intentos_fallidos': 0,
        'total_publicadas': 0,
        'ultima_fuente': None
    }

def guardar_estado(estado):
    """Guarda el estado del bot"""
    try:
        os.makedirs(os.path.dirname(ESTADO_FILE) if os.path.dirname(ESTADO_FILE) else '.', exist_ok=True)
        with open(ESTADO_FILE, 'w', encoding='utf-8') as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Error guardando estado: {e}")

def cargar_historial():
    """Carga el historial de publicaciones con manejo seguro de todas las claves"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                historial = json.load(f)
                # Asegurar que todas las claves existan
                historial.setdefault('urls', [])
                historial.setdefault('titulos', [])
                historial.setdefault('hashes', [])
                historial.setdefault('ultima_publicacion', None)
                print(f"📚 Historial cargado: {len(historial['urls'])} URLs")
                return historial
        except Exception as e:
            print(f"⚠️ Error cargando historial: {e}")
    
    print("🆕 Creando historial nuevo")
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
    
    # Mantener solo las últimas 1000 entradas (aumentado para más historial)
    historial['urls'] = historial['urls'][-1000:]
    historial['titulos'] = historial['titulos'][-1000:]
    historial['hashes'] = historial['hashes'][-1000:]
    
    try:
        os.makedirs(os.path.dirname(HISTORIAL_FILE) if os.path.dirname(HISTORIAL_FILE) else '.', exist_ok=True)
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Guardada en historial")
    except Exception as e:
        print(f"⚠️ Error guardando historial: {e}")

def es_duplicado(historial, url, titulo):
    """Verifica si una noticia ya fue publicada"""
    url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()
    
    # Verificar por hash de URL
    if url_hash in historial.get('hashes', []):
        return True
    
    # Verificar por URL exacta
    if url in historial.get('urls', []):
        return True
    
    # Verificar por similitud de título (más permisivo)
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial.get('titulos', []):
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            # Usar distancia de Levenshtein simple
            coincidencias = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            similitud = coincidencias / max(len(titulo_simple), len(t_simple))
            if similitud > 0.85:  # Más estricto para evitar duplicados
                return True
    
    return False

def detectar_pais(titulo, descripcion):
    """Detecta el país de la noticia para el hashtag"""
    texto = f"{titulo} {descripcion}".lower()
    
    for pais, hashtag in PAISES.items():
        if pais in texto:
            return hashtag
    
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
            if palabra in ['urgente', 'última hora', 'crisis', 'alerta', 'guerra', 'ataque', 'breaking']:
                puntaje += 5
            elif palabra in ['confirmado', 'revelan', 'escándalo', 'polémica', 'histórico']:
                puntaje += 3
            else:
                puntaje += 1
    
    # Bonus por longitud adecuada del título
    if 40 <= len(titulo) <= 100:
        puntaje += 2
    
    return puntaje

def asegurar_puntuacion(texto):
    """Asegura que el texto termine con punto final y tenga puntuación correcta"""
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
    """Limpia el texto extraído eliminando metadatos, fechas, horas y elementos no deseados"""
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
        r'^ANÁLISIS$',
        r'^OPINIÓN$',
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
                        'imprimir', 'guardar', 'enviar', 'suscríbete', 'newsletter',
                        'cookie', 'aviso legal', 'política de privacidad', 'mapa web']
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
            'xataka.com': ['.article-content', '.article-body'],
            'genbeta.com': ['.article-content', '.article-body'],
        }
        
        dominio = urlparse(url).netloc.replace('www.', '')
        
        if dominio in selectores_por_dominio:
            for selector in selectores_por_dominio[dominio]:
                try:
                    elem = soup.select_one(selector)
                    if elem and len(elem.get_text(strip=True)) > 300:
                        contenido = elem
                        print(f"   ✅ Selector específico para {dominio}")
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
                if any(x in texto.lower() for x in ['publicidad', 'anuncio', 'suscríbete', 
                                                     'comparte en', 'síguenos en', 'más información']):
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
                print(f"   ✅ Extraído: {len(texto_final)} caracteres, {len(parrafos)} párrafos")
                return texto_final
        
    except Exception as e:
        print(f"   ⚠️ Error: {str(e)[:60]}")
    
    return None

def generar_redaccion_profesional(titulo, texto_completo, descripcion_rss, fuente):
    """Genera redacción periodística profesional usando IA con el texto COMPLETO limpio"""
    print(f"   🤖 Generando redacción profesional...")
    
    texto_para_ia = texto_completo[:5000] if len(texto_completo) > 5000 else texto_completo
    
    if not OPENROUTER_API_KEY:
        return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)
    
    prompt = f"""Eres un editor senior de agencia de noticias internacional.

REDACTA UNA NOTICIA PROFESIONAL para publicar en Facebook usando esta información:

TÍTULO ORIGINAL: {titulo}
FUENTE: {fuente}

TEXTO COMPLETO DE LA NOTICIA:
{texto_para_ia}

REGLAS DE REDACCIÓN OBLIGATORIAS:

1. Escribe en ESPAÑOL neutro y profesional
2. Estructura EXACTA con párrafos separados por líneas en blanco:

PÁRRAFO 1 (Lead): Lo más importante (quién, qué, cuándo, dónde, por qué). Mínimo 2 oraciones, máximo 3. Debe terminar con PUNTO.

PÁRRAFO 2: Contexto y antecedentes. Mínimo 2 oraciones, máximo 3. Debe terminar con PUNTO.

PÁRRAFO 3: Desarrollo y detalles clave. Mínimo 2 oraciones, máximo 3. Debe terminar con PUNTO.

PÁRRAFO 4: Consecuencias o próximos pasos. Mínimo 2 oraciones, máximo 3. Debe terminar con PUNTO.

3. CADA párrafo DEBE terminar con punto (.)
4. Entre párrafo y párrafo deja UNA línea en blanco exactamente
5. Longitud total: 600-1200 caracteres
6. NO incluir: fechas de publicación, horas, nombres de fotógrafos, "ANÁLISIS", etiquetas de sección
7. NO usar corchetes ni texto entre [ ]
8. Terminar con: "Fuente: {fuente}."

EJEMPLO DE FORMATO CORRECTO:

El gobierno de Irán anunció nuevas medidas de defensa ante los ataques recibidos. Las autoridades confirmaron que se reforzarán las instalaciones militares en todo el territorio.

La tensión en la región ha escalado desde el inicio del conflicto hace dos semanas. Diversos países han expresado su preocupación por la situación y llamado al diálogo.

Los bombardeos han afectado principalmente zonas industriales y militares. Se reportan daños significativos en infraestructura crítica del país.

Las autoridades internacionales continúan monitoreando la situación. Se esperan declaraciones oficiales en las próximas horas.

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
                        print(f"   ✅ Redacción: {len(contenido)} caracteres")
                        return contenido
                    else:
                        print(f"   ⚠️ Respuesta corta, probando otro modelo...")
                        
        except Exception as e:
            print(f"   ⚠️ Error: {str(e)[:40]}")
            continue
    
    return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)

def asegurar_puntuacion_parrafos(texto):
    """Asegura que cada párrafo termine con punto final y estén separados por líneas en blanco"""
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
        r'^TÍTULO ATRACTIVO$',
        r'^Párrafo \d+',
        r'^PÁRRAFO \d+',
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
    """Genera redacción manual ordenada con puntación correcta y párrafos separados"""
    print(f"   📝 Redacción manual ordenada...")
    
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
        p = "El hecho ha generado amplia repercusión en los medios de comunicación y entre la opinión pública."
    parrafos.append(asegurar_puntuacion(p))
    
    if len(oraciones) >= 6:
        p = f"{oraciones[4]}. {oraciones[5]}."
    else:
        p = "Las autoridades competentes continúan evaluando la situación mientras se desarrollan los hechos."
    parrafos.append(asegurar_puntuacion(p))
    
    if len(oraciones) >= 8:
        p = f"{oraciones[6]}. {oraciones[7]}."
    else:
        p = "Se esperan actualizaciones oficiales en las próximas horas sobre el desarrollo de esta información."
    parrafos.append(asegurar_puntuacion(p))
    
    cuerpo = '\n\n'.join(parrafos)
    cuerpo = re.sub(r'\.\.+', '.', cuerpo)
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
        'politica': ['#Política', '#Gobierno'],
        'economia': ['#Economía', '#Finanzas'],
        'internacional': ['#Internacional', '#Mundo'],
        'seguridad': ['#Seguridad', '#Justicia'],
        'tecnologia': ['#Tecnología', '#Innovación'],
        'ciencia': ['#Ciencia', '#Investigación'],
        'salud': ['#Salud', '#Medicina'],
        'medio_ambiente': ['#MedioAmbiente', '#Clima'],
        'deportes': ['#Deportes', '#Actualidad'],
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
    """Publica en Facebook con formato limpio, párrafos separados y ordenado"""
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
    
    print(f"\n   📝 Publicación ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    lineas = mensaje.split('\n')
    for i, linea in enumerate(lineas[:12]):
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
    if len(lineas) > 12:
        print(f"   ... ({len(lineas) - 12} líneas más)")
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

def obtener_noticias_newsapi():
    """Obtiene noticias de NewsAPI"""
    noticias = []
    if not NEWS_API_KEY:
        return noticias
    
    terminos = [
        'noticias', 'actualidad', 'mundo', 'internacional',
        'política', 'economía', 'tecnología', 'deportes'
    ]
    
    for termino in random.sample(terminos, 3):
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    'q': termino,
                    'language': 'es',
                    'sortBy': 'publishedAt',
                    'pageSize': 10,
                    'apiKey': NEWS_API_KEY
                },
                timeout=15
            )
            data = resp.json()
            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    if not art.get('title') or "[Removed]" in art['title']:
                        continue
                    noticias.append({
                        'titulo': art.get('title', ''),
                        'descripcion': art.get('description', ''),
                        'url': art.get('url', ''),
                        'imagen': art.get('urlToImage', ''),
                        'fuente': art.get('source', {}).get('name', 'Agencias'),
                        'fecha': art.get('publishedAt', ''),
                        'puntaje_viral': calcular_puntaje_viral(art.get('title', ''), art.get('description', '')),
                        'texto_completo': None,
                        'tipo': 'newsapi'
                    })
        except Exception as e:
            print(f"   ⚠️ Error NewsAPI ({termino}): {str(e)[:40]}")
            continue
    
    return noticias

def obtener_noticias_rss():
    """Obtiene noticias de feeds RSS"""
    noticias = []
    feeds_procesados = 0
    
    # Mezclar feeds para variedad
    feeds_aleatorios = RSS_FEEDS.copy()
    random.shuffle(feeds_aleatorios)
    
    for feed_url in feeds_aleatorios[:15]:  # Procesar máximo 15 feeds por ejecución
        try:
            feed = feedparser.parse(feed_url)
            fuente_nombre = feed.feed.get('title', feed_url.split('/')[2])
            
            entradas_procesadas = 0
            for entry in feed.entries[:5]:  # Máximo 5 noticias por feed
                titulo = entry.get('title', '')
                descripcion = entry.get('summary', entry.get('description', ''))
                url = entry.get('link', '')
                
                if not titulo or len(titulo) < 10 or "[Removed]" in titulo:
                    continue
                
                # Limpiar descripción de HTML
                descripcion_limpia = re.sub(r'<[^>]+>', '', descripcion)
                
                imagen = extraer_imagen(entry, url)
                puntaje = calcular_puntaje_viral(titulo, descripcion_limpia)
                
                noticias.append({
                    'titulo': titulo,
                    'descripcion': descripcion_limpia,
                    'url': url,
                    'imagen': imagen,
                    'fuente': fuente_nombre,
                    'fecha': entry.get('published', ''),
                    'puntaje_viral': puntaje,
                    'texto_completo': None,
                    'tipo': 'rss'
                })
                entradas_procesadas += 1
            
            feeds_procesados += 1
            if entradas_procesadas > 0:
                print(f"   📡 {fuente_nombre[:30]}: {entradas_procesadas} noticias")
                
        except Exception as e:
            print(f"   ⚠️ Error feed {feed_url[:30]}: {str(e)[:40]}")
            continue
    
    print(f"   ✅ Feeds procesados: {feeds_procesados}")
    return noticias

def buscar_noticias_forzado(historial, minimo_noticias=20):
    """Busca noticias de forma forzada, incluso si no son muy virales"""
    print("\n🔍 Buscando noticias (modo forzado)...")
    
    todas_noticias = []
    
    # 1. Intentar NewsAPI primero
    print("   📡 Consultando NewsAPI...")
    noticias_api = obtener_noticias_newsapi()
    todas_noticias.extend(noticias_api)
    print(f"   ✅ NewsAPI: {len(noticias_api)} noticias")
    
    # 2. Consultar RSS
    print("   📡 Consultando feeds RSS...")
    noticias_rss = obtener_noticias_rss()
    todas_noticias.extend(noticias_rss)
    print(f"   ✅ RSS total: {len(noticias_rss)} noticias")
    
    print(f"\n📊 Total recolectado: {len(todas_noticias)} noticias")
    
    # Eliminar duplicados por URL
    urls_vistas = set()
    noticias_unicas = []
    for n in todas_noticias:
        if n['url'] not in urls_vistas:
            urls_vistas.add(n['url'])
            noticias_unicas.append(n)
    
    print(f"📊 Únicas después de filtrar: {len(noticias_unicas)} noticias")
    
    # Separar en publicadas y nuevas
    nuevas = []
    ya_publicadas = []
    
    for noticia in noticias_unicas:
        if es_duplicado(historial, noticia['url'], noticia['titulo']):
            ya_publicadas.append(noticia)
        else:
            nuevas.append(noticia)
    
    print(f"   🆕 Nuevas: {len(nuevas)} | 📚 Ya publicadas: {len(ya_publicadas)}")
    
    # Si hay suficientes nuevas, usar las mejor puntuadas
    if len(nuevas) >= 3:
        nuevas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
        print(f"   🎯 Usando noticias nuevas (mejor puntuada: {nuevas[0]['puntaje_viral']} pts)")
        return nuevas[:minimo_noticias]
    
    # Si hay pocas nuevas, incluir algunas ya publicadas (rotación)
    if nuevas:
        print(f"   ⚠️ Solo {len(nuevas)} nuevas, agregando rotación...")
        # Mezclar publicadas antiguas (más de 24h)
        ahora = datetime.now()
        antiguas = []
        for p in ya_publicadas:
            # Simular antigüedad basada en puntaje más bajo
            if p['puntaje_viral'] < 3:
                antiguas.append(p)
        
        random.shuffle(antiguas)
        combinadas = nuevas + antiguas[:5]
        combinadas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
        return combinadas[:minimo_noticias]
    
    # Si no hay ninguna nueva, usar las más antiguas del historial (rotación forzada)
    print("   🔄 Rotación forzada: reutilizando noticias antiguas...")
    random.shuffle(ya_publicadas)
    return ya_publicadas[:minimo_noticias] if ya_publicadas []

def seleccionar_mejor_noticia(noticias, estado):
    """Selecciona la mejor noticia, evitando la última fuente usada"""
    if not noticias:
        return None
    
    # Filtrar por fuente diferente a la última (para variedad)
    ultima_fuente = estado.get('ultima_fuente', '')
    candidatas = [n for n in noticias if n['fuente'] != ultima_fuente]
    
    if not candidatas:
        candidatas = noticias
    
    # Ordenar por puntaje viral
    candidatas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
    
    # Seleccionar la mejor
    seleccionada = candidatas[0]
    
    return seleccionada

def procesar_y_publicar(noticia, historial, estado):
    """Procesa una noticia y la publica"""
    print(f"\n🎯 Procesando: {noticia['titulo'][:50]}...")
    
    # Clasificar
    noticia['categoria'] = clasificar_categoria(noticia['titulo'], noticia['descripcion'])
    noticia['pais'] = detectar_pais(noticia['titulo'], noticia['descripcion'])
    
    print(f"   📂 Categoría: {noticia['categoria']} | 🌍 País: {noticia['pais']}")
    
    # Extraer texto completo
    print(f"\n📄 Extrayendo contenido...")
    texto_completo = extraer_texto_completo(noticia['url'])
    
    if texto_completo:
        noticia['texto_completo'] = texto_completo
    else:
        desc_limpia = re.sub(r'<[^>]+>', '', noticia['descripcion'])
        noticia['texto_completo'] = limpiar_texto_extraccion(desc_limpia)
        print(f"   ⚠️ Usando descripción: {len(noticia['texto_completo'])} caracteres")
    
    # Generar redacción
    print(f"\n✍️ Generando redacción...")
    redaccion = generar_redaccion_profesional(
        noticia['titulo'],
        noticia['texto_completo'],
        noticia['descripcion'],
        noticia['fuente']
    )
    
    # Generar hashtags
    hashtags = generar_hashtags(
        noticia['categoria'],
        noticia['pais'],
        noticia['titulo']
    )
    
    # Procesar imagen
    print(f"\n🖼️ Procesando imagen...")
    imagen_path = None
    
    if noticia.get('imagen'):
        imagen_path = descargar_imagen(noticia['imagen'])
    
    if not imagen_path and noticia.get('texto_completo'):
        urls_img = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png)', noticia['texto_completo'])
        for url_img in urls_img[:3]:
            print(f"   Intentando imagen del texto...")
            imagen_path = descargar_imagen(url_img)
            if imagen_path:
                break
    
    if not imagen_path:
        print("   ❌ Sin imagen, buscando alternativa...")
        # Intentar con la URL de la noticia para extraer imagen
        imagen_url = extraer_imagen(type('obj', (object,), {'link': noticia['url']})(), noticia['url'])
        if imagen_url:
            imagen_path = descargar_imagen(imagen_url)
    
    if not imagen_path:
        print("❌ ERROR: No se pudo obtener imagen")
        return False
    
    print(f"   ✅ Imagen lista")
    
    # Publicar
    print(f"\n📤 Publicando en Facebook...")
    exito = publicar_facebook(
        noticia['titulo'],
        redaccion,
        imagen_path,
        hashtags
    )
    
    # Limpieza
    try:
        if imagen_path and os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        # Guardar en historial
        guardar_historial(historial, noticia['url'], noticia['titulo'])
        
        # Actualizar estado
        estado['ultima_publicacion'] = datetime.now().isoformat()
        estado['ultima_fuente'] = noticia['fuente']
        estado['total_publicadas'] = estado.get('total_publicadas', 0) + 1
        estado['intentos_fallidos'] = 0
        guardar_estado(estado)
        
        return True
    else:
        estado['intentos_fallidos'] = estado.get('intentos_fallidos', 0) + 1
        guardar_estado(estado)
        return False

def main():
    """Función principal mejorada para publicación cada 30 minutos"""
    print("\n" + "="*60)
    print("🤖 BOT DE NOTICIAS - MODO PRODUCCIÓN")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Verificar credenciales
    print(f"\n🔐 Verificando credenciales...")
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ ERROR: Faltan credenciales de Facebook")
        return False
    
    print(f"   ✅ Facebook configurado")
    print(f"   📰 NewsAPI: {'✅' if NEWS_API_KEY else '⚠️'}")
    print(f"   🤖 OpenRouter: {'✅' if OPENROUTER_API_KEY else '⚠️'}")
    
    # Cargar estado e historial
    estado = cargar_estado()
    historial = cargar_historial()
    
    print(f"\n📊 Estado actual:")
    print(f"   - Total publicadas: {estado.get('total_publicadas', 0)}")
    print(f"   - Última publicación: {estado.get('ultima_publicacion', 'Nunca')}")
    print(f"   - Intentos fallidos: {estado.get('intentos_fallidos', 0)}")
    print(f"   - Historial: {len(historial.get('urls', []))} URLs")
    
    # Verificar si ya se publicó hace menos de 25 minutos (evitar duplicados por cron)
    if estado.get('ultima_publicacion'):
        try:
            ultima = datetime.fromisoformat(estado['ultima_publicacion'])
            tiempo_transcurrido = datetime.now() - ultima
            if tiempo_transcurrido < timedelta(minutes=25):
                minutos_restantes = 30 - tiempo_transcurrido.seconds // 60
                print(f"\n⏱️ Ya se publicó hace {tiempo_transcurrido.seconds//60} minutos")
                print(f"   Esperando {minutos_restantes} minutos para siguiente publicación")
                return True  # No es error, solo no es hora aún
        except:
            pass
    
    # Buscar noticias (modo forzado para asegurar contenido)
    noticias = buscar_noticias_forzado(historial, minimo_noticias=30)
    
    if not noticias:
        print("\n❌ ERROR: No se encontraron noticias en ninguna fuente")
        estado['intentos_fallidos'] = estado.get('intentos_fallidos', 0) + 1
        guardar_estado(estado)
        return False
    
    # Seleccionar y publicar la mejor
    seleccionada = seleccionar_mejor_noticia(noticias, estado)
    
    if not seleccionada:
        print("\n❌ ERROR: No se pudo seleccionar noticia")
        return False
    
    print(f"\n📝 Noticia seleccionada:")
    print(f"   Título: {seleccionada['titulo'][:60]}...")
    print(f"   Fuente: {seleccionada['fuente']}")
    print(f"   Puntaje: {seleccionada['puntaje_viral']}")
    
    # Procesar y publicar
    exito = procesar_y_publicar(seleccionada, historial, estado)
    
    if exito:
        print("\n" + "="*60)
        print("✅ PUBLICACIÓN EXITOSA")
        print(f"📰 {seleccionada['titulo'][:50]}...")
        print(f"🏢 {seleccionada['fuente']}")
        print(f"⏰ Próxima publicación: {(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')}")
        print("="*60)
        return True
    else:
        print("\n" + "="*60)
        print("❌ FALLÓ LA PUBLICACIÓN")
        print("   Intentando con siguiente noticia...")
        
        # Intentar con la siguiente noticia
        for noticia_alt in noticias[1:3]:
            print(f"\n🔄 Intentando alternativa: {noticia_alt['titulo'][:40]}...")
            exito = procesar_y_publicar(noticia_alt, historial, estado)
            if exito:
                print("✅ Publicación alternativa exitosa")
                return True
        
        print("❌ Todas las alternativas fallaron")
        print("="*60)
        return False

if __name__ == "__main__":
    try:
        resultado = main()
        exit(0 if resultado else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por usuario")
        exit(1)
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
