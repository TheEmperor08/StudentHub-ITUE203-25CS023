"""WCAG 2.1 contrast ratios for the colour pairs used in the Practical 3 pages (Python standard library only).
Text needs at least 4.5:1 (3:1 for large text, 24px+ or 18.66px+ bold); borders of form controls and the
focus outline need 3:1 against their background (WCAG 1.4.11). Colours are taken from assets/css/*.css and
from Bootstrap 5.3.3's defaults where the custom CSS does not override them.

    python Practical-3/source/contrast_check.py
"""

PAIRS = [
    # (where it is used, foreground, background, minimum ratio)
    ("Body text on page background", "#334155", "#f3f4f9", 4.5),
    ("Body text on cards", "#334155", "#ffffff", 4.5),
    ("Headings on page background", "#0f172a", "#f3f4f9", 4.5),
    ("Muted text (lead, labels, captions) on page background", "#5b6478", "#f3f4f9", 4.5),
    ("Muted text on cards", "#5b6478", "#ffffff", 4.5),
    ("Links on cards", "#4338ca", "#ffffff", 4.5),
    ("Links on page background", "#4338ca", "#f3f4f9", 4.5),
    ("Navigation links on navy header", "#c7cbe0", "#0b1437", 4.5),
    ("Navigation link hover on navy", "#ffffff", "#121d4a", 4.5),
    ("Current page link (white on indigo)", "#ffffff", "#4f46e5", 4.5),
    ("Primary button text (white on indigo)", "#ffffff", "#4f46e5", 4.5),
    ("Hero text on gradient start (indigo)", "#ffffff", "#4f46e5", 4.5),
    ("Hero text on gradient end (violet)", "#ffffff", "#7c3aed", 4.5),
    ("Hero light button text", "#4338ca", "#ffffff", 4.5),
    ("Alerts panel text (white on navy)", "#ffffff", "#0b1437", 4.5),
    ("Sample-data badge / static-form note", "#8a4b00", "#fff5e1", 4.5),
    ("Chips and event dates", "#4338ca", "#eef0ff", 4.5),
    ("Table header text", "#0f172a", "#eef0ff", 4.5),
    ("Footer text on navy", "#c7cbe0", "#0b1437", 4.5),
    ("Footer links on navy", "#ffffff", "#0b1437", 4.5),
    ("Bootstrap pages: secondary text on page background", "#5b6478", "#f3f4f9", 4.5),
    ("Bootstrap pages: 'Forgot your password?' (text-primary) on card", "#4f46e5", "#ffffff", 4.5),
    ("Bootstrap pages: outline-secondary button text", "#6c757d", "#ffffff", 4.5),
    ("Login card header text on gradient end (violet)", "#ffffff", "#7c3aed", 4.5),
    ("Form control border on white (non-text, 3:1)", "#8a93ab", "#ffffff", 3.0),
    ("Focus outline (violet) on page background (non-text, 3:1)", "#7c3aed", "#f3f4f9", 3.0),
    ("Focus outline (violet) on cards (non-text, 3:1)", "#7c3aed", "#ffffff", 3.0),
]


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(fg, bg):
    lighter, darker = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


failed = 0
for where, fg, bg, minimum in PAIRS:
    r = ratio(fg, bg)
    ok = r >= minimum
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {r:5.2f}:1 (min {minimum}:1)  {fg} on {bg}  {where}")
print(f"\n{len(PAIRS) - failed} of {len(PAIRS)} colour pairs meet their minimum ratio.")
