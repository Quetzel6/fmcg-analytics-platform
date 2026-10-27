"""Bind a candidate to its build inputs and review artifacts, without Git access."""
import hashlib


SOURCE_DIRS = ('src', 'tests', 'scripts', 'config', 'sql', 'dashboard', 'docs', '.github')
SOURCE_FILES = ('README.md', 'requirements.txt', 'compose.yaml')
ARTIFACT_DIRS = ('m2', 'm3', 'm4', 'm5', 'scenarios')
ARTIFACT_FILES = ('index.html', 'release_candidate.html', 'release_status.json',
                  'test_summary.json', 'data_quality.json', 'load_report.json')


def inventory(root, paths):
    result = {}
    for path in sorted(set(paths)):
        if path.is_symlink():
            raise ValueError('Symlink in evidence inventory: ' + path.relative_to(root).as_posix())
        data = path.read_bytes()
        result[path.relative_to(root).as_posix()] = dict(
            sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    return result


def sources(root):
    paths = [root / name for name in SOURCE_FILES if (root / name).is_file()]
    for name in SOURCE_DIRS:
        paths.extend(p for p in (root / name).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts
                     and p.suffix not in ('.pyc', '.log'))
    return inventory(root, paths)


def artifacts(root):
    output = root / 'output'
    paths = [output / name for name in ARTIFACT_FILES if (output / name).is_file()]
    for name in ARTIFACT_DIRS:
        paths.extend(p for p in (output / name).rglob('*')
                     if p.is_file() and p.suffix in ('.html', '.json', '.csv'))
    if (root / 'data/manifest.json').is_file():
        paths.append(root / 'data/manifest.json')
    return inventory(root, paths)


def verify(root, provenance):
    if not isinstance(provenance, dict) or provenance.get('version') != 1:
        raise ValueError('Missing candidate provenance; rebuild the candidate')
    if provenance.get('sources') != sources(root):
        raise ValueError('Build inputs changed; rebuild the candidate before packaging')
    if provenance.get('artifacts') != artifacts(root):
        raise ValueError('Candidate artifacts changed; rebuild the candidate before packaging')
