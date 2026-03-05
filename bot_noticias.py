import requests
import random
from datetime import datetime

# ===== CONFIGURACIÓN =====

PAGE_ID = "TU_PAGE_ID"
ACCESS_TOKEN = "TU_ACCESS_TOKEN"

# API de noticias (gratuita)
NEWS_API_KEY = "TU_API_KEY_NEWSAPI"

# ===== OBTENER NOTICIA =====

def obtener_noticia():
    url = f"https://newsapi.org/v2/top-headlines?language=es&pageSize=10&apiKey={NEWS_API_KEY}"
    r = requests.get(url)
    data = r.json()

    articulo = random.choice(data["articles"])

    titulo = articulo["title"]
    descripcion = articulo["description"]
    imagen = articulo["urlToImage"]

    return titulo, descripcion, imagen


# ===== GENERAR TEXTO PERIODÍSTICO =====

def crear_publicacion(titulo, descripcion):

    texto = f"""
📰 ÚLTIMO MOMENTO

{titulo}

{descripcion}

📌 Mantente informado con Verdad Hoy: Noticias al Minuto.

#Noticias #Actualidad #UltimoMomento
"""

    return texto


# ===== PUBLICAR EN FACEBOOK =====

def publicar_facebook(texto, imagen):

    url = f"https://graph.facebook.com/{PAGE_ID}/photos"

    payload = {
        "url": imagen,
        "caption": texto,
        "access_token": ACCESS_TOKEN
    }

    r = requests.post(url, data=payload)

    print("Respuesta Facebook:", r.json())


# ===== EJECUCIÓN =====

def main():

    titulo, descripcion, imagen = obtener_noticia()

    texto = crear_publicacion(titulo, descripcion)

    publicar_facebook(texto, imagen)

    print("Publicación realizada:", datetime.now())


if __name__ == "__main__":
    main()
