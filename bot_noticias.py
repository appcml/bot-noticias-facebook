#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales - V14.1
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
# CUOTAS EDITORIALES POR CATEGORÍA (monetización AdSense)
# ──────────────────────────────────────────────────────────
CUOTAS_CATEGORIA = {
    # Brand-safe / alto CPM — priorizados
    'economia':        {'cuota': 0.13, 'cpm_relativo': 1.55, 'brand_safe': True},
    'tecnologia':      {'cuota': 0.13, 'cpm_relativo': 1.45, 'brand_safe': True},
    'ciencia':         {'cuota': 0.10, 'cpm_relativo': 1.40, 'brand_safe': True},
    'salud':           {'cuota': 0.10, 'cpm_relativo': 1.40, 'brand_safe': True},
    'deportes':        {'cuota': 0.12, 'cpm_relativo': 1.20, 'brand_safe': True},
    'mundo':           {'cuota': 0.08, 'cpm_relativo': 1.00, 'brand_safe': True},
    'latinoamerica':   {'cuota': 0.06, 'cpm_relativo': 1.10, 'brand_safe': True},
    'politica':        {'cuota': 0.07, 'cpm_relativo': 1.05, 'brand_safe': False},
    'entretenimiento': {'cuota': 0.05, 'cpm_relativo': 1.15, 'brand_safe': True},
    'educacion':       {'cuota': 0.04, 'cpm_relativo': 1.35, 'brand_safe': True},
    'medio_ambiente':  {'cuota': 0.04, 'cpm_relativo': 1.28, 'brand_safe': True},
    'clima':           {'cuota': 0.03, 'cpm_relativo': 1.30, 'brand_safe': True},
    'religion':        {'cuota': 0.02, 'cpm_relativo': 1.00, 'brand_safe': True},
    'general':         {'cuota': 0.04, 'cpm_relativo': 1.35, 'brand_safe': True},
    # Bajo CPM / brand-unsafe — cuotas reducidas
    'guerra':          {'cuota': 0.04, 'cpm_relativo': 0.90, 'brand_safe': False},
    'desastre':        {'cuota': 0.03, 'cpm_relativo': 0.95, 'brand_safe': False},
    'crimen':          {'cuota': 0.02, 'cpm_relativo': 0.85, 'brand_safe': False},
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

# Tiempos
TIEMPO_ENTRE_WP_MIN = 30
TIEMPO_ENTRE_FB_MIN = 60   # 1 hora mínima entre posts de Facebook

# Límites diarios
MAX_POSTS_FB_DIA  = 6    # Máximo 6 posts/día en Facebook (calidad > cantidad)
MAX_POSTS_WP_DIA  = 48

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
    "guerra", "conflicto armado", "invasion", "ofensiva militar", "bombardeo",
    "misiles", "ataque aereo", "drones militares", "movilizacion militar",
    "tropas", "escalada de tension", "amenaza nuclear", "armas nucleares",
    "terrorismo", "atentado", "ataque terrorista",
    "ucrania", "rusia", "israel", "gaza", "iran", "china", "taiwan",
    "corea del norte", "otan", "nato", "brics", "medio oriente",
    "siria", "yemen", "sudan",
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

# ──────────────────────────────────────────────────────────
# DETECCIÓN DE TEMA — MEJORADA V12
# ──────────────────────────────────────────────────────────
def detectar_tema(titulo, descripcion=""):
    """
    Detecta el tema principal de una noticia.
    V13: Orden de prioridad estricto para evitar clasificaciones erróneas.
    - Deportes sube a prioridad 4 (antes de política) para capturar Mundial 2026
    - Política incluye presidentes LATAM para evitar que vayan a latinoamerica
    - Latinoamérica solo captura si no hay tema más específico
    - Entretenimiento solo si hay coincidencias EXPLÍCITAS y ninguna categoría anterior
    """
    txt = f"{titulo} {descripcion}".lower()

    # ── Prioridad 1: Conflicto / Guerra (nunca debe ir a entretenimiento)
    if any(p in txt for p in [
        "guerra", "bombardeo", "misil", "ataque", "conflicto armado",
        "invasion", "tropas", "nuclear", "terroris", "hamas",
        "hezbollah", "ucrania", "gaza", "israel", "rusia", "otan", "nato",
        "siria", "yemen", "sudan", "taliban", "isis", "ataque aereo",
        "escalada", "combate", "ofensiva", "contraofensiva", "drones militares",
        "muertos en combate", "bombardeado", "atacado", "fuego cruzado",
        "ejercito", "militares", "fuerza aerea", "marina de guerra",
        "corea del norte", "iran nuclear", "misil balistico",
    ]):
        return 'guerra'

    # ── Prioridad 2: Desastre natural / emergencia
    if any(p in txt for p in [
        "terremoto", "huracan", "inundacion", "desastre natural",
        "evacuacion", "tsunami", "explosion industrial", "incendio masivo",
        "derrumbe", "erupcion volcanica", "tormenta tropical",
        "alerta roja", "emergencia nacional", "sismo", "alerta de tsunami",
        "victimas del desastre", "catastrofe natural",
    ]):
        return 'desastre'

    # ── Prioridad 3: Crimen / Seguridad
    if any(p in txt for p in [
        "asesinato", "homicidio", "secuestro", "narcotrafico", "cartel",
        "crimen organizado", "mafia", "robo masivo", "fraude millonario",
        "detenido", "arrestado", "capturado", "condenado a prison",
        "banda criminal", "sicario", "feminicidio", "masacre",
        "traficante", "narcotraficante", "policia abate",
    ]):
        return 'crimen'

    # ── Prioridad 4: Deportes — subido para capturar Mundial 2026
    if any(p in txt for p in [
        "futbol", "olimpiadas", "mundial", "copa del mundo",
        "atletismo", "tenis", "baloncesto", "nba", "fifa",
        "formula 1", "f1", "champions league", "liga", "gol",
        "campeonato", "torneo", "medalla", "seleccion nacional",
        "boxeo", "ufc", "rugby", "ciclismo", "natacion",
        "partido", "jugador", "entrenador", "estadio", "marcador",
        "derrota deportiva", "victoria deportiva", "mundial 2026",
        "premier league", "laliga", "serie a", "bundesliga", "mls",
        "beisbol", "golf", "voleibol", "handball", "triathlon",
        "juegos olimpicos", "paris 2024", "los angeles 2028",
        "transfer futbolistico", "fichaje", "traspaso deportivo",
        "clasificacion mundial", "eliminatoria", "semifinal", "final deportiva",
        "arbitro", "penalti", "penalto", "corner", "fuera de juego",
    ]):
        return 'deportes'

    # ── Prioridad 5: Política — incluye presidentes LATAM para evitar desvíos
    if any(p in txt for p in [
        "trump", "biden", "harris", "presidente", "gobierno", "eleccion",
        "golpe de estado", "coup", "diplomaci", "congreso", "senado",
        "sancion", "otan", "g7", "g20", "cumbre", "tratado",
        "referendum", "parlamento", "primer ministro", "canciller",
        "politica exterior", "relaciones diplomaticas",
        "candidato presidencial", "campana electoral", "partido politico",
        "ministro", "gabinete", "decreto", "legislacion",
        # Presidentes y líderes LATAM — evita que vayan a 'latinoamerica'
        "petro", "milei", "lula", "maduro", "bukele", "boric",
        "sheinbaum", "claudia sheinbaum", "noboa", "arce", "lacalle",
        "congresista", "diputado", "senador", "alcalde", "gobernador",
        "oposicion politica", "coalicion", "elecciones presidenciales",
        "segunda vuelta", "balotaje", "voto", "urna", "comicios",
        "macron", "scholz", "sunak", "meloni", "modi", "xi jinping",
        "putin", "zelensky", "erdogan", "netanyahu",
    ]):
        return 'politica'

    # ── Prioridad 6: Economía
    if any(p in txt for p in [
        "economia", "inflacion", "recesion", "bolsa", "mercado financiero",
        "petroleo", "dolar", "euro", "fmi", "banco central",
        "crisis economica", "aranceles", "comercio", "exportaciones",
        "pib", "desempleo", "banco mundial", "reserva federal", "deuda",
        "crecimiento economico", "contraccion economica", "tasa de interes",
        "wall street", "nasdaq", "dow jones", "ibex", "merval",
        "criptomoneda", "bitcoin", "ethereum", "fintech",
        "inversion extranjera", "deficit fiscal", "superavit",
        "renta variable", "bonos", "acciones", "dividendo",
    ]):
        return 'economia'

    # ── Prioridad 7: Tecnología
    if any(p in txt for p in [
        "inteligencia artificial", "ia ", " ia,", "robot", "automatizacion",
        "ciberataque", "hackeo", "elon musk", "openai", "chatgpt",
        "software", "startup", "samsung", "apple", "google", "microsoft",
        "amazon", "tesla", "chip", "semiconductor", "quantum",
        "metaverso", "blockchain", "deepseek", "gemini", "llm",
        "red neuronal", "machine learning", "big data", "cloud computing",
        "5g", "6g", "internet de las cosas", "iot", "ciberseguridad",
        "huawei", "nvidia", "spacex", "starlink",
    ]):
        return 'tecnologia'

    # ── Prioridad 8: Salud / Medicina
    if any(p in txt for p in [
        "cancer", "enfermedad", "hospital", "medico", "tratamiento",
        "pandemia", "vacuna", "virus", "salud publica", "oms",
        "epidemia", "brote", "medicamento", "cirugia", "diagnostico",
        "sintoma", "dosis", "clinica", "ensayo clinico", "paciente",
        "investigadores hallaron", "estudio revela", "nuevo tratamiento",
        "farmaco", "terapia", "cura", "prevencion", "mortalidad",
        "obesidad", "diabetes", "hipertension", "salud mental",
        "antibiotico", "cepa", "mutacion viral", "variante",
        "oncologia", "cardiologia", "neurologia", "pediatria",
    ]):
        return 'salud'

    # ── Prioridad 9: Ciencia / Espacio
    if any(p in txt for p in [
        "ciencia", "investigacion cientifica", "descubrimiento cientifico",
        "espacio", "nasa", "planeta", "universo", "agujero negro",
        "fisica", "quimica", "biologia molecular", "genetica",
        "experimento", "laboratorio", "cohete", "satelite",
        "estudio cientifico", "hallazgo", "investigadores",
        "astronomia", "telescopio", "marte", "luna", "iss",
        "particula", "adn", "celula", "evolucion",
        "esa ", "agencia espacial", "exoplaneta", "supernova",
        "nobel de", "premio nobel", "paleontologia", "arqueologia",
    ]):
        return 'ciencia'

    # ── Prioridad 10: Medio ambiente / Clima
    if any(p in txt for p in [
        "cambio climatico", "calentamiento global", "temperatura record",
        "sequia", "incendio forestal", "contaminacion", "co2",
        "medio ambiente", "cop", "emision de carbono", "biodiversidad",
        "extincion", "deforestacion", "plastico en el oceano",
        "energia renovable", "solar", "eolica", "hidrogeno verde",
        "huella de carbono", "acuerdo de paris", "ipcc",
    ]):
        return 'medio_ambiente'

    if any(p in txt for p in [
        "clima", "lluvia intensa", "nieve record", "ola de calor",
        "helada", "tormenta", "ciclon", "tornado", "granizo",
        "pronostico meteorologico", "frente frio",
    ]):
        return 'clima'

    # ── Prioridad 11: Latinoamérica (geografía — solo si no hay tema específico)
    if any(p in txt for p in [
        "mexico", "colombia", "argentina", "chile", "peru", "venezuela",
        "brasil", "cuba", "bolivia", "ecuador", "america latina",
        "latinoamerica", "centroamerica", "caribe", "uruguay",
        "paraguay", "costa rica", "panama", "guatemala", "haiti",
        "nicaragua", "honduras", "el salvador", "republica dominicana",
    ]):
        return 'latinoamerica'

    # ── Prioridad 12: Educación
    if any(p in txt for p in [
        "educacion", "escuela", "universidad", "estudiantes",
        "maestros", "profesores", "reforma educativa", "becas",
        "escolaridad", "matricula", "campus", "pedagogia",
    ]):
        return 'educacion'

    # ── Prioridad 13: Religión
    if any(p in txt for p in [
        "papa francisco", "vaticano", "iglesia", "islam", "judaismo",
        "budismo", "hinduismo", "mezquita", "sinagoga", "catedral",
        "fe religiosa", "clerigo", "obispo", "encíclica", "enciclica",
        "pontífice", "pontifice", "cardenal", "pastor evangelico",
    ]):
        return 'religion'

    # ── Prioridad 14: Entretenimiento — SOLO coincidencias EXPLÍCITAS
    if any(p in txt for p in [
        "pelicula estreno", "serie de television", "musica pop",
        "artista musical", "actor de cine", "actriz premiada",
        "hollywood", "netflix serie", "oscar", "grammy",
        "album musical", "concierto mundial", "banda de musica",
        "celebridad", "influencer", "reality show",
        "festival de cine", "cannes", "sundance", "emmy",
        "spotify", "youtube music", "gira musical",
    ]):
        return 'entretenimiento'

    # ── Prioridad 15: Mundo (geografía internacional sin categoría específica)
    if any(p in txt for p in [
        "africa", "asia", "europa", "pacifico", "oriente medio",
        "naciones unidas", "onu", "cumbre mundial",
        "embajada", "cancilleria", "union europea",
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

def ajustar_categoria_por_cuota(categoria):
    if categoria_disponible(categoria):
        return categoria
    log(f"📊 Cuota llena para '{categoria}' — buscando alternativa brand-safe", 'advertencia')
    alternativas = sorted(
        [(c, v) for c, v in CUOTAS_CATEGORIA.items()
         if v.get('brand_safe') and categoria_disponible(c)],
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
def reescribir_noticia_v9(titulo, contenido, categoria):
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        return None

    brand_safe = es_brand_safe(categoria)
    instruccion_brand_safe = ""
    if not brand_safe:
        instruccion_brand_safe = """
BRAND SAFETY (OBLIGATORIO): Reencuadra el contenido enfocándote EN:
- Implicaciones económicas y geopolíticas a largo plazo
- Impacto en energía, comercio o tecnología
- Respuesta humanitaria e institucional
EVITA: lenguaje violento o gráfico, conteo de bajas, detalles tácticos militares."""

    prompt = f"""Eres el Editor Jefe Digital de VerdadHoy.com. Tu objetivo es maximizar SEO, Google Discover y seguridad de marca para AdSense.

NOTICIA ORIGINAL:
Título: {titulo}
Categoría: {categoria}
Contenido: {contenido[:2500]}
{instruccion_brand_safe}

REGLAS (OBLIGATORIAS):
- TÍTULO H1: Máximo 60 caracteres. Keyword principal en primeras 3 palabras.
  IMPORTANTE para Google Discover: El título debe generar curiosidad o urgencia.
  Usa números, preguntas o palabras de acción cuando sea posible.
  Ejemplos de estructura: "X países ya hacen Y", "Por qué Z cambia todo",
  "El plan que podría X", "Así funciona el nuevo Y"
- META DESCRIPCIÓN: Entre 140 y 155 caracteres exactos. Completa la historia del título.
- CUERPO: Primer párrafo responde Qué/Quién/Cuándo/Dónde en máx 50 palabras.
  Subtítulos <h2> cada 150-200 palabras. Párrafos de máx 3 líneas.
  1 lista <ul><li> si hay causas/consecuencias/datos. 3-4 términos en <strong>.
  Mínimo 350 palabras, máximo 600. Al final exactamente: [ENLACES_INTERNOS]
- TONO: Profesional, español neutro internacional. Sin opinión política.

RESPONDE ÚNICAMENTE con este JSON sin markdown:
{{"titulo_seo": "...", "meta_descripcion": "...", "contenido_html": "<p>...</p>...[ENLACES_INTERNOS]", "keyword_principal": "...", "keywords_secundarias": ["...", "..."]}}"""

    try:
        if OPENROUTER_API_KEY:
            url_api = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            modelo  = "openai/gpt-4o-mini"
        else:
            url_api = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            modelo  = "gpt-4o-mini"

        payload = {"model": modelo, "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.7, "max_tokens": 1400}
        resp = requests.post(url_api, headers=headers, json=payload, timeout=30)
        texto = resp.json()["choices"][0]["message"]["content"].strip()
        texto = re.sub(r'^```json\s*|```$', '', texto, flags=re.MULTILINE).strip()
        resultado = json.loads(texto)
        log(f"✅ IA SEO — Título: {resultado.get('titulo_seo','')[:55]}", 'info')
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
    if os.getenv('FORZAR_PUBLICACION', '').lower() == 'true':
        return True

    # Horario pico
    hora_utc = datetime.utcnow().hour
    en_pico  = any(inicio <= hora_utc < fin for inicio, fin in HORARIOS_PICO_UTC)
    if not en_pico:
        log(f"⏰ FB: fuera de horario pico (UTC {hora_utc:02d}h)", 'info')
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

def subir_imagen_wp(imagen_path, titulo, alt_text=""):
    """Sube imagen a WordPress y asigna alt_text."""
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
            if alt_text:
                try:
                    requests.post(
                        f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                        json={'alt_text': alt_text[:125]},
                        auth=(WP_USER, WP_APP_PASSWORD), timeout=10
                    )
                except:
                    pass
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

    if resultado_ia:
        titulo_final         = resultado_ia.get('titulo_seo', titulo)[:60] or titulo
        meta_desc            = resultado_ia.get('meta_descripcion', '')
        frase_clave          = resultado_ia.get('keyword_principal', '')
        contenido_formateado = resultado_ia.get('contenido_html', '')
        contenido_formateado = insertar_enlaces_internos(contenido_formateado)
        if frase_clave:
            alt_text_imagen = f"{frase_clave} - {titulo_final}"[:125]
        for kw in resultado_ia.get('keywords_secundarias', [])[:5]:
            tag_id = obtener_crear_tag_wp(kw)
            if tag_id:
                tags_ids.append(tag_id)
    else:
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
    imagen_schema_url  = f"{WP_URL}/wp-content/uploads/favicon_512.png"  # placeholder
    imagen_schema_w    = 1200
    imagen_schema_h    = 630

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
      "url": "{WP_URL}/wp-content/uploads/favicon_512.png",
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

    # Subir imagen
    imagen_id = subir_imagen_wp(imagen_path, titulo, alt_text=alt_text_imagen)
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

    # Reconstruir contenido_html con schema actualizado
    contenido_html = f"""
{contenido_formateado}

<hr>
<p><strong>Fuente:</strong> {nombre_medio}</p>
<p><em>Información verificada por Verdad Hoy — Tu fuente confiable de noticias internacionales.</em></p>
{schema_markup}
"""

    slug_cat   = CATEGORIA_WP.get(tema, 'internacional')
    cat_id     = obtener_id_categoria_wp(slug_cat)
    categorias = [cat_id] if cat_id else []

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
        'climate change disaster',
        'Latin America news',
        'technology artificial intelligence',
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
    categorias = ['world', 'politics', 'business', 'technology', 'science', 'health']
    noticias = []
    for cat in categorias:
        try:
            r = requests.get(
                'https://newsdata.io/api/1/news',
                params={'apikey': NEWSDATA_API_KEY, 'language': 'es',
                        'category': cat, 'size': 10, 'image': 1},
                timeout=15
            ).json()
            if r.get('status') == 'success':
                for a in r.get('results', []):
                    t   = a.get('title', '')
                    img = a.get('image_url')
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
    log(f"NewsData: {len(noticias)} noticias con imagen", 'info')
    return noticias

def obtener_gnews():
    if not GNEWS_API_KEY:
        return []
    topicos = ['world', 'nation', 'business', 'technology', 'sports', 'health', 'science', 'entertainment']
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
    log(f"GNews: {len(noticias)} noticias con imagen", 'info')
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
                # RSS: aceptar sin imagen (se intenta obtener después)
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
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
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
        if OPENROUTER_API_KEY:
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
    print("🌍 BOT DE NOTICIAS - V14.1")
    print("   WP: imágenes ≥1200px (Google Discover optimizado)")
    print("   FB: imagen+texto desde verdadhoy.com")
    print("   Pinterest: activo en paralelo con WP")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

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

                log(f"\n[{i+1}] Puntaje {nt.get('puntaje',0)} | {titulo[:55]}", 'debug')
                dup, razon = noticia_ya_publicada(h, url, titulo, desc)
                if dup:
                    log(f"   ❌ {razon}", 'debug')
                    continue
                if nt.get('puntaje', 0) < 3:
                    log(f"   ❌ Puntaje bajo ({nt.get('puntaje', 0)})", 'debug')
                    continue

                # Contenido
                cont_web, _ = extraer_contenido(url)
                if cont_web and len(cont_web) >= 200:
                    contenido_ok = cont_web
                elif desc and len(desc) >= 150:
                    contenido_ok = desc
                else:
                    log("   ❌ Contenido insuficiente", 'advertencia')
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
                seleccionada = nt
                contenido    = contenido_ok
                img_path     = imagen_encontrada
                break

            if not seleccionada:
                log("ERROR: No se encontró noticia válida con imagen", 'error')
            else:
                log(f"\n📝 SELECCIONADA: {seleccionada['titulo'][:70]}")
                tema = detectar_tema(seleccionada['titulo'], seleccionada.get('descripcion', ''))
                tema = ajustar_categoria_por_cuota(tema)
                log(f"   Categoría: {tema} | brand_safe={es_brand_safe(tema)}", 'info')

                url_articulo_wp = publicar_en_wordpress(
                    titulo       = seleccionada['titulo'],
                    contenido    = contenido,
                    tema         = tema,
                    imagen_path  = img_path,
                    fuente_url   = seleccionada['url'],
                    fecha_fuente = seleccionada.get('fecha'),
                    fuente_noticia = seleccionada.get('fuente', ''),
                )

                if url_articulo_wp:
                    exito_wp = True
                    guardar_estado_wp()
                    registrar_cuota(tema)
                    h['estadisticas']['total_wp'] = h['estadisticas'].get('total_wp', 0) + 1

                    # ── Pinterest en paralelo con WP ───────────────
                    if PINTEREST_TOKEN:
                        log("\n📌 Publicando en Pinterest...", 'info')
                        ok_pt = publicar_pinterest(
                            titulo       = seleccionada['titulo'],
                            descripcion  = contenido[:490],
                            url_articulo = url_articulo_wp,
                            img_path     = img_path,
                            categoria    = tema,
                        )
                        if ok_pt:
                            h['estadisticas']['total_pinterest'] = h['estadisticas'].get('total_pinterest', 0) + 1

                    # Guardar en historial
                    desc_completa = (seleccionada.get('descripcion', '') + ' ' + contenido[:400]).strip()
                    h = guardar_en_historial(h, seleccionada['url'], seleccionada['titulo'], desc_completa)

                # Limpiar imagen temporal WP
                try:
                    if img_path and os.path.exists(img_path):
                        os.remove(img_path)
                except:
                    pass

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
    log(f"\n{'='*50}", 'info')
    log(f"✅ RESUMEN V14.1:", 'exito')
    log(f"   Total publicadas: {stats.get('total_publicadas', 0)}", 'info')
    log(f"   WordPress: {stats.get('total_wp', 0)}", 'info')
    log(f"   Facebook:  {stats.get('total_fb', 0)}", 'info')
    log(f"   Pinterest: {stats.get('total_pinterest', 0)}", 'info')
    log(f"   Esta ejecución → WP={'✅' if exito_wp else '❌'} | FB={'✅' if exito_fb else '❌'}", 'info')

    if exito_wp or exito_fb:
        log("💡 Hacer git push de los JSON de estado (incluyendo estado_cuotas.json)", 'advertencia')
        return True
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
