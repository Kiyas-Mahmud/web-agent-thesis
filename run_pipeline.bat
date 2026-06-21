@echo off
REM Master script for dataset generation pipeline

echo ============================================================
echo Failure-Aware Web Dataset Generation Pipeline
echo ============================================================
echo.
echo This pipeline will:
echo   1. Test LOOP injector with 200 tasks
echo   2. Regenerate 100-task pilot with LOOP fixes
echo   3. Scale to 1,000-task full dataset
echo.
echo Current Status:
echo   [X] Step 1: LOOP injector fixed (state_after loading)
echo   [X] Step 2: Quality gate validation script created
echo   [ ] Step 3: Test with 200 tasks
echo   [ ] Step 4: Regenerate pilot (100 tasks)
echo   [ ] Step 5: Generate full dataset (1,000 tasks)
echo.
echo ============================================================
echo.

:menu
echo Choose an action:
echo   1. Test with 200 tasks (Step 3)
echo   2. Regenerate pilot (Step 4)
echo   3. Generate full 1,000-task dataset (Step 5)
echo   4. View quality reports
echo   5. Exit
echo.
set /p CHOICE="Enter choice (1-5): "

if "%CHOICE%"=="1" goto step3
if "%CHOICE%"=="2" goto step4
if "%CHOICE%"=="3" goto step5
if "%CHOICE%"=="4" goto reports
if "%CHOICE%"=="5" goto end
echo Invalid choice. Please try again.
goto menu

:step3
echo.
echo Running Step 3: Test with 200 tasks...
call run_step3_test_200_tasks.bat
goto menu

:step4
echo.
echo Running Step 4: Regenerate pilot...
call run_step4_regenerate_pilot.bat
goto menu

:step5
echo.
echo Running Step 5: Generate 1,000 tasks...
call run_step5_generate_1000_tasks.bat
goto menu

:reports
echo.
echo Available quality reports:
echo.
if exist "output\test_200_tasks\quality_report.html" (
    echo   [X] 200-task test: output\test_200_tasks\quality_report.html
) else (
    echo   [ ] 200-task test: Not generated yet
)
if exist "output\pilot_100_with_loop\quality_report.html" (
    echo   [X] 100-task pilot: output\pilot_100_with_loop\quality_report.html
) else (
    echo   [ ] 100-task pilot: Not generated yet
)
if exist "output\dataset_1000_full\quality_report.html" (
    echo   [X] 1,000-task full: output\dataset_1000_full\quality_report.html
) else (
    echo   [ ] 1,000-task full: Not generated yet
)
echo.
set /p OPEN="Open a report? (Enter filename or press Enter to skip): "
if not "%OPEN%"=="" start %OPEN%
goto menu

:end
echo.
echo ============================================================
echo Pipeline Status Summary
echo ============================================================
echo.

REM Check completion status
set STEP3_DONE=0
set STEP4_DONE=0
set STEP5_DONE=0

if exist "output\test_200_tasks\summary.json" set STEP3_DONE=1
if exist "output\pilot_100_with_loop\summary.json" set STEP4_DONE=1
if exist "output\dataset_1000_full\summary.json" set STEP5_DONE=1

if %STEP3_DONE%==1 (
    echo [X] Step 3: 200-task test completed
) else (
    echo [ ] Step 3: 200-task test - NOT DONE
)

if %STEP4_DONE%==1 (
    echo [X] Step 4: 100-task pilot completed
) else (
    echo [ ] Step 4: 100-task pilot - NOT DONE
)

if %STEP5_DONE%==1 (
    echo [X] Step 5: 1,000-task dataset completed
) else (
    echo [ ] Step 5: 1,000-task dataset - NOT DONE
)

echo.
if %STEP5_DONE%==1 (
    echo ============================================================
    echo DATASET GENERATION COMPLETE!
    echo ============================================================
    echo.
    echo Next steps:
    echo   6. Comprehensive QA (automated + manual)
    echo   7. Build baseline models (rule-based + vision)
    echo   8. Complete documentation and dataset card
    echo   9. Write Q1 journal paper
    echo.
    echo See TODO_COMPLETE.md for detailed checklist.
    echo.
) else (
    echo Complete the remaining steps to generate the full dataset.
    echo.
)

pause
