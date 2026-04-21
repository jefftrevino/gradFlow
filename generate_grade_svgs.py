#!/usr/bin/env python3
"""Generate per-grade SVG files from lwhs_course_selection.svg (single source of truth)."""

import re
import sys
from pathlib import Path

SOURCE = Path('lwhs_course_selection.svg')

SVG_HEADER = '''\
<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 1120 {height}" xmlns="http://www.w3.org/2000/svg"
     font-family="'Goudy Old Style', Georgia, serif">
<defs>
  <marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#686868"/>
  </marker>
</defs>
<rect width="1120" height="{height}" fill="#FFFFFF"/>'''

# g-coordinate where add/drop + footer begin
FOOTER_Y = 3222

# g-coordinates below this are the flex-pool preamble (the title bar and key
# live outside the g entirely and are extracted separately)
PREAMBLE_Y_MAX = 276

# y of the class-count line in the master (substituted per grade)
CLASS_COUNT_Y = 3385

# Positioning notes:
#   Preamble (title bar + key + flex pool) occupies absolute y=0–366.
#   Grade content is placed in its own <g> with content_shift = 366 − y_min,
#   so every grade heading lands at absolute y=366 right below the preamble.
#   Footer gap = 20px.  Footer height = 240px (g-y 3222–3462).  Bottom pad = 20px.
#   footer_shift satisfies: 3222 + footer_shift = (grade_abs_bottom + 20).
#   12th grade owns the footer in its own y-range so footer_shift=None.
#
#   Actual last-element g-y values used for height/footer_shift:
#     9th: 736   → abs_bottom=826  → footer@846  → h=1106
#     10th: 1304  → abs_bottom=898  → footer@918  → h=1178
#     11th: 2054  → abs_bottom=1088 → footer@1108 → h=1368
#     12th+footer: 3462 → abs_bottom=1746          → h=1766
GRADES = [
    dict(
        filename='9th/gradFlowNinth.svg',
        y_min=276,  y_max=772,
        content_shift=90,    height=1106, footer_shift=-2376,
        class_count='7 classes (8 max)',
    ),
    dict(
        filename='10th/gradFlowTenth.svg',
        y_min=772,  y_max=1332,
        content_shift=-406,  height=1178, footer_shift=-2304,
        class_count='6 classes (7 max)',
    ),
    dict(
        filename='11th/gradFlowEleventh.svg',
        y_min=1332, y_max=2082,
        content_shift=-966,  height=1368, footer_shift=-2114,
        class_count='6 classes (7 max)',
    ),
    dict(
        filename='12th/gradFlowTwelfth.svg',
        y_min=2082, y_max=FOOTER_Y,
        content_shift=-1716, height=1766, footer_shift=None,
        class_count='6 classes (7 max)',
    ),
]


def element_y(line):
    """Return the primary y-coordinate of a single SVG element line, or None."""
    m = re.search(r'\by="(-?\d+(?:\.\d+)?)"', line)
    if m:
        return float(m.group(1))
    m = re.search(r'\by1="(-?\d+(?:\.\d+)?)"', line)
    if m:
        return float(m.group(1))
    m = re.search(r'points="([^"]+)"', line)
    if m:
        tokens = re.split(r'[,\s]+', m.group(1).strip())
        ys = [float(tokens[i]) for i in range(1, len(tokens), 2)]
        return min(ys) if ys else None
    return None


def grade_footer(footer_lines, class_count):
    """Return footer_lines with the class-count line tailored to the grade."""
    result = []
    for line in footer_lines:
        if f'y="{CLASS_COUNT_Y}"' in line:
            line = re.sub(r'>Class count:.*?</text>', f'>Class count: {class_count}</text>', line)
        result.append(line)
    return result


def main():
    text = SOURCE.read_text()

    # --- Outer elements: title bar + key (between background rect and main <g>) ---
    outer_match = re.search(
        r'<rect width="1120" height="\d+" fill="#FFFFFF"/>(.*?)<g transform="translate\(0, 90\)">',
        text, re.DOTALL
    )
    if not outer_match:
        sys.exit('ERROR: Could not locate outer elements (title/key) in source SVG.')
    outer_lines = [l.strip() for l in outer_match.group(1).splitlines() if l.strip()]

    # --- All lines inside <g transform="translate(0, 90)"> ---
    g_match = re.search(
        r'<g transform="translate\(0, 90\)">(.*?)</g>',
        text, re.DOTALL
    )
    if not g_match:
        sys.exit('ERROR: Could not locate main <g transform="translate(0, 90)"> in source SVG.')
    g_lines = [l.strip() for l in g_match.group(1).splitlines() if l.strip()]

    # --- Classify g-lines into preamble (flex pool), grade buckets, or footer ---
    preamble_lines = []
    grade_lines = [[] for _ in GRADES]
    footer_lines = []

    for line in g_lines:
        y = element_y(line)
        if y is None:
            continue
        if y >= FOOTER_Y:
            footer_lines.append(line)
        elif y < PREAMBLE_Y_MAX:
            preamble_lines.append(line)
        else:
            for i, grade in enumerate(GRADES):
                if grade['y_min'] <= y < grade['y_max']:
                    grade_lines[i].append(line)
                    break

    # --- Write each grade SVG ---
    for i, grade in enumerate(GRADES):
        is_twelfth = grade['footer_shift'] is None
        footer = grade_footer(footer_lines, grade['class_count'])

        parts = [SVG_HEADER.format(height=grade['height'])]

        # Title bar + key (absolute coordinates, no transform needed).
        # Per-grade files describe one year, not four.
        parts.extend(
            l.replace('4-Year Course Selection Guide', 'Course Selection Guide')
            for l in outer_lines
        )

        # Flex-pool preamble, kept at its natural position
        parts.append('<g transform="translate(0, 90)">')
        parts.extend(preamble_lines)
        parts.append('</g>')

        # Grade content shifted so its heading lands at absolute y=366 (right
        # below the preamble), regardless of where it sat in the master
        parts.append(f'<g transform="translate(0, {grade["content_shift"]})">')
        parts.extend(grade_lines[i])
        if is_twelfth:
            parts.extend(footer)
        parts.append('</g>')

        # Footer in its own shifted g for 9th–11th
        if not is_twelfth:
            parts.append(f'<g transform="translate(0, {grade["footer_shift"]})">')
            parts.extend(footer)
            parts.append('</g>')

        parts.append('</svg>')

        outfile = Path(grade['filename'])
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_text('\n'.join(parts) + '\n')
        print(f'Generated {outfile}')


if __name__ == '__main__':
    main()
