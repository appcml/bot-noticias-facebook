import requests
import feedparser
import json
import hashlib
import os
from datetime import datetime
from io import BytesIO
from PIL import Image

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

HISTORIAL_FILE = "historial_publicaciones.json"

RSS_FEEDS = [
"https://rss.cnn.com/rss/edition.rss",
"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://www.france24.com/es/rss",
"https://www.dw.com/es/actualidad/s-30684/rss",
"https://www.eltiempo.com/rss/mundo.xml",
"https://www.clarin.com/rss/mundo/",
"https://www.latercera.com/feed/",
"https://www.infobae.com/feeds/rss/",
"https://www.20minutos.es/rss/",
"https://www.elconfidencial.com/rss/",
"https://www.rtve.es/api/rss/noticias/",
"https://www.eldiario.es/rss/",
"https://feeds.skynews.com/feeds/rss/world.xml",
"https://www.reutersagency.com/feed/?best-topics=world"
]

REDDIT_FEEDS = [
"https://www.reddit.com/r/worldnews/.rss",
"https://www.reddit.com/r/news/.rss"
]

PALABRAS_VIRALES = [
"urgente","crisis","ataque","histórico","explota","tensión",
"investigación","escándalo","colapso","protesta","invasión",
"guerra","bombardeo","crisis económica","inflación","recesión"
]

PAISES = {
"Estados Unidos":["biden","trump","washington","usa","eeuu"],
"Rusia":["putin","moscú","kremlin"],
"China":["xi jinping","beijing","china"],
"Ucrania":["zelensky","kiev","ucrania"],
"España":["sánchez","madrid","españa"],
"Chile":["boric","santiago","chile"],
"Argentina":["milei","buenos aires","argentina"],
"Irán":["iran","teherán"],
"Israel":["israel","tel aviv"]
}

CATEGORIAS = {
"Política":["presidente","gobierno","elecciones","congreso"],
"Economía":["inflación","mercado","economía","banco"],
"Tecnología":["tecnología","inteligencia artificial","IA"],
"Seguridad":["crimen","asesinato","detenido"],
"Salud":["virus","pandemia","hospital"],
"MedioAmbiente":["clima","huracán","incendio"],
"Ciencia":["descubrimiento","espacio","nasa"]
}


def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE,"r") as f:
            return json.load(f)
    return {"urls":[],"titulos":[]}


def guardar_historial(hist):
    with open(HISTORIAL_FILE,"w") as f:
        json.dump(hist,f)


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


def detectar_pais(texto):
    texto=texto.lower()

    for pais,claves in PAISES.items():
        for c in claves:
            if c in texto:
                return pais

    return "Mundo"


def detectar_categoria(texto):
    texto=texto.lower()

    for cat,claves in CATEGORIAS.items():
        for c in claves:
            if c in texto:
                return cat

    return "Actualidad"


def es_viral(texto):
    texto=texto.lower()
    return any(p in texto for p in PALABRAS_VIRALES)


def buscar_rss():

    noticias=[]

    for feed_url in RSS_FEEDS:

        try:
            feed=feedparser.parse(feed_url)

            for entry in feed.entries[:6]:

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
                    "imagen":imagen,
                    "fuente":feed_url
                })

        except:
            pass

    return noticias


def buscar_reddit():

    tendencias=[]

    for feed in REDDIT_FEEDS:

        try:
            data=feedparser.parse(feed)

            for entry in data.entries[:8]:
                tendencias.append(entry.title.lower())

        except:
            pass

    return tendencias


def calcular_score(noticia,tendencias):

    score=0

    titulo=noticia["titulo"].lower()

    if es_viral(titulo):
        score+=3

    if noticia["imagen"]:
        score+=1

    if any(t in titulo for t in tendencias):
        score+=2

    if len(titulo)>80:
        score+=1

    return score


def elegir_noticia(noticias,tendencias,historial):

    mejor=None
    mejor_score=0

    for n in noticias:

        if hash_url(n["url"]) in historial["urls"]:
            continue

        score=calcular_score(n,tendencias)

        if score>mejor_score:
            mejor_score=score
            mejor=n

    return mejor


def generar_texto(titulo, descripcion):

    prompt = f"""
Escribe una noticia periodística profesional en español.

TÍTULO:
{titulo}

INFORMACIÓN:
{descripcion}

REGLAS:
- 3 a 5 párrafos
- entre 700 y 1200 caracteres
- estilo periodístico
- explicar qué pasó, dónde ocurrió y por qué es importante
- NO repetir el título
- sin hashtags
"""

    try:

        if OPENROUTER_API_KEY:

            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct:free",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=25
            )

            data=r.json()

            texto=data["choices"][0]["message"]["content"]

            return texto.strip()

    except Exception as e:
        print("IA no disponible:", e)

    return f"""
La situación continúa desarrollándose tras conocerse nuevos antecedentes sobre este hecho que ha generado preocupación a nivel internacional.

De acuerdo con los primeros reportes, el acontecimiento ocurrió recientemente y ha provocado diversas reacciones tanto en autoridades como en analistas que siguen de cerca el desarrollo de los acontecimientos.

Expertos advierten que este escenario podría tener consecuencias importantes en los próximos días, especialmente considerando el contexto político y estratégico en la región.

Se espera que en las próximas horas se conozcan más detalles mientras organismos internacionales y gobiernos monitorean la evolución de la situación.
"""


def optimizar_titulo(titulo):

    if len(titulo)>90:
        titulo=titulo[:90]+"..."

    return titulo


def generar_hashtags(categoria,pais):

    pais_tag=pais.replace(" ","")

    tags=[
    f"#{categoria}",
    "#Noticias",
    "#Actualidad",
    f"#{pais_tag}",
    "#Mundo"
    ]

    return " ".join(tags)


def descargar_imagen(url):

    if not url:
        return None

    try:

        r=requests.get(url,timeout=15)

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

    texto=generar_texto(
    titulo,
    noticia["descripcion"]
    )

    pais=detectar_pais(titulo+texto)

    categoria=detectar_categoria(titulo+texto)

    hashtags=generar_hashtags(categoria,pais)

    mensaje=f"""📰 {titulo}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto
"""

    return mensaje,pais,categoria


def main():

    print("Buscando noticias...")

    historial=cargar_historial()

    noticias=buscar_rss()

    tendencias=buscar_reddit()

    noticia=elegir_noticia(noticias,tendencias,historial)

    if not noticia:
        print("No se encontró noticia nueva")
        return

    print("Noticia elegida:",noticia["titulo"])

    post,pais,categoria=crear_post(noticia)

    img=descargar_imagen(noticia["imagen"])

    publicado=publicar_facebook(post,img)

    if publicado:

        historial["urls"].append(hash_url(noticia["url"]))

        historial["titulos"].append(noticia["titulo"])

        guardar_historial(historial)

        print("Publicado correctamente")

    else:

        print("Error publicando")


if __name__=="__main__":
    main()
