import requests
import feedparser
import json
import hashlib
import os
from io import BytesIO
from PIL import Image

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

HISTORIAL_FILE = "historial_publicaciones.json"

# RSS MEJORES Y MAS RAPIDOS
RSS_FEEDS = [

"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://rss.cnn.com/rss/edition_world.rss",
"https://www.aljazeera.com/xml/rss/all.xml",
"https://www.theguardian.com/world/rss",
"https://www.reutersagency.com/feed/?best-topics=world",
"https://www.reutersagency.com/feed/?best-topics=politics",
"https://www.nytimes.com/services/xml/rss/nyt/World.xml",
"https://www.euronews.com/rss?level=theme&name=news",
"https://cnnespanol.cnn.com/feed/",
"https://actualidad.rt.com/feeds/all.rss"

]

PALABRAS_VIRALES = [

"urgente","última hora","guerra","ataque","crisis",
"explosión","conflicto","protestas","tensión",
"invasión","misiles","bombardeo","tragedia",
"colapso","investigación","escándalo","crisis económica",
"emergencia","alarma","amenaza","terrorista"

]


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


def es_viral(texto):

    texto=texto.lower()

    return any(p in texto for p in PALABRAS_VIRALES)


def buscar_rss():

    noticias=[]

    for feed_url in RSS_FEEDS:

        try:

            feed=feedparser.parse(feed_url)

            for entry in feed.entries[:5]:

                titulo=entry.get("title","")
                link=entry.get("link","")
                desc=entry.get("summary","")

                imagen=""

                if "media_content" in entry:
                    imagen=entry.media_content[0]["url"]

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

    mejor=None
    mejor_score=0

    for n in noticias:

        if hash_url(n["url"]) in historial["urls"]:
            continue

        score=0

        if es_viral(n["titulo"]):
            score+=3

        if n["imagen"]:
            score+=1

        if len(n["titulo"])>60:
            score+=1

        if score>mejor_score:

            mejor_score=score
            mejor=n

    return mejor


def optimizar_titulo(titulo):

    if len(titulo) > 140:
        titulo = titulo[:140] + "..."

    return titulo


def generar_texto(titulo,descripcion):

    prompt=f"""
Redacta una noticia periodística en español.

Título:
{titulo}

Información:
{descripcion}

Reglas:

3 a 5 párrafos
mínimo 700 caracteres
estilo periodístico claro
explicar qué pasó y por qué es importante
"""

    try:

        if OPENROUTER_API_KEY:

            r=requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization":f"Bearer {OPENROUTER_API_KEY}"},
            json={
            "model":"mistralai/mistral-7b-instruct:free",
            "messages":[{"role":"user","content":prompt}]
            },
            timeout=20
            )

            data=r.json()

            texto=data["choices"][0]["message"]["content"]

            return texto.strip()

    except:
        pass

    return descripcion


def generar_hashtags():

    tags=[
    "#Noticias",
    "#Actualidad",
    "#UltimaHora",
    "#Mundo"
    ]

    return " ".join(tags)


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


def crear_post(noticia):

    titulo=optimizar_titulo(noticia["titulo"])

    texto=generar_texto(titulo,noticia["descripcion"])

    hashtags=generar_hashtags()

    mensaje=f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto
"""

    return mensaje


def main():

    print("Buscando noticias...")

    historial=cargar_historial()

    noticias=buscar_rss()

    noticia=elegir_noticia(noticias,historial)

    if not noticia:
        print("No hay noticias nuevas")
        return

    print("Noticia elegida:",noticia["titulo"])

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
