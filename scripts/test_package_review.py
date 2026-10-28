import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from package_review import build, STAGES, PAGES
from evidence import sources, artifacts

class ReviewPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'output'
        self.output.mkdir()
        (self.root / 'docs').mkdir()
        (self.root / 'docs/MENTOR_REVIEW.md').write_text('walkthrough')
        self.status = dict(status='passed_local_database_pending', database_verified=False,
                           stages=[dict(name=n, status='passed', returncode=0) for n in STAGES], pages=PAGES)
        for name in ['index.html', 'release_candidate.html', 'test_summary.json', 'data_quality.json', *PAGES]:
            path = self.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')
        self.save()
    def save(self):
        self.status['provenance'] = dict(version=1, sources=sources(self.root), artifacts=artifacts(self.root))
        (self.output / 'candidate_status.json').write_text(json.dumps(self.status))
    def test_inventory_and_repeatability(self):
        (self.output / 'release_generate.txt').write_text('excluded process log')
        first = build(self.root).read_bytes()
        self.assertEqual(first, build(self.root).read_bytes())
        with zipfile.ZipFile(build(self.root)) as archive:
            self.assertNotIn('output/release_generate.txt', archive.namelist())
            manifest = json.loads(archive.read('review_manifest.json'))
            for name, row in manifest['files'].items():
                self.assertEqual(row['sha256'], hashlib.sha256(archive.read(name)).hexdigest())
            self.assertFalse(manifest['candidate_status']['database_verified'])
    def test_broken_link_rejected(self):
        (self.output / 'index.html').write_text('<a href="missing.html">missing</a>')
        self.save()
        with self.assertRaisesRegex(ValueError, 'Broken offline link'): build(self.root)
    def test_local_links_with_fragments(self):
        (self.output / 'index.html').write_text('<a href="m2/dashboard.html?x=1#table">valid</a>')
        path = self.output / 'm2/dashboard.html'
        path.parent.mkdir(exist_ok=True)
        path.write_text('<a href="../index.html">back</a>')
        self.save()
        build(self.root)
    def test_failed_stage_rejected(self):
        self.status['stages'][2]['returncode'] = 1
        self.save()
        with self.assertRaises(ValueError): build(self.root)
    def test_missing_page_rejected(self):
        (self.output / PAGES[2]).unlink()
        with self.assertRaises(ValueError): build(self.root)
    def test_false_database_claim_rejected(self):
        self.status['database_verified'] = True
        self.save()
        with self.assertRaises(ValueError): build(self.root)
    def test_symlink_rejected(self):
        path = self.output / PAGES[2]
        path.unlink()
        path.symlink_to(self.root / 'docs/MENTOR_REVIEW.md')
        with self.assertRaises(ValueError): build(self.root)

    def test_changed_output_rejected_even_with_successful_status(self):
        (self.output / PAGES[2]).write_text('altered result')
        with self.assertRaisesRegex(ValueError, 'artifacts changed'): build(self.root)

    def test_changed_or_added_source_rejected(self):
        (self.root / 'docs/MENTOR_REVIEW.md').write_text('changed assumptions')
        with self.assertRaisesRegex(ValueError, 'inputs changed'): build(self.root)
        self.save()
        (self.root / 'config').mkdir()
        (self.root / 'config/new.toml').write_text('new assumptions')
        with self.assertRaisesRegex(ValueError, 'inputs changed'): build(self.root)

    def test_old_candidate_without_provenance_requires_rebuild(self):
        del self.status['provenance']
        (self.output / 'candidate_status.json').write_text(json.dumps(self.status))
        with self.assertRaisesRegex(ValueError, 'Missing candidate provenance'): build(self.root)

if __name__ == '__main__': unittest.main()
