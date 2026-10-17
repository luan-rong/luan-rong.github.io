"""Find photographs for the static gallery; no extra packages required.

Drop jpg/jpeg/png/webp/avif files in public/photos/ to publish them.
Optional labels in data/photography.json are matched by relative filename.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.avif'}
ALLOWED_ORIENTATIONS = {'portrait', 'landscape', 'square', 'wide'}


def parse_date(value: str) -> tuple[str, str]:
    """Return an ISO-sortable date and a human-readable date (or both empty)."""
    value = str(value or '').strip()
    for fmt, pad in (('%Y-%m-%d', ''), ('%Y-%m', '-01'), ('%Y', '-01-01')):
        try:
            day = datetime.strptime(value, fmt)
            if day.strftime(fmt) == value:
                return value + pad, day.strftime('%b %Y' if fmt != '%Y' else '%Y')
        except ValueError:
            pass
    return '', ''


def fallback_title(stem: str) -> str:
    value = re.sub(r'^\d{4}[-_]\d{2}[-_]\d{2}[-_]', '', stem)
    value = re.sub(r'[_-]+', ' ', value).strip()
    return value.title() or 'Untitled moment'


def collect_photos(photo_dir: Path, settings: dict) -> list[dict]:
    """Scan photos (also subfolders), ignoring metadata for missing files.

    Dates come from metadata or the YYYY-MM-DD- prefix of a filename; sorting
    never depends on Git checkout modification times.
    """
    if not photo_dir.is_dir():
        return []
    metadata = {
        str(item.get('file', '')).replace('\\', '/'): item
        for item in settings.get('photos', [])
        if isinstance(item, dict) and item.get('file')
    }
    files = sorted(
        (p for p in photo_dir.rglob('*')
         if p.is_file() and not p.is_symlink() and p.suffix.lower() in ALLOWED_EXTENSIONS
         and not any(part.startswith('.') for part in p.relative_to(photo_dir).parts)),
        key=lambda p: p.relative_to(photo_dir).as_posix().casefold()
    )
    result = []
    for photo in files:
        rel = photo.relative_to(photo_dir).as_posix()
        info = metadata.get(rel, {})
        from_filename = re.match(r'^(\d{4})[-_](\d{2})[-_](\d{2})[-_]', photo.name)
        guessed = '-'.join(from_filename.groups()) if from_filename else ''
        sort_date, date_label = parse_date(info.get('date', guessed))
        orientation = str(info.get('orientation', 'landscape')).lower()
        if orientation not in ALLOWED_ORIENTATIONS:
            orientation = 'landscape'
        title = str(info.get('title') or fallback_title(photo.stem))
        album = str(info.get('album') or 'Moments')
        # The demo- prefix makes AI-generated sample photographs unmistakable.
        is_demo = photo.name.lower().startswith('demo-')
        result.append({
            'file': rel,
            'url': 'photos/' + quote(rel, safe='/'),
            'title': title,
            'alt': str(info.get('alt') or title),
            'location': str(info.get('location', '')),
            'date': sort_date,
            'date_label': date_label,
            'album': album,
            'orientation': orientation,
            'demo': is_demo,
        })
    result.sort(key=lambda p: (p['date'], p['file'].casefold()), reverse=True)
    return result
