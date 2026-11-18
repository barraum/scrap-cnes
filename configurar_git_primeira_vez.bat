@echo off
rem Garante que o diretorio de trabalho seja sempre a pasta do projeto
cd /d "%~dp0"

title CNES DATASUS - Configuracao Inicial do Git
color 0B
cls
echo =======================================================================
echo          CONFIGURACAO INICIAL DO REPOSITORIO GIT (1a VEZ)
echo =======================================================================
echo.
echo Este assistente vai preparar e enviar seu projeto para o GitHub
echo de forma 100%% automatica, sem precisar digitar comandos complexos.
echo.
echo =======================================================================
echo.

rem 1. Verifica se o Git esta instalado no computador
where git >nul 2>nul
if %errorlevel% neq 0 goto nogit

echo [OK] Git detectado com sucesso!
echo.
goto passogithub

:nogit
color 0C
echo [ERRO] O Git ainda nao foi detectado no seu computador!
echo.
echo Para continuar, instale o Git for Windows:
echo 1. Acesse o site oficial: https://git-scm.com/download/win
echo 2. Baixe o instalador 64-bit e instale com as opcoes padrao.
echo 3. Apos instalar, feche esta janela e execute este arquivo novamente.
echo.
set /p abrir="Deseja abrir a pagina de download do Git agora? [S/N]: "
if /i "%abrir%"=="S" start https://git-scm.com/download/win
echo.
echo Pressione qualquer tecla para fechar...
pause >nul
exit /b

:passogithub
echo -----------------------------------------------------------------------
echo PASSO 1: CRIAR O REPOSITORIO NO GITHUB
echo -----------------------------------------------------------------------
echo 1. Abra o seu navegador e acesse: https://github.com/new
echo 2. Em "Repository name", digite: cnes-mp (ou o nome que preferir).
echo 3. Escolha Public ou Private (recomendado Public para compartilhar).
echo 4. ATENCAO: Deixe DESMARCADAS as opcoes README, .gitignore e License.
echo 5. Clique no botao verde "Create repository".
echo.
set /p abrir_gh="Deseja abrir https://github.com/new no navegador agora? [S/N]: "
if /i "%abrir_gh%"=="S" start https://github.com/new
echo.
echo -----------------------------------------------------------------------
echo PASSO 2: COLAR O LINK DO REPOSITORIO
echo -----------------------------------------------------------------------
echo Copie a URL HTTPS gerada pelo GitHub (ex: https://github.com/usuario/cnes-mp.git)
echo.
set /p repo_url="Cole a URL do seu repositorio GitHub aqui: "

if "%repo_url%"=="" goto nourl

cls
echo =======================================================================
echo EXECUTANDO A PUBLICACAO INICIAL...
echo =======================================================================
echo.

echo 1/5. Compactando o banco de dados historico para deploy na nuvem...
python -c "from cnes_core.database import CNESDatabase; p = CNESDatabase.compress_db(); print('Snapshot gerado com sucesso:', p)"
if %errorlevel% neq 0 (
    color 0C
    echo [ERRO] Falha ao compactar o banco de dados.
    pause
    exit /b
)
echo.

echo 2/5. Inicializando o repositorio local...
git init
git branch -M main
for /f "delims=" %%i in ('git config user.name 2^>nul') do set git_name=%%i
for /f "delims=" %%i in ('git config user.email 2^>nul') do set git_email=%%i
if "%git_name%"=="" (
    set /p git_name="Informe seu Nome para os commits do Git: "
    git config --global user.name "%git_name%"
)
if "%git_email%"=="" (
    set /p git_email="Informe seu E-mail do GitHub para os commits do Git: "
    git config --global user.email "%git_email%"
)
echo.

echo 3/5. Vinculando ao GitHub...
git remote remove origin >nul 2>nul
git remote add origin "%repo_url%"
echo.

echo 4/5. Empacotando arquivos do projeto...
git add .
git commit -m "Versao Inicial - Painel CNES MP Analytics"
echo.

echo 5/5. Enviando para o GitHub (pode abrir uma janela solicitando login)...
git push -u origin main

if %errorlevel% equ 0 goto sucesso
goto falha

:nourl
color 0C
echo.
echo [ERRO] Nenhuma URL informada. Operacao cancelada.
echo.
pause
exit /b

:sucesso
color 0A
echo.
echo =======================================================================
echo  [SUCESSO] Seu projeto foi publicado com sucesso no GitHub!
echo =======================================================================
echo.
echo Agora, para disponibilizar o link para a equipe do MP:
echo 1. Acesse: https://share.streamlit.io
echo 2. Clique em "New app" e selecione o repositorio criado.
echo 3. Em "Main file path", confirme "app.py" e clique em "Deploy!".
echo.
pause
exit /b

:falha
color 0C
echo.
echo =======================================================================
echo  [ATENCAO] Ocorreu uma pendencia no envio para o GitHub.
echo =======================================================================
echo.
echo Verifique se a URL esta correta e se a autorizacao de login do GitHub
echo foi confirmada no navegador. Depois tente novamente.
echo.
pause
exit /b
