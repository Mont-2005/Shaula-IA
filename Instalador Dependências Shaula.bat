@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Instalador da Shaula

cd /d "%~dp0"

echo.
echo ==========================================
echo          INSTALADOR DA SHAULA
echo ==========================================
echo.
echo Este instalador vai preparar este computador
echo para executar a Shaula.
echo.
echo Internet sera necessaria durante a instalacao.
echo.
pause

REM =========================================================
REM 1 - VERIFICAR WINDOWS
REM =========================================================

echo.
echo [1/8] Verificando Windows...
echo.
ver


REM =========================================================
REM 2 - VERIFICAR / INSTALAR PYTHON
REM =========================================================

echo.
echo [2/8] Verificando Python...
echo.

set "PYTHON_CMD="

REM ---------------------------------------------------------
REM Primeiro tenta o Python Launcher (py).
REM O launcher e preferivel ao alias "python" da Microsoft Store.
REM ---------------------------------------------------------

py --version >nul 2>&1

if not errorlevel 1 (
    set "PYTHON_CMD=py"
    echo Python Launcher encontrado.
    py --version
    goto PYTHON_OK
)

REM ---------------------------------------------------------
REM Depois testa "python" de verdade.
REM Apenas where python nao e suficiente, pois o Windows pode
REM retornar o alias da Microsoft Store.
REM ---------------------------------------------------------

python --version >nul 2>&1

if not errorlevel 1 (
    set "PYTHON_CMD=python"
    echo Python encontrado.
    python --version
    goto PYTHON_OK
)

REM ---------------------------------------------------------
REM Python nao encontrado.
REM Tenta instalar automaticamente usando winget.
REM ---------------------------------------------------------

echo.
echo Python nao foi encontrado.
echo.

where winget >nul 2>&1

if errorlevel 1 (
    echo O winget nao esta disponivel neste computador.
    echo.
    echo Abra a pagina oficial do Python:
    echo https://www.python.org/downloads/windows/
    echo.
    echo Instale Python 3.13 ou superior e execute
    echo este instalador novamente.
    echo.
    pause
    exit /b 1
)

echo O instalador tentara instalar o Python automaticamente.
echo.

winget install --id Python.Python.3.13 -e --scope user --accept-source-agreements --accept-package-agreements

if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel instalar o Python automaticamente.
    echo.
    echo Instale o Python manualmente e execute este instalador
    echo novamente.
    echo.
    start "" "https://www.python.org/downloads/windows/"
    pause
    exit /b 1
)

echo.
echo Python instalado.
echo Atualizando as informacoes de ambiente...
echo.

REM O PATH desta janela pode nao ter sido atualizado pelo winget.
REM Tenta novamente pelo launcher e por alguns caminhos comuns.

py --version >nul 2>&1

if not errorlevel 1 (
    set "PYTHON_CMD=py"
    echo Python Launcher encontrado.
    py --version
    goto PYTHON_OK
)

python --version >nul 2>&1

if not errorlevel 1 (
    set "PYTHON_CMD=python"
    echo Python encontrado.
    python --version
    goto PYTHON_OK
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    echo Python encontrado em:
    echo %PYTHON_CMD%
    "%PYTHON_CMD%" --version
    goto PYTHON_OK
)

echo.
echo ERRO: o Python foi instalado, mas esta janela ainda
echo nao conseguiu localizar o executavel.
echo.
echo Feche esta janela e execute Instalador Dependências Shaula.bat novamente.
echo.
pause
exit /b 1


:PYTHON_OK

REM =========================================================
REM 3 - CRIAR / VALIDAR AMBIENTE VIRTUAL
REM =========================================================

echo.
echo [3/8] Preparando ambiente Python...
echo.

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    echo Ambiente virtual encontrado.
    echo Verificando se ele esta funcionando...
    echo.

    "%VENV_PYTHON%" -c "import sys; print('Python do ambiente:', sys.executable); print('Versao:', sys.version)" >nul 2>&1

    if not errorlevel 1 (
        echo Ambiente virtual valido.
        goto VENV_OK
    )

    echo.
    echo O ambiente virtual existente esta quebrado.
    echo Ele sera removido e recriado.
    echo.

    rmdir /s /q ".venv"

    if exist ".venv" (
        echo.
        echo ERRO: nao foi possivel remover o ambiente virtual antigo.
        echo Feche programas que possam estar usando .venv e tente novamente.
        echo.
        pause
        exit /b 1
    )
)

echo Criando ambiente virtual...

"%PYTHON_CMD%" -m venv .venv

if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel criar o ambiente virtual.
    echo.
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo.
    echo ERRO: o ambiente virtual foi criado, mas
    echo .venv\Scripts\python.exe nao foi encontrado.
    echo.
    pause
    exit /b 1
)

:VENV_OK

echo Ambiente virtual pronto.
"%VENV_PYTHON%" --version


REM =========================================================
REM 4 - ATUALIZAR PIP
REM =========================================================

echo.
echo [4/8] Atualizando pip...
echo.

"%VENV_PYTHON%" -m ensurepip --upgrade

if errorlevel 1 (
    echo.
    echo AVISO: ensurepip nao conseguiu atualizar o pip.
    echo Tentando continuar com o pip existente...
    echo.
)

"%VENV_PYTHON%" -m pip install --upgrade pip psutil

if errorlevel 1 (
    echo.
    echo ERRO ao atualizar o pip.
    echo.
    pause
    exit /b 1
)

echo.
echo Pip atualizado com sucesso.


REM =========================================================
REM 5 - INSTALAR DEPENDENCIAS
REM =========================================================

echo.
echo [5/8] Instalando dependencias da Shaula...
echo.

if exist "requirements.txt" (

echo.
echo [VERIFICACAO] Testando dependencias da Shaula...
"%VENV_PYTHON%" -c "import numpy; import psutil; import PySide6; import ollama; print("Dependencias principais OK.")"
if errorlevel 1 (
    echo ERRO: Uma ou mais dependencias principais nao foram instaladas.
    echo Tentando instalar novamente...
    "%VENV_PYTHON%" -m pip install --upgrade numpy psutil PySide6 ollama pymupdf opencv-python-headless
    if errorlevel 1 (
        echo ERRO: Nao foi possivel instalar as dependencias.
        pause
        exit /b 1
    )
    "%VENV_PYTHON%" -c "import numpy; import psutil; import PySide6; import ollama"
    if errorlevel 1 (
        echo ERRO: As dependencias continuam incompletas.
        pause
        exit /b 1
    )
)

    echo Encontrado requirements.txt.
    echo Instalando dependencias do projeto...
    echo.

    "%VENV_PYTHON%" -m pip install -r requirements.txt

    if errorlevel 1 (
        echo.
        echo ERRO ao instalar as dependencias do requirements.txt.
        echo.
        pause
        exit /b 1
    )

) else (

    echo requirements.txt nao encontrado.
    echo.
    echo Instalando dependencias conhecidas...
    echo.

    "%VENV_PYTHON%" -m pip install PySide6 ollama requests pymupdf opencv-python-headless

    if errorlevel 1 (
        echo.
        echo ERRO ao instalar as dependencias.
        echo.
        pause
        exit /b 1
    )
)

REM ---------------------------------------------------------
REM Garantir dependencias essenciais mesmo quando
REM requirements.txt existe e estiver incompleto.
REM ---------------------------------------------------------

echo.
echo Garantindo bibliotecas essenciais da Shaula...
echo.

"%VENV_PYTHON%" -m pip install --upgrade numpy PySide6 ollama requests pymupdf opencv-python-headless

if errorlevel 1 (
    echo.
    echo ERRO ao instalar as bibliotecas essenciais.
    echo.
    pause
    exit /b 1
)

echo Bibliotecas essenciais instaladas com sucesso.

REM ---------------------------------------------------------
REM Verificar numpy.
REM ---------------------------------------------------------

echo.
echo Verificando biblioteca numpy...
echo.

"%VENV_PYTHON%" -c "import numpy; print('numpy:', numpy.__version__)"

if errorlevel 1 (
    echo.
    echo ERRO: numpy nao pode ser importado.
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------
REM Verificar requests.
REM ---------------------------------------------------------
echo.
echo Verificando biblioteca requests...
echo.

"%VENV_PYTHON%" -c "import requests; print('requests:', requests.__version__)"

if errorlevel 1 (
    echo.
    echo ERRO: requests nao pode ser importado.
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------
REM VERIFICAR INSTALACAO
REM ---------------------------------------------------------

echo.
echo Verificando dependencias instaladas...
echo.

"%VENV_PYTHON%" -c "import PySide6; print('PySide6: OK')"

if errorlevel 1 (
    echo.
    echo ERRO: PySide6 nao pode ser importado.
    echo.
    pause
    exit /b 1
)

"%VENV_PYTHON%" -c "import ollama; print('ollama: OK')"

if errorlevel 1 (
    echo.
    echo ERRO: ollama nao pode ser importado.
    echo.
    pause
    exit /b 1
)

echo.
echo Todas as dependencias foram verificadas.
echo.


REM =========================================================
REM 6 - LOCALIZAR OLLAMA
REM =========================================================

echo.
echo [6/8] Verificando Ollama...
echo.

set "OLLAMA_EXE="

if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    goto OLLAMA_FOUND
)

where ollama >nul 2>&1

if not errorlevel 1 (
    for /f "delims=" %%A in ('where ollama') do (
        set "OLLAMA_EXE=%%A"
        goto OLLAMA_FOUND
    )
)

REM ---------------------------------------------------------
REM Tenta instalar Ollama automaticamente pelo winget.
REM ---------------------------------------------------------

echo.
echo Ollama nao encontrado.
echo.

where winget >nul 2>&1

if errorlevel 1 (
    echo O winget nao esta disponivel.
    echo.
    echo Abra a pagina oficial do Ollama:
    echo https://ollama.com/download/windows
    echo.
    echo Instale o Ollama e execute este instalador novamente.
    echo.
    start "" "https://ollama.com/download/windows"
    pause
    exit /b 1
)

echo Tentando instalar o Ollama automaticamente...
echo.

winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements

if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel instalar o Ollama automaticamente.
    echo.
    echo Instale o Ollama manualmente e execute este instalador novamente.
    echo.
    start "" "https://ollama.com/download/windows"
    pause
    exit /b 1
)

REM Procurar novamente depois da instalacao.
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    goto OLLAMA_FOUND
)

where ollama >nul 2>&1

if not errorlevel 1 (
    for /f "delims=" %%A in ('where ollama') do (
        set "OLLAMA_EXE=%%A"
        goto OLLAMA_FOUND
    )
)

echo.
echo Ollama foi instalado, mas o executavel ainda nao foi localizado.
echo Feche esta janela e execute o instalador novamente.
echo.
pause
exit /b 1


:OLLAMA_FOUND

echo Ollama encontrado:
echo %OLLAMA_EXE%
echo.

"%OLLAMA_EXE%" --version

if errorlevel 1 (
    echo.
    echo ERRO ao executar o Ollama.
    echo.
    pause
    exit /b 1
)


REM =========================================================
REM 7 - INICIAR E VERIFICAR OLLAMA
REM =========================================================

echo.
echo [7/8] Preparando Ollama...
echo.

echo Verificando se o servidor Ollama esta funcionando...
echo.

curl.exe -s --max-time 2 http://127.0.0.1:11434/api/tags >nul 2>&1

if not errorlevel 1 (
    echo.
    echo Ollama ja esta funcionando.
    goto OLLAMA_READY
)

echo.
echo Ollama nao esta rodando.
echo Iniciando Ollama em segundo plano...
echo.

start "" /min "%OLLAMA_EXE%" serve

echo Aguardando Ollama iniciar...
echo.

set /a TENTATIVAS=0

:WAIT_OLLAMA

set /a TENTATIVAS+=1

curl.exe -s --max-time 2 http://127.0.0.1:11434/api/tags >nul 2>&1

if not errorlevel 1 (
    goto OLLAMA_READY
)

if !TENTATIVAS! GEQ 30 (
    echo.
    echo ERRO: Ollama nao respondeu.
    echo.
    echo Verifique se o Ollama esta instalado corretamente.
    echo.
    pause
    exit /b 1
)

timeout /t 1 /nobreak >nul
goto WAIT_OLLAMA


:OLLAMA_READY

echo.
echo Ollama esta funcionando.
echo.

REM ---------------------------------------------------------
REM VERIFICAR MODELO
REM ---------------------------------------------------------

echo Verificando modelo da Shaula...
echo.
echo Modelo necessario:
echo qwen3.5:9b
echo.

"%OLLAMA_EXE%" list

echo.

"%OLLAMA_EXE%" list | findstr /i /c:"qwen3.5:9b" >nul 2>&1

if not errorlevel 1 (

    echo Modelo qwen3.5:9b ja esta instalado.

) else (

    echo Modelo qwen3.5:9b nao encontrado.
    echo.
    echo O modelo sera baixado agora.
    echo Isso pode levar algum tempo.
    echo.

    "%OLLAMA_EXE%" pull qwen3.5:9b

    if errorlevel 1 (
        echo.
        echo ERRO ao baixar o modelo qwen3.5:9b.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Modelo qwen3.5:9b instalado com sucesso.
)


REM =========================================================
REM 8 - VERIFICAR ARQUIVOS DA SHAULA
REM =========================================================

echo.
echo [8/8] Verificando arquivos da Shaula...
echo.

if not exist "interface.py" (
    echo.
    echo ERRO: interface.py nao encontrado.
    echo.
    echo Copie todos os arquivos do projeto da Shaula
    echo para esta pasta.
    echo.
    pause
    exit /b 1
)

echo interface.py encontrado.

if exist "tools" (
    echo Pasta tools encontrada.
) else (
    echo.
    echo AVISO: pasta tools nao encontrada.
)

echo.


REM =========================================================
REM CRIAR ATALHO
REM =========================================================

echo.
echo Criando atalho da Shaula...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$folder=(Get-Location).Path; $desktop=[Environment]::GetFolderPath('Desktop'); $bat=Join-Path $folder 'Shaula.bat'; $icon=Join-Path $folder 'Shaula.ico'; $shortcut=Join-Path $desktop 'Shaula.lnk'; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut($shortcut); $s.TargetPath=$bat; $s.WorkingDirectory=$folder; $s.IconLocation=$icon; $s.Description='Shaula'; $s.Save()"

if errorlevel 1 (
    echo.
    echo AVISO: nao foi possivel criar o atalho.
    echo.
) else (
    echo Atalho criado na Area de Trabalho.
    echo Icone: Shaula.ico
)


REM =========================================================
REM FINAL
REM =========================================================

echo.
echo ==========================================
echo       INSTALACAO CONCLUIDA
echo ==========================================
echo.
echo Python: OK
echo Ambiente virtual: OK
echo Pip: OK
echo Dependencias: OK
echo numpy: OK
echo PySide6: OK
echo ollama: OK
echo requests: OK
echo Modelo qwen3.5:9b: OK
echo Interface: OK
echo.
echo O modelo esta instalado localmente.
echo.
echo A biblioteca requests esta instalada.
echo Ela sera utilizada pela Shaula quando
echo o acesso a internet for autorizado.
echo.
echo Depois desta instalacao, a Shaula
echo pode funcionar sem internet.
echo.
echo O Ollama sera iniciado em segundo plano.
echo.
echo Um atalho para Shaula.bat foi criado na Area de Trabalho.
echo.
echo ==========================================
echo.

pause
endlocal