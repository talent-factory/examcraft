#!/usr/bin/env python3
"""
Deployment Health Check für ExamCraft AI
Prüft alle Services und Endpoints auf Render.com
"""

import sys
import requests
import json
from typing import Dict, List, Tuple
from datetime import datetime

# Farben für Terminal-Output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class DeploymentChecker:
    """Prüft Deployment-Status und Funktionalität"""

    def __init__(self, base_url: str = None, verbose: bool = False):
        self.base_url = base_url or "https://examcraft.talent-factory.xyz"
        self.api_url = base_url or "https://examcraft-backend-c0bm.onrender.com"
        self.verbose = verbose
        self.results = []

    def log(self, message: str, level: str = "INFO"):
        """Logging mit Farben"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if level == "SUCCESS":
            print(f"{GREEN}✓{RESET} [{timestamp}] {message}")
        elif level == "ERROR":
            print(f"{RED}✗{RESET} [{timestamp}] {message}")
        elif level == "WARNING":
            print(f"{YELLOW}⚠{RESET} [{timestamp}] {message}")
        elif level == "INFO":
            print(f"{BLUE}ℹ{RESET} [{timestamp}] {message}")

    def check_frontend(self) -> bool:
        """Prüft Frontend-Verfügbarkeit"""
        self.log("Checking Frontend...", "INFO")

        try:
            response = requests.get(self.base_url, timeout=10)

            if response.status_code == 200:
                self.log(f"Frontend erreichbar: {self.base_url}", "SUCCESS")

                # Prüfe ob React App geladen wurde
                if "root" in response.text or "react" in response.text.lower():
                    self.log("React App erfolgreich geladen", "SUCCESS")
                    return True
                else:
                    self.log("Frontend lädt, aber React App nicht erkannt", "WARNING")
                    return True
            else:
                self.log(f"Frontend Status Code: {response.status_code}", "ERROR")
                return False

        except requests.exceptions.RequestException as e:
            self.log(f"Frontend nicht erreichbar: {e}", "ERROR")
            return False

    def check_backend_health(self) -> bool:
        """Prüft Backend Health Endpoint"""
        self.log("Checking Backend Health...", "INFO")

        try:
            response = requests.get(f"{self.api_url}/api/v1/health", timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                self.log(f"Backend Health Check: OK", "SUCCESS")

                if self.verbose:
                    print(f"\n{BLUE}Health Check Details:{RESET}")
                    print(json.dumps(health_data, indent=2))
                    print()

                # Prüfe einzelne Services
                services = health_data.get("services", {})
                all_ok = True

                for service, status in services.items():
                    if status in ["connected", "configured", "available"]:
                        self.log(f"  {service}: {status}", "SUCCESS")
                    else:
                        self.log(f"  {service}: {status}", "WARNING")
                        all_ok = False

                return all_ok
            else:
                self.log(f"Health Check failed: {response.status_code}", "ERROR")
                return False

        except requests.exceptions.RequestException as e:
            self.log(f"Backend nicht erreichbar: {e}", "ERROR")
            return False

    def check_api_docs(self) -> bool:
        """Prüft API Dokumentation"""
        self.log("Checking API Documentation...", "INFO")

        try:
            response = requests.get(f"{self.api_url}/docs", timeout=10)

            if response.status_code == 200:
                self.log("API Docs erreichbar: /docs", "SUCCESS")
                return True
            else:
                self.log(f"API Docs Status: {response.status_code}", "WARNING")
                return False

        except requests.exceptions.RequestException as e:
            self.log(f"API Docs nicht erreichbar: {e}", "ERROR")
            return False

    def check_cors(self) -> bool:
        """Prüft CORS-Konfiguration"""
        self.log("Checking CORS Configuration...", "INFO")

        try:
            headers = {
                "Origin": self.base_url,
                "Access-Control-Request-Method": "GET"
            }

            response = requests.options(
                f"{self.api_url}/api/v1/health",
                headers=headers,
                timeout=10
            )

            cors_header = response.headers.get("Access-Control-Allow-Origin")

            if cors_header:
                self.log(f"CORS konfiguriert: {cors_header}", "SUCCESS")
                return True
            else:
                self.log("CORS Header nicht gefunden", "WARNING")
                return False

        except requests.exceptions.RequestException as e:
            self.log(f"CORS Check fehlgeschlagen: {e}", "WARNING")
            return False

    def check_api_endpoints(self) -> Dict[str, bool]:
        """Prüft kritische API Endpoints"""
        self.log("Checking API Endpoints...", "INFO")

        endpoints = {
            "Health": "/api/v1/health",
            "Root": "/",
        }

        results = {}

        for name, path in endpoints.items():
            try:
                response = requests.get(f"{self.api_url}{path}", timeout=10)

                if response.status_code in [200, 404]:  # 404 ist OK für Root
                    self.log(f"  {name} ({path}): OK", "SUCCESS")
                    results[name] = True
                else:
                    self.log(f"  {name} ({path}): {response.status_code}", "WARNING")
                    results[name] = False

            except requests.exceptions.RequestException as e:
                self.log(f"  {name} ({path}): ERROR - {e}", "ERROR")
                results[name] = False

        return results

    def run_all_checks(self) -> bool:
        """Führt alle Checks aus"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}ExamCraft AI - Deployment Health Check{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        print(f"Frontend URL: {self.base_url}")
        print(f"Backend URL:  {self.api_url}\n")

        checks = [
            ("Frontend", self.check_frontend),
            ("Backend Health", self.check_backend_health),
            ("API Documentation", self.check_api_docs),
            ("CORS Configuration", self.check_cors),
        ]

        results = {}

        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                self.log(f"{name} Check failed: {e}", "ERROR")
                results[name] = False
            print()  # Leerzeile zwischen Checks

        # API Endpoints
        endpoint_results = self.check_api_endpoints()
        results.update(endpoint_results)

        # Zusammenfassung
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Zusammenfassung{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        print(f"Checks bestanden: {passed}/{total}\n")

        if passed == total:
            print(f"{GREEN}✅ Alle Checks erfolgreich!{RESET}")
            print(f"\n{GREEN}🎉 Deployment ist vollständig funktional!{RESET}\n")
            return True
        elif passed >= total * 0.7:
            print(f"{YELLOW}⚠️  Deployment funktioniert mit Einschränkungen{RESET}")
            print(f"\n{YELLOW}💡 Einige Services benötigen Aufmerksamkeit{RESET}\n")
            return True
        else:
            print(f"{RED}❌ Deployment hat kritische Probleme!{RESET}")
            print(f"\n{RED}🔧 Bitte beheben Sie die Fehler{RESET}\n")
            return False


def main():
    """Hauptfunktion"""
    import argparse

    parser = argparse.ArgumentParser(
        description="ExamCraft AI Deployment Health Check"
    )
    parser.add_argument(
        "--url",
        default="https://examcraft.talent-factory.xyz",
        help="Frontend URL (default: https://examcraft.talent-factory.xyz)"
    )
    parser.add_argument(
        "--api-url",
        default="https://examcraft-backend-c0bm.onrender.com",
        help="Backend API URL"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    checker = DeploymentChecker(
        base_url=args.url,
        verbose=args.verbose
    )
    checker.api_url = args.api_url

    success = checker.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
