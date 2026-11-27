@echo off
setlocal
cd /d "%~dp0"

REM Uso:
REM   Shaula.bat           abre COM janela de console (da para acompanhar
REM                        o que acontece e ver erros)
REM   Shaula.bat oculto    abre SEM janela de console; tudo que o console
REM                        mostraria vai para
REM                        %USERPROFILE%\.shaula\logs\shaula.log
REM
REM O atalho da Area de Trabalho usa o Shaula.vbs, que chama o modo oculto.

set "OCULTO=0"
if /i "%~1"=="oculto" set "OCULTO=1"

if "%OCULTO%"=="1" goto MODO_OCULTO

title Shaula

call :PRINCIPAL

exit /b %errorlevel%

:MODO_OCULTO

set "PASTA_LOG=%USERPROFILE%\.shaula\logs"

if not exist "%PASTA_LOG%" mkdir "%PASTA_LOG%"

REM O registro vale so para esta execucao (e sobrescrito a cada abertura).
call :PRINCIPAL > "%PASTA_LOG%\shaula.log" 2>&1

exit /b %errorlevel%

:PRINCIPAL

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
if "%OCULTO%"=="0" pause
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
    if "%OCULTO%"=="0" pause
    exit /b 1
)

ping -n 2 127.0.0.1 >nul
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
    if "%OCULTO%"=="0" pause
    exit /b 1
)

".venv\Scripts\python.exe" interface.py

set "CODIGO=%errorlevel%"

echo.
echo Shaula encerrada.
if "%OCULTO%"=="0" pause

exit /b %CODIGO%
