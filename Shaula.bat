@echo off
setlocal
cd /d "%~dp0"

title Shaula

echo.
echo ==============================
echo        INICIANDO SHAULA
echo ==============================
echo.

REM Verifica se o Ollama ja esta rodando

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/tags' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Ollama ja esta funcionando.
    goto START_SHAULA
)

echo Ollama nao esta rodando.
echo Iniciando Ollama em segundo plano...

REM Procura o Ollama

where ollama.exe >nul 2>&1

if %errorlevel%==0 (
    set "OLLAMA_EXE=ollama.exe"
    goto START_OLLAMA
)

if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    goto START_OLLAMA
)

echo.
echo ERRO: Ollama nao foi encontrado.
echo.
pause
exit /b 1

:START_OLLAMA

REM Inicia o Ollama escondido

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%OLLAMA_EXE%' -ArgumentList 'serve' -WindowStyle Hidden"

echo Aguardando Ollama iniciar...

set /a TENTATIVAS=0

:WAIT_OLLAMA

set /a TENTATIVAS+=1

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/tags' -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Ollama iniciado com sucesso.
    goto START_SHAULA
)

if %TENTATIVAS% GEQ 20 (
    echo.
    echo ERRO: O Ollama nao respondeu.
    echo.
    pause
    exit /b 1
)

timeout /t 1 /nobreak >nul
goto WAIT_OLLAMA

:START_SHAULA
echo.
echo Iniciando Shaula...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERRO: ambiente Python da Shaula nao encontrado.
    echo.
    echo Esperado:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" interface.py

echo.
echo Shaula encerrada.
pause

endlocal