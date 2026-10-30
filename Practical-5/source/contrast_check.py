"""WCAG 2.1 contrast ratios for the Practical 5 colours (standard library only).
Text needs 4.5:1; non-text parts (input borders, focus outline) need 3:1. Colours come from assets/css/style.css.

    python Practical-5/source/contrast_check.py
"""

PAIRS = [
    ("Body text", "#334155", "#ffffff", 4.5),
    ("Headings, labels, legends", "#0f172a", "#ffffff", 4.5),
    ("Hints, intro, password rules (not met)", "#475569", "#ffffff", 4.5),
    ("Placeholder text", "#64748b", "#ffffff", 4.5),
    ("Error messages", "#b91c1c", "#ffffff", 4.5),
    ("Error summary text", "#b91c1c", "#fef2f2", 4.5),
    ("Strength: Weak", "#b91c1c", "#ffffff", 4.5),
    ("Strength: Medium", "#92400e", "#ffffff", 4.5),
    ("Strength: Strong / rules met", "#047857", "#ffffff", 4.5),
    ("Success heading", "#047857", "#ecfdf5", 4.5),
    ("Success text", "#0f172a", "#ecfdf5", 4.5),
    ("Register button (white on blue)", "#ffffff", "#2563eb", 4.5),
    ("Register button, hover", "#ffffff", "#1d4ed8", 4.5),
    ("Input text in an invalid field", "#0f172a", "#fef2f2", 4.5),
    ("CAPTCHA characters (lightest text colour, hsl(200, 60%, 25%))", "#1a4d66", "#f1f5f9", 4.5),
    ("Input border (non-text)", "#64748b", "#ffffff", 3.0),
    ("Invalid input border (non-text)", "#b91c1c", "#fef2f2", 3.0),
    ("Valid input border (non-text)", "#047857", "#ffffff", 3.0),
    ("Focus outline (non-text)", "#2563eb", "#ffffff", 3.0),
]


def luminance(hex_colour):
    c = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


failed = 0
for where, fg, bg, minimum in PAIRS:
    r = ratio(fg, bg)
    failed += r < minimum
    print(f"{'PASS' if r >= minimum else 'FAIL'}  {r:5.2f}:1 (min {minimum})  {fg} on {bg}  {where}")
print(f"\n{len(PAIRS) - failed} of {len(PAIRS)} colour pairs meet their minimum ratio.")
