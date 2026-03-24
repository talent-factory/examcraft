#!/usr/bin/env python3
"""
Requirements Validator für ExamCraft AI
Prüft requirements.txt auf Konsistenz und fehlende Dependencies
"""

import sys
import re
from pathlib import Path
from typing import Set, List, Tuple

# Farben für Terminal-Output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def parse_requirements(req_file: Path) -> Set[str]:
    """Parse requirements.txt und extrahiere Package-Namen"""
    packages = set()

    with open(req_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Überspringe Kommentare und leere Zeilen
            if not line or line.startswith('#'):
                continue

            # Extrahiere Package-Namen (vor ==, >=, etc.)
            match = re.match(r'^([a-zA-Z0-9_-]+)', line)
            if match:
                packages.add(match.group(1).lower())

    return packages


def find_imports_in_file(file_path: Path) -> Set[str]:
    """Findet alle Import-Statements in einer Python-Datei"""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # import xyz
                if line.startswith('import '):
                    parts = line.split()
                    if len(parts) >= 2:
                        package = parts[1].split('.')[0]
                        imports.add(package)

                # from xyz import ...
                elif line.startswith('from '):
                    parts = line.split()
                    if len(parts) >= 2:
                        package = parts[1].split('.')[0]
                        imports.add(package)

    except Exception as e:
        print(f"{YELLOW}⚠️  Could not read {file_path}: {e}{RESET}")

    return imports


def find_all_imports(directory: Path) -> Set[str]:
    """Findet alle Imports in allen Python-Dateien"""
    all_imports = set()

    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        imports = find_imports_in_file(py_file)
        all_imports.update(imports)

    return all_imports


# Standard Library Packages (müssen nicht in requirements.txt sein)
STDLIB_PACKAGES = {
    'os', 'sys', 'time', 'datetime', 'json', 'logging', 'typing',
    'pathlib', 'asyncio', 'dataclasses', 'enum', 'abc', 'collections',
    'functools', 'itertools', 're', 'uuid', 'hashlib', 'random',
    'concurrent', 'threading', 'multiprocessing', 'subprocess',
    'importlib', 'inspect', 'traceback', 'warnings', 'io', 'tempfile',
    'shutil', 'glob', 'pickle', 'copy', 'base64', 'urllib', 'http',
    'email', 'mimetypes', 'secrets', 'string', 'math', 'statistics',
}

# Package-Name Mappings (Import-Name → PyPI-Name)
PACKAGE_MAPPINGS = {
    'pydantic_settings': 'pydantic-settings',
    'jose': 'python-jose',
    'dotenv': 'python-dotenv',
    'docx': 'python-docx',
    'magic': 'python-magic',
    'PIL': 'pillow',
    'cv2': 'opencv-python',
    'sklearn': 'scikit-learn',
    'yaml': 'pyyaml',
}


def normalize_package_name(import_name: str) -> str:
    """Konvertiert Import-Namen zu PyPI-Package-Namen"""
    return PACKAGE_MAPPINGS.get(import_name, import_name.replace('_', '-'))


def main():
    """Hauptfunktion"""
    print(f"\n{YELLOW}🔍 Validating requirements.txt...{RESET}\n")

    # Pfade
    backend_dir = Path.cwd() / "backend"
    req_file = backend_dir / "requirements.txt"

    if not req_file.exists():
        print(f"{RED}❌ requirements.txt not found!{RESET}")
        return 1

    # Parse requirements.txt
    required_packages = parse_requirements(req_file)
    print(f"📦 Found {len(required_packages)} packages in requirements.txt")

    # Finde alle Imports im Code
    all_imports = find_all_imports(backend_dir)

    # Filtere Standard Library
    third_party_imports = {
        imp for imp in all_imports
        if imp not in STDLIB_PACKAGES
    }

    print(f"📥 Found {len(third_party_imports)} third-party imports in code\n")

    # Prüfe fehlende Dependencies
    missing = []
    for import_name in sorted(third_party_imports):
        package_name = normalize_package_name(import_name)

        if package_name not in required_packages:
            # Prüfe auch ohne Normalisierung
            if import_name.lower() not in required_packages:
                missing.append((import_name, package_name))

    # Prüfe ungenutzte Dependencies
    unused = []
    for package in sorted(required_packages):
        # Konvertiere zu Import-Namen
        import_name = package.replace('-', '_')

        if import_name not in all_imports and package not in all_imports:
            # Prüfe auch Reverse-Mappings
            is_used = False
            for imp, pkg in PACKAGE_MAPPINGS.items():
                if pkg == package and imp in all_imports:
                    is_used = True
                    break

            if not is_used:
                unused.append(package)

    # Ausgabe
    errors = []

    if missing:
        print(f"{RED}❌ Missing Dependencies:{RESET}")
        for import_name, package_name in missing:
            print(f"  {RED}•{RESET} Import '{import_name}' → Add '{package_name}' to requirements.txt")
            errors.append(f"Missing: {package_name}")
        print()

    if unused:
        print(f"{YELLOW}⚠️  Potentially Unused Dependencies:{RESET}")
        for package in unused:
            print(f"  {YELLOW}•{RESET} {package}")
        print(f"\n{YELLOW}💡 Consider removing unused packages to reduce build time{RESET}\n")

    # Zusammenfassung
    print(f"{'='*60}")

    if errors:
        print(f"{RED}❌ Validation FAILED{RESET}")
        print(f"\n{len(errors)} error(s) found\n")
        return 1
    else:
        print(f"{GREEN}✅ Requirements validation passed!{RESET}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
