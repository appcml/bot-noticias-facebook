def main():
    """Función principal que publica UNA noticia nueva"""
    print("\n" + "="*60)
    print("INICIANDO PUBLICACIÓN")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)
    
    # Verificar credenciales
    print(f"\n🔐 Verificando credenciales:")
    print(f"   FB_PAGE_ID: {'✅ Configurado' if FB_PAGE_ID else '❌ FALTA'}")
    print(f"   FB_ACCESS_TOKEN: {'✅ Configurado' if FB_ACCESS_TOKEN else '❌ FALTA'}")
    print(f"   NEWS_API_KEY: {'✅ Configurado' if NEWS_API_KEY else '⚠️ Opcional'}")
    print(f"   OPENROUTER_API_KEY: {'✅ Configurado' if OPENROUTER_API_KEY else '⚠️ Opcional'}")
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("❌ ERROR: Faltan credenciales de Facebook obligatorias")
        return False
    
    historial = cargar_historial()
    print(f"\n📚 Historial cargado:")
    print(f"   - URLs guardadas: {len(historial.get('urls', []))}")
    print(f"   - Hashes guardados: {len(historial.get('hashes', []))}")
    print(f"   - Última publicación: {historial.get('ultima_publicacion', 'Nunca')}")
    
    noticias = buscar_noticias()
    print(f"\n📰 Total noticias encontradas: {len(noticias)}")
    
    if not noticias:
        print("❌ ERROR: No se encontraron noticias en ninguna fuente")
        return False
    
    # Mostrar primeras 3 noticias encontradas
    print(f"\n📝 Primeras noticias encontradas:")
    for i, n in enumerate(noticias[:3]):
        print(f"   {i+1}. {n['titulo'][:50]}... (viral: {n['puntaje_viral']})")
    
    seleccionada = filtrar_y_seleccionar(noticias, historial)
    
    if not seleccionada:
        print("\n⚠️ No se encontraron noticias NUEVAS para publicar")
        print("   Posibles causas:")
        print("   - Todas las noticias ya fueron publicadas anteriormente")
        print("   - Las noticias no tienen suficiente puntaje viral")
        print("   - Fuentes RSS no están respondiendo")
        return False
    
    print(f"\n✍️ Redactando noticia...")
    redaccion = generar_redaccion_profesional(
        seleccionada['titulo'],
        seleccionada['texto_completo'],
        seleccionada['descripcion'],
        seleccionada['fuente']
    )
    
    hashtags = generar_hashtags(
        seleccionada['categoria'],
        seleccionada['pais'],
        seleccionada['titulo']
    )
    
    print(f"\n🖼️ Descargando imagen...")
    imagen_path = descargar_imagen(seleccionada['imagen'])
    
    if not imagen_path and seleccionada.get('texto_completo'):
        urls_img = re.findall(r'https?://[^\s"\']+\.(?:jpg|jpeg|png)', seleccionada['texto_completo'])
        print(f"   Buscando imágenes en texto: {len(urls_img)} encontradas")
        for url_img in urls_img[:2]:
            imagen_path = descargar_imagen(url_img)
            if imagen_path:
                break
    
    if not imagen_path:
        print("❌ ERROR: No se pudo descargar ninguna imagen")
        return False
    
    print(f"\n📤 Publicando en Facebook...")
    exito = publicar_facebook(
        seleccionada['titulo'],
        redaccion,
        imagen_path,
        hashtags
    )
    
    if exito:
        guardar_historial(historial, seleccionada['url'], seleccionada['titulo'])
        
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n" + "="*60)
        print("✅ PUBLICACIÓN EXITOSA")
        print("="*60)
        return True
    else:
        try:
            if os.path.exists(imagen_path):
                os.remove(imagen_path)
        except:
            pass
        
        print("\n❌ Falló la publicación en Facebook")
        return False
