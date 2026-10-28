"""Package a completed synthetic candidate for an offline mentor review."""
import argparse
import hashlib
import json
import posixpath
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from pathlib import Path
import tempfile
import zipfile
from evidence import verify

ROOT = Path(__file__).resolve().parents[1]
STAGES = ['default_release', 'promotion_scenario', 'receipt_scenario', 'q4_plan']
PAGES = ['index.html', 'scenarios/staggered-v1/benchmark.html',
         'scenarios/receipts-v1/benchmark.html', 'scenarios/q4-plan-v1/cockpit.html',
         'scenarios/q4-plan-v1/benchmark.html']


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src') and value)


def validate_links(payload):
    for name, data in payload.items():
        if not name.endswith('.html'):
            continue
        parser = Links()
        parser.feed(data.decode('utf-8'))
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path)))
            if target not in payload:
                raise ValueError('Broken offline link: ' + name + ' -> ' + link)


def build(root=ROOT):
    output = root / 'output'
    status = json.loads((output / 'candidate_status.json').read_text())
    mode = status.get('status')
    if mode not in ('passed', 'passed_local_database_pending'):
        raise ValueError('Rebuild a successful candidate before packaging')
    if status.get('database_verified') is not (mode == 'passed'):
        raise ValueError('Inconsistent database certification')
    verify(root, status.get('provenance'))
    stages = status.get('stages', [])
    if [s.get('name') for s in stages] != STAGES or any(
            s.get('status') != 'passed' or s.get('returncode') != 0 for s in stages):
        raise ValueError('Incomplete candidate stages')
    if status.get('pages') != PAGES:
        raise ValueError('Unexpected candidate page inventory')
    required = ['release_candidate.html', 'candidate_status.json', *PAGES]
    for name in required:
        if not (output / name).is_file():
            raise ValueError('Missing candidate file: ' + name)
    sources = []
    for path in sorted(output.rglob('*')):
        rel = path.relative_to(output)
        if rel.parts[0] in ('m2', 'm3', 'm4', 'm5', 'scenarios') and path.suffix in ('.html', '.json', '.csv'):
            sources.append((path, 'output/' + rel.as_posix()))
    for name in ['index.html', 'release_candidate.html', 'candidate_status.json',
                 'test_summary.json', 'data_quality.json']:
        sources.append((output / name, 'output/' + name))
    for path in sorted((root / 'docs').rglob('*.md')):
        sources.append((path, path.relative_to(root).as_posix()))
    for path, _ in sources:
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing file or symlink in review inventory')
    payload = {name: path.read_bytes() for path, name in sources}
    validate_links(payload)
    inventory = {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                 for name, data in payload.items()}
    manifest = dict(format_version=1, data_class='100% synthetic',
                    candidate_status=status, files=inventory)
    payload['review_manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    payload['START_HERE.txt'] = (
        'Extract this ZIP before opening output/release_candidate.html.\n'
        'Read docs/MENTOR_REVIEW.md for the walkthrough.\n'
        'Candidate status: ' + mode + '\n'
        'Database verified in this packaged run: ' + str(status['database_verified']) + '\n'
        'Source and artifact hashes match the completed candidate; packaging does not rerun tests.\n'
        'Source code, environments, raw warehouse/truth data and process logs are excluded.\n'
    ).encode()
    target = output / 'mentor_review.zip'
    with tempfile.NamedTemporaryFile(dir=output, suffix='.zip', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        print(build())
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit('Review package failed: ' + str(error))
