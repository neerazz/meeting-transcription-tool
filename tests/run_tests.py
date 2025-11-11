#!/usr/bin/env python3
"""
Convenience script to run all tests with various options.

This script provides a simple interface to run the test suite
with different configurations.
"""
import sys
import os
import argparse
import subprocess


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
    
    if result.returncode != 0:
        print(f"\n[ERROR] {description} failed with exit code {result.returncode}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for the meeting transcription tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests.py

  # Run with coverage
  python run_tests.py --coverage

  # Run specific test file
  python run_tests.py --file test_exporter.py

  # Run fast tests only (skip integration)
  python run_tests.py --fast

  # Run with verbose output
  python run_tests.py --verbose
        """
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage report"
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="Run specific test file (e.g., test_exporter.py)"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow and integration tests"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--parallel", "-n",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "--unittest",
        action="store_true",
        help="Use unittest instead of pytest"
    )
    
    args = parser.parse_args()
    
    # Check if pytest is available
    try:
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
        has_pytest = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        has_pytest = False
        if not args.unittest:
            print("[WARNING] pytest not found, falling back to unittest")
            print("Install pytest with: pip install pytest pytest-cov")
            args.unittest = True
    
    # Build command
    if args.unittest:
        # Use unittest
        if args.file:
            test_path = f"tests.{args.file.replace('.py', '')}"
            cmd = [sys.executable, "-m", "unittest", test_path]
        else:
            cmd = [sys.executable, "-m", "unittest", "discover", "tests"]
        
        if args.verbose:
            cmd.append("-v")
        
        success = run_command(cmd, "Running tests with unittest")
    
    else:
        # Use pytest
        cmd = ["pytest"]
        
        if args.verbose:
            cmd.append("-vv")
        else:
            cmd.append("-v")
        
        if args.coverage:
            cmd.extend([
                "--cov=src/meeting_transcription_tool",
                "--cov-report=html",
                "--cov-report=term"
            ])
        
        if args.fast:
            cmd.extend(["-m", "not integration and not slow"])
        
        if args.integration:
            cmd.extend(["-m", "integration"])
        
        if args.parallel:
            cmd.extend(["-n", "auto"])
        
        if args.file:
            cmd.append(f"tests/{args.file}")
        else:
            cmd.append("tests/")
        
        success = run_command(cmd, "Running tests with pytest")
        
        if success and args.coverage:
            print(f"\n{'='*80}")
            print("Coverage report generated: htmlcov/index.html")
            print(f"{'='*80}\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

