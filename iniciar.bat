@echo off
rem Garante que o diretorio de trabalho seja sempre a pasta onde o .bat esta localizado
cd /d "%~dp0"

title CNES DATASUS - Extrator & Historico
color 0A
cls
echo =======================================================================
echo               CNES DATASUS - Extrator & Historico
echo =======================================================================
echo.
echo  [1] Abrir Painel Web (Streamlit Dashboard)
echo  [2] Consultar CNES via Linha de Comando (CLI + Excel)
echo  [3] Listar Historico Local de CNES
echo  [4] Sair
echo.
echo =======================================================================
set /p opcao="Escolha uma opcao (1-4) e pressione Enter: "

if "%opcao%"=="1" goto web
if "%opcao%"=="2" goto cli
if "%opcao%"=="3" goto list
if "%opcao%"=="4" goto end

:web
cls
echo.
echo Iniciando o Dashboard Web em Streamlit...
echo Aguarde um instante, o navegador sera aberto automaticamente.
echo.
streamlit run app.py
pause
goto end

:cli
cls
echo.
echo -----------------------------------------------------------------------
echo Consulta Rapida de CNES via Terminal
echo -----------------------------------------------------------------------
echo.
set /p cnes_code="Digite o codigo CNES (ex: 2705982): "
if "%cnes_code%"=="" goto end
echo.
echo Executando extracao e gerando planilha Excel...
python cnes_cli.py --cnes %cnes_code% --export
echo.
pause
goto end

:list
cls
echo.
python cnes_cli.py --list
echo.
pause
goto end

:end
