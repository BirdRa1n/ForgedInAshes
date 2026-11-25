<#
.SYNOPSIS
  Compiles src\FerroEngrenagem\*.cs into Mods\FerroEngrenagem\FerroEngrenagem.dll.

.DESCRIPTION
  Uses the C# compiler that ships with Windows (.NET Framework 4, C# 5), because the local
  Visual Studio has no workloads installed. References come from the user's own game install
  (7DaysToDie_Data\Managed and Mods\0_TFP_Harmony) and are never copied into the repo.
  The game's TfpHarmony targets .NET Framework 4.8; this DLL links against the game's mscorlib.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\build.ps1
#>
param([string]$Out = '')   # -Out <path>: build elsewhere (e.g. to check while the game holds the DLL)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$game = (Get-Content (Join-Path $PSScriptRoot 'game_path.txt') -TotalCount 1).Trim()
$managed = Join-Path $game '7DaysToDie_Data\Managed'
$harmonyDir = Join-Path $game 'Mods\0_TFP_Harmony'
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { throw "csc not found: $csc" }

$src = Get-ChildItem (Join-Path $repo 'src\FerroEngrenagem') -Recurse -Filter *.cs | ForEach-Object { $_.FullName }
$out = if ($Out) { $Out } else { Join-Path $repo 'Mods\FerroEngrenagem\FerroEngrenagem.dll' }
$refs = @(
    (Join-Path $managed 'mscorlib.dll'),
    (Join-Path $managed 'System.dll'),
    (Join-Path $managed 'System.Core.dll'),
    (Join-Path $managed 'System.Xml.dll'),
    (Join-Path $managed 'netstandard.dll'),
    (Join-Path $managed 'Assembly-CSharp.dll'),
    (Join-Path $managed 'LogLibrary.dll'),
    (Join-Path $managed 'MemoryPack.dll'),
    (Join-Path $managed 'UnityEngine.dll'),
    (Join-Path $managed 'UnityEngine.CoreModule.dll'),
    (Join-Path $managed 'UnityEngine.AnimationModule.dll'),
    (Join-Path $managed 'UnityEngine.PhysicsModule.dll'),
    (Join-Path $managed 'UnityEngine.ParticleSystemModule.dll'),   # FxVisual: steam / smoke / sparks
    (Join-Path $managed 'UnityEngine.TextRenderingModule.dll'),    # Display Panel (TextMesh)
    (Join-Path $managed 'InControl.dll'),          # PlayerAction (Activate key) for the Crank
    (Join-Path $harmonyDir '0Harmony.dll')
)
$cscArgs = @('/nologo', '/target:library', '/optimize+', '/debug-', '/nostdlib+', '/noconfig', "/out:$out") +
        ($refs | ForEach-Object { "/reference:$_" }) + $src
& $csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "build failed ($LASTEXITCODE)" }
Write-Host "Built $out"
