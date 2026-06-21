"""
Automated pipeline runner - Runs all steps and handles errors

This script will:
1. Test LOOP with 200 tasks
2. Validate with quality gate
3. Report results
"""

import subprocess
import sys
import json
from pathlib import Path
import time


def run_command(command, description):
    """Run a command and handle errors"""
    print("\n" + "="*70)
    print(f"▶ {description}")
    print("="*70)
    print(f"Command: {command}\n")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=600  # 10 minute timeout
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        
        if result.returncode != 0:
            print(f"\n❌ Command failed with exit code {result.returncode}")
            return False
        
        print(f"\n✅ {description} completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"\n⏱️ Command timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def check_loop_percentage(summary_file):
    """Check if LOOP percentage is ≥5%"""
    try:
        with open(summary_file) as f:
            data = json.load(f)
        
        dist = data.get('failure_distribution', {})
        loop_count = dist.get('LOOP', 0)
        total_failures = data.get('augmented_steps', 0)
        
        if total_failures == 0:
            return False, 0.0
        
        loop_pct = (loop_count / total_failures) * 100
        
        return loop_pct >= 5.0, loop_pct
        
    except Exception as e:
        print(f"❌ Error checking LOOP percentage: {e}")
        return False, 0.0


def print_summary(summary_file):
    """Print dataset summary"""
    try:
        with open(summary_file) as f:
            data = json.load(f)
        
        print("\n" + "="*70)
        print("📊 DATASET SUMMARY")
        print("="*70)
        print(f"Total trajectories: {data.get('total_trajectories', 0)}")
        print(f"Total steps: {data.get('total_steps', 0)}")
        print(f"Clean steps: {data.get('clean_steps', 0)}")
        print(f"Augmented steps: {data.get('augmented_steps', 0)}")
        
        total = data.get('total_steps', 1)
        failures = data.get('augmented_steps', 0)
        print(f"Failure rate: {failures/total*100:.1f}%")
        
        print("\nFailure Distribution:")
        dist = data.get('failure_distribution', {})
        for ftype, count in sorted(dist.items(), key=lambda x: -x[1]):
            pct = (count / failures * 100) if failures > 0 else 0
            print(f"  {ftype}: {count} ({pct:.1f}%)")
        
        # Check LOOP
        loop_ok, loop_pct = check_loop_percentage(summary_file)
        if loop_ok:
            print(f"\n✅ LOOP: {loop_pct:.1f}% (target: ≥5%)")
        else:
            print(f"\n❌ LOOP: {loop_pct:.1f}% (target: ≥5%) - TOO LOW!")
        
        return loop_ok
        
    except Exception as e:
        print(f"❌ Error reading summary: {e}")
        return False


def main():
    print("="*70)
    print("🚀 AUTOMATED DATASET GENERATION PIPELINE")
    print("="*70)
    print("\nThis will:")
    print("  1. Generate 200 tasks to test LOOP injector")
    print("  2. Run quality gate validation")
    print("  3. Report results")
    print("\nEstimated time: 3-5 minutes")
    print("="*70)
    
    # Activate virtual environment
    venv_python = Path(".venv-2/Scripts/python.exe")
    if not venv_python.exists():
        print(f"\n❌ Virtual environment not found: {venv_python}")
        print("Please activate your virtual environment first.")
        return 1
    
    python_cmd = str(venv_python.absolute())
    
    # Step 3: Generate 200 tasks
    success = run_command(
        f'{python_cmd} scripts/test_downloaded_data.py --num-tasks 200 --output-dir output/test_200_tasks',
        "Step 3: Generate 200-task dataset"
    )
    
    if not success:
        print("\n" + "="*70)
        print("❌ STEP 3 FAILED - Cannot proceed")
        print("="*70)
        return 1
    
    # Check results
    summary_file = Path("output/test_200_tasks/summary.json")
    if not summary_file.exists():
        print(f"\n❌ Summary file not found: {summary_file}")
        return 1
    
    loop_ok = print_summary(summary_file)
    
    # Step 4: Run quality gate
    time.sleep(1)  # Brief pause
    
    success = run_command(
        f'{python_cmd} scripts/validate_quality_gate.py '
        f'--summary output/test_200_tasks/summary.json '
        f'--trajectories output/test_200_tasks/augmented_trajectories.json '
        f'--output output/test_200_tasks/quality_report.html',
        "Step 4: Validate with quality gate"
    )
    
    # Final report
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    report_file = Path("output/test_200_tasks/quality_report.html")
    
    if success and loop_ok:
        print("\n✅ ALL CHECKS PASSED!")
        print("\n✅ LOOP injector is working correctly")
        print(f"✅ Quality report: {report_file}")
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Review quality report (opening in browser...)")
        print("2. Run Step 4: Regenerate 100-task pilot")
        print("   Command: run_step4_regenerate_pilot.bat")
        print("3. Run Step 5: Generate 1,000-task dataset")
        print("   Command: run_step5_generate_1000_tasks.bat")
        
        # Try to open report in browser
        try:
            import webbrowser
            webbrowser.open(str(report_file.absolute()))
        except:
            pass
        
        return 0
    else:
        print("\n❌ QUALITY CHECKS FAILED")
        print(f"\nReview quality report: {report_file}")
        print("\nCommon issues:")
        print("  - LOOP percentage too low: Check state_after loading")
        print("  - Failure rate outside 40-60%: Adjust injection config")
        print("  - Missing recovery strategies: Check injector implementation")
        return 1


if __name__ == '__main__':
    sys.exit(main())
