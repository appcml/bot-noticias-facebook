import requests
import random
import json
import os

# CONFIGURACIÓN
NEWS_API_KEY = "TU_API_KEY"
PAGE_ID = "TU_PAGE_ID"
PAGE_TOKEN = "TU_PAGE_TOKEN"

archivo_historial = "noticias_publicadas.json"


def cargar_historial():
    if os.path.exists(archivo_historial):
        with open(archivo_historial, "r") as f:
            return json.load(f)
    return []


def guardar_historial(historial):
    with open(archivo_historial, "w") as f:
        json.dump(historial, f)


def obtener_noticia():
    url = f"https://newsapi.org/v2/top-headlines?language=es&pageSize=20&apiKey={NEWS_API_KEY}"
    r = requests.get(url).json()

    articulos = r.get("articles", [])
    random.shuffle(articulos)

    historial = cargar_historial()

    for articulo in articulos:
        titulo = articulo["title"]
        descripcion = articulo["description"]
        imagen = articulo["urlToImage"]
        link = articulo["url"]

        if link not in historial and imagen:
            historial.append(link)
            guardar_historial(historial)

            return titulo, descripcion, imagen, link

    return None, None, None, None


def crear_texto(titulo, descripcion, link):
    emojis = ["🚨", "📰", "🌎", "⚡", "🔴"]

    encabezado = random.choice([
        "ÚLTIMO MOMENTO",
        "NOTICIA DE ÚLTIMA HORA",
        "INFORMACIÓN EN DESARROLLO",
        "ATENCIÓN"
    ])

    texto = f"""
{random.choice(emojis)} {encabezado}

{titulo}

{descripcion}

Más detalles aquí:
{link}

#Noticias #Actualidad #UltimoMomento
"""

    return texto


def publicar_facebook(texto, imagen):

    url = f"https://graph.facebook.com/{PAGE_ID}/photos"

    payload = {
        "url": imagen,
        "caption": texto,
        "access_token": PAGE_TOKEN
    }

    r = requests.post(url, data=payload)

    print(r.text)


def main():

    titulo, descripcion, imagen, link = obtener_noticia()

    if titulo:
        texto = crear_texto(titulo, descripcion, link)
        publicar_facebook(texto, imagen)
        print("Noticia publicada")
    else:
        print("No se encontró noticia nueva")


if __name__ == "__main__":
    main()
