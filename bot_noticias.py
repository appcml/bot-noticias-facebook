import feedparser
import requests
from bs4 import BeautifulSoup
import random
import os

PAGE_ID = os.getenv("PAGE_ID")
ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

RSS_FEEDS = {

    "El Pais": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada",
    "Infobae": "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml",
    "BBC Mundo": "https://feeds.bbci.co.uk/mundo/rss.xml",
    "DW Español": "https://rss.dw.com/xml/rss-es-all",
    "La Vanguardia": "https://www.lavanguardia.com/rss/internacional.xml",
    "20 Minutos": "https://www.20minutos.es/rss/internacional/",
    "BioBioChile": "https://www.biobiochile.cl/rss/internacional.xml"

}

HASHTAGS = "#Noticias #Actualidad #UltimaHora #Mundo"


def obtener_articulo(url):

    try:

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers)

        soup = BeautifulSoup(r.text, "html.parser")

        parrafos = soup.find_all("p")

        texto = ""

        for p in parrafos:

            contenido = p.get_text()

            if len(contenido) > 80:

                texto += contenido + "\n\n"

        imagen = None

        img = soup.find("img")

        if img and img.get("src"):

            imagen = img["src"]

        return texto[:2000], imagen

    except:

        return "", None


def buscar_noticia():

    medio = random.choice(list(RSS_FEEDS.keys()))

    feed_url = RSS_FEEDS[medio]

    feed = feedparser.parse(feed_url)

    noticia = random.choice(feed.entries)

    titulo = noticia.title

    link = noticia.link

    texto, imagen = obtener_articulo(link)

    return titulo, texto, medio, imagen


def crear_post():

    titulo, texto, medio, imagen = buscar_noticia()

    if len(texto) < 200:

        texto = "Más detalles de esta noticia en desarrollo."

    mensaje = f"""📰 {titulo}

{texto}

{HASHTAGS}

Fuente: {medio}
— Verdad Hoy: Noticias al minuto
"""

    return mensaje, imagen


def publicar():

    mensaje, imagen = crear_post()

    url = f"https://graph.facebook.com/{PAGE_ID}/photos"

    data = {

        "caption": mensaje,
        "url": imagen,
        "access_token": ACCESS_TOKEN

    }

    r = requests.post(url, data=data)

    print("Respuesta Facebook:")
    print(r.text)


if __name__ == "__main__":

    publicar()
