# Makes the repo root importable so tests can do `from src... import ...`.
# pytest adds the directory containing the root conftest.py to sys.path;
# without this, bare `pytest` (what CI runs) fails with ModuleNotFoundError.
