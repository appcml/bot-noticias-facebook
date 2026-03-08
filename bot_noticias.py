import requests
import feedparser
import re
import hashlib
import json
import os
import random
from datetime import datetime, timedelta  # ← Agregado timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

# FUENTES RSS INTERNACIONALES - CORREGIDO: Eliminados espacios al final
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

# ... (PALABRAS_CLAVE_VIRALES, CATEGORIAS, PAISES se mantienen igual) ...

print("="*60)
print("🚀 BOT DE NOTICIAS - Verdad Hoy")
print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

def cargar_historial():
    """Carga el historial de publicaciones"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Asegurar que exista la clave 'hashes'
                if 'hashes' not in data:
                    data['hashes'] = []
                    # Generar hashes de URLs existentes
                    for url in data.get('urls', []):
                        url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()[:16]
                        data['hashes'].append(url_hash)
                return data
        except Exception as e:
            print(f"⚠️ Error cargando historial: {e}")
            pass
    return {'urls': [], 'titulos': [], 'hashes': [], 'ultima_publicacion': None}  # ← Agregado 'hashes'

def guardar_historial(historial, url, titulo):
    """Guarda una noticia en el historial - CORREGIDO"""
    # Generar hash de la URL
    url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()[:16]
    
    # Agregar a todas las listas
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['hashes'].append(url_hash)  # ← Nuevo: guardar hash
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    # Mantener solo últimas 500 entradas
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    historial['hashes'] = historial['hashes'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Guardada en historial: {url[:60]}...")
    except Exception as e:
        print(f"⚠️ Error guardando historial: {e}")

def es_duplicado(historial, url, titulo):
    """Verifica si una noticia ya fue publicada - CORREGIDO: Más estricto"""
    url_normalizada = url.lower().strip()
    url_hash = hashlib.md5(url_normalizada.encode()).hexdigest()[:16]
    
    # ← CORREGIDO: Verificar primero en hashes (más rápido y confiable)
    if url_hash in historial.get('hashes', []):
        print(f"   ⚠️ Duplicado por hash: {url[:50]}...")
        return True
    
    # Verificación adicional por URL exacta (backup)
    for url_guardada in historial.get('urls', []):
        if url_normalizada == url_guardada.lower().strip():
            print(f"   ⚠️ Duplicado por URL exacta")
            return True
    
    # ← CORREGIDO: Verificación de título más estricta (85% en vez de 75%)
    titulo_normalizado = re.sub(r'[^\w\s]', '', titulo.lower()).strip()
    palabras_titulo = set(titulo_normalizado.split())
    
    for titulo_guardado in historial.get('titulos', []):
        titulo_g_normalizado = re.sub(r'[^\w\s]', '', titulo_guardado.lower()).strip()
        palabras_guardadas = set(titulo_g_normalizado.split())
        
        if palabras_titulo and palabras_guardadas:
            # Calcular similitud de Jaccard
            interseccion = len(palabras_titulo & palabras_guardadas)
            union = len(palabras_titulo | palabras_guardadas)
            similitud = interseccion / union if union > 0 else 0
            
            if similitud > 0.85:  # ← Más estricto: 85% en vez de 75%
                print(f"   ⚠️ Duplicado por título similar ({similitud:.0%}): '{titulo[:40]}...'")
                return True
    
    return False

def verificar_tiempo_ultima_publicacion(historial):
    """← NUEVA FUNCIÓN: Verifica si pasaron 30 minutos desde la última publicación"""
    ultima = historial.get('ultima_publicacion')
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        ahora = datetime.now()
        diferencia = ahora - ultima_dt
        
        minutos_pasados = diferencia.total_seconds() / 60
        
        if minutos_pasados < 30:
            minutos_restantes = 30 - minutos_pasados
            print(f"⏰ Esperando... Última publicación hace {minutos_pasados:.1f} minutos. Faltan {minutos_restantes:.1f} minutos")
            return False
        return True
    except Exception as e:
        print(f"⚠️ Error verificando tiempo: {e}")
        return True

# ... (detectar_pais, clasificar_categoria, calcular_puntaje_viral se mantienen igual) ...

def asegurar_puntuacion(texto):
    # ... (igual que antes) ...
    pass

def limpiar_texto_extraccion(texto):
    # ... (igual que antes) ...
    pass

def extraer_texto_completo(url):
    # ... (igual que antes) ...
    pass

def generar_redaccion_profesional(titulo, texto_completo, descripcion_rss, fuente):
    # ... (igual que antes, pero corregir URL de OpenRouter) ...
    
    # CORREGIDO: Eliminar espacios en URLs
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'HTTP-Referer': 'https://github.com',  # ← Sin espacio al final
        'X-Title': 'Bot Noticias',
        'Content-Type': 'application/json'
    }
    
    for modelo in modelos:
        try:
            print(f"   🔄 Modelo: {modelo.split('/')[-1]}...")
            
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',  # ← Sin espacio al final
                headers=headers,
                json={
                    'model': modelo,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.2,
                    'max_tokens': 1500
                },
                timeout=120
            )
            # ... (resto igual) ...

def asegurar_puntuacion_parrafos(texto):
    # ... (igual que antes) ...
    pass

def limpiar_salida_ia(contenido):
    # ... (igual que antes) ...
    pass

def generar_redaccion_manual(titulo, texto_completo, descripcion_rss, fuente):
    # ... (igual que antes) ...
    pass

def generar_hashtags(categoria, pais, titulo):
    # ... (igual que antes) ...
    pass

def extraer_imagen(entry, url_noticia=None):
    # ... (igual que antes) ...
    pass

def descargar_imagen(url):
    # ... (igual que antes) ...
    pass

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    # ... (igual que antes, pero corregir URL) ...
    
    try:
        # CORREGIDO: Eliminar espacio en URL de Facebook
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"  # ← Sin espacio antes de FB_PAGE_ID
        
        # ... (resto igual) ...

def buscar_noticias():
    """Busca noticias en fuentes RSS - CORREGIDO"""
    print("\n🔍 Buscando noticias...")
    noticias = []
    
    if NEWS_API_KEY:
        try:
            terminos = random.sample([
                'urgente crisis', 'última hora', 'alerta internacional',
                'guerra conflicto', 'economía crisis', 'política elecciones'
            ], 2)
            
            for termino in terminos:
                try:
                    # CORREGIDO: Eliminar espacio en URL
                    resp = requests.get(
                        "https://newsapi.org/v2/everything",  # ← Sin espacio
                        params={
                            'q': termino,
                            'language': 'es',
                            'sortBy': 'publishedAt',
                            'pageSize': 5,
                            'apiKey': NEWS_API_KEY
                        },
                        timeout=15
                    )
                    # ... (resto igual) ...
        except:
            pass
    
    random.shuffle(RSS_FEEDS)
    
    for feed_url in RSS_FEEDS[:10]:
        try:
            # CORREGIDO: feedparser ahora recibe URLs limpias (sin espacios)
            feed = feedparser.parse(feed_url)
            fuente_nombre = feed.feed.get('title', feed_url.split('/')[2])
            
            # ← NUEVO: Verificar si el feed se parseó correctamente
            if not feed.entries:
                print(f"   ⚠️ Feed vacío o error: {fuente_nombre[:25]}")
                continue
            
            for entry in feed.entries[:3]:
                titulo = entry.get('title', '')
                descripcion = entry.get('summary', entry.get('description', ''))
                url = entry.get('link', '')
                
                # ← NUEVO: Validar que tenga URL y título
                if not url or not titulo:
                    continue
                
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
            print(f"   ⚠️ Error feed {feed_url[:30]}: {str(e)[:40]}")
            continue
    
    print(f"\n📊 Total: {len(noticias)} noticias candidatas")
    return noticias

def filtrar_y_seleccionar(noticias, historial):
    """Filtra y selecciona la mejor noticia - CORREGIDO"""
    print("\n🔎 Filtrando duplicados...")
    
    candidatas = []
    
    for noticia in noticias:
        # ← CORREGIDO: Verificación más detallada de duplicados
        if es_duplicado(historial, noticia['url'], noticia['titulo']):
            continue
        
        # ← NUEVO: Filtros adicionales de calidad
        if len(noticia['titulo']) < 15:
            print(f"   ⚠️ Título muy corto: {noticia['titulo'][:30]}...")
            continue
            
        if "[Removed]" in noticia['titulo'] or "removed" in noticia['titulo'].lower():
            print(f"   ⚠️ Noticia removida: {noticia['titulo'][:30]}...")
            continue
            
        # ← NUEVO: Verificar que la URL sea válida
        if not noticia['url'].startswith('http'):
            print(f"   ⚠️ URL inválida: {noticia['url'][:30]}...")
            continue
        
        noticia['categoria'] = clasificar_categoria(noticia['titulo'], noticia['descripcion'])
        noticia['pais'] = detectar_pais(noticia['titulo'], noticia['descripcion'])
        
        candidatas.append(noticia)
        print(f"   ✅ [{noticia['categoria']}] {noticia['titulo'][:45]}... (viral: {noticia['puntaje_viral']})")
    
    if not candidatas:
        print("⚠️ No hay noticias candidatas después de filtrar")
        return None
    
    # Ordenar por puntaje viral
    candidatas.sort(key=lambda x: x['puntaje_viral'], reverse=True)
    
    # ← NUEVO: Mostrar top 3 para debug
    print(f"\n🏆 Top 3 noticias candidatas:")
    for i, n in enumerate(candidatas[:3], 1):
        print(f"   {i}. [{n['puntaje_viral']}] {n['titulo'][:50]}...")
    
    seleccionada = candidatas[0]
    print(f"\n🎯 Seleccionada: {seleccionada['titulo'][:60]}...")
    print(f"   URL: {seleccionada['url'][:70]}...")
    
    print(f"\n📄 Extrayendo contenido completo...")
    texto_completo = extraer_texto_completo(seleccionada['url'])
    
    if texto_completo and len(texto_completo) > 200:
        seleccionada['texto_completo'] = texto_completo
        print(f"   ✅ Texto extraído: {len(texto_completo)} caracteres")
    else:
        desc_limpia = re.sub(r'<[^>]+>', '', seleccionada['descripcion'])
        seleccionada['texto_completo'] = limpiar_texto_extraccion(desc_limpia)
        print(f"   ⚠️ Usando descripción RSS: {len(seleccionada['texto_completo'])} caracteres")
    
    return seleccionada

def main():
    """Función principal - CORREGIDA"""
    print("\n" + "="*60)
    print("INICIANDO PUBLICACIÓN")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Cargar historial
    historial = cargar_historial()
    print(f"📚 Historial cargado: {len(historial.get('urls', []))} noticias publicadas")
    
    # ← NUEVO: Verificar tiempo mínimo entre publicaciones (30 minutos)
    if not verificar_tiempo_ultima_publicacion(historial):
        print("❌ No se puede publicar: deben pasar 30 minutos entre publicaciones")
        return False
    
    # Buscar noticias
    noticias = buscar_noticias()
    if not noticias:
        print("\n❌ No se encontraron noticias en las fuentes RSS")
        return False
    
    # Filtrar y seleccionar
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    if not seleccionada:
        print("\n❌ No hay noticias nuevas para publicar (todas son duplicadas)")
        return False
    
    # Generar redacción
    print(f"\n✍️ Generando redacción profesional...")
    redaccion = generar_redaccion_profesional(
        seleccionada['titulo'],
        seleccionada['texto_completo'],
        seleccionada['descripcion'],
        seleccionada['fuente']
    )
    
    # Generar hashtags
    hashtags = generar_hashtags(
        seleccionada['categoria'],
        seleccionada['pais'],
        seleccionada['titulo']
    )
    
    # Descargar imagen
    print(f"\n🖼️ Procesando imagen...")
    imagen_path = descargar_imagen(seleccionada['imagen'])
    
    if not imagen_path and seleccionada.get('texto_completo'):
        urls_img = re.findall(r'https?://[^\s"']+\.(?:jpg|jpeg|png)', seleccionada['texto_completo'])
        for url_img in urls_img[:2]:
            imagen_path = descargar_imagen(url_img)
            if imagen_path:
                print(f"   ✅ Imagen extraída del contenido")
                break
    
    if not imagen_path:
        print("❌ No se pudo obtener imagen para la noticia")
        return False
    
    # Publicar en Facebook
    print(f"\n📤 Publicando en Facebook...")
    exito = publicar_facebook(
        seleccionada['titulo'],
        redaccion,
        imagen_path,
        hashtags
    )
    
    # Limpiar y finalizar
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        # ← CORREGIDO: Guardar en historial inmediatamente después de publicar
        guardar_historial(historial, seleccionada['url'], seleccionada['titulo'])
        
        print("\n" + "="*60)
        print("✅ ÉXITO: Noticia publicada y guardada en historial")
        print(f"📰 {seleccionada['titulo'][:50]}...")
        print("="*60)
        return True
    else:
        print("\n❌ Falló la publicación en Facebook")
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por usuario")
        exit(1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
