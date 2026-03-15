#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias Internacionales para Facebook - VERSIÓN 3.1 CORREGIDA
- ✅ CORRECCIÓN: Sistema de puntuación por palabras individuales
- ✅ CORRECCIÓN: Resolución de redirecciones Google News
- ✅ CORRECCIÓN: Continuar buscando si una noticia falla
- Persistencia de historial extendida a 72 horas
- Detección de títulos similares (70% de coincidencia)
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
from difflib import SequenceMatcher

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
VENTANA_DUPLICADOS_HORAS = 72    # 72 horas (3 días)
UMBRAL_SIMILITUD_TITULO = 0.70   # 70% de coincidencia
UMBRAL_SIMILITUD_CONTENIDO = 0.65
MAX_TITULOS_HISTORIA = 150

# Blacklist de títulos genéricos
BLACKLIST_TITULOS = [
    r'^\s*última hora\s*$',
    r'^\s*breaking news\s*$', 
    r'^\s*noticias de hoy\s*$',
    r'^\s*resumen de noticias\s*$',
    r'^\s*titulares del día\s*$',
    r'^\s*flash informativo\s*$',
    r'^\s*boletín de noticias\s*$',
    r'^\s*actualidad internacional\s*$',
    r'^\s*mundo hoy\s*$',
    r'^\s*news update\s*$',
]

# =============================================================================
# REGLAS ESTRICTAS DE VALIDACIÓN
# =============================================================================

MIN_CARACTERES_CONTENIDO = 300
MIN_ORACIONES = 3
MAX_PARRAFOS = 8
MIN_PALABRAS_POR_PARrafo = 15

FRASES_PROHIBIDAS = [
    'actualidad portada', 'publicado:', 'compartir en', 'síguenos en',
    'cookies', 'aceptar cookies', 'política de privacidad', 'aviso legal',
    'todos los derechos reservados', 'copyright', 'suscríbete', 'newsletter',
    'última hora', 'portada', 'menú', 'buscar', 'inicio', 'contacto',
    'redes sociales', 'facebook', 'twitter', 'instagram', 'whatsapp',
    'relacionados', 'también te interesa', 'más noticias', 'etiquetas:',
    'archivado en:', 'ver comentarios', 'ocultar comentarios'
]

PATRONES_RUIDO = [
    r'Vista de.*Gettyimages?\.[a-z]+',
    r'Stringer\s*/\s*\w+',
    r'@\w+',
    r'—\s*\w+\s*\(@\w+\)\s*\w+\s+\d+',
    r'🚀.*$',
    r'El senador.*afirma.*mintió.*$',
    r'^\s*—\s*$',
]

# =============================================================================
# PALABRAS CLAVE INTERNACIONALES
# =============================================================================

PALABRAS_ALTA_PRIORIDAD = [
    "noticias urgentes hoy",
    "ultima hora internacional", 
    "breaking news today",
    "conflicto mundial hoy",
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
    "refugiados guerra",
    "crisis humanitaria hoy",
    "ayuda humanitaria bloqueada",
    "hambruna conflicto",
    "desplazados guerra",
    "campo refugiados",
    "genocidio noticias",
    "crimenes guerra",
    "tribunal penal internacional",
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
    "israel palestina guerra",
    "iran noticias hoy",
    "arabia saudi noticias",
    "yemen guerra hoy",
    "siria conflicto actual",
    "libano hezbollah",
    "irak noticias hoy",
    "emiratos arabes noticias",
    "qatar crisis diplomatica",
    "kurdistan conflicto",
    "zelensky",
    "netanyahu",
    "hamas",
    "hezbollah",
    "houthis",
    "red sea crisis",
    "taiwan strait",
    "south china sea",
    "arctic militarization",
    "space force",
    "nuclear proliferation",
    "climate war",
    "water conflict",
    "rare earth embargo",
    "chip war"
]

PALABRAS_MEDIA_PRIORIDAD = [
    'economía mundial', 'mercados globales', 'inflación', 'FMI', 
    'China', 'EEUU', 'Estados Unidos', 'Reino Unido', 'Alemania', 'Francia',
    'Banco Mundial', 'reserva federal', 'eurozona', 'petroleo precio',
    'gas natural', 'energia crisis', 'bitcoin', 'criptomonedas'
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
    return hashlib.md5(texto_normalizado.encode()).hexdigest()

def generar_hash_contenido(texto, longitud=800):
    if not texto:
        return ""
    muestra = texto.lower()[:longitud]
    muestra = re.sub(r'[^\w\s]', '', muestra)
    muestra = re.sub(r'\s+', ' ', muestra).strip()
    return hashlib.md5(muestra.encode()).hexdigest()

def normalizar_url(url):
    if not url:
        return ""
    url = re.sub(r'\?.*$', '', url)
    url = re.sub(r'#.*$', '', url)
    url = re.sub(r'https?://(www\.)?', '', url)
    return url.lower().rstrip('/')

def normalizar_url_v2(url):
    if not url:
        return ""
    url = url.lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^(www\.|m\.|movil\.|mobile\.|touch\.|wap\.)', '', url)
    url = re.sub(r'\?(utm_source|utm_medium|utm_campaign|fbclid|gclid|ref|source|medium|campaign|from|share|si|spref)=.*$', '', url)
    url = re.sub(r'\?.*$', '', url)
    url = re.sub(r'#.*$', '', url)
    url = url.rstrip('/')
    return url

def calcular_similitud_titulos(titulo1, titulo2):
    if not titulo1 or not titulo2:
        return 0.0
    
    def normalizar(t):
        t = t.lower()
        t = re.sub(r'[^\w\s]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t
    
    t1 = normalizar(titulo1)
    t2 = normalizar(titulo2)
    
    if not t1 or not t2:
        return 0.0
    
    return SequenceMatcher(None, t1, t2).ratio()

def es_titulo_generico(titulo):
    if not titulo:
        return True
    
    titulo_lower = titulo.lower().strip()
    
    for patron in BLACKLIST_TITULOS:
        if re.match(patron, titulo_lower):
            return True
    
    stop_words = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'al', 
                  'y', 'o', 'pero', 'en', 'con', 'por', 'para', 'a', 'ante',
                  'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'at',
                  'hoy', 'ayer', 'ahora', 'hace', 'después', 'antes'}
    
    palabras = [p for p in re.findall(r'\b\w+\b', titulo_lower) 
                if p not in stop_words and len(p) > 3]
    
    if len(set(palabras)) < 4:
        return True
    
    return False

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

# ✅ CORREGIDO: Sistema de puntuación por palabras individuales
def calcular_puntaje_internacional(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    puntaje = 0
    
    # Buscar palabras individuales de alta prioridad
    for frase in PALABRAS_ALTA_PRIORIDAD:
        palabras = frase.lower().split()
        for palabra in palabras:
            if len(palabra) >= 4 and palabra in texto:
                puntaje += 3
                break
        
        if frase.lower() in texto:
            puntaje += 7
    
    # Buscar palabras de media prioridad
    for frase in PALABRAS_MEDIA_PRIORIDAD:
        palabras = frase.lower().split()
        for palabra in palabras:
            if len(palabra) >= 3 and palabra in texto:
                puntaje += 1
                break
    
    # Bonus por longitud óptima
    if 30 <= len(titulo) <= 150:
        puntaje += 2
    
    # Bonus por descripción sustancial
    if len(descripcion) >= 50:
        puntaje += 2
    
    # Bonus por múltiples palabras clave
    palabras_encontradas = len([p for p in PALABRAS_ALTA_PRIORIDAD 
                                if any(word in texto for word in p.lower().split() if len(word) >= 4)])
    if palabras_encontradas >= 3:
        puntaje += 5
    
    return puntaje

# =============================================================================
# EXTRACCIÓN CON REGLAS ESTRICTAS
# =============================================================================

def extraer_contenido_estricto(url):
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
        
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                            'form', 'button', 'iframe', 'noscript', 'svg', 'canvas']):
            element.decompose()
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
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
        
        contenido = None
        creditos = None
        
        article = soup.find('article')
        if article:
            parrafos = article.find_all('p')
            if len(parrafos) >= 3:
                texto_limpio = extraer_parrafos_limpios(parrafos)
                if validar_calidad(texto_limpio):
                    contenido = texto_limpio
                    log(f"   ✅ Article válido: {len(contenido)} chars", 'debug')
        
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
        
        if not contenido:
            todos_p = soup.find_all('p')
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
    textos = []
    for p in parrafos:
        texto = p.get_text(strip=True)
        texto = limpiar_texto(texto)
        
        if len(texto) < 40:
            continue
        if tiene_basura(texto):
            continue
        if texto.count(' ') < 5:
            continue
            
        textos.append(texto)
    
    return ' '.join(textos)

def tiene_basura(texto):
    texto_lower = texto.lower()
    
    for frase in FRASES_PROHIBIDAS:
        if frase in texto_lower:
            return True
    
    if texto.isupper() and len(texto) > 10:
        return True
    
    simbolos = sum(1 for c in texto if c in '│├┤┬┴┼║╣╠╩╦╚╔╝╗▓▒░')
    if simbolos > 2:
        return True
    
    return False

def validar_calidad(texto):
    if not texto:
        return False
    
    if len(texto) < MIN_CARACTERES_CONTENIDO:
        log(f"   ❌ Muy corto: {len(texto)} chars", 'debug')
        return False
    
    oraciones = [o for o in re.split(r'[.!?]+', texto) if len(o.strip()) > 10]
    if len(oraciones) < MIN_ORACIONES:
        log(f"   ❌ Pocas oraciones: {len(oraciones)}", 'debug')
        return False
    
    ratio_mayus = sum(1 for c in texto if c.isupper()) / len(texto)
    if ratio_mayus > 0.4:
        log(f"   ❌ Muchas mayúsculas: {ratio_mayus:.2f}", 'debug')
        return False
    
    palabras_clave = ['dice', 'declaró', 'afirmó', 'señaló', 'indicó', 'según', 'tras']
    if not any(p in texto.lower() for p in palabras_clave):
        log(f"   ❌ No parece noticia (falta verbo de comunicación)", 'debug')
        return False
    
    log(f"   ✅ Calidad validada: {len(texto)} chars, {len(oraciones)} oraciones", 'debug')
    return True

def eliminar_ruido_final(texto):
    for patron in PATRONES_RUIDO:
        texto = re.sub(patron, '', texto, flags=re.IGNORECASE | re.MULTILINE)
    
    lineas = texto.split('\n')
    lineas_limpias = []
    for linea in lineas:
        linea_limpia = linea.strip()
        if linea_limpia and not re.match(r'^[\s\—\-\|\•\·]+$', linea_limpia):
            lineas_limpias.append(linea_limpia)
    
    texto = ' '.join(lineas_limpias)
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    if texto and texto[-1] not in '.!?':
        texto += '.'
    
    return texto

def extraer_creditos_limpios(soup):
    creditos = None
    
    for meta in ['author', 'article:author', 'byline', 'creator']:
        tag = soup.find('meta', attrs={'name': meta}) or soup.find('meta', property=meta)
        if tag:
            creditos = tag.get('content', '').strip()
            if creditos and len(creditos) < 100:
                return limpiar_credito(creditos)
    
    for clase in ['author', 'byline', 'autor', 'firma']:
        elem = soup.find(class_=lambda x: x and clase in x.lower())
        if elem:
            texto = elem.get_text(strip=True)
            if 5 < len(texto) < 100:
                return limpiar_credito(texto)
    
    return None

def limpiar_credito(credito):
    if not credito:
        return None
    
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
    if not texto:
        return []
    
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
        
        cerrar = False
        
        if palabras_en_parrafo >= 40:
            cerrar = True
        
        if '"' in oracion or '»' in oracion:
            comillas_abrir = oracion.count('"') + oracion.count('«')
            comillas_cerrar = oracion.count('"') + oracion.count('»')
            if comillas_cerrar > comillas_abrir or (comillas_abrir % 2 == 0 and comillas_abrir > 0):
                if palabras_en_parrafo >= 25:
                    cerrar = True
        
        if i < len(oraciones) - 1:
            siguiente = oraciones[i + 1].lower()
            conectores_fuertes = ['sin embargo', 'por otro lado', 'en contraste', 
                                 'no obstante', 'por el contrario', 'en cuanto a',
                                 'respecto a', 'sobre', 'acerca de', 'en relación']
            if any(siguiente.startswith(c) for c in conectores_fuertes):
                if palabras_en_parrafo >= 20:
                    cerrar = True
        
        if i == len(oraciones) - 1:
            cerrar = True
        
        if cerrar and parrafo_actual:
            parrafo_texto = ' '.join(parrafo_actual)
            if len(parrafo_texto.split()) >= MIN_PALABRAS_POR_PARrafo:
                parrafos.append(parrafo_texto)
            parrafo_actual = []
            palabras_en_parrafo = 0
    
    if len(parrafos) > MAX_PARRAFOS:
        parrafos = parrafos[:MAX_PARRAFOS]
    
    return parrafos

# =============================================================================
# CONSTRUCCIÓN DE PUBLICACIÓN CON VALIDACIÓN
# =============================================================================

def construir_publicacion_validada(titulo, contenido, creditos, fuente):
    titulo_limpio = limpiar_texto(titulo)
    
    parrafos = dividir_parrafos_estricto(contenido)
    
    if len(parrafos) < 2:
        log("   ⚠️ No se pudieron crear párrafos coherentes, usando formato alternativo", 'advertencia')
        parrafos = crear_parrafos_fallback(contenido)
    
    lineas = []
    
    lineas.append(f"📰 ÚLTIMA HORA | {titulo_limpio}")
    lineas.append("")
    
    for i, parrafo in enumerate(parrafos):
        lineas.append(parrafo)
        if i < len(parrafos) - 1:
            lineas.append("")
    
    lineas.append("")
    lineas.append("──────────────────────────────")
    lineas.append("")
    
    if creditos:
        lineas.append(f"✍️ {creditos}")
        lineas.append("")
    
    lineas.append(f"📎 {fuente}")
    
    texto = '\n'.join(lineas)
    
    errores = validar_formato_final(texto)
    if errores:
        log(f"   ❌ Errores de formato: {errores}", 'advertencia')
        texto = corregir_formato(texto)
    
    return texto

def crear_parrafos_fallback(contenido):
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
    
    parrafos = []
    for i in range(0, len(oraciones), 2):
        grupo = oraciones[i:i+2]
        if grupo:
            parrafos.append(' '.join(grupo))
    
    return parrafos[:MAX_PARRAFOS]

def validar_formato_final(texto):
    errores = []
    
    lineas = texto.split('\n')
    
    parrafos_contenido = [l for l in lineas if l.strip() 
                         and not l.startswith('─') 
                         and not l.startswith('✍️')
                         and not l.startswith('📎')
                         and not l.startswith('📰')]
    
    if len(parrafos_contenido) < 2:
        errores.append("Menos de 2 párrafos de contenido")
    
    for i, linea in enumerate(lineas):
        if i > 0 and i < len(lineas) - 1:
            if linea.strip() and not linea.startswith(('─', '✍️', '📎', '📰')):
                if lineas[i-1].strip() and not lineas[i-1].startswith(('─', '✍️', '📎', '📰', '')):
                    if lineas[i-1] != '':
                        pass
    
    if len(texto) < 200:
        errores.append("Texto muy corto")
    
    return errores

def corregir_formato(texto):
    lineas = texto.split('\n')
    nuevas_lineas = []
    
    for i, linea in enumerate(lineas):
        nuevas_lineas.append(linea)
        if linea.strip() and not linea.startswith(('─', '✍️', '📎', '📰')):
            if i < len(lineas) - 1:
                siguiente = lineas[i + 1]
                if siguiente.strip() and not siguiente.startswith(('─', '✍️', '📎')):
                    nuevas_lineas.append("")
    
    return '\n'.join(nuevas_lineas)

# =============================================================================
# GESTIÓN DE HISTORIAL
# =============================================================================

def cargar_historial():
    default = {
        'urls': [], 
        'hashes': [],
        'timestamps': [],
        'titulos': [],
        'descripciones': [],
        'hashes_contenido': [],
        'hashes_permanentes': [],
        'estadisticas': {'total_publicadas': 0}
    }
    datos = cargar_json(HISTORIAL_PATH, default)
    
    for key in default.keys():
        if key not in datos or not isinstance(datos[key], type(default[key])):
            datos[key] = default[key]
    
    return datos

def limpiar_historial_antiguo(historial):
    if not historial or not isinstance(historial, dict):
        return cargar_historial()
    
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
    
    total = len(timestamps)
    for i in range(max(0, total - 50), total):
        indices_validos.append(i)
    
    indices_validos = sorted(set(indices_validos))
    
    nuevo_historial = {
        'urls': [],
        'hashes': [],
        'timestamps': [],
        'titulos': [],
        'descripciones': [],
        'hashes_contenido': [],
        'estadisticas': historial.get('estadisticas', {'total_publicadas': 0})
    }
    
    urls = historial.get('urls', [])
    hashes = historial.get('hashes', [])
    titulos = historial.get('titulos', [])
    descripciones = historial.get('descripciones', [])
    hashes_contenido = historial.get('hashes_contenido', [])
    
    for i in indices_validos:
        if i < len(urls):
            nuevo_historial['urls'].append(urls[i])
        if i < len(hashes):
            nuevo_historial['hashes'].append(hashes[i])
        if i < len(timestamps):
            nuevo_historial['timestamps'].append(timestamps[i])
        if i < len(titulos):
            nuevo_historial['titulos'].append(titulos[i])
        if i < len(descripciones):
            nuevo_historial['descripciones'].append(descripciones[i])
        if i < len(hashes_contenido):
            nuevo_historial['hashes_contenido'].append(hashes_contenido[i])
    
    todos_hashes = historial.get('hashes', []) + historial.get('hashes_permanentes', [])
    nuevo_historial['hashes_permanentes'] = todos_hashes[-300:] if len(todos_hashes) > 300 else todos_hashes
    
    return nuevo_historial

def noticia_ya_publicada(historial, url, titulo, descripcion=""):
    if not historial or not isinstance(historial, dict):
        return False, "sin_historial"
    
    url_norm = normalizar_url_v2(url)
    hash_titulo = generar_hash(titulo)
    hash_desc = generar_hash_contenido(descripcion) if descripcion else ""
    
    log(f"   🔍 Verificando duplicados:", 'debug')
    log(f"      URL: {url_norm[:60]}...", 'debug')
    log(f"      Hash: {hash_titulo[:16]}", 'debug')
    
    if es_titulo_generico(titulo):
        log(f"   ⚠️ RECHAZADO: Título demasiado genérico", 'advertencia')
        return True, "titulo_generico"
    
    urls_guardadas = historial.get('urls', [])
    for i, url_hist in enumerate(urls_guardadas):
        if not isinstance(url_hist, str):
            continue
            
        if url_norm == normalizar_url_v2(url_hist):
            log(f"   ⚠️ DUPLICADO: URL idéntica (índice {i})", 'debug')
            return True, "url_exacta"
        
        path_actual = '/'.join(url_norm.split('/')[1:])
        path_hist = '/'.join(normalizar_url_v2(url_hist).split('/')[1:])
        
        if path_actual and path_actual == path_hist and len(path_actual) > 20:
            log(f"   ⚠️ DUPLICADO: Mismo path de URL", 'debug')
            return True, "url_path_identico"
    
    hashes_actuales = historial.get('hashes', [])
    hashes_permanentes = historial.get('hashes_permanentes', [])
    todos_hashes = list(dict.fromkeys(hashes_actuales + hashes_permanentes))
    
    if hash_titulo in todos_hashes:
        log(f"   ⚠️ DUPLICADO: Hash de título exacto", 'debug')
        return True, "hash_titulo_exacto"
    
    if hash_desc and 'hashes_contenido' in historial:
        if hash_desc in historial['hashes_contenido']:
            log(f"   ⚠️ DUPLICADO: Mismo contenido/descripción", 'debug')
            return True, "hash_contenido_exacto"
    
    titulos_guardados = historial.get('titulos', [])
    max_similitud = 0.0
    
    for titulo_hist in titulos_guardados:
        if not isinstance(titulo_hist, str):
            continue
        
        similitud = calcular_similitud_titulos(titulo, titulo_hist)
        max_similitud = max(max_similitud, similitud)
        
        if similitud >= UMBRAL_SIMILITUD_TITULO:
            log(f"   ⚠️ DUPLICADO: Similitud de título {similitud:.1%}", 'debug')
            log(f"      Nuevo: {titulo[:50]}...", 'debug')
            log(f"      Viejo: {titulo_hist[:50]}...", 'debug')
            return True, f"similitud_titulo_{similitud:.2f}"
    
    if descripcion and 'descripciones' in historial:
        desc_recientes = historial['descripciones'][-30:]
        
        for desc_hist in desc_recientes:
            if not isinstance(desc_hist, str) or not desc_hist:
                continue
            
            palabras_nueva = set(re.findall(r'\b\w{5,}\b', descripcion.lower()))
            palabras_vieja = set(re.findall(r'\b\w{5,}\b', desc_hist.lower()))
            
            if palabras_nueva and palabras_vieja:
                interseccion = len(palabras_nueva & palabras_vieja)
                union = len(palabras_nueva | palabras_vieja)
                similitud_jaccard = interseccion / union if union > 0 else 0
                
                if similitud_jaccard >= UMBRAL_SIMILITUD_CONTENIDO:
                    log(f"   ⚠️ DUPLICADO: Similitud de contenido {similitud_jaccard:.1%}", 'debug')
                    return True, f"similitud_contenido_{similitud_jaccard:.2f}"
    
    log(f"   ✅ NUEVO: Max similitud encontrada {max_similitud:.1%}", 'debug')
    return False, "nuevo"

def guardar_historial(historial, url, titulo, descripcion=""):
    campos_necesarios = {
        'urls': [], 'hashes': [], 'timestamps': [], 'titulos': [],
        'descripciones': [], 'hashes_contenido': [], 
        'hashes_permanentes': [], 'estadisticas': {'total_publicadas': 0}
    }
    
    for campo, default in campos_necesarios.items():
        if campo not in historial or not isinstance(historial[campo], type(default)):
            historial[campo] = default
    
    url_limpia = normalizar_url_v2(url)
    hash_titulo = generar_hash(titulo)
    hash_contenido = generar_hash_contenido(descripcion)
    ahora = datetime.now().isoformat()
    
    historial['urls'].append(url_limpia)
    historial['hashes'].append(hash_titulo)
    historial['timestamps'].append(ahora)
    historial['titulos'].append(titulo)
    historial['descripciones'].append(descripcion[:600] if descripcion else "")
    historial['hashes_contenido'].append(hash_contenido)
    
    historial['estadisticas']['total_publicadas'] = \
        historial['estadisticas'].get('total_publicadas', 0) + 1
    
    historial['hashes_permanentes'].append(hash_titulo)
    if len(historial['hashes_permanentes']) > 300:
        historial['hashes_permanentes'] = historial['hashes_permanentes'][-300:]
    
    max_size = MAX_TITULOS_HISTORIA
    for key in ['urls', 'hashes', 'timestamps', 'titulos', 'descripciones', 'hashes_contenido']:
        if len(historial[key]) > max_size:
            historial[key] = historial[key][-max_size:]
    
    historial = limpiar_historial_antiguo(historial)
    
    guardar_json(HISTORIAL_PATH, historial)
    return historial

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
# FUENTES DE NOTICIAS
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
        'Zelensky OR Netanyahu OR Hamas',
        'rare earth minerals OR lithium conflict',
        'AI warfare OR cyber attack military',
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

# ✅ NUEVA FUNCIÓN: Resolver redirecciones de Google News
def resolver_redireccion_google_news(url_google):
    """
    Resuelve las redirecciones de Google News RSS para obtener URL real del artículo.
    """
    if not url_google:
        return None
    
    if not url_google.startswith('https://news.google.com'):
        return url_google
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        resp = requests.get(
            url_google, 
            headers=headers, 
            timeout=15, 
            allow_redirects=True
        )
        
        url_final = resp.url
        
        if 'google.com' in url_final and '/sorry' in url_final:
            log(f"   ⚠️ Google bloqueó la redirección (captcha)", 'debug')
            return None
            
        if url_final == url_google:
            resp_head = requests.head(
                url_google, 
                headers=headers, 
                timeout=10, 
                allow_redirects=True
            )
            url_final = resp_head.url
        
        url_limpia = re.sub(r'\?(utm_source|utm_medium|utm_campaign|fbclid|gclid|ref|source|medium|campaign|from|share|si|spref)=.*$', '', url_final)
        url_limpia = re.sub(r'#.*$', '', url_limpia)
        
        log(f"   🔍 Redirigido: {url_google[:50]}... -> {url_limpia[:60]}...", 'debug')
        return url_limpia
        
    except Exception as e:
        log(f"   ⚠️ Error resolviendo redirección: {e}", 'debug')
        return None

# ✅ CORREGIDO: Google News RSS con resolución de redirecciones
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
                
                # ✅ Resolver redirección para obtener URL real
                url_real = resolver_redireccion_google_news(link)
                if not url_real:
                    continue
                
                # ✅ Obtener descripción del RSS
                descripcion = entry.get('summary', '') or entry.get('description', '')
                descripcion = re.sub(r'<[^>]+>', '', descripcion)
                descripcion = limpiar_texto(descripcion)
                
                if es_noticia_excluible(titulo, descripcion):
                    continue
                
                noticias.append({
                    'titulo': limpiar_texto(titulo),
                    'descripcion': descripcion,
                    'url': url_real,
                    'imagen': None,
                    'fuente': 'Google News',
                    'fecha': entry.get('published'),
                    'puntaje': calcular_puntaje_internacional(titulo, descripcion)
                })
        except Exception as e:
            log(f"Error en feed {feed_url}: {e}", 'debug')
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
        'ucrania|rusia|zelensky|putin': '#UcraniaRusia',
        'gaza|israel|palestina|hamas|netanyahu': '#IsraelGaza',
        'trump|biden|putin': '#PolíticaGlobal',
        'economía|mercados|inflación': '#EconomíaMundial',
        'irán|iran': '#Irán',
        'dron|drones|ia|inteligencia artificial': '#TecnologíaMilitar',
        'china|taiwan': '#ChinaTaiwán',
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
    
    if len(mensaje) > 2000:
        lineas = texto.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1600:
                texto_cortado += linea + "\n"
            else:
                break
        mensaje = f"{texto_cortado.rstrip()}\n\n[...]\n\n{hashtags}\n\n— 🌐 Verdad Hoy"
    
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
# FUNCIÓN PRINCIPAL - CORREGIDA
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🌍 BOT DE NOTICIAS INTERNACIONALES - V3.1 CORREGIDO")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    historial = cargar_historial()
    log(f"📊 Historial: {len(historial.get('urls', []))} URLs recientes (72h)")
    log(f"📊 Hashes permanentes: {len(historial.get('hashes_permanentes', []))} guardados")
    
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
    
    # Ordenar por puntaje y fecha
    todas_noticias.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    
    # ✅ CORREGIDO: Buscar noticia válida con reintentos
    noticia_seleccionada = None
    intentos = 0
    max_intentos = len(todas_noticias)
    
    while intentos < max_intentos:
        noticia = todas_noticias[intentos]
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        descripcion = noticia.get('descripcion', '')
        intentos += 1
        
        if not url or not titulo:
            continue
        
        log(f"   [{intentos}] Probando: {titulo[:50]}...", 'debug')
        
        # Verificar duplicados
        es_dup, razon = noticia_ya_publicada(historial, url, titulo, descripcion)
        if es_dup:
            log(f"      ❌ Rechazada: {razon}", 'debug')
            continue
        
        # ✅ CORREGIDO: Umbral de puntaje bajado a 3
        if noticia.get('puntaje', 0) < 3:
            log(f"      ❌ Rechazada: Puntaje bajo ({noticia.get('puntaje', 0)})", 'debug')
            continue
        
        log(f"      ✅ Aceptada: Noticia válida encontrada", 'debug')
        
        # Intentar extraer contenido
        log(f"\n📝 NOTICIA SELECCIONADA:")
        log(f"   Título: {noticia['titulo'][:60]}...")
        log(f"   Fuente: {noticia['fuente']}")
        log(f"   Puntaje: {noticia.get('puntaje', 0)}")
        
        log("🌐 Extrayendo contenido con validación estricta...")
        contenido, creditos = extraer_contenido_estricto(noticia['url'])
        
        if contenido:
            log(f"   ✅ Contenido válido: {len(contenido)} caracteres", 'exito')
            noticia_seleccionada = noticia
            break
        else:
            log("   ⚠️ Extracción falló, usando descripción de API", 'advertencia')
            contenido = noticia.get('descripcion', '')
            
            if len(contenido) >= 100:
                log(f"   ✅ Usando descripción: {len(contenido)} caracteres", 'exito')
                noticia_seleccionada = noticia
                break
            else:
                log(f"   ❌ Descripción insuficiente ({len(contenido)} chars), probando siguiente...", 'advertencia')
                # ✅ Guardar como usada para no repetir y continuar
                historial = guardar_historial(
                    historial, 
                    noticia['url'], 
                    noticia['titulo'],
                    noticia.get('descripcion', '')
                )
                continue
    
    if not noticia_seleccionada:
        log(f"ERROR: No hay noticias nuevas disponibles (revisadas {intentos} noticias)", 'error')
        log("💡 Sugerencia: Esperar a que las APIs actualicen su contenido o ampliar ventana de tiempo", 'info')
        return False
    
    # Construir publicación
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
    
    # Procesar imagen y publicar
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
        guardar_historial(
            historial, 
            noticia_seleccionada['url'], 
            noticia_seleccionada['titulo'],
            noticia_seleccionada.get('descripcion', '') + ' ' + contenido[:400]
        )
        
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
