<#
.SYNOPSIS
  Installs the mod into the game's Mods folder for testing.

.DESCRIPTION
  Default: creates a directory junction  <game>\Mods\ForgedInAshes -> <repo>\Mods\ForgedInAshes
  (no admin rights needed; edits in the repo show up in the game immediately).
  -Copy      copies the files instead of linking (e.g. to test what players get).
  -Uninstall removes the junction or the copied folder. Never touches anything else.
  Game path comes from tools\game_path.txt.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\install.ps1
  powershell -ExecutionPolicy Bypass -File tools\install.ps1 -Uninstall
#>
param([switch]$Copy, [switch]$Uninstall)
$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repo 'Mods\ForgedInAshes'
$pathFile = Join-Path $PSScriptRoot 'game_path.txt'
if (-not (Test-Path $pathFile)) { throw "Missing $pathFile" }
$game = (Get-Content $pathFile -TotalCount 1).Trim()
$mods = Join-Path $game 'Mods'
if (-not (Test-Path (Join-Path $game 'Data\Config'))) { throw "Not a 7DTD install: $game" }
$dst = Join-Path $mods 'ForgedInAshes'

function Remove-ModInstall {
    if (-not (Test-Path $dst)) { return }
    $item = Get-Item $dst -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        # Delete only the link, never the target.
        [IO.Directory]::Delete($dst)
        Write-Host "Removed junction $dst"
    } else {
        Remove-Item $dst -Recurse -Force -Confirm:$false
        Write-Host "Removed copied folder $dst"
    }
}

# The mod was called "FerroEngrenagem" until 2026-11-26: drop a leftover link/copy with the old name, otherwise the game
# would load two copies of the mod. A link is removed without touching its target.
$legacy = Join-Path $mods 'FerroEngrenagem'
if (Test-Path $legacy) {
    $li = Get-Item $legacy -Force
    if ($li.Attributes -band [IO.FileAttributes]::ReparsePoint) { [IO.Directory]::Delete($legacy); Write-Host "Removed old junction $legacy" }
    elseif (Test-Path (Join-Path $legacy 'FerroEngrenagem.dll')) { Remove-Item $legacy -Recurse -Force -Confirm:$false; Write-Host "Removed old copy $legacy" }
}

if ($Uninstall) { Remove-ModInstall; return }

Remove-ModInstall
if ($Copy) {
    Copy-Item $src $dst -Recurse
    Write-Host "Copied $src -> $dst"
} else {
    New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
    Write-Host "Junction $dst -> $src"
}
