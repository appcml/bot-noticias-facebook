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
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# CARGAR HISTORIAL
historial = {'urls': [], 'titulos': [], 'ultima_publicacion': None, 'categorias': {}}

if os.path.exists(HISTORIAL_FILE):
    try:
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        print(f"📚 Historial: {len(historial['urls'])} noticias")
    except Exception as e:
        print(f"⚠️ Error historial: {e}")

def guardar_historial(url, titulo, categoria='general'):
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    if 'categorias' not in historial:
        historial['categorias'] = {}
    if categoria not in historial['categorias']:
        historial['categorias'][categoria] = []
    historial['categorias'][categoria].append(url)
    
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Historial guardado ({categoria})")
    except Exception as e:
        print(f"❌ Error guardando: {e}")

def get_url_id(url):
    url_limpia = str(url).lower().strip().rstrip('/')
    return hashlib.md5(url_limpia.encode()).hexdigest()[:16]

def ya_publicada(url, titulo):
    url_id = get_url_id(url)
    if url_id in [get_url_id(u) for u in historial['urls']]:
        return True
    
    titulo_simple = re.sub(r'[^\w]', '', titulo.lower())[:40]
    for t in historial['titulos']:
        t_simple = re.sub(r'[^\w]', '', t.lower())[:40]
        if titulo_simple and t_simple:
            coincidencia = sum(1 for a, b in zip(titulo_simple, t_simple) if a == b)
            if coincidencia / max(len(titulo_simple), len(t_simple)) > 0.7:
                return True
    return False

def detectar_categoria(titulo, descripcion):
    """Detecta la categoría de la noticia"""
    texto = f"{titulo} {descripcion}".lower()
    
    CATEGORIAS = {
        'politica': ['presidente', 'gobierno', 'ministro', 'congreso', 'senado', 'elecciones', 
                    'reforma', 'ley', 'constitución', 'parlamento', 'oposición', 'coalición'],
        'economia': ['inflación', 'economía', 'crisis', 'mercado', 'bolsa', 'inversión', 
                    'banco', 'impuestos', 'empleo', 'desempleo', 'recesión', 'deuda'],
        'mundo': ['conflicto', 'diplomacia', 'guerra', 'tensión', 'ataque', 'bombardeo', 
                 'misil', 'ejército', 'invasión', 'frontera', 'embajada'],
        'deportes': ['fútbol', 'liga', 'campeonato', 'mundial', 'partido', 'jugador', 
                    'equipo', 'entrenador', 'victoria', 'derrota', 'gol', 'competición']
    }
    
    puntuaciones = {}
    for cat, keywords in CATEGORIAS.items():
        score = sum(1 for k in keywords if k in texto)
        puntuaciones[cat] = score
    
    if max(puntuaciones.values()) > 0:
        return max(puntuaciones, key=puntuaciones.get)
    return 'general'

def limpiar_texto(texto):
    """Limpia el texto de URLs, HTML y espacios extra"""
    if not texto:
        return ""
    
    # Eliminar URLs
    texto = re.sub(r'http[s]?://\S+', '', texto)
    # Eliminar HTML
    texto = re.sub(r'<[^>]+>', '', texto)
    # Eliminar caracteres especiales raros
    texto = re.sub(r'[^\w\s.,;:!?áéíóúÁÉÍÓÚñÑüÜ\-]', ' ', texto)
    # Eliminar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return texto

def extraer_info_clave(titulo, descripcion):
    """Extrae información clave para crear una redacción original"""
    texto_completo = f"{titulo}. {descripcion}"
    texto_limpio = limpiar_texto(texto_completo)
    
    # Dividir en oraciones
    oraciones = [s.strip() for s in texto_limpio.split('.') if len(s.strip()) > 10]
    
    # Extraer sujeto/actor principal (palabras mayúsculas al inicio)
    actores = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', texto_limpio)
    actor_principal = actores[0] if actores else "Las autoridades"
    
    # Extraer acción principal (verbos clave)
    acciones = ['acuerdan', 'anuncian', 'confirman', 'reportan', 'destacan', 'indican', 
                'señalan', 'advierten', 'revelan', 'acusan', 'denuncian']
    accion = next((a for a in acciones if a in texto_limpio.lower()), "informan")
    
    # Extraer tema principal
    temas = ['relaciones diplomáticas', 'crisis económica', 'conflicto armado', 
             'elecciones', 'acuerdo comercial', 'sanciones', 'investigación']
    tema = next((t for t in temas if t in texto_limpio.lower()), "un importante acontecimiento")
    
    return {
        'actor': actor_principal,
        'accion': accion,
        'tema': tema,
        'oraciones': oraciones[:3]  # Primeras 3 oraciones como base
    }

def generar_redaccion_limpia(titulo, descripcion, fuente, categoria):
    """
    Genera una redacción periodística LIMPIA y PROFESIONAL.
    Sin repeticiones, sin texto amontonado, estructura clara.
    """
    
    print(f"\n   📝 Procesando: {titulo[:50]}...")
    print(f"   🏷️ Categoría: {categoria}")
    
    # Limpiar entrada
    titulo_limpio = limpiar_texto(titulo)
    desc_limpia = limpiar_texto(descripcion)
    
    # Extraer información clave
    info = extraer_info_clave(titulo_limpio, desc_limpia)
    
    # Si tenemos IA, usarla para generar texto limpio
    if OPENROUTER_API_KEY:
        resultado = generar_con_ia_limpio(titulo_limpio, desc_limpia, fuente, categoria, info)
        if resultado and len(resultado['texto']) > 800:
            return resultado
    
    # Generar redacción limpia manualmente
    return redaccion_manual_limpia(titulo_limpio, desc_limpia, fuente, categoria, info)

def generar_con_ia_limpio(titulo, descripcion, fuente, categoria, info):
    """Genera texto limpio usando IA"""
    try:
        prompt = f"""Eres un redactor de agencia EFE. Escribe una NOTICIA LIMPIA y PROFESIONAL.

DATOS BRUTOS:
Título: {titulo}
Descripción: {descripcion}
Fuente: {fuente}
Actor: {info['actor']}
Tema: {info['tema']}

REGLAS ESTRICTAS PARA TEXTO LIMPIO:
1. TITULAR: Máximo 80 caracteres, informativo, sin repeticiones
2. ESTRUCTURA EXACTA (5 párrafos separados por línea en blanco):
   
   P1 - LEAD (2 oraciones): Quién + Qué + Cuándo. Máx 140 caracteres.
   
   P2 - CONTEXTO (2 oraciones): Antecedentes o situación previa.
   
   P3 - DESARROLLO (2 oraciones): Datos específicos, cifras, reacciones.
   
   P4 - ANÁLISIS (2 oraciones): Implicaciones o consecuencias.
   
   P5 - CIERRE (1 oración): Próximo paso + "Fuente: {fuente}"

3. REGLAS DE LIMPIEZA:
   - NUNCA repitas frases o ideas
   - Cada párrafo debe decir algo DIFERENTE
   - Oraciones cortas y claras (máx 25 palabras)
   - Sin adjetivos innecesarios
   - Solo hechos, sin relleno
   - Termina CADA oración en punto

4. PROHIBIDO:
   - "Los detalles serán proporcionados oportunamente" (frase genérica)
   - "Se esperan actualizaciones" (frase genérica)
   - Repetir el mismo concepto en diferentes párrafos
   - Texto amontonado sin espacios

FORMATO (respetar saltos de línea):
TITULAR: [titular]

P1: [lead]

P2: [contexto]

P3: [desarrollo]

P4: [análisis]

P5: [cierre]

FIN"""

        modelos = [
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free"
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
                        'temperature': 0.2,
                        'max_tokens': 1200
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        
                        # Extraer y limpiar
                        titular = extraer_linea(content, 'TITULAR:', 'P1:')
                        p1 = extraer_linea(content, 'P1:', 'P2:')
                        p2 = extraer_linea(content, 'P2:', 'P3:')
                        p3 = extraer_linea(content, 'P3:', 'P4:')
                        p4 = extraer_linea(content, 'P4:', 'P5:')
                        p5 = extraer_linea(content, 'P5:', 'FIN')
                        
                        # Limpiar cada párrafo
                        titular = limpiar_parrafo(titular) or titulo[:80]
                        p1 = limpiar_parrafo(p1)
                        p2 = limpiar_parrafo(p2)
                        p3 = limpiar_parrafo(p3)
                        p4 = limpiar_parrafo(p4)
                        p5 = limpiar_parrafo(p5) or f"Fuente: {fuente}."
                        
                        # Verificar que no haya repeticiones
                        parrafos = [p for p in [p1, p2, p3, p4, p5] if p and len(p) > 20]
                        
                        if len(parrafos) >= 4:
                            # Unir con doble salto de línea
                            texto_final = '\n\n'.join(parrafos)
                            
                            # Verificar que no esté repetido
                            if not hay_repeticiones(texto_final):
                                print(f"   ✅ IA generó texto limpio: {len(texto_final)} caracteres")
                                return {
                                    'titular': titular[:100],
                                    'texto': texto_final[:1900]
                                }
                            
            except Exception as e:
                print(f"   ⚠️ Error {modelo}: {e}")
                continue
                
    except Exception as e:
        print(f"   ⚠️ Error IA: {e}")
    
    return None

def extraer_linea(texto, inicio, fin):
    """Extrae una línea/párrafo específico"""
    try:
        if inicio in texto:
            parte = texto.split(inicio)[1]
            if fin in parte:
                resultado = parte.split(fin)[0].strip()
                # Tomar solo la primera línea si hay múltiples
                return resultado.split('\n')[0].strip()
            return parte.strip()[:300]
    except:
        pass
    return ""

def limpiar_parrafo(texto):
    """Limpia un párrafo individual"""
    if not texto:
        return ""
    
    # Eliminar prefijos como "P1:", "P2:", etc.
    texto = re.sub(r'^P\d+:\s*', '', texto)
    
    # Eliminar espacios extra
    texto = texto.strip()
    
    # Asegurar punto final
    if texto and not texto.endswith(('.', '!', '?')):
        texto += "."
    
    return texto

def hay_repeticiones(texto):
    """Detecta si hay frases repetidas en el texto"""
    oraciones = [s.strip().lower() for s in texto.split('.') if len(s.strip()) > 15]
    
    # Buscar frases similares
    for i, oracion1 in enumerate(oraciones):
        for j, oracion2 in enumerate(oraciones):
            if i != j:
                # Si comparten más del 70% de palabras
                palabras1 = set(oracion1.split())
                palabras2 = set(oracion2.split())
                if len(palabras1) > 5 and len(palabras2) > 5:
                    interseccion = palabras1.intersection(palabras2)
                    union = palabras1.union(palabras2)
                    if len(interseccion) / len(union) > 0.7:
                        return True
    
    return False

def redaccion_manual_limpia(titulo, descripcion, fuente, categoria, info):
    """Genera redacción limpia manualmente sin repeticiones"""
    print(f"   📝 Generando redacción manual limpia...")
    
    # Crear TITULAR limpio
    titular = crear_titular_limpio(titulo, info, categoria)
    
    # Crear 5 párrafos distintos, sin repeticiones
    parrafos = crear_parrafos_distintos(info, descripcion, fuente, categoria)
    
    # Unir con doble salto de línea
    texto_final = '\n\n'.join(parrafos)
    
    # Verificar longitud
    if len(texto_final) < 800:
        # Agregar párrafo adicional si es muy corto
        parrafo_extra = f"Los expertos consultados destacan la relevancia de este acontecimiento en el contexto {categoria} actual."
        parrafos.insert(-1, parrafo_extra)
        texto_final = '\n\n'.join(parrafos)
    
    print(f"   ✅ Redacción limpia: {len(texto_final)} caracteres, {len(parrafos)} párrafos")
    return {
        'titular': titular[:100],
        'texto': texto_final[:1900]
    }

def crear_titular_limpio(titulo, info, categoria):
    """Crea un titular limpio y profesional"""
    # Usar el titulo original si es bueno
    titulo_limpio = limpiar_texto(titulo)
    
    if len(titulo_limpio) > 20 and len(titulo_limpio) < 90:
        return titulo_limpio
    
    # Crear titular genérico profesional
    titulares_categoria = {
        'politica': f"{info['actor']} anuncia {info['tema']} en nuevo acuerdo",
        'economia': f"Nuevo indicador económico marca tendencia en {info['tema']}",
        'mundo': f"Desarrollo internacional: {info['actor']} confirma {info['tema']}",
        'deportes': f"Resultado importante: {info['actor']} destaca en competición"
    }
    
    return titulares_categoria.get(categoria, f"Nuevo acontecimiento: {info['tema']}")

def crear_parrafos_distintos(info, descripcion, fuente, categoria):
    """Crea 5 párrafos distintos sin repeticiones"""
    
    # P1: LEAD - El hecho principal
    if info['oraciones']:
        p1 = f"{info['oraciones'][0]}."
        if len(p1) < 100 and len(info['oraciones']) > 1:
            p1 += f" {info['oraciones'][1]}."
    else:
        p1 = f"{info['actor']} confirmó {info['tema']} en las últimas horas."
    
    # P2: CONTEXTO - Antecedentes (diferente a P1)
    contextos = {
        'politica': "El anuncio se produce en el marco de las negociaciones institucionales vigentes. Las partes involucradas mantenían conversaciones previas sobre este tema.",
        'economia': "El indicador refleja la tendencia observada durante el último trimestre. Los mercados habían anticipado movimientos en esta dirección.",
        'mundo': "La situación se enmarca en las relaciones bilaterales de los últimos meses. Ambas partes habían expresado interés en avanzar sobre este punto.",
        'deportes': "El encuentro forma parte de la competición regular de la temporada. Ambos equipos llegaban con expectativas diferentes al enfrentamiento."
    }
    p2 = contextos.get(categoria, "El acontecimiento se produce en un contexto de desarrollos recientes. Las partes habían mostrado posiciones previas sobre el tema.")
    
    # P3: DESARROLLO - Datos específicos (diferente a P1 y P2)
    desarrollos = {
        'politica': "Los detalles del acuerdo incluyen plazos específicos para su implementación. Los documentos firmados establecen responsabilidades claras para cada parte.",
        'economia': "Las cifras presentadas muestran variación respecto al período anterior. Los analistas comparan los datos con las proyecciones iniciales del ejercicio.",
        'mundo': "Las acciones concretas se desarrollarán en las próximas semanas según el calendario establecido. Los observadores internacionales seguirán de cerca los avances.",
        'deportes': "Las estadísticas del encuentro reflejan el desarrollo del marcador. Los jugadores destacados fueron clave en el resultado final del partido."
    }
    p3 = desarrollos.get(categoria, "Los detalles específicos se conocerán en los próximos días. Los involucrados preparan los pasos siguientes según lo acordado.")
    
    # P4: ANÁLISIS - Perspectiva (diferente a los anteriores)
    analisis = {
        'politica': "Los analistas políticos evalúan el impacto de este acuerdo en la agenda gubernamental. Las implicaciones legislativas dependerán de los trámites parlamentarios.",
        'economia': "Los especialistas financieros analizan la sostenibilidad de esta tendencia. Los inversores ajustarán sus estrategias según los datos confirmados.",
        'mundo': "Los expertos en relaciones internacionales observan las reacciones de otros actores globales. La estabilidad regional podría verse afectada por estos desarrollos.",
        'deportes': "Los comentaristas destacan la importancia de este resultado para la clasificación. El rendimiento del equipo será clave en los próximos encuentros."
    }
    p4 = analisis.get(categoria, "Los observadores destacan la trascendencia de este acontecimiento. Las consecuencias a mediano plazo dependerán de los desarrollos siguientes.")
    
    # P5: CIERRE - Conclusión (diferente a todos)
    p5 = f"Las autoridades competentes continuarán informando sobre los avances. Fuente: {fuente}."
    
    # Limpiar y retornar
    return [
        limpiar_parrafo(p1),
        limpiar_parrafo(p2),
        limpiar_parrafo(p3),
        limpiar_parrafo(p4),
        limpiar_parrafo(p5)
    ]

def buscar_noticias():
    """Busca noticias de fuentes confiables"""
    print("\n🔍 Buscando noticias...")
    noticias = []
    
    # NewsAPI en español
    if NEWS_API_KEY:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={'country': 'us', 'category': 'general', 'pageSize': 15, 'apiKey': NEWS_API_KEY},
                timeout=15
            )
            data = resp.json()
            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    cat = detectar_categoria(art.get('title', ''), art.get('description', ''))
                    art['categoria_detectada'] = cat
                    noticias.append(art)
                print(f"   📡 NewsAPI: {len(data.get('articles', []))}")
        except Exception as e:
            print(f"   ⚠️ NewsAPI: {e}")
    
    # GNews
    if GNEWS_API_KEY and len(noticias) < 5:
        try:
            resp = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={'lang': 'en', 'max': 15, 'apikey': GNEWS_API_KEY},
                timeout=15
            )
            data = resp.json()
            if 'articles' in data:
                for a in data['articles']:
                    cat = detectar_categoria(a.get('title', ''), a.get('description', ''))
                    noticias.append({
                        'title': a.get('title'),
                        'description': a.get('description'),
                        'url': a.get('url'),
                        'urlToImage': a.get('image'),
                        'source': {'name': a.get('source', {}).get('name', 'GNews')},
                        'categoria_detectada': cat
                    })
                print(f"   📡 GNews: {len(data['articles'])}")
        except Exception as e:
            print(f"   ⚠️ GNews: {e}")
    
    # RSS internacionales
    rss_feeds = [
        'http://feeds.bbci.co.uk/news/world/rss.xml',
        'https://www.reuters.com/rssFeed/worldNews',
        'https://rss.cnn.com/rss/edition_world.rss'
    ]
    
    for feed_url in random.sample(rss_feeds, min(2, len(rss_feeds))):
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                img = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    img = entry.media_content[0].get('url', '')
                elif 'summary' in entry:
                    m = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png))"', entry.summary, re.I)
                    if m:
                        img = m.group(1)
                
                cat = detectar_categoria(entry.get('title', ''), entry.get('summary', ''))
                noticias.append({
                    'title': entry.get('title'),
                    'description': entry.get('summary', entry.get('description', ''))[:400],
                    'url': entry.get('link'),
                    'urlToImage': img,
                    'source': {'name': feed.feed.get('title', 'RSS')},
                    'categoria_detectada': cat
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
        if ya_publicada(art['url'], art['title']):
            continue
        
        cat = art.get('categoria_detectada', 'general')
        art['prioridad'] = 2 if cat in ['politica', 'economia', 'mundo'] else 1
        nuevas.append(art)
        print(f"   ✅ [{cat}] {art['title'][:45]}...")
    
    nuevas.sort(key=lambda x: x.get('prioridad', 0), reverse=True)
    print(f"📊 Nuevas: {len(nuevas)}")
    return nuevas[:3]

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

def publicar(titulo, texto, img_path, categoria):
    """Publica en Facebook con formato limpio"""
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales Facebook")
        return False
    
    # Limpiar entrada
    titulo = limpiar_texto(titulo)
    texto = limpiar_texto(texto)
    
    # Hashtags
    hashtags_map = {
        'politica': '#Política #Gobierno #Actualidad',
        'economia': '#Economía #Finanzas #Negocios',
        'mundo': '#Internacional #Mundo #Noticias',
        'deportes': '#Deportes #Fútbol #Competición',
        'seguridad': '#Seguridad #Justicia',
        'tecnologia': '#Tecnología #Innovación',
        'salud': '#Salud #Medicina',
        'medio_ambiente': '#MedioAmbiente',
        'ciencia': '#Ciencia #Investigación',
        'tendencias': '#Viral #Tendencias'
    }
    
    hashtags = hashtags_map.get(categoria, '#Noticias #Actualidad')
    
    # Construir mensaje con espacios limpios
    mensaje = f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto"""
    
    # Preview limpio
    print(f"\n   📝 MENSAJE ({len(mensaje)} caracteres):")
    print(f"   {'='*50}")
    for linea in mensaje.split('\n')[:12]:
        if linea.strip() == '':
            print(f"   [espacio]")
        else:
            preview = linea[:65] + "..." if len(linea) > 65 else linea
            print(f"   {preview}")
    print(f"   {'='*50}")
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"   📤 Publicando...")
        
        with open(img_path, 'rb') as f:
            resp = requests.post(
                url,
                files={'file': f},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
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

def main():
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ Faltan credenciales de Facebook")
        return False
    
    noticias = buscar_noticias()
    
    if not noticias:
        print("⚠️ No hay noticias nuevas")
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
        
        categoria = noticia.get('categoria_detectada', 'general')
        
        resultado = generar_redaccion_limpia(
            noticia['title'],
            noticia.get('description', ''),
            noticia.get('source', {}).get('name', 'Agencias'),
            categoria
        )
        
        if publicar(resultado['titular'], resultado['texto'], img_path, categoria):
            guardar_historial(noticia['url'], noticia['title'], categoria)
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
