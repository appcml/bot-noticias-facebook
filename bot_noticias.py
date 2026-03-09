# ============================================================================
# BUCLE INFINITO - EJECUCIÓN AUTOMÁTICA CADA 30 MINUTOS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("🤖 BOT DE NOTICIAS - MODO AUTOMÁTICO ACTIVADO")
    print(f"⏱️  Intervalo: Cada {INTERVALO_MINUTOS} minutos")
    print("🛑 Presiona Ctrl+C para detener")
    print("🚀" * 30 + "\n")
    
    contador = 0
    
    while True:
        contador += 1
        print(f"\n{'='*60}")
        print(f"🔄 CICLO #{contador} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # Ejecutar publicación
            exito = main()
            
            if exito:
                print(f"\n✅ Ciclo completado exitosamente")
            else:
                print(f"\n⚠️ Ciclo completado con errores")
            
            # Calcular tiempo de espera
            siguiente_ejecucion = datetime.now() + timedelta(minutes=INTERVALO_MINUTOS)
            print(f"\n⏳ Próxima ejecución: {siguiente_ejecucion.strftime('%H:%M:%S')}")
            print(f"💤 Esperando {INTERVALO_MINUTOS} minutos...")
            print("-" * 60)
            
            # Esperar el intervalo (con manejo de interrupción)
            time.sleep(INTERVALO_MINUTOS * 60)
            
        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print("🛑 BOT DETENIDO POR EL USUARIO (Ctrl+C)")
            print(f"📊 Total de ciclos ejecutados: {contador}")
            print(f"{'='*60}\n")
            break
            
        except Exception as e:
            print(f"\n❌ ERROR EN EL CICLO: {str(e)}")
            print("🔄 Reintentando en 5 minutos...")
            time.sleep(300)  # 5 minutos de espera en caso de error
            continue
