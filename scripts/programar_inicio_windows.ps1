# Hadouken Zone - arranque automatico al iniciar sesion en Windows.
# Crea una tarea programada "Hadouken Zone" que lanza scripts\iniciar_bot.ps1 al entrar
# en Windows y lo reinicia si se cierra por error.
#
# Uso:     powershell -ExecutionPolicy Bypass -File .\scripts\programar_inicio_windows.ps1
# Quitar:  Unregister-ScheduledTask -TaskName "Hadouken Zone" -Confirm:$false
# Si Windows pide permisos, abre PowerShell como administrador.
$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "iniciar_bot.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-WindowStyle Minimized -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "Hadouken Zone" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Bot de ofertas Hadouken Zone (Telegram)" -Force | Out-Null
Write-Host "Tarea 'Hadouken Zone' creada: el bot arrancara al iniciar sesion."
