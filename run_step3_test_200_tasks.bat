@echo off
REM Test with 200 tasks to validate LOOP injector before scaling to 1,000

echo ============================================================
echo STEP 3: Test LOOP with 200 Tasks
echo ============================================================
echo.

REM Activate virtual environment
call .venv-2\Scripts\activate.bat

echo Generating 200-task dataset...
python scripts/test_downloaded_data.py --num-tasks 200 --output-dir output/test_200_tasks
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate dataset
    exit /b 1
)

echo.
echo ============================================================
echo Running Quality Gate Validation
echo ============================================================
echo.

python scripts/validate_quality_gate.py ^
    --summary output/test_200_tasks/summary.json ^
    --trajectories output/test_200_tasks/augmented_trajectories.json ^
    --output output/test_200_tasks/quality_report.html

if %ERRORLEVEL% EQ 0 (
    echo.
    echo ============================================================
    echo SUCCESS: All quality gates PASSED!
    echo ============================================================
    echo.
    echo Next step: Regenerate 100-task pilot with LOOP
    echo Run: run_step4_regenerate_pilot.bat
    echo.
) else (
    echo.
    echo ============================================================
    echo WARNING: Quality gates FAILED
    echo ============================================================
    echo.
    echo Please review the quality report:
    echo   output/test_200_tasks/quality_report.html
    echo.
    echo Common issues:
    echo   - LOOP percentage too low (need >=5%%)
    echo   - Failure rate outside 40-60%%
    echo.
    echo Fix issues before proceeding to full dataset generation.
    echo.
)

echo.
echo Opening quality report in browser...
start output/test_200_tasks/quality_report.html

pause
