# Mac project folder and Python environment

Open the source repository folder in VS Code using File → Open Folder. It must contain `scripts/run_release.py`, `src`, `config` and `requirements.txt`. A parent folder containing multiple extracted ZIP releases is not the source root.

## Use the working environment

From the project root:

```bash
source .venv-py313/bin/activate
python --version
python scripts/doctor.py
```

The doctor prints the active executable, project root, exact pinned package versions and readiness. It connects to no database and writes no generated output. The release runner performs the same check before launching stages. Python below 3.11, incomplete source folders, missing/wrong package pins and import failures block the run with a direct reason.

Use Python 3.13 to match CI. If rebuilding an environment after moving the project, first deactivate any active venv, then use:

```bash
python3.13 --version
python3.13 -m venv .venv-py313
source .venv-py313/bin/activate
python -m pip install -r requirements.txt
python scripts/doctor.py
python -u scripts/run_release.py --local
open output/index.html
```

If an existing `.venv-py313` cannot run after a move, rename that directory as a backup before recreating it. Do not overwrite a known working environment just to change its name. If `python3.13` is not found, locate the installed Python 3.13 executable before creating the environment; plain `python3` may still point to Python 3.10.

## VS Code

Install/enable the Microsoft Python extension. Open the source folder, then Command Palette → Python: Select Interpreter → Enter interpreter path. Choose `<project-root>/.venv-py313/bin/python`. Open a new terminal and verify `python --version` and `python -c "import sys; print(sys.executable)"`; editor selection and a previously activated terminal can differ.

## Older environments

Keep `.venv` and `.venv-new` until the replacement passes. They are disposable dependencies, not source code; they do not need edits or renaming to match the active environment. Remove unused environments later only after confirming VS Code and terminals use `.venv-py313`. Git ignores `.venv/`, `.venv-*/` and macOS `.DS_Store`.

Changing the interpreter does not redesign the dashboard. Inspect `output/release_status.json` to confirm the latest rebuild finished; opening an older HTML file is not release acceptance.
