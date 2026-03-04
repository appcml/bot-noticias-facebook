def publicar_en_facebook(titulo, contenido, resumen_seo, palabras_clave, imagen_path, url_fuente, nombre_fuente):
    """
    Publica correctamente una imagen + texto en Facebook usando Graph API.
    Luego agrega comentario con el link original.
    """

    print("\n[FACEBOOK] Iniciando publicación...")

    hashtags = ' '.join([f"#{kw.replace(' ', '')}" for kw in palabras_clave[:4]])

    mensaje_principal = f"""📰 {titulo}

{resumen_seo}

{hashtags}

— Verdad Hoy | {datetime.now().strftime('%d/%m/%Y')}"""

    try:
        # ==========================================
        # PASO 1: SUBIR IMAGEN SIN PUBLICAR
        # ==========================================
        if imagen_path and os.path.exists(imagen_path):

            print("[FACEBOOK] Subiendo imagen primero (modo seguro)...")

            url_foto = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"

            mime_type = "image/png"
            if imagen_path.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"

            with open(imagen_path, "rb") as img:
                files = {
                    "source": (os.path.basename(imagen_path), img, mime_type)
                }

                data = {
                    "access_token": FB_ACCESS_TOKEN,
                    "published": False
                }

                response = requests.post(url_foto, files=files, data=data, timeout=60)
                result = response.json()

                print("[DEBUG FOTO]", result)

                if response.status_code != 200 or "id" not in result:
                    print("[ERROR] No se pudo subir la imagen.")
                    return publicar_solo_texto(mensaje_principal, url_fuente)

                media_id = result["id"]

            # ==========================================
            # PASO 2: CREAR POST CON IMAGEN ADJUNTA
            # ==========================================
            print("[FACEBOOK] Creando post con imagen adjunta...")

            url_post = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"

            data_post = {
                "message": mensaje_principal,
                "attached_media": json.dumps([{"media_fbid": media_id}]),
                "access_token": FB_ACCESS_TOKEN
            }

            response_post = requests.post(url_post, data=data_post, timeout=60)
            result_post = response_post.json()

            print("[DEBUG POST]", result_post)

            if response_post.status_code == 200 and "id" in result_post:
                post_id = result_post["id"]
                print("[FACEBOOK] ✓ Publicación creada correctamente")
            else:
                print("[ERROR] Falló crear el post final.")
                return False

        else:
            print("[FACEBOOK] No hay imagen válida, publicando solo texto.")
            post_id = publicar_solo_texto(mensaje_principal, url_fuente)
            if not post_id:
                return False

        # ==========================================
        # PASO 3: AGREGAR COMENTARIO CON LINK
        # ==========================================
        if post_id and url_fuente:

            print("[FACEBOOK] Agregando comentario con link...")

            url_comment = f"https://graph.facebook.com/v19.0/{post_id}/comments"

            mensaje_comentario = f"""📎 Fuente original: {nombre_fuente}

🔗 {url_fuente}

#Noticias #Actualidad"""

            data_comment = {
                "message": mensaje_comentario,
                "access_token": FB_ACCESS_TOKEN
            }

            requests.post(url_comment, data=data_comment)

        return True

    except Exception as e:
        print("[ERROR FACEBOOK]", e)
        return False
