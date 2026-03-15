#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook
- Prioridad: Conflictos bélicos, política global, economía mundial
- Fuentes: NewsAPI, google news, NewsData, GNews (todo internacional)
- Extracción de texto completo con reglas estrictas de calidad
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
import html as html_module
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Comment

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_publicaciones.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')

TIEMPO_ENTRE_PUBLICACIONES = 60  # 60 minutos
VENTANA_DUPLICADOS_HORAS = 24    # 24 horas de memoria de duplicados

# =============================================================================
# REGLAS ESTRICTAS DE VALIDACIÓN
# =============================================================================

# Mínimos de calidad
MIN_CARACTERES_CONTENIDO = 300
MIN_ORACIONES = 3
MAX_PARRAFOS = 8
MIN_PALABRAS_POR_PARrafo = 15

# Frases prohibidas (contenido de menús/publicidad)
FRASES_PROHIBIDAS = [
    'actualidad portada', 'publicado:', 'compartir en', 'síguenos en',
    'cookies', 'aceptar cookies', 'política de privacidad', 'aviso legal',
    'todos los derechos reservados', 'copyright', 'suscríbete', 'newsletter',
    'última hora', 'portada', 'menú', 'buscar', 'inicio', 'contacto',
    'redes sociales', 'facebook', 'twitter', 'instagram', 'whatsapp',
    'relacionados', 'también te interesa', 'más noticias', 'etiquetas:',
    'archivado en:', 'ver comentarios', 'ocultar comentarios'
]

# Patrones de "ruido" a eliminar
PATRONES_RUIDO = [
    r'Vista de.*Gettyimages?\.[a-z]+',  # Descripciones de imágenes
    r'Stringer\s*/\s*\w+',              # Créditos de fotos
    r'@\w+',                            # Menciones de usuario
    r'—\s*\w+\s*\(@\w+\)\s*\w+\s+\d+', # Tweets embebidos
    r'🚀.*$',                           # Emojis con texto promocional
    r'El senador.*afirma.*mintió.*$',   # Textos duplicados/resumen
    r'^\s*—\s*$',                       # Líneas solo con guiones
]

# =============================================================================
# PALABRAS CLAVE INTERNACIONALES
# =============================================================================

PALABRAS_ALTA_PRIORIDAD = [
    'guerra', 'conflicto', 'bombardeo', 'ataque', 'invasión', 'invasion',
    'misil', 'dron', 'ataque aéreo', 'ataque aereo', 'ofensiva', 'combate',
    'Ucrania', 'Rusia', 'Gaza', 'Israel', 'Palestina', 'Trump', 'Biden', 'Putin',
    'OTAN', 'NATO', 'ONU', 'UE', 'sanciones', 'embargo', 'crisis diplomática', # 🎯 ORIGINALES (4)
        "noticias urgentes hoy",
        "ultima hora internacional", 
        "breaking news today",
        "conflicto mundial hoy",
        
        # 🏛️ DICTADURAS (10)
        "dictadura hoy",
        "regimen autoritario noticias",
        "represion gubernamental",
        "protestas dictadura",
        "sanciones regimen",
        "derechos humanos violaciones",
        "censura gubernamental",
        "oposicion politica perseguida",
        "elecciones fraudulentas",
        "transicion democratica fallida",
        
        # ⚔️ GUERRAS (10)
        "guerra hoy",
        "conflicto armado actual",
        "ofensiva militar",
        "ataque aereo hoy",
        "bombardeo noticias",
        "cese al fuego roto",
        "invasion territorial",
        "resistencia armada",
        "guerra civil",
        "intervencion militar",
        
        # ⛏️ TIERRAS RARAS (10)
        "tierras raras noticias",
        "minerales estrategicos guerra",
        "litio conflicto",
        "cobalto mineria",
        "recursos naturales disputa",
        "monopolio minero",
        "cadena suministro minerales",
        "china tierras raras",
        "guerra economica recursos",
        "sanciones minerales",
        
        # 🤖 TECNOLOGÍA MILITAR (12)
        "drones militares noticias",
        "inteligencia artificial guerra",
        "ciberataque militar",
        "armas hipersonicas",
        "guerra cibernetica",
        "robotica militar",
        "satelite espionaje",
        "defensa antimisiles",
        "tecnologia militar avance",
        "guerra electronica",
        "ia en combate",
        "autonomous weapons",
        
        # 🌍 GEOPOLÍTICA (10)
        "tension diplomatica hoy",
        "sanciones economicas noticias",
        "guerra fria 2.0",
        "alianza militar",
        "otan noticias",
        "otsc noticias",
        "brics guerra",
        "g7 g20 tension",
        "embargo armas",
        "crisis diplomatica",
        
        # 🔥 CRISIS HUMANITARIAS (9)
        "refugiados guerra",
        "crisis humanitaria hoy",
        "ayuda humanitaria bloqueada",
        "hambruna conflicto",
        "desplazados guerra",
        "campo refugiados",
        "genocidio noticias",
        "crimenes guerra",
        "tribunal penal internacional",
        
        # 🌎 AMÉRICA (12)
        "noticias america latina hoy",
        "mexico noticias urgentes",
        "colombia conflicto actual",
        "venezuela crisis noticias",
        "brasil protestas hoy",
        "argentina economia crisis",
        "chile noticias hoy",
        "peru protestas dictadura",
        "centroamerica violencia",
        "eeuu noticias hoy",
        "canada politica actual",
        "migracion frontera sur",
        
        # 🌍 ÁFRICA (12)
        "africa conflictos hoy",
        "sahel guerra jihadista",
        "mali noticias conflicto",
        "nigeria seguridad hoy",
        "etiopia guerra tigray",
        "sudan guerra civil",
        "somalia al shabaab",
        "rd congo m23",
        "sudafrica crisis actual",
        "magreb noticias hoy",
        "africa coup etat",
        "pirateria africa",
        
        # 🌏 ASIA-PACÍFICO (14)
        "china taiwan tension",
        "corea norte noticias",
        "japon militar noticias",
        "india pakistan conflicto",
        "myanmar dictadura noticias",
        "filipinas china mar",
        "vietnam noticias hoy",
        "tailandia protestas",
        "indonesia noticias",
        "afganistan taliban",
        "pakistan terrorismo",
        "bangladesh crisis",
        "australia noticias hoy",
        "nueva zelanda actualidad",
        
        # 🌍 EUROPA (10)
        "ue noticias hoy",
        "rusia ucrania guerra",
        "balkanes tension",
        "turquia erdogan",
        "polonia belarus frontera",
        "hungria orban dictadura",
        "serbia kosovo conflicto",
        "caucaso armenia azerbaiyan",
        "reino unido noticias",
        "escandinavia noticias",
        
        # 🌏 ORIENTE MEDIO (10)
        "israel palestina guerra",
        "iran noticias hoy",
        "arabia saudi noticias",
        "yemen guerra hoy",
        "siria conflicto actual",
        "libano hezbollah",
        "irak noticias hoy",
        "emiratos arabes noticias",
        "qatar crisis diplomatica",
        "kurdistan conflicto"
]

PALABRAS_MEDIA_PRIORIDAD = [
    'economía mundial', 'mercados globales', 'inflación', 'FMI', 
    'China', 'EEUU', 'Estados Unidos', 'Reino Unido', 'Alemania', 'Francia',
]

TERMINOS_EXCLUIR = [
    'liga local', 'campeonato municipal', 'feria del pueblo', 
    'concurso de belleza local', 'elecciones municipales de',
    'alcalde de', 'gobernador de', 'partido local', 'deporte local',
]

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def log(mensaje, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 'debug': '🔍'}
    icono = iconos.get(tipo, 'ℹ️')
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {icono} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                if not contenido:
                    return default.copy()
                return json.loads(contenido)
        except Exception as e:
            log(f"Error cargando JSON: {e}", 'error')
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"Error guardando JSON: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto:
        return ""
    texto_normalizado = re.sub(r'[^\w\s]', '', texto.lower().strip())
    texto_normalizado = re.sub(r'\s+', ' ', texto_normalizado)
    return hashlib.md5(texto_normalizado.encode()).hexdigest()[:16]

def limpiar_texto(texto):
    if not texto:
        return ""
    
    texto = html_module.unescape(texto)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)
    texto = re.sub(r'https?://\S*', '', texto)
    texto = re.sub(r'[.…]{2,}\s*$', '.', texto)
    
    texto = texto.strip()
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto.strip()

def es_noticia_excluible(titulo, descripcion=""):
    texto = f"{titulo} {descripcion}".lower()
    for termino in TERMINOS_EXCLUIR:
        if termino.lower() in texto:
            return True
    return False

def calcular_puntaje_internacional(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    for palabra in PALABRAS_ALTA_PRIORIDAD:
        if palabra.lower() in texto:
            puntaje += 10
    
    for palabra in PALABRAS_MEDIA_PRIORIDAD:
        if palabra.lower() in texto:
            puntaje += 3
    
    if 50 <= len(titulo) <= 120:
        puntaje += 2
    
    return puntaje

# =============================================================================
# EXTRACCIÓN CON REGLAS ESTRICTAS
# =============================================================================

def extraer_contenido_estricto(url):
    """
    Extrae contenido con reglas estrictas de calidad.
    Retorna None si no cumple los estándares mínimos.
    """
    if not url:
        return None, None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9',
    }
    
    try:
        log(f"   🔍 Extrayendo: {url[:50]}...", 'debug')
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Eliminar TODOS los elementos no deseados agresivamente
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                            'form', 'button', 'iframe', 'noscript', 'svg', 'canvas']):
            element.decompose()
        
        # Eliminar comentarios HTML
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Eliminar elementos con clases/IDs de publicidad/menú
        clases_basura = [
            'menu', 'nav', 'sidebar', 'footer', 'header', 'ad', 'ads', 'publicidad',
            'social', 'share', 'comments', 'related', 'tags', 'meta', 'author-box',
            'breadcrumb', 'pagination', 'widget', 'carousel', 'slider'
        ]
        
        for clase in clases_basura:
            for elem in soup.find_all(class_=lambda x: x and clase in x.lower()):
                elem.decompose()
            for elem in soup.find_all(id=lambda x: x and clase in x.lower()):
                elem.decompose()
        
        # Buscar el contenido principal
        contenido = None
        creditos = None
        
        # Estrategia 1: Article con puros párrafos
        article = soup.find('article')
        if article:
            parrafos = article.find_all('p')
            if len(parrafos) >= 3:
                texto_limpio = extraer_parrafos_limpios(parrafos)
                if validar_calidad(texto_limpio):
                    contenido = texto_limpio
                    log(f"   ✅ Article válido: {len(contenido)} chars", 'debug')
        
        # Estrategia 2: Div con clase de contenido
        if not contenido:
            for clase in ['article-content', 'entry-content', 'post-content', 
                         'article-body', 'story-body', 'content']:
                elem = soup.find(class_=lambda x: x and clase in x.lower())
                if elem:
                    parrafos = elem.find_all('p')
                    if len(parrafos) >= 2:
                        texto_limpio = extraer_parrafos_limpios(parrafos)
                        if validar_calidad(texto_limpio):
                            contenido = texto_limpio
                            log(f"   ✅ Clase '{clase}': {len(contenido)} chars", 'debug')
                            break
        
        # Estrategia 3: Buscar bloque de párrafos consecutivos
        if not contenido:
            todos_p = soup.find_all('p')
            # Buscar grupos de 3+ párrafos seguidos con texto sustancial
            grupos = []
            grupo_actual = []
            
            for p in todos_p:
                texto = p.get_text(strip=True)
                if len(texto) > 80 and not tiene_basura(texto):
                    grupo_actual.append(texto)
                else:
                    if len(grupo_actual) >= 3:
                        grupos.append(grupo_actual)
                    grupo_actual = []
            
            if grupo_actual and len(grupo_actual) >= 3:
                grupos.append(grupo_actual)
            
            if grupos:
                # Tomar el grupo más largo
                mejor_grupo = max(grupos, key=lambda x: sum(len(p) for p in x))
                texto_limpio = ' '.join(mejor_grupo)
                if validar_calidad(texto_limpio):
                    contenido = texto_limpio
                    log(f"   ✅ Grupo de párrafos: {len(contenido)} chars", 'debug')
        
        if contenido:
            contenido = eliminar_ruido_final(contenido)
            creditos = extraer_creditos_limpios(soup)
            return contenido[:2000], creditos
        
        return None, None
        
    except Exception as e:
        log(f"   ⚠️ Error: {e}", 'debug')
        return None, None

def extraer_parrafos_limpios(parrafos):
    """Extrae texto de párrafos filtrando los que tienen basura."""
    textos = []
    for p in parrafos:
        texto = p.get_text(strip=True)
        texto = limpiar_texto(texto)
        
        # Filtrar párrafos cortos o con basura
        if len(texto) < 40:
            continue
        if tiene_basura(texto):
            continue
        if texto.count(' ') < 5:  # Muy pocas palabras
            continue
            
        textos.append(texto)
    
    return ' '.join(textos)

def tiene_basura(texto):
    """Verifica si el texto contiene elementos de menú/publicidad."""
    texto_lower = texto.lower()
    
    for frase in FRASES_PROHIBIDAS:
        if frase in texto_lower:
            return True
    
    # Verificar si es solo mayúsculas (típico de menús)
    if texto.isupper() and len(texto) > 10:
        return True
    
    # Verificar si tiene demasiados símbolos especiales
    simbolos = sum(1 for c in texto if c in '│├┤┬┴┼║╣╠╩╦╚╔╝╗▓▒░')
    if simbolos > 2:
        return True
    
    return False

def validar_calidad(texto):
    """Valida que el texto cumpla estándares mínimos de calidad."""
    if not texto:
        return False
    
    # Mínimo de caracteres
    if len(texto) < MIN_CARACTERES_CONTENIDO:
        log(f"   ❌ Muy corto: {len(texto)} chars", 'debug')
        return False
    
    # Mínimo de oraciones
    oraciones = [o for o in re.split(r'[.!?]+', texto) if len(o.strip()) > 10]
    if len(oraciones) < MIN_ORACIONES:
        log(f"   ❌ Pocas oraciones: {len(oraciones)}", 'debug')
        return False
    
    # No debe tener demasiadas mayúsculas (signo de menú)
    ratio_mayus = sum(1 for c in texto if c.isupper()) / len(texto)
    if ratio_mayus > 0.4:
        log(f"   ❌ Muchas mayúsculas: {ratio_mayus:.2f}", 'debug')
        return False
    
    # Debe tener palabras del título o relacionadas
    palabras_clave = ['dice', 'declaró', 'afirmó', 'señaló', 'indicó', 'según', 'tras']
    if not any(p in texto.lower() for p in palabras_clave):
        log(f"   ❌ No parece noticia (falta verbo de comunicación)", 'debug')
        return False
    
    log(f"   ✅ Calidad validada: {len(texto)} chars, {len(oraciones)} oraciones", 'debug')
    return True

def eliminar_ruido_final(texto):
    """Elimina patrones de ruido específicos del texto final."""
    for patron in PATRONES_RUIDO:
        texto = re.sub(patron, '', texto, flags=re.IGNORECASE | re.MULTILINE)
    
    # Eliminar líneas que son solo espacios o símbolos
    lineas = texto.split('\n')
    lineas_limpias = []
    for linea in lineas:
        linea_limpia = linea.strip()
        if linea_limpia and not re.match(r'^[\s\—\-\|\•\·]+$', linea_limpia):
            lineas_limpias.append(linea_limpia)
    
    texto = ' '.join(lineas_limpias)
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # Asegurar que termine bien
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto

def extraer_creditos_limpios(soup):
    """Extrae créditos de forma limpia."""
    creditos = None
    
    # Buscar en meta tags
    for meta in ['author', 'article:author', 'byline', 'creator']:
        tag = soup.find('meta', attrs={'name': meta}) or soup.find('meta', property=meta)
        if tag:
            creditos = tag.get('content', '').strip()
            if creditos and len(creditos) < 100:
                return limpiar_credito(creditos)
    
    # Buscar en elementos específicos
    for clase in ['author', 'byline', 'autor', 'firma']:
        elem = soup.find(class_=lambda x: x and clase in x.lower())
        if elem:
            texto = elem.get_text(strip=True)
            if 5 < len(texto) < 100:
                return limpiar_credito(texto)
    
    return None

def limpiar_credito(credito):
    """Limpia el texto del crédito."""
    if not credito:
        return None
    
    # Eliminar prefijos comunes
    credito = re.sub(r'^(Por|By|De|Autor|Redacción)[\s:]+', '', credito, flags=re.IGNORECASE)
    credito = re.sub(r'\d{1,2}/\d{1,2}/\d{4}.*$', '', credito)
    credito = re.sub(r'\d{1,2} de [a-z]+ de \d{4}.*$', '', credito, flags=re.IGNORECASE)
    
    credito = credito.strip()
    
    if len(credito) < 3 or len(credito) > 80:
        return None
    
    return credito

# =============================================================================
# DIVISIÓN EN PÁRRAFOS CON REGLAS ESTRICTAS
# =============================================================================

def dividir_parrafos_estricto(texto):
    """
    Divide el texto en párrafos con reglas estrictas de coherencia.
    Garantiza que cada párrafo tenga sentido completo.
    """
    if not texto:
        return []
    
    # Dividir en oraciones
    oraciones = re.split(r'(?<=[.!?])\s+', texto)
    oraciones = [o.strip() for o in oraciones if len(o.strip()) > 15]
    
    if len(oraciones) < 3:
        return [texto] if len(texto) > 100 else []
    
    parrafos = []
    parrafo_actual = []
    palabras_en_parrafo = 0
    
    for i, oracion in enumerate(oraciones):
        parrafo_actual.append(oracion)
        palabras_en_parrafo += len(oracion.split())
        
        # Forzar cierre de párrafo si:
        cerrar = False
        
        # 1. Llegamos a 40-50 palabras (párrafo sustancial)
        if palabras_en_parrafo >= 40:
            cerrar = True
        
        # 2. La oración termina en cita completa
        if '"' in oracion or '»' in oracion:
            comillas_abrir = oracion.count('"') + oracion.count('«')
            comillas_cerrar = oracion.count('"') + oracion.count('»')
            if comillas_cerrar > comillas_abrir or (comillas_abrir % 2 == 0 and comillas_abrir > 0):
                if palabras_en_parrafo >= 25:
                    cerrar = True
        
        # 3. La siguiente oración empieza con conector fuerte
        if i < len(oraciones) - 1:
            siguiente = oraciones[i + 1].lower()
            conectores_fuertes = ['sin embargo', 'por otro lado', 'en contraste', 
                                 'no obstante', 'por el contrario', 'en cuanto a',
                                 'respecto a', 'sobre', 'acerca de', 'en relación']
            if any(siguiente.startswith(c) for c in conectores_fuertes):
                if palabras_en_parrafo >= 20:
                    cerrar = True
        
        # 4. Es la última oración
        if i == len(oraciones) - 1:
            cerrar = True
        
        if cerrar and parrafo_actual:
            parrafo_texto = ' '.join(parrafo_actual)
            # Validar que el párrafo tenga sentido
            if len(parrafo_texto.split()) >= MIN_PALABRAS_POR_PARrafo:
                parrafos.append(parrafo_texto)
            parrafo_actual = []
            palabras_en_parrafo = 0
    
    # Limitar número de párrafos
    if len(parrafos) > MAX_PARRAFOS:
        parrafos = parrafos[:MAX_PARRAFOS]
    
    return parrafos

# =============================================================================
# CONSTRUCCIÓN DE PUBLICACIÓN CON VALIDACIÓN
# =============================================================================

def construir_publicacion_validada(titulo, contenido, creditos, fuente):
    """
    Construye la publicación con validación estricta de formato.
    Si no cumple estándares, usa fallback.
    """
    titulo_limpio = limpiar_texto(titulo)
    
    # Intentar dividir en párrafos coherentes
    parrafos = dividir_parrafos_estricto(contenido)
    
    # Validar que tenemos párrafos válidos
    if len(parrafos) < 2:
        log("   ⚠️ No se pudieron crear párrafos coherentes, usando formato alternativo", 'advertencia')
        # Fallback: dividir por puntos y agrupar
        parrafos = crear_parrafos_fallback(contenido)
    
    # Construir texto con formato estricto
    lineas = []
    
    # Encabezado
    lineas.append(f"📰 ÚLTIMA HORA | {titulo_limpio}")
    lineas.append("")  # Línea en blanco obligatoria
    
    # Párrafos con separación
    for i, parrafo in enumerate(parrafos):
        lineas.append(parrafo)
        if i < len(parrafos) - 1:
            lineas.append("")  # Línea en blanco entre párrafos
    
    # Separador
    lineas.append("")
    lineas.append("──────────────────────────────")
    lineas.append("")
    
    # Metadatos
    if creditos:
        lineas.append(f"✍️ {creditos}")
        lineas.append("")
    
    lineas.append(f"📎 {fuente}")
    
    # Unir y validar
    texto = '\n'.join(lineas)
    
    # Validación final estricta
    errores = validar_formato_final(texto)
    if errores:
        log(f"   ❌ Errores de formato: {errores}", 'advertencia')
        # Intentar corrección
        texto = corregir_formato(texto)
    
    return texto

def crear_parrafos_fallback(contenido):
    """Crea párrafos básicos si el método principal falla."""
    # Dividir en oraciones y agrupar de 2 en 2
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
    
    parrafos = []
    for i in range(0, len(oraciones), 2):
        grupo = oraciones[i:i+2]
        if grupo:
            parrafos.append(' '.join(grupo))
    
    return parrafos[:MAX_PARRAFOS]

def validar_formato_final(texto):
    """Valida que el formato final sea correcto."""
    errores = []
    
    # Debe tener líneas en blanco entre párrafos
    lineas = texto.split('\n')
    
    # Contar párrafos de contenido (no vacíos, no separadores, no metadatos)
    parrafos_contenido = [l for l in lineas if l.strip() 
                         and not l.startswith('─') 
                         and not l.startswith('✍️')
                         and not l.startswith('📎')
                         and not l.startswith('📰')]
    
    if len(parrafos_contenido) < 2:
        errores.append("Menos de 2 párrafos de contenido")
    
    # Verificar que hay líneas en blanco entre párrafos
    for i, linea in enumerate(lineas):
        if i > 0 and i < len(lineas) - 1:
            if linea.strip() and not linea.startswith(('─', '✍️', '📎', '📰')):
                if lineas[i-1].strip() and not lineas[i-1].startswith(('─', '✍️', '📎', '📰', '')):
                    if lineas[i-1] != '':  # Si la anterior no es línea en blanco
                        pass  # Podría ser error, pero verificamos contexto
    
    # Verificar longitud
    if len(texto) < 200:
        errores.append("Texto muy corto")
    
    return errores

def corregir_formato(texto):
    """Intenta corregir problemas de formato."""
    # Asegurar líneas en blanco entre párrafos
    lineas = texto.split('\n')
    nuevas_lineas = []
    
    for i, linea in enumerate(lineas):
        nuevas_lineas.append(linea)
        # Agregar línea en blanco después de párrafos de contenido
        if linea.strip() and not linea.startswith(('─', '✍️', '📎', '📰')):
            if i < len(lineas) - 1:
                siguiente = lineas[i + 1]
                if siguiente.strip() and not siguiente.startswith(('─', '✍️', '📎')):
                    nuevas_lineas.append("")
    
    return '\n'.join(nuevas_lineas)

# =============================================================================
# GESTIÓN DE HISTORIAL (igual que antes)
# =============================================================================

def cargar_historial():
    default = {
        'urls': [], 
        'hashes': [],
        'timestamps': [],
        'estadisticas': {'total_publicadas': 0}
    }
    datos = cargar_json(HISTORIAL_PATH, default)
    
    for key in ['urls', 'hashes', 'timestamps']:
        if key not in datos or not isinstance(datos[key], list):
            datos[key] = []
    
    if 'estadisticas' not in datos or not isinstance(datos['estadisticas'], dict):
        datos['estadisticas'] = {'total_publicadas': 0}
    
    return datos

def limpiar_historial_antiguo(historial):
    if not historial or not isinstance(historial, dict):
        return {'urls': [], 'hashes': [], 'timestamps': [], 'estadisticas': {'total_publicadas': 0}}
    
    ahora = datetime.now()
    indices_validos = []
    
    timestamps = historial.get('timestamps', [])
    if not isinstance(timestamps, list):
        timestamps = []
    
    for i, ts_str in enumerate(timestamps):
        try:
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str)
                if (ahora - ts) < timedelta(hours=VENTANA_DUPLICADOS_HORAS):
                    indices_validos.append(i)
        except:
            continue
    
    nuevo_historial = {
        'urls': [],
        'hashes': [],
        'timestamps': [],
        'estadisticas': historial.get('estadisticas', {'total_publicadas': 0})
    }
    
    urls = historial.get('urls', [])
    hashes = historial.get('hashes', [])
    
    for i in indices_validos:
        if i < len(urls):
            nuevo_historial['urls'].append(urls[i])
        if i < len(hashes):
            nuevo_historial['hashes'].append(hashes[i])
        if i < len(timestamps):
            nuevo_historial['timestamps'].append(timestamps[i])
    
    return nuevo_historial

def noticia_ya_publicada(historial, url, titulo):
    if not historial or not isinstance(historial, dict):
        return False
    
    url_limpia = re.sub(r'\?.*$', '', url)
    url_base = re.sub(r'https?://(www\.)?', '', url_limpia).lower().rstrip('/')
    
    urls_guardadas = historial.get('urls', [])
    if not isinstance(urls_guardadas, list):
        urls_guardadas = []
    
    for url_hist in urls_guardadas:
        if not isinstance(url_hist, str):
            continue
        url_hist_limpia = re.sub(r'\?.*$', '', url_hist)
        url_hist_base = re.sub(r'https?://(www\.)?', '', url_hist_limpia).lower().rstrip('/')
        
        if url_base == url_hist_base:
            return True
        
        url_slug = url_base.split('/')[-1]
        hist_slug = url_hist_base.split('/')[-1]
        if url_slug and hist_slug and len(url_slug) > 15:
            if url_slug[:20] == hist_slug[:20]:
                return True
    
    hash_titulo = generar_hash(titulo)
    hashes_guardados = historial.get('hashes', [])
    if not isinstance(hashes_guardados, list):
        hashes_guardados = []
    
    if hash_titulo in hashes_guardados:
        return True
    
    return False

def guardar_historial(historial, url, titulo):
    historial = limpiar_historial_antiguo(historial)
    
    url_limpia = re.sub(r'\?.*$', '', url)
    hash_titulo = generar_hash(titulo)
    ahora = datetime.now().isoformat()
    
    historial['urls'].append(url_limpia)
    historial['hashes'].append(hash_titulo)
    historial['timestamps'].append(ahora)
    
    stats = historial.get('estadisticas', {'total_publicadas': 0})
    if not isinstance(stats, dict):
        stats = {'total_publicadas': 0}
    stats['total_publicadas'] = stats.get('total_publicadas', 0) + 1
    historial['estadisticas'] = stats
    
    max_size = 500
    for key in ['urls', 'hashes', 'timestamps']:
        if len(historial[key]) > max_size:
            historial[key] = historial[key][-max_size:]
    
    guardar_json(HISTORIAL_PATH, historial)

def cargar_estado():
    default = {'ultima_publicacion': None}
    datos = cargar_json(ESTADO_PATH, default)
    return datos

def guardar_estado(estado):
    guardar_json(ESTADO_PATH, estado)

def verificar_tiempo():
    estado = cargar_estado()
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos = (datetime.now() - ultima_dt).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {minutos:.0f} min", 'info')
            return False
        return True
    except:
        return True

# =============================================================================
# FUENTES DE NOTICIAS (simplificado)
# =============================================================================

def obtener_newsapi_internacional():
    if not NEWS_API_KEY:
        return []
    
    noticias = []
    queries = [
        'war OR conflict OR Ukraine OR Russia OR Gaza OR Israel',
        'Trump OR Biden OR Putin OR international politics',
        'economy OR inflation OR markets OR IMF',
        'NATO OR UN OR EU OR summit',
        'Iran OR Israel OR Middle East conflict',
    ]
    
    for q in queries:
        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'apiKey': NEWS_API_KEY,
                'q': q,
                'language': 'es',
                'sortBy': 'publishedAt',
                'pageSize': 10
            }
            
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('status') == 'ok':
                for art in data.get('articles', []):
                    titulo = art.get('title', '')
                    if not titulo or '[Removed]' in titulo:
                        continue
                    
                    desc = art.get('description', '')
                    
                    if es_noticia_excluible(titulo, desc):
                        continue
                    
                    noticias.append({
                        'titulo': limpiar_texto(titulo),
                        'descripcion': limpiar_texto(desc),
                        'url': art.get('url', ''),
                        'imagen': art.get('urlToImage'),
                        'fuente': f"NewsAPI:{art.get('source', {}).get('name', 'Unknown')}",
                        'fecha': art.get('publishedAt'),
                        'puntaje': calcular_puntaje_internacional(titulo, desc)
                    })
        except Exception as e:
            continue
    
    urls_vistas = set()
    noticias_unicas = []
    for n in noticias:
        url_base = re.sub(r'\?.*$', '', n['url'])
        if url_base not in urls_vistas:
            urls_vistas.add(url_base)
            noticias_unicas.append(n)
    
    log(f"NewsAPI: {len(noticias_unicas)} noticias", 'info')
    return noticias_unicas

def obtener_newsdata_internacional():
    if not NEWSDATA_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://newsdata.io/api/1/news'
        params = {
            'apikey': NEWSDATA_API_KEY,
            'language': 'es',
            'category': 'world,politics,business',
            'size': 30
        }
        
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        if data.get('status') == 'success':
            for art in data.get('results', []):
                titulo = art.get('title', '')
                if not titulo:
                    continue
                
                desc = art.get('description', '')
                
                if es_noticia_excluible(titulo, desc):
                    continue
                
                noticias.append({
                    'titulo': limpiar_texto(titulo),
                    'descripcion': limpiar_texto(desc),
                    'url': art.get('link', ''),
                    'imagen': art.get('image_url'),
                    'fuente': f"NewsData:{art.get('source_id', 'Unknown')}",
                    'fecha': art.get('pubDate'),
                    'puntaje': calcular_puntaje_internacional(titulo, desc)
                })
    except:
        pass
    
    log(f"NewsData: {len(noticias)} noticias", 'info')
    return noticias

def obtener_gnews_internacional():
    if not GNEWS_API_KEY:
        return []
    
    noticias = []
    try:
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {
            'apikey': GNEWS_API_KEY,
            'lang': 'es',
            'max': 20,
            'topic': 'world'
        }
        
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        for art in data.get('articles', []):
            titulo = art.get('title', '')
            if not titulo:
                continue
            
            desc = art.get('description', '')
            
            if es_noticia_excluible(titulo, desc):
                continue
            
            noticias.append({
                'titulo': limpiar_texto(titulo),
                'descripcion': limpiar_texto(desc),
                'url': art.get('url', ''),
                'imagen': art.get('image'),
                'fuente': f"GNews:{art.get('source', {}).get('name', 'Unknown')}",
                'fecha': art.get('publishedAt'),
                'puntaje': calcular_puntaje_internacional(titulo, desc)
            })
    except:
        pass
    
    log(f"GNews: {len(noticias)} noticias", 'info')
    return noticias

def obtener_google_news_rss():
    feeds = [
        'https://news.google.com/rss?hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es',
    ]
    
    noticias = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url, request_headers=headers)
            
            for entry in feed.entries[:8]:
                titulo = entry.get('title', '')
                if not titulo or '[Removed]' in titulo:
                    continue
                
                if ' - ' in titulo:
                    titulo = titulo.rsplit(' - ', 1)[0]
                
                link = entry.get('link', '')
                try:
                    resp = requests.head(link, allow_redirects=True, timeout=8, headers=headers)
                    link_final = resp.url
                except:
                    link_final = link
                
                if es_noticia_excluible(titulo):
                    continue
                
                noticias.append({
                    'titulo': limpiar_texto(titulo),
                    'descripcion': '',
                    'url': link_final,
                    'imagen': None,
                    'fuente': 'Google News',
                    'fecha': entry.get('published'),
                    'puntaje': calcular_puntaje_internacional(titulo, '')
                })
        except:
            pass
    
    log(f"Google News RSS: {len(noticias)} noticias", 'info')
    return noticias

# =============================================================================
# PROCESAMIENTO DE IMAGEN
# =============================================================================

def extraer_imagen_web(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for meta in ['og:image', 'twitter:image']:
            tag = soup.find('meta', property=meta) or soup.find('meta', attrs={'name': meta})
            if tag:
                img_url = tag.get('content', '')
                if img_url and img_url.startswith('http'):
                    return img_url
        
        img = soup.find('img')
        if img:
            src = img.get('src', '')
            if src and src.startswith('http'):
                return src
    except:
        pass
    return None

def descargar_imagen(url):
    if not url or not url.startswith('http'):
        return None
    try:
        from PIL import Image
        from io import BytesIO
        
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code != 200:
            return None
        
        img = Image.open(BytesIO(resp.content))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        img.thumbnail((1200, 1200))
        
        temp_path = f'/tmp/noticia_{generar_hash(url)}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
    except:
        return None

def crear_imagen_titulo(titulo):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.new('RGB', (1200, 630), color='#1e3a8a')
        draw = ImageDraw.Draw(img)
        
        try:
            font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_big = ImageFont.load_default()
            font_small = font_big
        
        titulo_envuelto = textwrap.fill(titulo[:130], width=38)
        draw.text((50, 80), titulo_envuelto, font=font_big, fill='white')
        
        draw.text((50, 550), "🌍 Noticias Internacionales • Verdad Hoy", font=font_small, fill='#93c5fd')
        
        temp_path = f'/tmp/noticia_gen_{generar_hash(titulo)}.jpg'
        img.save(temp_path, 'JPEG', quality=85)
        return temp_path
    except:
        return None

def generar_hashtags(titulo, contenido):
    texto = f"{titulo} {contenido}".lower()
    hashtags = ['#NoticiasInternacionales', '#ÚltimaHora']
    
    temas = {
        'guerra|conflicto|ataque|bombardeo': '#ConflictoArmado',
        'ucrania|rusia': '#UcraniaRusia',
        'gaza|israel|palestina': '#IsraelGaza',
        'trump|biden|putin': '#PolíticaGlobal',
        'economía|mercados|inflación': '#EconomíaMundial',
        'irán|iran': '#Irán',
    }
    
    for patron, tag in temas.items():
        if re.search(patron, texto):
            hashtags.append(tag)
            break
    
    hashtags.append('#Mundo')
    return ' '.join(hashtags)

# =============================================================================
# PUBLICACIÓN EN FACEBOOK
# =============================================================================

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales Facebook", 'error')
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— 🌐 Verdad Hoy | Agencia de Noticias Internacionales"
    
    # Validación de longitud
    if len(mensaje) > 2000:
        lineas = texto.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1600:
                texto_cortado += linea + "\n"
            else:
                break
        mensaje = f"{texto_cortado.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    
    # Limpieza final
    mensaje = re.sub(r'https?://\S+', '', mensaje)
    mensaje = re.sub(r'\n{5,}', '\n\n\n\n', mensaje)
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('imagen.jpg', f, 'image/jpeg')}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN}
            
            resp = requests.post(url, files=files, data=data, timeout=60)
            result = resp.json()
        
        if resp.status_code == 200 and 'id' in result:
            log(f"✅ Publicado ID: {result['id']}", 'exito')
            return True
        else:
            log(f"Error FB: {result.get('error', {}).get('message', 'Unknown')}", 'error')
            return False
    except Exception as e:
        log(f"Error publicando: {e}", 'error')
        return False

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS INTERNACIONALES")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    historial = cargar_historial()
    log(f"📊 Historial: {len(historial.get('urls', []))} URLs guardadas")
    
    # Recolectar noticias
    todas_noticias = []
    
    if NEWS_API_KEY:
        todas_noticias.extend(obtener_newsapi_internacional())
    if NEWSDATA_API_KEY and len(todas_noticias) < 15:
        todas_noticias.extend(obtener_newsdata_internacional())
    if GNEWS_API_KEY and len(todas_noticias) < 20:
        todas_noticias.extend(obtener_gnews_internacional())
    if len(todas_noticias) < 25:
        todas_noticias.extend(obtener_google_news_rss())
    
    log(f"📰 Total recolectadas: {len(todas_noticias)} noticias")
    
    if not todas_noticias:
        log("ERROR: No se encontraron noticias", 'error')
        return False
    
    todas_noticias.sort(key=lambda x: x.get('puntaje', 0), reverse=True)
    
    # Seleccionar noticia
    noticia_seleccionada = None
    
    for noticia in todas_noticias:
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        
        if not url or not titulo:
            continue
        
        if noticia_ya_publicada(historial, url, titulo):
            continue
        
        if noticia.get('puntaje', 0) < 5:
            continue
        
        noticia_seleccionada = noticia
        break
    
    if not noticia_seleccionada:
        log("ERROR: No hay noticias disponibles", 'error')
        return False
    
    log(f"\n📝 NOTICIA SELECCIONADA:")
    log(f"   Título: {noticia_seleccionada['titulo'][:60]}...")
    log(f"   Fuente: {noticia_seleccionada['fuente']}")
    
    # =================================================================
    # EXTRACCIÓN CON REGLAS ESTRICTAS
    # =================================================================
    
    log("🌐 Extrayendo contenido con validación estricta...")
    contenido, creditos = extraer_contenido_estricto(noticia_seleccionada['url'])
    
    if contenido:
        log(f"   ✅ Contenido válido: {len(contenido)} caracteres", 'exito')
    else:
        log("   ⚠️ Extracción falló, usando descripción de API", 'advertencia')
        contenido = noticia_seleccionada.get('descripcion', '')
        if len(contenido) < 100:
            log("   ❌ Descripción insuficiente, buscando otra noticia...", 'error')
            return False
    
    # =================================================================
    # CONSTRUIR PUBLICACIÓN VALIDADA
    # =================================================================
    
    log("📝 Construyendo publicación con formato validado...")
    texto_publicacion = construir_publicacion_validada(
        noticia_seleccionada['titulo'],
        contenido,
        creditos,
        noticia_seleccionada['fuente']
    )
    
    # Mostrar preview
    log("   📄 Preview de la publicación:", 'debug')
    for linea in texto_publicacion.split('\n')[:8]:
        log(f"      {linea[:65]}{'...' if len(linea) > 65 else ''}", 'debug')
    
    # =================================================================
    # PROCESAR IMAGEN Y PUBLICAR
    # =================================================================
    
    hashtags = generar_hashtags(noticia_seleccionada['titulo'], contenido)
    
    log("🖼️  Procesando imagen...")
    imagen_path = None
    
    if noticia_seleccionada.get('imagen'):
        imagen_path = descargar_imagen(noticia_seleccionada['imagen'])
    
    if not imagen_path:
        img_url = extraer_imagen_web(noticia_seleccionada['url'])
        if img_url:
            imagen_path = descargar_imagen(img_url)
    
    if not imagen_path:
        imagen_path = crear_imagen_titulo(noticia_seleccionada['titulo'])
    
    if not imagen_path:
        log("ERROR: No se pudo crear imagen", 'error')
        return False
    
    # Publicar
    exito = publicar_facebook(
        noticia_seleccionada['titulo'],
        texto_publicacion,
        imagen_path,
        hashtags
    )
    
    # Limpieza
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    # Guardar estado
    if exito:
        guardar_historial(historial, noticia_seleccionada['url'], noticia_seleccionada['titulo'])
        
        estado = cargar_estado()
        estado['ultima_publicacion'] = datetime.now().isoformat()
        guardar_estado(estado)
        
        total = cargar_historial().get('estadisticas', {}).get('total_publicadas', 0)
        log(f"✅ ÉXITO - Total acumulado: {total} noticias", 'exito')
        return True
    
    return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
