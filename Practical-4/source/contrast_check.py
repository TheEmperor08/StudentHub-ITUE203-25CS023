"""WCAG 2.1 contrast ratios for the Practical 4 colours in the light and the dark theme (standard library only).
Text needs 4.5:1; non-text parts (slider dots, focus outline) need 3:1. Colours come from assets/css/style.css.

    python Practical-4/source/contrast_check.py
"""


def blend(fg, bg, alpha):
    """Colour of fg drawn with opacity alpha over bg."""
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(alpha * x + (1 - alpha) * y):02x}" for x, y in zip(f, b))


# slide captions: rgba(11, 20, 55, 0.88) over the lightest pixel of a slide image (white) = worst case
CAPTION_BG = blend("#0b1437", "#ffffff", 0.88)

PAIRS = [
    ("Light", "Body text on page", "#334155", "#f3f4f9", 4.5),
    ("Light", "Body text on cards", "#334155", "#ffffff", 4.5),
    ("Light", "Headings / FAQ questions on cards", "#0f172a", "#ffffff", 4.5),
    ("Light", "FAQ answer text", "#334155", "#f7f8fc", 4.5),
    ("Light", "Links on cards", "#4338ca", "#ffffff", 4.5),
    ("Light", "Sample-data badge", "#8a4b00", "#fff5e1", 4.5),
    ("Light", "Slider dots (non-text)", "#4f46e5", "#ffffff", 3.0),
    ("Light", "Focus outline on page (non-text)", "#7c3aed", "#f3f4f9", 3.0),
    ("Both", "Banner text (white on indigo)", "#ffffff", "#4338ca", 4.5),
    ("Both", "Header links on navy", "#c7cbe0", "#0b1437", 4.5),
    ("Both", "Theme / Menu button text on navy", "#ffffff", "#0b1437", 4.5),
    ("Both", "Primary buttons (white on indigo)", "#ffffff", "#4f46e5", 4.5),
    ("Both", "Slide caption text (worst case)", "#ffffff", CAPTION_BG, 4.5),
    ("Both", "Footer text on navy", "#c7cbe0", "#0b1437", 4.5),
    ("Dark", "Body text on page", "#cbd5e1", "#0b1220", 4.5),
    ("Dark", "Body text on cards", "#cbd5e1", "#151d33", 4.5),
    ("Dark", "Headings / FAQ questions on cards", "#f1f5f9", "#151d33", 4.5),
    ("Dark", "FAQ answer text", "#cbd5e1", "#1b2440", 4.5),
    ("Dark", "Links on cards", "#a5b4fc", "#151d33", 4.5),
    ("Dark", "Sample-data badge", "#fcd38d", "#3a2a10", 4.5),
    ("Dark", "Slider dots (non-text)", "#a5b4fc", "#0b1220", 3.0),
    ("Dark", "Focus outline on page (non-text)", "#7c3aed", "#0b1220", 3.0),
]


def luminance(hex_colour):
    c = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


failed = 0
for theme, where, fg, bg, minimum in PAIRS:
    r = ratio(fg, bg)
    failed += r < minimum
    print(f"{'PASS' if r >= minimum else 'FAIL'}  {r:5.2f}:1 (min {minimum})  {theme:5}  {fg} on {bg}  {where}")
print(f"\n{len(PAIRS) - failed} of {len(PAIRS)} colour pairs meet their minimum ratio.")
