import requests
import feedparser
import os
import random
import re
from datetime import datetime
from PIL import Image
from io import BytesIO

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")

RSS_FEEDS = [
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "https://www.20minutos.es/rss/"
]

def buscar_noticia():

    print("Buscando noticias...")

    noticias = []

    for feed_url in RSS_FEEDS:

        try:

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:10]:

                imagen = ""

                if hasattr(entry, "media_content"):
                    imagen = entry.media_content[0]["url"]

                if "summary" in entry:
                    m = re.search(r'src="(https?://[^"]+)"', entry.summary)
                    if m:
                        imagen = m.group(1)

                noticias.append({
                    "titulo": entry.title,
                    "descripcion": entry.summary if "summary" in entry else "",
                    "imagen": imagen,
                    "fuente": feed.feed.title
                })

        except:
            continue

    if not noticias:
        return None

    noticia = random.choice(noticias)

    print("Noticia encontrada:", noticia["titulo"])

    return noticia


def generar_texto(titulo, descripcion, fuente):

    prompt = f"""
Actúa como editor profesional de noticias en español.

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

Formato final:

📰 TITULO COMPLETO

Párrafo 1

Párrafo 2

Párrafo 3

#Noticias #Actualidad #UltimaHora #Mundo

Fuente: {fuente}
— Verdad Hoy: Noticias al minuto

NOTICIA ORIGINAL

Título:
{titulo}

Descripción:
{descripcion}
"""

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4
            },
            timeout=60
        )

        data = response.json()

        texto = data["choices"][0]["message"]["content"]

        texto = re.sub(r'http\S+', '', texto)

        return texto

    except Exception as e:

        print("Error IA:", e)

        return None


def descargar_imagen(url):

    if not url:
        return None

    try:

        print("Descargando imagen...")

        r = requests.get(url, timeout=15)

        img = Image.open(BytesIO(r.content))

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        path = "/tmp/noticia.jpg"

        img.save(path, "JPEG", quality=90)

        return path

    except Exception as e:

        print("Error imagen:", e)

        return None


def publicar_facebook(texto, imagen):

    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("Faltan credenciales de Facebook")
        return

    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"

    try:

        with open(imagen, "rb") as f:

            response = requests.post(
                url,
                files={"file": f},
                data={
                    "message": texto,
                    "access_token": FB_ACCESS_TOKEN
                }
            )

        print("Respuesta Facebook:")
        print(response.text)

    except Exception as e:

        print("Error publicando:", e)


def main():

    print("BOT DE NOTICIAS VERDAD HOY")
    print(datetime.now())

    noticia = buscar_noticia()

    if not noticia:
        print("No se encontró noticia")
        return

    texto = generar_texto(
        noticia["titulo"],
        noticia["descripcion"],
        noticia["fuente"]
    )

    if not texto:
        print("No se pudo generar texto")
        return

    imagen = descargar_imagen(noticia["imagen"])

    if not imagen:
        print("No se encontró imagen")
        return

    publicar_facebook(texto, imagen)

    print("Proceso terminado")


if __name__ == "__main__":
    main()
