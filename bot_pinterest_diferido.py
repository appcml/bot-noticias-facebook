#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot_pinterest_diferido.py — Verdad Hoy V2.0
────────────────────────────────────────────────────────────────────────────
Bot INDEPENDIENTE que revisa publicaciones activas en verdadhoy.com
y publica Pines en Pinterest con retraso configurable (para que las
ediciones manuales estén listas antes de difundir).

MEJORAS V2.0 vs V1:
  - Descripciones enriquecidas con hashtags por categoría evergreen
  - Nuevas categorías: misterios, historia, geopolitica, innovacion, cultura
  - Tableros Pinterest actualizados con los nuevos del bot V20
  - Título optimizado: limpia el sufijo "| Verdad Hoy" antes de pinear
  - Descripción con excerpt + hashtags temáticos (máx 490 chars)
  - Pausa inteligente entre pines para no saturar la API
  - Log de categoría detectada en cada pin
  - FORZAR_POST_ID para testear un post específico
  - Limpieza automática de fallidos muy antiguos (>30 días)
"""

import os, re, json, time, html, sys, unicodedata
from datetime import datetime, timedelta, timezone
import requests

WP_URL                 = os.getenv('WP_URL', 'https://verdadhoy.com').rstrip('/')
PINTEREST_TOKEN        = os.getenv('PINTEREST_TOKEN', '')
RETRASO_HORAS          = float(os.getenv('RETRASO_HORAS', '2'))
VENTANA_MAX_DIAS       = float(os.getenv('VENTANA_MAX_DIAS', '10'))
MAX_PINS_POR_EJECUCION = int(os.getenv('MAX_PINS_POR_EJECUCION', '5'))
TIEMPO_ENTRE_PINS_SEG  = float(os.getenv('TIEMPO_ENTRE_PINS_SEG', '8'))
MAX_INTENTOS_FALLIDOS  = int(os.getenv('MAX_INTENTOS_FALLIDOS', '5'))
TABLERO_DEFECTO        = os.getenv('TABLERO_DEFECTO', 'noticias-del-mundo')
ESTADO_PATH            = os.getenv('ESTADO_PATH', 'estado_pinterest_diferido.json')
FORZAR                 = os.getenv('FORZAR', 'false').strip().lower() == 'true'
FORZAR_POST_ID         = os.getenv('FORZAR_POST_ID', '').strip()
UTM_CAMPAIGN           = 'pinterest_diferido'

# ── MAPA CATEGORÍA WP → TABLERO PINTEREST ──────────────────
# Usa los slugs exactos de tus tableros Pinterest
CATEGORIA_A_TABLERO = {
    # Latinoamérica
    'chile':           'latinoamerica',
    'latinoamerica':   'latinoamerica',
    # Política
    'politica':        'politica',
    # Economía
    'economia':        'economia',
    # Tecnología e innovación
    'tecnologia':      'tecnologia',
    'innovacion':      'tecnologia',
    # Deportes
    'deportes':        'deportes',
    # Todo lo demás → Noticias del Mundo
    'europa':          'noticias-del-mundo',
    'asia':            'noticias-del-mundo',
    'africa':          'noticias-del-mundo',
    'medio-oriente':   'noticias-del-mundo',
    'oceania':         'noticias-del-mundo',
    'mundo':           'noticias-del-mundo',
    'internacional':   'noticias-del-mundo',
    'entretenimiento': 'noticias-del-mundo',
    'cultura':         'noticias-del-mundo',
    'salud':           'noticias-del-mundo',
    'ciencia-y-salud': 'noticias-del-mundo',
    'ciencia':         'noticias-del-mundo',
    'historia':        'noticias-del-mundo',
    'misterios':       'noticias-del-mundo',
    'geopolitica':     'noticias-del-mundo',
    'medio-ambiente':  'noticias-del-mundo',
}

# ── HASHTAGS POR CATEGORÍA ──────────────────────────────────
HASHTAGS_POR_CATEGORIA = {
    'tecnologia':      '#Tecnologia #InteligenciaArtificial #Innovacion #IA #Tech',
    'innovacion':      '#Innovacion #Tecnologia #Futuro #Startup #IA',
    'ciencia':         '#Ciencia #Descubrimiento #Investigacion #Astronomia',
    'ciencia-y-salud': '#Ciencia #Salud #Medicina #Investigacion #Bienestar',
    'salud':           '#Salud #Bienestar #Medicina #Vida #Prevencion',
    'historia':        '#Historia #CulturaLatina #Pasado #Arqueologia #Civilizacion',
    'misterios':       '#Misterios #Historia #Ciencia #Enigmas #Descubrimiento',
    'geopolitica':     '#Geopolitica #Internacional #Mundo #Diplomacia #LATAM',
    'economia':        '#Economia #Finanzas #LATAM #Mercados #Dinero',
    'politica':        '#Politica #AméricaLatina #Gobierno #Noticias #LATAM',
    'medio-ambiente':  '#MedioAmbiente #CambioClimatico #Sustentabilidad #Planeta',
    'cultura':         '#Cultura #Arte #AméricaLatina #Creatividad #Identidad',
    'entretenimiento': '#Entretenimiento #Cine #Musica #Series #CulturaLatina',
    'deportes':        '#Deportes #Futbol #LATAM #Campeones #Deporte',
    'latinoamerica':   '#Latinoamerica #AméricaLatina #LATAM #Noticias #Cultura',
    'chile':           '#Chile #AméricaLatina #Noticias #LATAM',
    'mundo':           '#Mundo #Internacional #GlobalNews #Noticias',
    'internacional':   '#Internacional #Mundo #Noticias #GlobalNews',
}
HASHTAGS_DEFECTO = '#Noticias #AméricaLatina #VerdadHoy #LATAM'

_cache_tableros = {}


def log(msg, nivel='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'advertencia': '⚠️', 'error': '❌'}
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"[{ts}] {iconos.get(nivel, 'ℹ️')} {msg}", flush=True)


# ── ESTADO ──────────────────────────────────────────────────
def cargar_estado():
    if os.path.exists(ESTADO_PATH):
        try:
            with open(ESTADO_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"No se pudo leer estado previo: {e}", 'advertencia')
    return {'publicados': {}, 'fallidos': {}, 'ultima_ejecucion': None}

def guardar_estado(estado):
    estado['ultima_ejecucion'] = datetime.now(timezone.utc).isoformat()
    with open(ESTADO_PATH, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

def limpiar_fallidos_antiguos(fallidos, dias=30):
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    a_borrar = []
    for post_id, datos in fallidos.items():
        try:
            fecha = datetime.fromisoformat(datos.get('ultima_fecha','2000-01-01'))
            if fecha.tzinfo is None: fecha = fecha.replace(tzinfo=timezone.utc)
            if fecha < limite: a_borrar.append(post_id)
        except: a_borrar.append(post_id)
    for post_id in a_borrar:
        del fallidos[post_id]
    if a_borrar:
        log(f"Fallidos antiguos eliminados: {len(a_borrar)}", 'info')


# ── TEXTO ────────────────────────────────────────────────────
def limpiar_html(texto_html):
    if not texto_html: return ''
    texto = re.sub(r'<[^>]+>', ' ', texto_html)
    texto = html.unescape(texto)
    # Eliminar sufijo "| Verdad Hoy" del título
    texto = re.sub(r'\s*\|\s*Verdad Hoy\s*$', '', texto, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', texto).strip()

def construir_descripcion(excerpt, titulo, categoria_slug):
    hashtags = HASHTAGS_POR_CATEGORIA.get(categoria_slug, HASHTAGS_DEFECTO)
    base = excerpt if excerpt and len(excerpt) > 30 else titulo
    # Espacio disponible: 490 - len(hashtags) - 2 (separador)
    espacio_base = 490 - len(hashtags) - 2
    if len(base) > espacio_base:
        base = base[:espacio_base-3].rsplit(' ', 1)[0] + '...'
    return f"{base} {hashtags}"


# ── WORDPRESS ────────────────────────────────────────────────
def obtener_posts_candidatos(ahora):
    if FORZAR_POST_ID:
        log(f"FORZAR_POST_ID={FORZAR_POST_ID} — obteniendo post específico", 'info')
        try:
            resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{FORZAR_POST_ID}",
                                params={'_embed': 1}, timeout=20)
            if resp.status_code == 200:
                return [resp.json()]
            log(f"Post {FORZAR_POST_ID} no encontrado: {resp.status_code}", 'error')
        except Exception as e:
            log(f"Error obteniendo post {FORZAR_POST_ID}: {e}", 'error')
        return []

    limite_reciente = ahora - timedelta(hours=0 if FORZAR else RETRASO_HORAS)
    limite_antiguo  = ahora - timedelta(days=VENTANA_MAX_DIAS)
    candidatos = []
    page = 1
    while page <= 10:
        params = {
            'after':    limite_antiguo.strftime('%Y-%m-%dT%H:%M:%S'),
            'before':   limite_reciente.strftime('%Y-%m-%dT%H:%M:%S'),
            'per_page': 100, 'page': page,
            'orderby':  'date', 'order': 'asc',
            '_embed': 1, 'status': 'publish',
        }
        try:
            resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", params=params, timeout=20)
        except Exception as e:
            log(f"Error consultando WP página {page}: {e}", 'error'); break
        if resp.status_code == 400: break
        if resp.status_code != 200:
            log(f"WP respondió {resp.status_code}", 'advertencia'); break
        posts = resp.json()
        if not posts: break
        candidatos.extend(posts)
        total_paginas = int(resp.headers.get('X-WP-TotalPages', '1'))
        if page >= total_paginas: break
        page += 1
    return candidatos

def extraer_imagen_destacada(post):
    try:
        media_list = post.get('_embedded', {}).get('wp:featuredmedia', [])
        if media_list and isinstance(media_list, list):
            media = media_list[0]
            if media and media.get('source_url'): return media['source_url']
    except: pass
    return None

def extraer_categoria_slug(post):
    try:
        for grupo in post.get('_embedded', {}).get('wp:term', []):
            for termino in grupo:
                if termino.get('taxonomy') == 'category':
                    slug = (termino.get('slug') or '').lower()
                    if slug and slug != 'uncategorized': return slug
    except: pass
    return ''


# ── PINTEREST ────────────────────────────────────────────────
def obtener_tableros_pinterest():
    global _cache_tableros
    if _cache_tableros: return _cache_tableros
    if not PINTEREST_TOKEN: return {}
    try:
        resp = requests.get('https://api.pinterest.com/v5/boards',
                            headers={'Authorization': f'Bearer {PINTEREST_TOKEN}'},
                            params={'page_size': 50}, timeout=15)
        if resp.status_code == 200:
            for board in resp.json().get('items', []):
                nombre = board['name']
                board_id = board['id']
                _cache_tableros[nombre] = board_id
                # Guardar también por slug normalizado
                nfkd = unicodedata.normalize('NFKD', nombre.lower())
                slug = ''.join(c for c in nfkd if not unicodedata.combining(c))
                slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
                _cache_tableros[slug] = board_id
            log(f"Tableros Pinterest cargados: {[k for k in _cache_tableros if not k.lstrip('0123456789').startswith('')]}")
        else:
            log(f"Error tableros Pinterest: {resp.status_code}", 'advertencia')
    except Exception as e:
        log(f"Excepción obteniendo tableros: {e}", 'advertencia')
    return _cache_tableros

def obtener_board_id(categoria_slug):
    tableros = obtener_tableros_pinterest()
    slug_tablero = CATEGORIA_A_TABLERO.get(categoria_slug, TABLERO_DEFECTO)
    # Intentar por slug primero, luego por nombre directo
    board_id = tableros.get(slug_tablero)
    if not board_id:
        # Buscar coincidencia parcial
        for key, bid in tableros.items():
            if slug_tablero in key.lower() or key.lower() in slug_tablero:
                board_id = bid; break
    if not board_id and tableros:
        board_id = list(tableros.values())[0]
        log(f"Tablero '{slug_tablero}' no encontrado — usando primero disponible", 'advertencia')
    return board_id, slug_tablero

def publicar_pin(titulo, descripcion, url_articulo, imagen_url, categoria_slug):
    board_id, nombre_tablero = obtener_board_id(categoria_slug)
    if not board_id:
        return False, "no se encontró ningún tablero en Pinterest"

    url_utm = f"{url_articulo}?utm_source=pinterest&utm_medium=social&utm_campaign={UTM_CAMPAIGN}"

    payload = {
        'board_id':     board_id,
        'title':        titulo[:100],
        'description':  descripcion[:490],
        'link':         url_utm,
        'media_source': {'source_type': 'image_url', 'url': imagen_url},
    }

    try:
        resp = requests.post('https://api.pinterest.com/v5/pins',
                             headers={'Authorization': f'Bearer {PINTEREST_TOKEN}',
                                      'Content-Type': 'application/json'},
                             json=payload, timeout=20)
    except Exception as e:
        return False, f"excepción de red: {e}"

    if resp.status_code in (200, 201):
        pin_id = resp.json().get('id', '')
        return True, f"pin_id={pin_id} tablero='{nombre_tablero}'"
    return False, f"{resp.status_code} — {resp.text[:200]}"


# ── MAIN ─────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log(f"BOT PINTEREST DIFERIDO V2.0 — Verdad Hoy")
    log(f"Retraso: {'SIN RETRASO (FORZAR)' if FORZAR else f'{RETRASO_HORAS}h'}")
    log(f"Ventana: últimos {VENTANA_MAX_DIAS} días")
    log(f"Max pines por corrida: {MAX_PINS_POR_EJECUCION}")
    log("=" * 60)

    if not PINTEREST_TOKEN:
        log("Falta PINTEREST_TOKEN", 'error')
        sys.exit(0)

    estado = cargar_estado()
    publicados = estado.setdefault('publicados', {})
    fallidos   = estado.setdefault('fallidos', {})
    limpiar_fallidos_antiguos(fallidos)

    ahora = datetime.now(timezone.utc)
    candidatos = obtener_posts_candidatos(ahora)
    log(f"Posts en ventana de tiempo: {len(candidatos)}")

    pendientes = []
    for post in candidatos:
        post_id = str(post.get('id'))
        if post_id in publicados: continue
        intentos_previos = fallidos.get(post_id, {}).get('intentos', 0)
        if intentos_previos >= MAX_INTENTOS_FALLIDOS:
            log(f"Post {post_id} descartado ({intentos_previos} intentos fallidos)", 'advertencia')
            continue
        pendientes.append(post)

    log(f"Posts pendientes de pinear: {len(pendientes)}")

    publicados_corrida = 0
    for post in pendientes:
        if publicados_corrida >= MAX_PINS_POR_EJECUCION:
            log(f"Límite {MAX_PINS_POR_EJECUCION} pines alcanzado — resto queda para próxima corrida")
            break

        post_id   = str(post.get('id'))
        titulo    = limpiar_html(post.get('title', {}).get('rendered', ''))
        url_post  = post.get('link', '')
        excerpt   = limpiar_html(post.get('excerpt', {}).get('rendered', ''))
        imagen    = extraer_imagen_destacada(post)
        categoria = extraer_categoria_slug(post)

        if not titulo or not url_post:
            log(f"Post {post_id}: datos incompletos, se omite", 'advertencia')
            continue

        if not imagen:
            log(f"Post {post_id} '{titulo[:50]}': sin imagen — reintentará después", 'advertencia')
            reg = fallidos.setdefault(post_id, {'intentos': 0})
            reg['intentos'] += 1
            reg['ultimo_error'] = 'sin imagen destacada'
            reg['ultima_fecha'] = ahora.isoformat()
            continue

        descripcion = construir_descripcion(excerpt, titulo, categoria)
        log(f"Pineando post {post_id} [{categoria}]: '{titulo[:55]}'")

        ok, resultado = publicar_pin(titulo, descripcion, url_post, imagen, categoria)

        if ok:
            log(f"Pin publicado — {resultado}", 'exito')
            publicados[post_id] = {
                'pin_resultado': resultado,
                'titulo':        titulo,
                'url':           url_post,
                'categoria':     categoria,
                'fecha_pin':     ahora.isoformat(),
            }
            fallidos.pop(post_id, None)
            publicados_corrida += 1
            time.sleep(TIEMPO_ENTRE_PINS_SEG)
        else:
            log(f"Error pineando post {post_id}: {resultado}", 'error')
            reg = fallidos.setdefault(post_id, {'intentos': 0})
            reg['intentos'] += 1
            reg['ultimo_error'] = str(resultado)[:200]
            reg['ultima_fecha'] = ahora.isoformat()

    guardar_estado(estado)

    log("=" * 60)
    log(f"Resumen: {publicados_corrida} pin(es) publicados en esta corrida", 'exito' if publicados_corrida else 'info')
    log(f"Total histórico: {len(publicados)} | En reintento: {len(fallidos)}")
    log("=" * 60)


if __name__ == '__main__':
    main()
