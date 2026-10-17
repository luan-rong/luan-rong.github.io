#!/usr/bin/env python3
"""Build a completely static, GitHub Pages-compatible academic homepage.

No pip dependencies. From the repository root:
    python scripts/build.py
    python scripts/build.py --base /my-repo/   # GitHub project Pages
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from bibliography import load_publications, safe_url
from photography import collect_photos, render_photo_variants

ROOT = Path(__file__).resolve().parent.parent


def h(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def get_json(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def href(url: str) -> str:
    return h(safe_url(url))


def external_attrs(url: str) -> str:
    return ' target="_blank" rel="noopener noreferrer"' if url.startswith(("http://", "https://")) else ""


def inline_icon(name: str) -> str:
    paths = {
        "mail": '<path d="M3 5h18v14H3z"/><path d="m3 6 9 7 9-7"/>',
        "github": '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3-.3 6.2-1.4 6.2-6.8a5.3 5.3 0 0 0-1.4-3.7 4.9 4.9 0 0 0-.1-3.7S17.7 1 16 3a13.6 13.6 0 0 0-8 0C6.3 1 4.2 1.3 4.2 1.3a4.9 4.9 0 0 0-.1 3.7 5.3 5.3 0 0 0-1.4 3.7c0 5.4 3.2 6.5 6.2 6.8A3.4 3.4 0 0 0 8 18.1V22"/>',
        "scholar": '<path d="m2 9 10-6 10 6-10 6z"/><path d="M6 12v5c2 3 10 3 12 0v-5M22 10v6"/>',
        "file": '<path d="M5 2h10l5 5v15H5z"/><path d="M15 2v5h5M9 13h7M9 17h7"/>',
        "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
        "external": '<path d="M14 4h6v6M20 4l-9 9"/><path d="M19 14v5H5V5h5"/>',
        "flower": '<path d="M12 21v-8M12 13c-6 0-9-4-8-8 6-1 9 2 9 8M12 12c0-6 3-9 8-9 1 6-2 9-8 10"/>',
        "book": '<path d="M12 5C9 3 5 3 3 4v16c3-1 7-1 9 1 2-2 6-2 9-1V4c-3-1-7-1-9 1v16"/>',
    }
    if name == "zhihu":
        return '<span class="icon-zhihu" aria-hidden="true">知</span>'
    return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' + paths.get(name, paths["external"]) + '</svg>'


def nav_header(profile: dict, base: str, active: str) -> str:
    links = [("Home", "", "home"), ("Publications", "publications/", "publications"),
             ("Peer Review", "peer-review/", "peer-review"), ("Photography", "photography/", "photography")]
    nav = "".join(
        f'<a href="{h(base + path)}" class="nav-link {"is-active" if key == active else ""}"'
        f'{" aria-current=\"page\"" if key == active else ""}>{h(label)}</a>'
        for label, path, key in links
    )
    return f'''<header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="{h(base)}" aria-label="{h(profile['name_short'])}, home">
          <span class="brand-flower">{inline_icon('flower')}</span>
          <span>{h(profile['name_short'])}</span>
        </a>
        <nav class="nav" aria-label="Main navigation">{nav}</nav>
        <a class="nav-hello" href="mailto:{h(profile['email'])}" aria-label="Say hello by email">Say hello <span aria-hidden="true">↗</span></a>
      </div>
    </header>'''


def page_footer(profile: dict, base: str) -> str:
    return f'''<footer class="site-footer"><div class="container footer-inner">
      <p><span class="footer-flower" aria-hidden="true">✳</span> Made with curiosity & soft sunlight. <span class="footer-copy">© {datetime.now().year} {h(profile['name'])}</span></p>
      <a href="#top">Back to top ↑</a>
    </div></footer>'''


def bio_html(profile: dict) -> str:
    parts = []
    for segment in profile.get("bio", []):
        text = h(segment.get("text", ""))
        url = safe_url(segment.get("url", ""))
        parts.append(f'<a href="{href(url)}"{external_attrs(url)}>{text}</a>' if url else text)
    return "".join(parts)


def socials_html(profile: dict, base: str) -> str:
    links = profile.get("social_links", [])[:]
    cv = profile.get("cv", "")
    if cv:
        if (ROOT / "public" / cv).is_file():
            links.append({"label": "CV", "url": base + cv, "icon": "file", "local": True})
        else:
            print(f"[warning] CV was set but file not found: public/{cv}", file=sys.stderr)
    elements = []
    for link in links:
        url = (base + link["url"].lstrip("/")) if link.get("local") and not link["url"].startswith(base) else link.get("url", "")
        if link.get("local"):
            url = base + cv.lstrip("/")
        if not link.get("local"):
            url = safe_url(url)
        if not url:
            continue
        elements.append(f'<a class="social-link" href="{h(url)}"{external_attrs(url)}>{inline_icon(link.get("icon", "external"))}<span>{h(link["label"])}</span></a>')
    return "".join(elements)


def paper_links(links: list[dict]) -> str:
    if not links:
        return ""
    return '<div class="paper-links">' + "".join(
        f'<a href="{href(link["url"])}"{external_attrs(link["url"])}>{h(link["label"])} <span aria-hidden="true">↗</span></a>'
        for link in links if safe_url(link.get("url", ""))
    ) + '</div>'


def paper_card(pub: dict, full: bool = False) -> str:
    category = pub["category"]
    first_link = next((safe_url(l["url"]) for l in pub["links"] if safe_url(l.get("url", ""))), "")
    title_content = f'<a href="{h(first_link)}"{external_attrs(first_link)}>{h(pub["title"])}</a>' if first_link else h(pub["title"])
    ab = f'<details class="paper-abstract"><summary>Abstract</summary><p>{h(pub["abstract"])}</p></details>' if full and pub["abstract"] else ""
    hl = f'<span class="tag tag-highlight">{h(pub["highlight"])}</span>' if pub.get("highlight") else ""
    searchable = " ".join(str(pub.get(s, "")) for s in ("title", "authors", "venue", "year", "category")).lower()
    return f'''<article class="paper-card" data-category="{h(category)}" data-search="{h(searchable)}">
      <div class="paper-card__top"><span class="paper-date">{h(pub['date_label'])}</span><span class="tag tag-{h(category.lower())}">{h(category)}</span></div>
      <h3 class="paper-title">{title_content}</h3>
      <p class="paper-authors">{h(pub['authors'])}</p>
      <p class="paper-venue">{h(pub['venue'])}</p>
      {f'<div class="paper-highlights">{hl}</div>' if hl else ''}
      {ab}
      {paper_links(pub['links'])}
    </article>'''


def home_page(profile: dict, pubs: list[dict], base: str) -> str:
    featured = [p for p in pubs if p["featured"]]
    if len(featured) < 3:
        featured.extend([p for p in pubs if p not in featured])
    featured = sorted(featured, key=lambda p: p["sort_key"], reverse=True)[:3]
    cards = "".join(paper_card(pub) for pub in featured)
    tags = "".join(f'<span>{h(tag)}</span>' for tag in profile.get("research_tags", []))
    avatar = base + profile.get("avatar", "assets/avatar-placeholder.svg").lstrip("/")
    return f'''<section class="hero container" aria-labelledby="hero-title">
      <div class="hero-scene" aria-hidden="true"><img src="{h(base)}assets/window-watercolor.webp" alt="" fetchpriority="high" />
        <div class="hero-curtain"></div><div class="hero-glow"></div>
      </div>
      <div class="hero-content">
        <div class="hero-personal">
          <img class="portrait" src="{h(avatar)}" alt="Portrait of {h(profile['name'])} — replace placeholder with your photo" width="112" height="112" />
          <p class="eyebrow">{h(profile.get('hero_eyebrow', 'HELLO THERE'))}</p>
          <h1 id="hero-title">{h(profile['name'])}<span class="heading-spark" aria-hidden="true">✳</span></h1>
          <p class="hero-role">{h(profile.get('role', 'Researcher'))}</p>
          <p class="hero-school">{h(profile.get('department', ''))}<span class="bullet"> · </span>{h(profile.get('affiliation', ''))}</p>
          <p class="hero-bio">{bio_html(profile)}</p>
          <div class="research-tags" aria-label="Research interests">{tags}</div>
          <div class="socials">{socials_html(profile, base)}</div>
        </div>
      </div>
      <p class="scene-caption"><span aria-hidden="true">☀</span> A window into my little world</p>
    </section>
    <section class="section container section-papers" aria-labelledby="featured-title">
      <div class="section-heading"><div>
        <p class="section-kicker">THOUGHTS IN PROGRESS</p>
        <h2 id="featured-title">Recent publications <span aria-hidden="true">✳</span></h2>
        <p>A selection of papers and preprints, from the newest to the oldest.</p>
      </div><a class="more-link" href="{h(base)}publications/">All publications {inline_icon('arrow')}</a></div>
      {f'<div class="paper-grid">{cards}</div>' if cards else '<p class="empty-state">Add a .bib or .ris file in data/publications/ to show papers here.</p>'}
    </section>
    <section class="container little-more" aria-label="Beyond papers">
       <div class="little-more__art" aria-hidden="true"><span class="sun-orb"></span><span class="little-leaves">✿</span></div>
       <div class="little-more__text"><p class="section-kicker">BEYOND THE DESK</p><h2>Some moments live beyond the page.</h2>
         <p>Moments, places, and the light I noticed along the way.</p>
         <a class="more-link" href="{h(base)}photography/">Visit my photography {inline_icon('arrow')}</a>
       </div>
    </section>
    <p class="home-quote">“{h(profile.get('hero_quote', 'Stay curious, and keep learning.'))}” <span aria-hidden="true">❧</span></p>'''


def subpage_banner(kicker: str, title: str, intro: str, mark: str = "✳") -> str:
    return f'''<section class="subpage-banner"><div class="container subpage-banner__inner">
      <div class="subpage-banner__copy"><p class="section-kicker">{h(kicker)}</p>
      <h1>{h(title)} <span aria-hidden="true">{h(mark)}</span></h1><p>{h(intro)}</p></div>
      <div class="banner-decoration" aria-hidden="true"><span class="banner-sun"></span><span class="banner-leaf">✳</span></div>
    </div></section>'''


def publications_page(pubs: list[dict]) -> str:
    intro = "A little archive of things I've written, explored, and learned with collaborators. Newest first."
    counts = {cat: sum(1 for p in pubs if p["category"] == cat) for cat in ("Journal", "Conference", "Preprint", "Other")}
    filters = [("All", "all"), ("Journals", "Journal"), ("Conferences", "Conference"), ("Preprints", "Preprint")]
    if counts["Other"]:
        filters.append(("Other", "Other"))
    controls = "".join(
        f'<button class="filter-chip {"is-selected" if key == "all" else ""}" type="button" data-filter="{h(key)}" aria-pressed="{str(key == "all").lower()}">{h(label)}<span>{len(pubs) if key == "all" else counts[key]}</span></button>'
        for label, key in filters
    )
    papers = "".join(paper_card(pub, full=True) for pub in pubs)
    return subpage_banner("PUBLICATIONS & PREPRINTS", "Work & writing", intro, "☼") + f'''
      <section class="container content-section" aria-labelledby="browse-title">
        <div class="browse-heading"><h2 id="browse-title">Browse the archive</h2><p>Automatically imported from BibTeX and RIS files.</p></div>
        <div class="paper-toolbar" id="publication-toolbar"><div class="filter-chips" role="group" aria-label="Publication type">{controls}</div>
          <label class="paper-search"><span class="sr-only">Search publications</span><span aria-hidden="true">⌕</span>
           <input id="paper-search" type="search" placeholder="Search title, author, venue…" autocomplete="off" /></label>
        </div>
        <p id="results-counter" class="results-counter" aria-live="polite">Showing {len(pubs)} of {len(pubs)} entries</p>
        <div class="paper-list" id="publication-list">{papers}</div>
        <p id="no-results" class="empty-state" hidden>No matching papers. Try another search or filter.</p>
      </section>'''


def service_group(label: str, items: list[dict], marker: str) -> str:
    rows = []
    for entry in items:
        name = h(entry.get("name", ""))
        link = safe_url(entry.get("url", ""))
        title = f'<a href="{href(link)}"{external_attrs(link)}>{name} ↗</a>' if link else name
        rows.append(f'''<li class="service-item"><div class="service-dot" aria-hidden="true">✳</div>
          <div><h3>{title}</h3><p>{h(entry.get('area', ''))}</p></div>
          <span class="service-years">{h(entry.get('years', ''))}</span></li>''')
    if not rows:
        rows.append('<li class="service-item service-empty">Add entries to data/reviews.json to begin.</li>')
    return f'''<section class="service-panel" aria-labelledby="{marker}-title">
      <div class="service-panel__header"><div class="service-emblem" aria-hidden="true">{marker}</div>
      <div><p class="section-kicker">ACADEMIC SERVICE</p><h2 id="{marker}-title">{h(label)}</h2></div></div>
      <ul class="service-list">{''.join(rows)}</ul></section>'''


def review_page(reviews: dict) -> str:
    banner = subpage_banner("ACADEMIC SERVICE", "Peer review", reviews.get("intro", ""), "✿")
    panels = []
    if reviews.get("conferences"):
        panels.append(service_group("Conferences", reviews["conferences"], "C"))
    if reviews.get("journals"):
        panels.append(service_group("Journals", reviews["journals"], "J"))
    layout_class = "service-layout service-layout--single" if len(panels) <= 1 else "service-layout"
    content = "".join(panels) if panels else '<p class="empty-state">No peer-review entries to display yet.</p>'
    return banner + f'<div class="container content-section"><div class="{layout_class}">{content}</div><p class="service-note">I believe thoughtful reviewing is part of building a generous research community.</p></div>'


def photography_page(settings: dict, photos: list[dict], base: str) -> str:
    """An image-first gallery: no album filters, randomized in the visitor's browser."""
    cards = []
    for photo in photos:
        original = base + photo['url']
        preview = base + photo['display_url']
        thumbnail = base + photo['thumb_url']
        cards.append(f'''<article class="photo-card photo-card--{h(photo['orientation'])}">
          <a class="photo-card__link" href="{h(original)}" data-photo-preview="{h(preview)}"
             data-photo-title="{h(photo['title'])}" data-photo-alt="{h(photo['alt'])}"
             data-photo-date="{h(photo['date_label'])}" data-photo-location="{h(photo['location'])}">
            <span class="photo-frame" style="aspect-ratio: {photo['width']} / {photo['height']}">
              <img src="{h(thumbnail)}" width="{photo['width']}" height="{photo['height']}"
                   alt="{h(photo['alt'])}" loading="lazy" decoding="async" />
              <span class="photo-zoom" aria-hidden="true">↗</span>
            </span>
          </a>
        </article>''')
    gallery_or_empty = (
        '<div class="photo-gallery" id="photo-gallery">' + ''.join(cards) + '</div>'
        if photos else '<div class="photo-empty"><span aria-hidden="true">☁</span><h3>The gallery is waiting for its first photograph.</h3>'
                       '<p>Add a JPG, PNG, WebP, or AVIF image to <code>public/photos/</code> and rebuild the site.</p></div>'
    )
    return f'''<section class="photo-hero" aria-labelledby="photo-page-title">
      <div class="container photo-hero__inner">
        <div class="photo-hero__copy">
          <p class="section-kicker">{h(settings.get('eyebrow', 'say cheese, kaccha!'))}</p>
          <h1 id="photo-page-title">{h(settings.get('title', 'Photography'))}<span aria-hidden="true"> ✳</span></h1>
          <p>{h(settings.get('intro', 'just some random snapshots as I travel around.'))}</p>
          <span class="photo-hero__signature" aria-hidden="true">light & little moments&nbsp; ↗</span>
        </div>
      </div>
    </section>
    <section class="container photography-content" aria-labelledby="photo-gallery-heading">
      <div class="photography-heading"><div>
        <h2 id="photo-gallery-heading">{h(settings.get('gallery_title', 'Through my lens'))}</h2>
        <p>{h(settings.get('gallery_note', 'capturing the moments.'))}</p></div>
        <span class="photography-heading__mark" aria-hidden="true">☼ &nbsp; ☁ &nbsp; ✿</span>
      </div>
      <div class="photo-toolbar">
        <p class="photo-counter" aria-live="polite">{len(photos)} photograph{'s' if len(photos) != 1 else ''}</p>
      </div>
      {gallery_or_empty}
      <div class="photo-endnote"><span aria-hidden="true">✿</span><p>{h(settings.get('ending_quote', 'The little things are worth remembering.'))}</p></div>
    </section>
    <dialog class="photo-lightbox" id="photo-lightbox" aria-label="Photograph viewer">
      <div class="lightbox-panel">
        <button class="lightbox-close" type="button" aria-label="Close photo">×</button>
        <button class="lightbox-arrow lightbox-prev" type="button" aria-label="Previous photograph">←</button>
        <figure class="lightbox-figure"><img id="lightbox-image" alt="" />
          <figcaption><span><strong id="lightbox-title"></strong><span id="lightbox-details"></span></span>
          <span id="lightbox-position"></span><a id="lightbox-original" href="#" target="_blank" rel="noopener noreferrer">Original ↗</a></figcaption>
        </figure>
        <button class="lightbox-arrow lightbox-next" type="button" aria-label="Next photograph">→</button>
      </div>
    </dialog>'''


def build(base: str, output: Path) -> None:
    profile = get_json("profile.json")
    reviews = get_json("reviews.json")
    photography = get_json("photography.json")
    photos = collect_photos(ROOT / "public" / "photos", photography)
    publications = load_publications(ROOT / "data" / "publications")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT / "public", output)
    photos = render_photo_variants(ROOT / "public" / "photos", output / "assets", photos)
    template = (ROOT / "templates" / "layout.html").read_text(encoding="utf-8")
    site_url = str(profile.get("site_url", "")).strip().rstrip("/")

    pages = [
        ("", "home", "Home", home_page(profile, publications, base)),
        ("publications/", "publications", "Publications", publications_page(publications)),
        ("peer-review/", "peer-review", "Peer Review", review_page(reviews)),
        ("photography/", "photography", "Photography", photography_page(photography, photos, base)),
    ]
    for path, active, title, content in pages:
        canonical = f'<link rel="canonical" href="{h(site_url + "/" + path)}" />' if site_url else ""
        replacements = {
            "{{PAGE_TITLE}}": h(f"{title} | {profile['name']}"),
            "{{META_DESCRIPTION}}": h(profile.get("site_description", "")),
            "{{BASE}}": h(base),
            "{{CANONICAL}}": canonical,
            "{{HEADER}}": nav_header(profile, base, active),
            "{{CONTENT}}": content,
            "{{FOOTER}}": page_footer(profile, base),
        }
        markup = template
        for needle, replacement in replacements.items():
            markup = markup.replace(needle, replacement)
        dest = output / path / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markup, encoding="utf-8")

    # Preserve links from the previous version's /interests/ page.
    old_path = output / "interests" / "index.html"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    redirect_url = base + "photography/"
    old_path.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0;url={h(redirect_url)}">'
        f'<link rel="canonical" href="{h(site_url + "/photography/" if site_url else redirect_url)}">'
        '<title>Photography</title></head><body>'
        f'<p>This page has moved to <a href="{h(redirect_url)}">Photography</a>.</p></body></html>',
        encoding="utf-8",
    )
    # Machine-readable output is handy for other tools and archive integrations.
    (output / "publications.json").write_text(json.dumps(publications, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / ".nojekyll").touch()
    if site_url:
        urls = "".join(f"<url><loc>{h(site_url + '/' + path)}</loc></url>" for path, _, _, _ in pages)
        (output / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>', encoding="utf-8")
        (output / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
    print(f"✓ Generated {len(pages)} pages, {len(publications)} publications and {len(photos)} photos in {output}")
    for pub in publications:
        print(f"  {pub['sort_key']} · {pub['category']:<10} · {pub['title']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="/", help="Base URL path, e.g. / or /repo-name/")
    parser.add_argument("--output", default="dist", help="Destination folder; default: dist")
    args = parser.parse_args()
    base = "/" + args.base.strip("/") + "/" if args.base.strip("/") else "/"
    if not re.fullmatch(r"/(?:[\w.-]+/)*", base) or ".." in base:
        parser.error("--base must be a URL path such as / or /repo-name/")
    output = (ROOT / args.output).resolve()
    if output == ROOT or ROOT not in output.parents:
        parser.error("--output must be a subdirectory of this repository")
    build(base, output)


if __name__ == "__main__":
    main()
