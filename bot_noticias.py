import requests
import feedparser
import re
import hashlib
import json
import os
import random
from datetime import datetime, timedelta  # ← Agregar timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# CONFIGURACIÓN
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_FILE = 'historial_publicaciones.json'

# FUENTES RSS INTERNACIONALES - CORREGIDO: eliminados espacios al final
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

# ... (resto de configuraciones igual) ...

def cargar_historial():
    """Carga el historial de publicaciones"""
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'urls': [], 'titulos': [], 'ultima_publicacion': None, 'hashes': []}  # ← Agregar 'hashes'

def guardar_historial(historial, url, titulo):
    """Guarda una noticia en el historial - CORREGIDO"""
    url_hash = hashlib.md5(url.lower().strip().encode()).hexdigest()[:16]
    titulo_hash = hashlib.md5(titulo.lower().strip().encode()).hexdigest()[:16]
    
    # ← CORREGIDO: Agregar a listas en el objeto historial
    historial['urls'].append(url)
    historial['titulos'].append(titulo[:100])
    historial['hashes'].append(url_hash)  # ← Nuevo: guardar hash directamente
    historial['ultima_publicacion'] = datetime.now().isoformat()
    
    # Mantener solo últimas 500
    historial['urls'] = historial['urls'][-500:]
    historial['titulos'] = historial['titulos'][-500:]
    historial['hashes'] = historial['hashes'][-500:]
    
    try:
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        print(f"💾 Guardada en historial: {url[:50]}...")
    except Exception as e:
        print(f"⚠️ Error guardando historial: {e}")

def es_duplicado(historial, url, titulo):
    """Verifica si una noticia ya fue publicada - CORREGIDO: más estricto"""
    url_normalizada = url.lower().strip()
    url_hash = hashlib.md5(url_normalizada.encode()).hexdigest()[:16]
    
    # ← CORREGIDO: Verificar en hashes guardados
    if url_hash in historial.get('hashes', []):
        print(f"   ⚠️ Duplicado por hash: {url[:50]}...")
        return True
    
    # Verificación por URL exacta (backup)
    for url_guardada in historial.get('urls', []):
        if url_normalizada == url_guardada.lower().strip():
            print(f"   ⚠️ Duplicado por URL exacta")
            return True
    
    # ← CORREGIDO: Umbral más alto (85% en lugar de 75%) y comparación de palabras clave
    titulo_normalizado = re.sub(r'[^\w\s]', '', titulo.lower()).strip()
    palabras_titulo = set(titulo_normalizado.split())
    
    for titulo_guardado in historial.get('titulos', []):
        titulo_g_normalizado = re.sub(r'[^\w\s]', '', titulo_guardado.lower()).strip()
        palabras_guardadas = set(titulo_g_normalizado.split())
        
        # Calcular similitud de Jaccard
        if palabras_titulo and palabras_guardadas:
            interseccion = len(palabras_titulo & palabras_guardadas)
            union = len(palabras_titulo | palabras_guardadas)
            similitud = interseccion / union if union > 0 else 0
            
            if similitud > 0.85:  # ← Más estricto: 85%
                print(f"   ⚠️ Duplicado por título similar ({similitud:.0%})")
                return True
    
    return False

def verificar_tiempo_ultima_publicacion(historial):
    """← NUEVA FUNCIÓN: Verifica si pasaron 30 minutos"""
    ultima = historial.get('ultima_publicacion')
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        ahora = datetime.now()
        diferencia = ahora - ultima_dt
        
        if diferencia < timedelta(minutes=30):
            minutos_restantes = 30 - (diferencia.seconds // 60)
            print(f"⏰ Esperando... {minutos_restantes} minutos restantes")
            return False
        return True
    except:
        return True

# ... (resto de funciones igual hasta main) ...

def main():
    """Función principal - CORREGIDA"""
    print("\n" + "="*60)
    print("INICIANDO PUBLICACIÓN")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    historial = cargar_historial()
    print(f"📚 Historial: {len(historial.get('urls', []))} noticias")
    
    # ← NUEVO: Verificar tiempo mínimo entre publicaciones
    if not verificar_tiempo_ultima_publicacion(historial):
        print("❌ No han pasado 30 minutos desde la última publicación")
        return False
    
    noticias = buscar_noticias()
    if not noticias:
        print("\n❌ Sin noticias disponibles")
        return False
    
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    if not seleccionada:
        print("\n❌ Sin noticias nuevas para publicar")
        return False
    
    print(f"\n✍️ Redactando...")
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
    
    print(f"\n📤 Publicando...")
    exito = publicar_facebook(
        seleccionada['titulo'],
        redaccion,
        imagen_path,
        hashtags
    )
    
    if exito:
        # ← CORREGIDO: Guardar y actualizar historial en memoria
        guardar_historial(historial, seleccionada['url'], seleccionada['titulo'])
        
        # Limpiar imagen temporal
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n" + "="*60)
        print("✅ ÉXITO - Publicación guardada en historial")
        print("="*60)
        return True
    else:
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n❌ Falló la publicación")
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
