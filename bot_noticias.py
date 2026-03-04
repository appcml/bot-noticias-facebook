import requests
import random
import re
import hashlib
import os
from datetime import datetime
import json
import time
import feedparser
from bs4 import BeautifulSoup

# ==============================
# VARIABLES DE ENTORNO
# ==============================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')

print(f"DEBUG: FB={bool(FB_ACCESS_TOKEN)} OPENAI={bool(OPENAI_API_KEY)}")

if not all([FB_PAGE_ID, FB_ACCESS_TOKEN, OPENAI_API_KEY]):
    raise ValueError("Faltan variables obligatorias")

# ==============================
# FUENTES RSS
# ==============================

FUENTES_RSS = {
    'bbc': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'reuters': 'http://feeds.reuters.com/reuters/worldnews',
    'cnn': 'http://rss.cnn.com/rss/edition_world.rss',
}

HISTORIAL_URLS = set()

# ==============================
# BUSCAR NOTICIAS
# ==============================

def buscar_noticias():
    noticias = []

    for fuente, url_rss in FUENTES_RSS.items():
        try:
            response = requests.get(url_rss, timeout=15)
            feed = feedparser.parse(response.content)

            for entry in feed.entries[:5]:
                descripcion = BeautifulSoup(
                    entry.get('summary', ''),
                    'html.parser'
                ).get_text()

                noticias.append({
                    "title": entry.title,
                    "content": descripcion,
                    "url": entry.link,
                    "source": fuente.upper()
                })
        except:
            pass

    noticias_filtradas = [
        n for n in noticias
        if n["url"] not in HISTORIAL_URLS and len(n["content"]) > 200
    ]

    return noticias_filtradas[:3]

# ==============================
# REESCRIBIR CON OPENAI
# ==============================

def reescribir_noticia(titulo, contenido, fuente):

    prompt = f"""
Reescribe profesionalmente esta noticia.
Mantén hechos exactos.
Devuelve JSON con:
titulo, contenido, resumen_seo, palabras_clave, categoria.

Título: {titulo}
Contenido: {contenido[:800]}
Fuente: {fuente}
"""

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        },
        timeout=60
    )

    data = response.json()

    texto = data["choices"][0]["message"]["content"]
    json_match = re.search(r'\{.*\}', texto, re.DOTALL)

    if json_match:
        return json.loads(json_match.group())

    return None

# ==============================
# GENERAR IMAGEN SIMPLE IA
# ==============================

def generar_imagen_dummy():
    path = "/tmp/demo.png"
    with open(path, "wb") as f:
        f.write(os.urandom(50000))
    return path

# ==============================
# PUBLICAR EN FACEBOOK (VERSIÓN CORRECTA)
# ==============================

def publicar_en_facebook(titulo, resumen, palabras_clave, imagen_path, url_fuente, nombre_fuente):

    print("\n[FACEBOOK] Publicando...")

    hashtags = ' '.join([f"#{kw.replace(' ', '')}" for kw in palabras_clave[:4]])

    mensaje = f"""📰 {titulo}

{resumen}

{hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""

    try:

        # ==================================
        # PASO 1: SUBIR IMAGEN SIN PUBLICAR
        # ==================================

        url_photo = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"

        with open(imagen_path, "rb") as img:

            files = {
                "source": img
            }

            data = {
                "access_token": FB_ACCESS_TOKEN,
                "published": False
            }

            response_photo = requests.post(url_photo, files=files, data=data)
            result_photo = response_photo.json()

        print("[DEBUG FOTO]", result_photo)

        if "id" not in result_photo:
            print("Error subiendo imagen")
            return False

        media_id = result_photo["id"]

        # ==================================
        # PASO 2: CREAR POST CON IMAGEN
        # ==================================

        url_feed = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"

        data_feed = {
            "message": mensaje,
            "attached_media": json.dumps([{"media_fbid": media_id}]),
            "access_token": FB_ACCESS_TOKEN
        }

        response_feed = requests.post(url_feed, data=data_feed)
        result_feed = response_feed.json()

        print("[DEBUG POST]", result_feed)

        if "id" not in result_feed:
            print("Error creando post")
            return False

        post_id = result_feed["id"]

        # ==================================
        # PASO 3: COMENTARIO CON LINK
        # ==================================

        url_comment = f"https://graph.facebook.com/v19.0/{post_id}/comments"

        mensaje_comment = f"""📎 Fuente: {nombre_fuente}

🔗 {url_fuente}

#Noticias #Actualidad"""

        requests.post(url_comment, data={
            "message": mensaje_comment,
            "access_token": FB_ACCESS_TOKEN
        })

        print("✓ Publicación completa creada")

        return True

    except Exception as e:
        print("ERROR FACEBOOK:", e)
        return False

# ==============================
# MAIN
# ==============================

def main():

    print("🚀 VERDAD HOY BOT")

    noticias = buscar_noticias()

    if not noticias:
        print("No hay noticias")
        return

    noticia = noticias[0]
    HISTORIAL_URLS.add(noticia["url"])

    reescrita = reescribir_noticia(
        noticia["title"],
        noticia["content"],
        noticia["source"]
    )

    if not reescrita:
        print("Error OpenAI")
        return

    imagen = generar_imagen_dummy()

    publicar_en_facebook(
        reescrita["titulo"],
        reescrita["resumen_seo"],
        reescrita["palabras_clave"],
        imagen,
        noticia["url"],
        noticia["source"]
    )

if __name__ == "__main__":
    main()
