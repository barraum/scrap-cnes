@echo off
rem Garante que o diretorio de trabalho seja sempre a pasta do projeto
cd /d "%~dp0"

title CNES DATASUS - Publicar Atualizacao na Nuvem
color 0A
cls
echo =======================================================================
echo          PUBLICAR ATUALIZACAO NA NUVEM (STREAMLIT CLOUD)
echo =======================================================================
echo.
echo Este script atualiza o snapshot compactado do seu banco de dados
echo local e envia tudo automaticamente para o GitHub / Streamlit Cloud.
echo.
echo =======================================================================
echo.

rem 1. Verifica se o Git esta instalado
where git >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERRO] O comando git nao foi encontrado. Execute configurar_git_primeira_vez.bat primeiro.
    pause
    exit /b
)

rem 2. Compacta o banco de dados
echo 1/4. Compactando o banco de dados local para deploy na nuvem...
python -c "from cnes_core.database import CNESDatabase; p = CNESDatabase.compress_db(); print('Snapshot gerado com sucesso:', p)"
if %errorlevel% neq 0 (
    color 0C
    echo [ERRO] Falha ao compactar o banco de dados.
    pause
    exit /b
)
echo.

rem 3. Solicita nota da atualizacao
set /p msg="Digite uma descricao para esta atualizacao (ou pressione Enter para padrao): "
if "%msg%"=="" (
    set msg=Atualizacao automatica da base CNES - %date% %time%
)
echo.

rem 4. Adiciona ao Git
echo 2/4. Adicionando arquivos alterados...
git add .
echo.

rem 5. Cria o commit
echo 3/4. Registrando versao...
git commit -m "%msg%"
if %errorlevel% neq 0 (
    echo [INFO] Nenhuma alteracao nova detectada para envio.
    pause
    exit /b
)
echo.

rem 6. Envia para o GitHub
echo 4/4. Enviando atualizacao para o GitHub...
git push

if %errorlevel% equ 0 (
    color 0A
    echo.
    echo =======================================================================
    echo  [SUCESSO] Atualizacao enviada com sucesso!
    echo =======================================================================
    echo.
    echo Em cerca de 1 a 2 minutos, o Streamlit Cloud na nuvem sera
    echo atualizado automaticamente com os novos dados para a equipe do MP.
    echo.
) else (
    color 0C
    echo.
    echo [ATENCAO] Houve um erro ao enviar para o GitHub. Verifique sua conexao
    echo ou credenciais do Git.
)

pause
