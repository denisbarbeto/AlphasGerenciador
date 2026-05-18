@echo off
set EXE=%~dp0dist\AlphasGerenciador.exe
if not exist "%EXE%" (
    echo  EXE nao encontrado. Execute build.bat primeiro (duplo clique, SEM admin).
    pause & exit /b 1
)
echo Iniciando como Administrador...
powershell -Command "Start-Process '%EXE%' -Verb RunAs"
