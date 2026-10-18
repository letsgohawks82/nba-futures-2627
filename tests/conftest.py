import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: needs a completed `run.py repro` (clean-room) run; FAILS (never skips) if the run is missing")
