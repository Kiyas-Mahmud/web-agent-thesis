@echo off
echo ========================================
echo DATASET GENERATION - 1,000 TASKS
echo ========================================
echo.
echo IMPORTANT: This will run for 15-20 minutes
echo Close VS Code before running to avoid conflicts
echo.
echo Press Ctrl+C to cancel, or
pause

REM Activate virtual environment
call .venv-2\Scripts\activate.bat

REM Run batch generation
python generate_dataset_batch.py

echo.
echo ========================================
echo Generation complete!
echo ========================================
pause
