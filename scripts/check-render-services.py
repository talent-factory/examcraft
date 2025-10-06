#!/usr/bin/env python3
"""
ExamCraft AI - Render.com Service Health Checker
Überprüft den Status aller deployed Services auf Render.com
"""

import os
import sys
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime

# ANSI Color Codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class RenderServiceChecker:
    """Health Checker für Render.com Services"""
    
    def __init__(self, backend_url: str, frontend_url: str):
        self.backend_url = backend_url.rstrip('/')
        self.frontend_url = frontend_url.rstrip('/')
        self.results = {}
    
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}{text:^60}{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{GREEN}✅ {text}{RESET}")
    
    def print_error(self, text: str):
        """Print error message"""
        print(f"{RED}❌ {text}{RESET}")
    
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{YELLOW}⚠️  {text}{RESET}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"ℹ️  {text}")
    
    def check_backend_health(self) -> bool:
        """Check backend API health"""
        self.print_header("Backend API Health Check")
        
        try:
            # Basic health check
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            if response.status_code == 200:
                self.print_success(f"Backend is reachable: {self.backend_url}")
                data = response.json()
                self.print_info(f"Environment: {data.get('environment', 'unknown')}")
            else:
                self.print_error(f"Backend returned status {response.status_code}")
                return False
            
            # Detailed health check
            response = requests.get(f"{self.backend_url}/api/v1/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.print_success("Detailed health check passed")
                
                # Check individual services
                services = data.get('services', {})
                for service_name, status in services.items():
                    if 'error' in str(status).lower():
                        self.print_error(f"{service_name}: {status}")
                    else:
                        self.print_success(f"{service_name}: {status}")
                
                self.results['backend'] = {
                    'status': 'healthy',
                    'services': services,
                    'version': data.get('version', 'unknown')
                }
                return True
            else:
                self.print_warning("Detailed health check not available")
                self.results['backend'] = {'status': 'degraded'}
                return True
                
        except requests.exceptions.Timeout:
            self.print_error("Backend request timed out")
            self.results['backend'] = {'status': 'timeout'}
            return False
        except requests.exceptions.ConnectionError:
            self.print_error("Cannot connect to backend")
            self.results['backend'] = {'status': 'unreachable'}
            return False
        except Exception as e:
            self.print_error(f"Backend check failed: {str(e)}")
            self.results['backend'] = {'status': 'error', 'message': str(e)}
            return False
    
    def check_frontend(self) -> bool:
        """Check frontend availability"""
        self.print_header("Frontend Health Check")
        
        try:
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                self.print_success(f"Frontend is reachable: {self.frontend_url}")
                
                # Check if it's actually HTML
                if 'text/html' in response.headers.get('content-type', ''):
                    self.print_success("Frontend serving HTML content")
                    self.results['frontend'] = {'status': 'healthy'}
                    return True
                else:
                    self.print_warning("Frontend not serving HTML")
                    self.results['frontend'] = {'status': 'degraded'}
                    return True
            else:
                self.print_error(f"Frontend returned status {response.status_code}")
                self.results['frontend'] = {'status': 'error', 'code': response.status_code}
                return False
                
        except requests.exceptions.Timeout:
            self.print_error("Frontend request timed out")
            self.results['frontend'] = {'status': 'timeout'}
            return False
        except requests.exceptions.ConnectionError:
            self.print_error("Cannot connect to frontend")
            self.results['frontend'] = {'status': 'unreachable'}
            return False
        except Exception as e:
            self.print_error(f"Frontend check failed: {str(e)}")
            self.results['frontend'] = {'status': 'error', 'message': str(e)}
            return False
    
    def check_api_endpoints(self) -> bool:
        """Check critical API endpoints"""
        self.print_header("API Endpoints Check")
        
        endpoints = [
            ("/api/v1/topics", "GET", "Topics endpoint"),
            ("/docs", "GET", "API Documentation"),
        ]
        
        all_passed = True
        
        for path, method, description in endpoints:
            try:
                url = f"{self.backend_url}{path}"
                response = requests.request(method, url, timeout=5)
                
                if response.status_code in [200, 307]:  # 307 for redirects
                    self.print_success(f"{description}: {path}")
                else:
                    self.print_warning(f"{description}: {path} (status {response.status_code})")
                    all_passed = False
                    
            except Exception as e:
                self.print_error(f"{description}: {path} - {str(e)}")
                all_passed = False
        
        return all_passed
    
    def check_claude_integration(self) -> bool:
        """Check Claude API integration"""
        self.print_header("Claude API Integration Check")
        
        try:
            response = requests.get(f"{self.backend_url}/api/v1/claude/usage", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_success("Claude API is configured")
                self.print_info(f"Demo Mode: {data.get('demo_mode', 'unknown')}")
                self.print_info(f"Total Requests: {data.get('total_requests', 0)}")
                self.print_info(f"Total Cost: ${data.get('total_cost', 0):.4f}")
                return True
            else:
                self.print_warning("Claude API usage endpoint not available")
                return False
        except Exception as e:
            self.print_error(f"Claude API check failed: {str(e)}")
            return False
    
    def generate_report(self):
        """Generate summary report"""
        self.print_header("Summary Report")
        
        # Overall status
        backend_ok = self.results.get('backend', {}).get('status') == 'healthy'
        frontend_ok = self.results.get('frontend', {}).get('status') == 'healthy'
        
        if backend_ok and frontend_ok:
            self.print_success("All services are healthy! 🎉")
        elif backend_ok or frontend_ok:
            self.print_warning("Some services are degraded")
        else:
            self.print_error("Critical services are down")
        
        # Detailed results
        print(f"\n{BLUE}Detailed Results:{RESET}")
        print(json.dumps(self.results, indent=2))
        
        # Timestamp
        print(f"\n{BLUE}Report generated at:{RESET} {datetime.now().isoformat()}")
    
    def run_all_checks(self) -> bool:
        """Run all health checks"""
        print(f"\n{BLUE}ExamCraft AI - Render.com Service Health Check{RESET}")
        print(f"{BLUE}Started at: {datetime.now().isoformat()}{RESET}")
        
        backend_ok = self.check_backend_health()
        frontend_ok = self.check_frontend()
        
        if backend_ok:
            self.check_api_endpoints()
            self.check_claude_integration()
        
        self.generate_report()
        
        return backend_ok and frontend_ok


def main():
    """Main entry point"""
    # Get URLs from environment or use defaults
    backend_url = os.getenv(
        'BACKEND_URL',
        'https://examcraft-backend.onrender.com'
    )
    frontend_url = os.getenv(
        'FRONTEND_URL',
        'https://examcraft-frontend.onrender.com'
    )
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
    if len(sys.argv) > 2:
        frontend_url = sys.argv[2]
    
    # Run checks
    checker = RenderServiceChecker(backend_url, frontend_url)
    success = checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

