#!/usr/bin/env python
"""
Simple test runner - Run this manually to test the 200-task dataset

Usage:
    python run_test_200.py
"""

import sys
import subprocess
from pathlib import Path

def main():
    print("="*70)
    print("Testing LOOP Injector with 200 Tasks")
    print("="*70)
    print()
    
    # Step 1: Generate 200 tasks
    print("Step 1: Generating 200-task dataset...")
    print("Command: python scripts/test_downloaded_data.py --num-tasks 200 --output-dir output/test_200_tasks")
    print()
    
    result = subprocess.run([
        sys.executable,
        "scripts/test_downloaded_data.py",
        "--num-tasks", "200",
        "--output-dir", "output/test_200_tasks"
    ])
    
    if result.returncode != 0:
        print("\n❌ Failed to generate dataset")
        return 1
    
    print("\n✅ Dataset generated successfully")
    
    # Step 2: Run quality gate
    print("\n" + "="*70)
    print("Step 2: Running quality gate validation...")
    print("="*70)
    print()
    
    result = subprocess.run([
        sys.executable,
        "scripts/validate_quality_gate.py",
        "--summary", "output/test_200_tasks/summary.json",
        "--trajectories", "output/test_200_tasks/augmented_trajectories.json",
        "--output", "output/test_200_tasks/quality_report.html"
    ])
    
    if result.returncode == 0:
        print("\n" + "="*70)
        print("✅ ALL QUALITY GATES PASSED!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Review quality report: output/test_200_tasks/quality_report.html")
        print("  2. Run: python run_test_100.py   (regenerate pilot)")
        print("  3. Run: python run_test_1000.py  (full dataset)")
    else:
        print("\n" + "="*70)
        print("❌ QUALITY GATES FAILED")
        print("="*70)
        print("\nReview report: output/test_200_tasks/quality_report.html")
    
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
