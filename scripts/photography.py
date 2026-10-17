"""Find photographs for the static gallery; Pillow is used at build time to make fast, aspect-correct WebP previews.

Drop jpg/jpeg/png/webp/avif files in public/photos/ to publish them.
Optional labels in data/photography.json are matched by relative filename.
"""
from __future__ import annotations

import re
from hashlib import file_digest
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


def render_photo_variants(photo_dir: Path, output_dir: Path, photos: list[dict]) -> list[dict]:
    """Generate light WebP thumbnails and large lightbox images from originals.

    Keep the original files intact; detect real dimensions after applying camera
    EXIF orientation. The two image sizes preserve the same uncropped frame.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow is needed to generate gallery previews: pip install Pillow") from exc

    output_dir = Path(output_dir)
    photo_dir = Path(photo_dir)
    thumbs = output_dir / "photo-thumbs"
    displays = output_dir / "photo-display"
    thumbs.mkdir(parents=True, exist_ok=True)
    displays.mkdir(parents=True, exist_ok=True)
    optimized = []

    for photo in photos:
        source = photo_dir / photo["file"]
        with source.open("rb") as stream:
            digest = file_digest(stream, "sha256").hexdigest()[:20]
        thumb_path = thumbs / (digest + ".webp")
        display_path = displays / (digest + ".webp")
        try:
            with Image.open(source) as raw:
                image = ImageOps.exif_transpose(raw)
                width, height = image.size
                if not width or not height:
                    raise ValueError("invalid dimensions")
                if image.mode not in ("RGB", "RGBA"):
                    has_alpha = "A" in image.getbands() or "transparency" in image.info
                    image = image.convert("RGBA" if has_alpha else "RGB")
                # Resize in stages to avoid holding several huge originals in RAM.
                image.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
                image.save(display_path, "WEBP", quality=83, method=4)
                image.thumbnail((900, 900), Image.Resampling.LANCZOS)
                image.save(thumb_path, "WEBP", quality=76, method=4)
        except Exception as exc:
            raise ValueError(f"Could not optimize photograph {photo['file']}: {exc}") from exc

        if height > width:
            orientation = "portrait"
        elif width / height >= 1.7:
            orientation = "wide"
        elif abs(width - height) / max(width, height) < 0.08:
            orientation = "square"
        else:
            orientation = "landscape"
        optimized.append({
            **photo,
            "thumb_url": "assets/photo-thumbs/" + thumb_path.name,
            "display_url": "assets/photo-display/" + display_path.name,
            "width": width,
            "height": height,
            "orientation": orientation,
        })
    return optimized
