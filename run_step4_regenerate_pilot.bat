@echo off
REM Regenerate 100-task pilot with LOOP fixes

echo ============================================================
echo STEP 4: Regenerate 100-Task Pilot with LOOP
echo ============================================================
echo.

REM Activate virtual environment
call .venv-2\Scripts\activate.bat

echo Generating 100-task pilot dataset with LOOP fixes...
python scripts/test_downloaded_data.py --num-tasks 100 --output-dir output/pilot_100_with_loop
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate pilot dataset
    exit /b 1
)

echo.
echo ============================================================
echo Running Quality Gate Validation on Pilot
echo ============================================================
echo.

python scripts/validate_quality_gate.py ^
    --summary output/pilot_100_with_loop/summary.json ^
    --trajectories output/pilot_100_with_loop/augmented_trajectories.json ^
    --output output/pilot_100_with_loop/quality_report.html

if %ERRORLEVEL% EQ 0 (
    echo.
    echo ============================================================
    echo SUCCESS: Pilot quality gates PASSED!
    echo ============================================================
    echo.
    echo Pilot statistics:
    python -c "import json; s=json.load(open('output/pilot_100_with_loop/summary.json')); print(f'  Total steps: {s[\"total_steps\"]}'); print(f'  Failures: {s[\"augmented_steps\"]} ({s[\"augmented_steps\"]/s[\"total_steps\"]*100:.1f}%%)'); d=s['failure_distribution']; print('  Distribution:'); [print(f'    {k}: {v} ({v/s[\"augmented_steps\"]*100:.1f}%%)') for k,v in d.items()]"
    echo.
    echo Next step: Scale to 1,000 tasks
    echo Run: run_step5_generate_1000_tasks.bat
    echo.
) else (
    echo.
    echo ============================================================
    echo WARNING: Pilot quality gates FAILED
    echo ============================================================
    echo.
    echo Please review the quality report:
    echo   output/pilot_100_with_loop/quality_report.html
    echo.
    echo DO NOT PROCEED to full dataset generation until pilot passes.
    echo.
)

echo.
echo Opening quality report in browser...
start output/pilot_100_with_loop/quality_report.html

pause
