@echo off
echo ========================================
echo 10K DATASET GENERATION - FIXED VERSION
echo ========================================
echo.
echo Target: 10,000 steps with NO DUPLICATES
echo Estimated time: 20-30 minutes
echo.
echo IMPORTANT: Run this outside VS Code
echo.
echo Press Ctrl+C to cancel, or
pause

REM Activate virtual environment
call .venv-2\Scripts\activate.bat

REM Run generation
python generate_10k_dataset.py

echo.
echo ========================================
echo Generation complete! Check logs above.
echo ========================================
pause
