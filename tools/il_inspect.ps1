<#
.SYNOPSIS
  Read IL of the game's Assembly-CSharp.dll (study only; nothing is copied into the repo).
  Uses the Mono.Cecil.dll that ships with the game in Mods\0_TFP_Harmony.

.EXAMPLE
  # dump one method (all overloads)
  powershell -File tools\il_inspect.ps1 -Method 'TileEntityWorkstation::GetFuelTime'
  # list members of a type
  powershell -File tools\il_inspect.ps1 -Type 'BlockCollector'
  # find every method whose IL mentions a regex (operand text: strings, fields, calls)
  powershell -File tools\il_inspect.ps1 -Find 'FuelValue'
#>
param([string]$Method, [string]$Type, [string]$Find, [int]$Max = 400)
$ErrorActionPreference = 'Stop'
$game = (Get-Content (Join-Path $PSScriptRoot 'game_path.txt') -TotalCount 1).Trim()
Add-Type -Path (Join-Path $game 'Mods\0_TFP_Harmony\Mono.Cecil.dll')
$managed = Join-Path $game '7DaysToDie_Data\Managed'
$rp = New-Object Mono.Cecil.ReaderParameters
$res = New-Object Mono.Cecil.DefaultAssemblyResolver; $res.AddSearchDirectory($managed); $rp.AssemblyResolver = $res
$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $managed 'Assembly-CSharp.dll'), $rp)
$out = New-Object System.Collections.Generic.List[string]

if ($Type) {
    $t = $asm.MainModule.GetTypes() | Where-Object { $_.FullName -eq $Type -or $_.Name -eq $Type } | Select-Object -First 1
    if (-not $t) { throw "type not found: $Type" }
    $out.Add("type $($t.FullName) : $($t.BaseType)")
    foreach ($f in $t.Fields) { $out.Add("  field $($f.FieldType.Name) $($f.Name)") }
    foreach ($p in $t.Properties) { $out.Add("  prop  $($p.PropertyType.Name) $($p.Name)") }
    foreach ($m in $t.Methods) { $out.Add("  meth  $($m.ReturnType.Name) $($m.Name)(" + (($m.Parameters | ForEach-Object { "$($_.ParameterType.Name) $($_.Name)" }) -join ', ') + ")") }
    foreach ($n in $t.NestedTypes) { $out.Add("  nested $($n.Name)") }
}
if ($Method) {
    $tn, $mn = $Method -split '::', 2
    $t = $asm.MainModule.GetTypes() | Where-Object { $_.FullName -eq $tn -or $_.Name -eq $tn } | Select-Object -First 1
    if (-not $t) { throw "type not found: $tn" }
    foreach ($m in ($t.Methods | Where-Object { $_.Name -eq $mn })) {
        $out.Add("=== $($t.FullName)::$($m.Name)(" + (($m.Parameters | ForEach-Object { "$($_.ParameterType.Name) $($_.Name)" }) -join ', ') + ")")
        if ($m.HasBody) { foreach ($i in $m.Body.Instructions) { $out.Add("   $i") } }
    }
}
if ($Find) {
    foreach ($t in $asm.MainModule.GetTypes()) {
        foreach ($m in $t.Methods) {
            if (-not $m.HasBody) { continue }
            foreach ($i in $m.Body.Instructions) {
                if ($i.Operand -ne $null -and "$($i.Operand)" -match $Find) { $out.Add("$($t.FullName)::$($m.Name)  $($i.OpCode) $($i.Operand)") }
            }
        }
    }
}
$out | Select-Object -Unique | Select-Object -First $Max
