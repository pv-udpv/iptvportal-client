#!/usr/bin/env python3
"""
Documentation Consistency Validator

This script validates that documentation across the repository is consistent,
particularly ensuring that README.md aligns with docs/architecture.md.

Usage:
    python scripts/validate_docs.py                    # Check all
    python scripts/validate_docs.py --fix              # Auto-fix where possible
    python scripts/validate_docs.py --diagrams-only    # Check only diagrams
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of a documentation validation check."""
    
    passed: bool
    message: str
    details: Optional[str] = None
    fixable: bool = False


class DocValidator:
    """Validates documentation consistency across the repository."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.readme_path = repo_root / "README.md"
        self.arch_path = repo_root / "docs" / "architecture.md"
        
        if not self.readme_path.exists():
            raise FileNotFoundError(f"README.md not found at {self.readme_path}")
        if not self.arch_path.exists():
            raise FileNotFoundError(f"architecture.md not found at {self.arch_path}")
        
        self.readme_content = self.readme_path.read_text()
        self.arch_content = self.arch_path.read_text()
    
    def extract_mermaid_diagrams(self, content: str) -> Dict[str, str]:
        """Extract all Mermaid diagrams with their section headers as keys."""
        diagrams = {}
        
        # Split content into sections by headers
        sections = re.split(r'\n(#{2,3})\s+([^\n]+)\n', content)
        
        for i in range(1, len(sections), 3):
            if i + 1 < len(sections):
                header_level = sections[i]
                header_text = sections[i + 1].strip()
                section_content = sections[i + 2] if i + 2 < len(sections) else ""
                
                # Look for mermaid diagram in this section
                mermaid_match = re.search(r'```mermaid\n(.*?)\n```', section_content, re.DOTALL)
                if mermaid_match:
                    diagram_content = mermaid_match.group(1).strip()
                    diagrams[header_text] = diagram_content
        
        return diagrams
    
    def normalize_diagram(self, diagram: str) -> str:
        """Normalize a diagram for comparison by removing extra whitespace."""
        lines = [line.strip() for line in diagram.split('\n')]
        return '\n'.join(line for line in lines if line)
    
    def check_diagram_consistency(self) -> List[ValidationResult]:
        """Check that shared diagrams match between README and architecture.md."""
        results = []
        
        readme_diagrams = self.extract_mermaid_diagrams(self.readme_content)
        arch_diagrams = self.extract_mermaid_diagrams(self.arch_content)
        
        # Define which diagrams should be identical
        shared_diagrams = {
            "High-level architecture": "High-Level Component Architecture",
            "CLI SELECT call flow": "CLI SELECT call flow",
            "Sync/cache dataflow": "Sync/cache dataflow",
            "Auth/session lifecycle": "Auth/session lifecycle",
        }
        
        for readme_key, arch_key in shared_diagrams.items():
            readme_diag = readme_diagrams.get(readme_key)
            arch_diag = arch_diagrams.get(arch_key)
            
            if not readme_diag:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Diagram '{readme_key}' not found in README.md",
                    fixable=False
                ))
                continue
            
            if not arch_diag:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Diagram '{arch_key}' not found in architecture.md",
                    fixable=False
                ))
                continue
            
            # Normalize and compare
            readme_norm = self.normalize_diagram(readme_diag)
            arch_norm = self.normalize_diagram(arch_diag)
            
            if readme_norm != arch_norm:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Diagram '{readme_key}' differs from architecture.md",
                    details=f"README version has {len(readme_norm)} chars, "
                           f"architecture.md has {len(arch_norm)} chars",
                    fixable=True
                ))
            else:
                results.append(ValidationResult(
                    passed=True,
                    message=f"Diagram '{readme_key}' matches architecture.md"
                ))
        
        return results
    
    def check_architecture_concepts(self) -> List[ValidationResult]:
        """Check that key architecture concepts are present in README."""
        results = []
        
        key_concepts = [
            ("proxy-centric", "Proxy-centric architecture pattern"),
            ("schema-driven", "Schema-driven development approach"),
            ("multi-level caching", "Multi-level caching strategy"),
        ]
        
        for concept, description in key_concepts:
            if concept.lower() in self.readme_content.lower():
                results.append(ValidationResult(
                    passed=True,
                    message=f"Architecture concept '{concept}' mentioned in README"
                ))
            else:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Architecture concept '{concept}' not mentioned in README",
                    details=description,
                    fixable=False
                ))
        
        return results
    
    def check_architecture_reference(self) -> ValidationResult:
        """Check that README references architecture.md for details."""
        arch_ref_pattern = r'\[docs/architecture\.md\]|architecture\.md'
        
        if re.search(arch_ref_pattern, self.readme_content):
            return ValidationResult(
                passed=True,
                message="README references architecture.md for detailed documentation"
            )
        else:
            return ValidationResult(
                passed=False,
                message="README does not reference architecture.md",
                details="README should point readers to architecture.md for comprehensive details",
                fixable=False
            )
    
    def check_version_consistency(self) -> ValidationResult:
        """Check that version references are consistent."""
        # Extract Python version from README
        readme_py_version = re.search(r'python[:\-\s]+([0-9.]+\+?)', self.readme_content, re.IGNORECASE)
        
        # Extract from pyproject.toml
        pyproject_path = self.repo_root / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_content = pyproject_path.read_text()
            pyproject_py_version = re.search(r'requires-python\s*=\s*["\']>=([0-9.]+)', pyproject_content)
            
            if readme_py_version and pyproject_py_version:
                readme_ver = readme_py_version.group(1).strip('+')
                pyproject_ver = pyproject_py_version.group(1)
                
                if readme_ver.startswith(pyproject_ver):
                    return ValidationResult(
                        passed=True,
                        message=f"Python version consistent: {pyproject_ver}+"
                    )
                else:
                    return ValidationResult(
                        passed=False,
                        message=f"Python version mismatch: README has {readme_ver}, "
                               f"pyproject.toml requires {pyproject_ver}",
                        fixable=True
                    )
        
        return ValidationResult(
            passed=True,
            message="Could not verify Python version consistency (files not found)"
        )
    
    def run_all_checks(self, diagrams_only: bool = False) -> Tuple[List[ValidationResult], int, int]:
        """Run all validation checks."""
        all_results = []
        
        # Always check diagrams
        print("🔍 Checking diagram consistency...")
        diagram_results = self.check_diagram_consistency()
        all_results.extend(diagram_results)
        
        if not diagrams_only:
            print("🔍 Checking architecture concepts...")
            concept_results = self.check_architecture_concepts()
            all_results.extend(concept_results)
            
            print("🔍 Checking architecture.md reference...")
            ref_result = self.check_architecture_reference()
            all_results.append(ref_result)
            
            print("🔍 Checking version consistency...")
            version_result = self.check_version_consistency()
            all_results.append(version_result)
        
        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed)
        
        return all_results, passed, failed


def print_results(results: List[ValidationResult], verbose: bool = False):
    """Print validation results in a readable format."""
    for result in results:
        icon = "✅" if result.passed else "❌"
        print(f"{icon} {result.message}")
        
        if not result.passed and result.details:
            print(f"   ℹ️  {result.details}")
        
        if not result.passed and result.fixable:
            print(f"   🔧 This issue may be auto-fixable with --fix")
        
        if verbose and result.passed:
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate documentation consistency across the repository"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-fix issues where possible"
    )
    parser.add_argument(
        "--diagrams-only",
        action="store_true",
        help="Only check diagram consistency"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output for all checks"
    )
    
    args = parser.parse_args()
    
    # Determine repository root (script is in scripts/ directory)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    print("=" * 80)
    print("📚 Documentation Consistency Validator")
    print("=" * 80)
    print(f"\nRepository: {repo_root}")
    print()
    
    try:
        validator = DocValidator(repo_root)
        results, passed, failed = validator.run_all_checks(args.diagrams_only)
        
        print("\n" + "=" * 80)
        print("📊 Results")
        print("=" * 80)
        print()
        
        print_results(results, args.verbose)
        
        print("\n" + "=" * 80)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📝 Total:  {passed + failed}")
        print("=" * 80)
        
        if failed > 0:
            print("\n⚠️  Documentation validation failed!")
            if args.fix:
                print("🔧 Auto-fix mode is not yet implemented.")
                print("   Please manually update the documentation based on the errors above.")
            else:
                print("   Run with --fix to attempt automatic fixes (where supported).")
            sys.exit(1)
        else:
            print("\n✅ All documentation checks passed!")
            sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Error during validation: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
