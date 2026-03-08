import requests
import feedparser
import json
import hashlib
import os
import re
from io import BytesIO
from PIL import Image

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

HISTORIAL_FILE = "historial_publicaciones.json"

RSS_FEEDS = [

"https://cnnespanol.cnn.com/feed/",
"https://www.infobae.com/feeds/rss/",
"https://www.eltiempo.com/rss/mundo.xml",
"https://www.clarin.com/rss/mundo/",
"https://www.20minutos.es/rss/",
"https://www.eldiario.es/rss/",
"https://www.elconfidencial.com/rss/",
"https://www.dw.com/es/actualidad/s-30684/rss",
"https://www.france24.com/es/rss",
"https://actualidad.rt.com/feeds/all.rss",
"https://www.latercera.com/feed/",
"https://www.elpais.com/rss/",
"https://www.abc.es/rss/feeds/abc_Internacional.xml",
"https://www.lavanguardia.com/rss/internacional.xml"

]


def limpiar_html(texto):

    if not texto:
        return ""

    texto = re.sub("<.*?>", "", texto)
    texto = texto.replace("\n", " ")
    texto = texto.replace("Continue reading", "")

    return texto.strip()


def limpiar_titulo(titulo):

    if "|" in titulo:
        titulo = titulo.split("|")[0]

    titulo = titulo.replace("en directo", "")
    titulo = titulo.replace("En directo", "")

    return titulo.strip()


def cargar_historial():

    if os.path.exists(HISTORIAL_FILE):

        with open(HISTORIAL_FILE,"r") as f:
            return json.load(f)

    return {"urls":[]}


def guardar_historial(hist):

    with open(HISTORIAL_FILE,"w") as f:
        json.dump(hist,f)


def hash_url(url):

    return hashlib.md5(url.encode()).hexdigest()


def buscar_rss():

    noticias=[]

    for feed_url in RSS_FEEDS:

        try:

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:5]:

                titulo = limpiar_html(entry.get("title",""))
                link = entry.get("link","")
                desc = limpiar_html(entry.get("summary",""))

                imagen=""

                if "media_content" in entry:
                    imagen = entry.media_content[0]["url"]

                noticias.append({
                    "titulo":titulo,
                    "descripcion":desc,
                    "url":link,
                    "imagen":imagen
                })

        except:
            pass

    return noticias


def elegir_noticia(noticias,historial):

    for n in noticias:

        if hash_url(n["url"]) not in historial["urls"]:
            return n

    return None


def extraer_articulo(url):

    try:

        r = requests.get(url,timeout=15)

        texto = limpiar_html(r.text)

        texto = re.sub(r'\s+', ' ', texto)

        return texto[:3000]

    except:

        return ""


def generar_con_ia(titulo,contenido):

    if not OPENROUTER_API_KEY:
        return ""

    prompt=f"""
Escribe una noticia en español basada en esta información.

Titulo:
{titulo}

Contenido:
{contenido}

Reglas:

3 a 5 párrafos
mínimo 800 caracteres
explicar qué ocurrió
estilo periodístico
sin enlaces
"""

    try:

        r=requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
        "Authorization":f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":"application/json"
        },
        json={
        "model":"mistralai/mistral-7b-instruct",
        "messages":[{"role":"user","content":prompt}]
        },
        timeout=30
        )

        data=r.json()

        texto=data["choices"][0]["message"]["content"]

        return texto.strip()

    except:

        return ""


def verificar_texto(texto):

    if not texto:
        return False

    if len(texto) < 700:
        return False

    return True


def crear_post(noticia):

    titulo = limpiar_titulo(noticia["titulo"])

    contenido = noticia["descripcion"]

    texto = generar_con_ia(titulo,contenido)

    if not verificar_texto(texto):

        articulo = extraer_articulo(noticia["url"])

        texto = generar_con_ia(titulo,articulo)

        if not verificar_texto(texto):

            texto = articulo[:1200]

    hashtags = "#Noticias #Actualidad #UltimaHora #Mundo"

    mensaje=f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto
"""

    return mensaje


def descargar_imagen(url):

    if not url:
        return None

    try:

        r=requests.get(url,timeout=10)

        img=Image.open(BytesIO(r.content))

        path="/tmp/noticia.jpg"

        img.save(path)

        return path

    except:

        return None


def publicar_facebook(texto,img):

    if img:

        url=f"https://graph.facebook.com/{FB_PAGE_ID}/photos"

        with open(img,"rb") as f:

            r=requests.post(
            url,
            files={"file":f},
            data={
            "message":texto,
            "access_token":FB_ACCESS_TOKEN
            })

    else:

        url=f"https://graph.facebook.com/{FB_PAGE_ID}/feed"

        r=requests.post(
        url,
        data={
        "message":texto,
        "access_token":FB_ACCESS_TOKEN
        })

    print(r.text)

    return r.status_code==200


def main():

    historial=cargar_historial()

    noticias=buscar_rss()

    noticia=elegir_noticia(noticias,historial)

    if not noticia:
        print("No hay noticias nuevas")
        return

    post=crear_post(noticia)

    img=descargar_imagen(noticia["imagen"])

    publicado=publicar_facebook(post,img)

    if publicado:

        historial["urls"].append(hash_url(noticia["url"]))

        guardar_historial(historial)

        print("Publicado correctamente")

    else:

        print("Error publicando")


if __name__=="__main__":
    main()
