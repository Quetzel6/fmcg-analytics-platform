"""Read-only environment checks; no database connection or generated-data writes."""
import argparse
import importlib
from importlib import metadata
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "requirements.txt", "config/scenario.toml",
    "src/fmcg/generate.py", "scripts/run_release.py",
)
PACKAGES = (("numpy", "numpy", "2.3.5"), ("psycopg", "psycopg", "3.2.10"))


def check_environment(root=ROOT, version=None):
    root = Path(root).resolve()
    version = tuple(sys.version_info[:3]) if version is None else tuple(version)
    issues = []
    result = {
        "status": "ready",
        "python": ".".join(map(str, version)),
        "executable": sys.executable,
        "project_root": str(root),
        "virtual_environment": sys.prefix != sys.base_prefix,
        "packages": {},
        "issues": issues,
    }
    if version[:2] < (3, 11):
        issues.append("Python 3.11 or later is required; recreate the environment using Python 3.13.")
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        issues.append("Incomplete project folder; missing: " + ", ".join(missing))
    # Avoid third-party imports when the Python or project layout is already wrong.
    if not issues:
        for distribution, module, expected in PACKAGES:
            try:
                installed = metadata.version(distribution)
            except metadata.PackageNotFoundError:
                installed = None
            result["packages"][distribution] = {"installed": installed, "required": expected}
            if installed != expected:
                issues.append(distribution + " must be " + expected + "; installed: " + str(installed))
                continue
            try:
                importlib.import_module(module)
            except (ImportError, OSError):
                issues.append(distribution + " is installed but cannot be imported by this interpreter.")
    if issues:
        result["status"] = "blocked"
        result["reason"] = "; ".join(issues)
        result["install_command"] = shlex.join(
            [sys.executable, "-m", "pip", "install", "-r", str(root / "requirements.txt")]
        )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Project folder to inspect")
    args = parser.parse_args()
    result = check_environment(args.root)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "ready" else 2)
