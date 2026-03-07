# Al final del archivo, reemplazar el if __name__ == "__main__":
if __name__ == "__main__":
    import time
    while True:
        try:
            main()
            print(f"\n⏳ Esperando 30 minutos... ({datetime.now().strftime('%H:%M')})")
            time.sleep(1800)  # 30 minutos = 1800 segundos
        except Exception as e:
            print(f"💥 Error: {e}")
            time.sleep(300)  # Si hay error, esperar 5 minutos y reintentar
