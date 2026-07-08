#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales - V17.9.11
CAMBIOS EN V17.9.11 (9 de 13 fuentes RSS de Chile estaban muertas — HTTP 404):
  - DIAGNÓSTICO CONFIRMADO con el log real: La Tercera, BioBioChile,
    Cooperativa (URL vieja), T13, Diario Financiero, El Mostrador, 24 Horas,
    Mega Noticias, CHV Noticias y Publimetro devolvían HTTP 404 — NO era un
    bloqueo temporal de red, son URLs de RSS que esos medios ya no publican.
    Solo Emol (reset de conexión intermitente), CNN Chile y La Cuarta
    devolvían HTTP 200.
  - INVESTIGACIÓN: busqué reemplazos para cada fuente muerta. La mayoría de
    esos medios chilenos parecen haber descontinuado su RSS público por
    completo (tendencia general del rubro en los últimos años) — no
    encontré URLs de reemplazo confiables para 8 de las 9.
  - FIX CONFIRMADO: Cooperativa SÍ mantiene RSS vivo, solo que en otra ruta:
    https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml
    (categoría "País" — la más parecida a noticias generales de Chile).
    Encontrado en su propia página "RSS a la carta".
  - FIX: se eliminan las 8 fuentes sin reemplazo confiable de fuentes_chile
    en obtener_rss_chile(). Quedan 4: Emol, Cooperativa (URL corregida),
    CNN Chile, La Cuarta. Es una lista más corta, pero con URLs reales en
    vez de URLs muertas que solo agregaban tiempo de ejecución y ruido al
    log sin aportar ninguna noticia.
  - IMPORTANTE: no pude probar en vivo la URL corregida de Cooperativa desde
    mi entorno de pruebas (Claude tiene una lista blanca de dominios de red
    y cooperativa.cl no está en ella — el error que me devolvió fue de mi
    propio proxy, no de Cooperativa). La validé por otra vía (su propia
    página de suscripción RSS), pero la prueba real es la próxima ejecución
    del bot en GitHub Actions, que sí tiene acceso completo a internet.
  - Con solo 4 fuentes RSS, el bloque de Chile depende más de NewsAPI Chile
    para tener volumen — si en el próximo log NewsAPI Chile también aparece
    en 0, revisar cuota diaria de NewsAPI (planes gratis suelen tener
    límite ~100 solicitudes/día, y el bot hace varias decenas por día
    sumando los 3 flujos).

CAMBIOS EN V17.9.10 (Visibilidad + reintento en RSS Chile — Emol falla seguido):
  - CONTEXTO: "RSS Chile: 0 noticias" con solo 1 de las 13 fuentes mostrando
    error (Emol: Connection reset by peer) — las otras 12 fallaban en
    silencio (HTTP != 200 o feed vacío) sin quedar registrado en el log,
    haciendo imposible saber cuál era el verdadero cuello de botella.
  - FIX: obtener_rss_chile() ahora loguea (nivel debug) cuándo una fuente
    devuelve un HTTP distinto de 200 o un feed sin entradas, no solo cuando
    hay una excepción de conexión.
  - FIX: reintento automático (1 vez, con 1.5s de espera) ante errores de
    conexión/timeout — Emol resetea la conexión de forma intermitente, y en
    varios casos un segundo intento sí funciona. Esto no es un bug del bot:
    es el servidor de Emol rechazando la conexión momentáneamente, algo que
    no podemos controlar del todo, pero el reintento recupera parte de esos
    casos sin intervención manual.
  - Si en las próximas corridas Emol sigue fallando incluso con reintento,
    lo más probable es que esté bloqueando el rango de IPs de GitHub
    Actions — en ese caso no hay mucho que hacer desde el código, las otras
    12 fuentes RSS + NewsAPI Chile siguen cubriendo el bloque igual.

CAMBIOS EN V17.9.9 (Confirmación de slugs + eliminada región "América del Norte"):
  - CONFIRMADO: Cic revisó Entradas → Categorías en WordPress y los 8 slugs
    adivinados en V17.9.8 eran todos correctos (africa, america-del-norte,
    asia, europa, medio-oriente, mundo, oceania, latinoamerica, internacional).
  - CAMBIO: se elimina "América del Norte" como región propia — tenía 0
    artículos y muy bajo volumen esperado (las noticias de EE.UU./Canadá que
    importan a la audiencia ya van directo a "Política" o "Economía"; lo
    poco que quedaba para esta subcategoría era casi siempre desastre/crimen
    puntual). Decisión de Cic tras evaluar el trade-off.
  - Esas noticias ahora caen en "Mundo" (categoría ya existente, con tráfico
    real) en vez de crear/mantener una subcategoría vacía en el menú.
  - ACCIÓN MANUAL PENDIENTE PARA TI: borrar la categoría "América del Norte"
    (slug america-del-norte) desde WordPress → Entradas → Categorías — el
    bot ya no la usa, pero WordPress no la borra solo.
  - Europa, Asia, África, Medio Oriente, Oceanía y Latinoamérica no cambian.

CAMBIOS EN V17.9.8 (Distribución completa por las subcategorías reales del
menú "Internacional": Europa, Asia, África, América del Norte, Medio
Oriente, Oceanía, Latinoamérica, Mundo):
  - CONTEXTO: el menú real de verdadhoy.com tiene "Internacional" como
    categoría padre con 8 hijas (Europa/Asia/África/América del Norte/
    Medio Oriente/Oceanía/Latinoamérica/Mundo). El bot solo conocía el slug
    plano 'internacional' y nunca distribuía por región — todo lo que no
    era LATAM cataba en el mismo cajón.
  - NUEVO: KEYWORDS_REGIONES + detectar_region_internacional() — detecta,
    por conteo de coincidencias de país/ciudad/líder, si una noticia
    "paraguas" (desastre, guerra, crimen, religion, educacion, general,
    mundo) pertenece a Europa, Asia, África, América del Norte, Medio
    Oriente u Oceanía. Si no hay ninguna coincidencia clara, cae en "Mundo"
    (fallback seguro para temas multilaterales: ONU, cambio climático
    global, etc.). LATAM se sigue resolviendo primero (V17.9.7) con las
    listas KEYWORDS_CHILE/KEYWORDS_LATAM_PAISES ya existentes.
  - La región/país detectado pasa a ser la categoría PRINCIPAL, con
    "Internacional" como categoría SECUNDARIA (el artículo sigue apareciendo
    también en el listado general de Internacional).
  - RED DE SEGURIDAD: si el slug de una región no existe en WordPress (ver
    REGION_SLUG_WP — son mi mejor estimación de cómo WordPress genera esos
    slugs, ej. "América del Norte" → "america-del-norte"), el artículo cae
    en 'internacional' en vez de quedar sin categoría.
  - ⚠️ ACCIÓN PENDIENTE PARA TI: verifica en WordPress (Entradas → Categorías)
    los slugs REALES de Europa, Asia, África, América del Norte, Medio
    Oriente y Oceanía, y compáralos con REGION_SLUG_WP más abajo en este
    archivo. Si alguno no coincide, dime el slug correcto y lo corrijo.
  - Categorías temáticas (política, economía, tecnología, deportes,
    entretenimiento, ciencia-y-salud, medio-ambiente) NO cambian — siguen
    siendo su propio nivel del menú principal, esto solo afecta a la rama
    de "Internacional".

CAMBIOS EN V17.9.7 (Desastres/guerra/crimen en LATAM → categoría Latinoamérica):
  - CASO REAL: "Terremotos en Venezuela" se publicó en la categoría
    "Internacional" en vez de "Latinoamérica". No era un bug de clasificación
    de la IA — es el diseño original: CATEGORIA_WP mapea 'desastre' siempre
    a 'internacional' (correcto para un terremoto en Japón o Turquía, pero
    para un sitio LATAM-first, un desastre en Venezuela/Chile/México se
    pierde en el cajón genérico de Internacional en vez de reforzar la
    sección regional).
  - FIX: en publicar_en_wordpress(), si la categoría es 'desastre', 'guerra'
    o 'crimen' Y el artículo menciona un país de LATAM (usando las mismas
    listas KEYWORDS_CHILE / KEYWORDS_LATAM_PAISES del bloque LATAM), la
    categoría PRINCIPAL pasa a ser "Latinoamérica", y "Internacional" queda
    como categoría SECUNDARIA — el artículo sigue apareciendo en ambas
    secciones, pero prioriza la que más le importa a la audiencia del sitio.
  - Un desastre/guerra/crimen fuera de LATAM (Japón, Medio Oriente, etc.)
    sigue yendo a "Internacional" sin cambios — el criterio es puramente
    geográfico (país detectado por keyword), no cambia nada más.

CAMBIOS EN V17.9.6 (FIX: se coló un artículo de apuestas — riesgo AdSense):
  - CASO REAL: se publicó "Cuotas para el Mundial 2026" (cuotas de casas de
    apuestas, favoritos, "casa de apuestas" en el cuerpo) sin ser detectado
    como spam/apuestas.
  - CAUSA #1: el bloque LATAM (publicar_bloque_latam_chile, la mitad "LATAM
    sin Chile") NUNCA tuvo el filtro es_contenido_spam() — solo lo tenía la
    mitad de Chile y el flujo general. Esta noticia venía de una fuente
    peruana (RPP), así que pasó por el bloque que no tenía ningún filtro.
  - CAUSA #2: el filtro solo revisaba título+descripción de la fuente, nunca
    el contenido completo del artículo. El titular de origen era genérico
    ("Cuotas y favoritos"), sin ninguna palabra de la lista negra — la
    mención explícita a "casa de apuestas" solo aparecía en el cuerpo.
  - FIX: se agrega el filtro es_contenido_spam() al bloque LATAM (faltaba
    por completo).
  - FIX: en las 3 rutas (general, Chile, LATAM) ahora se revisa el contenido
    DOS veces — antes de scrapear (título+desc, barato, descarta rápido los
    casos obvios) y después de extraer el contenido completo (título+cuerpo,
    atrapa los casos donde el enfoque de apuestas solo aparece en el texto).
  - BLACKLIST ampliada con términos genéricos de cuotas/pronósticos que no
    requieren nombrar una casa de apuestas específica: "cuotas para el
    mundial", "cuotas y favoritos", "pronóstico deportivo", "para apostar",
    "dónde apostar", "favoritos para ganar el mundial", etc.
  - Motivo editorial: contenido de apuestas es una de las categorías de
    mayor riesgo de desmonetización/rechazo en AdSense — mejor perder
    ocasionalmente una noticia deportiva legítima con vocabulario ambiguo
    que arriesgar la cuenta.

CAMBIOS EN V17.9.5 (Groq como proveedor de IA gratuito — principal):
  - CONTEXTO: OpenRouter y OpenAI se quedaron sin saldo el mismo día
    (ver V17.9.4). En vez de solo recargar saldo, se agrega Groq como
    proveedor GRATUITO (sin tarjeta, para siempre dentro de límites de uso
    normales) y se lo pone primero en la cola.
  - FIX: reescribir_noticia_v9() y generar_metadatos_video_manual() ahora
    arman una lista ordenada de proveedores según qué API keys existan:
    Groq → OpenRouter → OpenAI. Prueba el primero; si falla, prueba el
    siguiente automáticamente, sin intervención manual. Groq es compatible
    con el formato "estilo OpenAI" (mismo esquema de chat/completions), así
    que no hizo falta tocar el parseo de la respuesta ni el prompt.
  - MODELO: Groq usa "llama-3.3-70b-versatile" (open-source, gratis, con
    capacidad de sobra para reescribir noticias de 550-800 palabras).
  - NUEVA VARIABLE DE ENTORNO: GROQ_API_KEY (agregar como secret en GitHub
    Actions). Si no está configurada, el bot simplemente la salta y usa
    OpenRouter/OpenAI como antes — no rompe nada para quien no la use.
  - LÍMITES DE GROQ (referencia, pueden variar por modelo): del orden de
    cientos a miles de solicitudes/día gratis. Con 12 artículos/día del bot,
    queda muchísimo margen — no debería acercarse al límite en uso normal.
  - PENDIENTE PARA TI: agregar el secret GROQ_API_KEY en el .yml del
    workflow (se entrega el .yml actualizado aparte).

CAMBIOS EN V17.9.4 (Fix del run real que reportaste — HTTP 402 OpenRouter):
  - CAUSA CONFIRMADA del "fallo": OpenRouter devolvió HTTP 402 "This request
    requires more credits... You requested up to 3500 tokens, but can only
    afford 3390" en las 6 noticias candidatas del bloque LATAM. Es decir: la
    cuenta de OpenRouter tiene saldo casi en cero (le faltaban ~110 tokens de
    presupuesto). El bot descartó correctamente las 6 noticias (tal como se
    diseñó en V17.9.3) en vez de publicarlas con contenido pobre — eso YA
    funcionó bien. Lo que faltaba era no rendirse ahí mismo.
  - FIX: fallback automático OpenRouter → OpenAI. Si el proveedor principal
    (OpenRouter) fallla por falta de crédito o rate limit, y hay una
    OPENAI_API_KEY configurada, el bot reintenta automáticamente con OpenAI
    directo antes de descartar la noticia. Requiere que OPENAI_API_KEY tenga
    saldo propio — si ambas cuentas están sin crédito, seguirá sin publicar
    (correctamente: es preferible no publicar a publicar contenido pobre).
  - FIX: se quita el exit(1) que marcaba la corrida de GitHub Actions como
    "fallida" (❌ roja) solo porque no se publicó nada en ese ciclo. Eso
    generaba alarmas falsas: "no publiqué esta vez" (sin crédito, sin
    candidatas, cuota llena) NO es un error del workflow. Los errores reales
    (excepciones no controladas) siguen marcando la corrida como fallida,
    igual que antes.
  - ACCIÓN PENDIENTE PARA TI: recargar saldo en OpenRouter
    (https://openrouter.ai/settings/credits) es la solución real y definitiva.
    El fallback a OpenAI es una red de seguridad, no un reemplazo — si OpenAI
    tampoco tiene saldo, el bot seguirá sin publicar esos ciclos.

CAMBIOS EN V17.9.3 (FIX CRÍTICO: eliminado el fallback sin IA que publicaba
contenido pobre — ver caso real "Senado se prepara para rechazar AC..."):
  - DIAGNÓSTICO: la nota sobre Chile publicada en verdadhoy.com no pasó por la
    IA. reescribir_noticia_v9() falló (probable error de API/créditos/rate
    limit — hay que revisar logs de esa ejecución puntual para confirmar la
    causa exacta) y publicar_en_wordpress() cayó al bloque `else` de
    emergencia, que tomaba las 2-3 oraciones originales, las repetía en el
    box "Puntos clave" Y en el cuerpo del artículo, sin H2, sin desarrollo,
    sin ningún valor editorial. Se publicó igual porque ese fallback solo
    exigía un mínimo de 3 oraciones.
  - FIX CRÍTICO: se ELIMINA por completo el fallback sin IA. Si
    reescribir_noticia_v9() falla, publicar_en_wordpress() ahora retorna None
    y esa noticia se descarta — main() y publicar_bloque_latam_chile() ya
    estaban preparados para probar la siguiente candidata en ese caso, así
    que este cambio no requirió tocar la lógica de los llamadores.
    Filosofía: mejor publicar MENOS artículos (o ninguno, en el peor caso)
    que publicar contenido sin valor editorial que arriesgue AdSense otra vez.
  - FIX: umbrales mínimos de contenido subidos en las 3 fuentes (general,
    Chile, LATAM): contenido web 300→500 chars, solo-descripción 200→400,
    combinado web+desc 150→250. Una fuente de 200 caracteres alcanzaba para
    "pasar" el filtro pero no da material suficiente para que la IA escriba
    un artículo real — subir el umbral reduce cuántas veces se intenta con
    material demasiado escaso en primer lugar.
  - IMPORTANTE: esto NO explica por qué la IA falló esa vez en particular.
    Para diagnosticar la causa exacta (créditos, rate limit, modelo caído)
    hay que revisar el log de esa ejecución en GitHub Actions — el bot ya
    imprime el diagnóstico (💳 sin créditos / ⏳ rate limit / 🔑 API key /
    🤖 modelo no disponible) desde V17.6.9, solo falta mirarlo.

CAMBIOS EN V17.9.2 (Ajuste de timing tras revisar el .yml real):
  - DESCUBRIMIENTO CLAVE: el workflow de GitHub Actions NUNCA seteaba la
    variable MODO_LATAM. Resultado: publicar_bloque_latam_chile() jamás se
    ejecutaba en producción — todo el trabajo de Chile/LATAM (V17.3 en
    adelante) estaba vivo en el código pero no se usaba nunca.
  - DESCUBRIMIENTO: el workflow tampoco guardaba estado_cuotas_latam.json
    en el commit de estado. Aunque se activara MODO_LATAM, los contadores
    diarios de Chile/LATAM se habrían reseteado en cada ejecución y la cuota
    diaria (3/3) no se habría respetado entre corridas.
  - FIX (bot): TIEMPO_ENTRE_WP_MIN subido de 60 a 230 min. Con
    MAX_POSTS_WP_DIA=6, un gate de 60 min permitía gastar toda la cuota del
    día en las primeras 6 horas y quedar sin publicar el resto del día.
    230 min reparte las 6 notas a lo largo de las 24 horas.
  - FIX (bot): margen de tolerancia del gate de WP subido de 5 a 15 min,
    proporcional al nuevo intervalo (evita falsos negativos por delay de
    push de GitHub Actions).
  - NOTA: el archivo .yml correspondiente se entrega aparte, con MODO_LATAM
    conectado a un segundo cron 3 veces/día y estado_cuotas_latam.json
    agregado al commit/artefacto de estado.

CAMBIOS EN V17.9.1 (Arranque conservador — bajar el total diario a 12):
  - CUOTAS: total diario bajado de 44 a 12 artículos/día para partir más despacio
    mientras se valida la calidad del contenido y el comportamiento de AdSense.
    MAX_POSTS_WP_DIA 24→6, MAX_POSTS_WP_DIA_CHILE 8→3, MAX_POSTS_WP_DIA_LATAM 12→3.
  - Nada más cambió: el scoring por país, el filtro anti-España y el prompt del
    Editor Jefe (V17.9.0) siguen exactamente igual — solo se redujeron los topes.
  - Para subir el total más adelante, basta con volver a subir estas 3 constantes;
    no hace falta tocar nada más del bot.

CAMBIOS EN V17.9.0 (Editor Jefe — scoring por país/tema + autovalidación IA):
  - PUNTAJE: calcular_puntaje() reemplaza el bono LATAM plano (V17.6) por un
    sistema de NIVELES por país, igual que pediste (Chile > México/Brasil/
    Argentina > Colombia/Perú > resto de Sudamérica > Centroamérica > Caribe),
    más un bono editorial por tema prioritario (economía, tecnología, política,
    salud, medio ambiente, deportes). Esto es el "editor de selección": evalúa
    TODAS las candidatas en Python (gratis e instantáneo) antes de que la IA
    escriba nada — no hace falta gastar tokens de IA en elegir, solo en redactar.
  - IMPORTANTE (arquitectura): no implementamos un "editor de selección" con IA
    que revise cientos de noticias a la vez, porque sería mucho más lento y caro
    (habría que mandarle 50-100 titulares en cada llamada) sin mejorar el
    resultado — el scoring por keywords ya cubre ese trabajo a costo cero.
  - PROMPT IA: se agrega el ELEMENTO extra "Tercer H2" para llegar a 4 subtítulos
    H2 obligatorios (antes eran 3), igual que en tu checklist manual.
  - PROMPT IA: keyword principal ahora debe aparecer antes de la palabra 100
    (antes decía "antes de la palabra 150"), para acercarse más a Yoast verde.
  - PROMPT IA: se agrega el bloque "AUTOVALIDACIÓN OBLIGATORIA ANTES DE RESPONDER"
    con el checklist que usas para la edición manual (keyword en título/slug/meta,
    box rotado, 4 H2, longitud de frases, transiciones, enlaces internos, etc.)
    para que la IA se autocorrija ANTES de devolver el JSON, en vez de que tengas
    que corregirlo tú después de publicado.
  - LONGITUD: rango de palabras ajustado a 550-800 (antes 500-750) para dar
    espacio al H2 adicional sin que quede forzado.
  - FIX: VERSION_BOT sincronizado a "V17.9.0" (quedó desactualizado en un
    borrador anterior) y etiquetas de versión dentro del prompt actualizadas.

CAMBIOS EN V17.8.0 (LATAM-BOOST — más noticias latinoamericanas, menos ruido de España):
  - PROBLEMA DETECTADO: el pool GENERAL (obtener_newsapi/newsdata/gnews/rss) usa
    language='es', y eso trae MUCHAS noticias 100% domésticas de España (Madrid,
    Ayuso, Teatro Real, Congreso de los Diputados, etc.) porque España es el país
    con más medios en español indexados. Esas noticias no tenían ningún filtro,
    solo se penalizaba EE.UU./Europa anglosajona, nunca España.
  - FIX: KEYWORDS_ESPANA_DOMESTICO + es_noticia_espana_domestica() — nueva función
    que detecta noticias 100% domésticas de España (política interna, sucesos y
    cultura locales) SIN ninguna conexión latinoamericana o de impacto global.
    Se aplica como filtro DURO (se descartan, no solo se penalizan) en
    obtener_newsapi(), obtener_newsdata(), obtener_gnews() y obtener_rss(),
    para que dejen de competir por los 24 espacios/día del flujo general.
  - FIX: calcular_puntaje() ahora también penaliza (-6) noticias con marcadores
    domésticos de España sin conexión LATAM, igual que ya hacía con EE.UU./Europa.
  - FUENTES: NewsData — se agrega 'country': 'cl,ar,mx,co,pe' en obtener_newsdata()
    para pedirle a la API directamente noticias de esos 5 países (máx. permitido
    en plan free/basic) en lugar de depender solo del idioma.
  - FUENTES: GNews — cada tópico de obtener_gnews() ahora fija un país LATAM
    (cl/ar/mx/co rotando) en vez de usar el país por defecto de la API, sin
    aumentar el número de llamadas.
  - LATAM+CHILE: KEYWORDS_LATAM_PAISES ampliado con Puerto Rico, Guyana, Surinam
    y Belice, más ciudades adicionales (Arequipa, Cusco, Maracaibo, Barranquilla,
    Santa Cruz de la Sierra) para mejorar la clasificación por país.
  - LATAM+CHILE: nuevas queries NewsAPI para Centroamérica/Caribe con menor
    cobertura previa (Guatemala, Honduras, Costa Rica, Panamá, Rep. Dominicana,
    Cuba, Puerto Rico).
  - CUOTAS: MAX_POSTS_WP_DIA_CHILE 6→8, MAX_POSTS_WP_DIA_LATAM 8→12.
    MAX_POSTS_WP_DIA_TOTAL actualizado a 44 (24 general + 8 Chile + 12 LATAM).
    IMPORTANTE: esto solo sube el TECHO diario del bot. Para que realmente se
    publiquen más notas LATAM/Chile hace falta que el workflow de GitHub Actions
    ejecute el modo MODO_LATAM=true con la frecuencia suficiente (revisar el
    .yml del workflow, que no forma parte de este archivo).

CAMBIOS EN V17.7.0 (Valor editorial real — anti-scraping AdSense):
  - PROMPT IA: Reescritura completa con enfoque en valor editorial ORIGINAL
    PROBLEMA: La IA a veces producía artículos que parafraseaban superficialmente
    el original sin agregar análisis, contexto ni perspectiva propia.
    SOLUCIÓN: Instrucciones explícitas de valor editorial obligatorio:
      ✅ Análisis propio del redactor en cada artículo
      ✅ Dato de contexto adicional NO presente en el original
      ✅ Perspectiva editorial VerdadHoy (¿por qué importa esto a LATAM?)
      ✅ Voz periodística activa, no pasiva ni neutral
      ✅ Apertura original (no copiar el lead del original)
  - PROMPT IA: Sección "Advertencias de contenido" eliminada del log interno
    Se reemplaza por validación silenciosa con fallback de calidad
  - PROMPT IA: Instrucción anti-duplicado de estructura reforzada
    El bot ahora verifica que apertura, H2 principal y cierre sean únicas
    respecto al artículo fuente (no solo parafraseo de las mismas oraciones)
  - PROMPT IA: Prohibición explícita de reproducir frases del original
    "PROHIBIDO copiar frases o estructuras del artículo fuente aunque estén
    reformuladas. Escribe como si no hubieras leído el artículo original,
    sino solo los datos."
  - VALIDACIÓN: post_procesar_contenido() ahora verifica originalidad básica
    Si el contenido generado supera 40% de similitud con el input original,
    se descarta y se reintenta (máx 1 reintento) para evitar scraping detectado

CAMBIOS EN V17.6.9 (Robustez: API caída, reintentos y errores NoneType):
  - FIX CRÍTICO: reescribir_noticia_v9() ahora maneja errores de la API correctamente
    PROBLEMA: Cuando OpenRouter/OpenAI devolvía un error (sin créditos, rate limit,
    API key inválida), el bot accedía a resp_json["choices"] → KeyError 'choices'
    → iba al fallback → fallaba por contenido insuficiente → NO publicaba nada.
    SOLUCIÓN: Verifica "choices" en la respuesta ANTES de acceder. Si falta, lee el
    campo "error" y muestra un diagnóstico claro:
      💳 Sin créditos/saldo → recargar API
      ⏳ Rate limit → reintenta en próxima ejecución
      🔑 API key inválida → revisar GitHub Secrets
      🤖 Modelo no disponible → revisar nombre del modelo
  - FIX CRÍTICO: Loop de publicación con reintentos (MAX_PUBLICACIONES_INTENTOS=5)
    PROBLEMA: El bot seleccionaba UNA sola noticia. Si fallaba al publicar (IA caída +
    contenido corto), se rendía sin intentar otra → ejecución desperdiciada.
    SOLUCIÓN: Ahora acumula hasta 5 candidatas válidas (con contenido + imagen) e
    intenta publicarlas EN ORDEN hasta que una tenga éxito. Limpia imágenes temporales
    de las candidatas no usadas.
  - FIX: object of type 'NoneType' has no len() en NewsData/GNews
    PROBLEMA: NewsData a veces devuelve description:null o title:null → calcular_puntaje()
    fallaba al hacer len() sobre None.
    SOLUCIÓN: a.get('title') or '' / a.get('description') or '' en NewsData y GNews.
    calcular_puntaje() también blindada: titulo = titulo or "".
  - FIX: VERSION_BOT como constante única. El banner y el resumen ya NO muestran
    "V17.6.3" hardcodeado — usan VERSION_BOT (cambiar solo en un lugar).

CAMBIOS EN V17.6.8 (Fix: medio ambiente antes que ciencia — caso Amazonía):
  - FIX CRÍTICO: detectar_tema() — "medio_ambiente" sube a Prioridad 8 (antes era 11)
    PROBLEMA: La noticia "Deforestación en la Amazonía boliviana" se clasificaba como
    'ciencia' porque mencionaba "NASA" (como fuente de datos satelitales MODIS).
    La keyword genérica "nasa" disparaba ciencia ANTES de evaluar medio ambiente.
    SOLUCIÓN:
      1. medio_ambiente ahora se evalúa ANTES de salud y ciencia
      2. Keywords ampliadas: deforestación, desmonte, tala ilegal, bosque, selva,
         amazonía, pueblos indígenas, territorio indígena, frontera agrícola,
         área protegida, glaciar, deshielo, ecosistema, fauna/flora silvestre
      3. Keyword "nasa" en ciencia ahora requiere contexto espacial real:
         "nasa lanza", "misión de la nasa", "agencia espacial nasa"
         (ya no dispara ciencia si "NASA" solo aparece mencionada como fuente)
    RESULTADO: "Deforestación Amazonía Bolivia" → medio_ambiente ✅ (antes → ciencia ❌)
               "NASA lanza misión a Marte" → ciencia ✅ (sigue correcto)

CAMBIOS EN V17.6.7 (Fix clasificación LATAM — categorías temáticas correctas):
  - FIX CRÍTICO: detectar_tema() — "latinoamerica" baja de Prioridad 4 → Prioridad 15
    Antes: cualquier noticia con "Argentina", "Chile", "Brasil" → clasificada como 'latinoamerica'
    Ahora: pasa primero por todas las categorías temáticas (deportes, politica, economia,
    tecnologia, salud, ciencia, entretenimiento) y solo llega a 'latinoamerica' si ninguna
    categoría más específica aplica.
    Efecto real:
      "Inflación en Argentina" → 'economia' ✅ (antes → 'latinoamerica' ❌)
      "Elecciones en Colombia" → 'politica' ✅ (antes → 'latinoamerica' ❌)
      "Messi en Libertadores" → 'deportes' ✅ (antes → 'latinoamerica' ❌)
      "Shakira lanza álbum"   → 'entretenimiento' ✅ (antes → 'latinoamerica' ❌)
      "IA en startups Brasil"  → 'tecnologia' ✅ (antes → 'latinoamerica' ❌)
      "Cumbre CELAC sin agenda clara" → 'latinoamerica' ✅ (correcto, sin categoría mejor)
  - FIX PROMPT IA: Instrucción de "latinoamerica" completamente reescrita
    Antes: "SOLO si el protagonista ES un país de LATAM" — ambiguo, la IA seguía sobre-usando
    Ahora: Lista de 8 ejemplos negativos (❌) y 4 ejemplos positivos (✅) con regla clara:
    "Si puedes usar una categoría más específica → úsala siempre"
  - RESULTADO: Las noticias latinoamericanas ahora se distribuyen en sus categorías temáticas
    correctas (economia, politica, deportes, tecnologia, etc.) en lugar de acumularse todas
    en la categoría 'latinoamerica'. La categoría 'latinoamerica' queda para noticias
    exclusivamente regionales sin tema temático dominante.
CAMBIOS EN V17.6.6 (Box resumen garantizado en 100% de artículos):
  - FIX CRÍTICO: Box resumen ahora se verifica DESPUÉS de que la IA responde
    Si la IA omite el box (por token limit o error), se inyecta automáticamente
    con _generar_box_fallback() que extrae los 4 puntos clave del contenido real
  - FIX CRÍTICO: Fallback sin IA también incluye box resumen ahora
    Antes: fallback publicaba párrafos crudos sin box
    Ahora: fallback genera box con las primeras 4 oraciones clave del artículo
  - DETECCIÓN: 6 variantes de texto detectadas para saber si el box ya está presente
    ('background:#f0f4ff', 'Lo esencial', 'Puntos clave', 'Resumen r', etc.)
  - ROTACIÓN: Los 4 títulos del box rotan aleatoriamente en todos los casos (IA y fallback)
  - RESULTADO: 100% de artículos publicados tendrán box resumen, sin excepciones

CAMBIOS EN V17.6.5 (SEO Yoast + clasificación corregida):
  - PROMPT IA: Reglas Yoast explícitas — máx 25% frases largas, H2 antes de palabra 150
  - PROMPT IA: Mínimo 3 H2 distribuidos, mínimo 4 keywords secundarias
  - PROMPT IA: Instrucciones de voz activa y palabras de transición explícitas
  - PROMPT IA: Reglas anti-errores frecuentes — España/transporte/relojería bien clasificadas
  - CLASIFICACIÓN: "decreto"/"legislacion" ya no disparan "política" solos (muy genéricos)
  - CLASIFICACIÓN: Transporte público, ferroviario, infraestructura → "economia"
  - ESTRUCTURA: H2 obligatorio antes de palabra 150 (era 300) — fix Yoast rojo
  - ESTRUCTURA: Segundo H2 en el desarrollo — 3 subtítulos mínimo por artículo

CAMBIOS EN V17.6.4 (Anti-spam + clasificación mejorada):
  - FILTRO: es_contenido_spam() — blacklist de 35+ keywords de casas de apuestas,
    contenido afiliado, préstamos, crypto spam y SEO basura aplicado en TODOS los loops
  - FILTRO: Bloquea automáticamente: rojabet, bet365, 1xbet, betano, "bono sin depósito",
    "casino online", "apuestas deportivas", "código promocional", etc.
  - CLASIFICACIÓN: Relojería de lujo y moda → "entretenimiento" (no "internacional")
    Keywords: rolex, audemars, patek philippe, swatch, colaboracion relojera, etc.
  - CLASIFICACIÓN: Smartwatch/wearables → "tecnología"
    Keywords: apple watch, galaxy watch, garmin, fitbit, reloj inteligente, etc.
  - PROMPT IA: Actualizado a V17.6.4 en la instrucción de categorías

CAMBIOS EN V17.6.3 (Tiempo de permanencia — de 31s a +2 min):
  - PROMPT IA: Box "En 30 segundos" al inicio de cada artículo (3-4 bullets resumen)
    → Paradójicamente retiene: el lector quiere el detalle después del gancho visual
  - PROMPT IA: Estructura H2/H3 obligatoria — lector escanea y decide quedarse
  - PROMPT IA: Párrafos máx 3 líneas (era 4) — más aire visual, menos abandono
  - PROMPT IA: Pregunta de engagement al cierre — invita a dejar comentario real
  - PROMPT IA: "Dato destacado" con <blockquote> en cada artículo — rompe monotonía visual
  - ESTRUCTURA WP: Box resumen con CSS inline propio — no depende del tema
  - ESTRUCTURA WP: Tiempo estimado de lectura calculado automáticamente y mostrado
  - ESTRUCTURA WP: Sección "Sigue leyendo" al final del artículo (ya existía, se refuerza)
  - OBJETIVO: Analytics time-on-page > 2min (era 31s) para mejorar señal AdSense/Discover

CAMBIOS EN V17.6.2 (Fix clasificación y titulares forzados):
  - PROMPT IA: Reescrito completamente — clasificación con lógica clara por categoría
  - PROMPT IA: "latinoamerica" ya NO es categoría por defecto para todo
    Ahora solo se usa cuando el protagonista de la noticia ES un país/actor de LATAM
  - PROMPT IA: "deportes" captura TODO lo deportivo (zapatos fútbol, lesiones, estadios)
  - PROMPT IA: "entretenimiento" captura artistas aunque sean en español (Ana Torroja)
  - PROMPT IA: Sección "Qué significa para Chile y LATAM" ahora es CONDICIONAL:
    * Aparece en economia/politica/tecnologia/guerra/medio_ambiente SOLO si hay impacto real
    * En deportes → "Análisis del partido/competencia" (conexión LATAM solo si es genuina)
    * En entretenimiento → "Por qué importa" (sin forzar conexión latinoamericana)
    * En latinoamerica → "Contexto regional" (ya ES de LATAM, no necesita conectar)
  - PROMPT IA: PROHIBIDO explícito añadir "en LATAM" / "y su impacto en LATAM" al título
    si no es genuinamente relevante para la región
  - CUOTAS: Sin cambios respecto a V17.6.1 (24/día, 60 min entre publicaciones)
  - CUOTAS DIARIAS: Reducidas a 24 artículos/día total (era 82)
      * Flujo general:   24 artículos/día (era 48) — 1 cada 60 min
      * Chile:            6 artículos/día (era 12) — distribuidos en el día
      * LATAM región:     8 artículos/día (era 22) — distribuidos en el día
      * Total global:    38 artículos/día (24 + 6 + 8) — realista y alcanzable
  - TIMING WP: Intervalo mínimo entre publicaciones: 30 min → 60 min
    (antes el JSON de estado no se pusheaba a tiempo y el bot leía hora vieja,
     saltándose publicaciones; con 60 min hay margen real entre ejecuciones)
  - FORZAR_PUBLICACION: Ahora se activa automáticamente si han pasado >55 min
    desde la última publicación (evita que el bot salte por error de timing)
  - FACEBOOK: Aclaración en código — FB y WP son flujos independientes.
    WP publica en cada ejecución válida. FB solo en horario pico.
    El horario pico NO afecta a WordPress.
  - SEO FOCUS: Con 24 artículos/día de alta calidad, Google Discover y
    Google News indexan mejor que con 72 artículos de calidad variable.
    Menos artículos = más tiempo de IA por artículo = mejor contenido.
  - CATEGORÍAS WP: Reducidas a las 8 que realmente aportan tráfico LATAM:
    latinoamerica, deportes, economia, tecnologia, entretenimiento,
    politica, ciencia-y-salud (combinada), mundo
    Las demás (guerra, crimen, desastre) van a 'internacional' como antes.

CAMBIOS EN V17.6:
  - ESTRATEGIA: Pivot editorial completo → medio de referencia para Latinoamérica
  - CUOTAS: latinoamerica 25%, deportes 18%, economia 15%, tecnologia 12%
  - FUENTES: RSS LATAM ampliados — 19 medios regionales prioritarios
  - PROMPT IA: Sección "Qué significa para Chile y América Latina"
  - detectar_tema(): latinoamerica sube a prioridad 4 (era 11)
  - calcular_puntaje(): bonus +10 para noticias con keywords LATAM
  - ESTRATEGIA: Pivot editorial completo → medio de referencia para Latinoamérica
  - OBJETIVO: 75-80% del contenido diario relacionado directa o indirectamente con LATAM
  - CUOTAS: Rebalanceo total orientado a LATAM-first:
      * latinoamerica:   10% → 25% (principal categoría del sitio)
      * chile:            7  → 12 artículos/día (era 7)
      * latam_region:    16  → 22 artículos/día (era 16)
      * deportes:        16% → 18% (fútbol LATAM, eliminatorias, libertadores, mundial)
      * economia:        13% → 15% (dólar, inflación, comercio regional)
      * tecnologia:      11% → 12% (IA, fintech, startups LATAM)
      * entretenimiento: 10% → 10% (artistas latinos, reggaeton, cine)
      * politica:         9% →  5% (solo líderes LATAM de alto impacto)
      * ciencia+salud:   14% →  5% (combinadas, foco en investigaciones LATAM)
      * mundo:            5% →  3% (solo noticias de alto impacto regional)
      * medio_ambiente:   3% →  3% (Amazonía, glaciares, recursos naturales LATAM)
      * guerra/crimen/desastre/clima: máx 1% cada una
  - FUENTES: Ampliadas para LATAM — nuevos RSS de Brasil, Paraguay, Bolivia, Venezuela
  - FUENTES: NewsAPI queries reenfocadas — 80% queries con contexto LATAM
  - FUENTES: GNews — queries prioritarias en español latino
  - PROMPT IA: Actualizado V17.6 — enfoque LATAM reforzado, perspectiva Chile y vecinos
  - PROMPT IA: Sección "Qué significa para Chile y sus vecinos" cuando aplique
  - DETECCIÓN: detectar_tema() actualizada — latinoamerica sube a prioridad 4
    (antes estaba en prioridad 11, perdiendo noticias regionales ante categorías genéricas)
  - PRIORIDAD: Noticias con keywords LATAM/Chile reciben bonus +8 de puntaje
  - FILTRO: Noticias exclusivamente de EE.UU./Europa/Asia sin impacto LATAM se penalizan -5
  - MAX_POSTS_WP_DIA_CHILE:  7  → 12 artículos/día
  - MAX_POSTS_WP_DIA_LATAM: 16  → 22 artículos/día
  - MAX_POSTS_WP_DIA_TOTAL: 71  → 82 (48 general + 12 Chile + 22 LATAM)

CAMBIOS EN V17.5:
  - CUOTAS LATAM: MAX_POSTS_WP_DIA_CHILE aumentado de 4 → 7 artículos/día
  - CUOTAS LATAM: MAX_POSTS_WP_DIA_LATAM aumentado de 11 → 16 artículos/día
  - CUOTAS LATAM: MAX_POSTS_WP_DIA_TOTAL actualizado de 63 → 71 (48 + 7 + 16)

CAMBIOS EN V17.3:
  - LATAM+CHILE: Nuevo bloque de publicación dedicado exclusivamente a noticias
    de América Latina y Chile — separado del flujo general de noticias.
  - LATAM+CHILE: 15 artículos adicionales por día distribuidos así:
      * 4 artículos de Chile específicamente
      * 11 artículos del resto de LATAM (sin Chile)
  - LATAM+CHILE: Nuevas fuentes dedicadas RSS para Chile:
      * La Tercera, El Mercurio, Emol, BioBioChile, Cooperativa, CNN Chile
  - LATAM+CHILE: Nuevas fuentes RSS LATAM región por región:
      * México: El Universal, Reforma, Milenio
      * Argentina: Infobae AR, La Nación, Página 12
      * Colombia: El Tiempo, Semana
      * Perú: El Comercio, RPP
      * Venezuela/Bolivia/Ecuador/Uruguay: medios regionales
  - LATAM+CHILE: Nuevas queries NewsAPI específicas para Chile y LATAM
  - LATAM+CHILE: Función obtener_noticias_chile() — solo retorna noticias
    cuyo origen/contenido sea claramente de Chile
  - LATAM+CHILE: Función obtener_noticias_latam() — retorna noticias de LATAM
    excluyendo Chile (para no duplicar)
  - LATAM+CHILE: Función es_noticia_chile() — detecta si una noticia es de Chile
    usando keywords geográficas específicas (Santiago, Boric, CONAF, Carabineros,
    peso chileno, etc.)
  - LATAM+CHILE: Control de cuotas independiente para Chile y LATAM en
    estado_cuotas_latam.json — no interfiere con cuotas generales
  - LATAM+CHILE: MAX_POSTS_WP_DIA actualizado a 71 (48 general + 23 LATAM/Chile)
  - LATAM+CHILE: GitHub Actions — se agrega una ejecución paralela del bloque
    LATAM cada 96 minutos para distribuir los 15 artículos durante el día

CAMBIOS EN V17.2:
  - PROMPT IA: Reescritura completamente rediseñada para cumplir estándares AdSense
    "contenido de valor original". Google dejó de aprobar sitios con reescrituras simples.
  - PROMPT IA: Estructura editorial obligatoria de 7 secciones:
    1) Apertura con datos duros (Qué/Quién/Cuándo/Dónde)
    2) Contexto y antecedentes (por qué importa ahora)
    3) Subtítulo + desarrollo con datos del original
    4) Lista de puntos clave
    5) Sección "Qué significa para América Latina" — OBLIGATORIA en cada artículo
    6) Cierre con reflexión
  - PROMPT IA: Perspectiva LATAM obligatoria en TODOS los artículos — diferenciador
    editorial clave vs BBC/CNN/DW que no tienen enfoque regional latinoamericano
  - PROMPT IA: Mínimo 420 palabras (era 350) — artículos más sustanciales
  - PROMPT IA: temperature 0.35 (era 0.4) — más coherencia, menos divagación
  - PROMPT IA: max_tokens 2000 (era 1600) — espacio para artículo completo sin truncar
CAMBIOS EN V17.1:
  - CUOTAS: Rebalanceo completo para público hispanoamericano (LATAM-first)
  - Deportes: 16% (Mundial 2026 en USA/México/Canadá — audiencia masiva)
  - Economía: 13% (dólar, inflación, crisis = tema diario del latino)
  - Latinoamérica: 10% (identidad regional — diferenciador vs BBC/CNN)
  - Entretenimiento: 10% (farándula latina, música urbana, reggaeton)
  - Política: 9% (Milei, Boric, Sheinbaum, Maduro = virales garantizados)
  - Guerra: 4% → bajada desde 8% (brand-unsafe + destruye RPM AdSense)
  - Crimen: 1% → casi eliminado (riesgo desmonetización AdSense)
  - Religión/General: 0% (no generan tráfico ni CPM)

CAMBIOS EN V17.0:
  - FUENTES: NewsAPI — queries duplicadas para Deportes, Entretenimiento y Mundo.
    Se agregaron 10 nuevas queries cubriendo fútbol, NBA, F1, cine, música,
    streaming, premios, farándula y noticias generales internacionales.
  - FUENTES: NewsData — se agregaron categorías 'entertainment' y 'sports'
    que estaban ausentes, cubriendo el 100% de categorías disponibles de la API.
  - FUENTES: GNews — se agregaron queries de respaldo por categoría para
    deportes y entretenimiento en caso de que los tópicos no devuelvan resultados.
  - FUENTES: RSS — se triplicaron los feeds:
    * Deportes: ESPN Deportes, Marca, AS, Mundo Deportivo
    * Entretenimiento: Espinof, Fotogramas, Los40
    * Mundo/Internacional: La Vanguardia, Clarín Internacional, DW Español
    * LATAM: Infobae América, El Universal, La Nación Argentina
  - CUOTAS: entretenimiento sube de 5% a 8% (era demasiado bajo para
    cubrir cine + música + series + celebrities)
  - CUOTAS: deportes sube de 12% a 14% durante el Mundial 2026
  - PRIORIDAD: deportes y entretenimiento agregados a PALABRAS_ALTA_PRIORIDAD
    para que el sistema de puntaje los compita con noticias de guerra
  - DETECCIÓN: keywords de entretenimiento ampliadas para capturar:
    "estreno", "tráiler", "película", "álbum", "gira", "concierto",
    "Billboard", "Spotify chart", "temporada", "secuela", "remake"

CAMBIOS EN V16.0:
  - CLASIFICACIÓN IA: La IA ahora lee y comprende el contenido completo para clasificar.
    Ya no depende de keywords estáticas. La función reescribir_noticia_v9() devuelve
    también la categoría definitiva (campo "categoria" en el JSON de respuesta).
  - CLASIFICACIÓN IA: detectar_tema() ahora es solo fallback de emergencia (si la IA falla).
  - CLASIFICACIÓN IA: El prompt incluye definición clara de cada categoría con ejemplos
    para que la IA tome decisiones editoriales correctas.
  - CLASIFICACIÓN IA: La categoría IA tiene prioridad sobre detectar_tema() en TODO el flujo.
  - FLUJO: publicar_en_wordpress() ya no recibe 'tema' como parámetro fijo — lo determina
    la IA al reescribir, garantizando coherencia entre contenido y categoría.
  - FALLBACK: Si la IA falla, detectar_tema() actúa como respaldo (V15 keywords).

CAMBIOS EN V15.0:
  - CLASIFICACIÓN: Keywords de guerra/conflicto ampliados — cubre "alto el fuego", "heridos",
    "muertos", "fuerzas armadas", "avión militar", "tanquero", "intercambio de fuego",
    "ataque terrorista", "víctimas", "bombardeo", "portaviones", "fragata", etc.
  - CLASIFICACIÓN: Keywords de política ampliados — "acuerdo de paz", "negociaciones",
    "espionaje", "sanciones", "bloqueo", "acuerdo nuclear", líderes mundiales adicionales
  - CLASIFICACIÓN: Bug crítico corregido — categorías brand-unsafe (guerra, crimen,
    desastre) ya NO se reclasifican a tecnologia/economia cuando la cuota se llena.
    Ahora publican igual porque la noticia importa más que la cuota de CPM.
  - CLASIFICACIÓN: Nueva función 'es_categoria_critica()' — protege la integridad editorial
  - CUOTAS: guerra sube a 8% (era 4%), desastre a 5% (era 3%), crimen a 4% (era 2%)
    para reflejar el volumen real de noticias internacionales

CAMBIOS EN V14.1:
  - SCHEMA: Agregado campo "image" con URL real de imagen subida a WP (fix Rich Results)
  - SCHEMA: Agregado campo "author" como Organization con URL (fix Rich Results)
  - SCHEMA: Fecha con zona horaria "+00:00" en datePublished y dateModified
  - SCHEMA: Agregado campo "isAccessibleForFree: True" (requerido por Google News)
  - SCHEMA: Logo publisher con dimensiones explícitas (512x512)
  - RICH RESULTS: Resuelve 3 problemas no críticos detectados por Google

CAMBIOS EN V14:
  - GOOGLE DISCOVER: Imágenes garantizadas ≥1200px ancho (requisito oficial Google)
  - GOOGLE DISCOVER: Imagen fallback ampliada a 1600x900 (16:9 óptimo para Discover)
  - GOOGLE DISCOVER: Imagen fallback mejorada visualmente (gradiente, logo, categoría)
  - GOOGLE DISCOVER: Redimensionado inteligente — amplía si <1200px, recorta si >2000px
  - GOOGLE DISCOVER: Open Graph image dimension hints en schema (1200x630 mínimo)
  - GOOGLE DISCOVER: Títulos más atractivos — prompt IA actualizado para Discover
  - GOOGLE DISCOVER: Campo 'max-image-preview:large' en robots meta via schema
  - SEO: Meta descripción con longitud verificada (140-155 chars estricto)
  - IMÁGENES: Calidad JPEG subida a 92 (era 88) para mejor nitidez en móvil
  - IMÁGENES: Watermark reposicionado y tipografía mejorada
  - FACEBOOK: Sin cambios (mantiene compresión a 720px para velocidad)

CAMBIOS EN V13:
  - CATEGORÍAS: Cuotas rebalanceadas — Deportes +6%, Ciencia/Salud +4% cada una
  - CATEGORÍAS: CATEGORIA_WP corregido — guerra/crimen/desastre/religion/educacion → 'internacional'
  - CATEGORÍAS: Keywords de Deportes ampliados (partido, fichaje, Mundial 2026, etc.)
  - CATEGORÍAS: Keywords de Salud ampliados (síntoma, clínica, ensayo clínico, etc.)
  - CATEGORÍAS: Keywords de Ciencia ampliados (astronomía, investigadores, ADN, etc.)
  - CATEGORÍAS: Keywords de Política ampliados con presidentes LATAM y términos locales
  - CATEGORÍAS: Latinoamérica ya no captura noticias que primero deben ir a Política
  - PINTEREST: Tableros actualizados con nuevas categorías geográficas

CAMBIOS EN V12:
  - FACEBOOK: Ya NO genera videos. Publica imagen + texto tomando artículos
    ya publicados en verdadhoy.com (via WP REST API). Formato limpio:
    📰 Titular | párrafo corto | link | CTA | hashtags
  - FACEBOOK: Filtro estricto — solo publica si el artículo en WP tiene imagen destacada
  - WORDPRESS: Filtro imagen aún más estricto — descarta sin imagen en TODAS las etapas
  - CATEGORÍAS: Mejoradas y expandidas. Corregida detección errónea que metía
    noticias de guerra/política en 'entretenimiento'. Nuevas: 'medio_ambiente',
    'educacion', 'religion', 'crimen'
  - PINTEREST: Verificado y activo en paralelo con WP (cada vez que publica WP)
  - ELIMINADO: crear_video_noticia(), publicar_facebook_video(), toda lógica moviepy/TTS

HEREDADO DE V11:
  - Función 3: Video manual via /pending_videos/ en GitHub
  - Anti-duplicados robusto
  - Schema JSON-LD NewsArticle
  - Alt text automático en imágenes
  - Tags automáticos desde keywords IA
  - Cuotas editoriales por categoría
  - Sección "Te puede interesar"
  - Brand safety automático
  - Fecha de publicación desde fuente original
"""

# ── VERSIÓN DEL BOT (única fuente de verdad — actualizar solo aquí) ──
VERSION_BOT = "V17.9.11"

import requests
import feedparser
import re
import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse

# ──────────────────────────────────────────────────────────
# CUOTAS EDITORIALES POR CATEGORÍA (monetización AdSense)
# ──────────────────────────────────────────────────────────
CUOTAS_CATEGORIA = {
    # ── V17.6 LATAM-FIRST: medio de referencia para América Latina ────
    # Objetivo: 75-80% del contenido con conexión directa a LATAM
    'latinoamerica':   {'cuota': 0.25, 'cpm_relativo': 1.18, 'brand_safe': True},   # ↑ 10%→25% — identidad regional CORE
    'deportes':        {'cuota': 0.18, 'cpm_relativo': 1.25, 'brand_safe': True},   # ↑ 16%→18% — fútbol LATAM, eliminatorias, Mundial 2026
    'economia':        {'cuota': 0.15, 'cpm_relativo': 1.55, 'brand_safe': True},   # ↑ 13%→15% — dólar, inflación, comercio regional
    'tecnologia':      {'cuota': 0.12, 'cpm_relativo': 1.45, 'brand_safe': True},   # ↑ 11%→12% — IA, fintech, startups LATAM
    'entretenimiento': {'cuota': 0.10, 'cpm_relativo': 1.20, 'brand_safe': True},   # = 10% — artistas latinos, reggaeton, cine
    'politica':        {'cuota': 0.05, 'cpm_relativo': 1.10, 'brand_safe': False},  # ↓ 9%→5%  — solo líderes LATAM alto impacto
    # Ciencia y Salud combinadas — foco en investigaciones LATAM
    'ciencia':         {'cuota': 0.03, 'cpm_relativo': 1.40, 'brand_safe': True},   # ↓ 7%→3%
    'salud':           {'cuota': 0.03, 'cpm_relativo': 1.40, 'brand_safe': True},   # ↓ 7%→3%
    'medio_ambiente':  {'cuota': 0.03, 'cpm_relativo': 1.28, 'brand_safe': True},   # = 3%  — Amazonía, glaciares, LATAM
    # Internacional solo de alto impacto para la región
    'mundo':           {'cuota': 0.03, 'cpm_relativo': 1.00, 'brand_safe': True},   # ↓ 5%→3%  — solo impacto real en LATAM
    # Brand-unsafe / bajo CPM — mínimos editoriales (solo si impactan LATAM)
    'guerra':          {'cuota': 0.01, 'cpm_relativo': 0.90, 'brand_safe': False},  # ↓ 4%→1%
    'desastre':        {'cuota': 0.01, 'cpm_relativo': 0.95, 'brand_safe': False},  # ↓ 2%→1%
    'clima':           {'cuota': 0.01, 'cpm_relativo': 1.30, 'brand_safe': True},   # = 1%
    'crimen':          {'cuota': 0.00, 'cpm_relativo': 0.85, 'brand_safe': False},  # ↓ 1%→0%  — desmonetiza AdSense
    'educacion':       {'cuota': 0.00, 'cpm_relativo': 1.35, 'brand_safe': True},   # ↓ 1%→0%
    # Sin cuota activa — no se buscan
    'religion':        {'cuota': 0.00, 'cpm_relativo': 1.00, 'brand_safe': True},
    'general':         {'cuota': 0.00, 'cpm_relativo': 1.00, 'brand_safe': True},
}
CUOTAS_CONTROL_PATH = 'estado_cuotas.json'

# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN — Variables de entorno / GitHub Secrets
# ──────────────────────────────────────────────────────────
NEWS_API_KEY       = os.getenv('NEWS_API_KEY', '')
NEWSDATA_API_KEY   = os.getenv('NEWSDATA_API_KEY', '')
GNEWS_API_KEY      = os.getenv('GNEWS_API_KEY', '')
FB_PAGE_ID         = os.getenv('FB_PAGE_ID', '')
FB_ACCESS_TOKEN    = os.getenv('FB_ACCESS_TOKEN', '')

WP_URL             = os.getenv('WP_URL', 'https://verdadhoy.com')
WP_USER            = os.getenv('WP_USER', 'verdadhoy_admin')
WP_APP_PASSWORD    = os.getenv('WP_APP_PASSWORD', '')

PINTEREST_TOKEN    = os.getenv('PINTEREST_TOKEN', '')
YOUTUBE_API_KEY    = os.getenv('YOUTUBE_API_KEY', '')
GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')       # V17.9.5: proveedor gratuito principal
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENAI_API_KEY     = os.getenv('OPENAI_API_KEY', '')
GITHUB_TOKEN       = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO        = os.getenv('GITHUB_REPOSITORY', '')

# Rutas de estado
HISTORIAL_PATH      = os.getenv('HISTORIAL_PATH', 'historial_publicaciones.json')
ESTADO_WP_PATH      = 'estado_wp.json'
ESTADO_FB_PATH      = 'estado_fb.json'
PENDING_VIDEOS_DIR  = 'pending_videos'
ESTADO_PENDING_PATH = 'estado_pending_videos.json'
ESTADO_LATAM_PATH   = 'estado_cuotas_latam.json'   # V17.3: cuotas Chile+LATAM independientes

# ── V17.3: Modo de ejecución ──────────────────────────────
# MODO_LATAM=true  → solo ejecuta bloque Chile+LATAM
# MODO_LATAM=false → ejecuta flujo general (default)
MODO_LATAM = os.getenv('MODO_LATAM', 'false').lower() == 'true'

# Tiempos
# V17.6.1: Subido a 60 min para dar margen real entre ejecuciones.
# Con 30 min el JSON de estado frecuentemente no estaba pusheado a tiempo
# y el bot leía la hora antigua → saltaba la publicación sin publicar nada.
# V17.9.1: Con MAX_POSTS_WP_DIA=6, si el gate se queda en 60 min, el bot puede
# gastar toda la cuota del día en las primeras 6 horas y quedar en silencio el
# resto del día. Subido a 230 min (~3h50) para repartir las 6 notas a lo largo
# de las 24 horas (24h / 6 = 4h, con margen).
TIEMPO_ENTRE_WP_MIN = 230
TIEMPO_ENTRE_FB_MIN = 90   # 1.5 horas mínima entre posts de Facebook

# Límites diarios — V17.6.1: Reducidos a números alcanzables
# Antes: 82/día → el bot no llegaba ni a 20. Ahora: 38/día → realista con 60min/pub
# Beneficio SEO: 24 artículos de alta calidad > 72 artículos de calidad variable
MAX_POSTS_FB_DIA        = 4    # Máximo 4 posts/día en Facebook (calidad > cantidad)
MAX_POSTS_WP_DIA        = 6    # Flujo general (V17.9.1: bajado de 24 a 6 — arranque conservador)
MAX_POSTS_WP_DIA_CHILE  = 3    # Chile: 3 artículos/día (V17.9.1: antes 8)
MAX_POSTS_WP_DIA_LATAM  = 3    # LATAM sin Chile: 3 artículos/día (V17.9.1: antes 12)
MAX_POSTS_WP_DIA_TOTAL  = 12   # Total máximo global (6 + 3 + 3)

# Anti-duplicados
UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 300
DIAS_HISTORIAL             = 14

# Horarios pico Facebook (hora UTC) — solo publica en estas franjas
HORARIOS_PICO_UTC = [
    (0, 4),    # 21:00-01:00 Chile
    (10, 14),  # 07:00-11:00 Chile
    (18, 22),  # 15:00-19:00 Chile
]

# ── MAPEO CATEGORÍAS → SLUGS WORDPRESS ─────────────────────
CATEGORIA_WP = {
    # Conflicto y seguridad → Internacional (es el paraguas correcto)
    'guerra':          'internacional',
    'desastre':        'internacional',
    'crimen':          'internacional',
    'religion':        'internacional',
    'educacion':       'internacional',
    'general':         'internacional',
    # Temáticas propias
    'politica':        'politica',
    'economia':        'economia',
    'tecnologia':      'tecnologia',
    'ciencia':         'ciencia-y-salud',
    'salud':           'ciencia-y-salud',
    'deportes':        'deportes',
    'entretenimiento': 'entretenimiento',
    'latinoamerica':   'latinoamerica',
    'clima':           'medio-ambiente',
    'medio_ambiente':  'medio-ambiente',
    'mundo':           'mundo',
}

# ── TABLEROS PINTEREST ──────────────────────────────────────
TABLEROS_PINTEREST = {
    'guerra':          'Noticias del Mundo',
    'politica':        'Politica',
    'economia':        'Economia',
    'tecnologia':      'Tecnologia',
    'desastre':        'Noticias del Mundo',
    'deportes':        'Noticias del Mundo',
    'ciencia':         'Noticias del Mundo',
    'salud':           'Noticias del Mundo',
    'entretenimiento': 'Noticias del Mundo',
    'latinoamerica':   'Latinoamerica',
    'clima':           'Noticias del Mundo',
    'medio_ambiente':  'Noticias del Mundo',
    'educacion':       'Noticias del Mundo',
    'religion':        'Noticias del Mundo',
    'crimen':          'Noticias del Mundo',
    'mundo':           'Noticias del Mundo',
    'general':         'Noticias del Mundo',
}
_cache_tableros_pinterest = {}
_cache_categorias_wp      = {}
_cache_tags_wp            = {}

# ── CTAs por tema para Facebook ────────────────────────────
CTAS_POR_TEMA = {
    'guerra': [
        "¿Crees que esto puede escalar a un conflicto mayor? Dinos abajo 👇",
        "¿Qué solución ves a este conflicto? Comenta 👇",
        "¿El mundo está haciendo suficiente? Tu opinión importa 👇",
    ],
    'politica': [
        "¿Estás de acuerdo con esta decisión? Comenta SÍ o NO 👇",
        "¿Qué opinas de esta medida? Tu voz cuenta 👇",
        "¿Cómo crees que afectará esto a la región? Dinos 👇",
    ],
    'economia': [
        "¿Sientes esto en tu bolsillo? Cuéntanos 👇",
        "¿Cómo te afecta esta situación económica? Comenta 👇",
        "¿Crees que mejorará la economía? SÍ o NO 👇",
    ],
    'tecnologia': [
        "¿La IA nos ayuda o nos amenaza? Comenta 👇",
        "¿Usarías esta tecnología? Dinos 👇",
        "¿El futuro te emociona o te preocupa? Opina 👇",
    ],
    'desastre': [
        "Nuestros pensamientos con los afectados 🙏 Comenta abajo 👇",
        "¿Cómo podemos ayudar en situaciones así? Opina 👇",
    ],
    'deportes': [
        "¿Qué opinas de este resultado? Comenta 👇",
        "¿Estás de acuerdo con esta decisión deportiva? SÍ o NO 👇",
        "¿Tu equipo favorito puede superarlo? Dinos 👇",
    ],
    'ciencia': [
        "¿Crees que la ciencia avanza lo suficiente? Comenta 👇",
        "¿Cambiaría esto tu vida? SÍ o NO 👇",
        "¿Lo sabías? Dinos abajo 👇",
    ],
    'salud': [
        "¿Cuidas tu salud? Comparte tu experiencia 👇",
        "¿Sabías esto sobre tu salud? Comenta 👇",
        "¿Crees que la medicina avanza rápido? SÍ o NO 👇",
    ],
    'entretenimiento': [
        "¿Lo viste? ¿Qué te pareció? Comenta 👇",
        "¿Estás de acuerdo? SÍ o NO 👇",
        "¿Tu favorito de siempre o hay nuevos? Opina 👇",
    ],
    'latinoamerica': [
        "¿Cómo afecta esto a tu país? Cuéntanos 👇",
        "¿Crees que Latinoamérica va por buen camino? Opina 👇",
        "¿Lo sentiste en tu región? Comenta abajo 👇",
    ],
    'clima': [
        "¿Sientes el cambio climático en tu ciudad? Comenta 👇",
        "¿Hacemos suficiente por el planeta? SÍ o NO 👇",
        "¿Qué haces tú para ayudar? Cuéntanos 👇",
    ],
    'medio_ambiente': [
        "¿Qué haces tú para cuidar el planeta? Comenta 👇",
        "¿Es suficiente lo que hacemos por el medio ambiente? SÍ o NO 👇",
    ],
    'educacion': [
        "¿Crees que la educación mejora el mundo? SÍ o NO 👇",
        "¿Qué cambiarías en el sistema educativo? Dinos 👇",
    ],
    'religion': [
        "¿Qué piensas de esta noticia? Comenta 👇",
        "¿Respetas todas las religiones? SÍ o NO 👇",
    ],
    'crimen': [
        "¿Crees que la justicia actúa bien? Comenta 👇",
        "¿Qué opinas de este caso? Dinos abajo 👇",
    ],
    'mundo': [
        "¿Qué piensas de lo que pasa en el mundo? Comenta 👇",
        "¿Estamos ante un cambio histórico? Opina 👇",
        "¿Sabías esto? Dinos SÍ o NO 👇",
    ],
    'general': [
        "¿Qué piensas de esta noticia? Comenta abajo 👇",
        "¿Sabías esto? Dinos SÍ o NO 👇",
        "Comparte si crees que todos deben saberlo 🔁",
    ],
}

PALABRAS_ALTA_PRIORIDAD = [
    # ── V17.6: LATAM-FIRST — keywords regionales en primer lugar ──────
    "copa libertadores", "copa sudamericana", "eliminatorias sudamericanas",
    "conmebol", "mundial 2026", "copa del mundo",
    "boric", "milei", "lula", "sheinbaum", "petro", "maduro", "bukele",
    "litio chile", "cobre chile", "petroleo venezuela",
    "peso chileno", "peso argentino",
    "inflacion argentina", "inflacion chile", "inflacion mexico",
    "elecciones chile", "elecciones argentina", "elecciones colombia",
    "terremoto chile", "sismo chile",
    "festival de viña", "seleccion chilena", "la roja",
    "colo-colo", "universidad de chile",
    # ── Internacional de alto impacto ─────────────────────────────────
    "guerra", "conflicto armado", "invasion", "ofensiva militar", "bombardeo",
    "misiles", "ataque aereo", "drones militares", "movilizacion militar",
    "tropas", "escalada de tension", "amenaza nuclear", "armas nucleares",
    "terrorismo", "atentado", "ataque terrorista",
    "ucrania", "rusia", "israel", "gaza", "iran", "china", "taiwan",
    "corea del norte", "otan", "nato", "brics", "medio oriente",
    "crisis humanitaria", "refugiados",
    "crisis de gobierno", "golpe de estado", "estado de emergencia",
    "negociaciones de paz", "alto el fuego", "sanciones internacionales",
    "economia mundial", "inflacion", "crisis economica", "recesion",
    "petroleo", "gas", "crisis energetica",
    "ciberataque", "hackeo", "inteligencia artificial",
    "ultima hora", "urgente", "breaking",
    "putin", "zelensky", "trump", "biden", "netanyahu",
    "xi jinping", "kim jong un", "macron",
    "hamas", "hezbollah", "isis", "taliban", "houthis",
    "elon musk",
    # ── Deportes — Mundial 2026 y grandes eventos ─────────────────────
    "champions league", "champions",
    "nba finals", "super bowl", "formula 1", "grand prix",
    "olimpiadas", "juegos olimpicos",
    "fichaje", "transfer", "gol", "campeón", "campeona",
    "messi", "mbappe", "neymar", "cristiano ronaldo",
    "lebron james", "verstappen", "djokovic", "alcaraz",
    # ── Entretenimiento LATAM — artistas de alto impacto ─────────────
    "oscar 2025", "oscar 2026", "grammy", "emmy",
    "taylor swift", "bad bunny", "shakira", "beyonce",
    "karol g", "maluma", "j balvin", "rauw alejandro",
    "rosalía", "daddy yankee",
    "netflix estreno", "disney plus", "marvel", "star wars",
    "cannes 2025", "cannes 2026",
]

PALABRAS_MEDIA_PRIORIDAD = [
    "economia", "mercados", "FMI", "banco mundial",
    "tecnologia", "innovacion", "salud", "educacion",
    "medio ambiente", "cambio climatico",
    "comercio internacional", "empresas",
]

BLACKLIST_TITULOS = [
    r'^\s*última hora\s*$',
    r'^\s*breaking news\s*$',
    r'^\s*noticias de hoy\s*$',
    r'^\s*\d+\s*$',
]

# ── V17.6.4: Blacklist de contenido spam, apuestas y publicitario ─────────────
# Filtra ANTES de procesar — evita contenido brand-unsafe, promocional y casas de apuestas
BLACKLIST_CONTENIDO_SPAM = [
    # Casas de apuestas / gambling — alto riesgo desmonetización AdSense
    "rojabet", "bet365", "1xbet", "betano", "codere", "tómbola", "tombola",
    "sportingbet", "bwin", "pokerstars", "888casino", "betfair", "unibet",
    "casino online", "apuestas deportivas", "apuestas en línea", "apuestas en linea",
    "bono de bienvenida casino", "bono sin depósito", "bono sin deposito",
    "giros gratis casino", "tragamonedas", "tragaperras", "ruleta online",
    "poker online", "blackjack online", "slots online", "juegos de azar",
    "casa de apuestas", "casas de apuestas", "cuotas de apuestas", "pronósticos deportivos pagos",
    # V17.9.6: términos genéricos de cuotas/pronósticos — el caso real que
    # se coló fue un artículo de "cuotas y favoritos" para el Mundial 2026
    # que NO usaba ninguna de las frases de arriba en el título/descripción,
    # solo en el cuerpo del artículo (de ahí también el fix de revisar el
    # contenido completo, no solo título+desc, ver es_contenido_spam()).
    "cuotas para el mundial", "cuotas y favoritos", "mejores cuotas",
    "cuota mundial", "apostar en", "para apostar", "dónde apostar", "donde apostar",
    "pronóstico deportivo", "pronostico deportivo", "picks deportivos",
    "predicciones deportivas", "predicción deportiva", "prediccion deportiva",
    "favoritos para ganar el mundial", "quién es favorito para ganar",
    "quien es favorito para ganar", "handicap deportivo", "casa de apuestas online",
    # Afiliados y contenido promocional disfrazado
    "código promocional", "codigo promocional", "cupón descuento", "cupon descuento",
    "oferta exclusiva para", "regístrate ahora y obtén", "registrate ahora y obtén",
    "haz clic aquí para", "cómo conseguirlo en 2026", "como conseguirlo en 2025",
    "cómo obtener gratis", "como obtener gratis",
    "descuento exclusivo", "precio especial hoy",
    # Contenido SEO basura / granjas de contenido
    "top 10 mejores", "los mejores del mundo en 2026", "ranking definitivo de",
    "guía definitiva para ganar", "guia definitiva para ganar",
    "cómo ganar dinero con", "como ganar dinero con",
    # Préstamos / crypto spam
    "prestamo rapido online", "préstamo rápido online", "credito inmediato",
    "crédito inmediato", "bitcoin gratis", "cripto gratis",
    "ganar criptomonedas", "invertir en crypto desde",
]

def es_contenido_spam(titulo, descripcion=""):
    """
    V17.6.4: Detecta si una noticia es contenido spam, publicitario o de apuestas.
    Retorna (True, motivo) si es spam, (False, None) si es legítima.
    """
    txt = f"{titulo} {descripcion}".lower()
    for keyword in BLACKLIST_CONTENIDO_SPAM:
        if keyword.lower() in txt:
            return True, keyword
    return False, None

# ──────────────────────────────────────────────────────────
# DETECCIÓN DE TEMA — V17.6.7
# ──────────────────────────────────────────────────────────
def detectar_tema(titulo, descripcion=""):
    """
    V17.6.7: Clasificación mejorada con keywords más precisas y sin colisiones.
    Orden de prioridad:
      1. Desastre natural (terremoto, tsunami, huracán)
      2. Crimen organizado / seguridad
      3. Guerra/conflicto armado (keywords específicas, no genéricas)
      4. Deportes (fútbol, Copa Libertadores, Champions, NBA, etc.)
      5. Entretenimiento (artistas, cine, series, premios)
      6. Tecnología (IA, gadgets, ciberseguridad, startups)
      7. Economía (inflación, dólar, bolsa, bancos centrales)
      8. Medio ambiente / Clima (deforestación, Amazonía, bosques)
      9. Salud / Medicina
      10. Ciencia / Espacio
      11. Política (elecciones, gobierno, diplomacia)
      12. Educación
      13. Religión
      14. Latinoamérica (fallback regional si no hubo categoría temática)
      15. Mundo (fallback internacional)
      16. General (último recurso)
    CAMBIO CLAVE V17.6.7: latinoamerica ya NO está en prioridad 4.
    Ahora es fallback (prioridad 14) para noticias LATAM sin tema dominante.
    """
    txt = f"{titulo} {descripcion}".lower()

    # ── Prioridad 1: Desastre natural / emergencia (antes que guerra)
    if any(p in txt for p in [
        "terremoto", "sismo", "huracan", "huracán", "inundacion", "inundación",
        "desastre natural", "tsunami", "erupcion volcanica", "erupción volcánica",
        "tormenta tropical", "derrumbe", "aluvion", "aluvión",
        "alerta de tsunami", "victimas del desastre", "catastrofe natural",
        "incendio forestal masivo", "explosion industrial",
    ]):
        return 'desastre'

    # ── Prioridad 2: Crimen / Seguridad
    if any(p in txt for p in [
        "asesinato", "homicidio", "narcotrafico", "narcotráfico", "cartel",
        "crimen organizado", "mafia", "fraude millonario",
        "banda criminal", "sicario", "feminicidio", "masacre",
        "narcotraficante", "policia abate", "detenidos por crimen",
    ]):
        return 'crimen'

    # ── Prioridad 3: Guerra / Conflicto armado (keywords ESPECÍFICAS, no genéricas)
    if any(p in txt for p in [
        "guerra", "bombardeo", "misil balístico", "misil balistico",
        "conflicto armado", "invasion", "invasión", "tropas rusas", "tropas ucranianas",
        "hamas", "hezbollah", "hezbola", "otan en guerra", "nato en guerra",
        "ataque aéreo", "ataque aereo", "ofensiva militar", "contraofensiva militar",
        "drones militares", "drones de combate", "dron de ataque",
        "muertos en combate", "bombardeado", "fuego cruzado", "bajas militares",
        "intercambio de fuego", "fusilamiento",
        "ataque terrorista", "atentado terrorista",
        "fuerzas armadas en", "marina de guerra",
        "portaviones", "fragata", "submarino de guerra",
        "misil interceptado", "defensa aerea", "iron dome",
        "civiles muertos en", "palestin", "cisjordania",
        "huti", "houthis", "zona de guerra", "frente de batalla",
        "convoy militar", "base militar atacada", "prisionero de guerra",
        "guerra civil", "milicias armadas", "paramilitares",
        "alto el fuego", "cese del fuego", "cese al fuego",
        "ucrania bombardeada", "gaza bombardeada", "israel ataca",
        "rusia ataca", "iran nuclear", "corea del norte misil",
    ]):
        return 'guerra'

    # ── Prioridad 4: Deportes — fútbol, Copa Libertadores, Mundial, NBA, etc.
    if any(p in txt for p in [
        "futbol", "fútbol", "copa libertadores", "copa sudamericana",
        "copa del mundo", "mundial de futbol", "mundial 2026",
        "champions league", "premier league", "laliga", "la liga",
        "serie a futbol", "bundesliga", "mls futbol",
        "eliminatoria", "eliminatorias mundialistas", "clasificacion mundial",
        "gol", "penalti", "penalto", "arbitro", "partido de futbol",
        "seleccion chilena", "seleccion argentina", "seleccion colombiana",
        "seleccion brasileña", "seleccion mexicana", "la roja",
        "colo-colo", "universidad de chile", "river plate", "boca juniors",
        "nba", "baloncesto", "basquetbol",
        "tenis", "djokovic", "alcaraz", "wimbledon",
        "formula 1", "f1", "gran premio",
        "olimpiadas", "juegos olimpicos",
        "atletismo", "boxeo", "ufc", "rugby",
        "ciclismo tour", "natacion mundial",
        "fichaje futbol", "traspaso deportivo", "transfer futbolistico",
        "semifinal deportiva", "final deportiva", "campeón deportivo",
        "medalla de oro", "medalla de plata",
        "messi", "cristiano ronaldo", "mbappe", "neymar futbol",
        "lebron james", "stephen curry",
        "verstappen formula",
    ]):
        return 'deportes'

    # ── Prioridad 5: Entretenimiento — artistas, cine, series, premios
    if any(p in txt for p in [
        "pelicula estreno", "película estreno", "estreno de pelicula",
        "trailer oficial", "tráiler oficial", "estreno mundial cine",
        "taquilla", "recaudacion en cines", "box office",
        "oscar", "grammy", "emmy", "golden globe", "bafta", "latin grammy",
        "festival de cine", "cannes", "sundance", "venecia film",
        "album musical", "álbum musical", "nuevo album", "nuevo álbum",
        "gira musical", "concierto de", "lanzamiento musical", "videoclip",
        "spotify charts", "billboard charts", "numero uno musical",
        "taylor swift", "bad bunny", "shakira", "beyonce", "rihanna",
        "billie eilish", "the weeknd", "drake",
        "karol g", "maluma", "j balvin", "rauw alejandro",
        "rosalía", "rosalia", "daddy yankee", "ozuna",
        "netflix estrena", "netflix serie", "disney plus estreno",
        "serie de tv", "temporada de", "segunda temporada",
        "actor de cine", "actriz premiada", "director de cine",
        "reggaeton", "musica pop latin", "artista latin",
        "reality show", "tiktoker viral", "youtuber",
        "reloj de lujo", "rolex", "audemars patek",
        "moda de lujo", "haute couture", "louis vuitton coleccion",
        "marvel pelicula", "star wars serie", "anime estreno",
        "secuela pelicula", "remake pelicula",
        "celebrity", "celebridad",
    ]):
        return 'entretenimiento'

    # ── Prioridad 6: Tecnología — IA, ciberseguridad, startups, gadgets
    if any(p in txt for p in [
        "inteligencia artificial", "chatgpt", "openai", "gemini google",
        "deepseek", "llm ", "modelo de lenguaje", "ia generativa",
        "robot", "automatizacion tecnologica", "automatización tecnológica",
        "ciberataque", "hackeo", "ciberseguridad", "ransomware",
        "elon musk", "spacex", "starlink", "tesla tecnologia",
        "openai", "microsoft ia", "google ia", "meta ia",
        "samsung galaxy", "apple iphone", "ipad", "macbook",
        "chip semiconductor", "nvidia gpu", "quantum computing",
        "startup tecnologica", "startup tecnológica", "fintech",
        "blockchain", "criptomoneda", "bitcoin tecnologia",
        "metaverso", "realidad virtual", "realidad aumentada",
        "5g", "6g", "internet de las cosas", "iot",
        "huawei", "deepmind", "anthropic", "xai",
        "smartwatch", "apple watch", "galaxy watch", "wearable",
        "reloj inteligente", "garmin sport", "fitbit",
        "software", "app nueva", "plataforma digital",
        "red neuronal", "machine learning", "big data",
        "startups tecnologica", "startups tecnológica",
        "innovacion tecnologica", "innovación tecnológica",
    ]):
        return 'tecnologia'

    # ── Prioridad 7: Economía — inflación, dólar, bolsa, bancos centrales
    if any(p in txt for p in [
        "inflacion", "inflación", "recesion", "recesión",
        "bolsa de valores", "mercado financiero", "mercado bursatil",
        "dolar", "dólar", "euro cae", "euro sube", "tipo de cambio",
        "fmi acuerdo", "banco central", "reserva federal",
        "crisis economica", "crisis económica", "aranceles",
        "exportaciones", "importaciones",
        "pib", "producto interno bruto", "desempleo",
        "banco mundial", "deuda externa", "deuda publica",
        "crecimiento economico", "contraccion economica",
        "wall street", "nasdaq", "dow jones", "ibex 35", "merval bolsa",
        "petroleo precio", "precio del petroleo", "barril de petroleo",
        "gas natural precio",
        "inversion extranjera", "deficit fiscal", "superavit",
        "bonos soberanos", "riesgo pais",
        "transporte publico tarifa", "metro de", "linea de metro",
        "aeropuerto concesion", "autopista concesion", "obra publica",
        "escasez de divisas", "fuga de divisas", "reservas en dolares",
        "libre comercio", "tratado comercial", "acuerdo comercial",
        "crisis de divisas", "devaluacion", "devaluación",
    ]):
        return 'economia'

    # ── Prioridad 8: Medio ambiente / Clima (ANTES de ciencia — "NASA" como fuente no es ciencia)
    if any(p in txt for p in [
        "cambio climatico", "cambio climático", "calentamiento global",
        "temperatura record", "sequia", "sequía",
        "incendio forestal", "contaminacion ambiental", "co2 emisiones",
        "medio ambiente", "cop30", "cop29", "emision de carbono",
        "biodiversidad", "extincion de especies", "deforestacion", "deforestación",
        "desmonte", "tala ilegal", "tala de bosque", "tala de arboles",
        "bosque", "selva", "amazonía", "amazonia", "amazonas",
        "reserva natural", "area protegida", "área protegida",
        "pueblos indigenas", "pueblos indígenas", "territorio indigena", "territorio indígena",
        "expansion agricola", "expansión agrícola", "frontera agricola",
        "plastico en el oceano", "energia renovable",
        "energia solar", "energia eolica", "hidrogeno verde",
        "huella de carbono", "acuerdo de paris clima", "ipcc",
        "ola de calor", "ciclon", "tornado",
        "lluvia intensa", "frente frio", "pronostico meteorologico",
        "conservacion ambiental", "conservación ambiental",
        "recursos naturales", "ecosistema", "fauna silvestre", "flora silvestre",
        "glaciar", "deshielo", "nivel del mar",
    ]):
        return 'medio_ambiente'

    # ── Prioridad 9: Salud / Medicina
    if any(p in txt for p in [
        "cancer", "cáncer", "enfermedad", "hospital", "medico",
        "pandemia", "vacuna", "virus", "salud publica", "oms",
        "epidemia", "brote infeccioso", "medicamento",
        "cirugia", "cirugía", "diagnostico médico",
        "ensayo clinico", "tratamiento médico",
        "farmaco", "fármaco", "terapia medica", "cura enfermedad",
        "mortalidad por enfermedad", "obesidad", "diabetes",
        "hipertension", "salud mental", "antibiotico",
        "variante viral", "oncologia", "cardiologia",
    ]):
        return 'salud'

    # ── Prioridad 10: Ciencia / Espacio (keywords con contexto científico REAL)
    if any(p in txt for p in [
        "descubrimiento cientifico", "descubrimiento científico",
        "agencia espacial nasa", "mision de la nasa", "nasa lanza",
        "agencia espacial", "cohete espacial", "satelite lanzado",
        "planeta", "universo", "agujero negro", "exoplaneta",
        "investigacion cientifica", "investigación científica",
        "astronomia", "telescopio espacial", "marte exploracion",
        "particula subatomica", "laboratorio cientifico",
        "adn descubrimiento", "evolucion biologica",
        "esa agencia espacial", "supernova", "paleontologia",
        "premio nobel de", "fisica cuantica",
    ]):
        return 'ciencia'

    # ── Prioridad 11: Política — elecciones, gobierno, diplomacia
    if any(p in txt for p in [
        "eleccion", "elección", "elecciones presidenciales",
        "presidente anuncia", "gobierno de", "gabinete presidencial",
        "golpe de estado", "diplomacia", "cumbre diplomatica",
        "sancion diplomatica", "sanciones internacionales",
        "g7", "g20", "onu debate", "naciones unidas debate",
        "referendum", "parlamento aprueba", "congreso aprueba",
        "primer ministro", "canciller anuncia",
        "politica exterior", "relaciones diplomaticas",
        "campana electoral", "partido politico",
        "decreto presidencial", "reforma legislativa",
        "diputado", "senador", "alcalde",
        "oposicion politica", "coalicion gubernamental",
        "segunda vuelta", "balotaje", "comicios",
        "macron", "scholz", "sunak", "meloni", "modi",
        "xi jinping", "putin", "zelensky", "erdogan", "netanyahu",
        "acuerdo diplomatico", "bloqueo economico",
        "espionaje estatal", "embajador expulsado",
        "nota diplomatica",
        "trump anuncia", "biden anuncia", "harris anuncia",
        "sheinbaum anuncia", "boric anuncia", "milei anuncia",
        "petro anuncia", "lula anuncia", "maduro anuncia",
    ]):
        return 'politica'


    # ── Prioridad 12: Educación
    if any(p in txt for p in [
        "reforma educativa", "sistema educativo", "becas universitarias",
        "universidad publica", "escuelas publicas",
        "maestros en huelga", "profesores protestan",
        "prueba pisa", "educacion en",
    ]):
        return 'educacion'

    # ── Prioridad 13: Religión
    if any(p in txt for p in [
        "papa francisco", "vaticano", "iglesia católica", "iglesia catolicla",
        "islam", "judaismo", "budismo", "hinduismo",
        "mezquita", "sinagoga", "catedral",
        "pontífice", "pontifice", "cardenal", "encíclica",
        "pastor evangelico", "obispo",
    ]):
        return 'religion'

    # ── Prioridad 14: Latinoamérica (fallback regional)
    # Solo llega aquí si la noticia NO tiene categoría temática más específica.
    # Ejemplos: "Cumbre CELAC sin acuerdos", "Migración LATAM", noticias regionales genéricas.
    if any(p in txt for p in [
        "chile", "chilena", "chileno", "boric", "carabineros", "codelco",
        "mexico", "mexicano", "mexicana", "cdmx", "sheinbaum", "pemex",
        "argentina", "argentino", "buenos aires", "milei",
        "brasil", "brazil", "brasileño", "lula", "sao paulo", "brasilia",
        "colombia", "colombiano", "bogotá", "bogota", "petro",
        "perú", "peru", "peruano", "boluarte",
        "venezuela", "venezolano", "maduro", "caracas",
        "ecuador", "ecuatoriano", "noboa",
        "bolivia", "boliviano",
        "uruguay", "uruguayo", "montevideo",
        "paraguay", "paraguayo",
        "cuba", "cubano", "nicaragua", "guatemala", "honduras",
        "el salvador", "bukele", "panamá", "panama", "costa rica",
        "república dominicana", "dominicano", "haití", "haiti",
        "america latina", "latinoamerica", "latinoamericano", "latam",
        "centroamerica", "caribe", "sudamerica", "cono sur",
        "mercosur", "unasur", "celac", "alba",
        "conmebol eliminatorias", "seleccion de futbol",
        "peso chileno", "peso argentino", "peso mexicano",
        "real brasileiro", "bolívar venezolano",
        "banco central de chile", "banco de mexico",
        "litio chile", "litio bolivia", "cobre chileno",
        "petroleo venezolano", "gas de bolivia",
        "amazonía", "amazonia", "patagonia", "atacama",
    ]):
        return 'latinoamerica'

    # ── Prioridad 15: Mundo (geografía internacional sin categoría específica)
    if any(p in txt for p in [
        "africa", "asia pacifico", "europa occidental", "oriente medio",
        "naciones unidas", "onu cumbre", "cumbre mundial",
        "union europea", "brics",
    ]):
        return 'mundo'

    return 'general'


# ──────────────────────────────────────────────────────────
# CONTROL DE CUOTAS DIARIAS
# ──────────────────────────────────────────────────────────
def cargar_cuotas_hoy():
    datos = cargar_json(CUOTAS_CONTROL_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy:
        return {'fecha': hoy, 'conteo': {}}
    return datos

def registrar_cuota(categoria):
    datos = cargar_cuotas_hoy()
    datos['conteo'][categoria] = datos['conteo'].get(categoria, 0) + 1
    guardar_json(CUOTAS_CONTROL_PATH, datos)

def categoria_disponible(categoria, total_dia=48):
    datos = cargar_cuotas_hoy()
    conteo = datos['conteo'].get(categoria, 0)
    maximo = max(1, int(total_dia * CUOTAS_CATEGORIA.get(categoria, {}).get('cuota', 0.10)))
    return conteo < maximo

def es_categoria_critica(categoria):
    """
    Categorías que NO deben reclasificarse por cuota.
    Una noticia de guerra NO puede convertirse en 'tecnologia' para mejorar CPM.
    La integridad editorial es prioritaria.
    """
    return categoria in ('guerra', 'crimen', 'desastre')

def ajustar_categoria_por_cuota(categoria):
    # V15: Las categorías críticas (guerra, crimen, desastre) nunca se reclasifican.
    # Publicar una noticia de guerra como 'tecnologia' daña la credibilidad del sitio.
    if es_categoria_critica(categoria):
        return categoria
    if categoria_disponible(categoria):
        return categoria
    log(f"📊 Cuota llena para '{categoria}' — buscando alternativa brand-safe", 'advertencia')
    alternativas = sorted(
        [(c, v) for c, v in CUOTAS_CATEGORIA.items()
         if v.get('brand_safe') and categoria_disponible(c)
         and not es_categoria_critica(c)],
        key=lambda x: -x[1]['cpm_relativo']
    )
    if alternativas:
        nueva = alternativas[0][0]
        log(f"   → Reasignado a '{nueva}' (CPM {CUOTAS_CATEGORIA[nueva]['cpm_relativo']}x)", 'info')
        return nueva
    return categoria

def es_brand_safe(categoria):
    return CUOTAS_CATEGORIA.get(categoria, {}).get('brand_safe', True)


# ──────────────────────────────────────────────────────────
# REESCRITURA CON IA (SEO avanzado)
# ──────────────────────────────────────────────────────────
def reescribir_noticia_v9(titulo, contenido, categoria_sugerida='general'):
    """
    V16: La IA lee el contenido completo y decide la categoría correcta.
    La categoria_sugerida es solo una pista inicial — la IA puede y debe corregirla.
    Devuelve dict con: titulo_seo, meta_descripcion, contenido_html,
                       keyword_principal, keywords_secundarias, categoria
    """
    api_key = GROQ_API_KEY or OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        return None

    # V17.6.3: Calcular tiempo de lectura estimado para el box resumen
    palabras_contenido = len(contenido.split())
    tiempo_lectura = max(2, round(palabras_contenido / 200))  # ~200 palabras/min lector promedio

    # V17.6.3: Rotacion aleatoria del titulo del box resumen — variedad visual entre articulos
    TITULOS_BOX_RESUMEN = [
        ('⚡', 'Lo que debes saber'),
        ('📌', 'Lo esencial'),
        ('🔑', 'Puntos clave'),
        ('📋', 'Resumen rápido'),
    ]
    emoji_box, texto_box = random.choice(TITULOS_BOX_RESUMEN)
    titulo_box_resumen = f"{emoji_box} {texto_box}"

    prompt = f"""Eres el Editor Jefe Digital de VerdadHoy.com, medio de noticias en español para América Latina.
Tu tarea: clasificar correctamente esta noticia y redactarla como un artículo periodístico ORIGINAL con valor editorial propio.

IMPORTANTE: No eres un parafraseador. Eres un periodista que toma los datos de la noticia fuente
y escribe un artículo NUEVO con análisis, contexto adicional y perspectiva propia para el lector latinoamericano.
El artículo debe poder existir de forma independiente al original — Google penaliza el contenido que es
solo una reescritura. Agrega al menos un dato de contexto, una perspectiva editorial o una implicación
práctica que el original NO menciona.

VerdadHoy.com tiene audiencia en Chile, Argentina, México, Colombia, Perú, Brasil y toda América Latina.

═══════════════════════════════════════
NOTICIA A PROCESAR:
Título original: {titulo}
Contenido: {contenido[:3000]}
Categoría sugerida por sistema: {categoria_sugerida}
Tiempo de lectura estimado: {tiempo_lectura} min
═══════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 1 — CLASIFICACIÓN V17.6.5: Elige la categoría MÁS ESPECÍFICA que describe el tema real de la noticia.
No uses "latinoamerica" como categoría genérica para todo.

⚠️ REGLAS ANTI-ERRORES FRECUENTES:
→ Noticias de España, Francia, UK, Alemania, Italia, Asia → "mundo" (no "politica", no "latinoamerica")
→ Transporte público, infraestructura, tren, metro, aeropuertos → "economia" o "mundo"
→ "politica" SOLO si hay: elecciones, líderes de gobierno tomando decisiones, diplomacia activa
→ Relojería de lujo, moda, colaboraciones de marcas → "entretenimiento"
→ Wearables, smartwatch, tecnología ponible → "tecnologia"
→ Empresa estatal, consejo de administración, tarifas → "economia"

• "latinoamerica"  → SOLO si el tema de la noticia es regional sin categoría temática más específica.
                     Úsala para: relaciones entre países LATAM, organismos regionales (CELAC,
                     MERCOSUR, ALBA), noticias sin tema dominante claro de otro tipo.
                     ❌ NO usar si la noticia tiene categoría temática más específica:
                       - "Inflación en Argentina" → "economia" (no latinoamerica)
                       - "Elecciones en Colombia" → "politica" (no latinoamerica)
                       - "Messi en la Copa Libertadores" → "deportes" (no latinoamerica)
                       - "Shakira lanza álbum en Colombia" → "entretenimiento" (no latinoamerica)
                       - "Chile sufre terremoto" → "desastre" (no latinoamerica)
                       - "IA en startups de Brasil" → "tecnologia" (no latinoamerica)
                       - "Lula anuncia reforma económica" → "economia" (no latinoamerica)
                       - "Petro firma decreto presidencial" → "politica" (no latinoamerica)
                     ✅ SÍ usar si:
                       - "Cumbre de presidentes latinoamericanos sin agenda concreta"
                       - "CELAC debate integración regional"
                       - "Migración venezolana impacta a varios países de LATAM"
                       - "América Latina y la deuda con el FMI" (sin economía específica)
                     REGLA: Si puedes usar una categoría más específica → úsala siempre.

• "deportes"       → TODO lo deportivo: fútbol (Champions, Copa Libertadores, eliminatorias,
                     Mundial 2026, ligas), tenis, NBA, F1, boxeo, atletismo, etc.
                     ⚠️ Una noticia sobre zapatos de fútbol, lesión de un jugador, estadios,
                     transferencias, VAR, árbitros → es DEPORTES, no latinoamerica.

• "entretenimiento"→ Música (aunque sea Ana Torroja, Shakira, Bad Bunny, Karol G),
                     cine, series, premios (Grammy, Oscar, Latin Billboard), reality shows,
                     plataformas de streaming, celebridades, festivales de música.
                     ⚠️ Una noticia de un artista que lanza un álbum → ENTRETENIMIENTO.

• "economia"       → Mercados, inflación, dólar, aranceles, petróleo, criptomonedas,
                     bancos centrales, comercio internacional, recesión, PIB.

• "tecnologia"     → IA, ciberseguridad, startups, redes sociales, gadgets, software,
                     innovación tecnológica, fintech.

• "politica"       → Decisiones gubernamentales, elecciones, diplomacia, líderes mundiales,
                     sanciones, cumbres. Incluye: Netanyahu, Trump, Sánchez, Macron, etc.
                     cuando toman decisiones políticas.

• "ciencia"        → Descubrimientos, espacio, NASA, física, biología, astronomía.

• "salud"          → Enfermedades, vacunas, medicamentos, OMS, hospitales, salud mental.

• "medio_ambiente" → Cambio climático, Amazonía, glaciares, energía renovable, biodiversidad.

• "guerra"         → Conflictos armados, bombardeos, misiles, tropas, terrorismo, víctimas de guerra.

• "desastre"       → Terremotos, huracanes, tsunamis, inundaciones con víctimas.

• "mundo"          → Internacional sin categoría más específica. Noticias de política exterior,
                     organismos internacionales (ONU, FMI, G20) cuando no hay categoría mejor.

• "general"        → Solo si ninguna otra categoría encaja.

REGLA DE ORO: Usa la categoría más ESPECÍFICA. Si es sobre fútbol → deportes. Si es sobre
un cantante → entretenimiento. "Latinoamerica" es para noticias cuyo eje central ES un país
o tema de la región, no para noticias globales a las que se les añade "y su impacto en LATAM".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 2 — TÍTULO SEO (máx 60 caracteres):
- La keyword principal en las primeras 3 palabras
- Describe el tema real sin exagerar ni forzar conexiones
- NO añadir "en LATAM" o "para Chile" si la noticia no es genuinamente sobre eso
- Sí incluir país/región en el título si la noticia ES de ese país: "Colombia reduce...",
  "Argentina anuncia...", "Chile enfrenta..."
- Para noticias globales con impacto real en LATAM: "Cómo afecta X a América Latina"
- Para deportes: título directo sobre el hecho deportivo
- Para entretenimiento: título sobre el artista/obra/evento real

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 3 — ARTÍCULO COMPLETO (estructura V17.9.0 — retención de lectura + 4 H2):

⚠️ REGLA CRÍTICA DE ESTRUCTURA: El artículo debe comenzar SIEMPRE con el box resumen
y seguir el orden exacto indicado. Esto aumenta el tiempo de lectura y la retención.

── ELEMENTO 1: BOX RESUMEN "EN 30 SEGUNDOS" (OBLIGATORIO — va primero siempre) ──
<div style="background:#f0f4ff;border-left:4px solid #1a56db;padding:16px 20px;margin:0 0 24px 0;border-radius:0 8px 8px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:#1a56db;font-size:0.95em;">{titulo_box_resumen}</p>
<ul style="margin:0;padding-left:20px;color:#374151;">
<li style="margin-bottom:6px;">[Punto clave 1 — el hecho principal en 1 línea]</li>
<li style="margin-bottom:6px;">[Punto clave 2 — el dato más relevante]</li>
<li style="margin-bottom:6px;">[Punto clave 3 — consecuencia o contexto importante]</li>
<li style="margin-bottom:0;">[Punto clave 4 — quién, cuándo o dónde si aplica]</li>
</ul>
</div>

── ELEMENTO 2: APERTURA ──
<p>[Apertura ≤40 palabras: Qué/Quién/Cuándo/Dónde — datos concretos del hecho real. NO copies el lead del artículo fuente. Abre con el dato más impactante, una cifra o la consecuencia directa. Máx 2 oraciones cortas en voz activa.]</p>

── ELEMENTO 3: PRIMER H2 + CONTEXTO (⚠️ OBLIGATORIO antes de la palabra 100) ──
<h2>[H2 #1 — debe contener la keyword principal o una variante]</h2>
<p>[Por qué importa esta noticia ahora. Antecedentes en 2 oraciones cortas (máx 20 palabras cada una).]</p>

── ELEMENTO 4: DESARROLLO PRINCIPAL ──
<p>[Primer párrafo de desarrollo — hechos y datos principales. Usa <strong>3-4 términos clave</strong>. Máx 2 oraciones.]</p>
<p>[Segundo párrafo — VALOR AGREGADO OBLIGATORIO: incluye un dato de contexto, antecedente histórico o comparación regional que el artículo fuente NO menciona explícitamente. Este párrafo demuestra análisis editorial propio. Máx 2 oraciones.]</p>
<h2>[H2 #2 — ángulo diferente del primero, informativo y con keyword secundaria]</h2>
<p>[Tercer párrafo — datos adicionales o perspectiva complementaria. Máx 2 oraciones.]</p>
<h2>[H2 #3 — un tercer ángulo del tema: consecuencias, reacciones, cifras o próximos pasos]</h2>
<p>[Cuarto párrafo — profundiza en ese ángulo con datos concretos. Máx 2 oraciones.]</p>

── ELEMENTO 5: DATO DESTACADO (OBLIGATORIO — rompe monotonía visual) ──
<blockquote style="border-left:3px solid #e5e7eb;padding:12px 16px;margin:20px 0;background:#f9fafb;font-style:italic;color:#4b5563;">
[Cita textual o dato estadístico relevante del artículo — máx 2 líneas. Si no hay cita, usa el dato más impactante con formato: "Según [fuente], [dato concreto]."]
</blockquote>

── ELEMENTO 6: SECCIÓN FINAL SEGÚN CATEGORÍA (H2 #4 — obligatorio, cierra el desarrollo) ──

▶ Si categoría = "latinoamerica":
<h2>Contexto regional</h2>
<p>[Amplía cómo este hecho afecta a otros países de la región. Menciona al menos 2 países con datos concretos. Ya ES de LATAM — no necesita conectar artificialmente. Máx 3 líneas.]</p>

▶ Si categoría = "economia" O "politica" O "tecnologia" O "medio_ambiente" O "guerra":
(Solo si hay impacto REAL y CONCRETO en América Latina — no solo teórico)
<h2>Qué significa esto para América Latina</h2>
<p>[Impacto específico en la región con datos reales. Menciona Chile y al menos otro país latinoamericano. Si el impacto es mínimo o especulativo, OMITE esta sección.]</p>

▶ Si categoría = "deportes":
<h2>Análisis del encuentro</h2>
<p>[Estadísticas, actuaciones destacadas, próximos partidos o contexto del torneo. Perspectiva LATAM solo si hay jugadores o equipos de la región involucrados de manera central.]</p>

▶ Si categoría = "entretenimiento":
<h2>Por qué importa</h2>
<p>[Contexto artístico, recepción del público, datos de audiencia o streaming. Mencionar LATAM solo si el artista es latinoamericano o el evento es en la región.]</p>

▶ Si categoría = "ciencia" O "salud":
<h2>Lo que dicen los expertos</h2>
<p>[Contexto científico e implicaciones prácticas para la población. Contexto latinoamericano solo si hay datos de la región.]</p>

── ELEMENTO 7: CIERRE CON PREGUNTA (OBLIGATORIO) ──
<p>[Reflexión final o dato de perspectiva que aporte valor. Terminar con una pregunta genuina y abierta que invite al lector a pensar o compartir su opinión. Ejemplo: "¿Crees que esta medida tendrá el impacto esperado?" o "¿Cómo afectará esto a tu día a día?". La pregunta debe ser específica al tema, no genérica. NO pedir comentarios ni suscripciones directamente.]</p>

[ENLACES_INTERNOS]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGLAS DE CALIDAD V17.9.0 — VALOR EDITORIAL ORIGINAL + YOAST SEO:

⚠️ REGLA MAESTRA (AdSense / anti-scraping):
Tu artículo NO es una paráfrasis del original. Es un artículo periodístico
NUEVO que usa los datos del original como punto de partida.

VALOR EDITORIAL OBLIGATORIO — cada artículo DEBE incluir al menos 2 de estos:
1. Un dato de CONTEXTO que el original no menciona pero que el lector necesita
   (ej: antecedente histórico, comparación regional, cifra relacionada)
2. Una PERSPECTIVA editorial clara: ¿por qué esto importa a Chile/LATAM HOY?
   (no "podría afectar" — una afirmación editorial concreta)
3. Una COMPARACIÓN o CONTRASTE con otro hecho reciente o tendencia regional
4. Una IMPLICACIÓN PRÁCTICA para el lector latinoamericano
   (ej: "Para los chilenos que tienen ahorros en dólares, esto significa...")

ORIGINALIDAD ESTRUCTURAL — PROHIBIDO:
- PROHIBIDO copiar la estructura del lead original (aunque cambies palabras)
- PROHIBIDO reproducir el orden de los párrafos del artículo fuente
- PROHIBIDO usar las mismas frases aunque las reformules levemente
- Escribe como si solo conocieras los DATOS del original, no el texto

APERTURA ORIGINAL (≤40 palabras):
- NO comenzar igual que el artículo fuente
- Abre con el dato más impactante o con la pregunta que responde la noticia
- Ejemplos válidos: cifra impactante, consecuencia directa, nombre propio + acción
- Ejemplos inválidos: "[Medio] informó que..." / "Según reportes..." / pasiva refleja

LONGITUD Y ESTRUCTURA:
- Mínimo 550 palabras, máximo 800 palabras
- PRIMER H2 obligatorio antes de la palabra 100 del artículo (Yoast lo penaliza si no)
- Mínimo 4 subtítulos H2 — cada uno debe abrir un ángulo diferente del tema
- Párrafos de MÁXIMO 2-3 líneas (máx 25 palabras por oración — requisito Yoast)
- Alternar párrafos cortos (1-2 líneas) con párrafos medianos (3 líneas)

FRASES Y LEGIBILIDAD (crítico para Yoast):
- MÁXIMO 25% de frases con más de 25 palabras
- Si una oración supera 25 palabras → dividirla en dos
- Voz activa siempre: "El gobierno anunció" no "fue anunciado por el gobierno"
- Palabras de transición: sin embargo, además, por otro lado, en consecuencia,
  a su vez, no obstante, por ejemplo, en primer lugar, finalmente, asimismo

KEYWORD SEO (crítico para Yoast):
- keyword_principal en: título, primer párrafo (antes de la palabra 100), al menos 1 H2, y cierre
- keywords_secundarias: mínimo 4, máximo 6 — palabras reales del texto
- Densidad de keyword principal: 1-2% del texto total
- NO repetir la keyword más de 3 veces en el mismo párrafo

ESTRUCTURA HTML:
- Box resumen → apertura → H2 → desarrollo → H2 → sección especial → H2 → cierre
- <strong> en 4-6 términos clave distribuidos en todo el artículo
- <ul><li> para listas de 3+ items
- <blockquote> para datos estadísticos o citas importantes

CLASIFICACIÓN:
- España, Francia, Alemania, Italia, UK → "mundo"
- Transporte público, infraestructura → "economia" o "mundo"
- "politica" SOLO para decisiones de gobierno con impacto real
- Relojería, moda, lujo → "entretenimiento"
- Wearables, smartwatch → "tecnologia"

ESPAÑOL NEUTRO LATINOAMERICANO:
- Sin regionalismos de España (evitar: "vosotros", "tío", "guay", "coger")
- Sin anglicismos innecesarios

PROHIBICIONES ABSOLUTAS:
- PROHIBIDO: Inventar datos, citas o cifras no presentes en el contenido original
- PROHIBIDO: "y su impacto en LATAM" al título si no es genuinamente relevante
- PROHIBIDO: Reproducir más de 5 palabras consecutivas del texto fuente
- BRAND SAFE: Sin lenguaje gráfico en guerra/crimen, sin conteo detallado de bajas

META DESCRIPCIÓN: 140-155 caracteres exactos.
- Incluir la keyword principal
- Describir el valor real del artículo (no prometer "descubre", "conoce", "entérate")
- Terminar con un dato concreto o pregunta que genere curiosidad

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTOVALIDACIÓN OBLIGATORIA ANTES DE RESPONDER (V17.9.0):
Antes de entregar el JSON, revisa tu propio borrador punto por punto contra este
checklist — es el mismo que se usa para la edición manual de VerdadHoy. Si algún
punto falla, CORRIGE el artículo tú mismo y vuelve a revisarlo. Solo entrega el
JSON cuando todos los puntos se cumplan. No menciones el checklist en la respuesta,
es un paso interno.

  1. La keyword principal aparece en el primer párrafo, antes de la palabra 100.
  2. La keyword principal aparece en el título SEO.
  3. La keyword principal (o una variante natural) aparece en al menos un H2.
  4. La keyword principal aparece en la meta descripción.
  5. Hay exactamente 4 subtítulos H2, cada uno con un ángulo distinto.
  6. El box resumen "en 30 segundos" va primero, con 4 puntos concretos.
  7. Ningún párrafo supera 2-3 líneas / 25 palabras por oración.
  8. Como máximo el 25% de las oraciones supera las 25 palabras.
  9. Se usan al menos 5 palabras de transición (sin embargo, además, por otro
     lado, en consecuencia, asimismo, no obstante, por ejemplo, finalmente...).
  10. El artículo tiene entre 550 y 800 palabras.
  11. Existe el dato de contexto/valor editorial que el original no menciona.
  12. El cierre termina con una pregunta genuina y específica al lector.
  13. [ENLACES_INTERNOS] aparece tal cual, al final del contenido_html.
  14. No hay frases ni estructura de párrafo copiadas del artículo original.
  15. El texto suena a periodista humano, no a resumen automático de IA.

RESPONDE ÚNICAMENTE con este JSON sin markdown ni texto extra:
{{"titulo_seo": "...", "meta_descripcion": "...", "contenido_html": "<div style=...>[BOX]</div><p>...</p>...[ENLACES_INTERNOS]", "keyword_principal": "...", "keywords_secundarias": ["kw2","kw3","kw4","kw5"], "categoria": "latinoamerica|deportes|economia|tecnologia|entretenimiento|politica|ciencia|salud|medio_ambiente|guerra|desastre|mundo|general"}}"""

    def _llamar_api_ia(url_api, headers, modelo, payload):
        """
        V17.9.4: request a la API de IA aislado en su propia función para poder
        reutilizarlo tanto para el proveedor principal como para el fallback.
        Devuelve (resp_json, None) si la llamada fue exitosa, o (None, motivo)
        si falló — motivo en {'credito','rate_limit','auth','modelo','otro'}.
        """
        try:
            resp = requests.post(url_api, headers=headers, json=payload, timeout=55)
        except Exception as e:
            log(f"❌ IA: error de red llamando a {url_api}: {e}", 'error')
            return None, 'otro'
        try:
            resp_json = resp.json()
        except Exception:
            log(f"❌ IA: respuesta no es JSON válido (HTTP {resp.status_code}): {resp.text[:200]}", 'error')
            return None, 'otro'

        if "choices" not in resp_json:
            err = resp_json.get("error", {})
            if isinstance(err, dict):
                msg  = err.get("message", str(resp_json)[:200])
                code = err.get("code", resp.status_code)
            else:
                msg  = str(err)[:200]
                code = resp.status_code
            log(f"❌ IA devolvió error (HTTP {resp.status_code}, code={code}): {msg}", 'error')
            msg_lower = str(msg).lower()
            if "insufficient" in msg_lower or "quota" in msg_lower or "credit" in msg_lower or "balance" in msg_lower:
                log("   💳 CAUSA PROBABLE: Sin créditos/saldo en la API.", 'error')
                return None, 'credito'
            elif "rate limit" in msg_lower or code == 429:
                log("   ⏳ CAUSA PROBABLE: Rate limit alcanzado.", 'advertencia')
                return None, 'rate_limit'
            elif ("invalid" in msg_lower and "key" in msg_lower) or code == 401:
                log("   🔑 CAUSA PROBABLE: API key inválida o expirada. Verifica los GitHub Secrets.", 'error')
                return None, 'auth'
            elif "model" in msg_lower:
                log(f"   🤖 CAUSA PROBABLE: Modelo '{modelo}' no disponible o nombre incorrecto.", 'error')
                return None, 'modelo'
            return None, 'otro'
        return resp_json, None

    try:
        # V17.9.5: Groq como proveedor GRATUITO principal. Se arma una lista
        # ordenada de proveedores disponibles (según qué API keys existan) y
        # se prueba uno por uno — el primero que responda gana. Antes de esto
        # solo existía OpenRouter→OpenAI; ahora Groq va primero porque no
        # cuesta nada y usa el mismo formato "estilo OpenAI" que ya soporta
        # _llamar_api_ia(), así que no hace falta tocar el resto del parseo.
        proveedores = []
        if GROQ_API_KEY:
            proveedores.append((
                "Groq",
                "https://api.groq.com/openai/v1/chat/completions",
                {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                "llama-3.3-70b-versatile",
            ))
        if OPENROUTER_API_KEY:
            proveedores.append((
                "OpenRouter",
                "https://openrouter.ai/api/v1/chat/completions",
                {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                "openai/gpt-4o-mini",
            ))
        if OPENAI_API_KEY:
            proveedores.append((
                "OpenAI",
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                "gpt-4o-mini",
            ))

        # V17.4 FIX: max_tokens subido a 3500 para evitar JSON cortado
        # El prompt ocupa ~1500-1800 tokens; necesitamos al menos 1500 para el artículo completo
        resp_json = None
        motivo    = 'otro'
        url_api = headers = modelo = payload = None
        for i, (nombre, url_i, headers_i, modelo_i) in enumerate(proveedores):
            payload_i = {"model": modelo_i, "messages": [{"role": "user", "content": prompt}],
                         "temperature": 0.35, "max_tokens": 3500}
            if i > 0:
                log(f"   🔁 Reintentando con {nombre}...", 'advertencia')
            resp_json, motivo = _llamar_api_ia(url_i, headers_i, modelo_i, payload_i)
            if resp_json is not None:
                url_api, headers, modelo, payload = url_i, headers_i, modelo_i, payload_i
                if i > 0:
                    log(f"   ✅ Fallback a {nombre} exitoso", 'exito')
                break
            # Cada proveedor es una cuenta/clave distinta, así que un error
            # con uno (crédito, rate limit, auth, modelo) no implica el mismo
            # resultado en el siguiente — probamos igual con el que sigue.

        if resp_json is None:
            return None

        # V17.4 FIX: Verificar finish_reason — si es 'length', el JSON está cortado
        choice       = resp_json["choices"][0]
        finish_reason = choice.get("finish_reason", "stop")
        if finish_reason == "length":
            log("⚠️ IA cortó respuesta por longitud (finish_reason=length) — reintentando con contenido más corto", 'advertencia')
            # Reintentar con contenido más corto para que quepa en tokens
            prompt_corto = prompt.replace(contenido[:3000], contenido[:1500])
            payload["messages"] = [{"role": "user", "content": prompt_corto}]
            payload["max_tokens"] = 3500
            resp = requests.post(url_api, headers=headers, json=payload, timeout=55)
            try:
                resp_json = resp.json()
            except Exception:
                log(f"❌ IA reintento: respuesta no es JSON válido (HTTP {resp.status_code})", 'error')
                return None
            if "choices" not in resp_json:
                log(f"❌ IA reintento devolvió error: {str(resp_json.get('error', resp_json))[:200]}", 'error')
                return None
            choice = resp_json["choices"][0]
            finish_reason = choice.get("finish_reason", "stop")
            if finish_reason == "length":
                log("⚠️ Segunda respuesta también cortada — usando fallback", 'advertencia')
                return None

        texto = choice["message"]["content"].strip()
        texto = re.sub(r'^```json\s*|```$', '', texto, flags=re.MULTILINE).strip()

        # V17.4 FIX: Verificar que el JSON esté completo antes de parsear
        if not texto.endswith('}'):
            log(f"⚠️ JSON incompleto (no termina en '}}') — respuesta cortada", 'advertencia')
            return None

        resultado = json.loads(texto)

        # Validar que la categoría devuelta sea válida
        categorias_validas = set(CATEGORIA_WP.keys())
        cat_ia = resultado.get('categoria', '').strip().lower()
        if cat_ia not in categorias_validas:
            log(f"⚠️ IA devolvió categoría inválida '{cat_ia}' — usando sugerida '{categoria_sugerida}'", 'advertencia')
            resultado['categoria'] = categoria_sugerida if categoria_sugerida in categorias_validas else 'general'
        else:
            if cat_ia != categoria_sugerida:
                log(f"🧠 IA corrigió categoría: '{categoria_sugerida}' → '{cat_ia}'", 'info')

        # V17.7.0: Verificar originalidad básica — detectar scraping/paráfrasis superficial
        contenido_generado = resultado.get('contenido_html', '')
        similitud_con_fuente = similitud_contenido(contenido_generado, contenido[:3000], longitud=200)
        if similitud_con_fuente > 0.42:
            log(f"⚠️ Contenido generado demasiado similar al original (similitud={similitud_con_fuente:.2f}) — reintentando con instrucción reforzada", 'advertencia')
            # Reintento con instrucción anti-scraping explícita como sistema
            payload_retry = {
                "model": modelo,
                "messages": [
                    {"role": "system", "content": "Eres un editor periodístico experto. NUNCA copies ni parafrasees el texto fuente. Siempre escribe artículos completamente originales usando solo los datos como referencia, con análisis y perspectiva propios."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.55,
                "max_tokens": 3500
            }
            resp2 = requests.post(url_api, headers=headers, json=payload_retry, timeout=55)
            try:
                resp2_json = resp2.json()
                if "choices" in resp2_json:
                    texto2 = resp2_json["choices"][0]["message"]["content"].strip()
                    texto2 = re.sub(r'^```json\s*|```$', '', texto2, flags=re.MULTILINE).strip()
                    if texto2.endswith('}'):
                        resultado2 = json.loads(texto2)
                        sim2 = similitud_contenido(resultado2.get('contenido_html', ''), contenido[:3000], longitud=200)
                        if sim2 < similitud_con_fuente:
                            resultado = resultado2
                            cat2 = resultado.get('categoria', '').strip().lower()
                            if cat2 not in categorias_validas:
                                resultado['categoria'] = categoria_sugerida if categoria_sugerida in categorias_validas else 'general'
                            log(f"✅ Reintento originalidad exitoso (similitud={sim2:.2f})", 'info')
                        else:
                            log(f"⚠️ Reintento no mejoró originalidad — se usa de todos modos (similitud={sim2:.2f})", 'advertencia')
            except Exception as e2:
                log(f"⚠️ Reintento originalidad falló: {e2}", 'advertencia')
        else:
            log(f"✅ Originalidad OK (similitud fuente={similitud_con_fuente:.2f})", 'info')

        log(f"✅ IA SEO — Título: {resultado.get('titulo_seo','')[:55]} | Cat: {resultado.get('categoria')}", 'info')
        return resultado
    except Exception as e:
        log(f"⚠️ reescribir_noticia error: {e}", 'advertencia')
        return None


# ──────────────────────────────────────────────────────────
# ENLACES INTERNOS AUTOMÁTICOS
# ──────────────────────────────────────────────────────────
def obtener_articulos_wp_recientes(num=3):
    if not WP_APP_PASSWORD:
        return []
    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={'per_page': num + 1, 'status': 'publish',
                    'orderby': 'date', 'order': 'desc',
                    '_fields': 'id,title,link'},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10
        )
        if resp.status_code == 200:
            return resp.json()[:num]
    except Exception as e:
        log(f"⚠️ No se pudieron obtener artículos relacionados: {e}", 'debug')
    return []

def generar_seccion_relacionados(articulos):
    if not articulos:
        return ""
    items = ""
    for art in articulos:
        t = art.get('title', {}).get('rendered', '')
        l = art.get('link', '#')
        if t and l:
            items += f'<li><a href="{l}" style="color:#1a1a1a;text-decoration:none;">{t}</a></li>\n'
    if not items:
        return ""
    return (
        '\n<div class="vh-relacionadas" style="margin-top:24px;padding:16px;'
        'background:#f8f9fa;border-left:4px solid #cc0000;border-radius:4px;">\n'
        '<h3 style="margin:0 0 10px;font-size:1rem;color:#cc0000;">📰 Te puede interesar</h3>\n'
        f'<ul style="margin:0;padding-left:20px;">\n{items}</ul>\n</div>\n'
    )

def insertar_enlaces_internos(contenido_html):
    articulos = obtener_articulos_wp_recientes(2)
    html_relacionados = generar_seccion_relacionados(articulos)
    if "[ENLACES_INTERNOS]" in contenido_html:
        return contenido_html.replace("[ENLACES_INTERNOS]", html_relacionados)
    return contenido_html + html_relacionados


# ──────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────
def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default.copy()
        except Exception as e:
            log(f"Error cargando JSON {ruta}: {e}", 'error')
    return default.copy()

def guardar_json(ruta, datos):
    try:
        directorio = os.path.dirname(ruta)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON {ruta}: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto:
        return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url(url):
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)', '', parsed.netloc.lower())
        path   = parsed.path.lower().rstrip('/')
        path   = re.sub(r'/index\.(html|php|htm|asp)$', '', path)
        path   = re.sub(r'\.html?$', '', path)
        return f"{netloc}{path}"
    except:
        return url.lower().strip()

def extraer_dominio(url):
    try:
        parts = urlparse(url).netloc.lower().split('.')
        return '.'.join(parts[-2:]) if len(parts) > 2 else '.'.join(parts)
    except:
        return ""

def similitud_titulos(t1, t2):
    if not t1 or not t2:
        return 0.0
    stopwords = {'el','la','los','las','un','una','en','de','del','al','y','o',
                 'que','con','por','para','sobre','entre','the','of','and','to',
                 'in','is','a','an','it','as','at','by','from','not','or'}
    def normalizar(t):
        t = re.sub(r'[^\w\s]', '', t.lower().strip())
        t = re.sub(r'\s+', ' ', t)
        palabras = [p for p in t.split() if p not in stopwords and len(p) > 3]
        return ' '.join(palabras)
    return SequenceMatcher(None, normalizar(t1), normalizar(t2)).ratio()

def similitud_contenido(c1, c2, longitud=120):
    if not c1 or not c2:
        return 0.0
    def n(c):
        c = re.sub(r'[^\w\s]', '', c.lower().strip())
        return re.sub(r'\s+', ' ', c)[:longitud]
    return SequenceMatcher(None, n(c1), n(c2)).ratio()

def es_titulo_generico(titulo):
    if not titulo:
        return True
    tl = titulo.lower().strip()
    for patron in BLACKLIST_TITULOS:
        if re.match(patron, tl):
            return True
    stop = {'el','la','de','y','en','the','of','to','hoy','los','las'}
    palabras = [p for p in re.findall(r'\b\w+\b', tl) if p not in stop and len(p) > 3]
    return len(set(palabras)) < 4

_FUENTES_INCRUSTADAS = re.compile(
    r'\b(LISTIN DIARIO|Listín Diario|EL PAÍS|El País|BBC|CNN|Reuters|AFP|'
    r'AP News|Associated Press|INFOBAE|Infobae|EFE|France 24|'
    r'DW|Euronews|RT|Sputnik|Al Jazeera|The Guardian|'
    r'NYT|New York Times|Washington Post|Fox News|'
    r'ANSA|NHK|Deutsche Welle|RFI|Clarín|Clarin|'
    r'El Mundo|La Nación|La Nacion|Milenio|Univision|'
    r'Telemundo|La Vanguardia|El Confidencial|20minutos)\b[,.]?\s*',
    re.IGNORECASE
)

_FRASES_SUSCRIPCION = re.compile(
    r'(Recib[ií]\s+en\s+tu\s+mail[^.]*\.?|Suscr[ií]bete\s+[^.]*\.?'
    r'|Registrate\s+[^.]*\.?|Regístrate\s+[^.]*\.?|Newsletter\s+[^.]*\.?'
    r'|Descarga\s+la\s+app\s+[^.]*\.?|Síguenos\s+en\s+[^.]*\.?'
    r'|Leer\s+más[^.]*\.?|Ver\s+más[^.]*\.?|Lee\s+también[^.]*\.?'
    r'|Fuente:\s*[A-Z][^.]*\.?|Copyright\s+[^.]*\.?'
    r'|©[^.]*\.?)',
    re.IGNORECASE
)

def limpiar_texto(texto):
    if not texto:
        return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    t = _FUENTES_INCRUSTADAS.sub('', t)
    t = _FRASES_SUSCRIPCION.sub('', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if t and t[-1] not in '.!?':
        t += '.'
    return t.strip()

def calcular_puntaje(titulo, desc):
    titulo = titulo or ""
    desc   = desc or ""
    txt = f"{titulo} {desc}".lower()
    p = 0
    for frase in PALABRAS_ALTA_PRIORIDAD:
        if frase.lower() in txt:
            p += 7
        else:
            for palabra in frase.lower().split():
                if len(palabra) >= 4 and palabra in txt:
                    p += 3
                    break
    for frase in PALABRAS_MEDIA_PRIORIDAD:
        for palabra in frase.lower().split():
            if len(palabra) >= 3 and palabra in txt:
                p += 1
                break
    if 30 <= len(titulo) <= 150:
        p += 2
    if len(desc) >= 50:
        p += 2

    # ── V17.9.0: Bonus LATAM por NIVEL de país (reemplaza el bono plano V17.6) ──
    # Filosofía "editor jefe": no todos los países pesan igual. Chile es el
    # mercado principal de VerdadHoy, luego los países grandes de LATAM,
    # después el resto de Sudamérica, y un bono menor para Centroamérica/Caribe.
    # Reutiliza las mismas listas de KEYWORDS_CHILE / KEYWORDS_LATAM_PAISES que
    # ya usa el bloque exclusivo de Chile/LATAM, para no mantener dos fuentes
    # de verdad distintas.
    PAISES_TIER_1 = KEYWORDS_CHILE
    PAISES_TIER_2 = (KEYWORDS_LATAM_PAISES['mexico'] + KEYWORDS_LATAM_PAISES['brasil']
                      + KEYWORDS_LATAM_PAISES['argentina'])
    PAISES_TIER_3 = KEYWORDS_LATAM_PAISES['colombia'] + KEYWORDS_LATAM_PAISES['peru']
    PAISES_TIER_4 = (KEYWORDS_LATAM_PAISES['ecuador'] + KEYWORDS_LATAM_PAISES['bolivia']
                      + KEYWORDS_LATAM_PAISES['paraguay'] + KEYWORDS_LATAM_PAISES['uruguay']
                      + KEYWORDS_LATAM_PAISES['venezuela'])
    PAISES_TIER_5 = (KEYWORDS_LATAM_PAISES['panama'] + KEYWORDS_LATAM_PAISES['costa_rica']
                      + KEYWORDS_LATAM_PAISES['guatemala'] + KEYWORDS_LATAM_PAISES['el_salvador']
                      + KEYWORDS_LATAM_PAISES['honduras'] + KEYWORDS_LATAM_PAISES['nicaragua'])
    PAISES_TIER_6 = (KEYWORDS_LATAM_PAISES['rep_dom'] + KEYWORDS_LATAM_PAISES['cuba']
                      + KEYWORDS_LATAM_PAISES['puerto_rico'] + KEYWORDS_LATAM_PAISES['haiti']
                      + KEYWORDS_LATAM_PAISES['guyana'] + KEYWORDS_LATAM_PAISES['surinam']
                      + KEYWORDS_LATAM_PAISES['belice'])

    tiene_pais_latam = False
    if any(kw in txt for kw in PAISES_TIER_1):
        p += 14; tiene_pais_latam = True
    elif any(kw in txt for kw in PAISES_TIER_2):
        p += 12; tiene_pais_latam = True
    elif any(kw in txt for kw in PAISES_TIER_3):
        p += 11; tiene_pais_latam = True
    elif any(kw in txt for kw in PAISES_TIER_4):
        p += 9; tiene_pais_latam = True
    elif any(kw in txt for kw in PAISES_TIER_5):
        p += 7; tiene_pais_latam = True
    elif any(kw in txt for kw in PAISES_TIER_6):
        p += 6; tiene_pais_latam = True

    # Señal regional genérica: temas/líderes/recursos LATAM sin país explícito
    # en el texto (ej. "Copa Libertadores", "Boric", "litio") — bono menor,
    # se suma aparte del bono por país (pueden coexistir).
    señales_regionales_latam = [
        "latinoamerica", "america latina", "centroamerica", "sudamerica",
        "copa libertadores", "copa sudamericana", "conmebol", "eliminatorias",
        "boric", "milei", "lula", "sheinbaum", "petro", "maduro", "bukele",
        "litio", "cobre", "petroleo venezolano", "amazonia", "patagonia", "atacama",
    ]
    tiene_senal_regional = any(kw in txt for kw in señales_regionales_latam)
    if tiene_senal_regional:
        p += 5

    latam_hits = 1 if (tiene_pais_latam or tiene_senal_regional) else 0

    # ── V17.9.0: Bono editorial por TEMA prioritario (criterio "editor jefe") ──
    # Además del bono geográfico, algunos temas son prioritarios para la línea
    # editorial de VerdadHoy independientemente del país.
    temas_prioritarios_puntaje = {
        "economia":       ["economía", "economia", "inflación", "inflacion", "dólar", "dolar",
                            "mercados", "pib", "recesión", "recesion", "aranceles"],
        "tecnologia":     ["inteligencia artificial", "tecnología", "tecnologia", "startup",
                            "fintech", "ciberseguridad"],
        "politica":       ["elecciones", "presidente", "gobierno", "congreso", "senado"],
        "salud":          ["salud", "vacuna", "hospital", "oms", "enfermedad"],
        "medio_ambiente": ["amazonía", "amazonia", "cambio climático", "cambio climatico",
                            "glaciares", "medio ambiente"],
        "deportes":       ["fútbol", "futbol", "mundial", "libertadores", "eliminatorias"],
    }
    for kws in temas_prioritarios_puntaje.values():
        if any(kw in txt for kw in kws):
            p += 2
            break  # solo se suma una vez, no por cada tema que matchee

    # ── V17.6: Penalización noticias exclusivamente de EE.UU./Europa/Asia ──
    # Solo si NO tienen conexión con LATAM
    if latam_hits == 0:
        keywords_no_latam = [
            "washington dc", "white house", "congress usa", "senate usa",
            "wall street", "silicon valley", "pentagon", "kremlin",
            "bundestag", "westminster", "downing street",
        ]
        no_latam_hits = sum(1 for kw in keywords_no_latam if kw in txt)
        if no_latam_hits >= 1:
            p -= 4   # Penaliza noticias exclusivamente extranjeras sin impacto LATAM

        # ── V17.8.0: Penalización adicional — noticias domésticas de España ──
        # (política interna, sucesos y cultura local sin ninguna conexión LATAM)
        if es_noticia_espana_domestica(titulo, desc):
            p -= 6

    return p


# ──────────────────────────────────────────────────────────
# HISTORIAL ANTI-DUPLICADOS
# ──────────────────────────────────────────────────────────
HISTORIAL_DEFAULT = {
    'urls': [], 'urls_normalizadas': [], 'hashes': [], 'timestamps': [],
    'titulos': [], 'descripciones': [], 'hashes_contenido': [],
    'hashes_permanentes': [],
    'estadisticas': {'total_publicadas': 0, 'total_wp': 0, 'total_fb': 0, 'total_pinterest': 0}
}

def cargar_historial():
    h = cargar_json(HISTORIAL_PATH, HISTORIAL_DEFAULT)
    for k, v in HISTORIAL_DEFAULT.items():
        if k not in h:
            h[k] = v if not isinstance(v, dict) else v.copy()
    _limpiar_historial_antiguo(h)
    return h

def _limpiar_historial_antiguo(h):
    ahora = datetime.now()
    indices_validos = []
    for i, ts in enumerate(h.get('timestamps', [])):
        try:
            if (ahora - datetime.fromisoformat(ts)).days < DIAS_HISTORIAL:
                indices_validos.append(i)
        except:
            continue
    for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps',
                'titulos', 'descripciones', 'hashes_contenido']:
        if key in h and isinstance(h[key], list):
            h[key] = [h[key][i] for i in indices_validos if i < len(h[key])]
    if len(h.get('hashes_permanentes', [])) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]

def noticia_ya_publicada(h, url, titulo, desc=""):
    if es_titulo_generico(titulo):
        return True, "titulo_generico"
    url_n   = normalizar_url(url)
    hash_t  = generar_hash(titulo)
    hash_d  = generar_hash(desc) if desc else ""
    dominio = extraer_dominio(url)
    if url_n in h.get('urls_normalizadas', []):
        return True, "url_duplicada"
    todos_hashes = set(h.get('hashes', [])) | set(h.get('hashes_permanentes', []))
    if hash_t in todos_hashes:
        return True, "hash_titulo"
    if hash_d and hash_d in h.get('hashes_contenido', []):
        return True, "hash_contenido"
    for th in h.get('titulos', []):
        if not isinstance(th, str):
            continue
        if similitud_titulos(titulo, th) >= UMBRAL_SIMILITUD_TITULO:
            return True, f"titulo_similar"
    if desc:
        for dh in h.get('descripciones', []):
            if isinstance(dh, str) and dh:
                if similitud_contenido(desc, dh, 150) >= UMBRAL_SIMILITUD_CONTENIDO:
                    return True, "descripcion_similar"
    return False, "nuevo"

def guardar_en_historial(h, url, titulo, desc=""):
    url_n  = normalizar_url(url)
    hash_t = generar_hash(titulo)
    if url_n in h.get('urls_normalizadas', []):
        return h
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_n)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:600] if desc else "")
    h['hashes_contenido'].append(generar_hash(desc) if desc else "")
    h['hashes_permanentes'].append(hash_t)
    h['estadisticas']['total_publicadas'] = h['estadisticas'].get('total_publicadas', 0) + 1
    for k in ['urls', 'urls_normalizadas', 'hashes', 'timestamps',
              'titulos', 'descripciones', 'hashes_contenido']:
        if len(h[k]) > MAX_TITULOS_HISTORIA:
            h[k] = h[k][-MAX_TITULOS_HISTORIA:]
    if len(h['hashes_permanentes']) > 500:
        h['hashes_permanentes'] = h['hashes_permanentes'][-500:]
    guardar_json(HISTORIAL_PATH, h)
    return h


# ──────────────────────────────────────────────────────────
# CONTROL DE TIEMPO — WP y FB separados
# ──────────────────────────────────────────────────────────
def puede_publicar_wp():
    """
    V17.6.1: Logica de timing mejorada.
    PROBLEMA ANTERIOR: El JSON estado_wp.json se guardaba localmente pero el push
    a GitHub a veces tardaba o fallaba. La proxima ejecucion leia una hora antigua
    y creia que no habian pasado 30 min, no publicaba, ejecucion de 34-49s sin output.

    SOLUCION: Usar TIEMPO_ENTRE_WP_MIN=60 + margen de 5 min de tolerancia.
    Si el JSON dice que publico hace 55-60 min, publicar igual (JSON puede estar
    levemente desactualizado por el delay del push de GitHub Actions).

    ADICIONALMENTE: Verificar cuota diaria de WP aquí para no desperdiciar
    tiempo recolectando noticias si ya se alcanzó el límite del día.
    """
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True

    # Verificar cuota diaria primero — si ya publicamos MAX_POSTS_WP_DIA hoy, salir
    cuotas_hoy = cargar_cuotas_hoy()
    total_hoy = sum(int(v) for v in cuotas_hoy.get('conteo', {}).values())
    if total_hoy >= MAX_POSTS_WP_DIA:
        log(f"🚫 WP: cuota diaria alcanzada ({total_hoy}/{MAX_POSTS_WP_DIA})", 'advertencia')
        return False

    e = cargar_json(ESTADO_WP_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u:
        return True
    try:
        minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        # Margen de tolerancia por delay de push en GitHub Actions
        # V17.9.1: con TIEMPO_ENTRE_WP_MIN=230, un margen de 15 min es más
        # proporcional que el de 5 min que usaba con el intervalo de 60 min.
        margen = TIEMPO_ENTRE_WP_MIN - 15
        if minutos < margen:
            log(f"⏱️ WP: publicado hace {minutos:.0f} min — mínimo {margen} min (con margen)", 'info')
            return False
        log(f"✅ WP: {minutos:.0f} min desde última publicación — OK para publicar", 'info')
    except:
        pass
    return True

def puede_publicar_fb(h):
    """
    V17.6.1: ACLARACIÓN IMPORTANTE — FB y WP son flujos COMPLETAMENTE independientes.
    - WP: publica en cada ejecución donde hayan pasado ≥55 min desde la última pub.
           NO depende del horario pico. NO depende de si FB publicó o no.
    - FB: solo publica en horarios pico definidos, máx 4 veces/día,
           tomando noticias YA publicadas en verdadhoy.com (no genera contenido nuevo).
    El horario pico de FB NUNCA bloquea la publicación en WordPress.
    """
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True

    # Horario pico — SOLO aplica a Facebook, nunca a WordPress
    hora_utc = datetime.utcnow().hour
    en_pico  = any(inicio <= hora_utc < fin for inicio, fin in HORARIOS_PICO_UTC)
    if not en_pico:
        log(f"⏰ FB: fuera de horario pico (UTC {hora_utc:02d}h) — WP no se ve afectado", 'info')
        return False

    # Límite diario
    hoy = datetime.now().date()
    posts_hoy = sum(
        1 for ts in h.get('timestamps', [])
        if ts and datetime.fromisoformat(ts).date() == hoy
    )
    if posts_hoy >= MAX_POSTS_FB_DIA:
        log(f"🚫 FB: límite diario ({posts_hoy}/{MAX_POSTS_FB_DIA})", 'advertencia')
        return False

    # Tiempo mínimo entre posts
    e = cargar_json(ESTADO_FB_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if u:
        try:
            minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
            if minutos < TIEMPO_ENTRE_FB_MIN:
                log(f"⏱️ FB: publicado hace {minutos:.0f} min — mínimo {TIEMPO_ENTRE_FB_MIN} min", 'info')
                return False
        except:
            pass

    log(f"✅ FB: en horario pico, {posts_hoy}/{MAX_POSTS_FB_DIA} posts hoy", 'info')
    return True

def guardar_estado_wp():
    guardar_json(ESTADO_WP_PATH, {'ultima_publicacion': datetime.now().isoformat()})

def guardar_estado_fb():
    guardar_json(ESTADO_FB_PATH, {'ultima_publicacion': datetime.now().isoformat()})


# ──────────────────────────────────────────────────────────
# V12: OBTENER ARTÍCULO RECIENTE DE VERDADHOY.COM PARA FACEBOOK
# ──────────────────────────────────────────────────────────
def obtener_articulo_wp_para_facebook(h):
    """
    Obtiene el artículo más reciente de verdadhoy.com que:
    1. Tenga imagen destacada (featured_media > 0)
    2. No haya sido ya publicado en Facebook (verificado en historial con prefijo 'fb_')
    3. Sea de las últimas 24 horas

    Retorna dict con: titulo, link, excerpt, imagen_url | None si no hay
    """
    if not WP_APP_PASSWORD:
        log("⚠️ Sin WP_APP_PASSWORD — no se puede obtener artículo para FB", 'advertencia')
        return None

    try:
        # Obtener los últimos 20 artículos publicados con imagen
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={
                'per_page': 20,
                'status': 'publish',
                'orderby': 'date',
                'order': 'desc',
                '_fields': 'id,title,link,excerpt,featured_media,date',
            },
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=15
        )
        if resp.status_code != 200:
            log(f"⚠️ WP API error: {resp.status_code}", 'advertencia')
            return None

        articulos = resp.json()
        log(f"📋 Artículos WP disponibles: {len(articulos)}", 'info')

        # Hashes de URLs de FB ya publicados
        urls_fb_ya = set(h.get('urls_fb_publicadas', []))

        for art in articulos:
            # Verificar que tiene imagen
            if not art.get('featured_media') or art['featured_media'] == 0:
                log(f"   ❌ Sin imagen: {art.get('title', {}).get('rendered', '')[:40]}", 'debug')
                continue

            url_art  = art.get('link', '')
            titulo   = art.get('title', {}).get('rendered', '')
            art_id   = str(art.get('id', ''))

            # Verificar no publicado antes en FB
            if art_id in urls_fb_ya or url_art in urls_fb_ya:
                log(f"   ↩️ Ya publicado en FB: {titulo[:40]}", 'debug')
                continue

            # Obtener URL de imagen destacada
            media_id = art['featured_media']
            imagen_url = obtener_url_imagen_wp(media_id)
            if not imagen_url:
                log(f"   ❌ No se pudo obtener imagen para ID {media_id}", 'debug')
                continue

            # Limpiar excerpt
            excerpt_raw = art.get('excerpt', {}).get('rendered', '')
            excerpt = re.sub(r'<[^>]+>', '', excerpt_raw).strip()
            excerpt = re.sub(r'\s+', ' ', excerpt)[:280]

            log(f"✅ Artículo seleccionado para FB: {titulo[:55]}", 'exito')
            return {
                'id':         art_id,
                'titulo':     re.sub(r'<[^>]+>', '', titulo),
                'link':       url_art,
                'excerpt':    excerpt,
                'imagen_url': imagen_url,
            }

        log("⚠️ No se encontró artículo válido con imagen para publicar en FB", 'advertencia')
        return None

    except Exception as e:
        log(f"❌ Error obteniendo artículo WP para FB: {e}", 'error')
        return None


def obtener_url_imagen_wp(media_id):
    """Obtiene la URL de una imagen de la biblioteca de medios de WordPress."""
    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            params={'_fields': 'source_url,media_details'},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            # Intentar tamaño large primero, luego full
            sizes = data.get('media_details', {}).get('sizes', {})
            if sizes.get('large', {}).get('source_url'):
                return sizes['large']['source_url']
            if sizes.get('full', {}).get('source_url'):
                return sizes['full']['source_url']
            return data.get('source_url', '')
    except Exception as e:
        log(f"⚠️ Error obteniendo imagen media {media_id}: {e}", 'debug')
    return None


def registrar_fb_publicado(h, art_id, url):
    """Registra que un artículo ya fue publicado en Facebook."""
    if 'urls_fb_publicadas' not in h:
        h['urls_fb_publicadas'] = []
    if art_id not in h['urls_fb_publicadas']:
        h['urls_fb_publicadas'].append(art_id)
    if url not in h['urls_fb_publicadas']:
        h['urls_fb_publicadas'].append(url)
    # Mantener máximo 200 registros
    if len(h['urls_fb_publicadas']) > 200:
        h['urls_fb_publicadas'] = h['urls_fb_publicadas'][-200:]
    return h


# ──────────────────────────────────────────────────────────
# V12: PUBLICAR EN FACEBOOK — SOLO IMAGEN + TEXTO
# ──────────────────────────────────────────────────────────
def construir_texto_facebook(titulo, excerpt, url_wp, categoria='general'):
    """
    Construye el texto del post de Facebook.
    Formato: 📰 Titular | párrafo corto | separador | link | CTA | hashtags
    """
    # Limpiar título de HTML entities
    titulo_limpio = titulo.replace('&quot;', '"').replace('&#8220;', '"').replace('&#8221;', '"')
    titulo_limpio = titulo_limpio.replace('&#8216;', "'").replace('&#8217;', "'")
    titulo_limpio = re.sub(r'&[a-zA-Z]+;', '', titulo_limpio).strip()

    # Excerpt limpio, máx 200 chars
    excerpt_limpio = excerpt[:200].strip()
    if excerpt_limpio and excerpt_limpio[-1] not in '.!?':
        excerpt_limpio += '...'

    # URL con UTM
    url_utm = (f"{url_wp}?utm_source=facebook&utm_medium=social&utm_campaign=bot_noticias"
               if '?' not in url_wp else
               f"{url_wp}&utm_source=facebook&utm_medium=social&utm_campaign=bot_noticias")

    # CTA por categoría
    cta = random.choice(CTAS_POR_TEMA.get(categoria, CTAS_POR_TEMA['general']))

    # Hashtags por categoría
    hashtags_base = '#NoticiasInternacionales #ÚltimaHora #VerdadHoy'
    hashtags_extra = {
        'guerra':          '#ConflictoArmado #Guerra',
        'politica':        '#Política #PolíticaMundial',
        'economia':        '#Economía #EconomíaMundial',
        'tecnologia':      '#Tecnología #IA #Innovación',
        'desastre':        '#Desastre #EmergenciaMundial',
        'deportes':        '#Deportes #FútbolMundial',
        'ciencia':         '#Ciencia #Descubrimiento',
        'salud':           '#Salud #Medicina',
        'entretenimiento': '#Entretenimiento #Cultura',
        'latinoamerica':   '#Latinoamérica #AméricaLatina',
        'clima':           '#Clima #CambioClimático',
        'medio_ambiente':  '#MedioAmbiente #Planeta',
        'educacion':       '#Educación #Futuro',
        'mundo':           '#Mundo #GlobalNews',
        'general':         '#Mundo',
    }
    ht = f"{hashtags_base} {hashtags_extra.get(categoria, '#Mundo')}"

    lineas = [
        f"📰 {titulo_limpio}",
        "",
        excerpt_limpio,
        "",
        "─────────────────────────────",
        "",
        "🔗 Lee la noticia completa:",
        f"👉 {url_utm}",
        f"🌐 verdadhoy.com",
        "",
        cta,
        "",
        ht,
        "",
        "— Verdad Hoy | verdadhoy.com",
    ]
    return '\n'.join(lineas)


def descargar_imagen_para_fb(imagen_url):
    """Descarga imagen desde URL para publicar en Facebook."""
    if not imagen_url:
        return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(imagen_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200:
            return None
        data = r.content
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 200 or h < 150:
            return None
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        # Asegurar tamaño mínimo para Facebook (600x315 recomendado)
        if w < 600:
            ratio = 600 / w
            img = img.resize((600, int(h * ratio)), Image.LANCZOS)
        p = f'/tmp/fb_img_{generar_hash(imagen_url)}.jpg'
        img.save(p, 'JPEG', quality=90)
        if os.path.getsize(p) < 3000:
            os.remove(p)
            return None
        log(f"🖼️ Imagen FB descargada: {w}x{h}", 'debug')
        return p
    except Exception as e:
        log(f"⚠️ Error descargando imagen para FB: {e}", 'debug')
        return None


def publicar_facebook_imagen(titulo, texto, imagen_path):
    """
    Publica imagen + texto en la página de Facebook.
    V12.1 Fix: comprime imagen a máx 600px y 200KB antes de enviar.
    El error 'reduce amount of data' viene del tamaño del archivo, no del texto.
    """
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("⚠️ FB: sin credenciales", 'advertencia')
        return False
    if not imagen_path or not os.path.exists(imagen_path):
        log("❌ FB: sin imagen local para publicar", 'error')
        return False

    # Comprimir imagen para Facebook — máx 720px ancho, calidad 75
    imagen_fb_path = imagen_path
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(imagen_path).convert('RGB')
        # Redimensionar si es muy grande
        max_w = 720
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        # Guardar con calidad reducida
        imagen_fb_path = f"{imagen_path}_fb.jpg"
        img.save(imagen_fb_path, 'JPEG', quality=72, optimize=True)
        size_kb = os.path.getsize(imagen_fb_path) / 1024
        log(f"🗜️ Imagen FB comprimida: {img.width}x{img.height} — {size_kb:.0f}KB", 'debug')
    except Exception as e:
        log(f"⚠️ No se pudo comprimir imagen FB: {e} — usando original", 'debug')
        imagen_fb_path = imagen_path

    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_fb_path, 'rb') as f:
            r = requests.post(
                url,
                files={'source': ('imagen.jpg', f, 'image/jpeg')},
                data={'message': texto, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            ).json()

        # Limpiar imagen temporal comprimida
        try:
            if imagen_fb_path != imagen_path and os.path.exists(imagen_fb_path):
                os.remove(imagen_fb_path)
        except:
            pass

        if 'id' in r:
            log(f"✅ Imagen publicada en Facebook — ID: {r['id']}", 'exito')
            return True
        else:
            err = r.get('error', {}).get('message', 'desconocido')
            log(f"❌ Error Facebook: {err}", 'error')
            return False
    except Exception as e:
        log(f"❌ Excepción publicando en Facebook: {e}", 'error')
        return False


# ──────────────────────────────────────────────────────────
# WORDPRESS — PUBLICACIÓN
# ──────────────────────────────────────────────────────────
def obtener_id_categoria_wp(slug_categoria):
    global _cache_categorias_wp
    if slug_categoria in _cache_categorias_wp:
        return _cache_categorias_wp[slug_categoria]
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories",
            params={'slug': slug_categoria, 'per_page': 1},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=15
        ).json()
        if r and isinstance(r, list) and len(r) > 0:
            cat_id = r[0]['id']
            _cache_categorias_wp[slug_categoria] = cat_id
            log(f"📂 Categoría WP '{slug_categoria}' → ID {cat_id}", 'info')
            return cat_id
    except Exception as e:
        log(f"⚠️ Error obteniendo categoría '{slug_categoria}': {e}", 'advertencia')
    return None

def obtener_crear_tag_wp(nombre_tag):
    global _cache_tags_wp
    tag_clean = nombre_tag.lower().strip()
    if not tag_clean or len(tag_clean) < 2:
        return None
    if tag_clean in _cache_tags_wp:
        return _cache_tags_wp[tag_clean]
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/tags",
            params={'search': tag_clean, 'per_page': 5},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10
        ).json()
        if r and isinstance(r, list):
            for tag in r:
                if tag.get('name', '').lower() == tag_clean:
                    _cache_tags_wp[tag_clean] = tag['id']
                    return tag['id']
        r_post = requests.post(
            f"{WP_URL}/wp-json/wp/v2/tags",
            json={'name': nombre_tag.strip()},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10
        ).json()
        if 'id' in r_post:
            _cache_tags_wp[tag_clean] = r_post['id']
            return r_post['id']
    except Exception as e:
        log(f"⚠️ Error gestionando tag '{nombre_tag}': {e}", 'debug')
    return None

def subir_imagen_wp(imagen_path, titulo, alt_text="", frase_clave="", meta_descripcion=""):
    """
    Sube imagen a WordPress y asigna los 4 campos de metadatos que antes se
    completaban a mano en cada artículo (texto alternativo, título, leyenda
    y descripción) — mismo criterio que se usaba en la revisión manual:
      - Texto alternativo: descriptivo del contenido de la foto (ya existía)
      - Título: frase clave / tema del artículo
      - Leyenda: contexto breve + "Fuente: Verdad Hoy" (siempre visible bajo
        la imagen en el front-end, ayuda a SEO de imágenes y a E-E-A-T)
      - Descripción: metadata interna más completa (no visible al público,
        pero indexable por buscadores de imágenes)
    """
    if not imagen_path or not os.path.exists(imagen_path):
        return None
    try:
        nombre_archivo = f"noticia-{generar_hash(titulo)}.jpg"
        with open(imagen_path, 'rb') as f:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media",
                headers={
                    'Content-Disposition': f'attachment; filename="{nombre_archivo}"',
                    'Content-Type': 'image/jpeg',
                },
                data=f.read(),
                auth=(WP_USER, WP_APP_PASSWORD), timeout=60
            ).json()
        if 'id' in r:
            media_id = r['id']
            log(f"🖼️ Imagen subida a WP — ID: {media_id}", 'exito')

            titulo_media = (frase_clave or titulo)[:100]
            leyenda_media = f"{titulo[:150]} — Fuente: Verdad Hoy"
            descripcion_media = (
                f"{titulo}. {meta_descripcion}".strip()[:300]
                if meta_descripcion else titulo[:300]
            )
            metadatos = {
                'title': titulo_media,
                'caption': leyenda_media,
                'description': descripcion_media,
            }
            if alt_text:
                metadatos['alt_text'] = alt_text[:125]
            try:
                requests.post(
                    f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                    json=metadatos,
                    auth=(WP_USER, WP_APP_PASSWORD), timeout=10
                )
            except Exception as e:
                log(f"⚠️ No se pudieron guardar metadatos completos de imagen: {e}", 'debug')
            return media_id
        else:
            log(f"⚠️ Error subiendo imagen: {r.get('message', 'desconocido')}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Excepción subiendo imagen: {e}", 'advertencia')
    return None

def publicar_en_wordpress(titulo, contenido, tema, imagen_path, fuente_url, fecha_fuente=None, fuente_noticia=None):
    """Publica artículo en WordPress. Imagen OBLIGATORIA."""
    if not WP_APP_PASSWORD:
        log("⚠️ WP_APP_PASSWORD no configurado", 'advertencia')
        return None
    if not imagen_path or not os.path.exists(imagen_path):
        log("❌ Sin imagen — no se publica en WordPress", 'error')
        return None

    # Nombre del medio fuente
    def extraer_nombre_medio(url):
        try:
            dominio = urlparse(url).netloc.lower()
            dominio = re.sub(r'^(www\.|m\.)', '', dominio)
            mapa = {
                'elpais.com': 'El País', 'bbc.com': 'BBC Mundo',
                'cnn.com': 'CNN en Español', 'infobae.com': 'Infobae',
                'reuters.com': 'Reuters', 'france24.com': 'France 24',
                'efe.com': 'EFE', 'dw.com': 'Deutsche Welle',
                'euronews.com': 'Euronews', 'theguardian.com': 'The Guardian',
            }
            for dom, nombre in mapa.items():
                if dom in dominio:
                    return nombre
            partes = dominio.split('.')
            return partes[-2].capitalize() if len(partes) >= 2 else dominio
        except:
            return 'Fuente externa'

    nombre_medio = extraer_nombre_medio(fuente_url)

    # IA reescritura SEO
    resultado_ia = reescribir_noticia_v9(titulo, contenido, tema)
    alt_text_imagen = titulo[:125]
    tags_ids = []

    # V17.6.6: Generar box resumen aquí — se usa tanto en resultado IA como en fallback
    # Rotación aleatoria del título del box
    _TITULOS_BOX = [
        ('⚡', 'Lo que debes saber'),
        ('📌', 'Lo esencial'),
        ('🔑', 'Puntos clave'),
        ('📋', 'Resumen rápido'),
    ]
    _emoji_b, _texto_b = random.choice(_TITULOS_BOX)
    _titulo_box = f"{_emoji_b} {_texto_b}"

    def _generar_box_fallback(titulo_art, contenido_art):
        """
        V17.6.6b: Genera box resumen cuando la IA lo omite.
        Usa oraciones COMPLETAS — nunca corta a mitad de una idea.
        Si la oración es muy larga (+180 chars), la divide en el punto
        más cercano a la mitad para mantener sentido completo.
        """
        # Limpiar HTML del contenido antes de extraer oraciones
        texto_limpio = re.sub(r'<[^>]+>', ' ', contenido_art)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto_limpio)
                     if len(o.strip()) > 40 and not o.strip().startswith('<')]
        puntos = []
        for o in oraciones[:10]:
            # Saltar oraciones que son frases de fuente/crédito
            if any(skip in o.lower() for skip in ['verdad hoy', 'fuente:', 'información verificada']):
                continue
            # Oración corta/media — usar completa
            if len(o) <= 160:
                punto = o if o.endswith(('.','!','?')) else o + '.'
            else:
                # Oración larga — buscar el primer punto, coma o "que" cercano a los 140 chars
                corte = o[:160]
                # Intentar cortar en punto y coma, coma, o "que"
                for sep in ['. ', ', ', ' que ', ' y ', ' con ']:
                    idx = corte.rfind(sep)
                    if idx > 80:
                        punto = corte[:idx + len(sep)].strip()
                        if not punto.endswith(('.','!','?')):
                            punto += '...'
                        break
                else:
                    # No encontró buen punto de corte — usar primeras 130 chars en palabra completa
                    punto = corte.rsplit(' ', 1)[0] + '...'
            puntos.append(punto)
            if len(puntos) == 4:
                break
        # Garantizar mínimo 3 puntos
        while len(puntos) < 3:
            puntos.append(f'Noticia: {titulo_art[:100]}.')
        items_html = '\n'.join(
            f'<li style="margin-bottom:6px;">{p}</li>' for p in puntos
        )
        return (
            f'<div style="background:#f0f4ff;border-left:4px solid #1a56db;'
            f'padding:16px 20px;margin:0 0 24px 0;border-radius:0 8px 8px 0;">'
            f'<p style="margin:0 0 8px 0;font-weight:700;color:#1a56db;font-size:0.95em;">{_titulo_box}</p>'
            f'<ul style="margin:0;padding-left:20px;color:#374151;">'
            f'{items_html}'
            f'</ul></div>'
        )

    if resultado_ia:
        titulo_final         = resultado_ia.get('titulo_seo', titulo)[:60] or titulo
        meta_desc            = resultado_ia.get('meta_descripcion', '')
        frase_clave          = resultado_ia.get('keyword_principal', '')
        contenido_formateado = resultado_ia.get('contenido_html', '')

        # V17.6.6 FIX CRÍTICO: Verificar que el box esté presente en el HTML de la IA
        # La IA a veces lo omite aunque el prompt lo pida — lo inyectamos si falta
        _tiene_box = ('background:#f0f4ff' in contenido_formateado or
                      'En 30 segundos' in contenido_formateado or
                      'Lo esencial' in contenido_formateado or
                      'Puntos clave' in contenido_formateado or
                      'Resumen r' in contenido_formateado or
                      'Lo que debes saber' in contenido_formateado)
        if not _tiene_box:
            log("⚠️ IA omitió el box resumen — inyectando automáticamente", 'advertencia')
            box_inject = _generar_box_fallback(titulo_final, contenido_formateado)
            contenido_formateado = box_inject + contenido_formateado

        contenido_formateado = insertar_enlaces_internos(contenido_formateado)
        if frase_clave:
            alt_text_imagen = f"{frase_clave} - {titulo_final}"[:125]
        for kw in resultado_ia.get('keywords_secundarias', [])[:5]:
            tag_id = obtener_crear_tag_wp(kw)
            if tag_id:
                tags_ids.append(tag_id)
    else:
        # V17.9.3 FIX CRÍTICO: se elimina el fallback "sin IA".
        # PROBLEMA DETECTADO: cuando reescribir_noticia_v9() fallaba (créditos
        # agotados, rate limit, error de API, JSON cortado), el bot publicaba
        # el contenido crudo de la fuente casi sin tocar: mismas 2-3 oraciones
        # repetidas en el box resumen Y en el cuerpo del artículo, sin H2, sin
        # desarrollo, sin ningún valor editorial. Eso es exactamente el tipo
        # de "contenido de bajo valor" que AdSense ya penalizó una vez.
        # SOLUCIÓN: si la IA no responde, esta noticia se descarta (return None)
        # y el llamador (main() o publicar_bloque_latam_chile()) prueba con la
        # siguiente candidata de la lista, en vez de publicar algo pobre.
        # Prioridad: publicar MENOS artículos pero todos con la calidad del
        # Editor Jefe > publicar más artículos rellenando con contenido crudo.
        log("❌ IA no disponible para esta noticia — se descarta (NO se publica sin IA)", 'error')
        return None

    # Bloque histórico (deshabilitado desde V17.9.3, se deja comentado como
    # referencia de por qué NO se debe reactivar sin más validación):
    #     titulo_final = titulo
    #     texto_limpio = contenido[:4000].strip()
    #     oraciones = [...]
    #     if len(oraciones) < 3: return None
    #     ... agrupaba oraciones en párrafos y las publicaba tal cual ...
    # Este bloque permitía que una noticia con solo 3 oraciones cortas
    # (el mínimo que exigía) se publicara completa sin ningún desarrollo.

    # Schema JSON-LD — V14.1: campos completos para Rich Results y Google Discover
    fecha_schema = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')
    if fecha_fuente:
        try:
            fecha_str = str(fecha_fuente).replace('Z', '+00:00')
            datetime.fromisoformat(fecha_str)
            fecha_schema = fecha_str if '+' in fecha_str or fecha_str.endswith('Z') else fecha_str + '+00:00'
        except:
            fecha_schema = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')

    fecha_modified = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')
    titulo_schema  = titulo_final.replace('"', "'").replace('\\', '')
    meta_schema    = (meta_desc or contenido[:155]).replace('"', "'").replace('\\\\', '')

    # V14.1: URL de imagen — se actualiza con URL real tras subir a WP
    # FIX LOGO: placeholder ÚNICO y distinto al del logo del publisher.
    # Antes, imagen_schema_url y publisher.logo.url eran el MISMO string
    # ("{WP_URL}/wp-content/uploads/favicon_512.png"), así que el .replace()
    # de más abajo (que solo debía actualizar la imagen del artículo con la
    # URL real subida a WP) también sobrescribía el logo del publisher con
    # la foto de la noticia — bug confirmado en los artículos de Colombia y
    # de conexión satelital, donde el "logo" del schema terminó siendo la
    # imagen destacada del artículo en vez del logo fijo de Verdad Hoy.
    imagen_schema_url  = "__PLACEHOLDER_IMAGEN_ARTICULO__"  # marcador único, nunca choca con el logo
    imagen_schema_w    = 1200
    imagen_schema_h    = 630
    LOGO_URL_FIJO      = f"{WP_URL}/wp-content/uploads/favicon_512.png"  # logo real del sitio, nunca se reemplaza

    schema_markup = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "{titulo_schema}",
  "datePublished": "{fecha_schema}",
  "dateModified": "{fecha_modified}",
  "description": "{meta_schema}",
  "inLanguage": "es",
  "isAccessibleForFree": "True",
  "image": {{
    "@type": "ImageObject",
    "url": "{imagen_schema_url}",
    "width": {imagen_schema_w},
    "height": {imagen_schema_h}
  }},
  "author": {{
    "@type": "Organization",
    "name": "Verdad Hoy",
    "url": "{WP_URL}"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "Verdad Hoy",
    "url": "{WP_URL}",
    "logo": {{
      "@type": "ImageObject",
      "url": "{LOGO_URL_FIJO}",
      "width": 512,
      "height": 512
    }}
  }},
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "{WP_URL}/"
  }}
}}
</script>"""

    # contenido_html se construye después de subir la imagen (para incluir URL real en schema)

    # SEO
    stopwords_es = {'para','como','este','esta','esto','pero','porque','cuando','donde',
                    'quien','ante','bajo','cada','con','contra','desde','durante','entre',
                    'hacia','hasta','por','según','tras','una','uno','los','las','del',
                    'que','sus','más','sin','sobre','también','hay','han','sido'}
    if not frase_clave:
        palabras_clave = [p for p in re.findall(r'\b\w{4,}\b', titulo_final.lower())
                          if p not in stopwords_es]
        frase_clave = ' '.join(palabras_clave[:4])

    sufijo_seo  = ' | Verdad Hoy'
    max_titulo  = 60 - len(sufijo_seo)
    if resultado_ia and resultado_ia.get('titulo_seo'):
        titulo_seo = resultado_ia['titulo_seo']
        if ' | Verdad Hoy' not in titulo_seo:
            titulo_seo = (titulo_seo[:max_titulo].rsplit(' ', 1)[0]
                          if len(titulo_seo) > max_titulo else titulo_seo) + sufijo_seo
    else:
        titulo_seo = (titulo_final[:max_titulo].rsplit(' ', 1)[0]
                      if len(titulo_final) > max_titulo else titulo_final) + sufijo_seo

    if not meta_desc:
        primera_oracion = re.split(r'(?<=[.!?])\s+', ' '.join(contenido.split()))[0]
        if len(primera_oracion) > 155:
            meta_desc = primera_oracion[:152].rsplit(' ', 1)[0] + '...'
        elif len(primera_oracion) < 50:
            meta_desc = (' '.join(contenido.split()))[:152].rsplit(' ', 1)[0] + '...'
        else:
            meta_desc = primera_oracion

    # Fecha de publicación desde fuente
    fecha_wp = None
    if fecha_fuente:
        try:
            fecha_str = str(fecha_fuente).replace('Z', '+00:00')
            dt = datetime.fromisoformat(fecha_str)
            fecha_wp = dt.strftime('%Y-%m-%dT%H:%M:%S')
        except:
            fecha_wp = None

    # Subir imagen (con metadatos completos: título, leyenda y descripción)
    imagen_id = subir_imagen_wp(
        imagen_path, titulo, alt_text=alt_text_imagen,
        frase_clave=frase_clave, meta_descripcion=meta_desc,
    )
    if not imagen_id:
        log("❌ No se pudo subir imagen — cancelando WP", 'error')
        return None

    # V14.1: Obtener URL real de imagen subida — actualiza schema con datos reales
    try:
        r_media = requests.get(
            f"{WP_URL}/wp-json/wp/v2/media/{imagen_id}",
            params={"_fields": "source_url,media_details"},
            auth=(WP_USER, WP_APP_PASSWORD), timeout=10
        ).json()
        sizes = r_media.get("media_details", {}).get("sizes", {})
        url_img_real = (sizes.get("large", {}).get("source_url") or
                        sizes.get("full", {}).get("source_url") or
                        r_media.get("source_url", imagen_schema_url))
        img_w_real = sizes.get("large", {}).get("width", imagen_schema_w)
        img_h_real = sizes.get("large", {}).get("height", imagen_schema_h)
        # Reemplazar placeholder con URL e dimensiones reales
        schema_markup = schema_markup.replace(
            imagen_schema_url, url_img_real
        ).replace(
            f'"width": {imagen_schema_w},', f'"width": {img_w_real},'
        ).replace(
            f'"height": {imagen_schema_h}', f'"height": {img_h_real}'
        )
        log(f"Schema imagen actualizada: {img_w_real}x{img_h_real}", "debug")
    except Exception as e:
        log(f"No se pudo obtener URL real de imagen: {e}", "debug")

    # V17.6.3: Calcular tiempo de lectura para mostrar en el artículo
    palabras_articulo = len(re.sub(r'<[^>]+>', '', contenido_formateado).split())
    minutos_lectura = max(2, round(palabras_articulo / 200))
    barra_lectura = f"""<p style="font-size:0.82em;color:#6b7280;margin:0 0 20px 0;display:flex;align-items:center;gap:6px;">
<span>🕐</span> <span>Tiempo de lectura: <strong>{minutos_lectura} min</strong></span>
</p>"""

    # Reconstruir contenido_html con schema actualizado
    contenido_html = f"""
{barra_lectura}
{contenido_formateado}

<hr>
<p><strong>Fuente:</strong> {nombre_medio}</p>
<p><em>Información verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
{schema_markup}
"""

    # V16: Usar categoría determinada por IA — tiene prioridad sobre el tema sugerido
    categoria_final = resultado_ia.get('categoria', tema) if resultado_ia else tema
    # Validar que sea una categoría conocida
    if categoria_final not in CATEGORIA_WP:
        log(f"⚠️ Categoría '{categoria_final}' inválida — usando '{tema}'", 'advertencia')
        categoria_final = tema if tema in CATEGORIA_WP else 'general'

    # V17.9.8: "desastre", "guerra", "crimen", "religion", "educacion",
    # "general" y "mundo" son categorías temáticas "paraguas" que antes
    # SIEMPRE caían en el slug plano 'internacional'. Ahora:
    #   1) si la noticia es de un país LATAM → categoría principal
    #      "Latinoamérica" (con "Internacional" como secundaria, V17.9.7)
    #   2) si no, se detecta la región real (Europa/Asia/África/América del
    #      Norte/Medio Oriente/Oceanía) y esa pasa a ser la categoría
    #      principal (con "Internacional" como secundaria); si no hay región
    #      específica clara, cae en "Mundo".
    CATEGORIAS_INTERNACIONAL_PARAGUAS = {'desastre', 'guerra', 'crimen', 'religion', 'educacion', 'general', 'mundo'}
    slug_cat_secundario = None
    if categoria_final in CATEGORIAS_INTERNACIONAL_PARAGUAS:
        _categoria_original = categoria_final
        _texto_chk = f"{titulo} {contenido_html}".lower()
        _es_latam = (
            any(kw in _texto_chk for kw in KEYWORDS_CHILE) or
            any(kw in _texto_chk for _kws in KEYWORDS_LATAM_PAISES.values() for kw in _kws)
        )
        if _es_latam:
            slug_cat = CATEGORIA_WP['latinoamerica']
            slug_cat_secundario = 'internacional'
            log(f"   🌎 Reasignado a 'Latinoamérica' (era '{_categoria_original}', país LATAM detectado)", 'info')
        else:
            _region = detectar_region_internacional(titulo, contenido_html)
            slug_cat = REGION_SLUG_WP.get(_region, 'internacional')
            slug_cat_secundario = 'internacional' if slug_cat != 'internacional' else None
            log(f"   🌍 Región '{_region}' → categoría '{slug_cat}' (era '{_categoria_original}')", 'info')
    else:
        slug_cat = CATEGORIA_WP.get(categoria_final, 'internacional')

    cat_id = obtener_id_categoria_wp(slug_cat)
    if not cat_id and slug_cat != 'internacional':
        # V17.9.8: si el slug de la subcategoría no existe en WordPress (el
        # slug real no coincide con REGION_SLUG_WP), no dejar el artículo
        # sin categoría — usar 'internacional' como red de seguridad.
        log(f"⚠️ Categoría WP '{slug_cat}' no encontrada — usando 'internacional' de respaldo. "
            f"Verifica el slug real de esa categoría y avísame para corregir REGION_SLUG_WP.", 'advertencia')
        cat_id = obtener_id_categoria_wp('internacional')
        slug_cat_secundario = None  # ya es internacional, no duplicar
    categorias = [cat_id] if cat_id else []
    if slug_cat_secundario:
        cat_id_sec = obtener_id_categoria_wp(slug_cat_secundario)
        if cat_id_sec and cat_id_sec not in categorias:
            categorias.append(cat_id_sec)

    post_data = {
        'title':          titulo_final,
        'content':        contenido_html,
        'excerpt':        meta_desc,
        'status':         'publish',
        'featured_media': imagen_id,
        'categories':     categorias,
        'tags':           tags_ids,
        'meta': {
            '_yoast_wpseo_title':    titulo_seo,
            '_yoast_wpseo_metadesc': meta_desc,
            '_yoast_wpseo_focuskw':  frase_clave,
        }
    }
    if fecha_wp:
        post_data['date'] = fecha_wp

    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD), timeout=30
        ).json()

        if 'id' in r:
            url_articulo = r.get('link', f"{WP_URL}/?p={r['id']}")
            log(f"✅ Publicado en WordPress: {url_articulo}", 'exito')
            return url_articulo
        else:
            log(f"❌ Error WP: {r.get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción WP: {e}", 'error')
    return None


# ──────────────────────────────────────────────────────────
# PINTEREST
# ──────────────────────────────────────────────────────────
def obtener_tableros_pinterest():
    global _cache_tableros_pinterest
    if _cache_tableros_pinterest:
        return _cache_tableros_pinterest
    if not PINTEREST_TOKEN:
        return {}
    try:
        resp = requests.get(
            'https://api.pinterest.com/v5/boards',
            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}'},
            timeout=15
        )
        if resp.status_code == 200:
            for board in resp.json().get('items', []):
                _cache_tableros_pinterest[board['name']] = board['id']
            log(f"📌 Tableros Pinterest: {list(_cache_tableros_pinterest.keys())}", 'info')
        else:
            log(f"⚠️ Pinterest boards error: {resp.status_code} — {resp.text[:100]}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Pinterest excepción: {e}", 'advertencia')
    return _cache_tableros_pinterest

def publicar_pinterest(titulo, descripcion, url_articulo, img_path, categoria):
    """Publica un Pin en el tablero correspondiente."""
    if not PINTEREST_TOKEN:
        log("⚠️ Pinterest: sin token", 'advertencia')
        return False
    if not img_path or not os.path.exists(img_path):
        log("⚠️ Pinterest: sin imagen", 'advertencia')
        return False
    try:
        tableros       = obtener_tableros_pinterest()
        nombre_tablero = TABLEROS_PINTEREST.get(categoria, 'Noticias del Mundo')
        board_id       = tableros.get(nombre_tablero)
        if not board_id:
            board_id = tableros.get('Noticias del Mundo') or (list(tableros.values())[0] if tableros else None)
        if not board_id:
            log("⚠️ Pinterest: no se encontró tablero", 'advertencia')
            return False

        url_utm = f"{url_articulo}?utm_source=pinterest&utm_medium=social&utm_campaign=bot_noticias"

        # Subir imagen
        with open(img_path, 'rb') as f:
            resp_img = requests.post(
                'https://api.pinterest.com/v5/media',
                headers={'Authorization': f'Bearer {PINTEREST_TOKEN}'},
                files={'file': ('image.jpg', f, 'image/jpeg')},
                timeout=30
            )
        media_id = None
        if resp_img.status_code in (200, 201):
            media_id = resp_img.json().get('media_id')

        desc_limpia = descripcion[:490] if descripcion else titulo
        payload = {
            'board_id':    board_id,
            'title':       titulo[:100],
            'description': desc_limpia,
            'link':        url_utm,
        }
        if media_id:
            payload['media_source'] = {'source_type': 'media_id', 'media_id': media_id}
        else:
            payload['media_source'] = {'source_type': 'image_url', 'url': url_articulo}

        resp_pin = requests.post(
            'https://api.pinterest.com/v5/pins',
            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}', 'Content-Type': 'application/json'},
            json=payload, timeout=20
        )
        if resp_pin.status_code in (200, 201):
            pin_id = resp_pin.json().get('id', '')
            log(f"✅ Pinterest OK: pin {pin_id} en '{nombre_tablero}'", 'exito')
            return True
        else:
            log(f"❌ Pinterest error {resp_pin.status_code}: {resp_pin.text[:200]}", 'error')
            return False
    except Exception as e:
        log(f"❌ Pinterest excepción: {e}", 'error')
        return False


# ══════════════════════════════════════════════════════════
# V17.3 — FUENTES LATAM + CHILE
# ══════════════════════════════════════════════════════════

# ── Keywords para detectar noticias de Chile ──────────────
KEYWORDS_CHILE = [
    # Geografía
    "chile", "chilena", "chileno", "chilenas", "chilenos",
    "santiago", "valparaíso", "valparaiso", "concepción", "concepcion",
    "antofagasta", "temuco", "viña del mar", "vina del mar",
    "la serena", "rancagua", "talca", "arica", "iquique", "puerto montt",
    # Instituciones/Política chile
    "gabriel boric", "boric", "gobierno de chile", "congreso chileno",
    "senado chileno", "cámara de diputados chile", "camara de diputados chile",
    "carabineros", "pdi chile", "ministerio de chile",
    "banco central de chile", "peso chileno", "peso cl",
    "conaf", "codelco", "enap chile", "transantiago", "metro de santiago",
    "sernac", "sernapesca", "sii chile", "servicio de impuestos internos",
    "comisión para el mercado financiero", "cmf chile",
    # Economía/Empresas chile
    "bolsa de santiago", "ipsa", "uf chilena", "utm chile",
    "falabella", "cencosud", "lider cl", "jumbo chile",
    "latam airlines chile", "sky airline",
    # Cultura/Sociedad chile
    "festival de viña", "festival de viña del mar",
    "selección chilena", "la roja", "la roja chilena",
    "colo colo", "universidad de chile", "universidad católica",
    "huaso", "mapuche", "araucanía", "la araucania",
]

# ── Keywords para detectar noticias de LATAM (sin Chile) ──
KEYWORDS_LATAM_PAISES = {
    'mexico':     ["méxico", "mexico", "mexicano", "mexicana", "cdmx", "ciudad de mexico",
                   "sheinbaum", "pemex", "guadalajara", "monterrey", "puebla"],
    'argentina':  ["argentina", "argentino", "argentina", "buenos aires", "milei",
                   "merval", "peso argentino", "rosario ar", "córdoba ar"],
    'colombia':   ["colombia", "colombiano", "bogotá", "bogota", "petro", "medellín",
                   "medellin", "cali colombia", "cartagena colombia", "barranquilla"],
    'brasil':     ["brasil", "brazil", "brasileño", "lula", "sao paulo", "río de janeiro",
                   "rio de janeiro", "brasilia", "real brasileiro"],
    'venezuela':  ["venezuela", "venezolano", "maduro", "caracas", "bolívar venezolano",
                   "maracaibo"],
    'peru':       ["perú", "peru", "peruano", "lima perú", "lima peru", "boluarte",
                   "arequipa", "cusco"],
    'ecuador':    ["ecuador", "ecuatoriano", "quito", "noboa", "guayaquil"],
    'bolivia':    ["bolivia", "boliviano", "la paz bolivia", "arce bolivia",
                   "santa cruz de la sierra"],
    'uruguay':    ["uruguay", "uruguayo", "montevideo", "orsi"],
    'paraguay':   ["paraguay", "paraguayo", "asunción", "asuncion"],
    'cuba':       ["cuba", "cubano", "la habana", "havana cuba"],
    'nicaragua':  ["nicaragua", "nicaragüense", "ortega nicaragua", "managua"],
    'guatemala':  ["guatemala", "guatemalteco", "ciudad de guatemala", "giammattei"],
    'honduras':   ["honduras", "hondureño", "tegucigalpa", "castro honduras"],
    'el_salvador':["el salvador", "salvadoreño", "bukele", "san salvador"],
    'panama':     ["panamá", "panama", "panameño", "ciudad de panamá"],
    'costa_rica': ["costa rica", "costarricense", "san josé cr", "chaves costa rica"],
    'rep_dom':    ["república dominicana", "dominicano", "santo domingo"],
    'haiti':      ["haití", "haiti", "haitiano", "puerto príncipe"],
    'puerto_rico':["puerto rico", "puertorriqueño", "san juan pr"],
    'guyana':     ["guyana", "guyanés", "georgetown guyana"],
    'surinam':    ["surinam", "surinamés", "paramaribo"],
    'belice':     ["belice", "beliceño", "belmopán"],
}

# ── V17.9.8/9.9: Subcategorías reales de "Internacional" en el menú ──────
# El menú de verdadhoy.com tiene: Europa, Asia, África, Medio Oriente,
# Oceanía, Latinoamérica, Mundo (todas hijas de "Internacional"). Antes,
# TODO lo que no era LATAM caía en el mismo cajón "internacional" sin
# distinguir región. Estas listas permiten repartir correctamente.
# ("América del Norte" existió como región hasta V17.9.8 — se eliminó en
# V17.9.9 por bajo volumen; ver nota más abajo.)
KEYWORDS_REGIONES = {
    'europa': [
        "españa", "espana", "francia", "alemania", "italia", "reino unido",
        "inglaterra", "escocia", "gales", "irlanda", "portugal", "países bajos",
        "paises bajos", "holanda", "bélgica", "belgica", "suiza", "austria",
        "polonia", "ucrania", "rusia", "kremlin", "rumania", "hungría", "hungria",
        "grecia", "suecia", "noruega", "dinamarca", "finlandia", "chequia",
        "república checa", "republica checa", "croacia", "serbia", "bulgaria",
        "bielorrusia", "moldavia", "bruselas", "unión europea", "union europea",
        " ue ", "otan", "vaticano", "madrid", "parís", "paris", "berlín", "berlin",
        "londres", "roma milán", "putin", "zelenski", "sánchez españa",
    ],
    'asia': [
        "china", "japón", "japon", "corea del sur", "corea del norte", "india",
        "pakistán", "pakistan", "bangladés", "bangladesh", "indonesia",
        "filipinas", "vietnam", "tailandia", "malasia", "singapur", "taiwán",
        "taiwan", "mongolia", "kazajistán", "kazajistan", "pekín", "pekin",
        "beijing", "tokio", "seúl", "seul", "nueva delhi", "shanghái", "shanghai",
        "xi jinping", "kim jong",
    ],
    'africa': [
        "nigeria", "sudáfrica", "sudafrica", "egipto", "kenia", "etiopía",
        "etiopia", "marruecos", "argelia", "túnez", "tunez", "libia", "sudán",
        "sudan", "congo", "angola", "mozambique", "ghana", "senegal",
        "costa de marfil", "ruanda", "somalia", "zimbabue", "tanzania",
        "uganda", "el cairo", "lagos nigeria", "johannesburgo", "nairobi",
        "unión africana", "union africana",
    ],
    # V17.9.9: "América del Norte" eliminada como región propia (a pedido de
    # Cic) — con 0 artículos y volumen tan bajo de noticias EE.UU./Canadá que
    # no son ya política/economía, se veía como una sección vacía en el menú.
    # Ahora esas noticias caen en "Mundo" por defecto (fallback normal de
    # detectar_region_internacional cuando no hay otra región más específica).
    'medio_oriente': [
        "israel", "palestina", "gaza", "cisjordania", "hamás", "hamas",
        "hezbolá", "hezbola", "irán", "iran", "teherán", "teheran", "irak",
        "bagdad", "siria", "damasco", "líbano", "libano", "beirut",
        "arabia saudita", "riad", "yemen", "jordania", "amán", "aman",
        "qatar", "catar", "emiratos árabes", "emiratos arabes", "dubái",
        "dubai", "kuwait", "omán", "oman", "turquía", "turquia", "ankara",
        "estambul", "netanyahu", "jomeiní", "jomeini",
    ],
    'oceania': [
        "australia", "nueva zelanda", "fiyi", "papúa nueva guinea",
        "papua nueva guinea", "canberra", "sídney", "sidney", "wellington",
        "auckland", "melbourne",
    ],
}

# Slugs REALES en WordPress (confirmados por Cic el 01/07/2026 — coinciden
# exactamente con lo que WordPress generó)
REGION_SLUG_WP = {
    'europa':             'europa',
    'asia':               'asia',
    'africa':             'africa',
    'medio_oriente':      'medio-oriente',
    'oceania':            'oceania',
    'mundo':              'mundo',
}


def detectar_region_internacional(titulo, descripcion=""):
    """
    V17.9.8: Para noticias que caen en categorías "paraguas" (desastre,
    guerra, crimen, religion, educacion, general, mundo) y NO son de LATAM,
    determina a qué subcategoría de "Internacional" pertenecen, contando
    cuántas keywords de cada región aparecen en el texto. La región con más
    coincidencias gana; si no hay ninguna, cae en 'mundo' (fallback seguro
    para temas multilaterales sin país protagonista claro: ONU, cambio
    climático global, IA a nivel mundial, etc.)
    """
    txt = f"{titulo} {descripcion}".lower()
    puntajes = {
        region: sum(1 for kw in kws if kw in txt)
        for region, kws in KEYWORDS_REGIONES.items()
    }
    mejor_region, mejor_puntaje = max(puntajes.items(), key=lambda x: x[1])
    if mejor_puntaje == 0:
        return 'mundo'
    return mejor_region

# ── Keywords para detectar noticias 100% DOMÉSTICAS de España ──
# (V17.8.0) El pool general usa language='es', y eso trae mucha prensa
# española local sin ninguna relevancia para LATAM. Estas keywords sirven
# para EXCLUIR ese ruido, no para bloquear noticias de España con impacto
# internacional o LATAM (guerra, Champions League, Real Madrid vs equipo
# latino, un ministro español hablando de LATAM, etc. — esas SÍ pasan porque
# también van a tener hits en KEYWORDS_LATAM_PAISES o son de alcance global).
KEYWORDS_ESPANA_DOMESTICO = [
    # Política interna española
    "ayuso", "sánchez", "pedro sanchez", "psoe", "vox", " pp ", "sumar",
    "congreso de los diputados", "senado español", "moncloa", "casa real española",
    "felipe vi", "junta electoral central", "defensor del pueblo",
    # Geografía/instituciones España
    "madrid", "barcelona", "sevilla", "valencia", "andalucía", "andalucia",
    "cataluña", "cataluna", "país vasco", "pais vasco", "galicia españa",
    "comunidad de madrid", "generalitat", "ayuntamiento de madrid",
    "guardia civil", "policía nacional española",
    # Cultura/sucesos locales España
    "teatro real", "rtve", "el corte inglés", "renfe", "adif",
]


def es_noticia_espana_domestica(titulo, descripcion=""):
    """
    V17.8.0: Detecta noticias 100% domésticas de España (sin conexión LATAM
    ni relevancia internacional). Se usa como filtro DURO en el pool general.
    """
    txt = f"{titulo} {descripcion}".lower()
    tiene_espana = any(kw in txt for kw in KEYWORDS_ESPANA_DOMESTICO)
    if not tiene_espana:
        return False
    # Si además menciona algún país/tema LATAM, NO es puramente doméstica
    if any(kw in txt for pais_kws in KEYWORDS_LATAM_PAISES.values() for kw in pais_kws):
        return False
    if any(kw in txt for kw in KEYWORDS_CHILE):
        return False
    return True





def es_noticia_chile(titulo, descripcion=""):
    """
    Detecta si una noticia es específicamente de Chile.
    Retorna True si encuentra keywords de Chile en título o descripción.
    """
    txt = f"{titulo} {descripcion}".lower()
    return any(kw in txt for kw in KEYWORDS_CHILE)


def es_noticia_latam_sin_chile(titulo, descripcion=""):
    """
    Detecta si una noticia es de LATAM pero NO de Chile.
    Retorna (True, pais) si es de LATAM, (False, None) si no.
    """
    txt = f"{titulo} {descripcion}".lower()
    # Primero verificar que no sea Chile
    if any(kw in txt for kw in KEYWORDS_CHILE):
        return False, None
    for pais, keywords in KEYWORDS_LATAM_PAISES.items():
        if any(kw in txt for kw in keywords):
            return True, pais
    # Keywords genéricas LATAM
    if any(kw in txt for kw in [
        "latinoamérica", "latinoamerica", "america latina",
        "centroamerica", "centroamérica", "caribe",
        "sudamerica", "sudamérica", "cono sur",
    ]):
        return True, 'latam_general'
    return False, None


def cargar_estado_latam():
    """Carga contadores diarios para Chile y LATAM."""
    datos = cargar_json(ESTADO_LATAM_PATH, {})
    hoy   = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy:
        return {'fecha': hoy, 'chile': 0, 'latam': 0}
    return datos


def guardar_estado_latam(datos):
    guardar_json(ESTADO_LATAM_PATH, datos)


def puede_publicar_latam_chile():
    """Verifica si todavía hay cupo en la cuota de Chile (máx 4/día)."""
    datos = cargar_estado_latam()
    return datos.get('chile', 0) < MAX_POSTS_WP_DIA_CHILE


def puede_publicar_latam_region():
    """Verifica si todavía hay cupo en la cuota LATAM sin Chile (máx 11/día)."""
    datos = cargar_estado_latam()
    return datos.get('latam', 0) < MAX_POSTS_WP_DIA_LATAM


def registrar_publicacion_latam(tipo):
    """Incrementa contador Chile o LATAM."""
    datos = cargar_estado_latam()
    datos[tipo] = datos.get(tipo, 0) + 1
    guardar_estado_latam(datos)


def obtener_rss_chile():
    """
    V17.3: Feeds RSS específicos de medios chilenos.
    Solo retorna noticias confirmadas de Chile.
    """
    fuentes_chile = [
        # V17.9.11: se eliminaron 9 fuentes que devolvían HTTP 404 de forma
        # permanente (La Tercera, BioBioChile, T13, Diario Financiero, El
        # Mostrador, 24 Horas, Mega Noticias, CHV Noticias, Publimetro) — no
        # era un bloqueo temporal, son URLs de RSS que esos medios ya no
        # usan. Busqué reemplazos, pero varios de esos medios parecen haber
        # descontinuado su RSS público por completo (tendencia del rubro).
        # Cooperativa SÍ tenía RSS vivo, solo en otra ruta — corregida abajo.
        ('https://www.emol.com/rss/',                               'Emol'),
        ('https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml', 'Cooperativa'),
        ('https://www.cnnchile.com/feed/',                          'CNN Chile'),
        ('https://www.lacuarta.com/feed/',                          'La Cuarta'),
    ]
    noticias = []
    for url_feed, nombre in fuentes_chile:
        try:
            # V17.9.10: un reintento simple ante errores de conexión
            # transitorios (ej. Emol resetea la conexión de vez en cuando).
            # No es un problema del bot — es el servidor de la fuente
            # rechazando la conexión momentáneamente — pero reintentar una
            # vez, con una pequeña pausa, recupera varios de esos casos.
            try:
                r = requests.get(url_feed, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                time.sleep(1.5)
                r = requests.get(url_feed, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200:
                log(f"RSS Chile: {nombre} devolvió HTTP {r.status_code}", 'debug')
                continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries:
                log(f"RSS Chile: {nombre} sin entradas en el feed", 'debug')
                continue
            for e in feed.entries[:10]:
                t = e.get('title', '')
                if not t:
                    continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l:
                    continue
                d = re.sub(r'<[^>]+>', '', e.get('summary', '') or e.get('description', ''))
                img = None
                if hasattr(e, 'media_content') and e.media_content:
                    img = e.media_content[0].get('url')
                if not img:
                    for enc in getattr(e, 'enclosures', []):
                        if enc.get('type', '').startswith('image'):
                            img = enc.get('href') or enc.get('url')
                            break
                noticias.append({
                    'titulo':      limpiar_texto(t),
                    'descripcion': limpiar_texto(d),
                    'url':         l,
                    'imagen':      img,
                    'fuente':      f"RSS_CL:{nombre}",
                    'fecha':       e.get('published'),
                    'puntaje':     calcular_puntaje(t, d) + 5,  # Bonus por fuente directa Chile
                    'pais':        'chile',
                })
        except Exception as ex:
            log(f"RSS Chile error ({nombre}): {ex}", 'advertencia')
    # Todas las noticias de RSS chilenos se consideran Chile
    log(f"RSS Chile: {len(noticias)} noticias", 'info')
    return noticias


def obtener_rss_latam():
    """
    V17.3: Feeds RSS de medios LATAM (excluyendo Chile).
    """
    fuentes_latam = [
        # México
        ('https://www.eluniversal.com.mx/rss.xml',                  'El Universal MX',   'mexico'),
        ('https://www.milenio.com/rss',                             'Milenio MX',         'mexico'),
        # Argentina
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/',  'Infobae América',    'argentina'),
        ('https://www.lanacion.com.ar/arc/outboundfeeds/rss/',      'La Nación AR',       'argentina'),
        ('https://www.pagina12.com.ar/rss/portada',                 'Página 12 AR',       'argentina'),
        # Colombia
        ('https://www.eltiempo.com/rss/portada.xml',                'El Tiempo CO',       'colombia'),
        ('https://www.semana.com/rss.xml',                          'Semana CO',          'colombia'),
        # Perú
        ('https://elcomercio.pe/arcio/rss/',                        'El Comercio PE',     'peru'),
        ('https://rpp.pe/rss/',                                     'RPP Perú',           'peru'),
        # Venezuela
        ('https://efectococuyo.com/feed/',                          'Efecto Cocuyo VE',   'venezuela'),
        # Bolivia
        ('https://www.paginasiete.bo/rss.xml',                     'Página Siete BO',    'bolivia'),
        # Ecuador
        ('https://www.eluniverso.com/rss.xml',                     'El Universo EC',     'ecuador'),
        # Uruguay
        ('https://www.elpais.com.uy/rss.xml',                      'El País UY',         'uruguay'),
        # LATAM General
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/',  'Infobae Latinoamérica', 'latam'),
        ('https://www.clarin.com/rss/elmundo/',                     'Clarín Mundo',       'latam'),
    ]
    noticias = []
    for url_feed, nombre, pais in fuentes_latam:
        try:
            r = requests.get(url_feed, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries:
                continue
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t:
                    continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l:
                    continue
                # Excluir si es Chile
                d = re.sub(r'<[^>]+>', '', e.get('summary', '') or e.get('description', ''))
                if es_noticia_chile(t, d):
                    continue
                img = None
                if hasattr(e, 'media_content') and e.media_content:
                    img = e.media_content[0].get('url')
                if not img:
                    for enc in getattr(e, 'enclosures', []):
                        if enc.get('type', '').startswith('image'):
                            img = enc.get('href') or enc.get('url')
                            break
                noticias.append({
                    'titulo':      limpiar_texto(t),
                    'descripcion': limpiar_texto(d),
                    'url':         l,
                    'imagen':      img,
                    'fuente':      f"RSS_LATAM:{nombre}",
                    'fecha':       e.get('published'),
                    'puntaje':     calcular_puntaje(t, d) + 3,  # Bonus fuente directa LATAM
                    'pais':        pais,
                })
        except Exception as ex:
            log(f"RSS LATAM error ({nombre}): {ex}", 'advertencia')
    log(f"RSS LATAM: {len(noticias)} noticias", 'info')
    return noticias


def obtener_newsapi_chile():
    """
    V17.3: Queries NewsAPI específicas para noticias de Chile.
    """
    if not NEWS_API_KEY:
        return []
    queries_chile = [
        'Chile noticias hoy Santiago',
        'Chile economía dólar peso chileno inflación',
        'Chile Boric gobierno política',
        'Chile Carabineros seguridad delincuencia',
        'Chile fútbol Colo-Colo Universidad Chile La Roja',
        'Chile terremoto sismo alerta tsunami',
        'Chile litio cobre minería Codelco',
        'Chile empleo trabajo desempleo',
        'Chile salud hospital sistema público',
        'Chile vivienda migración sociedad',
        'Chile vecinos Argentina Perú Bolivia acuerdo',
        'Atacama Patagonia Chile medio ambiente glaciares',
    ]
    noticias = []
    for q in queries_chile:
        try:
            r = requests.get(
                'https://newsapi.org/v2/everything',
                params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es',
                        'sortBy': 'publishedAt', 'pageSize': 5},
                timeout=15
            ).json()
            if r.get('status') == 'ok':
                for a in r.get('articles', []):
                    t   = a.get('title', '')
                    img = a.get('urlToImage')
                    if not t or '[Removed]' in t or not img:
                        continue
                    d = a.get('description', '')
                    if not es_noticia_chile(t, d):
                        continue
                    noticias.append({
                        'titulo':      limpiar_texto(t),
                        'descripcion': limpiar_texto(d),
                        'url':         a.get('url', ''),
                        'imagen':      img,
                        'fuente':      f"NewsAPI_CL:{a.get('source', {}).get('name', '')}",
                        'fecha':       a.get('publishedAt'),
                        'puntaje':     calcular_puntaje(t, d),
                        'pais':        'chile',
                    })
        except Exception as ex:
            log(f"NewsAPI Chile error ({q[:25]}): {ex}", 'advertencia')
    log(f"NewsAPI Chile: {len(noticias)} noticias", 'info')
    return noticias


def obtener_newsapi_latam():
    """
    V17.3: Queries NewsAPI específicas para LATAM (sin Chile).
    """
    if not NEWS_API_KEY:
        return []
    queries_latam = [
        'México noticias CDMX Sheinbaum',
        'Argentina Milei economía inflación',
        'Colombia Petro Bogotá noticias',
        'Brasil Lula sao paulo',
        'Venezuela Maduro Caracas crisis',
        'Perú Lima noticias gobierno',
        'Ecuador Quito Noboa noticias',
        'Bolivia La Paz Arce gobierno',
        'Uruguay Montevideo Orsi noticias',
        'El Salvador Bukele noticias',
        'Guatemala Honduras Costa Rica Panamá noticias',
        'República Dominicana Cuba Puerto Rico noticias',
        'América Latina economía política',
        'Centroamérica migración crisis',
    ]
    noticias = []
    for q in queries_latam:
        try:
            r = requests.get(
                'https://newsapi.org/v2/everything',
                params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es',
                        'sortBy': 'publishedAt', 'pageSize': 5},
                timeout=15
            ).json()
            if r.get('status') == 'ok':
                for a in r.get('articles', []):
                    t   = a.get('title', '')
                    img = a.get('urlToImage')
                    if not t or '[Removed]' in t or not img:
                        continue
                    d = a.get('description', '')
                    # Excluir si es Chile
                    if es_noticia_chile(t, d):
                        continue
                    noticias.append({
                        'titulo':      limpiar_texto(t),
                        'descripcion': limpiar_texto(d),
                        'url':         a.get('url', ''),
                        'imagen':      img,
                        'fuente':      f"NewsAPI_LATAM:{a.get('source', {}).get('name', '')}",
                        'fecha':       a.get('publishedAt'),
                        'puntaje':     calcular_puntaje(t, d),
                        'pais':        'latam',
                    })
        except Exception as ex:
            log(f"NewsAPI LATAM error ({q[:25]}): {ex}", 'advertencia')
    log(f"NewsAPI LATAM: {len(noticias)} noticias", 'info')
    return noticias


def publicar_bloque_latam_chile():
    """
    V17.3: Bloque de publicación exclusivo para noticias de Chile y LATAM.
    Publica hasta 1 artículo de Chile y/o 1 de LATAM por ejecución,
    respetando los límites diarios de 4 (Chile) y 11 (LATAM).
    Retorna (exito_chile, exito_latam).
    """
    log("\n" + "=" * 60, 'info')
    log("🌎 BLOQUE V17.3 — LATAM + CHILE", 'info')
    estado_latam = cargar_estado_latam()
    log(f"   Publicados hoy → Chile: {estado_latam.get('chile',0)}/{MAX_POSTS_WP_DIA_CHILE} | "
        f"LATAM: {estado_latam.get('latam',0)}/{MAX_POSTS_WP_DIA_LATAM}", 'info')

    h             = cargar_historial()
    exito_chile   = False
    exito_latam   = False

    # ── 1) Intentar publicar 1 artículo de CHILE ─────────────
    if puede_publicar_latam_chile():
        log("\n🇨🇱 Buscando noticia de Chile...", 'info')
        noticias_cl = []
        noticias_cl.extend(obtener_rss_chile())
        noticias_cl.extend(obtener_newsapi_chile())
        # Filtrar estricto: solo Chile
        noticias_cl = [n for n in noticias_cl if es_noticia_chile(n.get('titulo',''), n.get('descripcion',''))]
        noticias_cl = deduplicar_batch(noticias_cl)
        noticias_cl.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
        log(f"   Candidatas Chile: {len(noticias_cl)}", 'info')

        for nt in noticias_cl[:40]:
            url    = nt.get('url', '')
            titulo = nt.get('titulo', '')
            desc   = nt.get('descripcion', '')
            if not url or not titulo:
                continue
            dup, razon = noticia_ya_publicada(h, url, titulo, desc)
            if dup:
                continue
            if nt.get('puntaje', 0) < 2:
                continue
            # V17.6.4: Filtro spam en bloque Chile
            es_spam, kw_spam = es_contenido_spam(titulo, desc)
            if es_spam:
                log(f"   🚫 SPAM Chile: '{kw_spam}' — descartando", 'advertencia')
                continue

            # V17.9.3: umbrales subidos (300→500 / 200→400 / 150→250) — ver
            # nota completa en el flujo general, mismo motivo.
            cont_web, _ = extraer_contenido(url)
            contenido_ok = cont_web if (cont_web and len(cont_web) >= 500) else (desc if len(desc) >= 400 else None)
            if not contenido_ok and cont_web and len(cont_web) >= 250:
                contenido_ok = cont_web + ' ' + desc if desc else cont_web
            if not contenido_ok:
                continue

            # V17.9.6: segundo chequeo de spam/apuestas contra el contenido
            # completo — ver nota completa en el flujo general.
            es_spam2, kw_spam2 = es_contenido_spam(titulo, contenido_ok[:3000])
            if es_spam2:
                log(f"   🚫 SPAM Chile en contenido: '{kw_spam2}' — descartando", 'advertencia')
                continue

            imagen_encontrada = None
            if nt.get('imagen'):
                imagen_encontrada = descargar_imagen(nt['imagen'])
            if not imagen_encontrada:
                img_url = extraer_imagen_web(url)
                if img_url:
                    imagen_encontrada = descargar_imagen(img_url)
            if not imagen_encontrada:
                imagen_encontrada = crear_imagen_titulo(titulo, 'latinoamerica')
            if not imagen_encontrada:
                continue

            url_wp = publicar_en_wordpress(
                titulo         = titulo,
                contenido      = contenido_ok,
                tema           = 'latinoamerica',
                imagen_path    = imagen_encontrada,
                fuente_url     = url,
                fecha_fuente   = nt.get('fecha'),
                fuente_noticia = nt.get('fuente', ''),
            )
            try:
                if imagen_encontrada and os.path.exists(imagen_encontrada):
                    os.remove(imagen_encontrada)
            except:
                pass

            if url_wp:
                exito_chile = True
                registrar_publicacion_latam('chile')
                guardar_estado_wp()
                desc_full = (desc + ' ' + contenido_ok[:400]).strip()
                h = guardar_en_historial(h, url, titulo, desc_full)
                h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1
                guardar_json(HISTORIAL_PATH, h)
                log(f"✅ Chile publicado: {titulo[:60]}", 'exito')
                # Pinterest
                if PINTEREST_TOKEN:
                    publicar_pinterest(titulo, contenido_ok[:490], url_wp, None, 'latinoamerica')
                break
    else:
        log(f"🇨🇱 Chile: cuota diaria alcanzada ({MAX_POSTS_WP_DIA_CHILE}/{MAX_POSTS_WP_DIA_CHILE})", 'info')

    # ── 2) Intentar publicar 1 artículo de LATAM (sin Chile) ─
    if puede_publicar_latam_region():
        log("\n🌎 Buscando noticia LATAM (sin Chile)...", 'info')
        noticias_la = []
        noticias_la.extend(obtener_rss_latam())
        noticias_la.extend(obtener_newsapi_latam())
        # Filtrar: solo LATAM sin Chile
        filtradas = []
        for n in noticias_la:
            es_la, pais = es_noticia_latam_sin_chile(n.get('titulo',''), n.get('descripcion',''))
            if es_la:
                n['pais'] = pais
                filtradas.append(n)
        noticias_la = deduplicar_batch(filtradas)
        noticias_la.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
        log(f"   Candidatas LATAM: {len(noticias_la)}", 'info')

        for nt in noticias_la[:40]:
            url    = nt.get('url', '')
            titulo = nt.get('titulo', '')
            desc   = nt.get('descripcion', '')
            if not url or not titulo:
                continue
            dup, razon = noticia_ya_publicada(h, url, titulo, desc)
            if dup:
                continue
            if nt.get('puntaje', 0) < 2:
                continue

            # V17.9.6 FIX: este bloque LATAM nunca tuvo filtro de spam/apuestas
            # — solo lo tenía el bloque Chile. Por eso se coló un artículo de
            # cuotas de apuestas del Mundial 2026 (fuente peruana). Se agrega
            # el mismo filtro que ya existe en Chile y en el flujo general.
            es_spam, kw_spam = es_contenido_spam(titulo, desc)
            if es_spam:
                log(f"   🚫 SPAM LATAM: '{kw_spam}' — descartando", 'advertencia')
                continue

            # V17.9.3: umbrales subidos (300→500 / 200→400 / 150→250) — ver
            # nota completa en el flujo general, mismo motivo.
            cont_web, _ = extraer_contenido(url)
            contenido_ok = cont_web if (cont_web and len(cont_web) >= 500) else (desc if len(desc) >= 400 else None)
            if not contenido_ok and cont_web and len(cont_web) >= 250:
                contenido_ok = cont_web + ' ' + desc if desc else cont_web
            if not contenido_ok:
                continue

            # V17.9.6: segundo chequeo de spam/apuestas contra el contenido
            # completo — ver nota completa en el flujo general.
            es_spam2, kw_spam2 = es_contenido_spam(titulo, contenido_ok[:3000])
            if es_spam2:
                log(f"   🚫 SPAM LATAM en contenido: '{kw_spam2}' — descartando", 'advertencia')
                continue

            imagen_encontrada = None
            if nt.get('imagen'):
                imagen_encontrada = descargar_imagen(nt['imagen'])
            if not imagen_encontrada:
                img_url = extraer_imagen_web(url)
                if img_url:
                    imagen_encontrada = descargar_imagen(img_url)
            if not imagen_encontrada:
                imagen_encontrada = crear_imagen_titulo(titulo, 'latinoamerica')
            if not imagen_encontrada:
                continue

            url_wp = publicar_en_wordpress(
                titulo         = titulo,
                contenido      = contenido_ok,
                tema           = 'latinoamerica',
                imagen_path    = imagen_encontrada,
                fuente_url     = url,
                fecha_fuente   = nt.get('fecha'),
                fuente_noticia = nt.get('fuente', ''),
            )
            try:
                if imagen_encontrada and os.path.exists(imagen_encontrada):
                    os.remove(imagen_encontrada)
            except:
                pass

            if url_wp:
                exito_latam = True
                registrar_publicacion_latam('latam')
                guardar_estado_wp()
                desc_full = (desc + ' ' + contenido_ok[:400]).strip()
                h = guardar_en_historial(h, url, titulo, desc_full)
                h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1
                guardar_json(HISTORIAL_PATH, h)
                log(f"✅ LATAM publicado [{nt.get('pais','?')}]: {titulo[:55]}", 'exito')
                # Pinterest
                if PINTEREST_TOKEN:
                    publicar_pinterest(titulo, contenido_ok[:490], url_wp, None, 'latinoamerica')
                break
    else:
        log(f"🌎 LATAM: cuota diaria alcanzada ({MAX_POSTS_WP_DIA_LATAM}/{MAX_POSTS_WP_DIA_LATAM})", 'info')

    estado_latam = cargar_estado_latam()
    log(f"\n📊 LATAM hoy → Chile: {estado_latam.get('chile',0)}/{MAX_POSTS_WP_DIA_CHILE} | "
        f"LATAM: {estado_latam.get('latam',0)}/{MAX_POSTS_WP_DIA_LATAM}", 'info')
    return exito_chile, exito_latam


# ──────────────────────────────────────────────────────────
# FUENTES DE NOTICIAS
# ──────────────────────────────────────────────────────────
def obtener_newsapi():
    if not NEWS_API_KEY:
        return []
    # V17.6: Queries reenfocadas — 80% orientadas a LATAM y audiencia hispanohablante
    queries = [
        # ── LATAM prioridad máxima ────────────────────────────────────────────
        'Chile noticias economía política hoy',
        'Chile Argentina Colombia últimas noticias',
        'México Brasil Perú América Latina hoy',
        'Venezuela Bolivia Ecuador Uruguay noticias',
        'Latinoamérica economía inversión noticias',
        'Boric Milei Lula Sheinbaum política',
        'Copa Libertadores Sudamericana fútbol LATAM',
        'eliminatorias Mundial 2026 Sudamérica',
        'dólar inflación Argentina Chile México',
        'litio cobre minería Latinoamérica',
        'startups tecnología América Latina fintech',
        'reggaeton música latina Bad Bunny Shakira',
        'cine series streaming Latinoamérica',
        # ── Internacional con impacto LATAM ───────────────────────────────────
        'economy inflation markets Latin America impact',
        'technology artificial intelligence Spanish',
        'Trump tariffs trade Latin America',
        'climate change South America environment',
        # ── Deportes globales ─────────────────────────────────────────────────
        'football soccer Champions League goals',
        'Copa del Mundo 2026 World Cup Messi',
        'NBA basketball playoffs finals',
        'Formula 1 F1 Grand Prix race',
        'tennis ATP WTA Roland Garros',
        # ── Entretenimiento global con audiencia latina ───────────────────────
        'Netflix series premiere streaming español',
        'music Grammy Billboard Latin',
        'Oscar awards Hollywood cine',
        # ── Internacional de alto impacto ─────────────────────────────────────
        'Ukraine Russia war conflict',
        'world news international latest',
        'science space NASA discovery',
    ]
    noticias = []
    for q in queries:
        try:
            r = requests.get(
                'https://newsapi.org/v2/everything',
                params={'apiKey': NEWS_API_KEY, 'q': q, 'language': 'es',
                        'sortBy': 'publishedAt', 'pageSize': 5},
                timeout=15
            ).json()
            if r.get('status') == 'ok':
                for a in r.get('articles', []):
                    t   = a.get('title', '')
                    img = a.get('urlToImage')
                    # FILTRO ESTRICTO: sin imagen → descartar
                    if not t or '[Removed]' in t or not img:
                        continue
                    d = a.get('description', '')
                    # V17.8.0: descartar ruido doméstico de España (sin impacto LATAM)
                    if es_noticia_espana_domestica(t, d):
                        continue
                    noticias.append({
                        'titulo':      limpiar_texto(t),
                        'descripcion': limpiar_texto(d),
                        'url':         a.get('url', ''),
                        'imagen':      img,
                        'fuente':      f"NewsAPI:{a.get('source', {}).get('name', 'Unknown')}",
                        'fecha':       a.get('publishedAt'),
                        'puntaje':     calcular_puntaje(t, d),
                    })
        except Exception as e:
            log(f"NewsAPI error ({q[:20]}): {e}", 'advertencia')
    log(f"NewsAPI: {len(noticias)} noticias con imagen", 'info')
    return noticias

def obtener_newsdata():
    if not NEWSDATA_API_KEY:
        return []
    # V17: Se agregan 'entertainment' y 'sports' que estaban ausentes
    categorias = ['world', 'politics', 'business', 'technology', 'science',
                  'health', 'entertainment', 'sports']
    # V17.8.0: 'country' acota directamente a 5 países LATAM (máx. permitido
    # en plan free/basic de NewsData.io) en vez de depender solo del idioma,
    # que traía mucho ruido de España.
    PAISES_NEWSDATA = 'cl,ar,mx,co,pe'
    noticias = []
    for cat in categorias:
        try:
            r = requests.get(
                'https://newsdata.io/api/1/news',
                params={'apikey': NEWSDATA_API_KEY, 'language': 'es',
                        'country': PAISES_NEWSDATA,
                        'category': cat, 'size': 10, 'image': 1},
                timeout=15
            ).json()
            if r.get('status') == 'success':
                for a in r.get('results', []):
                    t   = a.get('title') or ''
                    img = a.get('image_url')
                    if not t or not img:
                        continue
                    d = a.get('description') or ''
                    # V17.8.0: filtro adicional por si igual llega ruido de España
                    if es_noticia_espana_domestica(t, d):
                        continue
                    noticias.append({
                        'titulo':      limpiar_texto(t),
                        'descripcion': limpiar_texto(d),
                        'url':         a.get('link', ''),
                        'imagen':      img,
                        'fuente':      f"NewsData:{a.get('source_id', 'Unknown')}",
                        'fecha':       a.get('pubDate'),
                        'puntaje':     calcular_puntaje(t, d),
                    })
        except Exception as e:
            log(f"NewsData error ({cat}): {e}", 'advertencia')
    log(f"NewsData: {len(noticias)} noticias con imagen", 'info')
    return noticias

def obtener_gnews():
    if not GNEWS_API_KEY:
        return []
    # V17.8.0: cada tópico ahora fija un país LATAM (antes usaba el país por
    # defecto de la API, que no es ninguno de LATAM) — mismo número de
    # llamadas, pero apuntando directo a la región.
    topicos_paises = [
        ('world',         'mx'),
        ('nation',        'cl'),
        ('business',      'ar'),
        ('technology',    'co'),
        ('sports',        'mx'),
        ('health',        'cl'),
        ('science',       'ar'),
        ('entertainment', 'co'),
    ]
    noticias = []
    for topic, pais in topicos_paises:
        try:
            r = requests.get(
                'https://gnews.io/api/v4/top-headlines',
                params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 10,
                        'topic': topic, 'country': pais},
                timeout=15
            ).json()
            for a in r.get('articles', []):
                t   = a.get('title') or ''
                img = a.get('image')
                if not t or not img:
                    continue
                d = a.get('description') or ''
                # V17.8.0: descartar ruido doméstico de España
                if es_noticia_espana_domestica(t, d):
                    continue
                noticias.append({
                    'titulo':      limpiar_texto(t),
                    'descripcion': limpiar_texto(d),
                    'url':         a.get('url', ''),
                    'imagen':      img,
                    'fuente':      f"GNews:{a.get('source', {}).get('name', 'Unknown')}",
                    'fecha':       a.get('publishedAt'),
                    'puntaje':     calcular_puntaje(t, d),
                })
        except Exception as e:
            log(f"GNews error ({topic}/{pais}): {e}", 'advertencia')
    log(f"GNews: {len(noticias)} noticias con imagen", 'info')
    return noticias

def obtener_rss():
    # V17.6: RSS reenfocados LATAM-first — medios regionales en primer lugar
    fuentes = [
        # ── LATAM principal — medios regionales de referencia ──────────────────
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/',     'Infobae América'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/economia/',    'Infobae Economía'),
        ('https://www.eluniversal.com.mx/rss.xml',                     'El Universal MX'),
        ('https://www.milenio.com/rss',                                'Milenio MX'),
        ('https://www.lanacion.com.ar/arc/outboundfeeds/rss/',         'La Nación Argentina'),
        ('https://www.pagina12.com.ar/rss/portada',                    'Página 12 AR'),
        ('https://www.clarin.com/rss/elmundo/',                        'Clarín Mundo'),
        ('https://www.eltiempo.com/rss/portada.xml',                   'El Tiempo Colombia'),
        ('https://www.semana.com/rss.xml',                             'Semana Colombia'),
        ('https://elcomercio.pe/arcio/rss/',                           'El Comercio Perú'),
        ('https://rpp.pe/rss/',                                        'RPP Perú'),
        ('https://efectococuyo.com/feed/',                             'Efecto Cocuyo VE'),
        ('https://www.eluniverso.com/rss.xml',                         'El Universo Ecuador'),
        ('https://www.elpais.com.uy/rss.xml',                          'El País Uruguay'),
        ('https://www.abc.com.py/rss/portada.xml',                     'ABC Paraguay'),
        ('https://www.paginasiete.bo/rss.xml',                         'Página Siete Bolivia'),
        ('https://www.nacion.com/rss/portada.rss',                     'La Nación Costa Rica'),
        ('https://www.prensa.com/feed/',                               'La Prensa Panamá'),
        ('https://www.listindiario.com/rss',                           'Listín Diario RD'),
        # ── Internacional de referencia ─────────────────────────────────────────
        ('http://feeds.bbci.co.uk/mundo/rss.xml',                      'BBC Mundo'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada', 'El País Internacional'),
        ('https://www.dw.com/es/ultimas-noticias/s-30689792/rss',      'Deutsche Welle ES'),
        ('https://feeds.france24.com/es/',                             'France 24 ES'),
        ('https://www.efe.com/efe/espana/1/rss',                       'EFE'),  # ⚠️ V17.8.0: esta URL apunta a la sección ESPAÑA de EFE (nota el "/espana/" en la ruta). El filtro es_noticia_espana_domestica() descarta lo puramente local, pero si tienen a mano el RSS de la sección América/Internacional de EFE, conviene reemplazar esta URL.
        # ── Deportes — fútbol LATAM y mundial ──────────────────────────────────
        ('https://www.espn.com.mx/rss/deportes.xml',                   'ESPN Deportes'),
        ('https://e00-marca.uecdn.es/rss/portada.xml',                 'Marca'),
        ('https://feeds.as.com/mrss-s/pages/as/site/as.com/portada/', 'AS Deportes'),
        ('https://www.goal.com/es/rss',                                'Goal ES'),
        ('https://www.record.com.mx/rss/portada.xml',                  'Record MX'),
        ('https://www.mundodeportivo.com/rss/home.xml',                'Mundo Deportivo'),
        # ── Entretenimiento — artistas latinos ─────────────────────────────────
        ('https://los40.com/los40/rss/portada/',                       'Los 40'),
        ('https://www.espinof.com/feed',                               'Espinof Cine'),
        ('https://www.fotogramas.es/rss/noticias/',                    'Fotogramas'),
        ('https://www.sensacine.com/rss/',                             'SensaCine'),
        # ── Tecnología ──────────────────────────────────────────────────────────
        ('https://feeds.xataka.com/xataka',                            'Xataka'),
        ('https://hipertextual.com/feed',                              'Hipertextual'),
    ]
    noticias = []
    for url_feed, nombre in fuentes:
        try:
            r = requests.get(url_feed, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries:
                continue
            for e in feed.entries[:8]:
                t = e.get('title', '')
                if not t:
                    continue
                t = re.sub(r'\s*-\s*[^-]*$', '', t)
                l = e.get('link', '')
                if not l:
                    continue
                d = re.sub(r'<[^>]+>', '', e.get('summary', '') or e.get('description', ''))
                img = None
                if hasattr(e, 'media_content') and e.media_content:
                    img = e.media_content[0].get('url')
                if not img:
                    # Intentar enclosure
                    for enc in getattr(e, 'enclosures', []):
                        if enc.get('type', '').startswith('image'):
                            img = enc.get('href') or enc.get('url')
                            break
                # RSS: aceptar sin imagen (se intenta obtener después)
                # V17.8.0: descartar ruido doméstico de España
                if es_noticia_espana_domestica(t, d):
                    continue
                noticias.append({
                    'titulo':      limpiar_texto(t),
                    'descripcion': limpiar_texto(d),
                    'url':         l,
                    'imagen':      img,
                    'fuente':      f"RSS:{nombre}",
                    'fecha':       e.get('published'),
                    'puntaje':     calcular_puntaje(t, d),
                })
        except Exception as e:
            log(f"RSS error ({nombre}): {e}", 'advertencia')
    log(f"RSS: {len(noticias)} noticias", 'info')
    return noticias


# ──────────────────────────────────────────────────────────
# DEDUPLICACIÓN
# ──────────────────────────────────────────────────────────
def deduplicar_batch(noticias):
    urls_vistas    = set()
    titulos_vistos = []
    resultado      = []
    for n in noticias:
        url_n  = normalizar_url(n.get('url', ''))
        titulo = n.get('titulo', '')
        if not url_n or not titulo:
            continue
        if url_n in urls_vistas:
            continue
        es_dup = any(similitud_titulos(titulo, t) > 0.78 for t in titulos_vistos)
        if es_dup:
            continue
        urls_vistas.add(url_n)
        titulos_vistos.append(titulo)
        resultado.append(n)
    log(f"Dedup batch: {len(noticias)} → {len(resultado)} únicas", 'info')
    return resultado


# ──────────────────────────────────────────────────────────
# EXTRACCIÓN DE CONTENIDO E IMAGEN
# ──────────────────────────────────────────────────────────
def extraer_contenido(url):
    if not url:
        return None, None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        s = BeautifulSoup(r.content, 'html.parser')
        for e in s(['script', 'style', 'nav', 'header', 'footer']):
            e.decompose()
        for selector in ['article', '[class*="article-content"]', '[class*="entry-content"]', '[class*="post-content"]']:
            art = s.select_one(selector)
            if art:
                ps = [p for p in art.find_all('p') if len(p.get_text()) > 40]
                if len(ps) >= 2:
                    txt = ' '.join([limpiar_texto(p.get_text()) for p in ps])
                    if len(txt) > 200:
                        return txt[:5000], None
        return None, None
    except:
        return None, None

def extraer_imagen_web(url):
    if not url:
        return None
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        s = BeautifulSoup(r.content, 'html.parser')
        for prop in ['og:image', 'twitter:image']:
            tag = s.find('meta', property=prop) or s.find('meta', attrs={'name': prop})
            if tag:
                img = tag.get('content', '').strip()
                if img and img.startswith('http') and 'google' not in img.lower():
                    return img
        return None
    except:
        return None

def descargar_imagen(url):
    """
    Descarga y optimiza imagen para WordPress + Google Discover.
    V14: Garantiza mínimo 1200px de ancho (requisito oficial Google Discover).
    - Si imagen < 1200px → amplía proporcionalmente con Lanczos
    - Si imagen > 2000px → recorta a 1600px máximo
    - Calidad JPEG 92 para nitidez en móvil
    """
    if not url:
        return None
    for bloqueo in ['google.com', 'gstatic.com', 'facebook.com', 'logo', 'icon', 'favicon']:
        if bloqueo in url.lower():
            return None
    try:
        from PIL import Image
        from io import BytesIO
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20, stream=True)
        if r.status_code != 200:
            return None
        ct = r.headers.get('content-type', '')
        if 'image' not in ct and 'octet' not in ct:
            return None
        data = r.content
        img  = Image.open(BytesIO(data))
        w, h = img.size

        # Descartar imágenes demasiado pequeñas (iconos, logos)
        if w < 300 or h < 200:
            log(f"⚠️ Imagen muy pequeña ({w}x{h}) — descartando", 'debug')
            return None

        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        # ── V14: Redimensionado inteligente para Google Discover ──────
        # Google Discover requiere MÍNIMO 1200px de ancho
        # Tamaño óptimo: 1200x630 (16:9) o 1600x900
        MIN_DISCOVER = 1200
        MAX_DISCOVER = 1600

        w2, h2 = img.size
        if w2 < MIN_DISCOVER:
            # Ampliar — siempre preservar proporción
            ratio = MIN_DISCOVER / w2
            nuevo_w = MIN_DISCOVER
            nuevo_h = int(h2 * ratio)
            img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)
            log(f"🔍 Imagen ampliada: {w2}x{h2} → {nuevo_w}x{nuevo_h} (Discover)", 'debug')
        elif w2 > MAX_DISCOVER:
            # Reducir para no desperdiciar espacio en disco
            ratio = MAX_DISCOVER / w2
            nuevo_w = MAX_DISCOVER
            nuevo_h = int(h2 * ratio)
            img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)
            log(f"📐 Imagen reducida: {w2}x{h2} → {nuevo_w}x{nuevo_h}", 'debug')

        img = agregar_watermark(img)
        p   = f'/tmp/noticia_{generar_hash(url)}.jpg'
        # Calidad 92 — mejor nitidez en móvil (era 88)
        img.save(p, 'JPEG', quality=92, optimize=True)
        if os.path.getsize(p) < 3000:
            os.remove(p)
            return None
        final_w, final_h = img.size
        log(f"🖼️ Imagen lista: {final_w}x{final_h} — {os.path.getsize(p)//1024}KB", 'debug')
        return p
    except Exception as e:
        log(f"⚠️ Error descargando imagen: {e}", 'debug')
        return None

def agregar_watermark(img, posicion='esquina_inferior_derecha'):
    """
    V14: Watermark mejorado — fondo más visible, tipografía más grande.
    Posición: esquina inferior derecha, con más margen del borde.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        ancho, alto = img.size
        # Tamaño de fuente proporcional al ancho de imagen
        font_size = max(20, int(ancho * 0.018))
        try:
            font_wm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font_wm = ImageFont.load_default()
        texto_wm = "verdadhoy.com"
        try:
            bbox = draw.textbbox((0, 0), texto_wm, font=font_wm)
            txt_w, txt_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except:
            txt_w, txt_h = 150, font_size
        margen, padding = 18, 8
        x = ancho - txt_w - margen - padding * 2
        y = alto  - txt_h - margen - padding * 2
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        # Fondo negro semitransparente con bordes redondeados
        overlay_draw.rounded_rectangle(
            [x - padding, y - padding, x + txt_w + padding, y + txt_h + padding],
            radius=6, fill=(0, 0, 0, 180)
        )
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        # Sombra sutil + texto amarillo dorado
        draw.text((x + 1, y + 1), texto_wm, font=font_wm, fill=(0, 0, 0, 200))
        draw.text((x, y), texto_wm, font=font_wm, fill='#f5c518')
        return img
    except Exception as e:
        log(f"⚠️ Watermark error: {e}", 'debug')
        return img

def crear_imagen_titulo(titulo, categoria='general'):
    """
    V14: Imagen fallback optimizada para Google Discover.
    - Tamaño 1600x900 (16:9 — óptimo para Discover y redes sociales)
    - Gradiente de fondo profesional
    - Badge de categoría con color
    - Tipografía escalada al título
    - Barra de marca VerdadHoy
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap

        W, H = 1600, 900
        img  = Image.new('RGB', (W, H), color='#0f172a')
        draw = ImageDraw.Draw(img)

        # ── Gradiente de fondo (simulado con rectángulos) ──
        for i in range(H):
            ratio = i / H
            r = int(15  + (30 - 15)  * ratio)
            g = int(23  + (41 - 23)  * ratio)
            b = int(42  + (69 - 42)  * ratio)
            draw.line([(0, i), (W, i)], fill=(r, g, b))

        # ── Barra superior de acento ──
        draw.rectangle([(0, 0), (W, 10)], fill='#dc2626')

        # ── Badge de categoría ──
        colores_cat = {
            'guerra':          '#dc2626', 'politica':        '#7c3aed',
            'economia':        '#059669', 'tecnologia':      '#2563eb',
            'deportes':        '#d97706', 'ciencia':         '#0891b2',
            'salud':           '#16a34a', 'entretenimiento': '#db2777',
            'latinoamerica':   '#ea580c', 'clima':           '#0284c7',
            'medio_ambiente':  '#15803d', 'crimen':          '#9f1239',
            'desastre':        '#b45309', 'mundo':           '#4338ca',
            'religion':        '#7e22ce', 'general':         '#475569',
        }
        nombres_cat = {
            'guerra': 'CONFLICTO', 'politica': 'POLÍTICA', 'economia': 'ECONOMÍA',
            'tecnologia': 'TECNOLOGÍA', 'deportes': 'DEPORTES', 'ciencia': 'CIENCIA',
            'salud': 'SALUD', 'entretenimiento': 'ENTRETENIMIENTO',
            'latinoamerica': 'LATINOAMÉRICA', 'clima': 'CLIMA',
            'medio_ambiente': 'MEDIO AMBIENTE', 'crimen': 'SEGURIDAD',
            'desastre': 'EMERGENCIA', 'mundo': 'MUNDO', 'general': 'NOTICIAS',
        }
        color_badge = colores_cat.get(categoria, '#475569')
        texto_badge = nombres_cat.get(categoria, 'NOTICIAS')

        try:
            font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 62)
            font_marca  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
            font_sub    = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            font_badge = font_titulo = font_marca = font_sub = ImageFont.load_default()

        # Badge rectángulo con color de categoría
        badge_x, badge_y = 70, 70
        try:
            bbox_b = draw.textbbox((0, 0), texto_badge, font=font_badge)
            bw, bh = bbox_b[2] - bbox_b[0], bbox_b[3] - bbox_b[1]
        except:
            bw, bh = 160, 32
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + bw + 28, badge_y + bh + 16],
            radius=6, fill=color_badge
        )
        draw.text((badge_x + 14, badge_y + 8), texto_badge, font=font_badge, fill='white')

        # ── Título principal (escalado para que quepa) ──
        chars_por_linea = 38 if len(titulo) > 80 else 44
        font_size_titulo = 52 if len(titulo) > 100 else 62
        try:
            font_titulo = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_titulo)
        except:
            pass

        tt = textwrap.fill(titulo[:160], width=chars_por_linea)
        lineas = tt.split('\n')
        alto_total_texto = len(lineas) * (font_size_titulo + 14)
        y_texto = max(160, (H - alto_total_texto) // 2 - 40)

        # Sombra del título
        for linea in lineas:
            draw.text((72, y_texto + 2), linea, font=font_titulo, fill=(0, 0, 0, 120))
            y_texto += font_size_titulo + 14
        # Texto real del título
        y_texto = max(160, (H - alto_total_texto) // 2 - 40)
        for linea in lineas:
            draw.text((70, y_texto), linea, font=font_titulo, fill='#f1f5f9')
            y_texto += font_size_titulo + 14

        # ── Barra inferior con marca ──
        draw.rectangle([(0, H - 90), (W, H)], fill='#1e293b')
        draw.rectangle([(0, H - 90), (W, H - 87)], fill=color_badge)
        draw.text((70, H - 65), "🌍 VERDAD HOY", font=font_marca, fill='#f1f5f9')
        draw.text((W - 420, H - 60), "verdadhoy.com", font=font_sub, fill='#94a3b8')

        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img = agregar_watermark(img)
        img.save(p, 'JPEG', quality=92, optimize=True)
        log(f"🖼️ Imagen Discover generada: 1600x900 (fallback)", 'advertencia')
        return p
    except Exception as e:
        log(f"⚠️ Error generando imagen fallback: {e}", 'debug')
        return None


# ──────────────────────────────────────────────────────────
# V11: FUNCIÓN 3 — VIDEO MANUAL VIA /pending_videos/
# ──────────────────────────────────────────────────────────
def listar_pending_videos_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return []
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PENDING_VIDEOS_DIR}"
        headers = {'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            log(f"⚠️ GitHub API error {resp.status_code}", 'advertencia')
            return []
        return [f for f in resp.json() if isinstance(f, dict) and f.get('name', '').endswith('.txt')]
    except Exception as e:
        log(f"⚠️ Error listando pending_videos: {e}", 'advertencia')
        return []

def leer_archivo_github(download_url):
    try:
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        resp = requests.get(download_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        log(f"⚠️ Error leyendo archivo GitHub: {e}", 'advertencia')
    return None

def eliminar_archivo_github(nombre_archivo, sha):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PENDING_VIDEOS_DIR}/{nombre_archivo}"
        headers = {'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
        payload = {'message': f'[bot] Eliminar video procesado: {nombre_archivo}', 'sha': sha}
        resp = requests.delete(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 204):
            log(f"🗑️ Archivo eliminado: {nombre_archivo}", 'exito')
            return True
    except Exception as e:
        log(f"⚠️ Error eliminando: {e}", 'advertencia')
    return False

def parsear_archivo_pending(contenido):
    resultado = {'descripcion': '', 'embed': ''}
    lineas = contenido.strip().split('\n')
    modo   = None
    buffer = []
    for linea in lineas:
        if linea.strip().upper().startswith('DESCRIPCION:'):
            if modo == 'embed' and buffer:
                resultado['embed'] = '\n'.join(buffer).strip()
            modo   = 'descripcion'
            buffer = [linea.split(':', 1)[1].strip() if ':' in linea else '']
        elif linea.strip().upper().startswith('EMBED:'):
            if modo == 'descripcion' and buffer:
                resultado['descripcion'] = '\n'.join(buffer).strip()
            modo   = 'embed'
            buffer = [linea.split(':', 1)[1].strip() if ':' in linea else '']
        else:
            if modo:
                buffer.append(linea)
    if modo == 'descripcion' and buffer:
        resultado['descripcion'] = '\n'.join(buffer).strip()
    elif modo == 'embed' and buffer:
        resultado['embed'] = '\n'.join(buffer).strip()
    return resultado

def generar_metadatos_video_manual(descripcion, embed):
    api_key = GROQ_API_KEY or OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        titulo = descripcion[:60].strip()
        return {
            'titulo_seo': titulo, 'meta_descripcion': descripcion[:155],
            'categoria': detectar_tema(titulo, descripcion),
            'keyword_principal': titulo.split()[0] if titulo else 'noticia',
            'keywords_secundarias': [], 'contenido_html': f"<p>{descripcion}</p>"
        }
    prompt = f"""Eres Editor Jefe de VerdadHoy.com. Analiza esta descripción de video y genera metadatos SEO.

DESCRIPCIÓN: {descripcion[:1500]}

RESPONDE SOLO con JSON exacto:
{{"titulo_seo": "máx 60 chars, keyword primero", "meta_descripcion": "140-155 chars exactos", "categoria": "guerra|politica|economia|tecnologia|desastre|deportes|ciencia|salud|entretenimiento|latinoamerica|clima|mundo|general", "keyword_principal": "2-4 palabras", "keywords_secundarias": ["kw2","kw3"], "contenido_html": "HTML con párrafos, máx 400 palabras"}}"""
    try:
        headers = {'Content-Type': 'application/json'}
        # V17.9.5: Groq (gratis) como proveedor preferido, igual que en reescribir_noticia_v9
        if GROQ_API_KEY:
            headers['Authorization'] = f'Bearer {GROQ_API_KEY}'
            url_ia, model = 'https://api.groq.com/openai/v1/chat/completions', 'llama-3.3-70b-versatile'
        elif OPENROUTER_API_KEY:
            headers['Authorization'] = f'Bearer {OPENROUTER_API_KEY}'
            url_ia, model = 'https://openrouter.ai/api/v1/chat/completions', 'openai/gpt-4o-mini'
        else:
            headers['Authorization'] = f'Bearer {OPENAI_API_KEY}'
            url_ia, model = 'https://api.openai.com/v1/chat/completions', 'gpt-4o-mini'
        payload = {'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                   'max_tokens': 900, 'temperature': 0.4}
        resp  = requests.post(url_ia, headers=headers, json=payload, timeout=30)
        texto = resp.json()['choices'][0]['message']['content'].strip()
        texto = re.sub(r'```json|```', '', texto).strip()
        return json.loads(texto)
    except Exception as e:
        log(f"⚠️ Error IA metadatos: {e}", 'advertencia')
        titulo = descripcion[:60].strip()
        return {
            'titulo_seo': titulo, 'meta_descripcion': descripcion[:155],
            'categoria': detectar_tema(titulo, descripcion),
            'keyword_principal': titulo.split()[0] if titulo else 'noticia',
            'keywords_secundarias': [], 'contenido_html': f"<p>{descripcion}</p>"
        }

def procesar_pending_videos():
    """Detecta y publica videos manuales desde /pending_videos/ en GitHub."""
    if not WP_APP_PASSWORD:
        return
    estado = cargar_json(ESTADO_PENDING_PATH, {'procesados': {}})
    ahora  = datetime.now()

    # Eliminar archivos con +24h publicados
    for nombre, info in list(estado['procesados'].items()):
        fecha_pub = info.get('publicado_en')
        sha       = info.get('sha')
        if fecha_pub and sha:
            try:
                if ahora - datetime.fromisoformat(fecha_pub) > timedelta(hours=24):
                    if eliminar_archivo_github(nombre, sha):
                        del estado['procesados'][nombre]
                        guardar_json(ESTADO_PENDING_PATH, estado)
            except:
                pass

    archivos = listar_pending_videos_github()
    if not archivos:
        return

    for archivo in archivos:
        nombre = archivo.get('name', '')
        sha    = archivo.get('sha', '')
        if nombre in estado['procesados']:
            continue

        log(f"\n🎥 Nuevo video manual: {nombre}", 'info')
        contenido_txt = leer_archivo_github(archivo.get('download_url', ''))
        if not contenido_txt:
            continue

        datos = parsear_archivo_pending(contenido_txt)
        if not datos['descripcion'] or not datos['embed']:
            log(f"⚠️ {nombre} sin DESCRIPCION o EMBED válidos", 'advertencia')
            continue

        meta      = generar_metadatos_video_manual(datos['descripcion'], datos['embed'])
        titulo    = meta.get('titulo_seo', datos['descripcion'][:60])
        categoria = ajustar_categoria_por_cuota(meta.get('categoria', 'mundo'))
        meta_desc = meta.get('meta_descripcion', datos['descripcion'][:155])
        cuerpo    = meta.get('contenido_html', f"<p>{datos['descripcion']}</p>")

        articulos_rel = obtener_articulos_wp_recientes(2)
        html_rel      = generar_seccion_relacionados(articulos_rel)
        fecha_schema  = ahora.strftime('%Y-%m-%dT%H:%M:%S')
        titulo_schema = titulo.replace('"', "'")
        meta_schema   = meta_desc.replace('"', "'")
        schema = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"NewsArticle","headline":"{titulo_schema}",
"datePublished":"{fecha_schema}","description":"{meta_schema}",
"publisher":{{"@type":"Organization","name":"Verdad Hoy","url":"https://verdadhoy.com"}}}}
</script>"""

        contenido_final = f"""
{cuerpo}
<div style="margin:28px auto;text-align:center;max-width:267px;">
  {datos['embed']}
  <p style="font-size:0.8em;color:#888;margin-top:8px;">📹 Video: Verdad Hoy en Facebook</p>
</div>
{html_rel}
{schema}
"""
        cat_slug = CATEGORIA_WP.get(categoria, 'internacional')
        cat_id   = obtener_id_categoria_wp(cat_slug)
        tag_ids  = [tid for kw in meta.get('keywords_secundarias', [])[:5]
                    if (tid := obtener_crear_tag_wp(kw))]

        post_data = {
            'title': titulo, 'content': contenido_final, 'excerpt': meta_desc,
            'status': 'publish',
            'meta': {'_yoast_wpseo_title': titulo, '_yoast_wpseo_metadesc': meta_desc,
                     '_yoast_wpseo_focuskw': meta.get('keyword_principal', '')},
        }
        if cat_id:
            post_data['categories'] = [cat_id]
        if tag_ids:
            post_data['tags'] = tag_ids

        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
                              json=post_data, auth=(WP_USER, WP_APP_PASSWORD), timeout=20).json()
            if 'id' in r:
                url_wp = r.get('link', '')
                log(f"✅ Video manual publicado: {url_wp}", 'exito')
                registrar_cuota(categoria)
                estado['procesados'][nombre] = {
                    'publicado_en': ahora.isoformat(), 'sha': sha,
                    'wp_url': url_wp, 'wp_id': r['id']
                }
                guardar_json(ESTADO_PENDING_PATH, estado)

                # Pinterest para video manual
                if PINTEREST_TOKEN:
                    tableros   = obtener_tableros_pinterest()
                    nombre_tab = TABLEROS_PINTEREST.get(categoria, 'Noticias del Mundo')
                    board_id   = tableros.get(nombre_tab) or (list(tableros.values())[0] if tableros else None)
                    if board_id:
                        url_utm = f"{url_wp}?utm_source=pinterest&utm_medium=social&utm_campaign=video_manual"
                        payload = {
                            'board_id': board_id, 'title': titulo[:100],
                            'description': meta_desc[:490], 'link': url_utm,
                            'media_source': {'source_type': 'image_url',
                                             'url': f"{WP_URL}/wp-content/uploads/favicon_512.png"}
                        }
                        requests.post(
                            'https://api.pinterest.com/v5/pins',
                            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}',
                                     'Content-Type': 'application/json'},
                            json=payload, timeout=20
                        )
            else:
                log(f"❌ Error publicando video manual: {r.get('message','?')}", 'error')
        except Exception as e:
            log(f"❌ Excepción video manual: {e}", 'error')


# ──────────────────────────────────────────────────────────
# MAIN — FLUJO PRINCIPAL V12
# ──────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print(f"🌍 BOT DE NOTICIAS - {VERSION_BOT}")
    print("   WP: 6 arts/día, flujo general — SEO focus")
    print("   FB: imagen+texto desde verdadhoy.com (horario pico, independiente de WP)")
    print("   LATAM-FIRST: Chile 3/día + LATAM 3/día adicionales (V17.9.1 — total 12/día)")
    print("   RETENCIÓN: Box resumen + blockquote + pregunta cierre (target >2min)")
    print(f"   MODO: {'🌎 LATAM+CHILE' if MODO_LATAM else '🌐 GENERAL'}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── MODO LATAM: solo ejecuta bloque Chile+LATAM ──────────
    if MODO_LATAM:
        exito_cl, exito_la = publicar_bloque_latam_chile()
        return exito_cl or exito_la

    # ── MODO GENERAL (default) ───────────────────────────────
    # Procesar videos manuales (Función 3)
    procesar_pending_videos()

    # Decidir qué publicar
    publicar_wp = puede_publicar_wp()
    h = cargar_historial()
    publicar_fb = puede_publicar_fb(h)

    if not publicar_wp and not publicar_fb:
        log("⏱️ Nada que publicar — esperando próximo ciclo", 'info')
        return None

    log(f"📋 Tareas: WP={'SÍ' if publicar_wp else 'NO'} | FB={'SÍ' if publicar_fb else 'NO'}", 'info')

    exito_wp        = False
    exito_fb        = False
    url_articulo_wp = None

    # ══════════════════════════════════════════════════════
    # BLOQUE 1: PUBLICAR EN WORDPRESS
    # ══════════════════════════════════════════════════════
    if publicar_wp:
        # Recolectar noticias
        noticias = []
        if NEWS_API_KEY:
            noticias.extend(obtener_newsapi())
        if NEWSDATA_API_KEY:
            noticias.extend(obtener_newsdata())
        if GNEWS_API_KEY:
            noticias.extend(obtener_gnews())
        if len(noticias) < 15:
            log("⚠️ Pocas noticias — complementando con RSS", 'advertencia')
            noticias.extend(obtener_rss())

        if not noticias:
            log("ERROR: Ninguna fuente devolvió noticias", 'error')
        else:
            noticias = deduplicar_batch(noticias)
            noticias.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
            log(f"📰 Candidatas ordenadas: {len(noticias)}", 'info')

            # V17.6.9: Loop de publicación con reintentos.
            # Si una noticia falla al publicar (IA caída + fallback insuficiente),
            # se intenta con la SIGUIENTE candidata en vez de rendirse.
            candidatas_validas = []  # acumula (nt, contenido, img_path) listas para publicar

            seleccionada = None
            contenido    = None
            img_path     = None
            intentos     = 0
            MAX_PUBLICACIONES_INTENTOS = 5  # cuántas noticias intentar publicar antes de rendirse

            # Primero filtramos candidatas válidas (con contenido + imagen)
            for i, nt in enumerate(noticias):
                if intentos >= 60 or len(candidatas_validas) >= MAX_PUBLICACIONES_INTENTOS:
                    break
                url    = nt.get('url', '')
                titulo = nt.get('titulo', '')
                desc   = nt.get('descripcion', '')
                if not url or not titulo:
                    continue
                intentos += 1
                if intentos % 15 == 0:
                    h = cargar_historial()

                log(f"\n[{i+1}] Puntaje {nt.get('puntaje',0)} | {titulo[:55]}", 'debug')
                dup, razon = noticia_ya_publicada(h, url, titulo, desc)
                if dup:
                    log(f"   ❌ {razon}", 'debug')
                    continue
                if nt.get('puntaje', 0) < 3:
                    log(f"   ❌ Puntaje bajo ({nt.get('puntaje', 0)})", 'debug')
                    continue

                # V17.6.4: Filtro spam/apuestas/contenido promocional
                es_spam, keyword_spam = es_contenido_spam(titulo, desc)
                if es_spam:
                    log(f"   🚫 SPAM/APUESTAS detectado: '{keyword_spam}' — descartando", 'advertencia')
                    continue

                # Contenido
                # V17.9.3: umbrales subidos — 150-300 chars (2-3 oraciones) era
                # suficiente para "pasar" pero NO alcanza para que la IA escriba
                # un artículo con valor editorial real. Con fuentes tan cortas,
                # si la IA fallaba, el bot terminaba publicando esas 2-3 oraciones
                # casi textuales (ver fix del fallback sin IA, más abajo).
                cont_web, _ = extraer_contenido(url)
                if cont_web and len(cont_web) >= 500:
                    contenido_ok = cont_web
                elif desc and len(desc) >= 400:
                    contenido_ok = desc
                elif cont_web and len(cont_web) >= 250:
                    # Combinar web + desc para llegar a un mínimo real de sustancia
                    contenido_ok = cont_web + ' ' + desc if desc else cont_web
                else:
                    log("   ❌ Contenido insuficiente (<250 chars) — no hay material para un artículo real", 'advertencia')
                    continue

                # V17.9.6: segundo chequeo de spam/apuestas, ahora contra el
                # CONTENIDO COMPLETO (no solo título+descripción de la fuente).
                # Caso real que motivó esto: un artículo de cuotas de apuestas
                # para el Mundial con título genérico ("Cuotas y favoritos")
                # que no disparaba el filtro por título/desc, pero cuyo cuerpo
                # completo era 100% sobre casas de apuestas.
                es_spam2, kw_spam2 = es_contenido_spam(titulo, contenido_ok[:3000])
                if es_spam2:
                    log(f"   🚫 SPAM/APUESTAS detectado en el contenido: '{kw_spam2}' — descartando", 'advertencia')
                    continue

                # Imagen — OBLIGATORIA
                imagen_encontrada = None
                if nt.get('imagen'):
                    imagen_encontrada = descargar_imagen(nt['imagen'])
                if not imagen_encontrada:
                    img_url = extraer_imagen_web(url)
                    if img_url:
                        imagen_encontrada = descargar_imagen(img_url)
                if not imagen_encontrada:
                    # Solo como último recurso absoluto — imagen Discover 1600x900
                    tema_fallback = detectar_tema(titulo, desc)
                    imagen_encontrada = crear_imagen_titulo(titulo, tema_fallback)
                if not imagen_encontrada:
                    log("   ❌ Sin imagen — descartando noticia", 'advertencia')
                    continue

                log("   ✅ Noticia válida con imagen")
                candidatas_validas.append((nt, contenido_ok, imagen_encontrada))

            if not candidatas_validas:
                log("ERROR: No se encontró noticia válida con imagen", 'error')
            else:
                # V17.6.9: Intentar publicar las candidatas en orden hasta que una tenga éxito
                for idx_pub, (nt_pub, cont_pub, img_pub) in enumerate(candidatas_validas):
                    log(f"\n📝 SELECCIONADA ({idx_pub+1}/{len(candidatas_validas)}): {nt_pub['titulo'][:70]}")
                    # V16: detectar_tema() es solo la pista inicial para la IA.
                    # La categoría definitiva la decide la IA al leer el contenido completo.
                    tema_sugerido = detectar_tema(nt_pub['titulo'], nt_pub.get('descripcion', ''))
                    tema_sugerido = ajustar_categoria_por_cuota(tema_sugerido)
                    log(f"   Categoría sugerida (keywords): {tema_sugerido} — la IA decidirá la final", 'info')

                    url_articulo_wp = publicar_en_wordpress(
                        titulo       = nt_pub['titulo'],
                        contenido    = cont_pub,
                        tema         = tema_sugerido,
                        imagen_path  = img_pub,
                        fuente_url   = nt_pub['url'],
                        fecha_fuente = nt_pub.get('fecha'),
                        fuente_noticia = nt_pub.get('fuente', ''),
                    )

                    if url_articulo_wp:
                        # Éxito — fijar como seleccionada y continuar con Pinterest/historial
                        seleccionada = nt_pub
                        contenido    = cont_pub
                        img_path     = img_pub
                        exito_wp = True
                        guardar_estado_wp()
                        registrar_cuota(tema_sugerido)
                        h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1

                        # ── Pinterest en paralelo con WP ───────────────
                        if PINTEREST_TOKEN:
                            log("\n📌 Publicando en Pinterest...", 'info')
                            ok_pt = publicar_pinterest(
                                titulo       = seleccionada['titulo'],
                                descripcion  = contenido[:490],
                                url_articulo = url_articulo_wp,
                                img_path     = img_path,
                                categoria    = tema_sugerido,
                            )
                            if ok_pt:
                                h['estadisticas']['total_pinterest'] = h['estadisticas'].get('total_pinterest', 0) + 1

                        # Guardar en historial
                        desc_completa = (seleccionada.get('descripcion', '') + ' ' + contenido[:400]).strip()
                        h = guardar_en_historial(h, seleccionada['url'], seleccionada['titulo'], desc_completa)

                        # Limpiar imagen temporal WP de la publicada
                        try:
                            if img_path and os.path.exists(img_path):
                                os.remove(img_path)
                        except:
                            pass
                        break  # publicación exitosa — salir del loop de reintentos
                    else:
                        # Falló esta candidata — limpiar su imagen y probar la siguiente
                        log(f"   ⚠️ No se pudo publicar esta noticia — probando siguiente candidata", 'advertencia')
                        try:
                            if img_pub and os.path.exists(img_pub):
                                os.remove(img_pub)
                        except:
                            pass
                        continue

                # Limpiar imágenes temporales de candidatas no usadas
                for _, _, img_sobrante in candidatas_validas:
                    try:
                        if img_sobrante and os.path.exists(img_sobrante):
                            os.remove(img_sobrante)
                    except:
                        pass

                if not exito_wp:
                    log("⚠️ Ninguna de las candidatas se pudo publicar (IA caída o contenido insuficiente)", 'advertencia')

    # ══════════════════════════════════════════════════════
    # BLOQUE 2: PUBLICAR EN FACEBOOK — imagen+texto desde WP
    # ══════════════════════════════════════════════════════
    if publicar_fb:
        log("\n📘 Publicando en Facebook (imagen + texto desde verdadhoy.com)...", 'info')
        h = cargar_historial()  # Recargar historial actualizado

        articulo_fb = obtener_articulo_wp_para_facebook(h)

        if not articulo_fb:
            log("⚠️ FB: no hay artículo válido con imagen en WP para publicar", 'advertencia')
        else:
            # Detectar categoría del artículo para CTA y hashtags
            tema_fb = detectar_tema(articulo_fb['titulo'], articulo_fb.get('excerpt', ''))

            texto_fb = construir_texto_facebook(
                titulo    = articulo_fb['titulo'],
                excerpt   = articulo_fb['excerpt'],
                url_wp    = articulo_fb['link'],
                categoria = tema_fb,
            )

            # Descargar imagen del artículo
            img_fb_path = descargar_imagen_para_fb(articulo_fb['imagen_url'])

            if not img_fb_path:
                log("❌ FB: no se pudo descargar imagen del artículo WP", 'error')
            else:
                exito_fb = publicar_facebook_imagen(
                    titulo     = articulo_fb['titulo'],
                    texto      = texto_fb,
                    imagen_path = img_fb_path,
                )
                if exito_fb:
                    guardar_estado_fb()
                    h = registrar_fb_publicado(h, articulo_fb['id'], articulo_fb['link'])
                    h['estadisticas']['total_fb'] = h['estadisticas'].get('total_fb', 0) + 1
                    guardar_json(HISTORIAL_PATH, h)
                    log(f"✅ FB publicado: {articulo_fb['titulo'][:55]}", 'exito')

                # Limpiar imagen FB
                try:
                    if img_fb_path and os.path.exists(img_fb_path):
                        os.remove(img_fb_path)
                except:
                    pass

    # Resumen final
    h = cargar_historial()
    stats = h.get('estadisticas', {})
    estado_latam = cargar_estado_latam()
    cuotas_hoy = cargar_cuotas_hoy()
    total_wp_hoy = sum(int(v) for v in cuotas_hoy.get('conteo', {}).values())
    log(f"\n{'='*50}", 'info')
    log(f"✅ RESUMEN {VERSION_BOT}:", 'exito')
    log(f"   WP hoy: {total_wp_hoy}/{MAX_POSTS_WP_DIA} artículos publicados", 'info')
    log(f"   Total acumulado: {stats.get('total_publicadas', 0)}", 'info')
    log(f"   WordPress: {stats.get('total_wp', 0)}", 'info')
    log(f"   Facebook:  {stats.get('total_fb', 0)}", 'info')
    log(f"   Pinterest: {stats.get('total_pinterest', 0)}", 'info')
    log(f"   Chile hoy: {estado_latam.get('chile',0)}/{MAX_POSTS_WP_DIA_CHILE}", 'info')
    log(f"   LATAM hoy: {estado_latam.get('latam',0)}/{MAX_POSTS_WP_DIA_LATAM}", 'info')
    log(f"   Esta ejecución → WP={'✅' if exito_wp else '❌'} | FB={'✅' if exito_fb else '❌'}", 'info')

    if exito_wp or exito_fb:
        log("💡 Hacer git push de los JSON de estado (incluyendo estado_cuotas.json)", 'advertencia')
        return True
    return False


if __name__ == "__main__":
    try:
        resultado = main()
        # V17.9.4 FIX: antes, si main() devolvía False (nada publicado en este
        # ciclo — ej. sin créditos de IA, sin candidatas válidas, cuota ya
        # llena) el script salía con exit(1), marcando la corrida de GitHub
        # Actions como "fallida" en rojo aunque no hubiera ningún error real.
        # Los errores DE VERDAD (excepciones) ya se capturan abajo y ahí sí
        # corresponde exit(1). "No publiqué nada esta vez" no es un fallo del
        # workflow — es un resultado normal y se ve reflejado en los logs.
        exit(0)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
