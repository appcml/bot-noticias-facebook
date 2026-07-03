#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot_pinterest_diferido.py — Verdad Hoy
────────────────────────────────────────────────────────────────────────────
Bot INDEPENDIENTE (no toca bot_noticias.py) que revisa las publicaciones
ya existentes en verdadhoy.com vía la REST API pública de WordPress y
publica un Pin en Pinterest solo cuando la noticia lleva un mínimo de
horas publicada (por defecto 24h), justo para que las ediciones manuales
ya estén "fijas" antes de difundir el enlace.

CARACTERÍSTICAS
────────────────
- No requiere credenciales de WordPress (usa la REST API pública de
  solo lectura: /wp-json/wp/v2/posts).
- No duplica publicaciones: guarda en estado_pinterest_diferido.json
  el ID de cada post ya pineado.
- Reintenta posts fallidos (ej: sin imagen destacada aún) hasta un
  máximo de intentos, luego los da por perdidos y deja de intentarlo.
- Respeta un límite de pines por ejecución y una pausa entre pines
  para no saturar la API de Pinterest.
- Asigna el tablero de Pinterest según la categoría de WordPress del
  post, reutilizando los mismos nombres de tablero que ya usa el bot
  principal (Noticias del Mundo, Politica, Economia, Tecnologia,
  Latinoamerica), para no crear tableros duplicados.

VARIABLES DE ENTORNO
─────────────────────
  WP_URL                    URL del sitio (default: https://verdadhoy.com)
  PINTEREST_TOKEN           Token de acceso de Pinterest (obligatorio)
  RETRASO_HORAS             Horas mínimas desde publicación (default: 24)
  VENTANA_MAX_DIAS          No mirar posts más antiguos que esto (default: 10)
  MAX_PINS_POR_EJECUCION    Tope de pines nuevos por corrida (default: 5)
  TIEMPO_ENTRE_PINS_SEG     Pausa entre pines, en segundos (default: 8)
  MAX_INTENTOS_FALLIDOS     Reintentos antes de abandonar un post (default: 5)
  TABLERO_DEFECTO           Tablero de respaldo (default: 'Noticias del Mundo')
  ESTADO_PATH               Ruta del archivo de estado (default: estado_pinterest_diferido.json)
  FORZAR                    'true' = ignora RETRASO_HORAS (pruebas manuales)
"""

import os
import re
import json
import time
import html
import sys
from datetime import datetime, timedelta, timezone

import requests

# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────
WP_URL                 = os.getenv('WP_URL', 'https://verdadhoy.com').rstrip('/')
PINTEREST_TOKEN        = os.getenv('PINTEREST_TOKEN', '')

RETRASO_HORAS          = float(os.getenv('RETRASO_HORAS', '24'))
VENTANA_MAX_DIAS        = float(os.getenv('VENTANA_MAX_DIAS', '10'))
MAX_PINS_POR_EJECUCION  = int(os.getenv('MAX_PINS_POR_EJECUCION', '5'))
TIEMPO_ENTRE_PINS_SEG   = float(os.getenv('TIEMPO_ENTRE_PINS_SEG', '8'))
MAX_INTENTOS_FALLIDOS   = int(os.getenv('MAX_INTENTOS_FALLIDOS', '5'))
TABLERO_DEFECTO         = os.getenv('TABLERO_DEFECTO', 'Noticias del Mundo')
ESTADO_PATH             = os.getenv('ESTADO_PATH', 'estado_pinterest_diferido.json')
FORZAR                  = os.getenv('FORZAR', 'false').strip().lower() == 'true'

UTM_CAMPAIGN            = 'pinterest_diferido'

# Mapa categoría WordPress (slug) → nombre de tablero en Pinterest.
# Usa los MISMOS nombres de tablero que ya existen en la cuenta
# (creados/usados por bot_noticias.py) para no fragmentar el contenido.
CATEGORIA_A_TABLERO = {
    'chile':          'Latinoamerica',
    'latinoamerica':  'Latinoamerica',
    'politica':       'Politica',
    'economia':       'Economia',
    'tecnologia':     'Tecnologia',
    'europa':         'Noticias del Mundo',
    'asia':           'Noticias del Mundo',
    'africa':         'Noticias del Mundo',
    'medio-oriente':  'Noticias del Mundo',
    'oceania':        'Noticias del Mundo',
    'mundo':          'Noticias del Mundo',
    'deportes':       'Noticias del Mundo',
    'entretenimiento':'Noticias del Mundo',
    'salud':          'Noticias del Mundo',
    'ciencia':        'Noticias del Mundo',
}

_cache_tableros = {}


# ──────────────────────────────────────────────────────────
# LOG
# ──────────────────────────────────────────────────────────
def log(msg, nivel='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'advertencia': '⚠️', 'error': '❌'}
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"[{ts}] {iconos.get(nivel, 'ℹ️')} {msg}", flush=True)


# ──────────────────────────────────────────────────────────
# ESTADO
# ──────────────────────────────────────────────────────────
def cargar_estado():
    if os.path.exists(ESTADO_PATH):
        try:
            with open(ESTADO_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"No se pudo leer estado previo, se crea uno nuevo: {e}", 'advertencia')
    return {'publicados': {}, 'fallidos': {}, 'ultima_ejecucion': None}


def guardar_estado(estado):
    estado['ultima_ejecucion'] = datetime.now(timezone.utc).isoformat()
    with open(ESTADO_PATH, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────
# UTILIDADES DE TEXTO
# ──────────────────────────────────────────────────────────
def limpiar_html(texto_html):
    if not texto_html:
        return ''
    texto = re.sub(r'<[^>]+>', ' ', texto_html)
    texto = html.unescape(texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


# ──────────────────────────────────────────────────────────
# WORDPRESS — obtener posts candidatos (REST API pública)
# ──────────────────────────────────────────────────────────
def obtener_posts_candidatos(ahora):
    """
    Devuelve posts publicados con fecha entre:
      - hace VENTANA_MAX_DIAS días (límite antiguo, para no barrer todo el historial)
      - hace RETRASO_HORAS horas (límite reciente, la noticia debe tener al menos
        ese tiempo publicada para considerarse "fija")
    """
    limite_reciente = ahora - timedelta(hours=0 if FORZAR else RETRASO_HORAS)
    limite_antiguo  = ahora - timedelta(days=VENTANA_MAX_DIAS)

    candidatos = []
    page = 1
    max_paginas = 10  # tope de seguridad

    while page <= max_paginas:
        params = {
            'after':    limite_antiguo.strftime('%Y-%m-%dT%H:%M:%S'),
            'before':   limite_reciente.strftime('%Y-%m-%dT%H:%M:%S'),
            'per_page': 100,
            'page':     page,
            'orderby':  'date',
            'order':    'asc',   # las más antiguas primero → se publican en orden
            '_embed':   1,
            'status':   'publish',
        }
        try:
            resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", params=params, timeout=20)
        except Exception as e:
            log(f"Error consultando WordPress (página {page}): {e}", 'error')
            break

        if resp.status_code == 400:
            # WP devuelve 400 cuando 'page' excede el total de páginas disponibles
            break
        if resp.status_code != 200:
            log(f"WordPress respondió {resp.status_code}: {resp.text[:150]}", 'advertencia')
            break

        posts = resp.json()
        if not posts:
            break
        candidatos.extend(posts)

        total_paginas = int(resp.headers.get('X-WP-TotalPages', '1'))
        if page >= total_paginas:
            break
        page += 1

    return candidatos


def extraer_imagen_destacada(post):
    try:
        media_list = post.get('_embedded', {}).get('wp:featuredmedia', [])
        if media_list and isinstance(media_list, list):
            media = media_list[0]
            if media and media.get('source_url'):
                return media['source_url']
    except Exception:
        pass
    return None


def extraer_categoria_slug(post):
    try:
        for grupo in post.get('_embedded', {}).get('wp:term', []):
            for termino in grupo:
                if termino.get('taxonomy') == 'category':
                    return (termino.get('slug') or '').lower()
    except Exception:
        pass
    return ''


# ──────────────────────────────────────────────────────────
# PINTEREST
# ──────────────────────────────────────────────────────────
def obtener_tableros_pinterest():
    global _cache_tableros
    if _cache_tableros:
        return _cache_tableros
    try:
        resp = requests.get(
            'https://api.pinterest.com/v5/boards',
            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}'},
            timeout=15
        )
        if resp.status_code == 200:
            for board in resp.json().get('items', []):
                _cache_tableros[board['name']] = board['id']
            log(f"Tableros Pinterest disponibles: {list(_cache_tableros.keys())}")
        else:
            log(f"Error obteniendo tableros de Pinterest: {resp.status_code} — {resp.text[:150]}", 'advertencia')
    except Exception as e:
        log(f"Excepción obteniendo tableros de Pinterest: {e}", 'advertencia')
    return _cache_tableros


def publicar_pin(titulo, descripcion, url_articulo, imagen_url, categoria_slug):
    tableros       = obtener_tableros_pinterest()
    nombre_tablero = CATEGORIA_A_TABLERO.get(categoria_slug, TABLERO_DEFECTO)
    board_id       = tableros.get(nombre_tablero) or tableros.get(TABLERO_DEFECTO)
    if not board_id and tableros:
        board_id = list(tableros.values())[0]
    if not board_id:
        return False, "no se encontró ningún tablero en la cuenta de Pinterest"

    url_utm = f"{url_articulo}?utm_source=pinterest&utm_medium=social&utm_campaign={UTM_CAMPAIGN}"

    payload = {
        'board_id':     board_id,
        'title':        titulo[:100],
        'description':  descripcion[:490] if descripcion else titulo[:490],
        'link':         url_utm,
        'media_source': {'source_type': 'image_url', 'url': imagen_url},
    }

    try:
        resp = requests.post(
            'https://api.pinterest.com/v5/pins',
            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}', 'Content-Type': 'application/json'},
            json=payload, timeout=20
        )
    except Exception as e:
        return False, f"excepción de red: {e}"

    if resp.status_code in (200, 201):
        pin_id = resp.json().get('id', '')
        return True, pin_id
    return False, f"{resp.status_code} — {resp.text[:200]}"


# ──────────────────────────────────────────────────────────
# PRINCIPAL
# ──────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("BOT PINTEREST DIFERIDO — Verdad Hoy")
    log(f"Retraso configurado: {'SIN RETRASO (FORZAR=true)' if FORZAR else f'{RETRASO_HORAS}h'}")
    log("=" * 60)

    if not PINTEREST_TOKEN:
        log("Falta PINTEREST_TOKEN — no se puede continuar.", 'error')
        sys.exit(0)  # no se marca la Action como fallida, solo no hace nada

    estado = cargar_estado()
    publicados = estado.setdefault('publicados', {})
    fallidos   = estado.setdefault('fallidos', {})

    ahora = datetime.now(timezone.utc)
    candidatos = obtener_posts_candidatos(ahora)
    log(f"Posts encontrados en la ventana de tiempo: {len(candidatos)}")

    pendientes = []
    for post in candidatos:
        post_id = str(post.get('id'))
        if post_id in publicados:
            continue
        intentos_previos = fallidos.get(post_id, {}).get('intentos', 0)
        if intentos_previos >= MAX_INTENTOS_FALLIDOS:
            continue
        pendientes.append(post)

    log(f"Posts pendientes de publicar en Pinterest: {len(pendientes)}")

    publicados_esta_corrida = 0
    for post in pendientes:
        if publicados_esta_corrida >= MAX_PINS_POR_EJECUCION:
            log(f"Límite de {MAX_PINS_POR_EJECUCION} pines por ejecución alcanzado, el resto queda para la próxima corrida.")
            break

        post_id  = str(post.get('id'))
        titulo   = limpiar_html(post.get('title', {}).get('rendered', ''))
        url_post = post.get('link', '')
        excerpt  = limpiar_html(post.get('excerpt', {}).get('rendered', ''))
        imagen   = extraer_imagen_destacada(post)
        categoria = extraer_categoria_slug(post)

        if not titulo or not url_post:
            log(f"Post {post_id}: datos incompletos, se omite.", 'advertencia')
            continue

        if not imagen:
            log(f"Post {post_id} ('{titulo[:50]}...'): sin imagen destacada todavía, se reintentará más adelante.", 'advertencia')
            reg = fallidos.setdefault(post_id, {'intentos': 0})
            reg['intentos'] += 1
            reg['ultimo_error'] = 'sin imagen destacada'
            reg['ultima_fecha'] = ahora.isoformat()
            continue

        descripcion = excerpt if excerpt else titulo

        ok, resultado = publicar_pin(titulo, descripcion, url_post, imagen, categoria)

        if ok:
            log(f"Pin publicado — post {post_id}: '{titulo[:60]}' → pin {resultado}", 'exito')
            publicados[post_id] = {
                'pin_id':    resultado,
                'titulo':    titulo,
                'url':       url_post,
                'fecha_pin': ahora.isoformat(),
            }
            fallidos.pop(post_id, None)
            publicados_esta_corrida += 1
            time.sleep(TIEMPO_ENTRE_PINS_SEG)
        else:
            log(f"Error publicando pin del post {post_id}: {resultado}", 'error')
            reg = fallidos.setdefault(post_id, {'intentos': 0})
            reg['intentos'] += 1
            reg['ultimo_error'] = str(resultado)[:200]
            reg['ultima_fecha'] = ahora.isoformat()

    guardar_estado(estado)

    log("=" * 60)
    log(f"Resumen: {publicados_esta_corrida} pin(es) nuevo(s) publicados en esta corrida.")
    log(f"Total histórico publicado: {len(publicados)} | En reintento: {len(fallidos)}")
    log("=" * 60)


if __name__ == '__main__':
    main()
