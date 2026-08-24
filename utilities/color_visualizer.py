import colorsys
from math import ceil

import matplotlib.pyplot as plt

from pymfcad.backend.color import (
    BASE_COLORS,
    OPEN_COLORS,
    TAB_COLORS,
    X11_COLORS,
    XKCD_COLORS,
)

GRID_COLS = 13
GRID_ROWS = 13


def _rgb_to_hsv(rgb):
    r, g, b = [v / 255 for v in rgb]
    return colorsys.rgb_to_hsv(r, g, b)


def _is_gray(rgb):
    return rgb[0] == rgb[1] == rgb[2]


def sort_svg_style(color_dict):
    grays = [(name, rgb) for name, rgb in color_dict.items() if _is_gray(rgb)]
    chroma = [(name, rgb) for name, rgb in color_dict.items() if not _is_gray(rgb)]

    grays.sort(key=lambda x: _rgb_to_hsv(x[1])[2])
    chroma.sort(
        key=lambda x: (_rgb_to_hsv(x[1])[0], -_rgb_to_hsv(x[1])[1], -_rgb_to_hsv(x[1])[2])
    )

    ordered = grays + chroma
    return ordered


def build_grid(items, n_cols=GRID_COLS, n_rows=None):
    if n_rows is None:
        n_rows = ceil(len(items) / n_cols)
    grid = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            idx = i * n_cols + j
            row.append(items[idx] if idx < len(items) else None)
        grid.append(row)
    return grid


def plot_grid(items, title, n_cols=GRID_COLS, n_rows=None, page=None):
    grid = build_grid(items, n_cols=n_cols, n_rows=n_rows)
    rows = len(grid)
    fig, ax = plt.subplots(figsize=(n_cols * 1.1, rows * 0.7))
    ax.axis("off")

    for i in range(rows):
        for j in range(n_cols):
            cell = grid[i][j]
            y = rows - i - 1
            if cell is None:
                rect = plt.Rectangle(
                    (j, y), 1, 1, fill=False, edgecolor="lightgray", linewidth=0.5
                )
                ax.add_patch(rect)
                continue

            name, rgb = cell
            color = tuple(v / 255 for v in rgb)
            rect = plt.Rectangle((j, y), 1, 1, color=color)
            ax.add_patch(rect)
            label = format_multiline_label(name)
            ax.text(
                j + 0.5,
                y + 0.5,
                label,
                va="center",
                ha="center",
                fontsize=8,
                color="black" if sum(rgb) > 400 else "white",
            )

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, rows)
    page_suffix = f" (page {page})" if page is not None else ""
    plt.title(f"{title}{page_suffix}")
    plt.tight_layout()
    plt.show()


def plot_grouped_columns(color_dict, title, group_by_digits=False):
    color_groups = {}
    if group_by_digits:
        for name, rgb in color_dict.items():
            base = "".join([c for c in name if not c.isdigit()])
            color_groups.setdefault(base, []).append((name, rgb))
        for group in color_groups.values():
            group.sort(
                key=lambda x: int("".join([c for c in x[0] if c.isdigit()]) or "0")
            )
    else:
        for name, rgb in color_dict.items():
            base = name.split(":", 1)[1] if ":" in name else name[0]
            color_groups.setdefault(base, []).append((name, rgb))
        for group in color_groups.values():
            group.sort()

    group_names = sorted(color_groups.keys())
    max_len = max(len(shades) for shades in color_groups.values())
    fig, ax = plt.subplots(figsize=(len(group_names) * 1.1 + 2, max_len * 0.7 + 1))
    ax.axis("off")
    for i, group in enumerate(group_names):
        shades = color_groups[group]
        for j, (name, rgb) in enumerate(shades):
            color = tuple(v / 255 for v in rgb)
            rect = plt.Rectangle((i, max_len - j - 1), 1, 1, color=color)
            ax.add_patch(rect)
            label = format_multiline_label(name)
            ax.text(
                i + 0.5,
                max_len - j - 0.5,
                label,
                va="center",
                ha="center",
                fontsize=8,
                color="black" if sum(rgb) > 400 else "white",
            )
        ax.text(
            i + 0.5,
            max_len + 0.2,
            group.capitalize(),
            va="bottom",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
    ax.set_xlim(-0.5, len(group_names))
    ax.set_ylim(0, max_len + 1)
    plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_xkcd_pages(color_dict, title, n_cols=GRID_COLS, n_rows=GRID_ROWS):
    ordered = sort_svg_style(color_dict)
    page_size = n_cols * n_rows
    total_pages = ceil(len(ordered) / page_size)

    for page in range(total_pages):
        start = page * page_size
        end = start + page_size
        plot_grid(
            ordered[start:end],
            title,
            n_cols=n_cols,
            n_rows=n_rows,
            page=page + 1,
        )


def format_multiline_label(label, max_len=14):
    if len(label) <= max_len or " " not in label:
        return label
    words = label.split()
    lines = []
    current = []
    for word in words:
        if sum(len(w) for w in current) + len(current) + len(word) <= max_len:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def plot_all_color_spaces():
    plot_grouped_columns(BASE_COLORS, "Base Colors")
    plot_grouped_columns(TAB_COLORS, "Tab Colors")
    plot_grouped_columns(OPEN_COLORS, "Open Colors", group_by_digits=True)

    plot_grid(sort_svg_style(X11_COLORS), "SVG/X11 Colors", n_cols=GRID_COLS)
    plot_xkcd_pages(XKCD_COLORS, "XKCD Colors", n_cols=GRID_COLS, n_rows=GRID_ROWS)


if __name__ == "__main__":
    plot_all_color_spaces()
