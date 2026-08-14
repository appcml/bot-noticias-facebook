#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales - V18.0.0
CAMBIOS EN V18.0.0 (Rediseño: máximo 6 noticias/día, rotación de categorías,
prioridad evergreen/SEO duradero — a pedido de Cic):
  - TOPE DIARIO GLOBAL: antes había TRES contadores separados (6 general +
    3 Chile + 3 LATAM = 12/día repartidos en dos flujos de ejecución
    distintos, MODO_LATAM=true/false). Ahora hay UN SOLO tope diario real:
    MAX_POSTS_WP_DIA = 6, compartido por TODAS las fuentes (general, Chile,
    LATAM). MAX_POSTS_WP_DIA_TOTAL también baja a 6 (antes 12) y pasa a ser
    el mismo número, ya no una suma de sub-cupos.
  - FLUJO ÚNICO: las fuentes RSS/NewsAPI dedicadas de Chile y LATAM
    (obtener_rss_chile, obtener_newsapi_chile, obtener_rss_latam,
    obtener_newsapi_latam) ahora se integran directamente al pool general
    de candidatas en main(), en vez de vivir en un bloque de publicación
    aparte (publicar_bloque_latam_chile, que queda sin usarse por defecto
    pero se mantiene en el código por compatibilidad). calcular_puntaje()
    ya da bonus fuerte por país LATAM/Chile (V17.9.0), así que Latinoamérica
    sigue bien representada sin necesitar un cupo separado.
  - MODO_LATAM: si la variable de entorno todavía está en 'true' (de un
    cron viejo en GitHub Actions), el bot ya NO ejecuta el bloque separado
    — loguea un aviso y sigue con el flujo único. El .yml puede simplificarse
    a un solo cron; ya no hace falta el segundo horario para LATAM.
  - ROTACIÓN DE CATEGORÍAS: nueva lista CATEGORIAS_ROTACION_WP con las 15
    categorías reales del menú del sitio (Política, África, Asia, Ciencia y
    Salud, Deportes, Economía, Entretenimiento, Europa, Internacional,
    Latinoamérica, Medio Ambiente, Medio Oriente, Mundo, Oceanía,
    Tecnología). Nueva función categorias_usadas_hoy() lee qué categorías
    ya se publicaron hoy (mismo contador que el tope de 6/día). Antes de
    publicar, main() reordena las candidatas válidas para preferir SIEMPRE
    una categoría todavía no usada hoy — con 6 cupos y 15 categorías, el
    bot nunca debería repetir categoría en un mismo día salvo que ya se
    hayan usado las 15 (imposible con tope 6).
  - NUEVA FUNCIÓN resolver_categoria_wp(): centraliza la lógica de mapeo
    categoría-editorial → slug real de WordPress (antes estaba duplicada
    dentro de publicar_en_wordpress). Se usa tanto para ESTIMAR la
    categoría final antes de publicar (rotación) como para el valor real
    dentro de publicar_en_wordpress, que ahora la reutiliza en vez de
    repetir la lógica.
  - publicar_en_wordpress() ahora devuelve (url, slug_categoria_final) en
    vez de solo url — para que main() pueda registrar la cuota diaria
    usando la categoría REAL asignada (después de que la IA clasifique y
    se resuelva la región), no solo la sugerencia previa por keywords.
  - EVERGREEN / SEO DURADERO: a pedido explícito de Cic — "prefiero que
    sean noticias que perduren a que sean noticias que pasan rápido":
      1. calcular_puntaje() suma un nuevo bonus_durabilidad: +10 si el tema
         es tecnología/ciencia/salud/medio ambiente (evergreen alto),
         +5 si es economía/educación (evergreen medio), -4 si es guerra/
         desastre/crimen (noticias que envejecen rápido en valor de
         búsqueda, aunque sigan siendo noticia legítima del día).
      2. validar_calidad_articulo() ahora exige el estándar evergreen
         COMPLETO (mínimo 620 palabras, 4+ transiciones, meta 120-170
         chars, blockquote, 4 H2) en TODOS los artículos, no solo en
         ciencia/tecnología/salud/medio ambiente como antes — con solo 6
         publicaciones al día, se prioriza calidad y permanencia sobre
         volumen en todas las categorías.
  - NO DUPLICADOS: sin cambios — el sistema de historial
    (noticia_ya_publicada / guardar_en_historial) ya impedía repetir una
    noticia ya publicada; se mantiene igual.
Bot de Noticias Internacionales - V17.9.29
CAMBIOS EN V17.9.29 (IA expande con conocimiento propio cuando la fuente es corta):
  - PROBLEMA RAÍZ IDENTIFICADO: cuando la fuente tenía 300 palabras, la IA
    parafraseaba esas 300 palabras y entregaba 400-500. No rechazaba, solo
    quedaba corto. La solución no es rechazar más — es que la IA entienda
    que debe CREAR contenido de 650 palabras independiente del tamaño de la fuente.
  - FIX PROMPT: nueva sección "REGLA CRÍTICA DE EXTENSIÓN" al inicio del prompt
    (antes del contenido) que explica: fuente de 300 palabras → artículo de 650.
    Cinco técnicas concretas de expansión: antecedente histórico, cifras de
    contexto, impacto LATAM, reacciones, próximos pasos.
  - FIX REINTENTO PALABRAS: cuando el validador detecta <600 palabras y activa
    el reintento, el feedback ahora da 4 instrucciones literales específicas:
    añadir párrafo de antecedente, párrafo de cifras, párrafo de impacto LATAM,
    y desarrollar cada dato del contexto web en 2-3 oraciones.
  - LÓGICA: el validador sigue exigiendo 600/650 palabras PERO el fallo activa
    REINTENTO (REINTENTAR_CALIDAD_IA=True), no descarte. Así noticias con fuentes
    cortas siempre tienen una segunda oportunidad de llegar a 600 palabras.
CAMBIOS HISTÓRICOS V17.9.28 A V12 (resumidos — el detalle completo de cada
versión histórica se conserva en el control de versiones / respaldo del
archivo original; se condensa aquí para mantener el archivo enfocado en el
comportamiento vigente):
  - V17.9.28: enlace externo dofollow a la fuente, power word validada en
    código, imagen title/alt = keyword exacta, mínimo 600/650 palabras.
  - V17.9.27: título SEO 55 chars, power word + número en título, imagen
    con keyword, logging de título SEO.
  - V17.9.26: fix de doble truncado de títulos, slug SEO limpio
    (generar_slug_seo), imagen usa titulo_final en vez de titulo bruto.
  - V17.9.11 a V17.9.25: fixes de fuentes RSS de Chile caídas, reintentos de
    conexión, distribución por subcategorías reales de "Internacional"
    (Europa/Asia/África/Medio Oriente/Oceanía/Mundo), eliminación de
    "América del Norte" como categoría (bajo volumen), desastres/guerra/
    crimen en LATAM reclasificados a "Latinoamérica", filtro anti-apuestas
    reforzado (título+desc y contenido completo), Groq/Gemini como
    proveedores de IA gratuitos con Groq→OpenRouter→OpenAI→Gemini de
    respaldo, eliminación del fallback "sin IA" que publicaba contenido
    pobre, aumento progresivo de mínimos de contenido y palabras, búsqueda
    web real (Tavily) para enriquecer artículos con datos verificables,
    validación de calidad en código con reintento guiado por feedback,
    keywords SEO por categoría y mejora de títulos genéricos.
  - V17.6 a V17.8: pivot editorial completo a medio de referencia LATAM
    (cuotas por país/tema, penalización de ruido doméstico de España,
    box resumen "en 30 segundos", estructura de 4 H2, reglas Yoast/Rank
    Math, filtro de contenido spam/apuestas, fix de clasificación por
    categoría temática antes que geográfica).
  - V17.0 a V17.5: ampliación de fuentes (NewsAPI/NewsData/GNews/RSS),
    cuotas editoriales iniciales, aumento de cupos Chile/LATAM (luego
    revertido en V17.9.1 al notar que 82/día no era sostenible).
  - V12 a V16: bot original — publicación en WordPress con imagen
    obligatoria, clasificación por IA con fallback a keywords, schema
    JSON-LD NewsArticle, integración Pinterest y Facebook (Facebook
    desactivado desde V17.9.17 por decisión del usuario), video manual vía
    /pending_videos/ en GitHub, anti-duplicados por historial.
"""
# ── VERSIÓN DEL BOT (única fuente de verdad — actualizar solo aquí) ──
VERSION_BOT = "V18.0.0"
import requests
import feedparser
import re
import hashlib
import json
import os
import random
import time
import unicodedata
from datetime import datetime, timedelta, timezone
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
GEMINI_API_KEY      = os.getenv('GEMINI_API_KEY', '')     # V17.9.14: 2do proveedor gratuito (tier diario más generoso que Groq)
TAVILY_API_KEY      = os.getenv('TAVILY_API_KEY', '')     # V17.9.20: búsqueda web real para enriquecer artículos (1000 créditos/mes gratis)
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
ESTADO_LATAM_PATH   = 'estado_cuotas_latam.json'   # V17.3: cuotas Chile+LATAM independientes (deprecado, ver nota V18.0 más abajo)
# ── V17.3: Modo de ejecución ──────────────────────────────
# MODO_LATAM=true  → (histórico) solo ejecutaba el bloque Chile+LATAM aparte
# MODO_LATAM=false → flujo general (default)
# V18.0: MODO_LATAM ya NO cambia el comportamiento del bot — el bloque
# Chile+LATAM se fusionó al flujo único (ver publicar_bloque_latam_chile()
# y el aviso en main()). Se conserva la variable solo para no romper un
# .yml de GitHub Actions que todavía la esté seteando.
MODO_LATAM = os.getenv('MODO_LATAM', 'false').lower() == 'true'
# Tiempos
# V17.9.1: con MAX_POSTS_WP_DIA=6, 230 min (~3h50) reparte las 6 notas a lo
# largo de las 24 horas (24h / 6 = 4h, con margen). V18.0: se mantiene igual
# — el tope de 6 ya no cambia, solo se unificó quién compite por esos 6 cupos.
TIEMPO_ENTRE_WP_MIN = 230
TIEMPO_ENTRE_FB_MIN = 90   # 1.5 horas mínima entre posts de Facebook
# Límites diarios
# V18.0: REDISEÑO A PEDIDO DE CIC — máximo 6 noticias/día en TODO el sitio,
# un solo contador global. Antes existían 3 contadores separados (6 general
# + 3 Chile + 3 LATAM = 12/día) que corrían en dos flujos de ejecución
# distintos (MODO_LATAM true/false) sin compartir tope real. Ahora todas las
# fuentes (general + Chile + LATAM, ver main()) alimentan el mismo pool de
# candidatas y compiten por los mismos 6 cupos/día, priorizando: 1) más
# puntaje (importancia + LATAM/Chile + durabilidad SEO), 2) categoría no
# usada todavía hoy (rotación, ver CATEGORIAS_ROTACION_WP más abajo).
MAX_POSTS_FB_DIA        = 4    # Máximo 4 posts/día en Facebook (deshabilitado, ver PUBLICAR_EN_FACEBOOK)
MAX_POSTS_WP_DIA        = 6    # ÚNICO tope diario real — todas las categorías compiten por estos 6 cupos
MAX_POSTS_WP_DIA_CHILE  = 3    # V18.0: ya NO se usa en el flujo principal — se deja solo por si se invoca
MAX_POSTS_WP_DIA_LATAM  = 3    # manualmente publicar_bloque_latam_chile() aparte del flujo único (no recomendado)
MAX_POSTS_WP_DIA_TOTAL  = 6    # V18.0: mismo valor que MAX_POSTS_WP_DIA — ya no es una suma de sub-cupos
# V17.9.19: OpenAI (de pago, saldo real) primero en la cascada de IA — más
# confiable que los proveedores gratuitos que se saturan a media tarde.
REINTENTAR_CALIDAD_IA   = True
# V17.9.17: Interruptor maestro de Facebook — DESACTIVADO por solicitud del
# usuario. Las funciones de Facebook siguen intactas en el código, solo no
# se llaman mientras esto sea False.
PUBLICAR_EN_FACEBOOK    = False
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
# ── V18.0: LAS 15 CATEGORÍAS REALES DEL MENÚ — usadas para la ROTACIÓN ────
# diaria (a pedido de Cic: "que vaya alternando categorías"). Con un tope de
# 6 noticias/día y 15 categorías posibles, el bot debería poder cubrir 6
# categorías distintas cada día sin repetir ninguna. Ver categorias_usadas_hoy()
# y resolver_categoria_wp() más abajo.
CATEGORIAS_ROTACION_WP = [
    'politica', 'africa', 'asia', 'ciencia-y-salud', 'deportes', 'economia',
    'entretenimiento', 'europa', 'internacional', 'latinoamerica',
    'medio-ambiente', 'medio-oriente', 'mundo', 'oceania', 'tecnologia',
]
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
BLACKLIST_CONTENIDO_SPAM = [
    # Casas de apuestas / gambling — alto riesgo desmonetización AdSense
    "rojabet", "bet365", "1xbet", "betano", "codere", "tómbola", "tombola",
    "sportingbet", "bwin", "pokerstars", "888casino", "betfair", "unibet",
    "casino online", "apuestas deportivas", "apuestas en línea", "apuestas en linea",
    "bono de bienvenida casino", "bono sin depósito", "bono sin deposito",
    "giros gratis casino", "tragamonedas", "tragaperras", "ruleta online",
    "poker online", "blackjack online", "slots online", "juegos de azar",
    "casa de apuestas", "casas de apuestas", "cuotas de apuestas", "pronósticos deportivos pagos",
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
    # ── Prioridad 8: Medio ambiente / Clima (ANTES de ciencia)
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
    # ── Prioridad 10: Ciencia / Espacio
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
def categoria_disponible(categoria, total_dia=MAX_POSTS_WP_DIA):
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
# V18.0: RESOLUCIÓN DE CATEGORÍA FINAL DE WORDPRESS + ROTACIÓN DIARIA
# ──────────────────────────────────────────────────────────
def resolver_categoria_wp(categoria_editorial, titulo, texto_analisis):
    """
    V18.0: dado el resultado de clasificación editorial (la categoría interna
    tipo 'guerra', 'crimen', 'desastre', 'religion', 'educacion', 'general',
    'mundo', 'latinoamerica', 'deportes', 'economia', 'tecnologia',
    'entretenimiento', 'politica', 'ciencia', 'salud', 'medio_ambiente',
    'clima'), devuelve el slug FINAL de WordPress — una de las 15 categorías
    reales del menú del sitio (ver CATEGORIAS_ROTACION_WP): politica, africa,
    asia, ciencia-y-salud, deportes, economia, entretenimiento, europa,
    internacional, latinoamerica, medio-ambiente, medio-oriente, mundo,
    oceania, tecnologia.
    Centraliza la lógica que antes estaba duplicada dentro de
    publicar_en_wordpress() (V17.9.8/9.9). Se usa en DOS momentos:
      1. ANTES de publicar, para ESTIMAR la categoría final de cada
         candidata y así poder rotar entre categorías (ver
         categorias_usadas_hoy() y el reordenamiento en main()).
      2. DENTRO de publicar_en_wordpress(), para el valor real que se usa
         al crear el post (reemplaza el bloque que antes estaba repetido
         ahí mismo).
    """
    categorias_internacional_paraguas = {'desastre', 'guerra', 'crimen', 'religion', 'educacion', 'general', 'mundo'}
    if categoria_editorial in categorias_internacional_paraguas:
        texto_chk = f"{titulo} {texto_analisis}".lower()
        es_latam = (
            any(kw in texto_chk for kw in KEYWORDS_CHILE) or
            any(kw in texto_chk for kws in KEYWORDS_LATAM_PAISES.values() for kw in kws)
        )
        if es_latam:
            return 'latinoamerica'
        region = detectar_region_internacional(titulo, texto_analisis)
        return REGION_SLUG_WP.get(region, 'internacional')
    return CATEGORIA_WP.get(categoria_editorial, 'internacional')
def categorias_usadas_hoy():
    """
    V18.0: devuelve el set de slugs de WordPress (de las 15 categorías reales
    del menú, ver CATEGORIAS_ROTACION_WP) que YA se publicaron hoy — se lee
    del mismo contador que controla el tope de 6/día (estado_cuotas.json),
    ahora registrado con la categoría FINAL (post-IA, post-región) en vez de
    la sugerencia previa por keywords.
    Con un tope de 6 noticias/día y 15 categorías posibles, el bot nunca
    debería repetir categoría en el mismo día — esta función es la que
    permite a main() comprobarlo y priorizar categorías todavía sin usar.
    """
    datos = cargar_cuotas_hoy()
    return {c for c, n in datos.get('conteo', {}).items() if int(n) > 0 and c in CATEGORIAS_ROTACION_WP}
# ──────────────────────────────────────────────────────────
# REESCRITURA CON IA (SEO avanzado)
# ──────────────────────────────────────────────────────────
KEYWORDS_SEO_CATEGORIA = {
    'latinoamerica': {
        'principal':   'noticias Latinoamérica',
        'secundarias': ['América Latina hoy', 'últimas noticias LATAM', 'sucesos latinoamericanos'],
        'modificadores': ['crece la tensión', 'anuncia', 'aprueba reforma', 'genera crisis', 'impacta la región'],
    },
    'chile': {
        'principal':   'noticias Chile',
        'secundarias': ['últimas noticias Chile', 'actualidad Chile', 'sucesos Chile hoy'],
        'modificadores': ['Gobierno de Chile', 'Boric anuncia', 'Congreso aprueba', 'impacta a los chilenos'],
    },
    'economia': {
        'principal':   'economía',
        'secundarias': ['dólar hoy', 'inflación', 'mercados financieros', 'crisis económica'],
        'modificadores': ['sube', 'cae', 'reforma económica', 'impacto económico', 'afecta el bolsillo'],
    },
    'politica': {
        'principal':   'política',
        'secundarias': ['gobierno', 'elecciones', 'congreso', 'presidente anuncia'],
        'modificadores': ['anuncia', 'aprueba', 'reforma', 'decreto presidencial', 'genera polémica'],
    },
    'tecnologia': {
        'principal':   'tecnología',
        'secundarias': ['inteligencia artificial', 'innovación', 'startups', 'IA'],
        'modificadores': ['revoluciona', 'lanza', 'presenta', 'cambia todo', 'transforma'],
    },
    'deportes': {
        'principal':   'deportes',
        'secundarias': ['fútbol', 'Copa Libertadores', 'eliminatorias', 'Mundial 2026'],
        'modificadores': ['gana', 'pierde', 'clasifica', 'sorprende', 'histórico'],
    },
    'entretenimiento': {
        'principal':   'entretenimiento',
        'secundarias': ['música latina', 'cine', 'series', 'artistas'],
        'modificadores': ['lanza', 'estrena', 'conquista', 'sorprende', 'regresa'],
    },
    'salud': {
        'principal':   'salud',
        'secundarias': ['medicina', 'vacuna', 'tratamiento', 'OMS'],
        'modificadores': ['alerta', 'descubre', 'recomienda', 'advierte', 'avanza'],
    },
    'ciencia': {
        'principal':   'ciencia',
        'secundarias': ['descubrimiento', 'investigación', 'espacio', 'NASA'],
        'modificadores': ['descubre', 'confirma', 'revela', 'sorprende', 'avanza'],
    },
    'medio_ambiente': {
        'principal':   'medio ambiente',
        'secundarias': ['cambio climático', 'Amazonía', 'glaciares', 'energía renovable'],
        'modificadores': ['alerta', 'amenaza', 'protege', 'destruye', 'impacta'],
    },
    'guerra': {
        'principal':   'conflicto',
        'secundarias': ['guerra', 'bombardeo', 'tropas', 'crisis militar'],
        'modificadores': ['escala', 'ataca', 'avanza', 'amenaza', 'cesan fuegos'],
    },
    'mundo': {
        'principal':   'noticias internacionales',
        'secundarias': ['noticias del mundo', 'actualidad global', 'internacional'],
        'modificadores': ['sacude al mundo', 'impacta globalmente', 'genera debate', 'histórico'],
    },
}
def obtener_keyword_categoria(categoria):
    """V17.9.25: Devuelve la keyword principal de una categoría."""
    return KEYWORDS_SEO_CATEGORIA.get(categoria, {}).get('principal', '')
def generar_slug_seo(titulo, max_palabras=8):
    """
    V17.9.26: Genera un slug SEO limpio desde el título del artículo.
    """
    STOPWORDS_SLUG = {
        'de','del','la','las','el','los','un','una','unos','unas',
        'y','e','o','u','a','al','en','por','para','con','sin',
        'que','se','su','sus','es','son','ha','han','fue','era',
        'lo','le','les','me','te','nos','ante','bajo','desde',
        'hacia','hasta','sobre','tras','entre','como','pero',
        'si','no','ni','ya','aun','aunque','sino'
    }
    if not titulo:
        return ''
    nfkd = unicodedata.normalize('NFKD', titulo)
    sin_acentos = ''.join(c for c in nfkd if not unicodedata.combining(c))
    texto = sin_acentos.lower()
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    palabras = [p for p in texto.split() if p not in STOPWORDS_SLUG and len(p) > 2]
    palabras = palabras[:max_palabras]
    slug = '-'.join(palabras)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')
    return slug
def mejorar_titulo_seo(titulo_original, categoria):
    """
    V17.9.25: Enriquece un título genérico con keyword + modificador contextual.
    """
    if not titulo_original or len(titulo_original.strip()) < 5:
        return titulo_original
    kw_data  = KEYWORDS_SEO_CATEGORIA.get(categoria, {})
    principal = kw_data.get('principal', '').lower()
    if principal and principal in titulo_original.lower():
        return titulo_original
    if len(titulo_original) >= 52:
        return titulo_original
    modificadores = kw_data.get('modificadores', [])
    if not modificadores:
        return titulo_original
    modificador = random.choice(modificadores)
    titulo_mejorado = f"{titulo_original}: {modificador}"
    if len(titulo_mejorado) > 70:
        return titulo_original
    return titulo_mejorado
PALABRAS_TRANSICION = [
    'sin embargo', 'además', 'por otro lado', 'en consecuencia', 'a su vez',
    'no obstante', 'por ejemplo', 'en primer lugar', 'finalmente', 'asimismo',
    'por lo tanto', 'en efecto', 'por su parte', 'en tanto', 'de hecho',
    'en este sentido', 'como resultado', 'en cambio', 'cabe destacar',
    'mientras tanto', 'por consiguiente', 'en última instancia', 'en tal caso',
    'aunque', 'aun así', 'pese a', 'a pesar de', 'de esta manera', 'de este modo',
    'en ese sentido', 'en esa línea', 'en la misma línea', 'bajo este escenario',
    'en ese contexto', 'en este marco', 'eso sí', 'cabe mencionar', 'vale destacar',
    'a la vez', 'al mismo tiempo', 'dado que', 'ya que', 'debido a esto',
    'por su lado', 'de igual forma', 'de igual manera', 'en definitiva',
]
INICIOS_META_PROHIBIDOS = ('descubre', 'conoce', 'entérate', 'entera', 'sabías')
CATEGORIAS_EVERGREEN = {'ciencia', 'tecnologia', 'medio_ambiente', 'salud'}
def validar_calidad_articulo(contenido_html, meta_desc, titulo_seo='', categoria=''):
    """
    V17.9.12: Verificación EN CÓDIGO (no solo en el prompt) de las reglas de
    calidad que se venían comprobando a mano en la revisión editorial manual.
    V18.0: con el tope bajado a 6 noticias/día (a pedido de Cic, que
    prefiere "noticias que perduren a que pasen rápido"), se exige el
    estándar EVERGREEN COMPLETO en TODOS los artículos — antes solo se
    exigía en ciencia/tecnología/salud/medio ambiente (V17.9.23) y el resto
    tenía un piso más bajo (350 palabras, sin exigir transiciones ni meta
    exacta). Con solo 6 publicaciones/día, prioriza calidad y permanencia
    SEO sobre volumen en absolutamente todas las categorías.
    Devuelve (es_valido: bool, problemas: list[str]).
    """
    problemas = []
    # V18.0: antes dependía de si categoria estaba en CATEGORIAS_EVERGREEN;
    # ahora siempre se exige el estándar más alto, en todas las categorías.
    es_evergreen = True
    minimo_palabras = 620 if es_evergreen else 600
    texto_plano = re.sub(r'<[^>]+>', ' ', contenido_html or '')
    texto_plano = re.sub(r'\s+', ' ', texto_plano).strip()
    n_palabras = len(texto_plano.split())
    if n_palabras < minimo_palabras:
        problemas.append(
            f"El artículo tiene solo {n_palabras} palabras — el mínimo exigido es {minimo_palabras}. "
            "Desarrolla más cada sección con datos concretos, no rellenes con frases genéricas."
        )
    if '<blockquote' not in (contenido_html or ''):
        problemas.append(
            "Falta el elemento 'Dato destacado' (bloque <blockquote>) — es obligatorio. "
            "Incluye una cita textual o el dato estadístico más impactante del artículo."
        )
    n_h2 = len(re.findall(r'<h2', contenido_html or '', flags=re.IGNORECASE))
    if n_h2 < 4:
        problemas.append(
            f"El artículo tiene solo {n_h2} subtítulos H2 — el mínimo exigido es 4, "
            "cada uno con un ángulo distinto del tema."
        )
    if es_evergreen:
        texto_lower = texto_plano.lower()
        n_transiciones = sum(1 for palabra in PALABRAS_TRANSICION if palabra in texto_lower)
        if n_transiciones < 4:
            problemas.append(
                f"Solo se detectaron {n_transiciones} palabras de transición — el mínimo es 4 "
                "(sin embargo, además, por otro lado, en consecuencia, asimismo, por ejemplo, etc.)."
            )
        meta_desc_chk = meta_desc or ''
        len_meta = len(meta_desc_chk)
        if len_meta < 120 or len_meta > 170:
            problemas.append(
                f"La meta descripción tiene {len_meta} caracteres — debe estar entre 130 y 160. "
                "Ajústala sin cortar palabras a la mitad."
            )
    meta_desc = meta_desc or ''
    if meta_desc.strip().lower().startswith(INICIOS_META_PROHIBIDOS):
        problemas.append(
            "La meta descripción empieza con una palabra prohibida "
            "('descubre', 'conoce', 'entérate'...). Empieza con el dato o el hecho real."
        )
    POWER_WORDS_ES = {
        'clave','crucial','decisivo','decisiva','histórico','histórica',
        'alerta','récord','record','oficial','confirmado','confirmada',
        'sorprendente','revolucionario','revolucionaria','explosivo','explosiva',
        'inesperado','inesperada','urgente','impactante','revelador','reveladora',
        'inédito','inédita','definitivo','definitiva','polémico','polémica',
        'esencial','crítico','crítica','exclusivo','exclusiva','extraordinario',
        'extraordinaria','primero','primera','único','única','máximo','mínimo',
        'grave','vital','histórico','nueva','nuevo','mejor','peor','mayor','menor',
        'real','verdad','secreto','secretos','brutal','radical','total','final',
        'absoluto','absoluta','masivo','masiva','sin precedentes','millones',
        'millonario','millonaria','récord','logra','logró','conquista','conquista',
    }
    if titulo_seo:
        titulo_lower = titulo_seo.lower()
        tiene_power_word = any(pw in titulo_lower for pw in POWER_WORDS_ES)
        if not tiene_power_word:
            problemas.append(
                f"El título SEO '{titulo_seo}' no contiene ninguna power word. "
                "Añade al menos una: clave, crucial, decisivo, histórico, récord, oficial, "
                "confirmado, revelador, urgente, exclusivo, sin precedentes, etc."
            )
    return (len(problemas) == 0, problemas)
def buscar_contexto_web(titulo, max_resultados=3):
    """
    V17.9.20: búsqueda web REAL (Tavily) para enriquecer artículos con datos
    verificables. Devuelve lista de dicts {"title","url","content"} (puede
    ser vacía si no hay TAVILY_API_KEY, si falla o no hay resultados).
    """
    if not TAVILY_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": titulo,
                "search_depth": "basic",
                "max_results": max_resultados,
                "include_answer": False,
            },
            timeout=15,
        )
        data = resp.json()
        resultados = data.get("results", [])
        if not resultados:
            log(f"🔎 Tavily: sin resultados para '{titulo[:60]}'", 'debug')
            return []
        log(f"🔎 Tavily: {len(resultados)} fuente(s) encontrada(s) para contexto adicional", 'info')
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content", "") or "")[:600],
            }
            for r in resultados
        ]
    except Exception as e:
        log(f"⚠️ Tavily: búsqueda falló ({e}) — se continúa sin contexto adicional", 'advertencia')
        return []
def reescribir_noticia_v9(titulo, contenido, categoria_sugerida='general', feedback_correccion=None):
    """
    V16: La IA lee el contenido completo y decide la categoría correcta.
    La categoria_sugerida es solo una pista inicial — la IA puede y debe corregirla.
    Devuelve dict con: titulo_seo, meta_descripcion, contenido_html,
                       keyword_principal, keywords_secundarias, categoria
    V17.9.12: feedback_correccion (lista de strings o None) — cuando el
    primer intento de esta noticia no pasó validar_calidad_articulo(), se
    reenvía aquí con los problemas detectados para que la IA corrija
    puntualmente esos fallos en el reintento.
    """
    api_key = GROQ_API_KEY or OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        return None
    palabras_contenido = len(contenido.split())
    tiempo_lectura = max(2, round(palabras_contenido / 200))
    TITULOS_BOX_RESUMEN = [
        ('⚡', 'Lo que debes saber'),
        ('📌', 'Lo esencial'),
        ('🔑', 'Puntos clave'),
        ('📋', 'Resumen rápido'),
    ]
    emoji_box, texto_box = random.choice(TITULOS_BOX_RESUMEN)
    titulo_box_resumen = f"{emoji_box} {texto_box}"
    if feedback_correccion:
        problemas_txt = '\n'.join(f'  - {p}' for p in feedback_correccion)
        hay_problema_transicion = any('transici' in p.lower() for p in feedback_correccion)
        hay_problema_palabras = any('palabras — el mínimo' in p for p in feedback_correccion)
        instrucciones_extra = ""
        if hay_problema_transicion:
            instrucciones_extra += """
INSTRUCCIÓN LITERAL PARA TRANSICIONES: elige AL MENOS 6 frases de esta lista
y cópialas TAL CUAL (sin cambiar la redacción) al inicio de 6 oraciones
distintas, repartidas en distintos párrafos:
"Sin embargo", "Además", "Por otro lado", "En consecuencia", "Asimismo",
"Por su parte", "De hecho", "Cabe destacar", "En ese sentido", "Al mismo tiempo",
"Aunque", "Eso sí", "Dado que", "En definitiva".
Antes de responder, cuenta cuántas de estas frases usaste. Si son menos de 6,
agrega más ANTES de entregar el JSON."""
        if hay_problema_palabras:
            instrucciones_extra += """
INSTRUCCIÓN LITERAL PARA EXTENSIÓN — el artículo anterior fue demasiado corto.
La fuente original puede ser corta pero TÚ tienes conocimiento propio para expandir.
Haz esto en CADA uno de los 4 bloques H2, en este orden:
  1. Agrega 1 párrafo de ANTECEDENTE: ¿qué pasó antes con este tema? Historia, contexto.
  2. Agrega 1 párrafo de CIFRAS: estadísticas, datos comparativos, magnitudes concretas.
  3. Agrega 1 párrafo de IMPACTO LATAM: ¿cómo afecta esto a Chile u otros países de la región?
  4. Desarrolla cada dato del contexto web en 2-3 oraciones, no solo una línea.
Antes de entregar el JSON, cuenta las palabras del contenido_html (sin HTML).
Si son menos de 650, agrega más párrafos hasta llegar. NO repitas frases ya escritas."""
        bloque_feedback_correccion = f"""⚠️ CORRECCIÓN OBLIGATORIA — este es un reintento.
Tu borrador anterior de esta misma noticia NO pasó el control de calidad por
estos motivos concretos:
{problemas_txt}
{instrucciones_extra}
Corrige específicamente estos puntos en esta nueva versión. No repitas los
mismos errores.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    else:
        bloque_feedback_correccion = ""
    bloque_contexto_web = ""
    if not feedback_correccion:
        fuentes_web = buscar_contexto_web(titulo)
        if fuentes_web:
            fuentes_txt = "\n\n".join(
                f"Fuente {i+1}: {f['title']}\n{f['content']}"
                for i, f in enumerate(fuentes_web)
            )
            bloque_contexto_web = f"""📚 CONTEXTO ADICIONAL VERIFICADO (de fuentes reales encontradas en la web,
úsalo para agregar valor real al artículo — cifras, antecedentes, comparaciones.
NO inventes nada que no esté aquí ni en el contenido original; si esta
información no aplica al ángulo del artículo, ignórala):
{fuentes_txt}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    prompt = f"""Eres el Editor Jefe Digital de VerdadHoy.com, medio de noticias en español para América Latina.
Tu tarea: clasificar correctamente esta noticia y redactarla como un artículo periodístico ORIGINAL con valor editorial propio.
IMPORTANTE: No eres un parafraseador. Eres un periodista que toma los datos de la noticia fuente
y escribe un artículo NUEVO con análisis, contexto adicional y perspectiva propia para el lector latinoamericano.
El artículo debe poder existir de forma independiente al original — Google penaliza el contenido que es
solo una reescritura. Agrega al menos un dato de contexto, una perspectiva editorial o una implicación
práctica que el original NO menciona.
⚠️ REGLA CRÍTICA DE EXTENSIÓN — LEE ESTO PRIMERO:
El artículo fuente puede ser CORTO (100-400 palabras). Eso es normal. Tu trabajo NO es copiar
ni parafrasear esas pocas palabras — es CREAR un artículo de 650 palabras usando:
  1. Los DATOS CONCRETOS de la fuente (qué pasó, quién, cuándo, dónde)
  2. Tu CONOCIMIENTO PROPIO sobre el tema (antecedentes, historia, contexto, cifras conocidas)
  3. El CONTEXTO VERIFICADO de las fuentes web que se te entregan abajo
  4. IMPLICACIONES REALES para América Latina y Chile
Si la fuente tiene 300 palabras → tú escribes 650. Si tiene 100 palabras → tú escribes 650.
El tamaño de la fuente NO determina el tamaño de tu artículo. Siempre 650 palabras mínimo.
CÓMO EXPANDIR correctamente (no rellenes con frases vacías):
- Antecedente histórico: ¿qué pasó antes? ¿es la primera vez? ¿cuántos años lleva este tema?
- Cifras de contexto: estadísticas relacionadas, datos comparativos, rankings, récords
- Impacto regional: ¿cómo afecta esto a Chile, Argentina, México u otros países de LATAM?
- Reacciones: ¿qué dijeron expertos, gobierno, ciudadanos? (si los conoces o están en el contexto web)
- Próximos pasos: ¿qué se espera que pase? ¿cuáles son las fechas o hitos importantes?
VerdadHoy.com tiene audiencia en Chile, Argentina, México, Colombia, Perú, Brasil y toda América Latina.
═══════════════════════════════════════
NOTICIA A PROCESAR:
Título original: {titulo}
Contenido: {contenido[:3000]}
Categoría sugerida por sistema: {categoria_sugerida}
Tiempo de lectura estimado: {tiempo_lectura} min
═══════════════════════════════════════
{bloque_contexto_web}
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
PASO 2 — TÍTULO SEO (máx 55 caracteres de texto) — V17.9.26:
⚠️ LÍMITE ESTRICTO: el campo "titulo_seo" en el JSON debe tener MÁXIMO 55 caracteres.
El bot agrega automáticamente " | Verdad Hoy" al final — NO lo incluyas en el JSON.
CUENTA los caracteres antes de entregar: si son más de 55, recorta hasta la última palabra completa.
ESTRUCTURA OBLIGATORIA: [KEYWORD] + [POWER WORD o DATO CONCRETO]
La keyword principal debe estar en los primeros 30 caracteres cuando sea natural.
⚠️ REGLAS RANK MATH (obligatorias para score alto):
- POWER WORD obligatoria: al menos una de estas palabras que generan urgencia/emoción:
  clave, crucial, definitivo, histórico, alerta, récord, oficial, confirmado,
  sorprendente, revolucionario, explosivo, inesperado, urgente, impactante,
  revelador, inédito, decisivo, polémico, esencial, crítico
- NÚMERO obligatorio cuando el hecho lo permita (no forzar si no hay dato real):
  cantidad de afectados, fecha, cifra, porcentaje, posición, año, precio
- Keyword principal completa — NO cortar a la mitad con el truncado
- SÍ incluir país si la noticia ES de ese país
- PROHIBIDO empezar con: "Entérate", "Descubre", "Conoce", "Último", "Te contamos"
ESTRUCTURA TITLE SEO = [Keyword] + [verbo/acción] + [power word o número]
El título debe tener sentido COMPLETO antes del límite de 48 chars (el sufijo "| Verdad Hoy" se agrega automáticamente, no lo incluyas en el JSON).
EJEMPLOS malos → buenos:
❌ "Temporal en La Araucanía"
✅ "Temporal azota La Araucanía: 5 mil hogares sin luz"  ← número + acción
❌ "Argentina y Brasil tienen problema"
✅ "Argentina no pide disculpas a Brasil: tensión diplomática crítica"  ← power word
❌ "Dólar sube hoy"
✅ "Dólar sube a máximo histórico: impacto en importaciones"  ← power word + dato
❌ "Nueva IA de Google"
✅ "Google lanza IA revolucionaria que supera a ChatGPT en código"  ← power word
❌ "Chile y la economía"
✅ "Chile reduce tasa de interés: primer recorte decisivo en 18 meses"  ← power word + número
❌ "River Plate inscribe a Thiago Almada para la"  ← CORTADO, incompleto
✅ "Thiago Almada: fichaje clave de River Plate para la Copa"  ← completo + power word
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
- Mínimo 650 palabras, máximo 850 palabras (Rank Math penaliza bajo 600 — el mínimo real con margen es 650)
- PRIMER H2 obligatorio antes de la palabra 100 del artículo (Yoast lo penaliza si no)
- Mínimo 4 subtítulos H2 — cada uno debe abrir un ángulo diferente del tema
- Párrafos de MÁXIMO 2-3 líneas (máx 25 palabras por oración — requisito Yoast)
- Alternar párrafos cortos (1-2 líneas) con párrafos medianos (3 líneas)
- CUENTA las palabras antes de entregar el JSON — si son menos de 650, agrega más desarrollo en el H2 más débil
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
META DESCRIPCIÓN: EXACTAMENTE 155-160 caracteres (no menos, no más).
- Incluir la keyword principal en los primeros 40 caracteres
- Primera frase: el hecho central (quién + qué)
- Segunda frase: consecuencia o dato concreto que genere curiosidad
- Terminar con pregunta corta o dato que invite al clic
- PROHIBIDO: "Descubre", "Entérate", "Conoce", "Te contamos", "Haz clic"
- OBLIGATORIO: cuenta los caracteres antes de responder — si son menos de 155, extiende la segunda frase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASO 7 — OPTIMIZACIÓN PARA IA (ChatGPT, Gemini, Perplexity) — V17.9.25:
Cuando alguien le pregunte a una IA sobre este tema, debe poder citar a Verdad Hoy.
Para eso, el artículo debe responder de forma explícita y verificable:
✅ ENTIDAD PRINCIPAL con nombre completo + cargo (SIEMPRE):
   ❌ "El mandatario dijo..."
   ✅ "Gabriel Boric, presidente de Chile, anunció..."
   ❌ "La empresa informó..."
   ✅ "Tesla, la fabricante estadounidense de vehículos eléctricos, anunció..."
✅ RESPONDE LAS 5W EN LOS PRIMEROS 2 PÁRRAFOS:
   - ¿QUÉ pasó? (hecho concreto, no vago)
   - ¿QUIÉN? (nombre completo + cargo o descripción)
   - ¿CUÁNDO? (fecha, día o contexto temporal)
   - ¿DÓNDE? (país, ciudad, institución)
   - ¿POR QUÉ IMPORTA? (consecuencia o impacto real)
✅ DATO VERIFICABLE (al menos 1 cifra, fecha o estadística concreta):
   ❌ "Los precios han subido considerablemente"
   ✅ "Los precios subieron un 4,7% en junio de 2026, según el INE"
   ❌ "Muchos países se vieron afectados"
   ✅ "Al menos 12 países de la región registraron escasez de divisas"
✅ ESTRUCTURA IA-FRIENDLY (párrafo de apertura modelo):
"[Nombre completo], [cargo], [verbo activo] [hecho concreto] el [fecha]
en [lugar]. La medida/decisión/evento [consecuencia directa] para [afectados]."
EJEMPLO CORRECTO:
"Gabriel Boric, presidente de Chile, promulgó el 5 de agosto de 2026
una reforma que elimina el impuesto a las importaciones de alimentos básicos.
La medida beneficia a aproximadamente 3 millones de familias de menores ingresos
y entra en vigencia en 30 días."
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
  10. El artículo tiene entre 650 y 850 palabras — CUENTA las palabras antes de entregar.
  11. Existe el dato de contexto/valor editorial que el original no menciona.
  12. El cierre termina con una pregunta genuina y específica al lector.
  13. [ENLACES_INTERNOS] aparece tal cual, al final del contenido_html.
  14. No hay frases ni estructura de párrafo copiadas del artículo original.
  15. El texto suena a periodista humano, no a resumen automático de IA.
  16. El título SEO contiene al menos una power word (clave, crucial, histórico,
      récord, oficial, confirmado, decisivo, polémico, revelador, crítico, etc.)
  17. El título SEO contiene un número si el hecho tiene datos concretos
      (cifras, fechas, posiciones, porcentajes).
  18. El título SEO está completo y tiene sentido sin cortarse — máx 55 chars de texto.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bloque_feedback_correccion}
RESPONDE ÚNICAMENTE con este JSON sin markdown ni texto extra:
{{"titulo_seo": "...", "meta_descripcion": "...", "contenido_html": "<div style=...>[BOX]</div><p>...</p>...[ENLACES_INTERNOS]", "keyword_principal": "...", "keywords_secundarias": ["kw2","kw3","kw4","kw5"], "categoria": "latinoamerica|deportes|economia|tecnologia|entretenimiento|politica|ciencia|salud|medio_ambiente|guerra|desastre|mundo|general"}}"""
    def _llamar_api_ia(url_api, headers, modelo, payload):
        """
        V17.9.4: request a la API de IA aislado en su propia función para poder
        reutilizarlo tanto para el proveedor principal como para el fallback.
        Devuelve (resp_json, None, None) si la llamada fue exitosa, o
        (None, motivo, espera_seg) si falló.
        """
        try:
            resp = requests.post(url_api, headers=headers, json=payload, timeout=55)
        except Exception as e:
            log(f"❌ IA: error de red llamando a {url_api}: {e}", 'error')
            return None, 'otro', None
        try:
            resp_json = resp.json()
        except Exception:
            log(f"❌ IA: respuesta no es JSON válido (HTTP {resp.status_code}): {resp.text[:200]}", 'error')
            return None, 'otro', None
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
                return None, 'credito', None
            elif "rate limit" in msg_lower or code == 429:
                log("   ⏳ CAUSA PROBABLE: Rate limit alcanzado.", 'advertencia')
                espera_seg = None
                m = re.search(r'try again in ([\d.]+)\s*s', msg_lower)
                if m:
                    try:
                        espera_seg = float(m.group(1))
                    except ValueError:
                        espera_seg = None
                return None, 'rate_limit', espera_seg
            elif ("invalid" in msg_lower and "key" in msg_lower) or code == 401:
                log("   🔑 CAUSA PROBABLE: API key inválida o expirada. Verifica los GitHub Secrets.", 'error')
                return None, 'auth', None
            elif "model" in msg_lower:
                log(f"   🤖 CAUSA PROBABLE: Modelo '{modelo}' no disponible o nombre incorrecto.", 'error')
                return None, 'modelo', None
            return None, 'otro', None
        return resp_json, None, None
    try:
        proveedores = []
        if OPENAI_API_KEY:
            proveedores.append((
                "OpenAI",
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                "gpt-4o-mini",
            ))
        if OPENROUTER_API_KEY:
            proveedores.append((
                "OpenRouter",
                "https://openrouter.ai/api/v1/chat/completions",
                {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                "meta-llama/llama-3.3-70b-instruct:free",
            ))
        if GROQ_API_KEY:
            proveedores.append((
                "Groq",
                "https://api.groq.com/openai/v1/chat/completions",
                {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                "llama-3.3-70b-versatile",
            ))
        if GEMINI_API_KEY:
            proveedores.append((
                "Gemini",
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"},
                "gemini-2.5-flash",
            ))
        global _proveedores_ia_logueados
        try:
            _proveedores_ia_logueados
        except NameError:
            _proveedores_ia_logueados = False
        if not _proveedores_ia_logueados:
            nombres_disponibles = [p[0] for p in proveedores]
            if nombres_disponibles:
                log(f"🔑 Proveedores de IA detectados (según API keys presentes): {', '.join(nombres_disponibles)}", 'info')
            else:
                log("🔑 ⚠️ NINGÚN proveedor de IA detectado — ninguna API key de IA llegó como variable de entorno", 'error')
            faltantes = []
            if not GROQ_API_KEY:       faltantes.append("GROQ_API_KEY")
            if not GEMINI_API_KEY:     faltantes.append("GEMINI_API_KEY")
            if not OPENROUTER_API_KEY: faltantes.append("OPENROUTER_API_KEY")
            if not OPENAI_API_KEY:     faltantes.append("OPENAI_API_KEY")
            if faltantes:
                log(f"🔑 No detectadas (revisa el secret en GitHub y el workflow .yml): {', '.join(faltantes)}", 'advertencia')
            _proveedores_ia_logueados = True
        resp_json = None
        motivo    = 'otro'
        url_api = headers = modelo = payload = None
        for i, (nombre, url_i, headers_i, modelo_i) in enumerate(proveedores):
            payload_i = {"model": modelo_i, "messages": [{"role": "user", "content": prompt}],
                         "temperature": 0.35, "max_tokens": 3500}
            if i > 0:
                log(f"   🔁 Reintentando con {nombre}...", 'advertencia')
            resp_json, motivo, espera_seg = _llamar_api_ia(url_i, headers_i, modelo_i, payload_i)
            if resp_json is None and motivo == 'rate_limit' and espera_seg is not None and espera_seg <= 45:
                espera_real = espera_seg + 2
                log(f"   ⏳ Esperando {espera_real:.0f}s por rate limit de {nombre} antes de reintentar (gratis)...", 'advertencia')
                time.sleep(espera_real)
                resp_json, motivo, espera_seg = _llamar_api_ia(url_i, headers_i, modelo_i, payload_i)
                if resp_json is not None:
                    log(f"   ✅ {nombre} respondió tras esperar el rate limit", 'exito')
            if resp_json is not None:
                url_api, headers, modelo, payload = url_i, headers_i, modelo_i, payload_i
                if i > 0:
                    log(f"   ✅ Fallback a {nombre} exitoso", 'exito')
                break
        if resp_json is None:
            return None
        choice       = resp_json["choices"][0]
        finish_reason = choice.get("finish_reason", "stop")
        if finish_reason == "length":
            log("⚠️ IA cortó respuesta por longitud (finish_reason=length) — reintentando con contenido más corto", 'advertencia')
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
        if not texto.endswith('}'):
            log(f"⚠️ JSON incompleto (no termina en '}}') — respuesta cortada", 'advertencia')
            return None
        resultado = json.loads(texto)
        categorias_validas = set(CATEGORIA_WP.keys())
        cat_ia = resultado.get('categoria', '').strip().lower()
        if cat_ia not in categorias_validas:
            log(f"⚠️ IA devolvió categoría inválida '{cat_ia}' — usando sugerida '{categoria_sugerida}'", 'advertencia')
            resultado['categoria'] = categoria_sugerida if categoria_sugerida in categorias_validas else 'general'
        else:
            if cat_ia != categoria_sugerida:
                log(f"🧠 IA corrigió categoría: '{categoria_sugerida}' → '{cat_ia}'", 'info')
        contenido_generado = resultado.get('contenido_html', '')
        similitud_con_fuente = similitud_contenido(contenido_generado, contenido[:3000], longitud=200)
        if similitud_con_fuente > 0.42:
            log(f"⚠️ Contenido generado demasiado similar al original (similitud={similitud_con_fuente:.2f}) — reintentando con instrucción reforzada", 'advertencia')
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
def bonus_frescura(fecha_str):
    """
    V17.9.23: bono de puntaje por antigüedad de la noticia — prioriza
    actualidad SIN descartar de plano nada por ser "vieja".
    """
    if not fecha_str:
        return 0
    try:
        fecha_str_norm = str(fecha_str).replace('Z', '+00:00')
        fecha_pub = datetime.fromisoformat(fecha_str_norm)
        if fecha_pub.tzinfo is None:
            fecha_pub = fecha_pub.replace(tzinfo=timezone.utc)
        horas = (datetime.now(timezone.utc) - fecha_pub).total_seconds() / 3600
        if horas < 0:
            return 0
        if horas <= 6:
            return 8
        elif horas <= 24:
            return 5
        elif horas <= 48:
            return 2
        return 0
    except Exception:
        return 0
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
    # ── V17.9.0: Bonus LATAM por NIVEL de país ──
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
    # ── V17.9.0: Bono editorial por TEMA prioritario ──
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
            break
    # ── V17.6: Penalización noticias exclusivamente de EE.UU./Europa/Asia ──
    if latam_hits == 0:
        keywords_no_latam = [
            "washington dc", "white house", "congress usa", "senate usa",
            "wall street", "silicon valley", "pentagon", "kremlin",
            "bundestag", "westminster", "downing street",
        ]
        no_latam_hits = sum(1 for kw in keywords_no_latam if kw in txt)
        if no_latam_hits >= 1:
            p -= 4
        if es_noticia_espana_domestica(titulo, desc):
            p -= 6
    # ── V18.0: Bonus de DURABILIDAD SEO — a pedido del usuario, se prioriza
    # contenido que mantiene valor de búsqueda en el tiempo (evergreen) por
    # sobre noticias que se vuelven irrelevantes en 1-2 días (resultado de un
    # partido puntual, un hecho policial aislado, la frase del día de un
    # político). Con solo 6 cupos/día, ante puntajes similares gana la nota
    # con vida útil más larga en Google — sin descartar por completo la
    # actualidad ni el bonus LATAM/Chile de arriba, que siguen sumando igual.
    tema_durabilidad = detectar_tema(titulo, desc)
    TEMAS_EVERGREEN_ALTO  = {'tecnologia', 'ciencia', 'salud', 'medio_ambiente'}
    TEMAS_EVERGREEN_MEDIO = {'economia', 'educacion'}
    TEMAS_EFIMEROS        = {'guerra', 'desastre', 'crimen'}
    if tema_durabilidad in TEMAS_EVERGREEN_ALTO:
        p += 10
    elif tema_durabilidad in TEMAS_EVERGREEN_MEDIO:
        p += 5
    elif tema_durabilidad in TEMAS_EFIMEROS:
        p -= 4
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
    V18.0: sigue siendo el único gate real de publicación — chequea la cuota
    GLOBAL de 6/día (MAX_POSTS_WP_DIA) contra estado_cuotas.json, que ahora
    es alimentado por TODAS las fuentes (general + Chile + LATAM, fusionadas
    en main() desde V18.0), no solo el flujo general.
    """
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True
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
        margen = TIEMPO_ENTRE_WP_MIN - 15
        if minutos < margen:
            log(f"⏱️ WP: publicado hace {minutos:.0f} min — mínimo {margen} min (con margen)", 'info')
            return False
        log(f"✅ WP: {minutos:.0f} min desde última publicación — OK para publicar", 'info')
    except:
        pass
    return True
def puede_publicar_fb(h):
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True
    hora_utc = datetime.utcnow().hour
    en_pico  = any(inicio <= hora_utc < fin for inicio, fin in HORARIOS_PICO_UTC)
    if not en_pico:
        log(f"⏰ FB: fuera de horario pico (UTC {hora_utc:02d}h) — WP no se ve afectado", 'info')
        return False
    hoy = datetime.now().date()
    posts_hoy = sum(
        1 for ts in h.get('timestamps', [])
        if ts and datetime.fromisoformat(ts).date() == hoy
    )
    if posts_hoy >= MAX_POSTS_FB_DIA:
        log(f"🚫 FB: límite diario ({posts_hoy}/{MAX_POSTS_FB_DIA})", 'advertencia')
        return False
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
    if not WP_APP_PASSWORD:
        log("⚠️ Sin WP_APP_PASSWORD — no se puede obtener artículo para FB", 'advertencia')
        return None
    try:
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
        urls_fb_ya = set(h.get('urls_fb_publicadas', []))
        for art in articulos:
            if not art.get('featured_media') or art['featured_media'] == 0:
                log(f"   ❌ Sin imagen: {art.get('title', {}).get('rendered', '')[:40]}", 'debug')
                continue
            url_art  = art.get('link', '')
            titulo   = art.get('title', {}).get('rendered', '')
            art_id   = str(art.get('id', ''))
            if art_id in urls_fb_ya or url_art in urls_fb_ya:
                log(f"   ↩️ Ya publicado en FB: {titulo[:40]}", 'debug')
                continue
            media_id = art['featured_media']
            imagen_url = obtener_url_imagen_wp(media_id)
            if not imagen_url:
                log(f"   ❌ No se pudo obtener imagen para ID {media_id}", 'debug')
                continue
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
    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            params={'_fields': 'source_url,media_details'},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
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
    if 'urls_fb_publicadas' not in h:
        h['urls_fb_publicadas'] = []
    if art_id not in h['urls_fb_publicadas']:
        h['urls_fb_publicadas'].append(art_id)
    if url not in h['urls_fb_publicadas']:
        h['urls_fb_publicadas'].append(url)
    if len(h['urls_fb_publicadas']) > 200:
        h['urls_fb_publicadas'] = h['urls_fb_publicadas'][-200:]
    return h
# ──────────────────────────────────────────────────────────
# V12: PUBLICAR EN FACEBOOK — SOLO IMAGEN + TEXTO
# ──────────────────────────────────────────────────────────
def construir_texto_facebook(titulo, excerpt, url_wp, categoria='general'):
    titulo_limpio = titulo.replace('&quot;', '"').replace('&#8220;', '"').replace('&#8221;', '"')
    titulo_limpio = titulo_limpio.replace('&#8216;', "'").replace('&#8217;', "'")
    titulo_limpio = re.sub(r'&[a-zA-Z]+;', '', titulo_limpio).strip()
    excerpt_limpio = excerpt[:200].strip()
    if excerpt_limpio and excerpt_limpio[-1] not in '.!?':
        excerpt_limpio += '...'
    url_utm = (f"{url_wp}?utm_source=facebook&utm_medium=social&utm_campaign=bot_noticias"
               if '?' not in url_wp else
               f"{url_wp}&utm_source=facebook&utm_medium=social&utm_campaign=bot_noticias")
    cta = random.choice(CTAS_POR_TEMA.get(categoria, CTAS_POR_TEMA['general']))
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
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("⚠️ FB: sin credenciales", 'advertencia')
        return False
    if not imagen_path or not os.path.exists(imagen_path):
        log("❌ FB: sin imagen local para publicar", 'error')
        return False
    imagen_fb_path = imagen_path
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(imagen_path).convert('RGB')
        max_w = 720
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
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
            kw_imagen = (frase_clave or titulo)[:125]
            leyenda_media = f"{titulo[:120]} — Fuente: Verdad Hoy"
            descripcion_media = (
                f"{frase_clave}. {meta_descripcion}".strip()[:300]
                if meta_descripcion and frase_clave
                else (frase_clave or titulo)[:300]
            )
            metadatos = {
                'title':       kw_imagen,
                'alt_text':    kw_imagen,
                'caption':     leyenda_media,
                'description': descripcion_media,
            }
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
    """
    Publica artículo en WordPress. Imagen OBLIGATORIA.
    V18.0: devuelve una tupla (url_articulo, slug_categoria_final) en vez de
    solo la URL — slug_categoria_final es una de las 15 categorías reales
    del menú (ver CATEGORIAS_ROTACION_WP) y se usa en main() para registrar
    la cuota diaria con la categoría REAL (post-IA, post-región) y así poder
    rotar correctamente entre categorías. En cualquier fallo se devuelve
    (None, None).
    """
    if not WP_APP_PASSWORD:
        log("⚠️ WP_APP_PASSWORD no configurado", 'advertencia')
        return None, None
    if not imagen_path or not os.path.exists(imagen_path):
        log("❌ Sin imagen — no se publica en WordPress", 'error')
        return None, None
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
    resultado_ia = reescribir_noticia_v9(titulo, contenido, tema)
    if resultado_ia:
        es_valido, problemas = validar_calidad_articulo(
            resultado_ia.get('contenido_html', ''),
            resultado_ia.get('meta_descripcion', ''),
            resultado_ia.get('titulo_seo', ''),
            resultado_ia.get('categoria', ''),
        )
        if not es_valido:
            if not REINTENTAR_CALIDAD_IA:
                log(f"❌ Artículo no pasó control de calidad ({len(problemas)} problema(s)) — se descarta (reintento desactivado, ver REINTENTAR_CALIDAD_IA)", 'error')
                for p in problemas:
                    log(f"   - {p}", 'error')
                return None, None
            log(f"⚠️ Artículo no pasó control de calidad ({len(problemas)} problema(s)) — reintentando con feedback:", 'advertencia')
            for p in problemas:
                log(f"   - {p}", 'advertencia')
            resultado_reintento = reescribir_noticia_v9(titulo, contenido, tema, feedback_correccion=problemas)
            if resultado_reintento:
                es_valido_2, problemas_2 = validar_calidad_articulo(
                    resultado_reintento.get('contenido_html', ''),
                    resultado_reintento.get('meta_descripcion', ''),
                    resultado_reintento.get('titulo_seo', ''),
                    resultado_reintento.get('categoria', ''),
                )
                if es_valido_2:
                    log("✅ Reintento corrigió los problemas — usando esta versión", 'exito')
                    resultado_ia = resultado_reintento
                else:
                    log(f"❌ El reintento tampoco pasó el control de calidad ({len(problemas_2)} problema(s)) — se descarta esta noticia", 'error')
                    for p in problemas_2:
                        log(f"   - {p}", 'error')
                    return None, None
            else:
                log("❌ IA no disponible para el reintento — se descarta esta noticia", 'error')
                return None, None
    alt_text_imagen = titulo[:125]
    tags_ids = []
    _TITULOS_BOX = [
        ('⚡', 'Lo que debes saber'),
        ('📌', 'Lo esencial'),
        ('🔑', 'Puntos clave'),
        ('📋', 'Resumen rápido'),
    ]
    _emoji_b, _texto_b = random.choice(_TITULOS_BOX)
    _titulo_box = f"{_emoji_b} {_texto_b}"
    def _generar_box_fallback(titulo_art, contenido_art):
        texto_limpio = re.sub(r'<[^>]+>', ' ', contenido_art)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto_limpio)
                     if len(o.strip()) > 40 and not o.strip().startswith('<')]
        puntos = []
        for o in oraciones[:10]:
            if any(skip in o.lower() for skip in ['verdad hoy', 'fuente:', 'información verificada']):
                continue
            if len(o) <= 160:
                punto = o if o.endswith(('.','!','?')) else o + '.'
            else:
                corte = o[:160]
                for sep in ['. ', ', ', ' que ', ' y ', ' con ']:
                    idx = corte.rfind(sep)
                    if idx > 80:
                        punto = corte[:idx + len(sep)].strip()
                        if not punto.endswith(('.','!','?')):
                            punto += '...'
                        break
                else:
                    punto = corte.rsplit(' ', 1)[0] + '...'
            puntos.append(punto)
            if len(puntos) == 4:
                break
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
        titulo_final_raw     = resultado_ia.get('titulo_seo', titulo) or titulo
        categoria_ia_tmp     = resultado_ia.get('categoria', tema)
        titulo_final         = mejorar_titulo_seo(titulo_final_raw, categoria_ia_tmp)
        meta_desc            = resultado_ia.get('meta_descripcion', '')
        frase_clave          = resultado_ia.get('keyword_principal', '')
        contenido_formateado = resultado_ia.get('contenido_html', '')
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
        log("❌ IA no disponible para esta noticia — se descarta (NO se publica sin IA)", 'error')
        return None, None
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
    imagen_schema_url  = "__PLACEHOLDER_IMAGEN_ARTICULO__"
    imagen_schema_w    = 1200
    imagen_schema_h    = 630
    LOGO_URL_FIJO      = f"{WP_URL}/wp-content/uploads/favicon_512.png"
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
    stopwords_es = {'para','como','este','esta','esto','pero','porque','cuando','donde',
                    'quien','ante','bajo','cada','con','contra','desde','durante','entre',
                    'hacia','hasta','por','según','tras','una','uno','los','las','del',
                    'que','sus','más','sin','sobre','también','hay','han','sido'}
    if not frase_clave:
        palabras_clave = [p for p in re.findall(r'\b\w{4,}\b', titulo_final.lower())
                          if p not in stopwords_es]
        frase_clave = ' '.join(palabras_clave[:4])
    sufijo_seo = ' | Verdad Hoy'
    max_titulo = 55
    if len(titulo_final) > max_titulo:
        titulo_truncado = titulo_final[:max_titulo]
        if ':' in titulo_truncado:
            idx_colon = titulo_truncado.rfind(':')
            if idx_colon >= max_titulo - 20:
                titulo_base = titulo_truncado[:idx_colon]
            else:
                titulo_base = titulo_truncado.rsplit(' ', 1)[0]
        else:
            titulo_base = titulo_truncado.rsplit(' ', 1)[0]
    else:
        titulo_base = titulo_final
    titulo_seo = titulo_base + sufijo_seo
    log(f"📰 titulo_seo: '{titulo_seo}' ({len(titulo_seo)} chars)", 'debug')
    if not meta_desc:
        primera_oracion = re.split(r'(?<=[.!?])\s+', ' '.join(contenido.split()))[0]
        if len(primera_oracion) > 160:
            meta_desc = primera_oracion[:157].rsplit(' ', 1)[0] + '...'
        elif len(primera_oracion) < 80:
            meta_desc = (' '.join(contenido.split()))[:157].rsplit(' ', 1)[0] + '...'
        else:
            meta_desc = primera_oracion
    else:
        meta_desc = meta_desc.strip()
        if len(meta_desc) < 150:
            texto_limpio = ' '.join(contenido.split())
            oraciones = re.split(r'(?<=[.!?])\s+', texto_limpio)
            for oracion_extra in oraciones[1:4]:
                oracion_extra = oracion_extra.strip()
                if not oracion_extra:
                    continue
                candidato = meta_desc.rstrip('.') + '. ' + oracion_extra
                if len(candidato) <= 160:
                    meta_desc = candidato
                else:
                    espacio = 157 - len(meta_desc) - 2
                    if espacio > 20:
                        meta_desc = meta_desc.rstrip('.') + '. ' + oracion_extra[:espacio].rsplit(' ', 1)[0] + '...'
                    break
                if len(meta_desc) >= 140:
                    break
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157].rsplit(' ', 1)[0] + '...'
    log(f"📝 meta_desc: {len(meta_desc)} chars — '{meta_desc[:80]}...'", 'debug')
    fecha_wp = None
    if fecha_fuente:
        try:
            fecha_str = str(fecha_fuente).replace('Z', '+00:00')
            dt = datetime.fromisoformat(fecha_str)
            fecha_wp = dt.strftime('%Y-%m-%dT%H:%M:%S')
        except:
            fecha_wp = None
    imagen_id = subir_imagen_wp(
        imagen_path, titulo_final, alt_text=alt_text_imagen,
        frase_clave=frase_clave, meta_descripcion=meta_desc,
    )
    if not imagen_id:
        log("❌ No se pudo subir imagen — cancelando WP", 'error')
        return None, None
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
    palabras_articulo = len(re.sub(r'<[^>]+>', '', contenido_formateado).split())
    minutos_lectura = max(2, round(palabras_articulo / 200))
    barra_lectura = f"""<p style="font-size:0.82em;color:#6b7280;margin:0 0 20px 0;display:flex;align-items:center;gap:6px;">
<span>🕐</span> <span>Tiempo de lectura: <strong>{minutos_lectura} min</strong></span>
</p>"""
    enlace_fuente_html = (
        f'<a href="{fuente_url}" target="_blank" rel="noopener">{nombre_medio}</a>'
        if fuente_url else nombre_medio
    )
    contenido_html = f"""
{barra_lectura}
{contenido_formateado}
<hr>
<p><strong>Fuente:</strong> {enlace_fuente_html}</p>
<p><em>Información verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
{schema_markup}
"""
    categoria_final = resultado_ia.get('categoria', tema) if resultado_ia else tema
    if categoria_final not in CATEGORIA_WP:
        log(f"⚠️ Categoría '{categoria_final}' inválida — usando '{tema}'", 'advertencia')
        categoria_final = tema if tema in CATEGORIA_WP else 'general'
    # V18.0: la resolución categoría-editorial → slug WP real ahora se hace
    # con resolver_categoria_wp() (antes esta lógica estaba duplicada aquí
    # mismo). slug_cat es también el valor que main() recibirá de vuelta
    # para registrar la cuota diaria y la rotación de categorías.
    categorias_internacional_paraguas = {'desastre', 'guerra', 'crimen', 'religion', 'educacion', 'general', 'mundo'}
    slug_cat_secundario = None
    if categoria_final in categorias_internacional_paraguas:
        _categoria_original = categoria_final
        slug_cat = resolver_categoria_wp(categoria_final, titulo, contenido_html)
        if slug_cat == 'latinoamerica':
            slug_cat_secundario = 'internacional'
            log(f"   🌎 Reasignado a 'Latinoamérica' (era '{_categoria_original}', país LATAM detectado)", 'info')
        elif slug_cat != 'internacional':
            slug_cat_secundario = 'internacional'
            log(f"   🌍 Región → categoría '{slug_cat}' (era '{_categoria_original}')", 'info')
    else:
        slug_cat = resolver_categoria_wp(categoria_final, titulo, contenido_html)
    cat_id = obtener_id_categoria_wp(slug_cat)
    if not cat_id and slug_cat != 'internacional':
        log(f"⚠️ Categoría WP '{slug_cat}' no encontrada — usando 'internacional' de respaldo. "
            f"Verifica el slug real de esa categoría y avísame para corregir REGION_SLUG_WP.", 'advertencia')
        cat_id = obtener_id_categoria_wp('internacional')
        slug_cat = 'internacional'
        slug_cat_secundario = None
    categorias = [cat_id] if cat_id else []
    if slug_cat_secundario:
        cat_id_sec = obtener_id_categoria_wp(slug_cat_secundario)
        if cat_id_sec and cat_id_sec not in categorias:
            categorias.append(cat_id_sec)
    slug_post = generar_slug_seo(titulo_final, max_palabras=8)
    log(f"🔗 Slug generado: {slug_post}", 'debug')
    post_data = {
        'title':          titulo_final,
        'slug':           slug_post,
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
            post_id      = r['id']
            url_articulo = r.get('link', f"{WP_URL}/?p={post_id}")
            log(f"✅ Publicado en WordPress: {url_articulo}", 'exito')
            seo_guardado = False
            try:
                rankmath_payload = {
                    'objectID':   post_id,
                    'objectType': 'post',
                    'meta': {
                        'rank_math_focus_keyword':   frase_clave,
                        'rank_math_title':           titulo_seo,
                        'rank_math_description':     meta_desc,
                        'rank_math_robots':          ['index', 'follow'],
                    }
                }
                log(f"📊 Rank Math payload: title='{titulo_seo}' ({len(titulo_seo)} chars), "
                    f"desc='{meta_desc[:60]}...' ({len(meta_desc)} chars), "
                    f"focuskw='{frase_clave}'", 'debug')
                r_rm = requests.post(
                    f"{WP_URL}/wp-json/rankmath/v1/updateMeta",
                    json=rankmath_payload,
                    auth=(WP_USER, WP_APP_PASSWORD), timeout=10
                )
                if r_rm.status_code in (200, 201):
                    log(f"✅ Rank Math SEO guardado (focuskw: {frase_clave[:40]})", 'exito')
                    seo_guardado = True
                else:
                    log(f"ℹ️ Rank Math endpoint no respondió (HTTP {r_rm.status_code}) — probando Yoast", 'debug')
            except Exception as e_rm:
                log(f"ℹ️ Rank Math no disponible ({e_rm}) — probando Yoast", 'debug')
            if not seo_guardado:
                try:
                    yoast_payload = {
                        'yoast_wpseo_focuskw':             frase_clave,
                        'yoast_wpseo_title':               titulo_seo,
                        'yoast_wpseo_metadesc':            meta_desc,
                        'yoast_wpseo_meta-robots-noindex': '0',
                    }
                    r_yoast = requests.post(
                        f"{WP_URL}/wp-json/yoast/v1/indexables",
                        json={'object_id': post_id, 'object_type': 'post', **yoast_payload},
                        auth=(WP_USER, WP_APP_PASSWORD), timeout=10
                    )
                    if r_yoast.status_code in (200, 201):
                        log(f"✅ Yoast SEO guardado (focuskw: {frase_clave[:40]})", 'exito')
                        seo_guardado = True
                except Exception as e_yoast:
                    log(f"ℹ️ Yoast no disponible: {e_yoast}", 'debug')
            if not seo_guardado:
                try:
                    meta_patch = {
                        'rank_math_focus_keyword': frase_clave,
                        'rank_math_title':         titulo_seo,
                        'rank_math_description':   meta_desc,
                        '_yoast_wpseo_focuskw':    frase_clave,
                        '_yoast_wpseo_title':      titulo_seo,
                        '_yoast_wpseo_metadesc':   meta_desc,
                    }
                    r_patch = requests.post(
                        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                        json={'meta': meta_patch},
                        auth=(WP_USER, WP_APP_PASSWORD), timeout=10
                    )
                    if r_patch.status_code in (200, 201):
                        log(f"✅ SEO guardado via PATCH REST (focuskw: {frase_clave[:40]})", 'exito')
                    else:
                        log(f"⚠️ SEO no confirmado (HTTP {r_patch.status_code}) — verificar manualmente en WordPress", 'advertencia')
                except Exception as e_patch:
                    log(f"⚠️ No se pudo guardar SEO meta: {e_patch}", 'advertencia')
            return url_articulo, slug_cat
        else:
            log(f"❌ Error WP: {r.get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción WP: {e}", 'error')
    return None, None
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
KEYWORDS_CHILE = [
    "chile", "chilena", "chileno", "chilenas", "chilenos",
    "santiago", "valparaíso", "valparaiso", "concepción", "concepcion",
    "antofagasta", "temuco", "viña del mar", "vina del mar",
    "la serena", "rancagua", "talca", "arica", "iquique", "puerto montt",
    "gabriel boric", "boric", "gobierno de chile", "congreso chileno",
    "senado chileno", "cámara de diputados chile", "camara de diputados chile",
    "carabineros", "pdi chile", "ministerio de chile",
    "banco central de chile", "peso chileno", "peso cl",
    "conaf", "codelco", "enap chile", "transantiago", "metro de santiago",
    "sernac", "sernapesca", "sii chile", "servicio de impuestos internos",
    "comisión para el mercado financiero", "cmf chile",
    "bolsa de santiago", "ipsa", "uf chilena", "utm chile",
    "falabella", "cencosud", "lider cl", "jumbo chile",
    "latam airlines chile", "sky airline",
    "festival de viña", "festival de viña del mar",
    "selección chilena", "la roja", "la roja chilena",
    "colo colo", "universidad de chile", "universidad católica",
    "huaso", "mapuche", "araucanía", "la araucania",
]
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
REGION_SLUG_WP = {
    'europa':             'europa',
    'asia':               'asia',
    'africa':             'africa',
    'medio_oriente':      'medio-oriente',
    'oceania':            'oceania',
    'mundo':              'mundo',
}
def detectar_region_internacional(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    puntajes = {
        region: sum(1 for kw in kws if kw in txt)
        for region, kws in KEYWORDS_REGIONES.items()
    }
    mejor_region, mejor_puntaje = max(puntajes.items(), key=lambda x: x[1])
    if mejor_puntaje == 0:
        return 'mundo'
    return mejor_region
KEYWORDS_ESPANA_DOMESTICO = [
    "ayuso", "sánchez", "pedro sanchez", "psoe", "vox", " pp ", "sumar",
    "congreso de los diputados", "senado español", "moncloa", "casa real española",
    "felipe vi", "junta electoral central", "defensor del pueblo",
    "madrid", "barcelona", "sevilla", "valencia", "andalucía", "andalucia",
    "cataluña", "cataluna", "país vasco", "pais vasco", "galicia españa",
    "comunidad de madrid", "generalitat", "ayuntamiento de madrid",
    "guardia civil", "policía nacional española",
    "teatro real", "rtve", "el corte inglés", "renfe", "adif",
]
def es_noticia_espana_domestica(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    tiene_espana = any(kw in txt for kw in KEYWORDS_ESPANA_DOMESTICO)
    if not tiene_espana:
        return False
    if any(kw in txt for pais_kws in KEYWORDS_LATAM_PAISES.values() for kw in pais_kws):
        return False
    if any(kw in txt for kw in KEYWORDS_CHILE):
        return False
    return True
def es_noticia_chile(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    return any(kw in txt for kw in KEYWORDS_CHILE)
def es_noticia_latam_sin_chile(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(kw in txt for kw in KEYWORDS_CHILE):
        return False, None
    for pais, keywords in KEYWORDS_LATAM_PAISES.items():
        if any(kw in txt for kw in keywords):
            return True, pais
    if any(kw in txt for kw in [
        "latinoamérica", "latinoamerica", "america latina",
        "centroamerica", "centroamérica", "caribe",
        "sudamerica", "sudamérica", "cono sur",
    ]):
        return True, 'latam_general'
    return False, None
def cargar_estado_latam():
    datos = cargar_json(ESTADO_LATAM_PATH, {})
    hoy   = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy:
        return {'fecha': hoy, 'chile': 0, 'latam': 0}
    return datos
def guardar_estado_latam(datos):
    guardar_json(ESTADO_LATAM_PATH, datos)
def puede_publicar_latam_chile():
    """V18.0: ya no se usa en el flujo principal (ver publicar_bloque_latam_chile)."""
    datos = cargar_estado_latam()
    return datos.get('chile', 0) < MAX_POSTS_WP_DIA_CHILE
def puede_publicar_latam_region():
    """V18.0: ya no se usa en el flujo principal (ver publicar_bloque_latam_chile)."""
    datos = cargar_estado_latam()
    return datos.get('latam', 0) < MAX_POSTS_WP_DIA_LATAM
def registrar_publicacion_latam(tipo):
    datos = cargar_estado_latam()
    datos[tipo] = datos.get(tipo, 0) + 1
    guardar_estado_latam(datos)
def obtener_rss_chile():
    """V17.3: Feeds RSS específicos de medios chilenos."""
    fuentes_chile = [
        ('https://www.emol.com/rss/',                               'Emol'),
        ('https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml', 'Cooperativa'),
        ('https://www.cnnchile.com/feed/',                          'CNN Chile'),
        ('https://www.lacuarta.com/feed/',                          'La Cuarta'),
    ]
    noticias = []
    for url_feed, nombre in fuentes_chile:
        try:
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
                    'puntaje':     calcular_puntaje(t, d) + 5,
                    'pais':        'chile',
                })
        except Exception as ex:
            log(f"RSS Chile error ({nombre}): {ex}", 'advertencia')
    log(f"RSS Chile: {len(noticias)} noticias", 'info')
    return noticias
def obtener_rss_latam():
    """V17.3: Feeds RSS de medios LATAM (excluyendo Chile)."""
    fuentes_latam = [
        ('https://www.eluniversal.com.mx/rss.xml',                  'El Universal MX',   'mexico'),
        ('https://www.milenio.com/rss',                             'Milenio MX',         'mexico'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/america/',  'Infobae América',    'argentina'),
        ('https://www.lanacion.com.ar/arc/outboundfeeds/rss/',      'La Nación AR',       'argentina'),
        ('https://www.pagina12.com.ar/rss/portada',                 'Página 12 AR',       'argentina'),
        ('https://www.eltiempo.com/rss/portada.xml',                'El Tiempo CO',       'colombia'),
        ('https://www.semana.com/rss.xml',                          'Semana CO',          'colombia'),
        ('https://elcomercio.pe/arcio/rss/',                        'El Comercio PE',     'peru'),
        ('https://rpp.pe/rss/',                                     'RPP Perú',           'peru'),
        ('https://efectococuyo.com/feed/',                          'Efecto Cocuyo VE',   'venezuela'),
        ('https://www.paginasiete.bo/rss.xml',                     'Página Siete BO',    'bolivia'),
        ('https://www.eluniverso.com/rss.xml',                     'El Universo EC',     'ecuador'),
        ('https://www.elpais.com.uy/rss.xml',                      'El País UY',         'uruguay'),
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
                    'puntaje':     calcular_puntaje(t, d) + 3,
                    'pais':        pais,
                })
        except Exception as ex:
            log(f"RSS LATAM error ({nombre}): {ex}", 'advertencia')
    log(f"RSS LATAM: {len(noticias)} noticias", 'info')
    return noticias
def obtener_newsapi_chile():
    """V17.3: Queries NewsAPI específicas para noticias de Chile."""
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
    """V17.3: Queries NewsAPI específicas para LATAM (sin Chile)."""
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
    V18.0: DEPRECADO como flujo automático — desde esta versión, main() ya
    fusiona las fuentes de Chile y LATAM (obtener_rss_chile, obtener_rss_latam,
    obtener_newsapi_chile, obtener_newsapi_latam) directamente al pool general
    de candidatas, y todo compite por el mismo tope de 6/día con rotación de
    categorías. Esta función se conserva funcional (por si se quiere invocar
    manualmente aparte del flujo único) pero main() ya NO la llama por
    defecto. Ver el aviso en main() sobre MODO_LATAM.
    """
    log("\n" + "=" * 60, 'info')
    log("🌎 BLOQUE V17.3 — LATAM + CHILE (uso manual/deprecado, ver V18.0)", 'info')
    estado_latam = cargar_estado_latam()
    log(f"   Publicados hoy → Chile: {estado_latam.get('chile',0)}/{MAX_POSTS_WP_DIA_CHILE} | "
        f"LATAM: {estado_latam.get('latam',0)}/{MAX_POSTS_WP_DIA_LATAM}", 'info')
    h             = cargar_historial()
    exito_chile   = False
    exito_latam   = False
    if puede_publicar_latam_chile():
        log("\n🇨🇱 Buscando noticia de Chile...", 'info')
        noticias_cl = []
        noticias_cl.extend(obtener_rss_chile())
        noticias_cl.extend(obtener_newsapi_chile())
        noticias_cl = [n for n in noticias_cl if es_noticia_chile(n.get('titulo',''), n.get('descripcion',''))]
        noticias_cl = deduplicar_batch(noticias_cl)
        for n in noticias_cl:
            n['puntaje'] = n.get('puntaje', 0) + bonus_frescura(n.get('fecha'))
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
            es_spam, kw_spam = es_contenido_spam(titulo, desc)
            if es_spam:
                log(f"   🚫 SPAM Chile: '{kw_spam}' — descartando", 'advertencia')
                continue
            cont_web, _ = extraer_contenido(url)
            contenido_ok = cont_web if (cont_web and len(cont_web) >= 500) else (desc if len(desc) >= 400 else None)
            if not contenido_ok and cont_web and len(cont_web) >= 250:
                contenido_ok = cont_web + ' ' + desc if desc else cont_web
            if not contenido_ok:
                continue
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
            url_wp, _slug = publicar_en_wordpress(
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
                if PINTEREST_TOKEN:
                    publicar_pinterest(titulo, contenido_ok[:490], url_wp, None, 'latinoamerica')
                break
    else:
        log(f"🇨🇱 Chile: cuota diaria alcanzada ({MAX_POSTS_WP_DIA_CHILE}/{MAX_POSTS_WP_DIA_CHILE})", 'info')
    if puede_publicar_latam_region():
        log("\n🌎 Buscando noticia LATAM (sin Chile)...", 'info')
        noticias_la = []
        noticias_la.extend(obtener_rss_latam())
        noticias_la.extend(obtener_newsapi_latam())
        filtradas = []
        for n in noticias_la:
            es_la, pais = es_noticia_latam_sin_chile(n.get('titulo',''), n.get('descripcion',''))
            if es_la:
                n['pais'] = pais
                filtradas.append(n)
        noticias_la = deduplicar_batch(filtradas)
        for n in noticias_la:
            n['puntaje'] = n.get('puntaje', 0) + bonus_frescura(n.get('fecha'))
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
            es_spam, kw_spam = es_contenido_spam(titulo, desc)
            if es_spam:
                log(f"   🚫 SPAM LATAM: '{kw_spam}' — descartando", 'advertencia')
                continue
            cont_web, _ = extraer_contenido(url)
            contenido_ok = cont_web if (cont_web and len(cont_web) >= 500) else (desc if len(desc) >= 400 else None)
            if not contenido_ok and cont_web and len(cont_web) >= 250:
                contenido_ok = cont_web + ' ' + desc if desc else cont_web
            if not contenido_ok:
                continue
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
            url_wp, _slug = publicar_en_wordpress(
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
    queries = [
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
        'economy inflation markets Latin America impact',
        'technology artificial intelligence Spanish',
        'Trump tariffs trade Latin America',
        'climate change South America environment',
        'football soccer Champions League goals',
        'Copa del Mundo 2026 World Cup Messi',
        'NBA basketball playoffs finals',
        'Formula 1 F1 Grand Prix race',
        'tennis ATP WTA Roland Garros',
        'Netflix series premiere streaming español',
        'music Grammy Billboard Latin',
        'Oscar awards Hollywood cine',
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
                    if not t or '[Removed]' in t or not img:
                        continue
                    d = a.get('description', '')
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
    categorias = ['world', 'politics', 'business', 'technology', 'science',
                  'health', 'entertainment', 'sports']
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
    fuentes = [
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
        ('http://feeds.bbci.co.uk/mundo/rss.xml',                      'BBC Mundo'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada', 'El País Internacional'),
        ('https://www.dw.com/es/ultimas-noticias/s-30689792/rss',      'Deutsche Welle ES'),
        ('https://feeds.france24.com/es/',                             'France 24 ES'),
        ('https://www.efe.com/efe/espana/1/rss',                       'EFE'),
        ('https://www.espn.com.mx/rss/deportes.xml',                   'ESPN Deportes'),
        ('https://e00-marca.uecdn.es/rss/portada.xml',                 'Marca'),
        ('https://feeds.as.com/mrss-s/pages/as/site/as.com/portada/', 'AS Deportes'),
        ('https://www.goal.com/es/rss',                                'Goal ES'),
        ('https://www.record.com.mx/rss/portada.xml',                  'Record MX'),
        ('https://www.mundodeportivo.com/rss/home.xml',                'Mundo Deportivo'),
        ('https://los40.com/los40/rss/portada/',                       'Los 40'),
        ('https://www.espinof.com/feed',                               'Espinof Cine'),
        ('https://www.fotogramas.es/rss/noticias/',                    'Fotogramas'),
        ('https://www.sensacine.com/rss/',                             'SensaCine'),
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
                    for enc in getattr(e, 'enclosures', []):
                        if enc.get('type', '').startswith('image'):
                            img = enc.get('href') or enc.get('url')
                            break
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
        if w < 300 or h < 200:
            log(f"⚠️ Imagen muy pequeña ({w}x{h}) — descartando", 'debug')
            return None
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        MIN_DISCOVER = 1200
        MAX_DISCOVER = 1600
        w2, h2 = img.size
        if w2 < MIN_DISCOVER:
            ratio = MIN_DISCOVER / w2
            nuevo_w = MIN_DISCOVER
            nuevo_h = int(h2 * ratio)
            img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)
            log(f"🔍 Imagen ampliada: {w2}x{h2} → {nuevo_w}x{nuevo_h} (Discover)", 'debug')
        elif w2 > MAX_DISCOVER:
            ratio = MAX_DISCOVER / w2
            nuevo_w = MAX_DISCOVER
            nuevo_h = int(h2 * ratio)
            img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)
            log(f"📐 Imagen reducida: {w2}x{h2} → {nuevo_w}x{nuevo_h}", 'debug')
        img = agregar_watermark(img)
        p   = f'/tmp/noticia_{generar_hash(url)}.jpg'
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
    try:
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        ancho, alto = img.size
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
        overlay_draw.rounded_rectangle(
            [x - padding, y - padding, x + txt_w + padding, y + txt_h + padding],
            radius=6, fill=(0, 0, 0, 180)
        )
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((x + 1, y + 1), texto_wm, font=font_wm, fill=(0, 0, 0, 200))
        draw.text((x, y), texto_wm, font=font_wm, fill='#f5c518')
        return img
    except Exception as e:
        log(f"⚠️ Watermark error: {e}", 'debug')
        return img
def crear_imagen_titulo(titulo, categoria='general'):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        W, H = 1600, 900
        img  = Image.new('RGB', (W, H), color='#0f172a')
        draw = ImageDraw.Draw(img)
        for i in range(H):
            ratio = i / H
            r = int(15  + (30 - 15)  * ratio)
            g = int(23  + (41 - 23)  * ratio)
            b = int(42  + (69 - 42)  * ratio)
            draw.line([(0, i), (W, i)], fill=(r, g, b))
        draw.rectangle([(0, 0), (W, 10)], fill='#dc2626')
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
        for linea in lineas:
            draw.text((72, y_texto + 2), linea, font=font_titulo, fill=(0, 0, 0, 120))
            y_texto += font_size_titulo + 14
        y_texto = max(160, (H - alto_total_texto) // 2 - 40)
        for linea in lineas:
            draw.text((70, y_texto), linea, font=font_titulo, fill='#f1f5f9')
            y_texto += font_size_titulo + 14
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
# MAIN — FLUJO PRINCIPAL V18.0
# ──────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print(f"🌍 BOT DE NOTICIAS - {VERSION_BOT}")
    print("   WP: MÁXIMO 6 noticias/día — TODAS las categorías compiten juntas")
    print("        (incluye Chile/LATAM, fusionado al flujo único desde V18.0)")
    print("   ROTACIÓN: no se repite categoría en el mismo día (15 categorías")
    print("        reales del menú, 6 cupos — ver CATEGORIAS_ROTACION_WP)")
    print("   EVERGREEN: se prioriza contenido con valor SEO duradero sobre")
    print("        noticias efímeras (bonus_durabilidad en calcular_puntaje)")
    print("   FB: imagen+texto desde verdadhoy.com (deshabilitado por defecto)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    if MODO_LATAM:
        log("ℹ️ MODO_LATAM=true detectado, pero desde V18.0 el bloque Chile+LATAM "
            "se fusionó al flujo único (todas las categorías compiten por las mismas "
            "6 publicaciones/día). Se ejecuta igual el flujo unificado — puedes quitar "
            "la variable MODO_LATAM y el cron duplicado del .yml de GitHub Actions, "
            "ya no hace falta un segundo horario para LATAM.", 'advertencia')
    # ── FLUJO ÚNICO V18.0 ────────────────────────────────────
    procesar_pending_videos()
    publicar_wp = puede_publicar_wp()
    h = cargar_historial()
    publicar_fb = PUBLICAR_EN_FACEBOOK and puede_publicar_fb(h)
    if not PUBLICAR_EN_FACEBOOK:
        log("📘 Publicación en Facebook DESACTIVADA (PUBLICAR_EN_FACEBOOK=False) — esto es intencional, no un error", 'info')
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
        # V18.0: se reúnen TODAS las fuentes en un solo pool — general +
        # Chile + LATAM. Antes Chile/LATAM vivían en un flujo aparte
        # (MODO_LATAM) con su propio cupo; ahora compiten por los mismos 6
        # cupos/día junto con todo lo demás. calcular_puntaje() ya da bonus
        # fuerte por país LATAM/Chile, así que la región sigue bien
        # representada sin necesitar un cupo separado.
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
        noticias.extend(obtener_rss_chile())
        noticias.extend(obtener_newsapi_chile())
        noticias.extend(obtener_rss_latam())
        noticias.extend(obtener_newsapi_latam())
        if not noticias:
            log("ERROR: Ninguna fuente devolvió noticias", 'error')
        else:
            noticias = deduplicar_batch(noticias)
            for n in noticias:
                n['puntaje'] = n.get('puntaje', 0) + bonus_frescura(n.get('fecha'))
            noticias.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
            log(f"📰 Candidatas ordenadas: {len(noticias)}", 'info')
            candidatas_validas = []
            intentos     = 0
            MAX_PUBLICACIONES_INTENTOS = 5
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
                es_spam, keyword_spam = es_contenido_spam(titulo, desc)
                if es_spam:
                    log(f"   🚫 SPAM/APUESTAS detectado: '{keyword_spam}' — descartando", 'advertencia')
                    continue
                cont_web, _ = extraer_contenido(url)
                if cont_web and len(cont_web) >= 500:
                    contenido_ok = cont_web
                elif desc and len(desc) >= 400:
                    contenido_ok = desc
                elif cont_web and len(cont_web) >= 250:
                    contenido_ok = cont_web + ' ' + desc if desc else cont_web
                else:
                    log("   ❌ Contenido insuficiente (<250 chars) — no hay material para un artículo real", 'advertencia')
                    continue
                es_spam2, kw_spam2 = es_contenido_spam(titulo, contenido_ok[:3000])
                if es_spam2:
                    log(f"   🚫 SPAM/APUESTAS detectado en el contenido: '{kw_spam2}' — descartando", 'advertencia')
                    continue
                imagen_encontrada = None
                if nt.get('imagen'):
                    imagen_encontrada = descargar_imagen(nt['imagen'])
                if not imagen_encontrada:
                    img_url = extraer_imagen_web(url)
                    if img_url:
                        imagen_encontrada = descargar_imagen(img_url)
                if not imagen_encontrada:
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
                # V18.0: ROTACIÓN DE CATEGORÍAS — con tope de 6 noticias/día y
                # 15 categorías reales en el menú, el objetivo es que esas 6
                # noticias caigan en categorías DISTINTAS siempre que sea
                # posible. Se estima la categoría final de cada candidata
                # (misma lógica que usará publicar_en_wordpress vía
                # resolver_categoria_wp) y se reordena: primero las
                # candidatas cuya categoría estimada NO se usó hoy, por
                # puntaje; después el resto, también por puntaje, como red
                # de seguridad (mejor repetir categoría que no publicar nada).
                categorias_hoy = categorias_usadas_hoy()
                log(f"🔄 Categorías ya usadas hoy: {sorted(categorias_hoy) if categorias_hoy else '(ninguna todavía)'}", 'info')
                def _slug_estimado(item):
                    nt_x, cont_x, _img_x = item
                    tema_x = detectar_tema(nt_x.get('titulo', ''), nt_x.get('descripcion', ''))
                    tema_x = ajustar_categoria_por_cuota(tema_x)
                    return resolver_categoria_wp(tema_x, nt_x.get('titulo', ''), cont_x[:1500])
                candidatas_validas.sort(
                    key=lambda item: (
                        0 if _slug_estimado(item) not in categorias_hoy else 1,
                        -item[0].get('puntaje', 0)
                    )
                )
                for idx_pub, (nt_pub, cont_pub, img_pub) in enumerate(candidatas_validas):
                    log(f"\n📝 SELECCIONADA ({idx_pub+1}/{len(candidatas_validas)}): {nt_pub['titulo'][:70]}")
                    tema_sugerido = detectar_tema(nt_pub['titulo'], nt_pub.get('descripcion', ''))
                    tema_sugerido = ajustar_categoria_por_cuota(tema_sugerido)
                    log(f"   Categoría sugerida (keywords): {tema_sugerido} — la IA decidirá la final", 'info')
                    url_articulo_wp, categoria_wp_final = publicar_en_wordpress(
                        titulo       = nt_pub['titulo'],
                        contenido    = cont_pub,
                        tema         = tema_sugerido,
                        imagen_path  = img_pub,
                        fuente_url   = nt_pub['url'],
                        fecha_fuente = nt_pub.get('fecha'),
                        fuente_noticia = nt_pub.get('fuente', ''),
                    )
                    if url_articulo_wp:
                        seleccionada = nt_pub
                        contenido    = cont_pub
                        img_path     = img_pub
                        exito_wp = True
                        guardar_estado_wp()
                        # V18.0: se registra la cuota/rotación con la
                        # categoría FINAL real (post-IA, post-región) — no
                        # con la sugerencia previa por keywords — para que
                        # categorias_usadas_hoy() refleje lo que de verdad
                        # se publicó.
                        categoria_para_cuota = categoria_wp_final or tema_sugerido
                        registrar_cuota(categoria_para_cuota)
                        h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1
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
                        desc_completa = (seleccionada.get('descripcion', '') + ' ' + contenido[:400]).strip()
                        h = guardar_en_historial(h, seleccionada['url'], seleccionada['titulo'], desc_completa)
                        try:
                            if img_path and os.path.exists(img_path):
                                os.remove(img_path)
                        except:
                            pass
                        break
                    else:
                        log(f"   ⚠️ No se pudo publicar esta noticia — probando siguiente candidata", 'advertencia')
                        try:
                            if img_pub and os.path.exists(img_pub):
                                os.remove(img_pub)
                        except:
                            pass
                        continue
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
        h = cargar_historial()
        articulo_fb = obtener_articulo_wp_para_facebook(h)
        if not articulo_fb:
            log("⚠️ FB: no hay artículo válido con imagen en WP para publicar", 'advertencia')
        else:
            tema_fb = detectar_tema(articulo_fb['titulo'], articulo_fb.get('excerpt', ''))
            texto_fb = construir_texto_facebook(
                titulo    = articulo_fb['titulo'],
                excerpt   = articulo_fb['excerpt'],
                url_wp    = articulo_fb['link'],
                categoria = tema_fb,
            )
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
                try:
                    if img_fb_path and os.path.exists(img_fb_path):
                        os.remove(img_fb_path)
                except:
                    pass
    # Resumen final
    h = cargar_historial()
    stats = h.get('estadisticas', {})
    cuotas_hoy = cargar_cuotas_hoy()
    total_wp_hoy = sum(int(v) for v in cuotas_hoy.get('conteo', {}).values())
    log(f"\n{'='*50}", 'info')
    log(f"✅ RESUMEN {VERSION_BOT}:", 'exito')
    log(f"   WP hoy: {total_wp_hoy}/{MAX_POSTS_WP_DIA} artículos publicados", 'info')
    log(f"   Total acumulado: {stats.get('total_publicadas', 0)}", 'info')
    log(f"   WordPress: {stats.get('total_wp', 0)}", 'info')
    log(f"   Facebook:  {stats.get('total_fb', 0)}", 'info')
    log(f"   Pinterest: {stats.get('total_pinterest', 0)}", 'info')
    categorias_publicadas_hoy = cuotas_hoy.get('conteo', {})
    if categorias_publicadas_hoy:
        detalle_cats = ', '.join(f"{c}:{n}" for c, n in categorias_publicadas_hoy.items())
        log(f"   Categorías publicadas hoy: {detalle_cats}", 'info')
    log(f"   Esta ejecución → WP={'✅' if exito_wp else '❌'} | FB={'✅' if exito_fb else '❌'}", 'info')
    if exito_wp or exito_fb:
        log("💡 Hacer git push de los JSON de estado (incluyendo estado_cuotas.json)", 'advertencia')
        return True
    return False
if __name__ == "__main__":
    try:
        resultado = main()
        exit(0)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
