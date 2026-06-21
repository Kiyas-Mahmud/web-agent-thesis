"""
Quality Gate Validation System

Prevents scaling to large dataset if pilot has issues.

Gates:
1. Failure rate must be 40-60%
2. LOOP failures must be ≥5%
3. Recovery strategies must be present (>0%)
4. No missing screenshots or critical fields
5. All 5 failure types must be present

Usage (pilot dataset):
    python scripts/validate_quality_gate.py \
        --summary output/pilot_100_final/summary.json \
        --trajectories output/pilot_100_final/augmented_trajectories.json \
        --output output/pilot_100_final/quality_report.html

Usage (10K dataset):
    python scripts/validate_quality_gate.py \
        --summary output/dataset_10k_final/summary.json \
        --trajectories output/dataset_10k_final/augmented_trajectories.json \
        --output output/dataset_10k_final/quality_report.html
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import argparse


@dataclass
class QualityThresholds:
    """Quality gate thresholds"""
    failure_rate_min: float = 0.40  # 40%
    failure_rate_max: float = 0.60  # 60%
    loop_min_percentage: float = 0.05  # 5%
    recovery_rate_min: float = 0.01  # >0%
    missing_screenshots_max: int = 0
    missing_fields_max: int = 0
    schema_violations_max: int = 0


class QualityGate:
    """Automated quality validation"""
    
    def __init__(self, summary_path: str, trajectories_path: str):
        with open(summary_path) as f:
            self.summary = json.load(f)
        with open(trajectories_path) as f:
            self.trajectories = json.load(f)
        
        self.thresholds = QualityThresholds()
        self.results = {}
    
    def check_failure_rate(self) -> Tuple[bool, str, Dict]:
        """Gate 1: Failure rate must be 40-60%"""
        total = self.summary['total_steps']
        failures = self.summary['augmented_steps']
        rate = failures / total if total > 0 else 0
        
        passed = self.thresholds.failure_rate_min <= rate <= self.thresholds.failure_rate_max
        
        details = {
            'total_steps': total,
            'failures': failures,
            'rate': rate,
            'target': f'{self.thresholds.failure_rate_min:.0%}-{self.thresholds.failure_rate_max:.0%}',
            'actual': f'{rate:.1%}'
        }
        
        message = f"Failure rate: {rate:.1%} (target: 40-60%)"
        if not passed:
            message += " ❌ FAIL"
        else:
            message += " ✅ PASS"
        
        return passed, message, details
    
    def check_loop_presence(self) -> Tuple[bool, str, Dict]:
        """Gate 2: LOOP must be ≥5% of failures"""
        dist = self.summary.get('failure_distribution', {})
        loop_count = dist.get('LOOP', 0)
        total_failures = self.summary['augmented_steps']
        loop_pct = (loop_count / total_failures) if total_failures > 0 else 0
        
        passed = loop_pct >= self.thresholds.loop_min_percentage
        
        details = {
            'loop_count': loop_count,
            'total_failures': total_failures,
            'loop_percentage': loop_pct,
            'target': f'≥{self.thresholds.loop_min_percentage:.0%}',
            'actual': f'{loop_pct:.1%}'
        }
        
        message = f"LOOP failures: {loop_count} ({loop_pct:.1%}, target: ≥5%)"
        if not passed:
            message += " ❌ FAIL"
        else:
            message += " ✅ PASS"
        
        return passed, message, details
    
    def check_recovery_strategies(self) -> Tuple[bool, str, Dict]:
        """Gate 3: Recovery strategies must be present"""
        with_recovery = 0
        total_augmented = 0
        
        for traj in self.trajectories:
            for step in traj.get('steps', []):
                if step.get('is_augmented'):
                    total_augmented += 1
                    if step.get('recovery_strategy'):
                        with_recovery += 1
        
        recovery_rate = (with_recovery / total_augmented) if total_augmented > 0 else 0
        passed = recovery_rate > self.thresholds.recovery_rate_min
        
        details = {
            'with_recovery': with_recovery,
            'total_augmented': total_augmented,
            'recovery_rate': recovery_rate,
            'target': f'>{self.thresholds.recovery_rate_min:.0%}',
            'actual': f'{recovery_rate:.1%}'
        }
        
        message = f"Recovery strategies: {with_recovery}/{total_augmented} ({recovery_rate:.1%})"
        if not passed:
            message += " ❌ FAIL"
        else:
            message += " ✅ PASS"
        
        return passed, message, details
    
    def check_missing_data(self) -> Tuple[bool, str, Dict]:
        """Gate 4: No missing screenshots or critical fields"""
        missing_screenshots = 0
        missing_fields = 0
        issues = []
        
        for traj in self.trajectories:
            task_id = traj.get('task_id', 'unknown')
            for step in traj.get('steps', []):
                # Check critical fields
                required = ['action_type', 'step_number']
                for field in required:
                    if field not in step or step.get(field) is None:
                        missing_fields += 1
                        issues.append(f"Missing {field} in {task_id}")
                
                # Check augmented steps have injection metadata
                if step.get('is_augmented'):
                    if not step.get('injection_type'):
                        missing_fields += 1
                        issues.append(f"Missing injection_type in {task_id}")
        
        passed = (missing_screenshots <= self.thresholds.missing_screenshots_max and
                 missing_fields <= self.thresholds.missing_fields_max)
        
        details = {
            'missing_screenshots': missing_screenshots,
            'missing_fields': missing_fields,
            'issues': issues[:10]  # Show first 10
        }
        
        message = f"Missing data: {missing_screenshots} screenshots, {missing_fields} fields"
        if not passed:
            message += " ❌ FAIL"
        else:
            message += " ✅ PASS"
        
        return passed, message, details
    
    def check_all_failure_types(self) -> Tuple[bool, str, Dict]:
        """Gate 5: All 5 failure types must be present"""
        required_types = ['TARGET_MISSING', 'MISCLICK', 'WRONG_OPERATION', 
                         'NO_STATE_CHANGE', 'LOOP']
        
        dist = self.summary.get('failure_distribution', {})
        present_types = [t for t in required_types if dist.get(t, 0) > 0]
        missing_types = [t for t in required_types if dist.get(t, 0) == 0]
        
        passed = len(missing_types) == 0
        
        details = {
            'required': required_types,
            'present': present_types,
            'missing': missing_types,
            'counts': {t: dist.get(t, 0) for t in required_types}
        }
        
        message = f"Failure types: {len(present_types)}/5 present"
        if missing_types:
            message += f" (missing: {', '.join(missing_types)})"
            message += " ❌ FAIL"
        else:
            message += " ✅ PASS"
        
        return passed, message, details
    
    def run_all_gates(self) -> Dict:
        """Run all quality gates and return full report"""
        gates = [
            ('failure_rate', self.check_failure_rate),
            ('loop_presence', self.check_loop_presence),
            ('recovery_strategies', self.check_recovery_strategies),
            ('missing_data', self.check_missing_data),
            ('all_failure_types', self.check_all_failure_types),
        ]
        
        results = {}
        all_passed = True
        
        print("\n" + "="*70)
        print("QUALITY GATE VALIDATION")
        print("="*70 + "\n")
        
        for gate_name, gate_func in gates:
            passed, message, details = gate_func()
            results[gate_name] = {
                'passed': passed,
                'message': message,
                'details': details
            }
            print(f"  {message}")
            all_passed = all_passed and passed
        
        results['overall'] = {
            'passed': all_passed,
            'gates_passed': sum(1 for r in results.values() if r.get('passed', False)),
            'gates_total': len(gates)
        }
        
        print("\n" + "="*70)
        if all_passed:
            print("  ✅ ALL GATES PASSED - Safe to scale to full dataset")
        else:
            print("  ❌ QUALITY GATE FAILED - Fix issues before scaling")
        print("="*70 + "\n")
        
        return results
    
    def generate_html_report(self, output_path: str):
        """Generate HTML quality report"""
        from datetime import datetime
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quality Gate Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .pass {{ color: #4CAF50; font-weight: bold; }}
        .fail {{ color: #f44336; font-weight: bold; }}
        .gate {{ margin: 20px 0; padding: 20px; border: 2px solid #ddd; border-radius: 5px; background: #fafafa; }}
        .gate.pass-gate {{ border-color: #4CAF50; background: #f1f8f4; }}
        .gate.fail-gate {{ border-color: #f44336; background: #fef1f0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .summary {{ background: #e3f2fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-size: 14px; }}
        .badge-success {{ background: #4CAF50; color: white; }}
        .badge-error {{ background: #f44336; color: white; }}
        details {{ margin: 10px 0; }}
        summary {{ cursor: pointer; padding: 10px; background: #e0e0e0; border-radius: 3px; }}
        summary:hover {{ background: #d0d0d0; }}
        pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚦 Quality Gate Validation Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Dataset:</strong> {Path(output_path).parent.name}</p>
        
        <div class="summary {'pass' if self.results['overall']['passed'] else 'fail'}">
            <h2>Overall Result: {'✅ PASS' if self.results['overall']['passed'] else '❌ FAIL'}</h2>
            <p><strong>{self.results['overall']['gates_passed']}/{self.results['overall']['gates_total']}</strong> gates passed</p>
            <p>{'All quality gates passed. Dataset is ready for scaling.' if self.results['overall']['passed'] else 'Quality gate failed. Please fix issues before scaling to full dataset.'}</p>
        </div>
        
        <h2>Gate Results</h2>
"""
        
        for gate_name, result in self.results.items():
            if gate_name == 'overall':
                continue
            
            status_class = 'pass-gate' if result['passed'] else 'fail-gate'
            badge_class = 'badge-success' if result['passed'] else 'badge-error'
            gate_title = gate_name.replace('_', ' ').title()
            
            html += f"""
        <div class="gate {status_class}">
            <h3>{gate_title} <span class="badge {badge_class}">{'PASS' if result['passed'] else 'FAIL'}</span></h3>
            <p><strong>{result['message']}</strong></p>
            <details>
                <summary>📊 Detailed Information</summary>
                <pre>{json.dumps(result['details'], indent=2)}</pre>
            </details>
        </div>
"""
        
        # Add distribution table
        dist = self.summary.get('failure_distribution', {})
        total_failures = sum(dist.values())
        
        html += """
        <h2>📊 Failure Type Distribution</h2>
        <table>
            <tr>
                <th>Failure Type</th>
                <th>Count</th>
                <th>Percentage</th>
                <th>Status</th>
            </tr>
"""
        
        required_types = ['TARGET_MISSING', 'MISCLICK', 'WRONG_OPERATION', 'NO_STATE_CHANGE', 'LOOP']
        for ftype in required_types:
            count = dist.get(ftype, 0)
            pct = (count / total_failures * 100) if total_failures > 0 else 0
            status = '✅' if count > 0 else '❌'
            
            # Special check for LOOP
            if ftype == 'LOOP':
                loop_pct = (count / total_failures) if total_failures > 0 else 0
                status = '✅' if loop_pct >= 0.05 else '❌'
            
            html += f"""
            <tr>
                <td><strong>{ftype}</strong></td>
                <td>{count}</td>
                <td>{pct:.1f}%</td>
                <td>{status}</td>
            </tr>
"""
        
        html += """
        </table>
        
        <h2>📈 Dataset Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
"""
        
        stats = [
            ('Total Trajectories', self.summary.get('total_trajectories', 0)),
            ('Total Steps', self.summary.get('total_steps', 0)),
            ('Clean Steps', self.summary.get('clean_steps', 0)),
            ('Augmented Steps (Failures)', self.summary.get('augmented_steps', 0)),
            ('Failure Rate', f"{self.summary.get('augmented_steps', 0) / self.summary.get('total_steps', 1) * 100:.1f}%"),
        ]
        
        for label, value in stats:
            html += f"""
            <tr>
                <td><strong>{label}</strong></td>
                <td>{value}</td>
            </tr>
"""
        
        html += """
        </table>
        
        <hr>
        <p style="text-align: center; color: #888; font-size: 12px;">
            Generated by Quality Gate Validation System<br>
            Part of Failure-Aware Web Interaction Dataset Pipeline
        </p>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ HTML report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Quality Gate Validation')
    parser.add_argument('--summary', required=True, help='Path to summary.json')
    parser.add_argument('--trajectories', required=True, help='Path to augmented_trajectories.json')
    parser.add_argument('--output', required=True, help='Path to output HTML report')
    args = parser.parse_args()
    
    # Check if files exist
    if not Path(args.summary).exists():
        print(f"❌ Error: Summary file not found: {args.summary}")
        sys.exit(1)
    
    if not Path(args.trajectories).exists():
        print(f"❌ Error: Trajectories file not found: {args.trajectories}")
        sys.exit(1)
    
    # Run quality gate
    gate = QualityGate(args.summary, args.trajectories)
    gate.results = gate.run_all_gates()
    
    # Generate HTML report
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    gate.generate_html_report(args.output)
    
    # Exit with error code if failed
    sys.exit(0 if gate.results['overall']['passed'] else 1)


if __name__ == '__main__':
    main()
