#!/usr/bin/env bash
# One-command clean-room reproduction + validation from a fresh clone of a release tag.
#   scripts/cleanroom.sh                       # N = 20000 seeds-fixed reduced run (about 10-15 minutes)
#   NBA_N=100000 scripts/cleanroom.sh          # full-N run at the production seed: the card must match exactly
# Needs: Python 3.13 (PYTHON=... to override). Windows-only pywin32 / xlwings are skipped; without Excel the workbook is rebuilt WITHOUT recalculation
# into repro/output (the committed workbook is never overwritten) and its integrity checks are re-computed in Python. Nothing is downloaded except the pinned packages.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 NBA_CLEANROOM=1 NBA_OUTPUT_DIR="$PWD/repro/output" NBA_N="${NBA_N:-20000}" NBA_SEED="${NBA_SEED:-2026}"
BASE_PY="${PYTHON:-python3}"; command -v "$BASE_PY" >/dev/null 2>&1 || BASE_PY=python
if [ "$(uname -s | cut -c1-5)" != "MINGW" ] && [ "$(uname -s | cut -c1-6)" != "CYGWIN" ]; then export NBA_NO_EXCEL=1 NBA_ALLOW_NO_EXCEL=1; else :; fi
if [ "${NBA_NO_EXCEL:-0}" = "1" ]; then echo "[cleanroom] no Excel: workbook will be built without recalculation"; fi
mkdir -p repro/output
step() { echo; echo "=== [cleanroom] $* ==="; }
step "1. venv from requirements.lock.txt (pywin32 / xlwings skipped off Windows)"
"$BASE_PY" -m venv .venv_cleanroom
if [ -x .venv_cleanroom/bin/python ]; then VPY=.venv_cleanroom/bin/python; else VPY=.venv_cleanroom/Scripts/python.exe; fi
case "$(uname -s)" in MINGW*|CYGWIN*|MSYS*) grep -v -i -E '^(colorama)==' requirements.lock.txt > repro/requirements.cleanroom.txt ;; *) grep -v -i -E '^(pywin32|xlwings|colorama)==' requirements.lock.txt > repro/requirements.cleanroom.txt ;; esac
"$VPY" -m pip install --quiet --disable-pip-version-check -r repro/requirements.cleanroom.txt
if [ "${NBA_BLOCK_NETWORK:-0}" = "1" ]; then : > repro/network_attempts.log; export PYTHONPATH="$PWD/scripts/nonet" NBA_NONET_LOG="$PWD/repro/network_attempts.log"; echo "[cleanroom] outbound network blocked for steps 2-7 (log: repro/network_attempts.log)"; fi
step "2. restore + verify the frozen input archive (SHA-256 against data/manifest.csv)"
"$VPY" scripts/verify_inputs.py --restore
step "3. static tests (inputs, engine invariants, release metadata, committed card vs committed workbook)"
NBA_OUTPUT_DIR= "$VPY" -m pytest -q -m "not e2e" tests
step "4. ratings -> fixed-seed simulation (N=$NBA_N, seed=$NBA_SEED) -> pricing -> reports/repro_check.md"
"$VPY" run.py repro --n "$NBA_N" --seed "$NBA_SEED"
step "5. rebuild the workbook (fail-closed on any integrity flag) and, with Excel, the dashboard PDF"
"$VPY" -m src.workbook.build
if [ "${NBA_NO_EXCEL:-0}" != "1" ]; then "$VPY" -m src.workbook.export_pdf; else echo "[cleanroom] PDF skipped: the workbook has no cached values without Excel"; fi
step "6. end-to-end tests against the rebuilt outputs"
"$VPY" -m pytest -q tests
step "7. SHA-256 of key inputs and outputs"
"$VPY" scripts/hash_outputs.py
if [ "${NBA_BLOCK_NETWORK:-0}" = "1" ]; then echo "[cleanroom] network attempts during steps 2-7: $(wc -l < repro/network_attempts.log)"; [ ! -s repro/network_attempts.log ] || { echo "[cleanroom] FAILED: network was used"; exit 1; }; fi
echo; echo "[cleanroom] ALL STEPS PASSED"
