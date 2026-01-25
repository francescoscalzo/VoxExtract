# -*- coding: utf-8 -*-
"""
Script per generare l'icona di VoxExtract.

Crea un'icona moderna con onda sonora stilizzata.
"""

from PIL import Image, ImageDraw
import os


def create_vox_extract_icon(size: int = 256) -> Image.Image:
    """
    Crea l'icona di VoxExtract.

    Args:
        size: Dimensione dell'icona in pixel

    Returns:
        Immagine PIL
    """
    # Crea immagine con sfondo trasparente
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colori del tema
    bg_color = '#1a1a2e'
    accent_color = '#4a47a3'
    highlight_color = '#00b894'
    wave_color = '#eaeaea'

    # Disegna sfondo circolare
    padding = size // 16
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=bg_color,
        outline=accent_color,
        width=size // 32
    )

    # Centro e raggio per le onde
    center_x = size // 2
    center_y = size // 2
    max_radius = size // 3

    # Disegna onde sonore concentriche
    for i, ratio in enumerate([0.4, 0.65, 0.9]):
        r = int(max_radius * ratio)
        thickness = max(2, size // 64)

        # Disegna arco sinistro
        draw.arc(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            start=120,
            end=240,
            fill=highlight_color,
            width=thickness
        )

        # Disegna arco destro
        draw.arc(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            start=-60,
            end=60,
            fill=highlight_color,
            width=thickness
        )

    # Disegna un piccolo cerchio centrale (fonte del suono)
    inner_radius = size // 12
    draw.ellipse(
        [
            center_x - inner_radius,
            center_y - inner_radius,
            center_x + inner_radius,
            center_y + inner_radius
        ],
        fill=highlight_color,
        outline=wave_color,
        width=max(1, size // 128)
    )

    # Aggiungi "V" stilizzato per "Vox"
    v_size = size // 6
    v_top = center_y - v_size // 2
    v_thickness = max(2, size // 64)

    # Linea sinistra della V
    draw.line(
        [(center_x - v_size // 2, v_top), (center_x, v_top + v_size)],
        fill=wave_color,
        width=v_thickness
    )
    # Linea destra della V
    draw.line(
        [(center_x, v_top + v_size), (center_x + v_size // 2, v_top)],
        fill=wave_color,
        width=v_thickness
    )

    return img


def main():
    """Genera l'icona in varie dimensioni e salva come .ico"""
    print("Generazione icona VoxExtract...")

    # Genera icona base ad alta risoluzione
    icon_large = create_vox_extract_icon(256)

    # Crea versioni a diverse risoluzioni
    sizes = [256, 128, 64, 48, 32, 16]

    for size in sizes:
        print(f"  Generata versione {size}x{size}")

    # Salva come file .ico
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    icon_large.save(
        icon_path,
        format='ICO',
        sizes=[(s, s) for s in sizes]
    )

    print(f"Icona salvata: {icon_path}")


if __name__ == "__main__":
    main()
