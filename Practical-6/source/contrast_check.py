"""WCAG 2.1 contrast ratios for the Practical 6 colours (standard library only).
Text needs 4.5:1; non-text parts (control borders, focus outline) need 3:1. Colours come from assets/css/style.css.

    python source/contrast_check.py          (run from the Practical-6 folder)
"""

PAIRS = [
    ("Body text on page", "#334155", "#f3f4f9", 4.5),
    ("Body text in the panel", "#334155", "#ffffff", 4.5),
    ("Headings, labels, table text", "#0f172a", "#ffffff", 4.5),
    ("Results summary, hints", "#475569", "#ffffff", 4.5),
    ("Placeholder text", "#64748b", "#ffffff", 4.5),
    ("Header subtitle and footer on navy", "#c7cbe0", "#0b1437", 4.5),
    ("Header title on navy", "#ffffff", "#0b1437", 4.5),
    ("Sample-data notice", "#92400e", "#fffbeb", 4.5),
    ("Tab, not selected", "#0f172a", "#e2e8f0", 4.5),
    ("Tab, hover", "#0f172a", "#d7dce8", 4.5),
    ("Tab selected / current page (white on indigo)", "#ffffff", "#4f46e5", 4.5),
    ("Retry button, hover", "#ffffff", "#4338ca", 4.5),
    ("Table header", "#0f172a", "#f7f8fc", 4.5),
    ("Sorted table header", "#0f172a", "#eef2ff", 4.5),
    ("Search highlight <mark>", "#0f172a", "#fde68a", 4.5),
    ("Loading message", "#0f172a", "#eef2ff", 4.5),
    ("Error message", "#b91c1c", "#fef2f2", 4.5),
    ("Saved-copy notice", "#92400e", "#fffbeb", 4.5),
    ("Disabled page button text", "#64748b", "#ffffff", 4.5),
    ("Control and button borders (non-text)", "#64748b", "#ffffff", 3.0),
    ("Focus outline on the panel (non-text)", "#7c3aed", "#ffffff", 3.0),
    ("Focus outline on the page (non-text)", "#7c3aed", "#f3f4f9", 3.0),
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
