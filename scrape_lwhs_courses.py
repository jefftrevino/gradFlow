#!/usr/bin/env python3
"""Scrape the LWHS course catalog and produce lwhs_courses.json."""

import json
import re
import time
import urllib.request
from pathlib import Path

SOURCE_URL  = 'https://www.lwhs.org/academic/course-catalog'
ELEMENT_URL = 'https://www.lwhs.org/fs/elements/6532'
OUT_FILE    = Path('lwhs_courses.json')

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; lwhs-course-scraper/1.0)'}

# Category IDs discovered from the live page
DEPARTMENTS = {
    16: 'BME',
    19: 'English',
    76: 'Ethnic Studies',
    73: 'History',
    30: 'Independent Studies',
    28: 'Mathematics',
    33: 'Performing Arts',
    29: 'Science',
    31: 'Teaching Assistantships',
    34: 'Technical Arts',
    36: 'Visual Arts',
    66: 'World Languages',
}


def fetch(url, params=None):
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'{url}?{qs}'
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', errors='replace')


def clean(html):
    """Strip all HTML tags and collapse whitespace."""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).strip()


def unescape(s):
    """Decode common HTML entities."""
    return (s.replace('&amp;', '&').replace('&rsquo;', '\u2019')
             .replace('&lsquo;', '\u2018').replace('&ldquo;', '\u201c')
             .replace('&rdquo;', '\u201d').replace('&ndash;', '\u2013')
             .replace('&mdash;', '\u2014').replace('&nbsp;', ' ')
             .replace('&#39;', "'"))


def parse_popup(post_id):
    """Fetch course detail popup and return parsed fields."""
    html = fetch(ELEMENT_URL, {
        'is_popup': 'true',
        'post_id': post_id,
        'show_post': 'true',
    })

    # ── fsSummary block ────────────────────────────────────────────────────
    # Structure: <strong><em>TERM</em></strong><br />\n<em>Brief desc</em>
    summary_m = re.search(
        r'<div class="fsSummary">(.*?)</div>',
        html, re.DOTALL,
    )
    s_raw = summary_m.group(1) if summary_m else ''

    # Term: inside <strong>…</strong> (may wrap <em>)
    term_m = re.search(r'<strong[^>]*>(.*?)</strong>', s_raw, re.DOTALL)
    term = clean(term_m.group(1)) if term_m else ''

    # Brief: first <em> after the <br/>
    after_br = re.split(r'<br\s*/?>', s_raw, maxsplit=1)
    if len(after_br) > 1:
        em_m = re.search(r'<em[^>]*>(.*?)</em>', after_br[1], re.DOTALL)
        brief = unescape(clean(em_m.group(1))) if em_m else clean(after_br[1].split('<')[0])
    else:
        brief = ''

    # ── fsBody block ──────────────────────────────────────────────────────
    body_m = re.search(r'<div class="fsBody">(.*?)</div>', html, re.DOTALL)
    body_raw = body_m.group(1) if body_m else ''
    description = unescape(clean(body_raw)).strip()

    # ── prerequisites ─────────────────────────────────────────────────────
    # Look for "Prerequisites:" label anywhere in popup
    prereq_m = re.search(
        r'[Pp]rerequisites?\s*:?\s*(?:</?\w+>)?\s*(.*?)(?:<br|</p>|$)',
        html, re.DOTALL,
    )
    prerequisites = unescape(clean(prereq_m.group(1))) if prereq_m else ''

    # ── flags from article tag classes ────────────────────────────────────
    # e.g. class="... fsTag-15 fsTag-38 icon-apple"
    tag_ids = set(re.findall(r'fsTag-(\d+)', html))

    # Pull tag label text from any <li class="fsTag-N"> or visible tag spans
    tag_labels_raw = re.findall(
        r'class="[^"]*fsTag-\d+[^"]*"[^>]*>\s*<[^>]+>\s*([^<]+)', html
    )
    tag_labels = [t.strip() for t in tag_labels_raw]

    # Derive boolean flags from description / tag text
    full_text = html.lower()
    uc_approved = bool(re.search(r'uc\s+approved|uc\s+["\u201c][a-g]["\u201d]', full_text))
    honors      = bool(re.search(r'\bhonors\b', full_text))
    g_course    = bool(re.search(r'uc\s+.g.\s+elective|"g"\s+elective|\u201cg\u201d\s+elective', full_text))
    ppp         = bool(re.search(r'public purpose program|ppp requirement|\bppp\b', full_text))

    # Grade requirements from description text
    grade_reqs = []
    if re.search(r'frosh requirement|9th.grade', full_text):
        grade_reqs.append('Frosh Requirement')
    if re.search(r'junior[s/]|seniors?|11th|12th', full_text):
        grade_reqs.append('Junior/Senior')
    if re.search(r'open to all', full_text):
        grade_reqs.append('Open to All')
    grade_reqs = list(dict.fromkeys(grade_reqs))  # deduplicate preserving order

    return dict(
        term=term,
        brief_description=brief,
        description=description,
        prerequisites=prerequisites,
        uc_approved=uc_approved,
        honors=honors,
        g_course=g_course,
        ppp=ppp,
        grade_requirements=grade_reqs,
        tag_ids=sorted(tag_ids),
    )


def get_category_courses(cat_id, dept_name):
    """Return list of basic course dicts for one department."""
    courses = []
    seen_ids = set()
    start_row = 0
    prev_ids = None

    while True:
        html = fetch(ELEMENT_URL, {
            'post_category_id': cat_id,
            'start_row': start_row,
        })

        post_ids = re.findall(r'data-post-id="(\d+)"', html)
        if not post_ids or tuple(post_ids) == prev_ids:
            break
        prev_ids = tuple(post_ids)

        slugs = re.findall(r'data-slug="([^"]+)"', html)
        titles_raw = re.findall(
            r'data-slug="[^"]+"[^>]*>\s*(.*?)\s*</a>',
            html, re.DOTALL,
        )

        for j, pid in enumerate(post_ids):
            pid_int = int(pid)
            if pid_int in seen_ids:
                continue
            seen_ids.add(pid_int)
            slug  = slugs[j]  if j < len(slugs)      else ''
            title = unescape(clean(titles_raw[j])) if j < len(titles_raw) else f'Course {pid}'
            courses.append({'id': pid_int, 'title': title, 'slug': slug,
                            'department': dept_name})

        start_row += 9
        time.sleep(0.2)

    return courses


def build_tags(term, grade_reqs):
    tags = []
    if term:
        for part in re.split(r'\band\b|[;,]', term):
            t = part.strip()
            if t:
                tags.append(t)
    tags.extend(grade_reqs)
    return tags


def main():
    all_courses = []
    seen_ids = set()

    for cat_id, dept_name in DEPARTMENTS.items():
        print(f'  {dept_name} (cat {cat_id})...', flush=True)
        dept_courses = get_category_courses(cat_id, dept_name)
        print(f'    → {len(dept_courses)} courses listed', flush=True)

        for c in dept_courses:
            if c['id'] in seen_ids:
                continue
            seen_ids.add(c['id'])

            print(f'    [{c["id"]}] {c["title"]}', flush=True)
            try:
                detail = parse_popup(c['id'])
                time.sleep(0.2)
            except Exception as exc:
                print(f'      ERROR: {exc}')
                detail = dict(term='', brief_description='', description='',
                              prerequisites='', uc_approved=False, honors=False,
                              g_course=False, ppp=False, grade_requirements=[],
                              tag_ids=[])

            all_courses.append({
                'id':                c['id'],
                'title':             c['title'],
                'slug':              c['slug'],
                'department':        c['department'],
                'term':              detail['term'],
                'brief_description': detail['brief_description'],
                'description':       detail['description'],
                'prerequisites':     detail['prerequisites'],
                'uc_approved':       detail['uc_approved'],
                'honors':            detail['honors'],
                'g_course':          detail['g_course'],
                'ppp':               detail['ppp'],
                'grade_requirements': detail['grade_requirements'],
                'tags':              build_tags(detail['term'], detail['grade_requirements']),
            })

    all_courses.sort(key=lambda c: (c['department'], c['title']))

    payload = {
        'source':        SOURCE_URL,
        'total_courses': len(all_courses),
        'courses':       all_courses,
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f'\nWrote {len(all_courses)} courses → {OUT_FILE}')


if __name__ == '__main__':
    main()
