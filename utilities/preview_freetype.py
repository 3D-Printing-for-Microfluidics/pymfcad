"""
This script uses FreeType to load a TrueType font and extract the outline of a glyph character.
It then plots the outline using Matplotlib.
It requires the `freetype-py` and `matplotlib` libraries.
"""

import freetype
import matplotlib.pyplot as plt
import numpy as np


def glyph_to_polygons(face, char, scale=1.0):
    """
    Convert a glyph to a list of polygons (as numpy arrays) representing its outline.

    Parameters:
    - face: freetype.Face object for the font.
    - char: Character to convert to polygons.
    - scale: Scale factor to apply to the coordinates.

    Returns:
    - polys: List of polygons, each represented as a numpy array of shape (N, 2).
    """
    face.load_char(char, freetype.FT_LOAD_NO_BITMAP)
    outline = face.glyph.outline
    points = np.array(outline.points, dtype=np.float32) * scale
    contours = outline.contours

    polys = []
    start = 0
    for end in contours:
        contour = points[start : end + 1]
        if len(contour) >= 3:
            polys.append(contour)
        start = end + 1
    return polys


def plot_glyph(char, font_path="Arial.ttf", scale=1.0 / 64.0):
    """
    Plot the outline of a glyph character using FreeType and Matplotlib.
    Parameters:
    - char: Character to plot.
    - font_path: Path to the TrueType font file.
    - scale: Scale factor for the glyph coordinates.
    """

    face = freetype.Face(font_path)
    face.set_char_size(64 * 100)  # font size in 1/64 pt

    loops = glyph_to_polygons(face, char, scale=scale)

    fig, ax = plt.subplots()
    for loop in loops:
        loop = np.array(loop)
        x, y = loop[:, 0], loop[:, 1]
        # Close the loop
        x = np.append(x, x[0])
        y = np.append(y, y[0])
        ax.plot(x, y, linewidth=2)

    ax.set_aspect("equal")
    ax.set_title(f"Glyph outline for '{char}'")
    ax.invert_yaxis()  # match FreeType’s Y-up coordinate system
    plt.show()


# Example usage
plot_glyph("B", font_path="pymfd/backend/fonts/arial.ttf")
