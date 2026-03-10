#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Noticias para Facebook - Versión Corregida
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
import base64
import html as html_module  # ← NUEVO: Para limpiar entidades HTML
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote

# ... (configuración igual) ...

def limpiar_texto(texto):
    """Limpia texto de HTML y espacios extras - CORREGIDO"""
    if not texto:
        return ""
    # Decodificar entidades HTML primero (&nbsp; → espacio, &quot; → ", etc.)
    texto = html_module.unescape(texto)  # ← NUEVO
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def extraer_imagen_rss(entry, es_google_news=False):
    """
    Extrae imagen de una entrada RSS - CORREGIDO
    Ignora imágenes de Google News (logos genéricos)
    """
    # Si es Google News, NO usar la imagen del feed (es el logo genérico)
    if es_google_news:
        return None  # ← CORREGIDO: Forzar búsqueda en el artículo original
    
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url', '')
            # Verificar que no sea logo de Google News
            if url and 'google' not in url.lower() and 'gstatic' not in url.lower():
                return url
    
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            url = enc.get('href', '')
            if url and 'google' not in url.lower():
                return url
    
    # Buscar imagen en el contenido HTML
    if hasattr(entry, 'content'):
        for content in entry.content:
            if 'value' in content:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content['value'])
                if img_match:
                    url = img_match.group(1)
                    if 'google' not in url.lower():
                        return url
    
    # Buscar en summary/description
    summary = entry.get('summary', '')
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
    if img_match:
        url = img_match.group(1)
        if 'google' not in url.lower():
            return url
    
    return None

def procesar_feed_rss(feed_url, es_google_news=False):
    """Procesa un feed RSS individual - CORREGIDO"""
    noticias = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        timeout = 20 if es_google_news else 15
        feed = feedparser.parse(feed_url, request_headers=headers)
        
        fuente = feed.feed.get('title', feed_url.split('/')[2])
        entries = feed.entries[:5] if es_google_news else feed.entries[:3]
        
        for entry in entries:
            titulo = entry.get('title', '')
            if not titulo or len(titulo) < 10 or '[Removed]' in titulo:
                continue
            
            # Limpiar título de entidades HTML
            titulo = html_module.unescape(titulo)  # ← NUEVO
            
            if es_google_news and ' - ' in titulo:
                titulo = titulo.rsplit(' - ', 1)[0]
            
            descripcion = limpiar_texto(entry.get('summary', entry.get('description', '')))
            link = entry.get('link', '')
            
            if es_google_news and 'news.google.com' in link:
                link = limpiar_link_google_news(link)
                fuente_limpia = 'Google News'
            else:
                fuente_limpia = fuente
            
            # ← CORREGIDO: Pasar es_google_news para ignorar imágenes genéricas
            imagen = extraer_imagen_rss(entry, es_google_news=es_google_news)
            
            puntaje_base = calcular_puntaje(titulo, descripcion)
            puntaje_bonus = 2 if es_google_news else 0
            
            noticias.append({
                'titulo': titulo,
                'descripcion': descripcion,
                'url': link,
                'imagen': imagen,  # Será None para Google News, se buscará después
                'fuente': fuente_limpia,
                'puntaje': puntaje_base + puntaje_bonus,
                'es_google_news': es_google_news
            })
            
    except Exception as e:
        tipo = "Google News" if es_google_news else "RSS"
        log(f"Error {tipo}: {str(e)[:50]}", 'advertencia')
    
    return noticias

def extraer_imagen_de_articulo(url):
    """
    Extrae imagen del artículo original - MEJORADO
    Prioriza imágenes reales, ignora logos e iconos
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # 1. Meta tag og:image (más confiable)
        og_image = soup.find('meta', property='og:image')
        if og_image:
            img_url = og_image.get('content', '')
            # Filtrar logos e iconos comunes
            if img_url and not any(x in img_url.lower() for x in [
                'logo', 'icon', 'favicon', 'google', 'gstatic', 
                'avatar', 'profile', 'user'
            ]):
                # Verificar que no sea imagen pequeña (icono)
                if not any(img_url.endswith(ext) for ext in ['.ico', '.svg']):
                    return img_url
        
        # 2. Meta tag twitter:image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image:
            img_url = twitter_image.get('content', '')
            if img_url and not any(x in img_url.lower() for x in ['logo', 'icon', 'google']):
                return img_url
        
        # 3. Imagen principal del artículo (con filtros)
        img_selectores = [
            'article img',
            '.article-body img',
            '.entry-content img',
            'main img',
            '.content img',
            'figure img',
            '.post-thumbnail img'
        ]
        
        for selector in img_selectores:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src', '')
                # Filtrar imágenes pequeñas o de logos
                width = img.get('width', '')
                if width and int(width) < 200:
                    continue
                
                # Filtrar por nombre de archivo
                if any(x in src.lower() for x in ['logo', 'icon', 'avatar', 'user', 'google']):
                    continue
                
                # Asegurar URL completa
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    parsed = urlparse(url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                
                # Verificar que sea URL válida
                if src.startswith('http'):
                    return src
        
        # 4. Primera imagen grande de la página (último recurso)
        for img in soup.find_all('img'):
            src = img.get('src', '')
            width = img.get('width', '')
            # Solo imágenes grandes (probablemente contenido, no iconos)
            if width and int(width) >= 400:
                if not any(x in src.lower() for x in ['logo', 'icon', 'google']):
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        parsed = urlparse(url)
                        src = f"{parsed.scheme}://{parsed.netloc}{src}"
                    return src
        
        return None
        
    except Exception as e:
        log(f"Error extrayendo imagen: {str(e)[:50]}", 'advertencia')
        return None

def generar_texto_publicacion(noticia):
    """Genera el texto para publicar en Facebook - CORREGIDO"""
    titulo = html_module.unescape(noticia['titulo'])  # ← NUEVO
    descripcion = noticia['descripcion']
    fuente = noticia['fuente']
    
    contenido = extraer_contenido_web(noticia['url'])
    if not contenido:
        contenido = descripcion
    
    # Limpiar entidades HTML del contenido extraído
    contenido = html_module.unescape(contenido)  # ← NUEVO
    contenido = re.sub(r'\s+', ' ', contenido).strip()
    
    # ... (resto igual) ...

def main():
    """Función principal - CORREGIDA"""
    # ... (inicio igual) ...
    
    # Obtener imagen (múltiples intentos) - CORREGIDO
    log("Procesando imagen...")
    imagen_path = None
    
    # Intento 1: Imagen del feed RSS/NewsData/NewsAPI (solo si no es Google News)
    if noticia.get('imagen') and not noticia.get('es_google_news'):
        log(f"Intentando imagen del feed...", 'debug')
        imagen_path = descargar_imagen(noticia['imagen'])
        if imagen_path:
            log("Imagen del feed usada", 'exito')
    
    # Intento 2: Extraer del artículo original (PRINCIPAL para Google News)
    if not imagen_path:
        log("Extrayendo imagen del artículo original...", 'debug')
        img_url = extraer_imagen_de_articulo(noticia['url'])
        if img_url:
            log(f"Imagen encontrada: {img_url[:60]}...", 'debug')
            imagen_path = descargar_imagen(img_url)
            if imagen_path:
                log("Imagen del artículo descargada", 'exito')
    
    # ... (resto igual) ...
