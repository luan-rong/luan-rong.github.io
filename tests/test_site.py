"""Run with python -m unittest discover -s tests -v"""
import json
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bibliography import clean_tex, load_publications, normalize_entry, parse_bibtex, parse_ris, safe_url
from build import build
from photography import collect_photos, parse_date, fallback_title


class BibtexTests(unittest.TestCase):
    def test_nested_braces_quoted_macros_and_concatenation(self):
        txt = r'''
        @string{conf = "Proceedings of " # {the Neat Conference}}
        @inproceedings{entry1,
          title={How {AI} Can Be Gentle: {A} Study},
          author={Doe, Jane and {Zhang Wei}},
          booktitle=conf,
          year=2026, month=sep,
          abstract="Nested {braces} and commas, okay.",
          code={https://github.com/somewhere/example}
        }
        '''
        items = parse_bibtex(txt)
        self.assertEqual(len(items), 1)
        p = normalize_entry(items[0])
        self.assertEqual(p['title'], 'How AI Can Be Gentle: A Study')
        self.assertEqual(p['authors'], 'Jane Doe, Zhang Wei')
        self.assertEqual(p['venue'], 'Proceedings of the Neat Conference')
        self.assertEqual(p['sort_key'], '2026-09-00')
        self.assertEqual(p['category'], 'Conference')
        self.assertTrue(any(x['label'] == 'Code' for x in p['links']))

    def test_arxiv_classification(self):
        src = '@misc{pre, title={A Gentle Arxiv Paper}, author={Y, X}, year={2026}, month={1}, eprint={2601.12345}, archivePrefix={arXiv}}'
        item = normalize_entry(parse_bibtex(src)[0])
        self.assertEqual(item['category'], 'Preprint')
        self.assertEqual(item['url'], 'https://arxiv.org/abs/2601.12345')
        self.assertEqual(item['links'][0]['label'], 'arXiv')

    def test_ris_continuations(self):
        txt = '''TY  - JOUR
TI  - An Example Title
  with a second line
AU  - Doe, Jane
AU  - Zhang, Wei
DA  - 2025/05/12
JO  - Example Journal
DO  - 10.9999/example
ER  -
'''
        r = normalize_entry(parse_ris(txt)[0])
        self.assertEqual(r['title'], 'An Example Title with a second line')
        self.assertEqual(r['authors'], 'Jane Doe, Wei Zhang')
        self.assertEqual(r['sort_key'], '2025-05-12')
        self.assertEqual(r['category'], 'Journal')
        self.assertTrue(r['url'].startswith('https://doi.org/'))

    def test_duplicate_preprint_and_published_record(self):
        with TemporaryDirectory() as temp:
            Path(temp, '1.bib').write_text('@misc{x,title={Same Great Idea},author={Doe, Jane},year={2024},eprint={2401.12345},archivePrefix={arXiv}}')
            Path(temp, '2.bib').write_text('@article{y,title={Same Great Idea},author={Doe, Jane},journal={Research Journal},year={2025}}')
            pubs = load_publications(Path(temp))
        self.assertEqual(len(pubs), 1)
        self.assertEqual(pubs[0]['category'], 'Journal')

    def test_publications_are_sorted_and_not_demo(self):
        pubs = load_publications(ROOT / 'data/publications')
        self.assertTrue(all('demo' not in p['id'].lower() for p in pubs))
        self.assertEqual([p['sort_key'] for p in pubs], sorted([p['sort_key'] for p in pubs], reverse=True))

    def test_url_safety_and_title_escaping(self):
        self.assertEqual(safe_url('javascript:alert(1)'), '')
        self.assertEqual(safe_url('https://example.edu/test'), 'https://example.edu/test')
        self.assertEqual(clean_tex('Nested {brace} groups'), 'Nested brace groups')


class BuildTests(unittest.TestCase):
    def test_root_and_project_base(self):
        path = ROOT / 'dist-test-only'
        try:
            build('/some-repository/', path)
            main = (path / 'index.html').read_text()
            sub = (path / 'publications/index.html').read_text()
            self.assertIn('href="/some-repository/assets/site.css"', main)
            self.assertIn('href="/some-repository/publications/"', main)
            self.assertIn('href="/some-repository/"', sub)
            self.assertIn('id="publication-list"', sub)
            self.assertEqual(len(json.loads((path / 'publications.json').read_text())),
                             len(load_publications(ROOT / 'data/publications')))
            self.assertTrue((path / 'assets/window-watercolor.webp').exists())
            self.assertTrue((path / 'peer-review/index.html').exists())
            self.assertTrue((path / 'photography/index.html').exists())
            gallery_html = (path / 'photography/index.html').read_text(encoding='utf-8')
            self.assertIn('id="photo-gallery"', gallery_html)
            self.assertIn('id="photo-lightbox"', gallery_html)
            self.assertIn('href="/some-repository/photography/"', main)
            self.assertEqual(gallery_html.count('class="photo-card photo-card--'), 8)
            self.assertNotIn('Links worth keeping', gallery_html)
            self.assertNotIn('Beyond the papers', gallery_html)
            self.assertTrue((path / 'photos/demo-01-aegean-evening.webp').exists())
            # Legacy deep links should lead to the new photography page.
            old_html = (path / 'interests/index.html').read_text()
            self.assertIn('/some-repository/photography/', old_html)
        finally:
            if path.exists():
                shutil.rmtree(path)


class PhotographyTests(unittest.TestCase):
    def test_date_parsing_and_filename_fallback(self):
        self.assertEqual(parse_date('2026-07-12'), ('2026-07-12', 'Jul 2026'))
        self.assertEqual(parse_date('2025-02'), ('2025-02-01', 'Feb 2025'))
        self.assertEqual(parse_date('2025'), ('2025-01-01', '2025'))
        self.assertEqual(parse_date('2025-02-30'), ('', ''))
        self.assertEqual(fallback_title('2026-05-12-blue-hour'), 'Blue Hour')

    def test_new_photos_detected_without_metadata_and_ordered(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / '2026-05-02-autumn-light.jpg').write_bytes(b'mock')
            (folder / '2025-04-18-sunset.webp').write_bytes(b'mock')
            (folder / '2026-05-04-blue-sky.png').write_bytes(b'mock')
            (folder / 'readme.txt').write_text('not a photo')
            photos = collect_photos(folder, {'photos': []})
        self.assertEqual(len(photos), 3)
        self.assertEqual(photos[0]['title'], 'Blue Sky')
        self.assertEqual(photos[0]['album'], 'Moments')
        self.assertEqual(photos[0]['date'], '2026-05-04')
        self.assertEqual(photos[-1]['title'], 'Sunset')

    def test_metadata_overrides_and_safe_url(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'space image.webp').write_bytes(b'mock')
            photos = collect_photos(folder, {'photos': [{
                'file': 'space image.webp', 'title': '<Moon>', 'date': '2024-01',
                'location': 'Hong Kong', 'album': 'City', 'orientation': 'portrait',
            }]})
        self.assertEqual(photos[0]['url'], 'photos/space%20image.webp')
        self.assertEqual(photos[0]['title'], '<Moon>')
        self.assertEqual(photos[0]['album'], 'City')
        self.assertEqual(photos[0]['orientation'], 'portrait')



if __name__ == '__main__':
    unittest.main()
