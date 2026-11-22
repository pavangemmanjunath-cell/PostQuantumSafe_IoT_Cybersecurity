@echo off
setlocal EnableExtensions
REM ===================================================================================================================
REM  start_all.bat - Windows launcher for TIPPSS SafeGuard-PQ v0.3.0: web application, data pipeline with the
REM  reproduction check, tests, figures and Word summary.
REM
REM    start_all.bat                   interactive menu (pauses before it returns to the menu)
REM    start_all.bat app               [1] web application: backend :8000, frontend :5173 (scripts\dev.ps1)
REM    start_all.bat pipeline          [2] full data pipeline with checks: benchmarks\run_all.py --check
REM    start_all.bat pipeline-quick    [3] the same with --skip-slow (leaves out E8, about 100 s)
REM    start_all.bat tests             [4] ruff, pytest, frontend type check and build, Playwright browser tests
REM    start_all.bat docs              [5] result figures, schematic figure PDFs and the Word summary only
REM
REM  With an argument the launcher runs that option, does not pause and exits with the first failing exit code.
REM  Options 2-5 create backend\.venv (pip install -e "backend[dev,benchmark]") when it is missing; option 1 leaves
REM  that to scripts\dev.ps1. Every path is quoted because the repository path may contain spaces.
REM
REM  Note: the old v0 launchers kept in the legacy archive (TIPPSS_SafeGuard-PQ_v0_legacy_archive\03_v0_scripts:
REM  start_all.bat, start_dashboard.bat, run.bat) start the retired n8n + Streamlit prototype, not this application.
REM ===================================================================================================================
cd /d "%~dp0"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%backend\.venv\Scripts\python.exe"
title TIPPSS SafeGuard-PQ launcher

echo.
echo  ===================================================================
echo   TIPPSS SafeGuard-PQ v0.3.0  -  Windows launcher
echo   Repository: "%ROOT%"
echo  ===================================================================

set "INTERACTIVE=0"
set "TRIES=0"
set "CHOICE=%~1"
if "%CHOICE%"=="" goto :menu
goto :dispatch

:menu
set "INTERACTIVE=1"
set /a TRIES+=1
if %TRIES% GTR 3 goto :usage
echo.
echo    [1] Start the web application (backend + frontend, Research Results tab)
echo    [2] Rerun the full data pipeline with checks
echo    [3] Quick pipeline (--skip-slow, without E8)
echo    [4] Run all tests (ruff, pytest, type check, build, Playwright)
echo    [5] Rebuild figures and the Word summary only
echo    [0] Exit
echo.
set "CHOICE="
set /p "CHOICE=  Select an option [0-5]: "

:dispatch
if "%CHOICE%"=="1" set "CHOICE=app"
if "%CHOICE%"=="2" set "CHOICE=pipeline"
if "%CHOICE%"=="3" set "CHOICE=pipeline-quick"
if "%CHOICE%"=="4" set "CHOICE=tests"
if "%CHOICE%"=="5" set "CHOICE=docs"
if "%CHOICE%"=="0" goto :quit
if /i "%CHOICE%"=="exit" goto :quit
if /i "%CHOICE%"=="help" goto :usage
if /i "%CHOICE%"=="-h" goto :usage
if /i "%CHOICE%"=="--help" goto :usage
set "RC=0"
set "FIRST_FAIL="
if /i "%CHOICE%"=="app" goto :run_app
if /i "%CHOICE%"=="pipeline" goto :run_pipeline
if /i "%CHOICE%"=="pipeline-quick" goto :run_pipeline_quick
if /i "%CHOICE%"=="tests" goto :run_tests
if /i "%CHOICE%"=="docs" goto :run_docs
echo.
echo   Unknown option "%CHOICE%".
if "%INTERACTIVE%"=="1" goto :menu
goto :usage

:run_app
set "TRIES=0"
call :do_app
goto :done
:run_pipeline
set "TRIES=0"
call :do_pipeline full
goto :done
:run_pipeline_quick
set "TRIES=0"
call :do_pipeline quick
goto :done
:run_tests
set "TRIES=0"
call :do_tests
goto :done
:run_docs
set "TRIES=0"
call :do_docs
goto :done

:done
echo.
echo  -------------------------------------------------------------------
if "%RC%"=="0" echo   RESULT: %CHOICE% succeeded - exit code 0
if not "%RC%"=="0" echo   RESULT: %CHOICE% FAILED - exit code %RC% - first failing step: %FIRST_FAIL%
echo  -------------------------------------------------------------------
if "%INTERACTIVE%"=="1" (
    echo.
    pause
    goto :menu
)
exit /b %RC%

:quit
exit /b 0

:usage
echo.
echo   Usage: start_all.bat [app ^| pipeline ^| pipeline-quick ^| tests ^| docs]
echo          without an argument an interactive menu is shown.
exit /b 2

REM ------------------------------------------------------------------------------------------------- subroutines

:result
REM  %1 = step description, %2 = exit code. Prints OK / FAIL and keeps the first failing exit code in RC.
if "%~2"=="0" echo   [ OK ] %~1
if "%~2"=="0" exit /b 0
echo   [FAIL] %~1 - exit code %~2
if "%RC%"=="0" set "RC=%~2"
if not defined FIRST_FAIL set "FIRST_FAIL=%~1"
exit /b 0

:ensure_venv
REM  Create backend\.venv with the dev and benchmark extras when it is missing.
if exist "%VENV_PY%" exit /b 0
echo.
echo  [setup] backend\.venv not found: creating it and installing backend[dev,benchmark]
set "BASE_PY="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "BASE_PY=python"
if defined BASE_PY goto :ensure_venv_create
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "BASE_PY=py -3"
if not defined BASE_PY goto :ensure_venv_nopython
:ensure_venv_create
%BASE_PY% -m venv "%ROOT%backend\.venv"
call :result "Create backend\.venv with %BASE_PY%" %ERRORLEVEL%
if not "%RC%"=="0" exit /b 1
"%VENV_PY%" -m pip install --upgrade pip
call :result "Upgrade pip in backend\.venv" %ERRORLEVEL%
if not "%RC%"=="0" exit /b 1
"%VENV_PY%" -m pip install -e "backend[dev,benchmark]"
call :result "pip install -e backend[dev,benchmark]" %ERRORLEVEL%
if not "%RC%"=="0" exit /b 1
exit /b 0
:ensure_venv_nopython
call :result "Find Python 3.11 or newer on PATH to create backend\.venv - install it from https://www.python.org/downloads/" 9009
exit /b 1

:find_figures_python
REM  FIG_PY = Anaconda Python (working matplotlib) when present, else the venv Python.
set "FIG_PY=%VENV_PY%"
if exist "%USERPROFILE%\anaconda3\python.exe" set "FIG_PY=%USERPROFILE%\anaconda3\python.exe"
echo   figures Python: "%FIG_PY%"
exit /b 0

:do_app
echo.
echo  [step] Web application: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev.ps1
echo         (creates backend\.venv and installs the frontend packages on first run)
echo.
echo         API and its docs   http://127.0.0.1:8000/docs
echo         Web application    http://127.0.0.1:5173
echo         Research Results   http://127.0.0.1:5173/#results
echo.
echo         Press Ctrl+C in this window to stop both servers; a non-zero exit code is then expected.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\dev.ps1"
call :result "Web application - scripts\dev.ps1" %ERRORLEVEL%
exit /b 0

:do_pipeline
call :ensure_venv
if not "%RC%"=="0" exit /b 0
call :find_figures_python
set "CIC_DIR="
for %%I in ("%ROOT%..\Input") do set "CIC_CANDIDATE=%%~fI"
if exist "%CIC_CANDIDATE%\" set "CIC_DIR=%CIC_CANDIDATE%"
if defined CIC_DIR echo   CICIoMT2024 test split: "%CIC_DIR%"
if not defined CIC_DIR echo   CICIoMT2024 test split: not found next to the repository - E6 and E10 P1/P2 are skipped
set "SLOW="
if /i "%~1"=="quick" set "SLOW=--skip-slow"
echo.
echo  [step] Data pipeline: benchmarks\run_all.py --check %SLOW%
if defined CIC_DIR goto :pipeline_with_cic
"%VENV_PY%" benchmarks\run_all.py --check %SLOW% --figures-python "%FIG_PY%"
call :result "Data pipeline with checks - benchmarks\run_all.py --check %SLOW%" %ERRORLEVEL%
exit /b 0
:pipeline_with_cic
"%VENV_PY%" benchmarks\run_all.py --check %SLOW% --cic-test-dir "%CIC_DIR%" --figures-python "%FIG_PY%"
call :result "Data pipeline with checks - benchmarks\run_all.py --check %SLOW% --cic-test-dir" %ERRORLEVEL%
exit /b 0

:do_tests
call :ensure_venv
if not "%RC%"=="0" exit /b 0
if exist "frontend\node_modules\" goto :tests_run
echo.
echo  [setup] frontend\node_modules not found: npm ci
call npm --prefix frontend ci
call :result "npm ci in frontend" %ERRORLEVEL%
if not "%RC%"=="0" exit /b 0
:tests_run
echo.
echo  [step] Lint, CI form: ruff check src tests (in backend)
pushd "%ROOT%backend"
"%VENV_PY%" -m ruff check src tests
call :result "Lint, CI form - ruff check src tests" %ERRORLEVEL%
popd
echo.
echo  [step] Lint, benchmarks and scripts: ruff check benchmarks scripts --config backend\pyproject.toml
"%VENV_PY%" -m ruff check benchmarks scripts --config backend\pyproject.toml
call :result "Lint - ruff check benchmarks scripts" %ERRORLEVEL%
echo.
echo  [step] Backend tests: pytest (in backend)
pushd "%ROOT%backend"
"%VENV_PY%" -m pytest -q
call :result "Backend tests - pytest" %ERRORLEVEL%
popd
echo.
echo  [step] Frontend type check: npm --prefix frontend run typecheck
call npm --prefix frontend run typecheck
call :result "Frontend type check - npm run typecheck" %ERRORLEVEL%
echo.
echo  [step] Frontend build: npm --prefix frontend run build
call npm --prefix frontend run build
call :result "Frontend build - npm run build" %ERRORLEVEL%
echo.
echo  [step] Browser end-to-end tests: npx playwright test (in frontend)
pushd "%ROOT%frontend"
call npx playwright test
call :result "Browser end-to-end tests - npx playwright test" %ERRORLEVEL%
popd
exit /b 0

:do_docs
call :ensure_venv
if not "%RC%"=="0" exit /b 0
call :find_figures_python
echo.
echo  [step] Result figures: benchmarks\make_figures.py
"%FIG_PY%" -I benchmarks\make_figures.py
call :result "Result figures - benchmarks\make_figures.py" %ERRORLEVEL%
if not "%RC%"=="0" exit /b 0
where node >nul 2>nul
if errorlevel 1 goto :docs_no_node
if not exist "frontend\node_modules\playwright\" goto :docs_no_playwright
echo.
echo  [step] Schematic figure PDFs: node scripts\svg_to_pdf.cjs
node scripts\svg_to_pdf.cjs
call :result "Schematic figure PDFs - scripts\svg_to_pdf.cjs" %ERRORLEVEL%
if not "%RC%"=="0" exit /b 0
goto :docs_word
:docs_no_playwright
echo   [skip] Schematic figure PDFs: frontend\node_modules\playwright not found
:docs_word
echo.
echo  [step] Word summary: scripts\build_release3_docx.py
"%VENV_PY%" scripts\build_release3_docx.py
call :result "Word summary - scripts\build_release3_docx.py" %ERRORLEVEL%
exit /b 0
:docs_no_node
call :result "Find Node.js for the schematic figure PDFs and the Word summary - install it from https://nodejs.org" 9009
exit /b 0
