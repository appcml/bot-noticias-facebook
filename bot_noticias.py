#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicador de parche V17.9.30 para bot_noticias.py
Uso: python3 aplicar_v17930.py bot_noticias.py
Genera: bot_noticias_v17930.py

Cambios que aplica:
  1. VERSION_BOT → V17.9.30
  2. Cuota unificada: MAX_POSTS_WP_DIA = 6 (Chile + LATAM + General en un solo pool)
  3. Nuevas constantes: CATEGORIAS_MENU_REAL, CATEGORIAS_EVERGREEN_POOL,
     PUNTAJE_EVERGREEN_BONUS, KEYWORDS_EFIMERO, KEYWORDS_EVERGREEN
  4. Nuevas funciones: es_contenido_evergreen(), categoria_en_rotacion(),
     cargar_historial_categorias_hoy(), registrar_categoria_publicada()
  5. calcular_puntaje(): bonus +10 evergreen, -4 efímero
  6. publicar_en_wordpress(): registra categoría publicada para rotación
  7. main() bloque general: pool unificado (General + Chile + LATAM),
     factor rotación de categorías, log debug de top-10 candidatas
  8. Banner main() actualizado
"""

import sys
import re
import shutil
import os
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 aplicar_v17930.py bot_noticias.py")
        sys.exit(1)

    src_path = sys.argv[1]
    if not os.path.exists(src_path):
        print(f"Error: no se encuentra {src_path}")
        sys.exit(1)

    # Backup automático
    bk_path = src_path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(src_path, bk_path)
    print(f"✅ Backup creado: {bk_path}")

    with open(src_path, encoding='utf-8') as f:
        src = f.read()

    n_cambios = 0

    def reemplazar(viejo, nuevo, descripcion):
        nonlocal src, n_cambios
        if viejo in src:
            src = src.replace(viejo, nuevo, 1)
            n_cambios += 1
            print(f"  ✅ {descripcion}")
        else:
            print(f"  ⚠️  NO encontrado (puede ya estar aplicado): {descripcion}")

    print("\n🔧 Aplicando parche V17.9.30...")

    # ── 1. VERSION_BOT ─────────────────────────────────────────────────────────
    reemplazar(
        'VERSION_BOT = "V17.9.25"',
        'VERSION_BOT = "V17.9.30"',
        "VERSION_BOT → V17.9.30"
    )
    # Por si el archivo ya era V17.9.26..29
    for v in ["V17.9.26", "V17.9.27", "V17.9.28", "V17.9.29"]:
        if f'VERSION_BOT = "{v}"' in src:
            src = src.replace(f'VERSION_BOT = "{v}"', 'VERSION_BOT = "V17.9.30"', 1)
            n_cambios += 1
            print(f"  ✅ VERSION_BOT {v} → V17.9.30")

    # ── 2. Cuotas — bloque MAX_POSTS ───────────────────────────────────────────
    BLOQUE_CUOTAS_VIEJO = (
        'MAX_POSTS_FB_DIA        = 4    # Máximo 4 posts/día en Facebook (calidad > cantidad)\n'
        'MAX_POSTS_WP_DIA        = 6    # Flujo general (V17.9.1: bajado de 24 a 6 — arranque conservador)\n'
        'MAX_POSTS_WP_DIA_CHILE  = 3    # Chile: 3 artículos/día (V17.9.1: antes 8)\n'
        'MAX_POSTS_WP_DIA_LATAM  = 3    # LATAM sin Chile: 3 artículos/día (V17.9.1: antes 12)\n'
        'MAX_POSTS_WP_DIA_TOTAL  = 12   # Total máximo global (6 + 3 + 3)'
    )
    BLOQUE_CUOTAS_NUEVO = (
        'MAX_POSTS_FB_DIA        = 4    # Máximo 4 posts/día en Facebook (calidad > cantidad)\n'
        '# V17.9.30: cuota ÚNICA de 6/día para todo el sitio. Chile y LATAM\n'
        '# compiten en el mismo pool que el resto — siempre se publican los\n'
        '# 6 artículos de MAYOR VALOR sin importar su origen geográfico.\n'
        'MAX_POSTS_WP_DIA        = 6    # Total diario unificado (V17.9.30)\n'
        'MAX_POSTS_WP_DIA_CHILE  = 6    # Alias — Chile compite en pool unificado\n'
        'MAX_POSTS_WP_DIA_LATAM  = 6    # Alias — LATAM compite en pool unificado\n'
        'MAX_POSTS_WP_DIA_TOTAL  = 6    # Total máximo global unificado'
    )
    reemplazar(BLOQUE_CUOTAS_VIEJO, BLOQUE_CUOTAS_NUEVO, "Cuotas → pool unificado 6/día")

    # ── 3. Nuevas constantes + funciones ───────────────────────────────────────
    NUEVAS_CONST_Y_FUNCS = '''
# ══════════════════════════════════════════════════════════
# V17.9.30 — ROTACIÓN DE CATEGORÍAS Y PREFERENCIA EVERGREEN
# ══════════════════════════════════════════════════════════

# Categorías reales del menú de verdadhoy.com.
# La rotación garantiza que las 6 publicaciones diarias cubran
# categorías distintas del menú en vez de concentrarse en 1-2.
CATEGORIAS_MENU_REAL = [
    'politica', 'africa', 'asia', 'ciencia-y-salud', 'deportes',
    'economia', 'entretenimiento', 'europa', 'internacional',
    'latinoamerica', 'medio-ambiente', 'medio-oriente', 'mundo',
    'oceania', 'tecnologia',
]

# Categorías que generan contenido evergreen (posicionamiento duradero).
CATEGORIAS_EVERGREEN_POOL = {
    'economia', 'tecnologia', 'ciencia', 'salud', 'medio_ambiente',
    'deportes', 'latinoamerica', 'educacion',
}

# Bonus de puntaje para contenido evergreen detectado por keywords
PUNTAJE_EVERGREEN_BONUS = 10

# Señales de contenido efímero (penalizar)
KEYWORDS_EFIMERO = [
    'última hora', 'urgente', 'breaking', 'hoy se confirmó', 'esta mañana',
    'en las próximas horas', 'rumores', 'se rumorea', 'en directo',
    'minuto a minuto', 'actualización en vivo', 'sigue en desarrollo',
    'sin confirmar', 'fuentes no verificadas',
]

# Keywords de contenido duradero (favorecer)
KEYWORDS_EVERGREEN = [
    'análisis', 'explicación', 'cómo funciona', 'historia de', 'qué es',
    'guía', 'investigación', 'estudio', 'informe', 'tendencia', 'impacto',
    'consecuencias', 'causas', 'contexto', 'perspectiva', 'evolución',
    'reforma', 'ley', 'política pública', 'economía estructural',
    'cambio climático', 'biodiversidad', 'ciencia', 'tecnología', 'salud',
    'derechos', 'educación', 'infraestructura', 'energía', 'agua',
    'récord histórico', 'récord', 'primera vez en', 'hito histórico',
    'acuerdo histórico', 'tratado', 'convenio',
]


def es_contenido_evergreen(titulo, descripcion=""):
    """
    V17.9.30: Detecta si un artículo tiene potencial de posicionamiento
    duradero (evergreen) vs efímero (última hora, rumores, sucesos del día).

    Retorna (True, score) si es evergreen, (False, score) en caso contrario.
    score = número de señales evergreen encontradas.
    """
    txt = f"{titulo} {descripcion}".lower()

    # Señal negativa (efímero): si hay 1+ keyword efímera → no es evergreen
    efimeras = sum(1 for kw in KEYWORDS_EFIMERO if kw in txt)
    if efimeras >= 1:
        return False, 0

    # Señales positivas (evergreen)
    score = sum(1 for kw in KEYWORDS_EVERGREEN if kw in txt)

    # Bonus por categoría evergreen
    tema = detectar_tema(titulo, descripcion)
    if tema in CATEGORIAS_EVERGREEN_POOL:
        score += 1

    return (score >= 2, score)


def categoria_en_rotacion(categoria_slug, historial_categorias_hoy):
    """
    V17.9.30: Factor de penalización por sobrerepresentación de categoría.
    Si la misma categoría ya aparece 2+ veces hoy → -8 puntos.
    Si aparece 1 vez → -3 puntos (preferencia leve por otras categorías).
    """
    conteo = historial_categorias_hoy.count(categoria_slug)
    if conteo >= 2:
        return -8
    if conteo == 1:
        return -3
    return 0


def cargar_historial_categorias_hoy():
    """
    V17.9.30: Carga lista de slugs de categorías publicadas hoy.
    Se persiste en estado_wp.json bajo la clave 'categorias_hoy'.
    """
    e = cargar_json(ESTADO_WP_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if e.get('fecha_categorias') != hoy:
        return []
    return e.get('categorias_hoy', [])


def registrar_categoria_publicada(slug_categoria):
    """
    V17.9.30: Registra la categoría en el historial diario (estado_wp.json).
    Llamado por publicar_en_wordpress() tras publicar exitosamente.
    """
    e = cargar_json(ESTADO_WP_PATH, {})
    hoy = datetime.now().strftime('%Y-%m-%d')
    if e.get('fecha_categorias') != hoy:
        e['fecha_categorias'] = hoy
        e['categorias_hoy'] = []
    if slug_categoria not in ['', None]:
        e['categorias_hoy'].append(slug_categoria)
    guardar_json(ESTADO_WP_PATH, e)

'''

    ANCLA_CONSTANTES = '# V17.9.13: Reintento de calidad'
    if ANCLA_CONSTANTES in src:
        src = src.replace(ANCLA_CONSTANTES, NUEVAS_CONST_Y_FUNCS + ANCLA_CONSTANTES, 1)
        n_cambios += 1
        print("  ✅ Nuevas constantes + funciones de rotación/evergreen insertadas")
    else:
        print("  ⚠️  Ancla 'V17.9.13' no encontrada — insertar manualmente las constantes")

    # ── 4. Insertar nuevas funciones antes de es_contenido_spam() ──────────────
    # (ya insertadas en el bloque anterior junto con las constantes — nada más)

    # ── 5. calcular_puntaje(): bonus evergreen antes del return p ──────────────
    OLD_RETURN_P = '    return p\ndef puede_publicar_wp():'
    NEW_RETURN_P = (
        '    # V17.9.30: bonus evergreen — contenido duradero sube en ranking\n'
        '    _is_ev, _ev_score = es_contenido_evergreen(titulo, desc)\n'
        '    if _is_ev:\n'
        '        p += PUNTAJE_EVERGREEN_BONUS\n'
        '    elif _ev_score == 0 and any(kw in txt for kw in KEYWORDS_EFIMERO):\n'
        '        p -= 4  # penalizar noticias puramente efímeras\n'
        '    return p\n'
        'def puede_publicar_wp():'
    )
    reemplazar(OLD_RETURN_P, NEW_RETURN_P, "calcular_puntaje(): bonus evergreen")

    # ── 6. publicar_en_wordpress(): registrar categoría para rotación ───────────
    OLD_LOG_EXITO = "            log(f\"✅ Publicado en WordPress: {url_articulo}\", 'exito')"
    NEW_LOG_EXITO = (
        "            log(f\"✅ Publicado en WordPress: {url_articulo}\", 'exito')\n"
        "            # V17.9.30: registrar categoría para rotación diaria\n"
        "            registrar_categoria_publicada(slug_cat)\n"
    )
    reemplazar(OLD_LOG_EXITO, NEW_LOG_EXITO, "publicar_en_wordpress(): registro de categoría")

    # ── 7. main(): pool unificado en bloque MODO GENERAL ───────────────────────
    OLD_POOL = (
        '        # Recolectar noticias\n'
        '        noticias = []\n'
        '        if NEWS_API_KEY:\n'
        '            noticias.extend(obtener_newsapi())\n'
        '        if NEWSDATA_API_KEY:\n'
        '            noticias.extend(obtener_newsdata())\n'
        '        if GNEWS_API_KEY:\n'
        '            noticias.extend(obtener_gnews())\n'
        '        if len(noticias) < 15:\n'
        '            log("⚠️ Pocas noticias — complementando con RSS", \'advertencia\')\n'
        '            noticias.extend(obtener_rss())'
    )
    NEW_POOL = (
        '        # V17.9.30: Pool UNIFICADO — General + Chile + LATAM compiten juntos.\n'
        '        # Los 6 artículos/día son los de mayor valor total (puntaje +\n'
        '        # evergreen + rotación de categorías), sin importar origen geográfico.\n'
        '        noticias = []\n'
        '        if NEWS_API_KEY:\n'
        '            noticias.extend(obtener_newsapi())\n'
        '            noticias.extend(obtener_newsapi_chile())\n'
        '            noticias.extend(obtener_newsapi_latam())\n'
        '        if NEWSDATA_API_KEY:\n'
        '            noticias.extend(obtener_newsdata())\n'
        '        if GNEWS_API_KEY:\n'
        '            noticias.extend(obtener_gnews())\n'
        '        # RSS siempre — sin condición de volumen mínimo\n'
        '        noticias.extend(obtener_rss())\n'
        '        noticias.extend(obtener_rss_chile())\n'
        '        noticias.extend(obtener_rss_latam())\n'
        '        if len(noticias) < 10:\n'
        '            log("⚠️ Pool unificado con pocas candidatas (<10) — revisar APIs", \'advertencia\')'
    )
    reemplazar(OLD_POOL, NEW_POOL, "main(): pool unificado General+Chile+LATAM")

    # ── 8. main(): ordenamiento con factor rotación ─────────────────────────────
    OLD_SORT = (
        '            noticias = deduplicar_batch(noticias)\n'
        '            for n in noticias:\n'
        '                n[\'puntaje\'] = n.get(\'puntaje\', 0) + bonus_frescura(n.get(\'fecha\'))\n'
        '            noticias.sort(key=lambda x: (x.get(\'puntaje\', 0), x.get(\'fecha\', \'\')), reverse=True)\n'
        '            log(f"📰 Candidatas ordenadas: {len(noticias)}", \'info\')'
    )
    NEW_SORT = (
        '            noticias = deduplicar_batch(noticias)\n'
        '            # V17.9.30: puntaje final = base + frescura + evergreen + rotación\n'
        '            cats_hoy = cargar_historial_categorias_hoy()\n'
        '            log(f"🔄 Categorías publicadas hoy: {cats_hoy if cats_hoy else \'ninguna aún\'}", \'info\')\n'
        '            for n in noticias:\n'
        '                pbase = n.get(\'puntaje\', 0) + bonus_frescura(n.get(\'fecha\'))\n'
        '                tema_tmp = detectar_tema(n.get(\'titulo\',\'\'), n.get(\'descripcion\',\'\'))\n'
        '                slug_tmp = CATEGORIA_WP.get(tema_tmp, \'internacional\')\n'
        '                pbase += categoria_en_rotacion(slug_tmp, cats_hoy)\n'
        '                n[\'puntaje\'] = pbase\n'
        '            noticias.sort(key=lambda x: (x.get(\'puntaje\', 0), x.get(\'fecha\', \'\')), reverse=True)\n'
        '            # Log top-10 para debugging en GitHub Actions\n'
        '            for _i, _dbg in enumerate(noticias[:10]):\n'
        '                _ev, _evs = es_contenido_evergreen(_dbg.get(\'titulo\',\'\'), _dbg.get(\'descripcion\',\'\'))\n'
        '                _slug_dbg = CATEGORIA_WP.get(detectar_tema(_dbg.get(\'titulo\',\'\'), _dbg.get(\'descripcion\',\'\')), \'?\')\n'
        '                log(f"   [{_i+1}|{_dbg.get(\'puntaje\',0):+d}] {"🌲" if _ev else "📰"} [{_slug_dbg}] {_dbg.get(\'titulo\',\'\')[:55]}", \'debug\')\n'
        '            log(f"📰 Candidatas ordenadas (pool unificado): {len(noticias)}", \'info\')'
    )
    reemplazar(OLD_SORT, NEW_SORT, "main(): ordenamiento con factor rotación de categorías")

    # ── 9. Banner main() ────────────────────────────────────────────────────────
    OLD_BANNER = (
        '    print("   WP: 6 arts/día, flujo general — SEO focus")\n'
        '    print("   FB: imagen+texto desde verdadhoy.com (horario pico, independiente de WP)")\n'
        '    print("   LATAM-FIRST: Chile 3/día + LATAM 3/día adicionales (V17.9.1 — total 12/día)")\n'
        '    print("   RETENCIÓN: Box resumen + blockquote + pregunta cierre (target >2min)")'
    )
    NEW_BANNER = (
        '    print("   WP: 6 arts/día UNIFICADOS — los mejores del pool General+Chile+LATAM")\n'
        '    print("   FB: imagen+texto desde verdadhoy.com (horario pico, independiente de WP)")\n'
        '    print("   EVERGREEN-FIRST: +10pts duradero | rotación entre 14 categorías del menú")\n'
        '    print("   RETENCIÓN: Box resumen + blockquote + pregunta cierre (target >2min)")'
    )
    reemplazar(OLD_BANNER, NEW_BANNER, "Banner main() actualizado")

    # ── Guardar resultado ───────────────────────────────────────────────────────
    out_path = src_path.replace('.py', '_v17930.py')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(src)

    print(f"\n{'='*60}")
    print(f"✅ Parche V17.9.30 aplicado: {n_cambios} cambio(s)")
    print(f"📄 Archivo generado: {out_path}")
    print(f"💾 Backup en: {bk_path}")
    if n_cambios < 9:
        print(f"⚠️  Solo {n_cambios}/9 cambios aplicados — revisar advertencias arriba.")
        print("   Puede que el archivo ya tenga partes de V17.9.30 o que los")
        print("   textos a buscar difieran ligeramente de la versión original.")
    print("="*60)

if __name__ == "__main__":
    main()
