<#
.SYNOPSIS
  Installs the mod into the game's Mods folder for testing.

.DESCRIPTION
  Default: creates a directory junction  <game>\Mods\FerroEngrenagem -> <repo>\Mods\FerroEngrenagem
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
$src = Join-Path $repo 'Mods\FerroEngrenagem'
$pathFile = Join-Path $PSScriptRoot 'game_path.txt'
if (-not (Test-Path $pathFile)) { throw "Missing $pathFile" }
$game = (Get-Content $pathFile -TotalCount 1).Trim()
$mods = Join-Path $game 'Mods'
if (-not (Test-Path (Join-Path $game 'Data\Config'))) { throw "Not a 7DTD install: $game" }
$dst = Join-Path $mods 'FerroEngrenagem'

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

if ($Uninstall) { Remove-ModInstall; return }

Remove-ModInstall
if ($Copy) {
    Copy-Item $src $dst -Recurse
    Write-Host "Copied $src -> $dst"
} else {
    New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
    Write-Host "Junction $dst -> $src"
}
