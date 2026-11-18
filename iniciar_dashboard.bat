@echo off
rem Garante que o diretorio de trabalho seja sempre a pasta onde o .bat esta localizado
cd /d "%~dp0"

title CNES DATASUS - Painel Web
color 0A
cls
echo =======================================================================
echo          Iniciando Painel Web CNES DATASUS em Streamlit...
echo =======================================================================
echo.
echo O navegador sera aberto automaticamente em instantes.
echo Para fechar a aplicacao, feche esta janela.
echo.
streamlit run app.py
pause
