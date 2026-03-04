    descripcion = noticia['description']
    fuente = noticia.get('source', {}).get('name', 'Medios internacionales')
    
    tono = detectar_tono(titulo, descripcion)
    
    palabras_clave = [w for w in re.findall(r'\b[A-Za-zÁáÉéÍíÓóÚúÑñ]{4,}\b', titulo) 
                     if w.lower() not in ['como', 'para', 'pero', 'con', 'los', 'las', 'del', 'por', 'una', 'este', 'esta', 'desde', 'entre', 'sobre', 'hacia']]
    palabra_destacada = random.choice(palabras_clave) if palabras_clave else "este hecho"
    
    aperturas = {
        'crisis': {
            'grave': [
                f"La situación en torno a {palabra_destacada} ha alcanzado un punto crítico que demanda atención inmediata de la comunidad internacional.",
                f"Nuevos desarrollos confirman la gravedad de {palabra_destacada}, generando alerta entre los principales actores geopolíticos.",
                f"El escenario de {palabra_destacada} se complica con información que revela la magnitud real de la crisis."
            ],
            'neutral': [
                f"Los acontecimientos recientes en torno a {palabra_destacada} están redefiniendo el panorama de seguridad internacional.",
                f"La evolución de {palabra_destacada} mantiene en vilo a observadores y autoridades por igual.",
                f"Analistas internacionales siguen de cerca {palabra_destacada} ante posibles repercusiones regionales."
            ]
        },
        'economia': {
            'grave': [
                f"Los mercados registran turbulencias significativas vinculadas a {palabra_destacada}, con proyecciones ajustadas a la baja.",
                f"La incertidumbre en torno a {palabra_destacada} ha activado señales de alerta en los principales centros financieros.",
                f"Inversores reevalúan estrategias ante el impacto potencial de {palabra_destacada} en la economía global."
            ],
            'positivo': [
                f"Indicadores recientes vinculados a {palabra_destacada} sugieren una recuperación más robusta de lo anticipado.",
                f"El desempeño de {palabra_destacada} supera expectativas, generando optimismo cauteloso entre analistas.",
                f"Nuevos datos sobre {palabra_destacada} confirman tendencias positivas para el cierre del período."
            ],
            'neutral': [
                f"Los mercados ajustan posiciones ante la última información disponible sobre {palabra_destacada}.",
                f"Especialistas financieros analizan el impacto a mediano plazo de {palabra_destacada} en diversos sectores.",
                f"La evolución de {palabra_destacada} será determinante para las proyecciones del próximo trimestre."
            ]
        },
        'tech': {
            'positivo': [
                f"El avance de {palabra_destacada} marca un hito significativo en la trayectoria de innovación tecnológica.",
                f"Desarrollos recientes en {palabra_destacada} prometen transformar la experiencia de usuarios y empresas.",
                f"La consolidación de {palabra_destacada} posiciona a los principales actores del sector en nueva fase competitiva."
            ],
            'analitico': [
                f"Un análisis profundo de {palabra_destacada} revela implicaciones que trascienden el ámbito tecnológico convencional.",
                f"Expertos evalúan el alcance real de {palabra_destacada} más allá de las primeras impresiones.",
                f"El estudio de {palabra_destacada} plantea interrogantes fundamentales sobre el rumbo de la industria."
            ],
            'neutral': [
                f"La industria tecnológica ajusta estrategias ante el creciente protagonismo de {palabra_destacada}.",
                f"Nuevas propuestas en torno a {palabra_destacada} generan debate entre desarrolladores y reguladores.",
                f"La adopción de {palabra_destacada} avanza a ritmo desigual según regiones y sectores."
            ]
        },
        'politica': {
            'grave': [
                f"La polarización en torno a {palabra_destacada} alcanza niveles que complican cualquier salida negociada.",
                f"La gravedad de {palabra_destacada} ha movilizado a actores hasta ahora al margen del debate público.",
                f"La crisis vinculada a {palabra_destacada} pone a prueba la estabilidad de alianzas tradicionales."
            ],
            'positivo': [
                f"Un acuerdo inesperado en torno a {palabra_destacada} abre posibilidades de diálogo antes descartadas.",
                f"El consenso alcanzado sobre {palabra_destacada} representa un paso significativo en la agenda legislativa.",
                f"Los avances en {palabra_destacada} superan las expectativas más optimistas de los negociadores."
            ],
            'neutral': [
                f"El debate en torno a {palabra_destacada} continúa con posiciones que muestran escasa flexibilidad.",
                f"Los actores políticos redefinen estrategias ante la complejidad de {palabra_destacada}.",
                f"La discusión sobre {palabra_destacada} anticipa una negociación prolongada en los próximos meses."
            ]
        },
        'emergencia': {
            'grave': [
                f"La magnitud de {palabra_destacada} supera las primeras estimaciones, ampliando la zona de afectación.",
                f"Equipos de rescate trabajan contra el tiempo ante la gravedad de {palabra_destacada}.",
                f"La comunidad se moviliza ante el impacto devastador de {palabra_destacada} en zonas pobladas."
            ],
            'neutral': [
                f"Las autoridades coordinan respuesta integral ante {palabra_destacada} en múltiples frentes.",
                f"El monitoreo constante de {palabra_destacada} permite ajustar protocolos en tiempo real.",
                f"La experiencia previa en situaciones similares a {palabra_destacada} orienta la respuesta actual."
            ]
        }
    }
    
    cat_aperturas = aperturas.get(categoria, aperturas['crisis'])
    tono_aperturas = cat_aperturas.get(tono, cat_aperturas.get('neutral', cat_aperturas.get('grave')))
    apertura = random.choice(tono_aperturas)
    
    desarrollos = {
        'crisis': [
            f"Fuentes oficiales confirman que la situación evoluciona rápidamente, con actualizaciones cada pocas horas. Los análisis preliminares sugieren que los efectos podrían extenderse más allá de las fronteras inmediatas.",
            f"La comunidad internacional ha comenzado a articular una respuesta coordinada, aunque persisten diferencias sobre la estrategia más efectiva. Los organismos multilaterales mantienen reuniones de emergencia.",
            f"Especialistas en seguridad advierten que el escenario actual podría estabilizarse o deteriorarse en las próximas 48 horas, dependiendo de decisiones clave que aún están pendientes."
        ],
        'economia': [
            f"Los datos más recientes indican una volatilidad que podría mantenerse durante la semana. Los inversores institucionales recomiendan cautela y diversificación de carteras ante la incertidumbre.",
            f"Las proyecciones de los principales bancos de inversión muestran dispersión significativa, reflejando la dificultad de anticipar el desenlace de los factores en juego.",
            f"El sector empresarial ha manifestado preocupación por el impacto en cadenas de suministro y costos operativos, solicitando claridad en las políticas públicas a implementar."
        ],
        'tech': [
            f"Los competidores directos aceleran sus propios desarrollos en respuesta, anticipando una oleada de lanzamientos en el próximo trimestre. La presión por innovar se intensifica en todo el sector.",
            f"Expertos en ética tecnológica plantean interrogantes sobre las implicaciones sociales de estas capacidades, proponiendo marcos de regulación que aún no existen en la mayoría de jurisdicciones.",
            f"La adopción temprana por parte de grandes corporaciones sugiere una maduración más rápida de lo habitual, aunque la accesibilidad para usuarios individuales podría demorar varios meses."
        ],
        'politica': [
            f"Los sondeos de opinión pública muestran división acerca de la conveniencia de la medida, con diferencias marcadas según edad, región y nivel educativo de los consultados.",
            f"La agenda mediática de las próximas semanas estará dominada por este tema, con audiencias parlamentarias y foros públicos donde se expondrán argumentos encontrados.",
            f"Analistas políticos anticipan que la resolución de este asunto definirá las coaliciones de poder para el período legislativo venidero, con consecuencias que se extenderán por años."
        ],
        'emergencia': [
            f"Los protocolos de atención a damnificados han sido activados en coordinación con organizaciones de la sociedad civil. Se establecen centros de acopio y albergues temporales en puntos estratégicos.",
            f"La evaluación de daños materiales continúa, con cifras preliminares que probablemente se revisarán al alza conforme avancen los equipos de inspección por zonas de difícil acceso.",
            f"La solidaridad internacional se manifiesta mediante ofertas de asistencia técnica y recursos que serán canalizados a través de los mecanismos establecidos de cooperación."
        ]
    }
    
    desarrollos_cat = desarrollos.get(categoria, desarrollos['crisis'])
    desarrollo = random.choice(desarrollos_cat)
    
    cierres = {
        'grave': [
            "La situación permanece fluida y requiere monitoreo constante.",
            "Se esperan desarrollos significativos en las próximas horas.",
            "La comunidad internacional mantiene alerta máxima."
        ],
        'positivo': [
            "Los avances confirmados abren perspectivas prometedoras.",
            "El seguimiento de estos desarrollos continuará en próximas actualizaciones.",
            "Los actores involucrados expresan cauteloso optimismo."
        ],
        'analitico': [
            "El análisis profundo de estos datos continuará en reportes posteriores.",
            "Las implicaciones completas se comprenderán mejor con el paso de los días.",
            "Expertos convienen en que el estudio de este fenómeno apenas comienza."
        ],
        'neutral': [
            "Los detalles adicionales se conocerán conforme avancen las investigaciones.",
            "La cobertura de este tema continuará con actualizaciones pertinentes.",
            "Se mantiene contacto con fuentes para ampliar esta información."
        ]
    }
    
    cierre = random.choice(cierres.get(tono, cierres['neutral']))
    
    texto_redactado = f"{apertura}\n\n{descripcion}\n\n{desarrollo}\n\n{cierre}"
    
    return texto_redactado

def redactar_noticia(noticia, categoria):
    titulo = noticia['title']
    url = noticia['url']
    fuente = noticia.get('source', {}).get('name', 'Medios internacionales')
    
    cuerpo = generar_redaccion_inteligente(noticia, categoria)
    hashtags = generar_hashtags(titulo, categoria)
    
    mensaje = f"""📰 {titulo}

{cuerpo}

📡 Fuente: {fuente}
🔗 {url}

{hashtags}

— Verdad Hoy: Noticias Al Minuto"""
    
    return mensaje

def generar_hashtags(titulo, categoria):
    tags_base = {
        'crisis': ['#ActualidadInternacional', '#CrisisGlobal'],
        'economia': ['#Economía', '#Mercados'],
        'tech': ['#Tecnología', '#Innovación'],
        'politica': ['#Política', '#Gobierno'],
        'emergencia': ['#ÚltimaHora', '#Emergencia']
    }
    
    base = tags_base.get(categoria, ['#Noticias'])
    
    titulo_lower = titulo.lower()
    if any(p in titulo_lower for p in ['eeuu', 'estados unidos', 'biden', 'trump']):
        base.append('#EEUU')
    elif 'mexico' in titulo_lower:
        base.append('#México')
    elif any(p in titulo_lower for p in ['iran', 'israel', 'palestina', 'gaza']):
        base.append('#MedioOriente')
    elif 'ucrania' in titulo_lower or 'rusia' in titulo_lower:
        base.append('#Ucrania')
    
    base.append(f"#{datetime.now().strftime('%Y')}")
    
    return ' '.join(base[:4])

def publicar_en_facebook():
    global HISTORIAL_URLS
    
    noticias = buscar_noticias_frescas()
    
    if not noticias:
        print("[AVISO] No hay noticias nuevas disponibles")
        return False
    
    noticia = noticias[0]
    categoria = noticia['categoria']
    
    HISTORIAL_URLS.add(noticia['url'])
    if len(HISTORIAL_URLS) > MAX_HISTORIAL:
        HISTORIAL_URLS.pop()
    
    print(f"\n[SELECCIONADA] {noticia['title'][:60]}...")
    print(f"  Score: {noticia['score']} | Categoría: {categoria}")
    
    mensaje = redactar_noticia(noticia, categoria)
    
    try:
        print("[INFO] Publicando en Facebook...")
        url_fb = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        payload = {
            'message': mensaje,
            'access_token': FB_ACCESS_TOKEN,
            'link': noticia['url']
        }
        response = requests.post(url_fb, data=payload, timeout=30)
        
        result = response.json()
        print(f"[DEBUG] Status: {response.status_code}")
        print(f"[DEBUG] Response: {result}")
        
        if response.status_code == 200 and 'id' in result:
            print(f"✅ PUBLICADO: {result['id']}")
            return True
        else:
            error_msg = result.get('error', {}).get('message', 'Error desconocido')
            print(f"❌ ERROR DE FACEBOOK: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 VERDAD DE HOY - GitHub Actions")
    print("="*60)
    exit_code = 0 if publicar_en_facebook() else 1
    exit(exit_code)