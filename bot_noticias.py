import requests
import random
import re
import os
import json
import feedparser
from datetime import datetime
from io import BytesIO
from PIL import Image

# ==============================
# CONFIGURACIÓN
# ==============================

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")

HISTORIAL_FILE = "historial_publicaciones.json"

# ==============================
# FUENTES RSS
# ==============================

RSS_FEEDS = [

# INTERNACIONALES
"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://rss.cnn.com/rss/edition_world.rss",

# ESPAÑA
"https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
"https://www.abc.es/rss/feeds/abc_Internacional.xml",

# LATAM
"https://www.clarin.com/rss/lo-ultimo/",
"https://www.eltiempo.com/rss/mundo.xml"

]

# ==============================
# CARGAR HISTORIAL
# ==============================

def cargar_historial():

    if not os.path.exists(HISTORIAL_FILE):
        return []

    with open(HISTORIAL_FILE, "r") as f:
        return json.load(f)


def guardar_historial(historial):

    with open(HISTORIAL_FILE, "w") as f:
        json.dump(historial, f)

# ==============================
# LIMPIAR TEXTO IA
# ==============================

def limpiar_texto(texto):

    texto = re.sub(r"\[.*?\]", "", texto)
    texto = re.sub(r"Párrafo\s*\d+:?", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"Lead:?", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"Titular:?", "", texto, flags=re.IGNORECASE)

    return texto.strip()

# ==============================
# BUSCAR NOTICIAS
# ==============================

def buscar_noticia():

    random.shuffle(RSS_FEEDS)

    for feed_url in RSS_FEEDS:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:10]:

            titulo = entry.title
            descripcion = entry.get("summary", "")

            imagen = None

            if "media_content" in entry:
                imagen = entry.media_content[0]["url"]

            return {
                "titulo": titulo,
                "descripcion": descripcion,
                "imagen": imagen,
                "fuente": feed.feed.title
            }

    return None

# ==============================
# GENERAR NOTICIA CON IA
# ==============================

def generar_noticia_ia(titulo, descripcion, fuente):

    prompt = f"""
Eres un periodista profesional.

Debes escribir una noticia real con estilo periodístico.

DATOS:

Título original:
{titulo}

Descripción:
{descripcion}

Fuente:
{fuente}

INSTRUCCIONES:

Escribe una noticia nueva basada en esta información.

Estructura:

1 Titular atractivo
2 Párrafo de introducción
3 Desarrollo de la noticia
4 Contexto o antecedentes
5 Conclusión

REGLAS:

NO escribas instrucciones.
NO pongas "Párrafo 1".
NO uses corchetes.

Solo escribe la noticia completa.

Longitud aproximada: 1200 caracteres.
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    data = response.json()

    texto = data["choices"][0]["message"]["content"]

    return limpiar_texto(texto)

# ==============================
# DESCARGAR IMAGEN
# ==============================

def descargar_imagen(url):

    if not url:
        return None

    try:

        r = requests.get(url, timeout=10)

        img = Image.open(BytesIO(r.content))

        path = "imagen_noticia.jpg"

        img.save(path)

        return path

    except:
        return None

# ==============================
# PUBLICAR EN FACEBOOK
# ==============================

def publicar_facebook(texto, imagen):

    url = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"

    with open(imagen, "rb") as img:

        response = requests.post(
            url,
            files={"source": img},
            data={
                "caption": texto,
                "access_token": FB_ACCESS_TOKEN
            }
        )

    return response.json()

# ==============================
# BOT PRINCIPAL
# ==============================

def ejecutar_bot():

    historial = cargar_historial()

    noticia = buscar_noticia()

    if not noticia:
        print("No se encontró noticia")
        return

    titulo = noticia["titulo"]

    if titulo in historial:
        print("Noticia ya publicada")
        return

    descripcion = noticia["descripcion"]
    fuente = noticia["fuente"]
    imagen_url = noticia["imagen"]

    print("Generando noticia con IA...")

    texto = generar_noticia_ia(titulo, descripcion, fuente)

    texto_final = f"""📰 {titulo}

{texto}

#Noticias #UltimaHora #Mundo

Fuente: {fuente}
"""

    print("Descargando imagen...")

    imagen = descargar_imagen(imagen_url)

    if imagen:

        print("Publicando en Facebook...")

        publicar_facebook(texto_final, imagen)

        historial.append(titulo)

        guardar_historial(historial)

        print("Noticia publicada")

    else:

        print("No se pudo descargar imagen")


# ==============================
# EJECUTAR BOT
# ==============================

if __name__ == "__main__":

    ejecutar_bot()
