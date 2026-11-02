# ---------------------------------------------------------------------------
# Hadouken Zone - migracion unica de amazon-deals-bot a hadouken-zone
#
#  1. Mueve todo lo que no forma parte del producto a una copia de seguridad
#     FUERA del proyecto:  Proyectos\hadouken-zone_respaldo_<fecha>\
#  2. Rehace .env a partir de .env.example conservando tus valores
#     (token, canal, DRY_RUN...). Copia del .env anterior en el respaldo.
#  3. Renombra la carpeta del proyecto a "hadouken-zone".
#  4. Se borra a si mismo.
#
# Uso (desde la carpeta del proyecto):
#   powershell -ExecutionPolicy Bypass -File .\scripts\migrar_a_hadouken_zone.ps1
# ---------------------------------------------------------------------------
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$parent = Split-Path -Parent $root
$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$backup = Join-Path $parent "hadouken-zone_respaldo_$stamp"
Set-Location -Path $root

$manifest = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
@(
    ".env.example",
    ".gitignore",
    "README.md",
    "branding\README.md",
    "branding\fuentes\Inter-Bold.otf",
    "branding\fuentes\Inter-ExtraBold.otf",
    "branding\fuentes\InterDisplay-BlackItalic.otf",
    "branding\fuentes\LICENCIA_OFL.txt",
    "branding\mascota\mascota_cabeza.png",
    "branding\mascota\mascota_hadouken.png",
    "branding\originales\avatar_original_400x400.jpg",
    "branding\originales\banner_original_600x200.jpg",
    "branding\telegram\avatar\avatar_morado_640.png",
    "branding\telegram\avatar\avatar_naranja_640.png",
    "branding\telegram\cabeceras\cabecera_buenos_dias.png",
    "branding\telegram\cabeceras\cabecera_chollo_del_dia.png",
    "branding\telegram\cabeceras\cabecera_especial_ps5.png",
    "branding\telegram\cabeceras\cabecera_especial_switch.png",
    "branding\telegram\cabeceras\cabecera_oferta_flash.png",
    "branding\telegram\cabeceras\cabecera_top_semana.png",
    "branding\telegram\publicaciones\bienvenida_1280x720.png",
    "branding\telegram\stickers\sticker_agotado.png",
    "branding\telegram\stickers\sticker_chollazo.png",
    "branding\telegram\stickers\sticker_corre.png",
    "branding\telegram\stickers\sticker_minimo_historico.png",
    "branding\telegram\tarjetas_ejemplo\tarjeta_ejemplo_ps5.jpg",
    "branding\telegram\tarjetas_ejemplo\tarjeta_ejemplo_switch.jpg",
    "docs\CHANGELOG.md",
    "docs\contexto_hadouken.md",
    "hadouken_zone\__init__.py",
    "hadouken_zone\affiliate.py",
    "hadouken_zone\amazon\__init__.py",
    "hadouken_zone\amazon\client.py",
    "hadouken_zone\amazon\parser.py",
    "hadouken_zone\amazon\scraper.py",
    "hadouken_zone\cards.py",
    "hadouken_zone\config.py",
    "hadouken_zone\logging_setup.py",
    "hadouken_zone\messages.py",
    "hadouken_zone\models.py",
    "hadouken_zone\pipeline.py",
    "hadouken_zone\rules.py",
    "hadouken_zone\scheduler.py",
    "hadouken_zone\storage.py",
    "hadouken_zone\telegram.py",
    "main.py",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
    "scripts\iniciar_bot.ps1",
    "scripts\migrar_a_hadouken_zone.ps1",
    "scripts\programar_inicio_windows.ps1",
    "tests\conftest.py",
    "tests\fixtures\amazon_busqueda.html",
    "tests\fixtures\amazon_captcha.html",
    "tests\fixtures\amazon_ficha.html",
    "tests\fixtures\amazon_ficha_no_disponible.html",
    "tests\test_affiliate_and_messages.py",
    "tests\test_amazon_parser.py",
    "tests\test_cards_and_telegram.py",
    "tests\test_pipeline.py",
    "tests\test_rules.py",
    "tests\test_scheduler.py",
    "tests\test_storage.py",
    "tools\branding\generar_disenos.py",
    "tools\branding\hzlib.py",
    "tools\branding\mejorar_mascota.py"
) | ForEach-Object { [void]$manifest.Add($_) }

# Elementos de la raiz que nunca se tocan
$keep = @(".env", ".venv", "venv", ".git")

Write-Host ""
Write-Host "1) Limpiando el proyecto (respaldo en $backup)"
$moved = 0
Get-ChildItem -LiteralPath $root -Force | Where-Object { $keep -notcontains $_.Name } | ForEach-Object {
    $items = if ($_.PSIsContainer) { Get-ChildItem -LiteralPath $_.FullName -Recurse -File -Force } else { @($_) }
    foreach ($file in $items) {
        $rel = $file.FullName.Substring($root.Length + 1)
        if ($manifest.Contains($rel)) { continue }
        $dest = Join-Path $backup $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        Move-Item -LiteralPath $file.FullName -Destination $dest -Force
        Write-Host "   - $rel"
        $moved++
    }
}
# Carpetas vacias (de la mas profunda a la mas alta)
Get-ChildItem -LiteralPath $root -Recurse -Directory -Force |
    Where-Object { $keep -notcontains ($_.FullName.Substring($root.Length + 1).Split('\')[0]) } |
    Sort-Object { $_.FullName.Length } -Descending |
    Where-Object { -not (Get-ChildItem -LiteralPath $_.FullName -Force) } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
Write-Host "   $moved archivos movidos al respaldo."

Write-Host ""
Write-Host "2) Actualizando .env con las variables nuevas"
$envPath = Join-Path $root ".env"
$examplePath = Join-Path $root ".env.example"
if (Test-Path -LiteralPath $envPath) {
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    Copy-Item -LiteralPath $envPath -Destination (Join-Path $backup ".env.anterior")
    $old = @{}
    foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') { $old[$matches[1]] = $matches[2].Trim() }
    }
    $out = foreach ($line in Get-Content -LiteralPath $examplePath -Encoding UTF8) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$' -and $old.ContainsKey($matches[1])) {
            "$($matches[1])=$($old[$matches[1]])"
        } else { $line }
    }
    [IO.File]::WriteAllLines($envPath, [string[]]$out, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "   .env actualizado (copia del anterior en el respaldo)."
} else {
    Copy-Item -LiteralPath $examplePath -Destination $envPath
    Write-Host "   No habia .env: creado desde .env.example. Rellena tus claves."
}

Write-Host ""
Write-Host "3) Renombrando la carpeta a hadouken-zone"
Remove-Item -LiteralPath $PSCommandPath -Force
Set-Location -Path $parent
[Environment]::CurrentDirectory = $parent   # Windows no deja renombrar la carpeta en uso
$target = Join-Path $parent "hadouken-zone"
if ((Split-Path -Leaf $root) -eq "hadouken-zone") {
    Write-Host "   La carpeta ya se llama hadouken-zone."
} elseif (Test-Path -LiteralPath $target) {
    Write-Host "   AVISO: ya existe $target. Renombra la carpeta a mano."
} else {
    try {
        Rename-Item -LiteralPath $root -NewName "hadouken-zone"
        Write-Host "   Listo: $target"
    } catch {
        Write-Host "   AVISO: no se pudo renombrar (alguna ventana o programa tiene la carpeta abierta)."
        Write-Host "   Cierralo y renombra la carpeta a mano a: hadouken-zone"
    }
}
Write-Host ""
Write-Host "Migracion completada."
