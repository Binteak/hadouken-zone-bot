# Hadouken Zone - arranca el bot 24/7 (buenos dias + escaneo cada 30 min).
# Uso:  powershell -ExecutionPolicy Bypass -File .\scripts\iniciar_bot.ps1
# Para detenerlo: Ctrl+C en la ventana.
$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)
Write-Host "Hadouken Zone - iniciando bot (registro en logs\hadouken_zone.log)"
py main.py
