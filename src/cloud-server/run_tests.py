#!/usr/bin/env python3
"""
ArchBuilder.AI Test Runner
Convenient script to run different test suites with proper configuration
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔍 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="ArchBuilder.AI Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run only unit tests
  python run_tests.py --integration      # Run only integration tests
  python run_tests.py --security         # Run only security tests
  python run_tests.py --fast             # Run fast tests only (exclude slow)
  python run_tests.py --coverage         # Run with coverage report
  python run_tests.py --verbose          # Run with verbose output
        """
    )
    
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--security", 
        action="store_true", 
        help="Run only security tests"
    )
    parser.add_argument(
        "--ai", 
        action="store_true", 
        help="Run only AI-related tests"
    )
    parser.add_argument(
        "--database", 
        action="store_true", 
        help="Run only database tests"
    )
    parser.add_argument(
        "--fast", 
        action="store_true", 
        help="Run fast tests only (exclude slow tests)"
    )
    parser.add_argument(
        "--slow", 
        action="store_true", 
        help="Run only slow tests"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Run with verbose output"
    )
    parser.add_argument(
        "--parallel", 
        action="store_true", 
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--failfast", 
        action="store_true", 
        help="Stop on first failure"
    )
    parser.add_argument(
        "--lf", 
        action="store_true", 
        help="Run last failed tests only"
    )
    parser.add_argument(
        "--pdb", 
        action="store_true", 
        help="Drop into debugger on failures"
    )
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test selection based on markers
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.security:
        markers.append("security")
    if args.ai:
        markers.append("ai")
    if args.database:
        markers.append("database")
    
    if markers:
        marker_expr = " or ".join(markers)
        cmd.extend(["-m", marker_expr])
    
    # Add exclusion for slow tests if fast mode
    if args.fast:
        cmd.extend(["-m", "not slow"])
    elif args.slow:
        cmd.extend(["-m", "slow"])
    
    # Add coverage options
    if args.coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml"
        ])
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    # Add fail fast
    if args.failfast:
        cmd.append("-x")
    
    # Add last failed
    if args.lf:
        cmd.append("--lf")
    
    # Add debugger
    if args.pdb:
        cmd.append("--pdb")
    
    # Add test paths
    if args.unit and not args.integration:
        cmd.append("tests/test_unit")
    elif args.integration and not args.unit:
        cmd.append("tests/test_integration")
    else:
        cmd.append("tests")
    
    # Run the tests
    success = run_command(cmd, "Running tests")
    
    if success:
        print("\n🎉 All tests passed!")
        
        if args.coverage:
            print("\n📊 Coverage report generated:")
            print("  - Terminal: See output above")
            print("  - HTML: Open htmlcov/index.html")
            print("  - XML: coverage.xml")
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    # Change to the script directory
    script_dir = Path(__file__).parent
    if script_dir.name == "scripts":
        # If run from scripts directory, go to parent
        script_dir = script_dir.parent
    
    sys.path.insert(0, str(script_dir))
    
    main()