#!/usr/bin/env python3
"""
Import Checker für ExamCraft AI
Prüft, ob alle Python-Imports funktionieren
Verhindert NameError und ImportError vor Commits
"""

import sys
import os
import importlib.util
from pathlib import Path
from typing import List, Tuple

# Farben für Terminal-Output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def check_file_imports(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Prüft, ob eine Python-Datei importiert werden kann

    Returns:
        (success, errors): Tuple mit Erfolg und Fehlerliste
    """
    errors = []

    # Konvertiere Dateipfad zu Modul-Namen
    # Stelle sicher, dass file_path absolut ist
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    relative_path = file_path.relative_to(Path.cwd())
    module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
    module_name = '.'.join(module_parts)

    try:
        # Versuche Modul zu laden
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            errors.append(f"Could not create module spec for {file_path}")
            return False, errors

        module = importlib.util.module_from_spec(spec)

        # Füge zum sys.modules hinzu (wichtig für relative Imports)
        sys.modules[module_name] = module

        # Führe Modul aus (lädt alle Imports)
        spec.loader.exec_module(module)

        return True, []

    except ImportError as e:
        errors.append(f"ImportError in {file_path}: {e}")
        return False, errors
    except NameError as e:
        errors.append(f"NameError in {file_path}: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Error in {file_path}: {type(e).__name__}: {e}")
        return False, errors


def find_python_files(directories: List[str]) -> List[Path]:
    """Findet alle Python-Dateien in den angegebenen Verzeichnissen"""
    python_files = []

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue

        # Finde alle .py Dateien
        for py_file in dir_path.rglob("*.py"):
            # Überspringe __pycache__ und Tests
            if "__pycache__" in str(py_file):
                continue
            if "test_" in py_file.name and "tests/" in str(py_file):
                continue  # Tests werden separat geprüft

            python_files.append(py_file)

    return sorted(python_files)


def main():
    """Hauptfunktion"""
    print(f"\n{YELLOW}🔍 Checking Python Imports...{RESET}\n")

    # Füge Backend und Utils zu Python Path hinzu
    backend_path = Path.cwd() / "backend"
    utils_path = Path.cwd() / "utils"

    if backend_path.exists():
        sys.path.insert(0, str(backend_path))
    if utils_path.exists():
        sys.path.insert(0, str(utils_path))

    # Finde alle Python-Dateien
    directories = ["backend", "utils"]
    python_files = find_python_files(directories)

    if not python_files:
        print(f"{YELLOW}⚠️  No Python files found{RESET}")
        return 0

    print(f"Found {len(python_files)} Python files to check\n")

    # Prüfe jede Datei
    failed_files = []
    all_errors = []

    for file_path in python_files:
        success, errors = check_file_imports(file_path)

        if success:
            print(f"{GREEN}✓{RESET} {file_path}")
        else:
            print(f"{RED}✗{RESET} {file_path}")
            failed_files.append(file_path)
            all_errors.extend(errors)

    # Zusammenfassung
    print(f"\n{'='*60}")

    if failed_files:
        print(f"{RED}❌ Import Check FAILED{RESET}")
        print(f"\nFailed files: {len(failed_files)}/{len(python_files)}\n")

        print("Errors:")
        for error in all_errors:
            print(f"  {RED}•{RESET} {error}")

        print(f"\n{YELLOW}💡 Fix these import errors before committing!{RESET}\n")
        return 1
    else:
        print(f"{GREEN}✅ All imports OK!{RESET}")
        print(f"Checked {len(python_files)} files successfully\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
