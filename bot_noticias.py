import feedparser
import requests
from bs4 import BeautifulSoup
import random
import os

# ==============================
# CONFIGURACIÓN FACEBOOK
# ==============================

PAGE_ID = os.getenv("PAGE_ID")
ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

# ==============================
# MEDIOS EN ESPAÑOL
# ==============================

RSS_FEEDS = {

    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada",
    "20 Minutos": "https://www.20minutos.es/rss/internacional/",
    "La Vanguardia": "https://www.lavanguardia.com/rss/internacional.xml",
    "ABC": "https://www.abc.es/rss/feeds/abc_Internacional.xml",
    "El Mundo": "https://www.elmundo.es/rss/internacional.xml",
    "Clarín": "https://www.clarin.com/rss/mundo/",
    "Infobae": "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml",
    "BioBioChile": "https://www.biobiochile.cl/rss/internacional.xml",
    "DW Español": "https://rss.dw.com/xml/rss-es-all"

}

HASHTAGS = "#Noticias #Actualidad #UltimaHora #Mundo"


# ==============================
# EXTRAER TEXTO
# ==============================

def obtener_texto(url):

    try:

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        parrafos = soup.find_all("p")

        texto = ""

        for p in parrafos:

            t = p.get_text()

            if len(t) > 80:
                texto += t + "\n\n"

        return texto[:1500]

    except Exception as e:

        print("Error extrayendo texto:", e)

        return ""


# ==============================
# BUSCAR NOTICIA
# ==============================

def buscar_noticia():

    medio = random.choice(list(RSS_FEEDS.keys()))
    feed_url = RSS_FEEDS[medio]

    print("Buscando noticia en:", medio)

    feed = feedparser.parse(feed_url)

    if not feed.entries:

        print("No se encontraron noticias")

        return None, None, None

    noticia = random.choice(feed.entries)

    titulo = noticia.title
    link = noticia.link

    print("Titulo encontrado:", titulo)

    texto = obtener_texto(link)

    return titulo, texto, medio


# ==============================
# CREAR POST
# ==============================

def crear_post():

    titulo, texto, medio = buscar_noticia()

    if titulo is None:
        return None

    if len(texto) < 200:
        texto = "Más información en desarrollo."

    post = f"""📰 {titulo}

{texto}

{HASHTAGS}

Fuente: {medio}
— Verdad Hoy: Noticias al minuto
"""

    return post


# ==============================
# PUBLICAR EN FACEBOOK
# ==============================

def publicar():

    mensaje = crear_post()

    if mensaje is None:

        print("No se pudo generar noticia")

        return

    print("Publicando en Facebook...")

    url = f"https://graph.facebook.com/{PAGE_ID}/feed"

    data = {

        "message": mensaje,
        "access_token": ACCESS_TOKEN

    }

    r = requests.post(url, data=data)

    print("Respuesta Facebook:")

    print(r.text)


# ==============================
# EJECUCIÓN
# ==============================

if __name__ == "__main__":

    publicar()
