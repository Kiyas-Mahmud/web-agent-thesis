@echo off
REM Generate full 1,000-task dataset (only after pilot passes quality gate)

echo ============================================================
echo STEP 5: Generate Full 1,000-Task Dataset
echo ============================================================
echo.

REM Check if pilot passed quality gate
if not exist "output\pilot_100_with_loop\quality_report.html" (
    echo ERROR: Pilot quality report not found!
    echo Please run step 4 first: run_step4_regenerate_pilot.bat
    pause
    exit /b 1
)

echo WARNING: This will generate ~7,000 steps and may take 10-15 minutes.
echo Make sure:
echo   - Pilot quality gates PASSED
echo   - You have ~10GB disk space available
echo   - You have 8GB+ RAM available
echo.
set /p CONFIRM="Continue? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled.
    exit /b 0
)

REM Activate virtual environment
call .venv-2\Scripts\activate.bat

echo.
echo ============================================================
echo Generating 1,000-task dataset...
echo ============================================================
echo.

python scripts/test_downloaded_data.py --num-tasks 1000 --output-dir output/dataset_1000_full
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate dataset
    exit /b 1
)

echo.
echo ============================================================
echo Running Quality Gate Validation on Full Dataset
echo ============================================================
echo.

python scripts/validate_quality_gate.py ^
    --summary output/dataset_1000_full/summary.json ^
    --trajectories output/dataset_1000_full/augmented_trajectories.json ^
    --output output/dataset_1000_full/quality_report.html

if %ERRORLEVEL% EQ 0 (
    echo.
    echo ============================================================
    echo SUCCESS: Full dataset quality gates PASSED!
    echo ============================================================
    echo.
    echo Full dataset statistics:
    python -c "import json; s=json.load(open('output/dataset_1000_full/summary.json')); print(f'  Total trajectories: {s[\"total_trajectories\"]}'); print(f'  Total steps: {s[\"total_steps\"]}'); print(f'  Failures: {s[\"augmented_steps\"]} ({s[\"augmented_steps\"]/s[\"total_steps\"]*100:.1f}%%)'); d=s['failure_distribution']; print('  Distribution:'); [print(f'    {k}: {v} ({v/s[\"augmented_steps\"]*100:.1f}%%)') for k,v in sorted(d.items(), key=lambda x: -x[1])]"
    echo.
    echo ============================================================
    echo Next steps:
    echo   1. Comprehensive QA (Step 6)
    echo   2. Build baseline models (Step 7)
    echo   3. Complete documentation (Step 8)
    echo   4. Write Q1 paper (Step 9)
    echo ============================================================
    echo.
) else (
    echo.
    echo ============================================================
    echo WARNING: Full dataset quality gates FAILED
    echo ============================================================
    echo.
    echo Please review the quality report:
    echo   output/dataset_1000_full/quality_report.html
    echo.
    echo Common issues at scale:
    echo   - Distribution drift (compare to pilot)
    echo   - Missing data or schema violations
    echo   - LOOP percentage dropped below 5%%
    echo.
    echo You may need to:
    echo   1. Adjust injection weights in config
    echo   2. Re-run with different random seed
    echo   3. Investigate specific failure types
    echo.
)

echo.
echo Opening quality report in browser...
start output/dataset_1000_full/quality_report.html

pause
