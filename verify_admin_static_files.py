#!/usr/bin/env python3
"""
Admin Dashboard Static Files Verification Script
Verifies the existence, accessibility, and integrity of all required static files
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

class StaticFileVerifier:
    def __init__(self, base_path: str = "ai-agent/admin-dashboard/frontend"):
        self.base_path = Path(base_path)
        self.css_path = self.base_path / "css"
        self.js_path = self.base_path / "js"
        self.results = {
            "css_files": {},
            "js_files": {},
            "summary": {
                "total_files": 0,
                "verified_files": 0,
                "missing_files": 0,
                "syntax_errors": 0,
                "permission_errors": 0
            },
            "errors": []
        }
        
        # Required files based on the requirements document
        self.required_css_files = [
            "modern-dashboard.css",
            "admin.css", 
            "styles.css",
            "support.css"
        ]
        
        self.required_js_files = [
            "session-manager.js",
            "auth-error-handler.js", 
            "api-connectivity-checker.js",
            "admin-auth-service.js",
            "unified_api.js",
            "api.js",
            "navigation.js",
            "ui-feedback.js",
            "auth.js",
            "dashboard.js",
            "integration.js",
            "main.js",
            "simple-auth-fix.js"
        ]

    def verify_file_exists(self, file_path: Path) -> bool:
        """Check if file exists and is readable"""
        try:
            return file_path.exists() and file_path.is_file()
        except Exception as e:
            self.results["errors"].append(f"Error checking file {file_path}: {str(e)}")
            return False

    def check_file_permissions(self, file_path: Path) -> Dict[str, Any]:
        """Check file permissions and accessibility"""
        permissions = {
            "readable": False,
            "size": 0,
            "error": None
        }
        
        try:
            if file_path.exists():
                permissions["readable"] = os.access(file_path, os.R_OK)
                permissions["size"] = file_path.stat().st_size
            else:
                permissions["error"] = "File does not exist"
        except Exception as e:
            permissions["error"] = str(e)
            
        return permissions

    def validate_css_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Basic CSS syntax validation"""
        validation = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic CSS validation checks
            open_braces = content.count('{')
            close_braces = content.count('}')
            
            if open_braces != close_braces:
                validation["errors"].append(f"Mismatched braces: {open_braces} open, {close_braces} close")
            
            # Check for basic CSS structure
            if ':' not in content and open_braces == 0:
                validation["warnings"].append("File appears to be empty or not contain CSS rules")
            
            # Check for common CSS syntax issues
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('/*') and not line.endswith('*/'):
                    if line.endswith(';') and '{' in line:
                        validation["warnings"].append(f"Line {i}: Possible syntax issue - semicolon before brace")
            
            validation["valid"] = len(validation["errors"]) == 0
            
        except Exception as e:
            validation["errors"].append(f"Error reading file: {str(e)}")
            
        return validation

    def validate_js_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Basic JavaScript syntax validation"""
        validation = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic JavaScript validation checks
            open_parens = content.count('(')
            close_parens = content.count(')')
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_brackets = content.count('[')
            close_brackets = content.count(']')
            
            if open_parens != close_parens:
                validation["errors"].append(f"Mismatched parentheses: {open_parens} open, {close_parens} close")
            
            if open_braces != close_braces:
                validation["errors"].append(f"Mismatched braces: {open_braces} open, {close_braces} close")
                
            if open_brackets != close_brackets:
                validation["errors"].append(f"Mismatched brackets: {open_brackets} open, {close_brackets} close")
            
            # Check for basic JavaScript structure
            if 'function' not in content and 'class' not in content and '=>' not in content and content.strip():
                validation["warnings"].append("File may not contain JavaScript functions or classes")
            
            validation["valid"] = len(validation["errors"]) == 0
            
        except Exception as e:
            validation["errors"].append(f"Error reading file: {str(e)}")
            
        return validation

    def verify_css_files(self) -> None:
        """Verify all CSS files"""
        print("Verifying CSS files...")
        
        for css_file in self.required_css_files:
            file_path = self.css_path / css_file
            print(f"  Checking {css_file}...")
            
            file_info = {
                "path": str(file_path),
                "exists": self.verify_file_exists(file_path),
                "permissions": self.check_file_permissions(file_path),
                "syntax": None
            }
            
            if file_info["exists"]:
                file_info["syntax"] = self.validate_css_syntax(file_path)
                print(f"    ✓ Found and readable")
                if not file_info["syntax"]["valid"]:
                    print(f"    ⚠ Syntax issues: {file_info['syntax']['errors']}")
                    self.results["summary"]["syntax_errors"] += 1
                else:
                    self.results["summary"]["verified_files"] += 1
            else:
                print(f"    ✗ Missing or not accessible")
                self.results["summary"]["missing_files"] += 1
                
            if not file_info["permissions"]["readable"]:
                self.results["summary"]["permission_errors"] += 1
                
            self.results["css_files"][css_file] = file_info
            self.results["summary"]["total_files"] += 1

    def verify_js_files(self) -> None:
        """Verify all JavaScript files"""
        print("\nVerifying JavaScript files...")
        
        for js_file in self.required_js_files:
            file_path = self.js_path / js_file
            print(f"  Checking {js_file}...")
            
            file_info = {
                "path": str(file_path),
                "exists": self.verify_file_exists(file_path),
                "permissions": self.check_file_permissions(file_path),
                "syntax": None
            }
            
            if file_info["exists"]:
                file_info["syntax"] = self.validate_js_syntax(file_path)
                print(f"    ✓ Found and readable")
                if not file_info["syntax"]["valid"]:
                    print(f"    ⚠ Syntax issues: {file_info['syntax']['errors']}")
                    self.results["summary"]["syntax_errors"] += 1
                else:
                    self.results["summary"]["verified_files"] += 1
            else:
                print(f"    ✗ Missing or not accessible")
                self.results["summary"]["missing_files"] += 1
                
            if not file_info["permissions"]["readable"]:
                self.results["summary"]["permission_errors"] += 1
                
            self.results["js_files"][js_file] = file_info
            self.results["summary"]["total_files"] += 1

    def check_directory_structure(self) -> None:
        """Verify the directory structure exists"""
        print("Verifying directory structure...")
        
        directories = [
            self.base_path,
            self.css_path,
            self.js_path
        ]
        
        for directory in directories:
            if directory.exists() and directory.is_dir():
                print(f"  ✓ {directory} exists")
            else:
                print(f"  ✗ {directory} missing")
                self.results["errors"].append(f"Directory missing: {directory}")

    def discover_additional_files(self) -> None:
        """Discover any additional static files not in the required list"""
        print("\nDiscovering additional static files...")
        
        # Check for additional CSS files
        if self.css_path.exists():
            css_files = list(self.css_path.glob("*.css"))
            additional_css = [f.name for f in css_files if f.name not in self.required_css_files]
            if additional_css:
                print(f"  Additional CSS files found: {additional_css}")
                
        # Check for additional JS files  
        if self.js_path.exists():
            js_files = list(self.js_path.glob("*.js"))
            additional_js = [f.name for f in js_files if f.name not in self.required_js_files]
            if additional_js:
                print(f"  Additional JS files found: {additional_js}")

    def generate_report(self) -> None:
        """Generate a comprehensive verification report"""
        print("\n" + "="*60)
        print("ADMIN DASHBOARD STATIC FILES VERIFICATION REPORT")
        print("="*60)
        
        summary = self.results["summary"]
        print(f"Total files checked: {summary['total_files']}")
        print(f"Successfully verified: {summary['verified_files']}")
        print(f"Missing files: {summary['missing_files']}")
        print(f"Syntax errors: {summary['syntax_errors']}")
        print(f"Permission errors: {summary['permission_errors']}")
        
        # Success rate
        if summary['total_files'] > 0:
            success_rate = (summary['verified_files'] / summary['total_files']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        # Detailed errors
        if self.results["errors"]:
            print(f"\nErrors encountered:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        # Missing files
        missing_files = []
        for file_type in ["css_files", "js_files"]:
            for filename, info in self.results[file_type].items():
                if not info["exists"]:
                    missing_files.append(f"{file_type.replace('_files', '').upper()}: {filename}")
        
        if missing_files:
            print(f"\nMissing files:")
            for missing in missing_files:
                print(f"  - {missing}")
        
        # Files with syntax issues
        syntax_issues = []
        for file_type in ["css_files", "js_files"]:
            for filename, info in self.results[file_type].items():
                if info["syntax"] and not info["syntax"]["valid"]:
                    syntax_issues.append(f"{file_type.replace('_files', '').upper()}: {filename}")
        
        if syntax_issues:
            print(f"\nFiles with syntax issues:")
            for issue in syntax_issues:
                print(f"  - {issue}")
        
        print("\n" + "="*60)

    def save_report(self, filename: str = "admin_static_files_verification.json") -> None:
        """Save detailed report to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"Detailed report saved to: {filename}")
        except Exception as e:
            print(f"Error saving report: {e}")

    def run_verification(self) -> bool:
        """Run complete verification process"""
        print("Starting Admin Dashboard Static Files Verification...")
        print("="*60)
        
        self.check_directory_structure()
        self.verify_css_files()
        self.verify_js_files()
        self.discover_additional_files()
        self.generate_report()
        self.save_report()
        
        # Return True if all files are verified successfully
        summary = self.results["summary"]
        return (summary["missing_files"] == 0 and 
                summary["syntax_errors"] == 0 and 
                summary["permission_errors"] == 0)

def main():
    """Main function"""
    verifier = StaticFileVerifier()
    success = verifier.run_verification()
    
    if success:
        print("\n✅ All static files verified successfully!")
        sys.exit(0)
    else:
        print("\n❌ Static file verification failed. Please check the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()