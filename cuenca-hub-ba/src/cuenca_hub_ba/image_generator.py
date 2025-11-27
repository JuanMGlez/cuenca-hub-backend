"""Generador de imágenes diagnósticas para Sentinel-2"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as mpatches
import io

def generar_imagen_diagnostica_hd(bands, timestamp_suffix=""):
    """Genera imagen de diagnóstico científico de alto valor"""
    
    # RGB Real con corrección de brillo agresiva
    rgb = np.dstack((bands['B4_Red'], bands['B3_Green'], bands['B2_Blue']))
    # Estiramiento de histograma + ganancia alta
    rgb = np.clip(rgb * 4.5, 0, 1)
    # Corrección Gamma para realzar detalles
    rgb = np.power(rgb, 0.7)
    
    # NDCI (Clorofila)
    ndci = (bands['B5_RedEdge'] - bands['B4_Red']) / (bands['B5_RedEdge'] + bands['B4_Red'])
    
    # FAI (Lirio)
    fai = bands['B8_NIR'] - (bands['B4_Red'] + (bands['B11_SWIR'] - bands['B4_Red']) * 0.5)
    
    # NDTI (Turbidez)
    ndti = (bands['B4_Red'] - bands['B3_Green']) / (bands['B4_Red'] + bands['B3_Green'])
    
    # Máscara de agua
    mndwi = (bands['B3_Green'] - bands['B11_SWIR']) / (bands['B3_Green'] + bands['B11_SWIR'])
    water_mask = (mndwi > 0.0)
    
    # Aplicar máscara
    rgb[~water_mask] = 0
    ndci[~water_mask] = np.nan
    fai[~water_mask] = np.nan
    ndti[~water_mask] = np.nan
    
    # Crear figura con layout científico
    fig = plt.figure(figsize=(20, 14), facecolor='white')
    
    # Grid 2x2 con espacio para título y metadata
    gs = fig.add_gridspec(3, 2, height_ratios=[0.5, 4, 4], hspace=0.3, wspace=0.25,
                          left=0.08, right=0.92, top=0.93, bottom=0.05)
    
    # Título principal
    fig.suptitle('ANÁLISIS MULTISPECTRAL SENTINEL-2\nCuenca Lerma-Chapala-Santiago',
                 fontsize=18, fontweight='bold', y=0.98)
    
    # Panel 1: RGB True Color
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.imshow(rgb)
    ax1.set_title('A) Imagen RGB True Color', fontsize=14, fontweight='bold', loc='left', pad=10)
    ax1.text(0.02, 0.98, 'Bandas: R(665nm), G(560nm), B(490nm)\nResolución: 10m',
             transform=ax1.transAxes, fontsize=9, va='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax1.axis('off')
    
    # Panel 2: NDCI (Eutrofización)
    ax2 = fig.add_subplot(gs[1, 1])
    cmap_ndci = plt.get_cmap('RdYlGn_r')
    cmap_ndci.set_bad(color='#f0f0f0')
    # Ajuste de rango para mejor contraste
    im_ndci = ax2.imshow(ndci, cmap=cmap_ndci, vmin=-0.05, vmax=0.25)
    ax2.set_title('B) Índice de Clorofila (NDCI)', fontsize=14, fontweight='bold', loc='left', pad=10)
    ax2.text(0.02, 0.98, 'NDCI = (RE - R) / (RE + R)\nReferencia: Mishra & Mishra (2012)',
             transform=ax2.transAxes, fontsize=9, va='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax2.axis('off')
    cbar2 = plt.colorbar(im_ndci, ax=ax2, fraction=0.046, pad=0.04)
    cbar2.set_label('Concentración Relativa', fontsize=10)
    cbar2.ax.tick_params(labelsize=9)
    
    # Panel 3: FAI (Lirio Acuático) - Alto contraste para detección
    ax3 = fig.add_subplot(gs[2, 0])
    # Fondo negro para resaltar lirio
    ax3.set_facecolor('black')
    # Colormap neón para máximo contraste
    cmap_fai = LinearSegmentedColormap.from_list('LirioAlert', 
                                                   [(0, '#000000'), (0.3, '#1a1a1a'), 
                                                    (0.5, '#00ff00'), (1, '#ffff00')])
    cmap_fai.set_bad(color='black')
    # Rango ajustado para detectar lirio
    im_fai = ax3.imshow(fai, cmap=cmap_fai, vmin=-0.01, vmax=0.08)
    ax3.set_title('C) Índice de Vegetación Flotante (FAI)', fontsize=14, fontweight='bold', loc='left', pad=10)
    ax3.text(0.02, 0.98, 'FAI = NIR - [R + (SWIR - R) × 0.5]\nReferencia: Hu (2009)\n⚠️ Verde/Amarillo = Lirio Acuático',
             transform=ax3.transAxes, fontsize=9, va='top', color='white',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.8, edgecolor='lime'))
    ax3.axis('off')
    cbar3 = plt.colorbar(im_fai, ax=ax3, fraction=0.046, pad=0.04)
    cbar3.set_label('Densidad de Macrófitas', fontsize=10)
    cbar3.ax.tick_params(labelsize=9)
    
    # Panel 4: NDTI (Turbidez) - Rango ajustado para Lerma
    ax4 = fig.add_subplot(gs[2, 1])
    cmap_ndti = plt.get_cmap('YlOrBr')
    cmap_ndti.set_bad(color='#f0f0f0')
    # Rango optimizado para sedimentos del Río Lerma
    ndti_p5 = np.nanpercentile(ndti, 5)
    ndti_p95 = np.nanpercentile(ndti, 95)
    im_ndti = ax4.imshow(ndti, cmap=cmap_ndti, vmin=ndti_p5, vmax=ndti_p95)
    ax4.set_title('D) Índice de Turbidez (NDTI)', fontsize=14, fontweight='bold', loc='left', pad=10)
    ax4.text(0.02, 0.98, 'NDTI = (R - G) / (R + G)\nReferencia: Lacaux et al. (2007)',
             transform=ax4.transAxes, fontsize=9, va='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax4.axis('off')
    cbar4 = plt.colorbar(im_ndti, ax=ax4, fraction=0.046, pad=0.04)
    cbar4.set_label('Sólidos Suspendidos', fontsize=10)
    cbar4.ax.tick_params(labelsize=9)
    
    # Metadata footer
    from datetime import datetime
    footer_text = f'Procesamiento: Level-2A Surface Reflectance | Sensor: Sentinel-2 MSI | Generado: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}'
    fig.text(0.5, 0.01, footer_text, ha='center', fontsize=9, style='italic', color='gray')
    
    # Guardar en memoria
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_data = buffer.getvalue()
    buffer.close()
    plt.close()
    
    return image_data