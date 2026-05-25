#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales - V11.0
NUEVO EN V11:
  - FUNCIÓN 3: Video manual via /pending_videos/ en GitHub
      · Tú subes un archivo .txt con DESCRIPCION y EMBED (iframe de Facebook)
      · El bot lo detecta, genera título SEO, categoría, slug y metadatos con IA
      · Publica en WordPress con video incrustado + Pinterest automático
      · Elimina el archivo de GitHub 24 horas después de publicar
      · Anti-duplicados: estado_pending_videos.json
  - ELIMINADO: sincronizar_videos_facebook_a_wp() — ya no republica posts
    de Facebook a WordPress (generaba contenido pobre: solo descripción + enlace)
  - Pinterest ahora corre en paralelo con Función 1 Y con Función 3

HEREDADO DE V10 (SEO avanzado, Filtro estricto de imágenes):
  - Alt text automático en imágenes subidas a WP
  - Tags automáticos en WP desde keywords_secundarias
  - Schema Markup JSON-LD (NewsArticle)
  - Filtro estricto: noticias sin imagen descartadas desde origen

HEREDADO DE V9 (mejoras de monetización y SEO):
  - Cuotas de mezcla editorial por categoría (CPM optimizado)
  - Prompt SEO avanzado (H1 ≤60, meta 140-155, pirámide invertida, H2/H3)
  - Brand safety automático
  - Fecha de publicación desde fuente original
  - Sección "Te puede interesar" con 2 artículos relacionados de WordPress

HEREDADO DE V8.1:
  - Videos YouTube embebidos automáticos en WordPress
  - Pinterest con tableros por categoría
  - Facebook siempre como VIDEO/Reel
  - Watermark verdadhoy.com en imágenes
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse

# ──────────────────────────────────────────────────────────
# V9: CUOTAS EDITORIALES POR CATEGORÍA (monetización)
# ──────────────────────────────────────────────────────────
# Distribuye artículos diarios según CPM relativo de cada categoría.
# brand_safe=True → mayor valorización publicitaria (AdSense)
CUOTAS_CATEGORIA = {
    'tecnologia':      {'cuota': 0.15, 'cpm_relativo': 1.45, 'brand_safe': True},
    'economia':        {'cuota': 0.15, 'cpm_relativo': 1.55, 'brand_safe': True},
    'ciencia':         {'cuota': 0.10, 'cpm_relativo': 1.40, 'brand_safe': True},
    'salud':           {'cuota': 0.10, 'cpm_relativo': 1.40, 'brand_safe': True},
    'general':         {'cuota': 0.10, 'cpm_relativo': 1.35, 'brand_safe': True},
    'deportes':        {'cuota': 0.05, 'cpm_relativo': 1.20, 'brand_safe': True},
    'entretenimiento': {'cuota': 0.05, 'cpm_relativo': 1.15, 'brand_safe': True},
    'clima':           {'cuota': 0.05, 'cpm_relativo': 1.30, 'brand_safe': True},
    'latinoamerica':   {'cuota': 0.10, 'cpm_relativo': 1.10, 'brand_safe': True},
    'politica':        {'cuota': 0.05, 'cpm_relativo': 1.05, 'brand_safe': False},
    'guerra':          {'cuota': 0.05, 'cpm_relativo': 0.90, 'brand_safe': False},
    'desastre':        {'cuota': 0.05, 'cpm_relativo': 0.95, 'brand_safe': False},
    'mundo':           {'cuota': 0.10, 'cpm_relativo': 1.00, 'brand_safe': True},
}
# Archivo para control de cuotas diarias (se resetea automáticamente cada día)
CUOTAS_CONTROL_PATH = 'estado_cuotas.json'

# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────
NEWS_API_KEY       = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY   = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY      = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID         = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN    = os.getenv('FB_ACCESS_TOKEN')

# ── NUEVO V6: WordPress ────────────────────────────────────
WP_URL             = os.getenv('WP_URL', 'https://verdadhoy.com')
WP_USER            = os.getenv('WP_USER', 'verdadhoy_admin')
WP_APP_PASSWORD    = os.getenv('WP_APP_PASSWORD', '')

# ── NUEVO V8: Pinterest ─────────────────────────────────────
PINTEREST_TOKEN    = os.getenv('PINTEREST_TOKEN', '')

# ── NUEVO V8.1: YouTube embed ───────────────────────────────
YOUTUBE_API_KEY    = os.getenv('YOUTUBE_API_KEY', '')
# Canales oficiales en español — únicos autorizados para embed de video
CANALES_YT_CONFIABLES = [
    "CNN en Español", "CNN en espanol",
    "DW Español", "DW en español",
    "France 24", "France24 Español",
    "BBC News Mundo",
    "Al Jazeera Español",
    "Euronews en español", "euronews (en español)",
    "NTN24",
]

# Mapeo de dominios/fuentes de noticias → nombre de canal YouTube oficial
FUENTE_A_CANAL_YT = {
    "cnn":        "CNN en Español",
    "dw":         "DW Español",
    "france24":   "France 24",
    "bbc":        "BBC News Mundo",
    "aljazeera":  "Al Jazeera Español",
    "euronews":   "Euronews en español",
    "ntn24":      "NTN24",
}

# RUTAS
HISTORIAL_PATH     = os.getenv('HISTORIAL_PATH', 'historial_publicaciones.json')
ESTADO_PATH        = os.getenv('ESTADO_PATH',    'estado_bot.json')
ESTADO_WP_PATH     = 'estado_wp.json'   # control separado para WordPress
ESTADO_FB_PATH     = 'estado_fb.json'   # control separado para Facebook
ESTADO_FORMATO_PATH = 'estado_formato_fb.json'  # alterna video/imagen
# V10: Historial para Sync FB -> WP (ELIMINADO EN V11 — ya no se usa)
ESTADO_FB_SYNC_PATH = 'estado_fb_to_wp.json'

# V11: Pending videos — carpeta en GitHub y control de estado
PENDING_VIDEOS_DIR  = 'pending_videos'
ESTADO_PENDING_PATH = 'estado_pending_videos.json'
GITHUB_TOKEN        = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO         = os.getenv('GITHUB_REPOSITORY', '')  # ej: appcml/bot-noticias-facebook

# Tiempos
TIEMPO_ENTRE_WP_MIN    = 30   # WordPress: cada 30 minutos
TIEMPO_ENTRE_FB_MIN    = 55   # Facebook: mínimo 55 min entre posts
UMBRAL_SIMILITUD_TITULO    = 0.72
UMBRAL_SIMILITUD_CONTENIDO = 0.62
MAX_TITULOS_HISTORIA       = 300
DIAS_HISTORIAL             = 14

# ── ENGAGEMENT ─────────────────────────────────────────────
MAX_POSTS_FB_DIA  = 8   # Facebook: máximo 8/día
MAX_POSTS_WP_DIA  = 48  # WordPress: máximo 48/día (cada 30 min)

# Horarios pico Facebook (hora UTC) — solo para RRSS
HORARIOS_PICO_UTC = [
    (0, 4),
    (10, 14),
    (17, 22),
]

# ── CATEGORÍAS WORDPRESS ────────────────────────────────────
# Deben coincidir con los slugs que creaste en WordPress
CATEGORIA_WP = {
    'guerra':           'internacional',
    'politica':         'politica',
    'economia':         'economia',
    'tecnologia':       'tecnologia',
    'desastre':         'mundo',
    'deportes':         'deportes',
    'ciencia':          'ciencia-y-salud',
    'salud':            'ciencia-y-salud',
    'entretenimiento':  'entretenimiento',
    'latinoamerica':    'latinoamerica',
    'clima':            'medio-ambiente',
    'mundo':            'mundo',
    'general':          'internacional',
}

# IDs de categorías WordPress (se obtienen automáticamente al publicar)
_cache_categorias_wp = {}
# V10: caché de tags WordPress (nombre_lower -> id)
_cache_tags_wp = {}

# ── TABLEROS PINTEREST (nombres exactos como los creaste) ───
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
    'mundo':           'Noticias del Mundo',
    'general':         'Noticias del Mundo',
}
_cache_tableros_pinterest = {}  # nombre -> board_id

# CTAs por tema para Facebook
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

CTAS_VIDEO_POR_TEMA = {
    'guerra':          "¿Crees que esto escalará?",
    'politica':        "¿Estás de acuerdo?  SÍ o NO",
    'economia':        "¿Te afecta esto?",
    'tecnologia':      "¿A favor o en contra?",
    'desastre':        "Deja tu mensaje de apoyo 🙏",
    'deportes':        "¿Qué opinas del resultado?",
    'ciencia':         "¿Lo sabías? ¡Comenta!",
    'salud':           "¿Cuidas tu salud? SÍ o NO",
    'entretenimiento': "¿Estás de acuerdo? Opina",
    'latinoamerica':   "¿Cómo afecta a tu país?",
    'clima':           "¿Sientes el cambio climático?",
    'mundo':           "¿Qué opinas del mundo hoy?",
    'general':         "¿Qué opinas de esta noticia?",
}

CTA_VIDEO_CIERRE = "💬 Comenta · 👍 Reacciona · 🔁 Comparte\nMás detalles en la descripción 👇"

VOCES_TTS = [
    "es-MX-DaliaNeural",
    "es-MX-JorgeNeural",
    "es-CO-SalomeNeural",
    "es-AR-ElenaNeural",
]

# ──────────────────────────────────────────────────────────
# V9: CONTROL DE CUOTAS DIARIAS POR CATEGORÍA
# ──────────────────────────────────────────────────────────
def cargar_cuotas_hoy():
    """Carga el conteo de artículos publicados hoy por categoría."""
    datos = cargar_json(CUOTAS_CONTROL_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if datos.get('fecha') != hoy:
        return {'fecha': hoy, 'conteo': {}}
    return datos

def registrar_cuota(categoria):
    """Suma 1 al conteo de la categoría del día."""
    datos = cargar_cuotas_hoy()
    datos['conteo'][categoria] = datos['conteo'].get(categoria, 0) + 1
    guardar_json(CUOTAS_CONTROL_PATH, datos)

def categoria_disponible(categoria, total_dia=48):
    """
    Retorna True si la categoría aún tiene cuota disponible para hoy.
    Si la categoría supera su cuota, se busca una alternativa brand-safe.
    """
    datos = cargar_cuotas_hoy()
    conteo = datos['conteo'].get(categoria, 0)
    maximo = max(1, int(total_dia * CUOTAS_CATEGORIA.get(categoria, {}).get('cuota', 0.10)))
    return conteo < maximo

def ajustar_categoria_por_cuota(categoria):
    """
    Si la categoría detectada ya agotó su cuota diaria,
    retorna la categoría brand-safe con más cuota disponible.
    """
    if categoria_disponible(categoria):
        return categoria
    log(f"📊 Cuota llena para '{categoria}' — buscando alternativa brand-safe", 'advertencia')
    # Ordenar por CPM descendente, solo brand-safe con cuota disponible
    alternativas = sorted(
        [(c, v) for c, v in CUOTAS_CATEGORIA.items()
         if v.get('brand_safe') and categoria_disponible(c)],
        key=lambda x: -x[1]['cpm_relativo']
    )
    if alternativas:
        nueva = alternativas[0][0]
        log(f"   → Reasignado a '{nueva}' (CPM {CUOTAS_CATEGORIA[nueva]['cpm_relativo']}x)", 'info')
        return nueva
    return categoria  # si todo lleno, publicar igual

def es_brand_safe(categoria):
    """Retorna True si la categoría es brand-safe para AdSense."""
    return CUOTAS_CATEGORIA.get(categoria, {}).get('brand_safe', True)

# ──────────────────────────────────────────────────────────
# V9: REESCRITURA MEJORADA CON SEO Y BRAND SAFETY
# ──────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENAI_API_KEY     = os.getenv('OPENAI_API_KEY', '')

def reescribir_noticia_v9(titulo, contenido, categoria):
    """
    Reescribe la noticia con prompt optimizado para SEO y monetización.
    Aplica brand safety automático en categorías de conflicto/violencia.
    Retorna dict con: titulo_seo, meta_descripcion, contenido_html,
                      keyword_principal, keywords_secundarias
    Requiere OPENROUTER_API_KEY u OPENAI_API_KEY en GitHub Secrets.
    """
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        return None  # sin clave IA, usar flujo anterior

    brand_safe = es_brand_safe(categoria)
    instruccion_brand_safe = ""
    if not brand_safe:
        instruccion_brand_safe = """
BRAND SAFETY (OBLIGATORIO): Esta noticia involucra conflicto, violencia o política sensible.
Reencuadra el contenido enfocándote EN:
- Implicaciones económicas y de mercados financieros
- Consecuencias geopolíticas y diplomáticas a largo plazo
- Impacto en energía, comercio o tecnología
- Respuesta humanitaria e institucional
EVITA completamente: lenguaje violento o gráfico, conteo de bajas,
detalles militares tácticos, imágenes de shock emocional negativo."""

    prompt = f"""Eres el Editor Jefe Digital de VerdadHoy.com, medio de noticias en español para audiencia global hispanohablante. Tu objetivo es maximizar SEO, tiempo de lectura y seguridad de marca para monetización con Google AdSense.

NOTICIA ORIGINAL:
Título: {titulo}
Categoría: {categoria}
Contenido: {contenido[:2500]}
{instruccion_brand_safe}

REGLAS DE FORMATO (OBLIGATORIAS):

TÍTULO H1:
- Máximo 60 caracteres incluyendo espacios
- Keyword principal en las primeras 3 palabras
- Directo e informativo, sin clickbait

META DESCRIPCIÓN:
- Entre 140 y 155 caracteres exactos
- Resume el valor informativo
- Incluye keyword secundaria natural

CUERPO DEL ARTÍCULO (HTML):
- PRIMER PÁRRAFO: responde Qué/Quién/Cuándo/Dónde/Por qué en máximo 50 palabras (pirámide invertida)
- Subtítulos <h2> cada 150-200 palabras con keywords secundarias
- Párrafos de máximo 3 líneas
- 1 lista <ul><li> con 3-4 puntos si hay causas, consecuencias o datos clave
- Entre 3 y 4 palabras o frases en <strong> (términos técnicos o nombres clave)
- Mínimo 350 palabras, máximo 600 palabras
- Al final del artículo agrega EXACTAMENTE esta línea: [ENLACES_INTERNOS]

TONO: Profesional, informativo, en español neutro internacional. Sin opinión política explícita.

RESPONDE ÚNICAMENTE con este JSON sin markdown ni texto adicional:
{{"titulo_seo": "...", "meta_descripcion": "...", "contenido_html": "<p>...</p>...[ENLACES_INTERNOS]", "keyword_principal": "...", "keywords_secundarias": ["...", "..."]}}"""

    try:
        # Intentar con OpenRouter primero, luego OpenAI directo
        if OPENROUTER_API_KEY:
            url_api   = "https://openrouter.ai/api/v1/chat/completions"
            headers   = {"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                         "Content-Type": "application/json"}
            modelo    = "openai/gpt-4o-mini"
        else:
            url_api   = "https://api.openai.com/v1/chat/completions"
            headers   = {"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"}
            modelo    = "gpt-4o-mini"

        payload = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1400,
        }
        resp = requests.post(url_api, headers=headers, json=payload, timeout=30)
        texto = resp.json()["choices"][0]["message"]["content"].strip()
        # Limpiar posibles markdown fences
        texto = re.sub(r'^```json\s*|```$', '', texto, flags=re.MULTILINE).strip()
        resultado = json.loads(texto)
        log(f"✅ V9 SEO — Título: {resultado.get('titulo_seo','')[:55]}", 'info')
        log(f"✅ V9 SEO — Meta ({len(resultado.get('meta_descripcion',''))} chars)", 'info')
        return resultado
    except Exception as e:
        log(f"⚠️ reescribir_noticia_v9 error: {e} — usando flujo estándar", 'advertencia')
        return None

# ──────────────────────────────────────────────────────────
# V9: ENLACES INTERNOS AUTOMÁTICOS
# ──────────────────────────────────────────────────────────
def obtener_articulos_wp_recientes(num=3):
    """Obtiene títulos y URLs de artículos recientes de WordPress."""
    if not WP_APP_PASSWORD:
        return []
    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={'per_page': num + 1, 'status': 'publish',
                    'orderby': 'date', 'order': 'desc',
                    '_fields': 'id,title,link'},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()[:num]
    except Exception as e:
        log(f"⚠️ No se pudieron obtener artículos relacionados: {e}", 'debug')
    return []

def generar_seccion_relacionados(articulos):
    """Genera HTML de la sección 'Te puede interesar'."""
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
    """Reemplaza [ENLACES_INTERNOS] con artículos reales de WordPress."""
    articulos = obtener_articulos_wp_recientes(2)
    html_relacionados = generar_seccion_relacionados(articulos)
    if "[ENLACES_INTERNOS]" in contenido_html:
        return contenido_html.replace("[ENLACES_INTERNOS]", html_relacionados)
    return contenido_html + html_relacionados

# ──────────────────────────────────────────────────────────
# DETECCIÓN DE TEMA
# ──────────────────────────────────────────────────────────
def detectar_tema(titulo, descripcion=""):
    txt = f"{titulo} {descripcion}".lower()
    if any(p in txt for p in ["guerra", "bombardeo", "misil", "ataque", "conflicto",
                               "invasion", "tropas", "nuclear", "terroris", "hamas",
                               "hezbollah", "ucrania", "gaza", "israel", "rusia"]):
        return 'guerra'
    if any(p in txt for p in ["trump", "biden", "presidente", "gobierno", "eleccion",
                               "politica", "congreso", "sancion", "diplomaci",
                               "golpe de estado", "otan", "nato"]):
        return 'politica'
    if any(p in txt for p in ["economia", "inflacion", "recesion", "bolsa", "mercado",
                               "petroleo", "dolar", "fmi", "banco", "crisis economica",
                               "aranceles", "comercio"]):
        return 'economia'
    if any(p in txt for p in ["inteligencia artificial", "tecnologia", "ia ", " ia,", "robot",
                               "ciberataque", "hackeo", "elon musk", "openai", "software",
                               "startup", "samsung", "apple", "google", "microsoft"]):
        return 'tecnologia'
    if any(p in txt for p in ["terremoto", "huracan", "inundacion", "desastre",
                               "victimas", "muertos", "evacuacion", "tsunami", "explosion"]):
        return 'desastre'
    if any(p in txt for p in ["futbol", "deporte", "olimpiadas", "mundial", "copa",
                               "atletismo", "tenis", "baloncesto", "nba", "fifa",
                               "formula 1", "f1", "champions", "liga", "gol"]):
        return 'deportes'
    if any(p in txt for p in ["cancer", "enfermedad", "hospital", "medico", "tratamiento",
                               "pandemia", "vacuna", "virus", "salud publica", "oms"]):
        return 'salud'
    if any(p in txt for p in ["ciencia", "investigacion", "descubrimiento", "estudio",
                               "espacio", "nasa", "planeta", "universo", "fisica", "quimica"]):
        return 'ciencia'
    if any(p in txt for p in ["clima", "cambio climatico", "calentamiento", "temperatura",
                               "sequia", "incendio forestal", "contaminacion", "co2",
                               "medio ambiente", "cop", "emision"]):
        return 'clima'
    if any(p in txt for p in ["mexico", "colombia", "argentina", "chile", "peru", "venezuela",
                               "brasil", "cuba", "bolivia", "ecuador", "america latina",
                               "latinoamerica", "centroamerica", "caribe"]):
        return 'latinoamerica'
    if any(p in txt for p in ["pelicula", "serie", "musica", "artista", "actor", "actriz",
                               "famoso", "celebridad", "hollywood", "netflix", "oscar",
                               "album", "concierto", "entretenimiento"]):
        return 'entretenimiento'
    if any(p in txt for p in ["africa", "asia", "europa", "oriente medio", "pacifico",
                               "naciones unidas", "onu", "g20", "g7", "cumbre mundial"]):
        return 'mundo'
    return 'general'

def agregar_cta(texto, titulo="", descripcion=""):
    tema = detectar_tema(titulo, descripcion)
    cta  = random.choice(CTAS_POR_TEMA.get(tema, CTAS_POR_TEMA['general']))
    return f"{texto}\n\n{cta}"

def obtener_cta_video(titulo, descripcion=""):
    tema      = detectar_tema(titulo, descripcion)
    linea_cta = CTAS_VIDEO_POR_TEMA.get(tema, CTAS_VIDEO_POR_TEMA['general'])
    return linea_cta, CTA_VIDEO_CIERRE

def obtener_voz_aleatoria():
    voz = random.choice(VOCES_TTS)
    log(f"🎙️ Voz seleccionada: {voz}", 'info')
    return voz

BLACKLIST_TITULOS = [
    r'^\s*última hora\s*$',
    r'^\s*breaking news\s*$',
    r'^\s*noticias de hoy\s*$',
    r'^\s*\d+\s*$',
]

PALABRAS_ALTA_PRIORIDAD = [
    "guerra", "conflicto armado", "invasion", "ofensiva militar", "bombardeo",
    "misiles", "ataque aereo", "drones militares", "movilizacion militar",
    "tropas", "escalada de tension", "amenaza nuclear", "armas nucleares",
    "terrorismo", "atentado", "ataque terrorista",
    "ucrania", "rusia", "israel", "gaza", "iran", "china", "taiwan",
    "corea del norte", "otan", "nato", "brics", "medio oriente",
    "siria", "yemen", "sudan",
    "crisis humanitaria", "refugiados",
    "crisis de gobierno", "golpe de estado", "coup", "estado de emergencia",
    "negociaciones de paz", "alto el fuego", "sanciones internacionales",
    "economia mundial", "inflacion", "crisis economica", "recesion",
    "petroleo", "gas", "crisis energetica",
    "ciberataque", "hackeo", "inteligencia artificial",
    "ultima hora", "urgente", "breaking",
    "putin", "zelensky", "trump", "biden", "netanyahu",
    "xi jinping", "kim jong un", "macron",
    "hamas", "hezbollah", "isis", "taliban", "houthis",
    "elon musk",
]

PALABRAS_MEDIA_PRIORIDAD = [
    "economia", "mercados", "FMI", "banco mundial",
    "tecnologia", "innovacion", "salud", "educacion",
    "medio ambiente", "cambio climatico",
    "comercio internacional", "empresas",
]

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

# Patrones de fuentes/medios que aparecen incrustados en el texto
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

# Frases de suscripción/promoción de medios que se cuelan en el contenido (V9)
_FRASES_SUSCRIPCION = re.compile(
    r'(Recib[ií]\s+en\s+tu\s+mail[^.]*\.?'
    r'|Suscr[ií]bete\s+[^.]*\.?'
    r'|Registrate\s+[^.]*\.?'
    r'|Regístrate\s+[^.]*\.?'
    r'|Suscríbete\s+[^.]*\.?'
    r'|Newsletter\s+[^.]*\.?'
    r'|Boletín\s+[^.]*\.?'
    r'|Boletin\s+[^.]*\.?'
    r'|Haz\s+click\s+[^.]*\.?'
    r'|Haz\s+clic\s+[^.]*\.?'
    r'|Descarga\s+la\s+app\s+[^.]*\.?'
    r'|Descarga\s+nuestra\s+app\s+[^.]*\.?'
    r'|Síguenos\s+en\s+[^.]*\.?'
    r'|Siguenos\s+en\s+[^.]*\.?'
    r'|Todas\s+las\s+noticias[^.]*\.?'
    r'|Más\s+información\s+en\s+[^.]*\.?'
    r'|Para\s+más\s+información[^.]*\.?'
    r'|Lee\s+también[^.]*\.?'
    r'|También\s+te\s+puede\s+interesar[^.]*\.?'
    r'|Te\s+puede\s+interesar[^.]*\.?'
    r'|Enterate\s+[^.]*\.?'
    r'|Entérate\s+[^.]*\.?'
    r'|Mirá\s+también[^.]*\.?'
    r'|Mira\s+también[^.]*\.?'
    r'|Con\s+información\s+de\s+[^.]*\.?'
    r'|Fuente:\s*[A-Z][^.]*\.?'
    r'|Copyright\s+[^.]*\.?'
    r'|Todos\s+los\s+derechos\s+reservados[^.]*\.?'
    r'|©[^.]*\.?)',
    re.IGNORECASE
)

# Links de redes sociales incrustados en el contenido scrapeado (V9)
_LINKS_SOCIALES = re.compile(
    r'(Ver\s+(video|publicación|post|nota)\s+en\s+(Facebook|Instagram|Twitter|X|TikTok|YouTube)[^.]*\.?'
    r'|Ver\s+en\s+(Facebook|Instagram|Twitter|X|TikTok|YouTube)[^.]*\.?'
    r'|Mira\s+(esto|el video|la publicación)\s+en\s+[^.]*\.?'
    r'|Compartir\s+en\s+[^.]*\.?'
    r'|Seguir\s+leyendo[^.]*\.?'
    r'|Leer\s+más[^.]*\.?'
    r'|Ver\s+más[^.]*\.?'
    r'|Continúa\s+leyendo[^.]*\.?'
    r'|Continua\s+leyendo[^.]*\.?'
    r'|La\s+nota\s+completa[^.]*\.?'
    r'|El\s+artículo\s+completo[^.]*\.?)',
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
    # Eliminar nombres de fuentes incrustados en medio del texto
    t = _FUENTES_INCRUSTADAS.sub('', t)
    # V9: Eliminar frases de suscripción/promoción de medios
    t = _FRASES_SUSCRIPCION.sub('', t)
    # V9: Eliminar links/referencias a redes sociales incrustados
    t = _LINKS_SOCIALES.sub('', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if t and t[-1] not in '.!?':
        t += '.'
    return t.strip()

def calcular_puntaje(titulo, desc):
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
    return p

# ──────────────────────────────────────────────────────────
# HISTORIAL
# ──────────────────────────────────────────────────────────
HISTORIAL_DEFAULT = {
    'urls': [],
    'urls_normalizadas': [],
    'hashes': [],
    'timestamps': [],
    'titulos': [],
    'descripciones': [],
    'hashes_contenido': [],
    'hashes_permanentes': [],
    'estadisticas': {'total_publicadas': 0, 'total_wp': 0, 'total_fb': 0}
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
    claves_con_indice = ['urls', 'urls_normalizadas', 'hashes', 'timestamps',
                         'titulos', 'descripciones', 'hashes_contenido']
    for key in claves_con_indice:
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
        sim = similitud_titulos(titulo, th)
        if sim >= UMBRAL_SIMILITUD_TITULO:
            return True, f"titulo_similar_{sim:.2f}"
    for i, uh in enumerate(h.get('urls', [])):
        if extraer_dominio(uh) == dominio and i < len(h.get('titulos', [])):
            sim = similitud_titulos(titulo, h['titulos'][i])
            if sim >= 0.82:
                return True, f"mismo_sitio_{sim:.2f}"
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
    if guardar_json(HISTORIAL_PATH, h):
        log(f"💾 Historial guardado: {len(h['urls'])} entradas", 'exito')
    return h

# ──────────────────────────────────────────────────────────
# CONTROL DE TIEMPO — SEPARADO PARA WP Y FB
# ──────────────────────────────────────────────────────────
def puede_publicar_wp():
    """WordPress: cada 30 minutos, todo el día."""
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True
    e = cargar_json(ESTADO_WP_PATH, {'ultima_publicacion': None})
    u = e.get('ultima_publicacion')
    if not u:
        return True
    try:
        minutos = (datetime.now() - datetime.fromisoformat(u)).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_WP_MIN:
            log(f"⏱️ WP: publicado hace {minutos:.0f} min — mínimo {TIEMPO_ENTRE_WP_MIN} min", 'info')
            return False
    except:
        pass
    return True

def puede_publicar_fb(h):
    """Facebook: solo en horario pico + máximo 8/día + mínimo 55 min entre posts."""
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True

    # Control horario pico
    hora_utc = datetime.utcnow().hour
    en_pico = any(inicio <= hora_utc < fin for inicio, fin in HORARIOS_PICO_UTC)
    if not en_pico:
        log(f"⏰ FB: fuera de horario pico (UTC {hora_utc:02d}h)", 'info')
        return False

    # Control límite diario
    hoy = datetime.now().date()
    posts_hoy = sum(
        1 for ts in h.get('timestamps', [])
        if ts and datetime.fromisoformat(ts).date() == hoy
    )
    if posts_hoy >= MAX_POSTS_FB_DIA:
        log(f"🚫 FB: límite diario alcanzado ({posts_hoy}/{MAX_POSTS_FB_DIA})", 'advertencia')
        return False

    # Control tiempo mínimo entre posts
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
# NUEVO V6: PUBLICAR EN WORDPRESS
# ──────────────────────────────────────────────────────────
def obtener_id_categoria_wp(slug_categoria):
    """Obtiene el ID de una categoría de WordPress por su slug."""
    global _cache_categorias_wp
    if slug_categoria in _cache_categorias_wp:
        return _cache_categorias_wp[slug_categoria]
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories",
            params={'slug': slug_categoria, 'per_page': 1},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=15
        ).json()
        if r and isinstance(r, list) and len(r) > 0:
            cat_id = r[0]['id']
            _cache_categorias_wp[slug_categoria] = cat_id
            log(f"📂 Categoría WP '{slug_categoria}' → ID {cat_id}", 'info')
            return cat_id
    except Exception as e:
        log(f"⚠️ Error obteniendo categoría WP '{slug_categoria}': {e}", 'advertencia')
    return None

def obtener_crear_tag_wp(nombre_tag):
    """
    V10 SEO: Obtiene el ID de un tag existente en WordPress o lo crea si no existe.
    Usa caché en memoria para evitar peticiones repetidas en el mismo ciclo.
    """
    global _cache_tags_wp
    tag_clean = nombre_tag.lower().strip()
    if not tag_clean or len(tag_clean) < 2:
        return None
    if tag_clean in _cache_tags_wp:
        return _cache_tags_wp[tag_clean]
    try:
        # Buscar tag existente
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/tags",
            params={'search': tag_clean, 'per_page': 5},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=10
        ).json()
        if r and isinstance(r, list):
            for tag in r:
                if tag.get('name', '').lower() == tag_clean:
                    _cache_tags_wp[tag_clean] = tag['id']
                    return tag['id']
        # Crear tag nuevo
        r_post = requests.post(
            f"{WP_URL}/wp-json/wp/v2/tags",
            json={'name': nombre_tag.strip()},
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=10
        ).json()
        if 'id' in r_post:
            _cache_tags_wp[tag_clean] = r_post['id']
            log(f"🏷️ Tag WP creado: '{nombre_tag}' → ID {r_post['id']}", 'info')
            return r_post['id']
    except Exception as e:
        log(f"⚠️ Error gestionando tag '{nombre_tag}': {e}", 'debug')
    return None

def subir_imagen_wp(imagen_path, titulo, alt_text=""):
    """
    Sube una imagen a la biblioteca de medios de WordPress.
    V10 SEO: acepta alt_text y lo aplica vía PATCH después de subir.
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
                auth=(WP_USER, WP_APP_PASSWORD),
                timeout=60
            ).json()
        if 'id' in r:
            media_id = r['id']
            log(f"🖼️ Imagen subida a WP — ID: {media_id}", 'exito')
            # V10 SEO: asignar alt_text si está disponible
            if alt_text:
                try:
                    requests.post(
                        f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                        json={'alt_text': alt_text[:125]},
                        auth=(WP_USER, WP_APP_PASSWORD),
                        timeout=10
                    )
                    log(f"🏷️ Alt text asignado: '{alt_text[:60]}'", 'debug')
                except Exception as e:
                    log(f"⚠️ No se pudo asignar alt_text: {e}", 'debug')
            return media_id
        else:
            log(f"⚠️ Error subiendo imagen a WP: {r.get('message', 'desconocido')}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Excepción subiendo imagen WP: {e}", 'advertencia')
    return None

def detectar_canal_oficial(fuente_str):
    """
    Detecta si la noticia viene de un canal oficial con video en YouTube.
    Retorna el nombre del canal YouTube o None si no es fuente oficial.
    """
    if not fuente_str:
        return None
    fuente_lower = fuente_str.lower()
    for clave, canal in FUENTE_A_CANAL_YT.items():
        if clave in fuente_lower:
            return canal
    return None

def buscar_video_youtube(titulo, canal_preferido=None):
    """
    Busca en YouTube el video de la noticia en el canal oficial correspondiente.
    - Solo se ejecuta si la noticia viene de un canal oficial (canal_preferido definido).
    - Verifica que el video encontrado sea del mismo canal oficial.
    - Retorna HTML del iframe o None si no encuentra.
    """
    if not YOUTUBE_API_KEY:
        return None

    if not canal_preferido:
        return None  # Solo buscar si la noticia viene de canal oficial

    try:
        palabras_titulo = ' '.join(titulo.split()[:7])
        query = f"{palabras_titulo} {canal_preferido}"

        from datetime import timezone
        fecha_limite = (datetime.now(timezone.utc) - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ')

        params = {
            "q": query,
            "type": "video",
            "maxResults": 8,
            "relevanceLanguage": "es",
            "order": "relevance",
            "publishedAfter": fecha_limite,
            "key": YOUTUBE_API_KEY
        }

        resp = requests.get("https://www.googleapis.com/youtube/v3/search",
                            params=params, timeout=10)
        data = resp.json()

        if "error" in data:
            log(f"⚠️ YouTube API error: {data['error'].get('message','')}", 'advertencia')
            return None

        items = data.get("items", [])
        if not items:
            log(f"📭 Sin videos YouTube para: {titulo[:50]}", 'info')
            return None

        # Solo aceptar video si el canal coincide con el canal oficial de la noticia
        for item in items:
            channel     = item["snippet"]["channelTitle"]
            video_id    = item["id"]["videoId"]
            video_titulo = item["snippet"]["title"]

            if canal_preferido.lower() in channel.lower():
                log(f"🎬 Video encontrado: {video_titulo[:50]} | Canal: {channel}", 'exito')
                embed_html = f"""
<div class="video-relacionado" style="margin:30px 0; padding:20px; background:#f8f8f8; border-left:4px solid #cc0000; border-radius:4px;">
<h3 style="margin-top:0; color:#1a1a2e; font-size:1.1em;">📺 Video relacionado</h3>
<div style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden;">
<iframe
    style="position:absolute; top:0; left:0; width:100%; height:100%;"
    src="https://www.youtube.com/embed/{video_id}?rel=0"
    title="{video_titulo}"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
</iframe>
</div>
<p style="margin-bottom:0; font-size:0.85em; color:#666;">Fuente: {channel} (YouTube)</p>
</div>"""
                return embed_html

        log(f"📭 No se encontró video de '{canal_preferido}' para: {titulo[:50]}", 'info')
        return None

    except Exception as e:
        log(f"⚠️ Error buscando video YouTube: {e}", 'advertencia')
        return None


def publicar_en_wordpress(titulo, contenido, tema, imagen_path, fuente_url, fecha_fuente=None, fuente_noticia=None):
    """
    Publica una noticia en WordPress y retorna la URL del artículo.
    REQUIERE imagen obligatoriamente.
    V9: reescritura SEO con IA, brand safety, fecha real y enlaces internos.
    V10: alt_text en imágenes, tags automáticos desde keywords IA, Schema JSON-LD.
    """
    if not WP_APP_PASSWORD:
        log("⚠️ WP_APP_PASSWORD no configurado — saltando WordPress", 'advertencia')
        return None

    if not imagen_path:
        log("❌ No hay imagen — no se publica en WordPress", 'error')
        return None

    # Extraer nombre del medio desde la URL de la fuente
    def extraer_nombre_medio(url):
        try:
            from urllib.parse import urlparse
            dominio = urlparse(url).netloc.lower()
            dominio = re.sub(r'^(www\.|m\.)', '', dominio)
            # Mapeo de dominios conocidos a nombres
            mapa = {
                'listindiario.com': 'Listín Diario',
                'elpais.com': 'El País',
                'bbc.com': 'BBC Mundo', 'bbc.co.uk': 'BBC Mundo',
                'cnn.com': 'CNN en Español',
                'infobae.com': 'Infobae',
                'reuters.com': 'Reuters',
                'france24.com': 'France 24',
                'efe.com': 'EFE',
                'laopinioncoruna.es': 'La Opinión A Coruña',
                'dw.com': 'Deutsche Welle',
                'euronews.com': 'Euronews',
                'theguardian.com': 'The Guardian',
                'nytimes.com': 'New York Times',
            }
            for dom, nombre in mapa.items():
                if dom in dominio:
                    return nombre
            partes = dominio.split('.')
            return partes[-2].capitalize() if len(partes) >= 2 else dominio
        except:
            return 'Fuente externa'

    nombre_medio = extraer_nombre_medio(fuente_url)

    # ── V9: Intentar reescritura mejorada con IA ───────────────
    resultado_ia = reescribir_noticia_v9(titulo, contenido, tema)

    # V10 SEO: preparar alt_text y tags desde resultado IA
    alt_text_imagen = titulo[:125]
    tags_ids = []

    if resultado_ia:
        titulo_final         = resultado_ia.get('titulo_seo', titulo)[:60] or titulo
        meta_desc            = resultado_ia.get('meta_descripcion', '')
        frase_clave          = resultado_ia.get('keyword_principal', '')
        contenido_formateado = resultado_ia.get('contenido_html', '')
        contenido_formateado = insertar_enlaces_internos(contenido_formateado)
        log("✅ V9: usando contenido reescrito por IA con SEO avanzado", 'exito')

        # V10 SEO: Alt text = keyword_principal + título SEO
        if frase_clave:
            alt_text_imagen = f"{frase_clave} - {titulo_final}"[:125]

        # V10 SEO: Tags desde keywords_secundarias de la IA (hasta 5)
        for kw in resultado_ia.get('keywords_secundarias', [])[:5]:
            tag_id = obtener_crear_tag_wp(kw)
            if tag_id:
                tags_ids.append(tag_id)
        if tags_ids:
            log(f"🏷️ Tags asignados al post: {resultado_ia.get('keywords_secundarias', [])[:5]}", 'info')
    else:
        # Fallback: flujo estándar V8
        titulo_final = titulo
        oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        parrafos_html = []
        parrafo_actual = []
        palabras = 0
        for oracion in oraciones:
            parrafo_actual.append(oracion)
            palabras += len(oracion.split())
            if palabras >= 60:
                parrafos_html.append(f'<p>{" ".join(parrafo_actual)}</p>')
                parrafo_actual = []
                palabras = 0
        if parrafo_actual:
            parrafos_html.append(f'<p>{" ".join(parrafo_actual)}</p>')
        contenido_formateado = '\n'.join(parrafos_html[:15])
        contenido_formateado += insertar_enlaces_internos("")
        meta_desc   = ""
        frase_clave = ""

    # ── V9: Video YouTube — solo si la noticia viene de canal oficial ──
    video_embed_html = ""
    if YOUTUBE_API_KEY:
        canal_oficial = detectar_canal_oficial(fuente_noticia)
        if canal_oficial:
            log(f"🎬 Noticia de canal oficial '{canal_oficial}' → buscando video en YouTube...", 'info')
            video_embed_html = buscar_video_youtube(titulo, canal_oficial) or ""
            if not video_embed_html:
                log(f"📭 Sin video disponible — publicando solo con imagen", 'info')
        else:
            log(f"📰 Fuente no oficial → sin búsqueda de video", 'info')

    # ── V10 SEO: Schema Markup JSON-LD NewsArticle ─────────────
    fecha_schema = datetime.now().isoformat()
    if fecha_fuente:
        try:
            fecha_schema = str(fecha_fuente).replace('Z', '+00:00')
            datetime.fromisoformat(fecha_schema)  # validar
        except:
            fecha_schema = datetime.now().isoformat()

    titulo_schema  = titulo_final.replace('"', "'").replace('\\', '')
    meta_schema    = (meta_desc or contenido[:155]).replace('"', "'").replace('\\', '')
    schema_markup = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "{titulo_schema}",
  "datePublished": "{fecha_schema}",
  "dateModified": "{datetime.now().isoformat()}",
  "description": "{meta_schema}",
  "inLanguage": "es",
  "publisher": {{
    "@type": "Organization",
    "name": "Verdad Hoy",
    "url": "{WP_URL}",
    "logo": {{
      "@type": "ImageObject",
      "url": "{WP_URL}/wp-content/uploads/favicon_512.png"
    }}
  }},
  "author": {{
    "@type": "Organization",
    "name": "Verdad Hoy"
  }}
}}
</script>"""

    contenido_html = f"""
{contenido_formateado}

{video_embed_html}

<hr>
<p><strong>Fuente:</strong> {nombre_medio}</p>
<p><em>Información verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
{schema_markup}
"""

    # ── V9: SEO mejorado ─────────────────────────────────────────
    stopwords_es = {
        'para','como','este','esta','esto','pero','porque','cuando','donde',
        'quien','cuyo','cuya','ante','bajo','cabe','cada','con','contra',
        'desde','durante','entre','hacia','hasta','mediante','por','según',
        'tras','versus','vía','una','uno','unos','unas','los','las','del',
        'que','sus','les','más','sin','sobre','también','hay','han','sido'
    }

    if not frase_clave:
        palabras_clave = [
            p for p in re.findall(r'\b\w{4,}\b', titulo_final.lower())
            if p not in stopwords_es
        ]
        frase_clave = ' '.join(palabras_clave[:4])

    sufijo_seo = ' | Verdad Hoy'
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
            extracto_crudo = ' '.join(contenido.split())
            meta_desc = extracto_crudo[:152].rsplit(' ', 1)[0] + '...'
        else:
            meta_desc = primera_oracion

    extracto = meta_desc

    log(f"🔍 SEO — Título: {titulo_seo}", 'info')
    log(f"🔍 SEO — Meta ({len(meta_desc)} chars): {meta_desc[:80]}...", 'info')
    log(f"🔍 SEO — Frase clave: {frase_clave}", 'info')

    # ── V9: Fecha desde la fuente original ───────────────────────
    fecha_wp = None
    if fecha_fuente:
        try:
            fecha_str = str(fecha_fuente).replace('Z', '+00:00')
            dt = datetime.fromisoformat(fecha_str)
            fecha_wp = dt.strftime('%Y-%m-%dT%H:%M:%S')
        except Exception:
            fecha_wp = None

    # ── V10: Subir imagen con alt_text ───────────────────────────
    imagen_id = subir_imagen_wp(imagen_path, titulo, alt_text=alt_text_imagen)
    if not imagen_id:
        log("❌ No se pudo subir imagen a WP — cancelando", 'error')
        return None

    # Obtener categoría
    slug_cat   = CATEGORIA_WP.get(tema, 'internacional')
    cat_id     = obtener_id_categoria_wp(slug_cat)
    categorias = [cat_id] if cat_id else []

    # Datos del post — V10: incluye 'tags'
    post_data = {
        'title':          titulo_final,
        'content':        contenido_html,
        'excerpt':        extracto,
        'status':         'publish',
        'featured_media': imagen_id,
        'categories':     categorias,
        'tags':           tags_ids,   # V10 SEO
        'meta': {
            '_yoast_wpseo_title':    titulo_seo,
            '_yoast_wpseo_metadesc': meta_desc,
            '_yoast_wpseo_focuskw':  frase_clave,
        }
    }
    if fecha_wp:
        post_data['date'] = fecha_wp
        log(f"📅 Fecha publicación (fuente original): {fecha_wp}", 'info')

    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        ).json()

        if 'id' in r:
            url_articulo = r.get('link', f"{WP_URL}/?p={r['id']}")
            log(f"✅ Publicado en WordPress — ID: {r['id']} | URL: {url_articulo}", 'exito')
            return url_articulo
        else:
            log(f"❌ Error WordPress: {r.get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando en WP: {e}", 'error')

    return None

# ──────────────────────────────────────────────────────────
# FUENTES DE NOTICIAS
# ──────────────────────────────────────────────────────────
def obtener_newsapi():
    if not NEWS_API_KEY:
        return []
    queries = [
        'Ukraine war Russia Putin Zelensky',
        'Israel Gaza Hamas Iran conflict',
        'China Taiwan US tensions',
        'Trump Biden US politics',
        'economy inflation recession',
        'NATO EU Europe summit',
        'cyberattack hacking security',
        'coup dictatorship sanctions',
        'climate change disaster',
        'India Pakistan Asia conflict',
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
                    # V10: FILTRO ESTRICTO — descartar si no hay imagen o título
                    if not t or '[Removed]' in t or not img:
                        continue
                    d = a.get('description', '')
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
            continue
    log(f"NewsAPI: {len(noticias)} noticias (con imagen)", 'info')
    return noticias

def obtener_newsdata():
    if not NEWSDATA_API_KEY:
        return []
    categorias = ['world', 'politics', 'business', 'technology']
    noticias = []
    for cat in categorias:
        try:
            r = requests.get(
                'https://newsdata.io/api/1/news',
                params={'apikey': NEWSDATA_API_KEY, 'language': 'es',
                        'category': cat, 'size': 10, 'image': 1},  # V10: image=1 pre-filtra en API
                timeout=15
            ).json()
            if r.get('status') == 'success':
                for a in r.get('results', []):
                    t   = a.get('title', '')
                    img = a.get('image_url')
                    # V10: FILTRO ESTRICTO — descartar si no hay imagen o título
                    if not t or not img:
                        continue
                    d = a.get('description', '')
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
            continue
    log(f"NewsData: {len(noticias)} noticias (con imagen)", 'info')
    return noticias

def obtener_gnews():
    if not GNEWS_API_KEY:
        return []
    topicos = ['world', 'nation', 'business', 'technology', 'sports', 'health']
    noticias = []
    for topic in topicos:
        try:
            r = requests.get(
                'https://gnews.io/api/v4/top-headlines',
                params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 10, 'topic': topic},
                timeout=15
            ).json()
            for a in r.get('articles', []):
                t   = a.get('title', '')
                img = a.get('image')
                # V10: FILTRO ESTRICTO — descartar si no hay imagen o título
                if not t or not img:
                    continue
                d = a.get('description', '')
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
            log(f"GNews error ({topic}): {e}", 'advertencia')
            continue
    log(f"GNews: {len(noticias)} noticias (con imagen)", 'info')
    return noticias

def obtener_rss():
    fuentes = [
        ('http://feeds.bbci.co.uk/mundo/rss.xml',             'BBC Mundo'),
        ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada', 'El País'),
        ('https://www.infobae.com/arc/outboundfeeds/rss/mundo/', 'Infobae'),
        ('https://feeds.france24.com/es/',                    'France 24'),
        ('https://www.efe.com/efe/espana/1/rss',              'EFE'),
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
            continue
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
        es_dup = False
        for t_previo in titulos_vistos:
            if similitud_titulos(titulo, t_previo) > 0.78:
                es_dup = True
                break
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
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 200 or h < 150:
            return None
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.thumbnail((1280, 1280))
        # Agregar watermark verdadhoy.com
        img = agregar_watermark(img, posicion='esquina_inferior_derecha')
        p = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(p, 'JPEG', quality=88)
        if os.path.getsize(p) < 3000:
            os.remove(p)
            return None
        log(f"🖼️ Imagen descargada con watermark: {w}x{h}", 'debug')
        return p
    except Exception as e:
        log(f"⚠️ Error descargando imagen: {e}", 'debug')
        return None

def agregar_watermark(img, posicion='esquina_inferior_derecha'):
    """
    Agrega watermark 'verdadhoy.com' a una imagen PIL.
    Posiciones: esquina_inferior_derecha, esquina_inferior_izquierda,
                esquina_superior_derecha, esquina_superior_izquierda
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        ancho, alto = img.size

        # Fuente para el watermark
        try:
            font_wm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except:
            font_wm = ImageFont.load_default()

        texto_wm = "verdadhoy.com"

        # Calcular tamaño del texto
        try:
            bbox = draw.textbbox((0, 0), texto_wm, font=font_wm)
            txt_w = bbox[2] - bbox[0]
            txt_h = bbox[3] - bbox[1]
        except:
            txt_w, txt_h = 140, 20

        margen = 14
        padding = 6

        # Calcular posición
        if posicion == 'esquina_inferior_derecha':
            x = ancho - txt_w - margen - padding * 2
            y = alto - txt_h - margen - padding * 2
        elif posicion == 'esquina_inferior_izquierda':
            x = margen
            y = alto - txt_h - margen - padding * 2
        elif posicion == 'esquina_superior_derecha':
            x = ancho - txt_w - margen - padding * 2
            y = margen
        else:  # superior izquierda
            x = margen
            y = margen

        # Fondo semitransparente detrás del texto
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [x - padding, y - padding,
             x + txt_w + padding, y + txt_h + padding],
            radius=4,
            fill=(0, 0, 0, 160)  # negro semitransparente
        )
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')

        # Texto del watermark
        draw = ImageDraw.Draw(img)
        # Sombra
        draw.text((x + 1, y + 1), texto_wm, font=font_wm, fill=(0, 0, 0, 180))
        # Texto principal en dorado
        draw.text((x, y), texto_wm, font=font_wm, fill='#f5c518')

        return img
    except Exception as e:
        log(f"⚠️ Error agregando watermark: {e}", 'debug')
        return img

def aplicar_watermark_a_archivo(imagen_path):
    """Aplica watermark a un archivo de imagen y lo guarda en el mismo path."""
    try:
        from PIL import Image
        img = Image.open(imagen_path).convert('RGB')
        img = agregar_watermark(img, posicion='esquina_inferior_derecha')
        img.save(imagen_path, 'JPEG', quality=88)
        log("🏷️ Watermark agregado a imagen", 'exito')
        return imagen_path
    except Exception as e:
        log(f"⚠️ Error aplicando watermark: {e}", 'debug')
        return imagen_path

def crear_imagen_titulo(titulo):
    """Genera imagen de respaldo con el título — solo si no hay imagen real."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        img  = Image.new('RGB', (1200, 630), color='#0f172a')
        draw = ImageDraw.Draw(img)
        try:
            fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            fb = fs = ImageFont.load_default()
        draw.rectangle([(0, 0), (1200, 8)], fill='#3b82f6')
        tt = textwrap.fill(titulo[:140], width=36)
        ls = tt.split('\n')
        y  = (630 - len(ls) * 50) // 2 - 50
        draw.text((60, y), tt, font=fb, fill='white')
        draw.text((60, 550), "🌍 Noticias Internacionales", font=fs, fill='#94a3b8')
        draw.text((60, 580), "Verdad Hoy • Tu fuente confiable", font=fs, fill='#64748b')
        p = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        # Watermark antes de guardar
        img = agregar_watermark(img, posicion='esquina_inferior_derecha')
        img.save(p, 'JPEG', quality=90)
        log("🖼️ Imagen generada desde título (fallback)", 'advertencia')
        return p
    except:
        return None

# ──────────────────────────────────────────────────────────
# CONSTRUCCIÓN DEL POST FACEBOOK
# ──────────────────────────────────────────────────────────
def dividir_parrafos(texto):
    if not texto:
        return []
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    if len(oraciones) < 3:
        return [texto] if len(texto) > 100 else []
    parrafos, actual, palabras = [], [], 0
    for i, o in enumerate(oraciones):
        actual.append(o)
        palabras += len(o.split())
        if palabras >= 40 or i == len(oraciones) - 1:
            if len(' '.join(actual).split()) >= 15:
                parrafos.append(' '.join(actual))
            actual, palabras = [], 0
    return parrafos[:20]

def construir_publicacion_fb(titulo, contenido, fuente, url_wp):
    """
    Texto corto para Facebook:
    titular + 1 párrafo (máx 45 palabras) + link a verdadhoy.com
    """
    t = limpiar_texto(titulo)

    # Primer párrafo limpio — máx 4 líneas en móvil
    # Limpiar fuentes incrustadas del contenido
    contenido_limpio = _FUENTES_INCRUSTADAS.sub('', contenido).strip()
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido_limpio) if len(o.strip()) > 20]
    parrafo = ""
    palabras_count = 0
    for oracion in oraciones[:6]:
        palabras_count += len(oracion.split())
        parrafo += oracion + " "
        if palabras_count >= 45:
            break
    parrafo = parrafo.strip()
    # Terminar en punto limpio
    if parrafo and parrafo[-1] not in '.!?':
        parrafo += '...'
    elif len(parrafo) > 280:
        parrafo = parrafo[:277].rsplit(' ', 1)[0] + '...'

    # Agregar UTM params para tracking en Analytics
    url_utm = f"{url_wp}?utm_source=facebook&utm_medium=social&utm_campaign=bot_noticias"

    lineas = [
        f"📰 {t}",
        "",
        parrafo,
        "",
        "─────────────────────────────",
        "",
        "🔗 Lee la noticia completa:",
        f"👉 {url_utm}",
        "",
        "🌐 verdadhoy.com",
    ]
    return '\n'.join(lineas)

# ──────────────────────────────────────────────────────────
# PINTEREST
# ──────────────────────────────────────────────────────────

def obtener_tableros_pinterest():
    """Obtiene los tableros del usuario y los guarda en caché."""
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
            log(f"⚠️ Pinterest boards error: {resp.status_code}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Pinterest boards excepción: {e}", 'advertencia')
    return _cache_tableros_pinterest

def publicar_pinterest(titulo, descripcion, url_articulo, img_path, categoria):
    """Publica un Pin en Pinterest en el tablero correspondiente a la categoría."""
    if not PINTEREST_TOKEN:
        log("⚠️ Pinterest: sin token, omitiendo", 'advertencia')
        return False
    if not img_path or not os.path.exists(img_path):
        log("⚠️ Pinterest: sin imagen, omitiendo", 'advertencia')
        return False

    try:
        # Obtener tableros
        tableros = obtener_tableros_pinterest()
        nombre_tablero = TABLEROS_PINTEREST.get(categoria, 'Noticias del Mundo')
        board_id = tableros.get(nombre_tablero)

        if not board_id:
            # Fallback al tablero principal
            board_id = tableros.get('Noticias del Mundo') or (list(tableros.values())[0] if tableros else None)

        if not board_id:
            log("⚠️ Pinterest: no se encontró tablero", 'advertencia')
            return False

        # URL con UTM para Pinterest
        url_utm = f"{url_articulo}?utm_source=pinterest&utm_medium=social&utm_campaign=bot_noticias"

        # Subir imagen primero
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

        # Crear el Pin
        desc_limpia = descripcion[:490] if descripcion else titulo
        payload = {
            'board_id': board_id,
            'title': titulo[:100],
            'description': desc_limpia,
            'link': url_utm,
        }
        if media_id:
            payload['media_source'] = {'source_type': 'media_id', 'media_id': media_id}
        else:
            # Fallback: usar URL de imagen desde WordPress
            payload['media_source'] = {'source_type': 'image_url', 'url': url_articulo}

        resp_pin = requests.post(
            'https://api.pinterest.com/v5/pins',
            headers={
                'Authorization': f'Bearer {PINTEREST_TOKEN}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=20
        )

        if resp_pin.status_code in (200, 201):
            pin_id = resp_pin.json().get('id', '')
            log(f"✅ Pinterest OK: pin {pin_id} en tablero '{nombre_tablero}'", 'exito')
            return True
        else:
            log(f"❌ Pinterest error {resp_pin.status_code}: {resp_pin.text[:200]}", 'error')
            return False

    except Exception as e:
        log(f"❌ Pinterest excepción: {e}", 'error')
        return False


def generar_hashtags(titulo, contenido):
    txt = f"{titulo} {contenido}".lower()
    tags = ['#NoticiasInternacionales', '#ÚltimaHora']
    mapa = {
        r'guerra|conflicto|ataque|bombardeo': '#ConflictoArmado',
        r'ucrania|rusia|putin':               '#UcraniaRusia',
        r'gaza|israel|hamas':                 '#IsraelGaza',
        r'trump|biden|eeuu|estados unidos':   '#PolíticaGlobal',
        r'economía|inflación|recesión':       '#EconomíaMundial',
        r'china|taiwan':                      '#ChinaTaiwán',
        r'iran|medio oriente':                '#MedioOriente',
        r'terrorismo|atentado':               '#Terrorismo',
    }
    for patron, tag in mapa.items():
        if re.search(patron, txt):
            tags.append(tag)
            break
    tags.append('#VerdadHoy #Mundo')
    return ' '.join(tags)

def _truncar_mensaje(texto, hashtags, firma, limite=60000):
    sufijo = f"\n\n{hashtags}\n\n— {firma}"
    espacio = limite - len(sufijo)
    if len(texto) > espacio:
        texto = texto[:espacio - 4].rsplit(' ', 1)[0] + ' [...]'
    return f"{texto}{sufijo}"

# ──────────────────────────────────────────────────────────
# GENERACIÓN DE VIDEO
# ──────────────────────────────────────────────────────────
def crear_video_noticia(titulo, resumen, fondo_path=None):
    """Genera un video MP4 con el titular y resumen de la noticia."""
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
        import textwrap
        import numpy as np

        duracion = 30
        fps      = 24
        ancho, alto = 1280, 720
        mitad = ancho // 2

        def cargar_fuente(paths, size):
            for p in paths:
                try:
                    from PIL import ImageFont
                    return ImageFont.truetype(p, size)
                except:
                    continue
            from PIL import ImageFont
            return ImageFont.load_default()

        font_paths     = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        font_paths_reg = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        font_breaking  = cargar_fuente(font_paths, 24)
        font_titulo    = cargar_fuente(font_paths, 44)
        font_resumen   = cargar_fuente(font_paths_reg, 24)

        def crear_frame_pil(progreso=1.0):
            frame = Image.new('RGB', (ancho, alto), '#0d1117')
            if fondo_path and os.path.exists(fondo_path):
                try:
                    img = Image.open(fondo_path).convert('RGB')
                    img_ratio = img.width / img.height
                    target_ratio = mitad / alto
                    if img_ratio > target_ratio:
                        new_h, new_w = alto, int(alto * img_ratio)
                    else:
                        new_w, new_h = mitad, int(mitad / img_ratio)
                    img = img.resize((new_w, new_h), Image.LANCZOS)
                    x = (new_w - mitad) // 2
                    y = (new_h - alto) // 2
                    img = img.crop((x, y, x + mitad, y + alto))
                    img = ImageEnhance.Sharpness(img).enhance(1.4)
                    frame.paste(img, (mitad, 0))
                except:
                    pass
            panel = Image.new('RGB', (mitad + 40, alto), '#0d1117')
            frame.paste(panel, (0, 0))
            draw = ImageDraw.Draw(frame)
            draw.rectangle([(0, 0), (ancho, 52)], fill='#dc2626')
            draw.text((20, 14), "  ÚLTIMA HORA  |  VERDAD HOY", font=font_breaking, fill='white')
            draw.rectangle([(20, 68), (mitad - 20, 71)], fill='#3b82f6')
            titulo_wrap = textwrap.fill(titulo[:110], width=22)
            y_t = 90
            for linea in titulo_wrap.split('\n'):
                draw.text((20, y_t), linea, font=font_titulo, fill='white')
                y_t += 52
            y_r = y_t + 20
            resumen_wrap = textwrap.fill(resumen[:200], width=34)
            for linea in resumen_wrap.split('\n'):
                if y_r < alto - 120:
                    draw.text((20, y_r), linea, font=font_resumen, fill='#94a3b8')
                    y_r += 32
            # Panel CTA inferior
            draw.rectangle([(0, alto - 90), (ancho, alto)], fill='#dc2626')
            cta_tema, cta_cierre = obtener_cta_video(titulo)
            draw.text((20, alto - 80), cta_tema, font=font_resumen, fill='white')
            draw.text((20, alto - 48), "verdadhoy.com", font=font_resumen, fill='#fbbf24')
            return np.array(frame)

        frames = [crear_frame_pil(progreso=t/duracion) for t in range(duracion * fps)]
        clip = ImageClip(frames[0]).set_duration(duracion)

        video_path = f'/tmp/video_{generar_hash(titulo)}.mp4'

        # Intentar agregar audio TTS
        audio_path = None
        try:
            import edge_tts
            import asyncio
            voz = obtener_voz_aleatoria()
            texto_tts = f"{titulo}. {resumen[:300]}"
            audio_path = f'/tmp/audio_{generar_hash(titulo)}.mp3'

            async def generar_audio():
                comunicar = edge_tts.Communicate(texto_tts, voz)
                await comunicar.save(audio_path)

            asyncio.run(generar_audio())
            log("🎙️ Audio TTS generado", 'exito')
        except Exception as e:
            log(f"⚠️ TTS no disponible: {e} — video sin audio", 'advertencia')
            audio_path = None

        if audio_path and os.path.exists(audio_path):
            try:
                audio_clip = AudioFileClip(audio_path).subclip(0, duracion)
                clip = clip.set_audio(audio_clip)
                clip.write_videofile(video_path, codec='libx264', audio_codec='aac',
                                     preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)
                audio_clip.close()
            except:
                clip.write_videofile(video_path, codec='libx264', audio=False,
                                     preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)
            finally:
                try:
                    os.remove(audio_path)
                except:
                    pass
        else:
            clip.write_videofile(video_path, codec='libx264', audio=False,
                                 preset='ultrafast', ffmpeg_params=['-crf', '28'], logger=None)

        clip.close()
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log(f"✅ Video generado: {size_mb:.1f} MB, {duracion}s", 'exito')
        return video_path

    except ImportError:
        log("⚠️ moviepy no disponible — usando imagen", 'advertencia')
        return None
    except Exception as e:
        log(f"⚠️ Error generando video: {e}", 'advertencia')
        return None

# ──────────────────────────────────────────────────────────
# V11: FUNCIÓN 3 — VIDEO MANUAL VIA /pending_videos/
# ──────────────────────────────────────────────────────────

def listar_pending_videos_github():
    """
    Lista los archivos .txt en la carpeta pending_videos/ del repo de GitHub.
    Retorna lista de dicts con: name, download_url, sha
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        log("⚠️ Pending videos: GITHUB_TOKEN o GITHUB_REPOSITORY no configurados", 'advertencia')
        return []
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PENDING_VIDEOS_DIR}"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            log(f"ℹ️ Carpeta {PENDING_VIDEOS_DIR}/ no existe o está vacía", 'info')
            return []
        if resp.status_code != 200:
            log(f"⚠️ GitHub API error {resp.status_code}: {resp.text[:100]}", 'advertencia')
            return []
        archivos = [
            f for f in resp.json()
            if isinstance(f, dict) and f.get('name', '').endswith('.txt')
        ]
        log(f"📂 Pending videos encontrados: {len(archivos)}", 'info')
        return archivos
    except Exception as e:
        log(f"⚠️ Error listando pending_videos: {e}", 'advertencia')
        return []


def leer_archivo_github(download_url):
    """Descarga y retorna el contenido de un archivo desde GitHub."""
    try:
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        resp = requests.get(download_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        log(f"⚠️ Error leyendo archivo GitHub: {e}", 'advertencia')
    return None


def eliminar_archivo_github(nombre_archivo, sha):
    """Elimina un archivo del repo de GitHub."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PENDING_VIDEOS_DIR}/{nombre_archivo}"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        payload = {
            'message': f'[bot] Eliminar video procesado: {nombre_archivo}',
            'sha': sha
        }
        resp = requests.delete(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 204):
            log(f"🗑️ Archivo eliminado de GitHub: {nombre_archivo}", 'exito')
            return True
        else:
            log(f"⚠️ No se pudo eliminar {nombre_archivo}: {resp.status_code}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Error eliminando archivo GitHub: {e}", 'advertencia')
    return False


def parsear_archivo_pending(contenido):
    """
    Parsea el archivo .txt subido manualmente.
    Formato esperado:
      DESCRIPCION: texto de la noticia
      EMBED: <iframe ...></iframe>
    Retorna dict con: descripcion, embed
    """
    resultado = {'descripcion': '', 'embed': ''}
    lineas = contenido.strip().split('\n')
    modo = None
    buffer = []

    for linea in lineas:
        if linea.strip().upper().startswith('DESCRIPCION:'):
            if modo == 'embed' and buffer:
                resultado['embed'] = '\n'.join(buffer).strip()
            modo = 'descripcion'
            buffer = [linea.split(':', 1)[1].strip() if ':' in linea else '']
        elif linea.strip().upper().startswith('EMBED:'):
            if modo == 'descripcion' and buffer:
                resultado['descripcion'] = '\n'.join(buffer).strip()
            modo = 'embed'
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
    """
    Usa IA para generar título SEO, categoría, meta descripción y slug
    a partir de la descripción del video manual.
    """
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        # Fallback sin IA
        titulo = descripcion[:60].strip()
        return {
            'titulo_seo':      titulo,
            'meta_descripcion': descripcion[:155],
            'categoria':        detectar_tema(titulo, descripcion),
            'keyword_principal': titulo.split()[0] if titulo else 'noticia',
            'keywords_secundarias': [],
            'contenido_html':  f"<p>{descripcion}</p>"
        }

    prompt = f"""Eres el Editor Jefe Digital de VerdadHoy.com, medio de noticias en español.
Analiza esta descripción de video de noticias y genera los metadatos SEO.

DESCRIPCIÓN DEL VIDEO:
{descripcion[:1500]}

GENERA en formato JSON exacto (sin markdown, sin explicaciones):
{{
  "titulo_seo": "Título H1 máximo 60 caracteres, keyword principal primero, informativo",
  "meta_descripcion": "Meta descripción 140-155 caracteres exactos con keyword secundaria",
  "categoria": "una de: guerra|politica|economia|tecnologia|desastre|deportes|ciencia|salud|entretenimiento|latinoamerica|clima|mundo|general",
  "keyword_principal": "keyword principal 2-4 palabras",
  "keywords_secundarias": ["kw2", "kw3", "kw4"],
  "contenido_html": "HTML del artículo: primer párrafo con Qué/Quién/Cuándo/Dónde/Por qué en 50 palabras, luego 2-3 párrafos de contexto con subtítulos <h2>, máximo 400 palabras total, sin repetir el título"
}}"""

    try:
        headers = {'Content-Type': 'application/json'}
        if OPENROUTER_API_KEY:
            headers['Authorization'] = f'Bearer {OPENROUTER_API_KEY}'
            headers['HTTP-Referer']  = 'https://verdadhoy.com'
            url_ia = 'https://openrouter.ai/api/v1/chat/completions'
            model  = 'openai/gpt-4o-mini'
        else:
            headers['Authorization'] = f'Bearer {OPENAI_API_KEY}'
            url_ia = 'https://api.openai.com/v1/chat/completions'
            model  = 'gpt-4o-mini'

        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 900,
            'temperature': 0.4,
        }
        resp = requests.post(url_ia, headers=headers, json=payload, timeout=30)
        texto = resp.json()['choices'][0]['message']['content'].strip()
        texto = re.sub(r'```json|```', '', texto).strip()
        datos = json.loads(texto)
        log(f"✅ IA generó metadatos para video manual: {datos.get('titulo_seo','')[:50]}", 'exito')
        return datos
    except Exception as e:
        log(f"⚠️ Error IA metadatos video: {e} — usando fallback", 'advertencia')
        titulo = descripcion[:60].strip()
        return {
            'titulo_seo':       titulo,
            'meta_descripcion':  descripcion[:155],
            'categoria':         detectar_tema(titulo, descripcion),
            'keyword_principal': titulo.split()[0] if titulo else 'noticia',
            'keywords_secundarias': [],
            'contenido_html':   f"<p>{descripcion}</p>"
        }


def procesar_pending_videos():
    """
    V11 FUNCIÓN 3: Detecta archivos nuevos en /pending_videos/, los procesa
    y publica en WordPress + Pinterest. Elimina archivos tras 24h de publicados.
    """
    if not WP_APP_PASSWORD:
        log("⚠️ Pending videos: WP_APP_PASSWORD no configurado", 'advertencia')
        return

    estado = cargar_json(ESTADO_PENDING_PATH, {'procesados': {}})
    ahora  = datetime.now()

    # ── Paso 1: Eliminar archivos que llevan +24h publicados ──
    for nombre, info in list(estado['procesados'].items()):
        fecha_pub = info.get('publicado_en')
        sha       = info.get('sha')
        if fecha_pub and sha:
            try:
                dt_pub = datetime.fromisoformat(fecha_pub)
                if ahora - dt_pub > timedelta(hours=24):
                    log(f"🗑️ Eliminando {nombre} (24h cumplidas)...", 'info')
                    if eliminar_archivo_github(nombre, sha):
                        del estado['procesados'][nombre]
                        guardar_json(ESTADO_PENDING_PATH, estado)
            except Exception as e:
                log(f"⚠️ Error revisando expiración de {nombre}: {e}", 'advertencia')

    # ── Paso 2: Detectar archivos nuevos ──
    archivos = listar_pending_videos_github()
    if not archivos:
        return

    nuevos_publicados = 0
    for archivo in archivos:
        nombre = archivo.get('name', '')
        sha    = archivo.get('sha', '')

        # Saltar si ya fue procesado
        if nombre in estado['procesados']:
            log(f"ℹ️ {nombre} ya procesado — omitiendo", 'debug')
            continue

        log(f"\n🎥 Nuevo video manual detectado: {nombre}", 'info')

        # Leer contenido del archivo
        contenido_txt = leer_archivo_github(archivo.get('download_url', ''))
        if not contenido_txt:
            log(f"⚠️ No se pudo leer {nombre}", 'advertencia')
            continue

        datos = parsear_archivo_pending(contenido_txt)
        if not datos['descripcion'] or not datos['embed']:
            log(f"⚠️ {nombre} no tiene DESCRIPCION o EMBED válidos — omitiendo", 'advertencia')
            continue

        # Generar metadatos con IA
        meta = generar_metadatos_video_manual(datos['descripcion'], datos['embed'])

        titulo    = meta.get('titulo_seo', datos['descripcion'][:60])
        categoria = meta.get('categoria', 'mundo')
        meta_desc = meta.get('meta_descripcion', datos['descripcion'][:155])
        cuerpo_html = meta.get('contenido_html', f"<p>{datos['descripcion']}</p>")

        # Ajustar por cuota editorial
        categoria = ajustar_categoria_por_cuota(categoria)

        # Construir contenido WordPress
        embed_html = datos['embed']
        articulos_rel = obtener_articulos_wp_recientes(2)
        html_rel = generar_seccion_relacionados(articulos_rel)

        # Schema JSON-LD
        schema = generar_schema_jsonld(
            titulo=titulo,
            descripcion=meta_desc,
            imagen_url=f"{WP_URL}/wp-content/uploads/vh-video-placeholder.jpg",
            fecha_pub=ahora.strftime('%Y-%m-%dT%H:%M:%S')
        )

        contenido_final = f"""
{cuerpo_html}

<div style="margin:28px auto; text-align:center; max-width:267px;">
  {embed_html}
  <p style="font-size:0.8em; color:#888; margin-top:8px;">📹 Video: Verdad Hoy en Facebook</p>
</div>

{html_rel}

{schema}
"""

        # Obtener categoría WP
        cat_slug = CATEGORIA_WP.get(categoria, 'internacional')
        cat_id   = obtener_id_categoria_wp(cat_slug)

        # Obtener/crear tags
        tag_ids = []
        for kw in meta.get('keywords_secundarias', [])[:5]:
            tid = obtener_crear_tag_wp(kw)
            if tid:
                tag_ids.append(tid)

        # Construir post WP
        post_data = {
            'title':   titulo,
            'content': contenido_final,
            'excerpt': meta_desc,
            'status':  'publish',
            'meta': {
                '_yoast_wpseo_title':           titulo,
                '_yoast_wpseo_metadesc':        meta_desc,
                '_yoast_wpseo_focuskw':         meta.get('keyword_principal', ''),
            },
        }
        if cat_id:
            post_data['categories'] = [cat_id]
        if tag_ids:
            post_data['tags'] = tag_ids

        try:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/posts",
                json=post_data,
                auth=(WP_USER, WP_APP_PASSWORD),
                timeout=20
            ).json()

            if 'id' in r:
                url_wp = r.get('link', '')
                log(f"✅ Video manual publicado en WordPress: {url_wp}", 'exito')
                registrar_cuota(categoria)

                # Guardar en estado con timestamp para eliminar tras 24h
                estado['procesados'][nombre] = {
                    'publicado_en': ahora.isoformat(),
                    'sha':          sha,
                    'wp_url':       url_wp,
                    'wp_id':        r['id']
                }
                guardar_json(ESTADO_PENDING_PATH, estado)
                nuevos_publicados += 1

                # Pinterest en paralelo
                if PINTEREST_TOKEN:
                    log("📌 Publicando video manual en Pinterest...", 'info')
                    # Para video sin imagen usamos URL del artículo como media
                    publicar_pinterest_video_manual(
                        titulo=titulo,
                        descripcion=meta_desc,
                        url_articulo=url_wp,
                        categoria=categoria
                    )
            else:
                log(f"❌ Error publicando video manual en WP: {r.get('message','?')}", 'error')

        except Exception as e:
            log(f"❌ Excepción publicando video manual: {e}", 'error')

    if nuevos_publicados:
        log(f"\n✅ Pending videos procesados: {nuevos_publicados}", 'exito')
    else:
        log("ℹ️ Pending videos: ningún archivo nuevo pendiente", 'info')


def publicar_pinterest_video_manual(titulo, descripcion, url_articulo, categoria):
    """Publica en Pinterest un pin de video manual (sin imagen local, usa URL del artículo)."""
    if not PINTEREST_TOKEN:
        return False
    try:
        tableros    = obtener_tableros_pinterest()
        nombre_tab  = TABLEROS_PINTEREST.get(categoria, 'Noticias del Mundo')
        board_id    = tableros.get(nombre_tab) or (list(tableros.values())[0] if tableros else None)
        if not board_id:
            return False

        url_utm = f"{url_articulo}?utm_source=pinterest&utm_medium=social&utm_campaign=video_manual"
        payload = {
            'board_id':    board_id,
            'title':       titulo[:100],
            'description': descripcion[:490],
            'link':        url_utm,
            'media_source': {'source_type': 'image_url', 'url': f"{WP_URL}/wp-content/uploads/vh-og-default.jpg"}
        }
        resp = requests.post(
            'https://api.pinterest.com/v5/pins',
            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}', 'Content-Type': 'application/json'},
            json=payload, timeout=20
        )
        if resp.status_code in (200, 201):
            log(f"✅ Pinterest video manual OK: pin en '{nombre_tab}'", 'exito')
            return True
        else:
            log(f"⚠️ Pinterest video manual error {resp.status_code}", 'advertencia')
    except Exception as e:
        log(f"⚠️ Pinterest video manual excepción: {e}", 'advertencia')
    return False


# ──────────────────────────────────────────────────────────
# PUBLICACIÓN EN FACEBOOK
# ──────────────────────────────────────────────────────────
def publicar_facebook_video(titulo, texto, video_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    descripcion = _truncar_mensaje(texto, hashtags, "🌐 Verdad Hoy | verdadhoy.com")
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
        with open(video_path, 'rb') as f:
            r = requests.post(
                url,
                files={'source': ('video.mp4', f, 'video/mp4')},
                data={'title': titulo[:255], 'description': descripcion,
                      'access_token': FB_ACCESS_TOKEN},
                timeout=120,
            ).json()
        if 'id' in r:
            log(f"✅ Video publicado en Facebook — ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook video: {r.get('error', {}).get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando video: {e}", 'error')
    return False

def publicar_facebook_imagen(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return False
    mensaje = _truncar_mensaje(texto, hashtags, "🌐 Verdad Hoy | verdadhoy.com")
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            r = requests.post(
                url,
                files={'file': ('imagen.jpg', f, 'image/jpeg')},
                data={'message': mensaje, 'access_token': FB_ACCESS_TOKEN},
                timeout=60
            ).json()
        if 'id' in r:
            log(f"✅ Imagen publicada en Facebook — ID: {r['id']}", 'exito')
            return True
        else:
            log(f"❌ Error Facebook imagen: {r.get('error', {}).get('message', 'desconocido')}", 'error')
    except Exception as e:
        log(f"❌ Excepción publicando imagen: {e}", 'error')
    return False

# ──────────────────────────────────────────────────────────
# MAIN — FLUJO PRINCIPAL V6
# ──────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("🌍 BOT DE NOTICIAS - V11.0 (Video Manual | Pinterest Paralelo | Sin Sync FB→WP)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # V11: Procesar videos manuales desde /pending_videos/ en GitHub
    procesar_pending_videos()

    # Verificar qué debe publicarse en esta ejecución
    publicar_wp = puede_publicar_wp()
    h = cargar_historial()
    publicar_fb = puede_publicar_fb(h)

    if not publicar_wp and not publicar_fb:
        log("⏱️ Nada que publicar en esta ejecución — esperando próximo ciclo", 'info')
        return None

    log(f"📋 Tareas: WordPress={'SÍ' if publicar_wp else 'NO'} | Facebook={'SÍ' if publicar_fb else 'NO'}", 'info')

    # Recolectar noticias
    noticias = []
    if NEWS_API_KEY:
        noticias.extend(obtener_newsapi())
    if NEWSDATA_API_KEY:
        noticias.extend(obtener_newsdata())
    if GNEWS_API_KEY:
        noticias.extend(obtener_gnews())
    if len(noticias) < 15:
        log("⚠️ Pocas noticias, complementando con RSS...", 'advertencia')
        noticias.extend(obtener_rss())

    if not noticias:
        log("ERROR: Ninguna fuente devolvió noticias", 'error')
        return False

    noticias = deduplicar_batch(noticias)
    noticias.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    log(f"📰 Candidatas ordenadas: {len(noticias)}", 'info')

    # Buscar noticia válida CON IMAGEN (obligatoria)
    seleccionada = None
    contenido    = None
    img_path     = None
    intentos     = 0

    for i, nt in enumerate(noticias):
        if intentos >= 60:
            break

        url    = nt.get('url', '')
        titulo = nt.get('titulo', '')
        desc   = nt.get('descripcion', '')

        if not url or not titulo:
            continue

        intentos += 1

        if intentos % 15 == 0:
            h = cargar_historial()

        log(f"\n[{i+1}] Puntaje {nt.get('puntaje',0)} | {titulo[:55]}...", 'debug')

        dup, razon = noticia_ya_publicada(h, url, titulo, desc)
        if dup:
            log(f"   ❌ {razon}", 'debug')
            continue

        if nt.get('puntaje', 0) < 3:
            log(f"   ❌ Puntaje insuficiente ({nt.get('puntaje', 0)})", 'debug')
            continue

        # Obtener contenido
        cont_web, _ = extraer_contenido(url)
        if cont_web and len(cont_web) >= 200:
            contenido_ok = cont_web
        elif desc and len(desc) >= 150:
            contenido_ok = desc
        else:
            log(f"   ❌ Contenido insuficiente", 'advertencia')
            continue

        # IMAGEN OBLIGATORIA — buscar en múltiples fuentes
        imagen_encontrada = None
        if nt.get('imagen'):
            imagen_encontrada = descargar_imagen(nt['imagen'])
        if not imagen_encontrada:
            img_url = extraer_imagen_web(url)
            if img_url:
                imagen_encontrada = descargar_imagen(img_url)
        if not imagen_encontrada:
            # Solo en último caso: generar imagen desde título
            imagen_encontrada = crear_imagen_titulo(titulo)

        if not imagen_encontrada:
            log(f"   ❌ Sin imagen disponible — saltando noticia", 'advertencia')
            continue

        log(f"   ✅ Noticia válida con imagen — procesando...")
        seleccionada = nt
        contenido    = contenido_ok
        img_path     = imagen_encontrada
        break

    if not seleccionada:
        log("ERROR: No se encontró ninguna noticia válida con imagen", 'error')
        return False

    log(f"\n📝 SELECCIONADA: {seleccionada['titulo'][:70]}")
    log(f"   Fuente: {seleccionada['fuente']} | Puntaje: {seleccionada.get('puntaje', 0)}")

    tema = detectar_tema(seleccionada['titulo'], seleccionada.get('descripcion', ''))
    log(f"   Tema detectado: {tema}", 'info')

    # ── V9: Ajustar categoría según cuotas editoriales ────────
    tema = ajustar_categoria_por_cuota(tema)
    log(f"   Categoría final (con cuota): {tema} | brand_safe={es_brand_safe(tema)} | CPM={CUOTAS_CATEGORIA.get(tema,{}).get('cpm_relativo',1.0)}x", 'info')

    exito_wp = False
    exito_fb = False
    url_articulo_wp = None

    # ── PASO 1: Publicar en WordPress ─────────────────────
    if publicar_wp:
        log("\n🌐 Publicando en WordPress...", 'info')
        url_articulo_wp = publicar_en_wordpress(
            titulo       = seleccionada['titulo'],
            contenido    = contenido,
            tema         = tema,
            imagen_path  = img_path,
            fuente_url   = seleccionada['url'],
            fecha_fuente = seleccionada.get('fecha'),
            fuente_noticia = seleccionada.get('fuente', ''),  # V9: para detectar canal oficial
        )
        if url_articulo_wp:
            exito_wp = True
            guardar_estado_wp()
            registrar_cuota(tema)  # V9: registrar cuota de categoría
            h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1
            log(f"✅ WordPress OK: {url_articulo_wp}", 'exito')

            # ── PASO 1b: Publicar en Pinterest ────────────────
            if PINTEREST_TOKEN:
                log("\n📌 Publicando en Pinterest...", 'info')
                exito_pinterest = publicar_pinterest(
                    titulo      = seleccionada['titulo'],
                    descripcion = contenido[:490] if contenido else seleccionada.get('descripcion', ''),
                    url_articulo = url_articulo_wp,
                    img_path    = img_path,
                    categoria   = tema,
                )
                if exito_pinterest:
                    h['estadisticas']['total_pinterest'] = h['estadisticas'].get('total_pinterest', 0) + 1
        else:
            log("❌ WordPress falló", 'error')

    # ── PASO 2: Publicar en Facebook (con link a WP) ──────
    if publicar_fb:
        log("\n📘 Publicando en Facebook...", 'info')

        # Usar URL de WordPress si existe, si no usar URL original
        link_fb = url_articulo_wp or seleccionada['url']

        pub = construir_publicacion_fb(
            titulo   = seleccionada['titulo'],
            contenido = contenido,
            fuente   = seleccionada['fuente'],
            url_wp   = link_fb,
        )
        pub = agregar_cta(pub, seleccionada['titulo'], seleccionada.get('descripcion', ''))
        ht  = generar_hashtags(seleccionada['titulo'], contenido)

        # SIEMPRE VIDEO — Facebook publica como Reel
        usar_video = True
        log("🎬 Formato FB: SIEMPRE VIDEO (Reel)", 'info')

        resumen_video = contenido[:300] if contenido else seleccionada.get('descripcion', '')

        if usar_video:
            video_path = crear_video_noticia(
                titulo     = seleccionada['titulo'],
                resumen    = resumen_video,
                fondo_path = img_path,
            )
            if video_path:
                log("📹 Publicando como VIDEO/Reel en Facebook...", 'info')
                exito_fb = publicar_facebook_video(seleccionada['titulo'], pub, video_path, ht)
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                except:
                    pass
            if not exito_fb:
                log("🖼️ Video falló — fallback a imagen...", 'advertencia')
                exito_fb = publicar_facebook_imagen(seleccionada['titulo'], pub, img_path, ht)
                usar_video = False

        # Guardar formato usado para alternar la próxima vez
        if exito_fb:
            guardar_json(ESTADO_FORMATO_PATH, {'ultimo_formato': 'video' if usar_video else 'imagen'})

        if exito_fb:
            guardar_estado_fb()
            h['estadisticas']['total_fb'] = h['estadisticas'].get('total_fb', 0) + 1

    # Limpiar imagen temporal
    try:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
    except:
        pass

    # Guardar historial si algo se publicó
    if exito_wp or exito_fb:
        desc_completa = (seleccionada.get('descripcion', '') + ' ' + contenido[:400]).strip()
        h = guardar_en_historial(h, seleccionada['url'], seleccionada['titulo'], desc_completa)
        total = h.get('estadisticas', {}).get('total_publicadas', 0)
        wp_total = h.get('estadisticas', {}).get('total_wp', 0)
        fb_total = h.get('estadisticas', {}).get('total_fb', 0)
        pt_total = h.get('estadisticas', {}).get('total_pinterest', 0)
        log(f"\n✅ RESUMEN: Total={total} | WP={wp_total} | FB={fb_total} | Pinterest={pt_total}", 'exito')
        log(f"💡 IMPORTANTE: El workflow debe hacer git push de los archivos JSON (incluido estado_cuotas.json)", 'advertencia')
        return True
    else:
        log("❌ No se publicó en ninguna plataforma", 'error')
        return False


if __name__ == "__main__":
    try:
        resultado = main()
        exit(0 if resultado is not False else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
