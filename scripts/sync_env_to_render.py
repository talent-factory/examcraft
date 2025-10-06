#!/usr/bin/env python3
"""
Environment Variable Sync für Render.com
Liest .env Datei und zeigt fehlende/falsche Environment Variables im Render Service
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Farben für Terminal-Output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


class RenderEnvSync:
    """Synchronisiert Environment Variables mit Render.com"""
    
    # Variables die von Render automatisch gesetzt werden
    RENDER_AUTO_VARS = {
        'PORT',
        'RENDER',
        'RENDER_SERVICE_NAME',
        'RENDER_INSTANCE_ID',
        'RENDER_GIT_COMMIT',
        'RENDER_GIT_BRANCH',
        'DATABASE_URL',  # Wird von Render PostgreSQL gesetzt
        'REDIS_URL',     # Wird von Render Redis gesetzt
    }
    
    # Variables die Secrets sind (nicht anzeigen)
    SECRET_VARS = {
        'CLAUDE_API_KEY',
        'QDRANT_API_KEY',
        'SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL',
    }
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self.env_vars = {}
        
    def load_env_file(self) -> bool:
        """Lädt .env Datei"""
        if not self.env_file.exists():
            print(f"{RED}✗{RESET} .env Datei nicht gefunden: {self.env_file}")
            return False
        
        # Load .env file
        load_dotenv(self.env_file)
        
        # Parse .env file manually to get all variables
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Skip template values
                    if value and not value.startswith('${') and not value.startswith('your_'):
                        self.env_vars[key] = value
        
        print(f"{GREEN}✓{RESET} .env Datei geladen: {len(self.env_vars)} Variables")
        return True
    
    def categorize_variables(self) -> Dict[str, List[str]]:
        """Kategorisiert Environment Variables"""
        categories = {
            'required': [],      # Muss manuell gesetzt werden
            'auto': [],          # Wird von Render automatisch gesetzt
            'optional': [],      # Optional
        }
        
        for key in self.env_vars.keys():
            if key in self.RENDER_AUTO_VARS:
                categories['auto'].append(key)
            elif key in self.SECRET_VARS or 'KEY' in key or 'SECRET' in key:
                categories['required'].append(key)
            else:
                categories['optional'].append(key)
        
        return categories
    
    def mask_secret(self, value: str) -> str:
        """Maskiert Secret-Werte"""
        if len(value) <= 8:
            return '*' * len(value)
        return value[:4] + '*' * (len(value) - 8) + value[-4:]
    
    def print_env_summary(self):
        """Zeigt Zusammenfassung der Environment Variables"""
        categories = self.categorize_variables()
        
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Environment Variables Übersicht{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        
        # Required Variables (müssen manuell gesetzt werden)
        if categories['required']:
            print(f"{YELLOW}📋 REQUIRED - Manuell in Render Dashboard setzen:{RESET}\n")
            
            for key in sorted(categories['required']):
                value = self.env_vars[key]
                
                if key in self.SECRET_VARS:
                    display_value = self.mask_secret(value)
                else:
                    display_value = value
                
                print(f"  {CYAN}{key:30}{RESET} = {display_value}")
            
            print()
        
        # Auto Variables (werden von Render gesetzt)
        if categories['auto']:
            print(f"{GREEN}✓ AUTO - Automatisch von Render.com gesetzt:{RESET}\n")
            
            for key in sorted(categories['auto']):
                if key in self.env_vars:
                    value = self.env_vars[key]
                    if key in self.SECRET_VARS:
                        display_value = self.mask_secret(value)
                    else:
                        display_value = value
                    print(f"  {CYAN}{key:30}{RESET} = {display_value}")
                else:
                    print(f"  {CYAN}{key:30}{RESET} = {YELLOW}(wird automatisch gesetzt){RESET}")
            
            print()
        
        # Optional Variables
        if categories['optional']:
            print(f"{BLUE}ℹ OPTIONAL - Empfohlen zu setzen:{RESET}\n")
            
            for key in sorted(categories['optional']):
                value = self.env_vars[key]
                print(f"  {CYAN}{key:30}{RESET} = {value}")
            
            print()
    
    def generate_render_commands(self):
        """Generiert Render CLI Commands (falls verfügbar)"""
        categories = self.categorize_variables()
        
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Render Dashboard - Environment Variables setzen{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        
        print(f"{YELLOW}Gehen Sie zu:{RESET}")
        print(f"  https://dashboard.render.com/web/srv-d3hnuk1r0fns73chrjsg/env\n")
        
        print(f"{YELLOW}Setzen Sie folgende Variables:{RESET}\n")
        
        # Required + Optional (nicht Auto)
        all_manual = categories['required'] + categories['optional']
        
        for key in sorted(all_manual):
            value = self.env_vars[key]
            
            if key in self.SECRET_VARS:
                print(f"  {CYAN}{key:30}{RESET} = {YELLOW}<Ihr Secret>{RESET}")
            else:
                print(f"  {CYAN}{key:30}{RESET} = {value}")
        
        print()
    
    def generate_env_file_template(self, output_file: str = ".env.render"):
        """Generiert .env Template für Render.com"""
        categories = self.categorize_variables()
        
        with open(output_file, 'w') as f:
            f.write("# ExamCraft AI - Render.com Environment Variables\n")
            f.write("# Generiert von sync_env_to_render.py\n")
            f.write(f"# Quelle: {self.env_file}\n\n")
            
            # Required
            if categories['required']:
                f.write("# ============================================\n")
                f.write("# REQUIRED - Manuell setzen\n")
                f.write("# ============================================\n\n")
                
                for key in sorted(categories['required']):
                    value = self.env_vars[key]
                    
                    if key in self.SECRET_VARS:
                        f.write(f"{key}=<YOUR_SECRET_HERE>\n")
                    else:
                        f.write(f"{key}={value}\n")
                
                f.write("\n")
            
            # Optional
            if categories['optional']:
                f.write("# ============================================\n")
                f.write("# OPTIONAL - Empfohlen\n")
                f.write("# ============================================\n\n")
                
                for key in sorted(categories['optional']):
                    value = self.env_vars[key]
                    f.write(f"{key}={value}\n")
                
                f.write("\n")
            
            # Auto
            if categories['auto']:
                f.write("# ============================================\n")
                f.write("# AUTO - Automatisch von Render.com gesetzt\n")
                f.write("# Diese müssen NICHT manuell gesetzt werden\n")
                f.write("# ============================================\n\n")
                
                for key in sorted(categories['auto']):
                    f.write(f"# {key}=<automatisch>\n")
                
                f.write("\n")
        
        print(f"{GREEN}✓{RESET} Template generiert: {output_file}")
        print(f"  Verwenden Sie diese Datei als Referenz für Render Dashboard\n")


def main():
    """Hauptfunktion"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Synchronisiert Environment Variables mit Render.com"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Pfad zur .env Datei (default: .env)"
    )
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Generiert .env.render Template"
    )
    parser.add_argument(
        "--output",
        default=".env.render",
        help="Output-Datei für Template (default: .env.render)"
    )
    
    args = parser.parse_args()
    
    # Sync erstellen
    sync = RenderEnvSync(env_file=args.env_file)
    
    # .env laden
    if not sync.load_env_file():
        sys.exit(1)
    
    # Zusammenfassung anzeigen
    sync.print_env_summary()
    
    # Render Commands generieren
    sync.generate_render_commands()
    
    # Template generieren
    if args.generate_template:
        sync.generate_env_file_template(output_file=args.output)
    
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{GREEN}✓ Fertig!{RESET}\n")
    
    print(f"{YELLOW}Nächste Schritte:{RESET}")
    print(f"  1. Öffnen Sie: https://dashboard.render.com/web/srv-d3hnuk1r0fns73chrjsg/env")
    print(f"  2. Setzen Sie die REQUIRED Variables (siehe oben)")
    print(f"  3. Klicken Sie 'Save Changes'")
    print(f"  4. Neues Deployment wird automatisch getriggert\n")


if __name__ == "__main__":
    main()

