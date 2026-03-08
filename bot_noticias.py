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

def extraer_texto_completo(url):
    """
    Extrae el texto completo de una noticia desde su URL
    usando técnicas de scraping avanzadas
    """
    print(f"   🔍 Extrayendo texto completo de: {url[:50]}...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Eliminar elementos no deseados
        for elemento in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe', 'noscript']):
            elemento.decompose()
        
        # Intentar encontrar el contenido principal (múltiples estrategias)
        contenido = None
        
        # Estrategia 1: Buscar por clases comunes de artículos
        selectores_articulo = [
            'article',
            '[class*="article"]',
            '[class*="content"]',
            '[class*="body"]',
            '[class*="text"]',
            '[class*="news"]',
            '[class*="story"]',
            '[class*="post"]',
            'main',
            '[role="main"]',
            '.entry-content',
            '.post-content',
            '.article-content',
            '.news-content',
            '#article-body',
            '#content-body',
        ]
        
        for selector in selectores_articulo:
            try:
                elem = soup.select_one(selector)
                if elem and len(elem.get_text(strip=True)) > 500:
                    contenido = elem
                    break
            except:
                continue
        
        # Estrategia 2: Buscar el div con más párrafos
        if not contenido:
            parrafos = soup.find_all('p')
            if len(parrafos) > 5:
                # Encontrar el padre común de la mayoría de los párrafos
                padres = {}
                for p in parrafos:
                    padre = p.find_parent(['div', 'article', 'section'])
                    if padre:
                        id_padre = id(padre)
                        padres[id_padre] = padres.get(id_padre, 0) + 1
                
                if padres:
                    padre_id = max(padres, key=padres.get)
                    for p in parrafos:
                        if id(p.find_parent(['div', 'article', 'section'])) == padre_id:
                            contenido = p.find_parent(['div', 'article', 'section'])
                            break
        
        # Estrategia 3: Extraer todos los párrafos significativos
        if not contenido:
            texto_parrafos = []
            for p in soup.find_all('p'):
                texto = p.get_text(strip=True)
                # Filtrar párrafos muy cortos o que parezcan menú/navegación
                if len(texto) > 80 and not any(x in texto.lower() for x in ['cookie', 'suscríbete', 'newsletter', 'compartir', 'facebook', 'twitter']):
                    texto_parrafos.append(texto)
            
            if len(texto_parrafos) > 3:
                return '\n\n'.join(texto_parrafos[:15])  # Limitar a 15 párrafos
        
        if contenido:
            # Extraer texto limpio
            texto = contenido.get_text(separator='\n', strip=True)
            
            # Limpiar el texto
            lineas = [l.strip() for l in texto.split('\n') if l.strip()]
            texto_limpio = '\n\n'.join(lineas)
            
            # Limitar longitud razonable
            if len(texto_limpio) > 8000:
                texto_limpio = texto_limpio[:8000].rsplit('.', 1)[0] + '.'
            
            print(f"   ✅ Texto extraído: {len(texto_limpio)} caracteres, {len(lineas)} párrafos")
            return texto_limpio
        
    except Exception as e:
        print(f"   ⚠️ Error extrayendo texto: {str(e)[:60]}")
    
    return None

def generar_redaccion_profesional(titulo, texto_completo, descripcion_rss, fuente):
    """
    Genera redacción periodística profesional usando IA con el texto COMPLETO
    """
    print(f"   🤖 Generando redacción profesional con IA...")
    
    # Preparar el texto para la IA (resumir si es muy largo)
    texto_para_ia = texto_completo[:6000] if len(texto_completo) > 6000 else texto_completo
    
    if not OPENROUTER_API_KEY:
        return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)
    
    prompt = f"""Actúa como editor senior de una agencia internacional de noticias.

Tu tarea es redactar una noticia profesional para publicar en Facebook.

INFORMACIÓN DE ENTRADA:
Título original: {titulo}
Fuente: {fuente}

TEXTO COMPLETO DE LA NOTICIA:
{texto_para_ia}

INSTRUCCIONES DE REDACCIÓN:

1. Lee TODO el texto completo proporcionado.
2. Redacta una noticia en español con TODA la información importante.
3. Estructura:
   - TÍTULO: Atractivo, informativo, máximo 100 caracteres
   - LEAD: Primer párrafo con lo más importante (quién, qué, cuándo, dónde)
   - DESARROLLO: 3-4 párrafos con detalles, contexto, datos y análisis
   - CIERRE: Breve conclusión o próximos pasos

4. La noticia debe tener entre 800 y 1500 caracteres.
5. Usa párrafos cortos (2-3 oraciones cada uno).
6. Tono periodístico: objetivo, claro, profesional.
7. NO incluir enlaces ni instrucciones de formato.
8. NO usar corchetes ni etiquetas como [Párrafo 1].

FORMATO DE SALIDA:

📰 TÍTULO DE LA NOTICIA

[Lead completo]

[Párrafo de desarrollo 1]

[Párrafo de desarrollo 2]

[Párrafo de desarrollo 3]

[Cierre con fuente]

Escribe la noticia ahora:"""

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
            print(f"   🔄 Probando modelo: {modelo.split('/')[-1]}...")
            
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={
                    'model': modelo,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 2000
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    contenido = data['choices'][0]['message']['content']
                    
                    # Limpiar el contenido
                    contenido = limpiar_contenido_ia(contenido)
                    
                    # Verificar que tenga contenido sustancial
                    if len(contenido) > 600:
                        print(f"   ✅ Redacción IA: {len(contenido)} caracteres")
                        return contenido
                    else:
                        print(f"   ⚠️ Respuesta muy corta ({len(contenido)} chars), probando siguiente modelo...")
                        
        except Exception as e:
            print(f"   ⚠️ Error con {modelo}: {str(e)[:50]}")
            continue
    
    # Fallback manual con texto completo
    print("   📝 Usando redacción manual con texto completo...")
    return generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente)

def limpiar_contenido_ia(contenido):
    """Limpia el contenido generado por IA"""
    # Eliminar instrucciones y corchetes
    contenido = re.sub(r'\[.*?\]', '', contenido, flags=re.DOTALL)
    contenido = re.sub(r'Párrafo \d+:?', '', contenido, flags=re.IGNORECASE)
    contenido = re.sub(r'INSTRUCCIONES.*?(?=\n\n|\Z)', '', contenido, flags=re.DOTALL | re.IGNORECASE)
    contenido = re.sub(r'FORMATO DE SALIDA.*?(?=\n\n|\Z)', '', contenido, flags=re.DOTALL | re.IGNORECASE)
    contenido = re.sub(r'Escribe la noticia ahora:?', '', contenido, flags=re.IGNORECASE)
    
    # Limpiar espacios
    contenido = re.sub(r'\n{3,}', '\n\n', contenido)
    contenido = re.sub(r'[ \t]+', ' ', contenido)
    
    # Asegurar que empiece con 📰
    if not contenido.strip().startswith('📰'):
        contenido = f"📰 {contenido.strip()}"
    
    return contenido.strip()

def generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente):
    """Genera redacción manual cuando la IA falla, usando el texto completo"""
    print(f"   📝 Creando redacción manual desde texto completo...")
    
    # Extraer oraciones del texto completo
    oraciones = [s.strip() for s in re.split(r'[.!?]+', texto_completo) if len(s.strip()) > 40]
    
    # Si no hay suficientes oraciones, usar la descripción RSS
    if len(oraciones) < 5:
        oraciones = [s.strip() for s in re.split(r'[.!?]+', descripcion_rss) if len(s.strip()) > 20]
        oraciones.extend([s.strip() for s in re.split(r'[.!?]+', texto_completo) if len(s.strip()) > 40])
    
    # Construir párrafos
    parrafos = []
    
    # Lead: primeras 2-3 oraciones más importantes
    lead_oraciones = oraciones[:3] if len(oraciones) >= 3 else oraciones
    lead = ' '.join(lead_oraciones) + '.'
    parrafos.append(lead)
    
    # Desarrollo: agrupar oraciones en párrafos de 2-3 oraciones
    i = 3
    while i < len(oraciones) and len(parrafos) < 5:
        grupo = oraciones[i:i+3]
        if grupo:
            parrafo = ' '.join(grupo) + '.'
            # Limpiar dobles puntos
            parrafo = parrafo.replace('..', '.').replace('. .', '.')
            if len(parrafo) > 80:
                parrafos.append(parrafo)
        i += 3
    
    # Si quedó muy corto, agregar contexto
    if len(parrafos) < 3:
        parrafos.append(f"Las autoridades de {fuente} continúan monitoreando la situación. Se esperan más detalles en las próximas horas.")
    
    # Cierre
    parrafos.append(f"Fuente: {fuente}. — Verdad Hoy: Noticias al minuto")
    
    # Unir todo
    cuerpo = '\n\n'.join(parrafos)
    
    # Limitar longitud
    if len(cuerpo) > 1500:
        cuerpo = cuerpo[:1500].rsplit('.', 1)[0] + '.'
        cuerpo += f"\n\nFuente: {fuente}. — Verdad Hoy: Noticias al minuto"
    
    redaccion = f"📰 {titulo}\n\n{cuerpo}"
    
    print(f"   ✅ Redacción manual: {len(redaccion)} caracteres, {len(parrafos)} párrafos")
    return redaccion

def generar_hashtags(categoria, pais, titulo):
    """Genera hashtags relevantes para la noticia"""
    hashtags_categoria = {
        'politica': ['#Política', '#Gobierno', '#Congreso'],
        'economia': ['#Economía', '#Finanzas', '#Mercados'],
        'internacional': ['#Internacional', '#Mundo', '#Diplomacia'],
        'seguridad': ['#Seguridad', '#Justicia', '#Policiales'],
        'tecnologia': ['#Tecnología', '#Innovación', '#IA'],
        'ciencia': ['#Ciencia', '#Investigación', '#Descubrimiento'],
        'salud': ['#Salud', '#Medicina', '#Bienestar'],
        'medio_ambiente': ['#MedioAmbiente', '#Clima', '#Sostenibilidad'],
        'general': ['#Actualidad', '#Noticias', '#Información']
    }
    
    # Seleccionar hashtags de categoría
    tags = hashtags_categoria.get(categoria, hashtags_categoria['general'])[:2]
    
    # Agregar hashtag de país
    tags.append(f"#{pais}")
    
    # Hashtag viral según contenido
    titulo_lower = titulo.lower()
    if any(x in titulo_lower for x in ['urgente', 'última hora', 'alerta']):
        tags.append('#Urgente')
    elif any(x in titulo_lower for x in ['crisis', 'grave', 'crítico']):
        tags.append('#Crisis')
    else:
        tags.append('#UltimaHora')
    
    return ' '.join(tags)

def extraer_imagen(entry, url_noticia=None):
    """Extrae la imagen de una entrada RSS o de la URL de la noticia"""
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
    
    # Buscar en summary/description con regex
    for campo in ['summary', 'description', 'content']:
        if hasattr(entry, campo):
            texto = getattr(entry, campo, '')
            if texto:
                match = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"', texto, re.I)
                if match:
                    return match.group(1)
                match = re.search(r'url\(["\']?(https?://[^"\')]+\.(?:jpg|jpeg|png|gif))', texto, re.I)
                if match:
                    return match.group(1)
    
    # Si no se encontró en RSS, intentar extraer de la URL de la noticia
    if url_noticia:
        try:
            print(f"   🔍 Buscando imagen en la noticia...")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url_noticia, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Buscar meta tags de imagen
            meta_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'})
            if meta_img:
                img_url = meta_img.get('content') or meta_img.get('value')
                if img_url:
                    return img_url
            
            # Buscar imagen principal
            img = soup.find('img', class_=re.compile(r'article|main|featured|hero', re.I))
            if img and img.get('src'):
                return img['src']
                
        except Exception as e:
            print(f"   ⚠️ Error buscando imagen: {str(e)[:40]}")
    
    return None

def descargar_imagen(url):
    """Descarga una imagen temporalmente"""
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
            
            # Redimensionar si es muy grande
            img.thumbnail((1200, 1200))
            
            # Guardar temporalmente
            temp_path = f'/tmp/noticia_{hashlib.md5(url.encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85)
            return temp_path
            
    except Exception as e:
        print(f"   ⚠️ Error descargando imagen: {str(e)[:50]}")
    
    return None

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook con imagen"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales de Facebook")
        return False
    
    # Construir mensaje final
    mensaje = f"""{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Verificar longitud (límite de Facebook ~2000 caracteres)
    if len(mensaje) > 2000:
        # Acortar texto manteniendo coherencia
        exceso = len(mensaje) - 1950
        # Encontrar el último párrafo completo que quepa
        parrafos = texto.split('\n\n')
        texto_corto = ''
        for p in parrafos[:-1]:
            if len(texto_corto) + len(p) < (len(texto) - exceso - 50):
                texto_corto += p + '\n\n'
            else:
                break
        
        texto_corto = texto_corto.strip().rsplit('.', 1)[0] + "."
        mensaje = f"""{titulo}

{texto_corto}

[Continúa en la noticia completa]

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    print(f"\n   📝 Publicación ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    lineas_preview = mensaje.split('\n')[:6]
    for linea in lineas_preview:
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
    if len(mensaje.split('\n')) > 6:
        print(f"   ... ({len(mensaje.split(chr(10))) - 6} líneas más)")
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
                print(f"   ✅ PUBLICADO EXITOSAMENTE: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', str(result))
                print(f"   ❌ Error Facebook: {error}")
                
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    return False

def buscar_noticias():
    """Busca noticias en todas las fuentes RSS"""
    print("\n🔍 Buscando noticias en fuentes RSS...")
    noticias = []
    
    # También intentar NewsAPI si está disponible
    if NEWS_API_KEY:
        try:
            terminos_virales = random.sample([
                'urgente crisis', 'última hora', 'alerta internacional',
                'guerra conflicto', 'economía crisis', 'política elecciones'
            ], 2)
            
            for termino in terminos_virales:
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
                                'texto_completo': None  # Se extraerá después
                            })
                        print(f"   📡 NewsAPI '{termino}': {len(data.get('articles', []))} noticias")
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ NewsAPI error: {e}")
    
    # Procesar feeds RSS
    random.shuffle(RSS_FEEDS)
    
    for feed_url in RSS_FEEDS[:10]:  # Limitar a 10 feeds por ejecución
        try:
            feed = feedparser.parse(feed_url)
            fuente_nombre = feed.feed.get('title', feed_url.split('/')[2])
            
            for entry in feed.entries[:3]:  # Máximo 3 por feed
                titulo = entry.get('title', '')
                descripcion = entry.get('summary', entry.get('description', ''))
                url = entry.get('link', '')
                
                # Extraer imagen
                imagen = extraer_imagen(entry, url)
                
                # Calcular puntaje viral
                puntaje = calcular_puntaje_viral(titulo, descripcion)
                
                if puntaje > 0:  # Solo noticias con palabras virales
                    noticias.append({
                        'titulo': titulo,
                        'descripcion': descripcion,
                        'url': url,
                        'imagen': imagen,
                        'fuente': fuente_nombre,
                        'fecha': entry.get('published', entry.get('updated', '')),
                        'puntaje_viral': puntaje,
                        'texto_completo': None  # Se extraerá después
                    })
            
            print(f"   📡 {fuente_nombre[:25]}: {len(feed.entries)} entradas")
            
        except Exception as e:
            print(f"   ⚠️ Error en feed {feed_url[:30]}: {str(e)[:40]}")
            continue
    
    print(f"\n📊 Total noticias encontradas: {len(noticias)}")
    return noticias

def filtrar_y_seleccionar(noticias, historial):
    """Filtra duplicados y selecciona la mejor noticia"""
    print("\n🔎 Filtrando noticias...")
    
    candidatas = []
    
    for noticia in noticias:
        # Verificar duplicados
        if es_duplicado(historial, noticia['url'], noticia['titulo']):
            continue
        
        # Verificar que tenga contenido válido
        if len(noticia['titulo']) < 15 or "[Removed]" in noticia['titulo']:
            continue
        
        # Clasificar categoría
        categoria = clasificar_categoria(noticia['titulo'], noticia['descripcion'])
        noticia['categoria'] = categoria
        
        # Detectar país
        pais = detectar_pais(noticia['titulo'], noticia['descripcion'])
        noticia['pais'] = pais
        
        candidatas.append(noticia)
        print(f"   ✅ [{categoria}] {noticia['titulo'][:45]}... (viral: {noticia['puntaje_viral']})")
    
    if not candidatas:
        print("⚠️ No hay noticias candidatas")
        return None
    
    # Ordenar por puntaje viral (descendente)
    candidatas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
    
    # Seleccionar la mejor
    seleccionada = candidatas[0]
    print(f"\n🎯 Mejor candidata: {seleccionada['titulo'][:50]}...")
    
    # EXTRAER TEXTO COMPLETO AQUÍ
    print(f"\n📄 Extrayendo contenido completo...")
    texto_completo = extraer_texto_completo(seleccionada['url'])
    
    if texto_completo:
        seleccionada['texto_completo'] = texto_completo
        print(f"   ✅ Texto completo extraído: {len(texto_completo)} caracteres")
    else:
        # Usar descripción RSS como fallback
        seleccionada['texto_completo'] = seleccionada['descripcion']
        print(f"   ⚠️ Usando descripción RSS: {len(seleccionada['descripcion'])} caracteres")
    
    return seleccionada

def main():
    """Función principal del bot"""
    print("\n" + "="*60)
    print("INICIANDO CICLO DE PUBLICACIÓN")
    print("="*60)
    
    # 1. Cargar historial
    historial = cargar_historial()
    print(f"📚 Historial cargado: {len(historial.get('urls', []))} noticias publicadas")
    
    # 2. Buscar noticias
    noticias = buscar_noticias()
    
    if not noticias:
        print("\n❌ No se encontraron noticias")
        return False
    
    # 3. Filtrar, seleccionar y EXTRAER TEXTO COMPLETO
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    
    if not seleccionada:
        print("\n❌ No hay noticias nuevas para publicar")
        return False
    
    # 4. Generar redacción profesional con TEXTO COMPLETO
    print(f"\n✍️ Generando redacción profesional...")
    redaccion = generar_redaccion_profesional(
        seleccionada['titulo'],
        seleccionada['texto_completo'],
        seleccionada['descripcion'],
        seleccionada['fuente']
    )
    
    # Extraer componentes
    lineas = redaccion.split('\n')
    titulo_publicacion = lineas[0].replace('📰', '').strip() if lineas[0].startswith('📰') else seleccionada['titulo']
    
    # El cuerpo es todo excepto el título
    cuerpo = '\n'.join(lineas[1:]).strip()
    
    # Quitar firma duplicada si existe
    cuerpo = re.sub(r'\n?— Verdad Hoy:.*$', '', cuerpo).strip()
    cuerpo = re.sub(r'\n?Fuente:.*?\n?— Verdad Hoy:.*$', '', cuerpo, flags=re.DOTALL).strip()
    
    # 5. Generar hashtags
    hashtags = generar_hashtags(
        seleccionada['categoria'],
        seleccionada['pais'],
        seleccionada['titulo']
    )
    
    # 6. Descargar imagen
    print(f"\n🖼️ Descargando imagen...")
    imagen_path = descargar_imagen(seleccionada['imagen'])
    
    if not imagen_path:
        print("   ⚠️ No se pudo obtener imagen principal, intentando alternativa...")
        # Intentar buscar imagen en el contenido
        if seleccionada.get('texto_completo'):
            # Buscar URLs de imagen en el texto
            urls_img = re.findall(r'https?://[^\s"\']+\.(?:jpg|jpeg|png|gif)', seleccionada['texto_completo'])
            for url_img in urls_img[:3]:
                imagen_path = descargar_imagen(url_img)
                if imagen_path:
                    break
    
    if not imagen_path:
        print("❌ No hay imagen disponible, cancelando publicación")
        return False
    
    # 7. Publicar en Facebook
    print(f"\n📤 Publicando en Facebook...")
    exito = publicar_facebook(titulo_publicacion, cuerpo, imagen_path, hashtags)
    
    # 8. Guardar en historial si fue exitoso
    if exito:
        guardar_historial(historial, seleccionada['url'], seleccionada['titulo'])
        
        # Limpiar imagen temporal
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n" + "="*60)
        print("✅ PUBLICACIÓN COMPLETADA CON ÉXITO")
        print("="*60)
        return True
    else:
        # Limpiar imagen temporal
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n❌ La publicación falló")
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Ejecución interrumpida por usuario")
        exit(1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
