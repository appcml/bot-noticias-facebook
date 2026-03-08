import requests
import feedparser
import re
import hashlib
import json
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup

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

def generar_redaccion_profesional(titulo, descripcion, fuente):
    """Genera redacción periodística profesional usando IA"""
    print(f"   🤖 Generando redacción con IA...")
    
    if not OPENROUTER_API_KEY:
        return generar_redaccion_manual(titulo, descripcion, fuente)
    
    prompt = f"""Actúa como editor profesional de noticias en español.

Tu tarea es tomar el contenido de una noticia real y reorganizarlo para publicarlo en redes sociales.

Reglas:
1. El texto debe estar completamente en español.
2. La primera línea debe ser el título completo de la noticia.
3. Luego escribir entre 3 y 5 párrafos claros que expliquen la noticia.
4. Cada párrafo debe tener 2 o 3 frases.
5. El texto debe ser informativo y neutral.
6. No incluir enlaces.
7. No cortar el título original.
8. No inventar información.
9. Mantener el sentido original de la noticia.

DATOS DE ENTRADA:
Título: {titulo}
Descripción: {descripcion}
Fuente: {fuente}

Formato final requerido:
📰 TITULO COMPLETO

Párrafo 1

Párrafo 2

Párrafo 3

#Noticias #Actualidad #UltimaHora #Mundo

Fuente: {fuente}
— Verdad Hoy: Noticias al minuto

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
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={
                    'model': modelo,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.4,
                    'max_tokens': 1500
                },
                timeout=90
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    contenido = data['choices'][0]['message']['content']
                    
                    # Limpiar el contenido
                    contenido = limpiar_contenido_ia(contenido)
                    
                    if len(contenido) > 400:
                        print(f"   ✅ Redacción generada: {len(contenido)} caracteres")
                        return contenido
                        
        except Exception as e:
            print(f"   ⚠️ Error con {modelo}: {str(e)[:40]}")
            continue
    
    # Fallback manual
    return generar_redaccion_manual(titulo, descripcion, fuente)

def limpiar_contenido_ia(contenido):
    """Limpia el contenido generado por IA"""
    # Eliminar instrucciones y corchetes
    contenido = re.sub(r'\[.*?\]', '', contenido, flags=re.DOTALL)
    contenido = re.sub(r'Párrafo \d+:?', '', contenido, flags=re.IGNORECASE)
    contenido = re.sub(r'Reglas?:?', '', contenido, flags=re.IGNORECASE)
    contenido = re.sub(r'Datos de entrada:?', '', contenido, flags=re.IGNORECASE)
    contenido = re.sub(r'Formato final requerido:?', '', contenido, flags=re.IGNORECASE)
    
    # Limpiar espacios
    contenido = re.sub(r'\n{3,}', '\n\n', contenido)
    contenido = re.sub(r'[ \t]+', ' ', contenido)
    
    return contenido.strip()

def generar_redaccion_manual(titulo, descripcion, fuente):
    """Genera redacción manual cuando la IA falla"""
    print(f"   📝 Usando redacción manual...")
    
    # Limpiar descripción
    desc_limpia = re.sub(r'<[^>]+>', '', descripcion)
    oraciones = [s.strip() for s in desc_limpia.split('.') if len(s.strip()) > 20]
    
    # Construir párrafos
    if len(oraciones) >= 3:
        parrafo1 = f"{oraciones[0]}. {oraciones[1]}."
        parrafo2 = f"{oraciones[2]}." + (f" {oraciones[3]}." if len(oraciones) > 3 else "")
        parrafo3 = f"La información continúa desarrollándose. {oraciones[-1] if len(oraciones) > 4 else 'Se esperan actualizaciones oficiales en las próximas horas.'}"
    elif len(oraciones) == 2:
        parrafo1 = f"{oraciones[0]}."
        parrafo2 = f"{oraciones[1]}. Las autoridades competentes confirmaron la información."
        parrafo3 = "Se esperan actualizaciones oficiales en las próximas horas."
    else:
        parrafo1 = f"Se reporta un importante acontecimiento de relevancia internacional."
        parrafo2 = f"Las autoridades confirmaron la información en las últimas horas."
        parrafo3 = "Se esperan actualizaciones oficiales sobre el desarrollo de los hechos."
    
    # Asegurar longitud adecuada
    while len(parrafo1) < 80 and len(oraciones) > 2:
        parrafo1 += f" {oraciones[2]}."
        break
    
    redaccion = f"""📰 {titulo}

{parrafo1}

{parrafo2}

{parrafo3}

Fuente: {fuente}
— Verdad Hoy: Noticias al minuto"""
    
    print(f"   ✅ Redacción manual: {len(redaccion)} caracteres")
    return redaccion

def generar_hashtags(categoria, pais, titulo):
    """Genera hashtags relevantes para la noticia"""
    hashtags_categoria = {
        'politica': ['#Política', '#Gobierno', '#Congreso'],
        'economia': ['#Economía', '#Finanzas', '#Mercados'],
        'internacional': ['#Internacional', '#Mundo', '#Diplomacia'],
        'guerra_defensa': ['#Conflicto', '#Defensa', '#Seguridad'],
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

def extraer_imagen(entry):
    """Extrae la imagen de una entrada RSS"""
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
    mensaje = f"""{titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Verificar longitud (límite de Facebook ~2000 caracteres)
    if len(mensaje) > 2000:
        # Acortar texto manteniendo coherencia
        exceso = len(mensaje) - 1950
        texto_corto = texto[:-exceso-10].rsplit('.', 1)[0] + "."
        mensaje = f"""{titulo}

{texto_corto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    print(f"\n   📝 Publicación ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:5]:
        preview = linea[:55] + "..." if len(linea) > 55 else linea
        print(f"   {preview}")
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
                                'puntaje_viral': calcular_puntaje_viral(art.get('title', ''), art.get('description', ''))
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
                imagen = extraer_imagen(entry)
                
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
                        'puntaje_viral': puntaje
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
    
    print(f"\n🎯 Mejor candidata: {candidatas[0]['titulo'][:50]}...")
    return candidatas[0]

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
    
    # 3. Filtrar y seleccionar
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    
    if not seleccionada:
        print("\n❌ No hay noticias nuevas para publicar")
        return False
    
    # 4. Generar redacción
    print(f"\n✍️ Generando redacción profesional...")
    redaccion = generar_redaccion_profesional(
        seleccionada['titulo'],
        seleccionada['descripcion'],
        seleccionada['fuente']
    )
    
    # Extraer título del formato 📰 TITULO
    titulo_match = re.search(r'📰\s*(.+?)\n', redaccion)
    if titulo_match:
        titulo_publicacion = titulo_match.group(1).strip()
        # El resto es el cuerpo
        cuerpo = re.sub(r'📰\s*.+?\n', '', redaccion, count=1).strip()
        # Quitar firma y hashtags del cuerpo para manejarlos separado
        cuerpo = re.sub(r'\n?Fuente:.*?\n?— Verdad Hoy:.*$', '', cuerpo, flags=re.DOTALL).strip()
        cuerpo = re.sub(r'\n?#Noticias.*$', '', cuerpo, flags=re.DOTALL).strip()
    else:
        titulo_publicacion = seleccionada['titulo']
        cuerpo = redaccion
    
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
        print("   ⚠️ No se pudo obtener imagen, intentando búsqueda alternativa...")
        # Intentar con placeholder o buscar en el contenido
        imagen_path = None
    
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

