import requests
import feedparser
import json
import hashlib
import random
import re
import os
from datetime import datetime
from PIL import Image
from io import BytesIO

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
"https://www.reutersagency.com/feed/?best-topics=world",
"https://www.reddit.com/r/worldnews/.rss",
"https://www.reddit.com/r/news/.rss"
]

PALABRAS_VIRALES = [
"urgente","última hora","crisis","ataque","histórico","guerra",
"conflicto","escándalo","investigación","tensión","alerta",
"explota","colapso","crisis económica","recesión","inflación",
"protesta","revuelta","bombardeo","invasión"
]

CATEGORIAS = {
"política":["presidente","gobierno","elecciones","congreso"],
"economía":["inflación","mercado","economía","banco"],
"tecnología":["tecnología","inteligencia artificial","IA"],
"seguridad":["crimen","asesinato","detenido"],
"salud":["virus","pandemia","hospital"],
"medio ambiente":["clima","huracán","incendio"],
"ciencia":["descubrimiento","espacio","NASA"],
"internacional":[]
}

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE,"r") as f:
            return json.load(f)
    return []

def guardar_historial(hist):
    with open(HISTORIAL_FILE,"w") as f:
        json.dump(hist,f)

def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()

def es_viral(texto):
    texto=texto.lower()
    return any(p in texto for p in PALABRAS_VIRALES)

def detectar_categoria(texto):
    texto=texto.lower()
    for cat,keys in CATEGORIAS.items():
        for k in keys:
            if k in texto:
                return cat
    return "actualidad"

def buscar_noticias():
    noticias=[]
    
    for feed_url in RSS_FEEDS:
        try:
            feed=feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                
                titulo=entry.get("title","")
                link=entry.get("link","")
                desc=entry.get("summary","")
                
                img=""
                if "media_content" in entry:
                    img=entry.media_content[0]["url"]
                
                score=0
                
                if es_viral(titulo):
                    score+=3
                
                if img:
                    score+=1
                
                categoria=detectar_categoria(titulo+" "+desc)
                
                noticias.append({
                    "titulo":titulo,
                    "descripcion":desc,
                    "url":link,
                    "imagen":img,
                    "score":score,
                    "categoria":categoria
                })
                
        except:
            pass
    
    noticias.sort(key=lambda x:x["score"],reverse=True)
    
    return noticias

def generar_texto(titulo,descripcion):

    if not OPENROUTER_API_KEY:
        return descripcion[:800]

    prompt=f"""
Escribe una noticia profesional.

Título:
{titulo}

Información:
{descripcion}

Escribe entre 500 y 900 caracteres.
Sin markdown.
Sin links.
"""

    try:
        r=requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
        "Authorization":f"Bearer {OPENROUTER_API_KEY}"
        },
        json={
        "model":"mistralai/mistral-7b-instruct:free",
        "messages":[{"role":"user","content":prompt}]
        }
        )

        data=r.json()
        return data["choices"][0]["message"]["content"]

    except:
        return descripcion[:800]

def descargar_imagen(url):

    if not url:
        return None

    try:
        r=requests.get(url,timeout=15)
        img=Image.open(BytesIO(r.content))
        path="/tmp/img.jpg"
        img.save(path)
        return path
    except:
        return None

def publicar_facebook(texto,img):

    url=f"https://graph.facebook.com/{FB_PAGE_ID}/photos"

    with open(img,"rb") as f:
        r=requests.post(
        url,
        files={"file":f},
        data={
        "message":texto,
        "access_token":FB_ACCESS_TOKEN
        })

    return r.status_code==200

def crear_post(noticia):

    texto=generar_texto(
        noticia["titulo"],
        noticia["descripcion"]
    )

    hashtags=f"#{noticia['categoria']} #Noticias #Actualidad #Mundo"

    mensaje=f"""📰 {noticia['titulo']}

{texto}

{hashtags}

— Verdad Hoy: Noticias al minuto
"""

    return mensaje

def main():

    historial=cargar_historial()

    noticias=buscar_noticias()

    for n in noticias:

        if hash_url(n["url"]) in historial:
            continue

        img=descargar_imagen(n["imagen"])

        if not img:
            continue

        post=crear_post(n)

        if publicar_facebook(post,img):

            historial.append(hash_url(n["url"]))
            guardar_historial(historial)

            return

if __name__=="__main__":
    main()
