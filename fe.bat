@echo off
REM Ferro & Engrenagem: menu da ferramenta (tools\fe.ps1). Duplo clique, ou: fe.bat tudo / fe.bat modelos / fe.bat mod
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\fe.ps1" %*
if "%~1"=="" pause
