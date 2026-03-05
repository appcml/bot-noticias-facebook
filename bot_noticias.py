import requests
import random
import re
import hashlib
import os
import json
from datetime import datetime
from urllib.parse import urlparse, urldefrag, quote
from PIL import Image
from io import BytesIO

# Configuración desde variables de entorno
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

print(f"🔍 DEBUG: NEWS_API_KEY presente: {bool(NEWS_API_KEY)}")
print(f"🔍 DEBUG: FB_PAGE_ID presente: {bool(FB_PAGE_ID)}")
print(f"🔍 DEBUG: FB_ACCESS_TOKEN presente: {bool(FB_ACCESS_TOKEN)}")

if not all([NEWS_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
    print("❌ ERROR: Faltan variables de entorno esenciales")
    raise ValueError("Faltan variables de entorno esenciales")

print("✅ Variables esenciales OK")

# Fuentes premium por categoría
FUENTES_PREMIUM = {
    'internacional': ['bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'aljazeera.com', 'elpais.com', 'clarin.com', 'nytimes.com', 'washingtonpost.com'],
    'economia': ['bloomberg.com', 'forbes.com', 'eleconomista.es', 'expansion.com', 'ambito.com', 'ft.com', 'wsj.com'],
    'tecnologia': ['techcrunch.com', 'theverge.com', 'wired.com', 'xataka.com', 'fayerwayer.com', 'arstechnica.com'],
    'politica': ['politico.com', 'axios.com', 'infobae.com', 'animalpolitico.com', 'reforma.com']
}

HISTORIAL_FILE = 'historial_publicaciones.json'
MAX_HISTORIAL = 1000  # Más grande para GitHub Actions

def normalizar_url(url):
    """Normaliza URL para evitar duplicados por parámetros de tracking"""
    if not url:
        return ""
    url, _ = urldefrag(url)
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        params_borrar = ['utm_', 'fbclid', 'gclid', 'ref', 'source', 'campaign', 'medium', 'content']
        query_filtrado = {k: v for k, v in query.items() 
                         if not any(p in k.lower() for p in params_borrar)}
        nuevo_query = urlencode(query_filtrado, doseq=True)
        url_limpia = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, nuevo_query, ''
        ))
        return url_limpia.lower().strip().rstrip('/')
    except:
        return url.lower().strip().rstrip('/')

def cargar_historial():
    """Carga el historial de URLs publicadas"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                urls = set(data.get('urls', []))
                hashes = set(data.get('hashes', []))  # Usar set para búsqueda rápida
                print(f"📚 Historial cargado: {len(urls)} URLs, {len(hashes)} hashes")
                return urls, hashes
        except Exception as e:
            print(f"⚠️ Error cargando historial: {e}")
            return set(), set()
    print("📚 No existe historial previo, creando nuevo")
    return set(), set()

def guardar_historial(urls, hashes):
    """Guarda el historial de URLs publicadas"""
    data = {
        'urls': list(urls)[-MAX_HISTORIAL:],
        'hashes': list(hashes)[-MAX_HISTORIAL:],
        'last_update': datetime.now().isoformat(),
        'total_guardadas': len(urls)
    }
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Historial guardado: {len(urls)} URLs totales")

# Cargar historial al inicio
HISTORIAL_URLS, HISTORIAL_HASHES = cargar_historial()

def traducir_texto(texto, idioma_origen='EN'):
    """Traduce texto usando DeepL"""
    if not DEEPL_API_KEY or idioma_origen.upper() != 'EN':
        return texto
    
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            'auth_key': DEEPL_API_KEY,
            'text': texto[:500],  # Limitar texto para evitar errores
            'source_lang': 'EN',
            'target_lang': 'ES'
        }
        response = requests.post(url, data=params, timeout=10)
        if response.status_code == 200:
            return response.json()['translations'][0]['text']
        else:
            print(f"⚠️ DeepL error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"⚠️ Error traducción: {e}")
    
    return texto

def buscar_noticias_frescas():
    print(f"\n{'='*60}")
    print(f"🔍 BUSCANDO NOTICIAS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    fecha_ayer = (datetime.now().timestamp() - 86400)
    fecha_ayer_str = datetime.fromtimestamp(fecha_ayer).strftime('%Y-%m-%d')
    fecha_hoy_str = datetime.now().strftime('%Y-%m-%d')
    
    # Búsquedas más específicas para obtener noticias frescas
    busquedas_virales = [
        ('breaking news', 'internacional'),
        ('world news today', 'internacional'),
        ('politics crisis emergency', 'politica'),
        ('economy markets stock', 'economia'),
        ('artificial intelligence AI', 'tech'),
        ('war conflict ukraine', 'crisis'),
        ('disaster earthquake hurricane', 'emergencia')
    ]
    
    # Seleccionar 3 búsquedas aleatorias para variedad
    busquedas_hoy = random.sample(busquedas_virales, min(3, len(busquedas_virales)))
    todas_noticias = []
    
    for query, categoria in busquedas_hoy:
        # Codificar query correctamente
        query_encoded = quote(query)
        
        # Buscar en español
        url_es = f"https://newsapi.org/v2/everything?q={query_encoded}&language=es&from={fecha_ayer_str}&to={fecha_hoy_str}&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}"
        
        try:
            print(f"\n📡 [{categoria.upper()}] Buscando: {query[:30]}...")
            
            response = requests.get(url_es, timeout=15)
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                for art in data['articles']:
                    if es_noticia_valida(art):
                        url_norm = normalizar_url(art['url'])
                        url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
                        
                        # Verificar DUPLICADO inmediatamente
                        if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
                            print(f"   ⏭️  YA PUBLICADA: {art['title'][:40]}...")
                            continue
                        
                        score = calcular_score(art, categoria)
                        art['categoria'] = categoria
                        art['score'] = score
                        art['url_hash'] = url_hash
                        art['url_normalizada'] = url_norm
                        art['idioma'] = 'ES'
                        todas_noticias.append(art)
                        print(f"   ✅ NUEVA: {art['title'][:50]}... (score: {score})")
            else:
                print(f"   ⚠️ API error: {data.get('message', 'Sin artículos')}")
                
        except Exception as e:
            print(f"   ❌ Error búsqueda ES: {e}")
        
        # Buscar en inglés si tenemos DeepL
        if DEEPL_API_KEY:
            url_en = f"https://newsapi.org/v2/everything?q={query_encoded}&language=en&from={fecha_ayer_str}&to={fecha_hoy_str}&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}"
            try:
                response_en = requests.get(url_en, timeout=15)
                data_en = response_en.json()
                
                if data_en.get('status') == 'ok' and data_en.get('articles'):
                    for art in data_en['articles']:
                        if es_noticia_valida(art):
                            url_norm = normalizar_url(art['url'])
                            url_hash = hashlib.md5(url_norm.encode()).hexdigest()[:16]
                            
                            # Verificar DUPLICADO
                            if url_norm in HISTORIAL_URLS or url_hash in HISTORIAL_HASHES:
                                print(f"   ⏭️  YA PUBLICADA (EN): {art['title'][:40]}...")
                                continue
                            
                            score = calcular_score(art, categoria)
                            art['categoria'] = categoria
                            art['score'] = score
                            art['url_hash'] = url_hash
                            art['url_normalizada'] = url_norm
                            art['idioma'] = 'EN'
                            art['title'] = traducir_texto(art['title'], 'EN')
                            art['description'] = traducir_texto(art['description'], 'EN')
                            todas_noticias.append(art)
                            print(f"   ✅ NUEVA (EN→ES): {art['title'][:50]}... (score: {score})")
            except Exception as e:
                print(f"   ❌ Error búsqueda EN: {e}")
    
    print(f"\n📊 Total candidatas: {len(todas_noticias)}")
    
    # Filtrar solo con imagen
    con_imagen = [n for n in todas_noticias if n.get('urlToImage') and n['urlToImage'].startswith('http')]
    print(f"📊 Con imagen: {len(con_imagen)}")
    
    # Ordenar por score
    con_imagen.sort(key=lambda x: x['score'], reverse=True)
    
    # Devolver top 5
    return con_imagen[:5]

def es_noticia_valida(art):
    """Valida que la noticia sea publicable"""
    if not art.get('title') or "[Removed]" in art['title']:
        return False
    if len(art.get('title', '')) < 15:
        return False
    if not art.get('description') or len(art['description']) < 50:
        return False
    url = art.get('url', '')
    if not url or not url.startswith('http'):
        return False
    
    # Dominios a excluir
    dominios_excluir = ['news.google', 'google.com/news', 'facebook.com', 'twitter.com', 
                       'youtube.com', 'reddit.com', 'instagram.com']
    if any(d in url.lower() for d in dominios_excluir):
        return False
    
    return True

def calcular_score(art, categoria):
    """Calcula score viral de la noticia"""
    score = 50
    texto = f"{art.get('title', '')} {art.get('description', '')}".lower()
    
    palabras_clave = {
        'breaking': 40, 'urgent': 35, 'alert': 30, 'just now': 35,
        'exclusive': 30, 'developing': 25, 'live': 25,
        'trump': 30, 'biden': 25, 'putin': 30, 'zelensky': 25,
        'war': 35, 'attack': 35, 'invasion': 35, 'missile': 30,
        'crash': 30, 'crisis': 25, 'emergency': 25,
        'dead': 30, 'killed': 35, 'dies': 30,
        'earthquake': 30, 'tsunami': 35, 'hurricane': 30,
        'market': 20, 'stocks': 20, 'economy': 20, 'inflation': 25,
        'ai': 25, 'artificial intelligence': 30, 'chatgpt': 25,
        'scandal': 30, 'resigns': 25, 'impeachment': 30
    }
    
    for palabra, puntos in palabras_clave.items():
        if palabra in texto:
            score += puntos
    
    # Bonus por fuente premium
    fuente = urlparse(art.get('url', '')).netloc.lower()
    for cat, fuentes in FUENTES_PREMIUM.items():
        if any(f in fuente for f in fuentes):
            score += 20
            break
    
    # Bonus por recencia
    try:
        fecha_pub = art.get('publishedAt', '')
        if fecha_pub:
            fecha_art = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00'))
            horas = (datetime.now().timestamp() - fecha_art.timestamp()) / 3600
            if horas < 1: score += 40
            elif horas < 3: score += 30
            elif horas < 6: score += 20
            elif horas < 12: score += 10
            else: score -= 5
    except:
        pass
    
    # Bonus por imagen
    if art.get('urlToImage'):
        score += 15
    
    return score

def detectar_tono(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    graves = ['muerte', 'muertos', 'ataque', 'guerra', 'tragedia', 'crisis', 'urgente']
    positivas = ['avance', 'descubrimiento', 'acuerdo', 'paz', 'logro', 'éxito']
    
    if any(p in texto for p in graves):
        return 'grave'
    elif any(p in texto for p in positivas):
        return 'positivo'
    else:
        return 'neutral'

def descargar_imagen(url_imagen):
    """Descarga y optimiza imagen para Facebook"""
    if not url_imagen or not url_imagen.startswith('http'):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url_imagen, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            
            # Convertir a RGB si es necesario
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionar si es muy grande (Facebook prefiere < 8MB)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            temp_path = f'/tmp/noticia_{hashlib.md5(url_imagen.encode()).hexdigest()[:8]}.jpg'
            img.save(temp_path, 'JPEG', quality=85, optimize=True)
            print(f"🖼️  Imagen descargada: {temp_path} ({os.path.getsize(temp_path)/1024:.1f} KB)")
            return temp_path
    except Exception as e:
        print(f"⚠️ Error imagen: {e}")
    
    return None

def publicar_foto_con_texto(image_path, mensaje):
    """Publica en Facebook con foto adjunta"""
    if not image_path or not os.path.exists(image_path):
        print("❌ No hay imagen para publicar")
        return False
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }
            
            print(f"📤 Subiendo a Facebook...")
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            if response.status_code == 200 and 'id' in result:
                print(f"✅ PUBLICADO EXITOSAMENTE: {result['id']}")
                return True
            else:
                error = result.get('error', {}).get('message', 'Error desconocido')
                print(f"❌ ERROR FACEBOOK: {error}")
                print(f"   Respuesta: {result}")
                return False
                
    except Exception as e:
        print(f"❌ ERROR publicando: {e}")
        return False

def generar_redaccion(noticia, categoria):
    """Genera texto de la publicación"""
    titulo = noticia['title']
    descripcion = noticia['description']
    fuente = noticia.get('source', {}).get('name', 'Medios Internacionales')
    tono = detectar_tono(titulo, descripcion)
    idioma = noticia.get('idioma', 'ES')
    
    # Extraer palabra clave del título
    palabras = [w for w in re.findall(r'\b[A-Za-zÁáÉéÍíÓóÚúÑñ]{5,}\b', titulo) 
               if w.lower() not in ['como', 'para', 'pero', 'con', 'los', 'esta']]
    palabra_destacada = random.choice(palabras) if palabras else "este desarrollo"
    
    # Plantillas por categoría y tono
    aperturas = {
        'crisis': {
            'grave': [
                f"🚨 URGENTE: La situación de {palabra_destacada} evoluciona rápidamente.",
                f"⚠️ ALERTA: Nuevos desarrollos confirman la gravedad de {palabra_destacada}.",
                f"🔴 CRISIS: La comunidad internacional reacciona ante {palabra_destacada}."
            ]
        },
        'emergencia': {
            'grave': [
                f"🆘 EMERGENCIA: Servicios de rescate responden a {palabra_destacada}.",
                f"🚨 ALERTA MÁXIMA: La magnitud de {palabra_destacada} supera expectativas."
            ]
        }
    }
    
    # Default a internacional
    cat_aperturas = aperturas.get(categoria, {
        'neutral': [
            f"🌍 Desarrollo internacional: {palabra_destacada} mantiene en vilo a observadores globales.",
            f"📰 Actualidad mundial: La situación de {palabra_destacada} genera debate internacional."
        ]
    })
    
    tono_aperturas = cat_aperturas.get(tono, cat_aperturas.get('neutral', ["Noticia internacional de última hora."]))
    apertura = random.choice(tono_aperturas)
    
    # Cuerpo del mensaje
    desarrollo = f"Fuentes internacionales confirman que la situación continúa desarrollándose. Los detalles completos se conocerán en las próximas horas."
    
    cierres = {
        'grave': ["La situación permanece fluida. Manténgase informado."],
        'positivo': ["Desarrollo positivo que continuará actualizándose."],
        'neutral': ["Seguimiento continuo de este tema internacional."]
    }
    cierre = random.choice(cierres.get(tono, cierres['neutral']))
    
    # Indicador de traducción
    header = "🌐 Noticia internacional traducida al español\n\n" if idioma == 'EN' else ""
    
    # Hashtags
    hashtags = f"#NoticiasMundiales #{datetime.now().strftime('%Y')} #{categoria.capitalize()}"
    
    mensaje = f"""{header}📰 {apertura}

{descripcion}

{desarrollo}

{cierre}

📡 Fuente: {fuente}

{hashtags}

— Verdad Hoy: Noticias Internacionales"""
    
    return mensaje

def publicar_en_facebook():
    """Función principal de publicación"""
    global HISTORIAL_URLS, HISTORIAL_HASHES
    
    print("🚀 Iniciando proceso de publicación...")
    
    # Buscar noticias
    noticias = buscar_noticias_frescas()
    
    if not noticias:
        print("⚠️ No se encontraron noticias nuevas para publicar")
        # Guardar historial igual para mantener consistencia
        guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
        return False
    
    print(f"\n🎯 Intentando publicar {len(noticias)} noticia(s) candidata(s)")
    
    # Intentar cada noticia hasta que una funcione
    for i, noticia in enumerate(noticias, 1):
        print(f"\n{'='*50}")
        print(f"📰 Intento {i}/{len(noticias)}: {noticia['title'][:60]}...")
        print(f"   Score: {noticia['score']} | Categoría: {noticia['categoria']}")
        
        # Verificar imagen
        if not noticia.get('urlToImage'):
            print("   ⏭️ Sin imagen, saltando...")
            continue
        
        # Descargar imagen
        img_path = descargar_imagen(noticia['urlToImage'])
        if not img_path:
            print("   ⏭️ Error descargando imagen, saltando...")
            continue
        
        # Generar mensaje
        mensaje = generar_redaccion(noticia, noticia['categoria'])
        
        # Publicar
        exito = publicar_foto_con_texto(img_path, mensaje)
        
        # Limpiar imagen temporal
        if os.path.exists(img_path):
            os.remove(img_path)
        
        if exito:
            # Éxito: guardar en historial
            url_norm = noticia['url_normalizada']
            url_hash = noticia['url_hash']
            HISTORIAL_URLS.add(url_norm)
            HISTORIAL_HASHES.add(url_hash)
            guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
            print(f"\n✅ PROCESO COMPLETADO - Noticia publicada y guardada")
            return True
        else:
            print(f"   ⏭️ Falló publicación, intentando siguiente...")
            continue
    
    # Si llegamos aquí, ninguna funcionó
    print("\n❌ No se pudo publicar ninguna noticia")
    guardar_historial(HISTORIAL_URLS, HISTORIAL_HASHES)
    return False

if __name__ == "__main__":
    try:
        resultado = publicar_en_facebook()
        exit(0 if resultado else 1)
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
