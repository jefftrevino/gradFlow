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

# y-coordinate (in the master's <g> space) where add/drop + footer begin
FOOTER_Y = 3222

# Each grade's y-range in the master <g>, the transform needed to place its
# heading 20px from the top of the output canvas, and the total canvas height.
# footer_shift is the translate needed to place FOOTER_Y at (content bottom + 20px);
# None means the grade already contains the footer in its own y-range (12th).
GRADES = [
    dict(
        filename='gradFlowNinth.svg',
        y_min=276,  y_max=772,
        shift=-256,  height=760,  footer_shift=-2722,
    ),
    dict(
        filename='gradFlowTenth.svg',
        y_min=772,  y_max=1332,
        shift=-752,  height=840,  footer_shift=-2650,
    ),
    dict(
        filename='gradFlowEleventh.svg',
        y_min=1332, y_max=2082,
        shift=-1312, height=1042, footer_shift=-2460,
    ),
    dict(
        filename='GradFlowTwelfth.svg',
        y_min=2082, y_max=FOOTER_Y,
        shift=-2062, height=1440, footer_shift=None,
    ),
]


def element_y(line):
    """Return the primary y-coordinate of a single SVG element line, or None."""
    # rect, text → y="…"
    m = re.search(r'\by="(-?\d+(?:\.\d+)?)"', line)
    if m:
        return float(m.group(1))
    # line element → y1="…"
    m = re.search(r'\by1="(-?\d+(?:\.\d+)?)"', line)
    if m:
        return float(m.group(1))
    # polygon → points="x,y x,y …"
    m = re.search(r'points="([^"]+)"', line)
    if m:
        tokens = re.split(r'[,\s]+', m.group(1).strip())
        ys = [float(tokens[i]) for i in range(1, len(tokens), 2)]
        return min(ys) if ys else None
    return None


def main():
    text = SOURCE.read_text()

    # Pull out every line inside <g transform="translate(0, 90)"> … </g>
    m = re.search(
        r'<g transform="translate\(0, 90\)">(.*?)</g>',
        text, re.DOTALL
    )
    if not m:
        sys.exit('ERROR: Could not locate main <g transform="translate(0, 90)"> in source SVG.')

    g_lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]

    # Classify lines into grade buckets or the shared footer bucket
    grade_lines = [[] for _ in GRADES]
    footer_lines = []

    for line in g_lines:
        y = element_y(line)
        if y is None:
            continue
        if y >= FOOTER_Y:
            footer_lines.append(line)
        else:
            for i, grade in enumerate(GRADES):
                if grade['y_min'] <= y < grade['y_max']:
                    grade_lines[i].append(line)
                    break

    # Write each grade SVG
    for i, grade in enumerate(GRADES):
        is_twelfth = grade['footer_shift'] is None

        parts = [SVG_HEADER.format(height=grade['height'])]

        # Grade content (+ footer inlined for 12th, which owns that y-range)
        parts.append(f'<g transform="translate(0, {grade["shift"]})">')
        parts.extend(grade_lines[i])
        if is_twelfth:
            parts.extend(footer_lines)
        parts.append('</g>')

        # Shared footer block appended for 9th–11th
        if not is_twelfth:
            parts.append(f'<g transform="translate(0, {grade["footer_shift"]})">')
            parts.extend(footer_lines)
            parts.append('</g>')

        parts.append('</svg>')

        outfile = Path(grade['filename'])
        outfile.write_text('\n'.join(parts) + '\n')
        print(f'Generated {outfile}')


if __name__ == '__main__':
    main()
