@echo off
cd /d "%~dp0"
title Alphas - BUILD

echo.
echo ============================================================
echo  Alphas Consultoria Digital - Gerenciador do Windows
echo  BUILD
echo ============================================================
echo.
echo Pasta atual: %CD%
echo.
echo Pressione qualquer tecla para iniciar o build...
pause

echo.
echo [1/6] Verificando Python...
python --version
if errorlevel 1 (
    echo.
    echo ERRO: Python nao encontrado!
    echo Instale em https://python.org e marque "Add to PATH"
    echo.
    pause
    exit /b 1
)

echo.
echo [2/6] Instalando dependencias...
pip install pyinstaller customtkinter pillow requests
echo.
echo Dependencias OK
echo.
pause

echo [3/6] Limpando build anterior...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist AlphasGerenciador.spec del AlphasGerenciador.spec
if exist AlphasGerenciadorSetup.spec del AlphasGerenciadorSetup.spec
echo Limpeza OK
echo.

echo [4/6] Compilando app principal (AlphasGerenciador.exe)...
echo.

python -m PyInstaller ^
  --onefile --windowed ^
  --name "AlphasGerenciador" ^
  --add-data "modules;modules" ^
  --add-data "theme.py;." ^
  --add-data "widgets.py;." ^
  --add-data "backend.py;." ^
  --add-data "updater.py;." ^
  --add-data "version.json;." ^
  --hidden-import=customtkinter ^
  --hidden-import=PIL ^
  --hidden-import=PIL._tkinter_finder ^
  --hidden-import=modules.pages ^
  --collect-all customtkinter ^
  --uac-admin ^
  --clean ^
  app.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  ERRO ao compilar o app principal!
    echo ============================================================
    echo.
    pause
    exit /b 1
)

copy /y version.json dist\version.json

echo.
echo App principal OK: dist\AlphasGerenciador.exe
echo.

echo [5/6] Compilando instalador (AlphasGerenciadorSetup.exe)...
echo.

python -m PyInstaller ^
  --onefile --windowed ^
  --name "AlphasGerenciadorSetup" ^
  --add-data "dist\AlphasGerenciador.exe;." ^
  --add-data "version.json;." ^
  --add-data "theme.py;." ^
  --hidden-import=customtkinter ^
  --collect-all customtkinter ^
  --uac-admin ^
  --clean ^
  installer.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  ERRO ao compilar o instalador!
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo.
echo [6/6] Finalizando...
echo.
echo ============================================================
echo  SUCESSO! Arquivos gerados em dist\:
echo    - AlphasGerenciador.exe      (app principal)
echo    - AlphasGerenciadorSetup.exe (instalador wizard)
echo.
echo  Para publicar uma nova versao:
echo    1. Atualize version.json
echo    2. Rode este build.bat
echo    3. Crie um GitHub Release e anexe o AlphasGerenciadorSetup.exe
echo ============================================================
echo.
pause
