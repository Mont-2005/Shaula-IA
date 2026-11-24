@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo ERRO: ambiente Python da Shaula nao encontrado.
    echo.
    echo Esperado:
    echo %CD%\.venv\Scripts\pythonw.exe
    echo.
    pause
    exit /b 1
)

if not exist "tests\test_ver_banco_gui.py" (
    echo ERRO: tests\ver_banco_gui.py nao encontrado.
    echo.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "tests\test_ver_banco_gui.py"

endlocal
