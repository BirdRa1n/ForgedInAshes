<#
.SYNOPSIS
  Ferro & Engrenagem: uma ferramenta para os três trabalhos repetitivos do mod.

.DESCRIPTION
  1. modelos  Recompila os modelos 3D alterados no Blender e gera o bundle do Unity (ferroengrenagem.unity3d).
              Para cada Art/<modelo>/hd:
                - <modelo>_HD.blend mais novo que o <modelo>_HD.fbx (editado à mão no Blender)
                    -> reexporta o FBX desse .blend (tools/blender_export_hd.py);
                - <modelo>_src.blend mais novo que o _HD.blend e o FBX (geometria alterada)
                    -> retexturiza e faz o bake (F:\IA\texturizar.bat <config>), o que REFAZ o _HD.blend;
                - se os dois mudaram, o _HD.blend vence (para não perder a edição à mão) e aparece um aviso.
              Modelos antigos: Art/feKinetic/feKinetic.blend mais novo que os FBX -> export_feKinetic.py.
              Se algum FBX ou textura ficou mais novo que o bundle: Unity FeBuild.BuildAll.
  2. icones   Renderiza o ícone (a foto da lista do inventário) dos modelos HD cujo ícone é mais velho que o
              modelo (Art/feHD/render_icons_hd.py) e aplica no XML (tools/apply_icons.py).
  3. mod      Valida os XML (check_xpath, check_processes, check_phase3, check_coverage), compila a DLL
              (tools/build.ps1) e instala na pasta do jogo (tools/install.ps1: link; -Copiar = cópia de verdade).
  4. tudo     1 + 2 + 3, nessa ordem.
  0. estado   Só mostra o que está desatualizado (não muda nada).

  Sem parâmetros abre um menu. -Modelos limita aos nomes dados; -Forcar refaz mesmo sem mudança;
  -Simular mostra o que faria sem fazer.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\fe.ps1
  powershell -ExecutionPolicy Bypass -File tools\fe.ps1 tudo
  powershell -ExecutionPolicy Bypass -File tools\fe.ps1 modelos -Modelos feCrusher,feWasher
  powershell -ExecutionPolicy Bypass -File tools\fe.ps1 icones -Forcar -Modelos feCrusher
  powershell -ExecutionPolicy Bypass -File tools\fe.ps1 mod -Copiar
#>
param(
    [Parameter(Position = 0)][ValidateSet('', 'estado', 'modelos', 'icones', 'mod', 'tudo')][string]$Acao = '',
    [string[]]$Modelos = @(),
    [switch]$Forcar,
    [switch]$Copiar,
    [switch]$Simular
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$art = Join-Path $repo 'Art'
$mod = Join-Path $repo 'Mods\FerroEngrenagem'
$bundle = Join-Path $mod 'Resources\ferroengrenagem.unity3d'
$icons = Join-Path $mod 'UIAtlases\ItemIconAtlas'

# ------------------------------------------------------------------ caminhos das ferramentas (ajuste aqui se mudar)
$Blender = 'C:\Program Files\Blender Foundation\Blender 5.3\blender.exe'
$Unity = 'E:\UnityEditors\2022.3.62f2\Editor\Unity.exe'
$Texturizar = 'F:\IA\texturizar.bat'
$IaConfigs = 'F:\IA\fe_blender\configs'
$Python = 'python'
# modelo -> nome do ícone quando são diferentes (Art/feHD/render_icons_hd.py BLOCKS)
$IconeDe = @{ 'feM_Foundry' = 'feFoundry'; 'feM_Lathe' = 'feLathe'; 'feM_Ammo' = 'feAmmoPress' }
$Folga = [TimeSpan]::FromSeconds(5)   # o texturizador salva o .blend segundos antes do FBX

function Titulo([string]$t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }
function Ok([string]$t) { Write-Host "   $t" -ForegroundColor Green }
function Aviso([string]$t) { Write-Host "   $t" -ForegroundColor Yellow }
function Info([string]$t) { Write-Host "   $t" }

function Exigir([string]$caminho, [string]$nome) {
    if (-not (Test-Path $caminho)) { throw "$nome não encontrado: $caminho (ajuste o caminho no topo de tools\fe.ps1)" }
}

function Hora([string]$p) {
    if (Test-Path $p) { return (Get-Item $p).LastWriteTime }
    return [DateTime]::MinValue
}

function Mais-Novo([string]$a, [string]$b) {
    # $a mais novo que $b (com folga); $b inexistente = sim
    if (-not (Test-Path $a)) { return $false }
    if (-not (Test-Path $b)) { return $true }
    return (Hora $a) -gt ((Hora $b) + $Folga)
}

function Rodar([string]$exe, [string[]]$argumentos, [string]$log) {
    if ($Simular) { Info ("(simulação) " + $exe + ' ' + ($argumentos -join ' ')); return 0 }
    $p = Start-Process -FilePath $exe -ArgumentList $argumentos -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
    return $p.ExitCode
}

function Q([string]$s) { return '"' + $s + '"' }

function Jogo-Aberto { return [bool](Get-Process 7DaysToDie -ErrorAction SilentlyContinue) }

$tmp = Join-Path $env:TEMP 'fe_tool'
New-Item -ItemType Directory -Force $tmp | Out-Null

# ------------------------------------------------------------------ o que mudou
function Modelos-HD {
    Get-ChildItem $art -Directory | Where-Object {
        $n = $_.Name
        (Test-Path (Join-Path $_.FullName "hd\$($n)_HD.blend")) -or (Test-Path (Join-Path $_.FullName "hd\$($n)_src.blend"))
    } | ForEach-Object { $_.Name } | Where-Object { $Modelos.Count -eq 0 -or $Modelos -contains $_ }
}

function Estado-Modelo([string]$m) {
    $hd = Join-Path $art "$m\hd"
    $src = Join-Path $hd "$($m)_src.blend"
    $blend = Join-Path $hd "$($m)_HD.blend"
    $fbx = Join-Path $hd "$($m)_HD.fbx"
    $srcMudou = (Test-Path $src) -and ((Mais-Novo $src $blend) -and (Mais-Novo $src $fbx))
    $hdMudou = (Test-Path $blend) -and (Mais-Novo $blend $fbx)
    $acao = ''
    if ($Forcar) { $acao = if (Test-Path $blend) { 'exportar' } else { 'texturizar' } }
    elseif ($hdMudou) { $acao = 'exportar' }
    elseif ($srcMudou) { $acao = 'texturizar' }
    return [pscustomobject]@{ Modelo = $m; Acao = $acao; Conflito = ($srcMudou -and $hdMudou); Src = $src; Blend = $blend; Fbx = $fbx }
}

function Kinetic-Mudou {
    $kb = Join-Path $art 'feKinetic\feKinetic.blend'
    if (-not (Test-Path $kb)) { return $false }
    if ($Forcar -and $Modelos.Count -eq 0) { return $true }
    # only the blocks export_feKinetic.py writes (its NAMES list)
    $py = Get-Content (Join-Path $art 'feKinetic\export_feKinetic.py') -Raw
    $m = [regex]::Match($py, 'NAMES\s*=\s*\[(.*?)\]', 'Singleline')
    $nomes = [regex]::Matches($m.Groups[1].Value, '"(\w+)"') | ForEach-Object { $_.Groups[1].Value }
    if ($Modelos.Count -gt 0) { $nomes = $nomes | Where-Object { $Modelos -contains $_ } }
    if (-not $nomes) { return $false }
    $velho = $nomes | ForEach-Object { Join-Path $art "$_\$_.fbx" } |
        Where-Object { Test-Path $_ } | ForEach-Object { Hora $_ } | Sort-Object | Select-Object -First 1
    if (-not $velho) { return $true }
    return (Hora $kb) -gt ($velho + $Folga)
}

function Bundle-Desatualizado {
    $b = Hora $bundle
    $novo = Get-ChildItem $art -Recurse -File -Include *.fbx, *_Albedo.png, *_Normal.png, *_MetallicSmoothness.png, *_Emission.png -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike '*UnityProject*' -and $_.LastWriteTime -gt ($b + $Folga) } | Select-Object -First 1
    $editor = Get-ChildItem (Join-Path $art 'UnityProject\Assets\Editor') -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt ($b + $Folga) } | Select-Object -First 1
    return [bool]($novo -or $editor)
}

function Icones-Velhos {
    Modelos-HD | Where-Object {
        $m = $_
        $nome = if ($IconeDe.ContainsKey($m)) { $IconeDe[$m] } else { $m }
        $png = Join-Path $icons "$nome.png"
        $blend = Join-Path $art "$m\hd\$($m)_HD.blend"
        (Test-Path $blend) -and ($Forcar -or (Mais-Novo $blend $png))
    }
}

# ------------------------------------------------------------------ 0. estado
function Mostrar-Estado {
    Titulo 'Estado'
    $mud = @(Modelos-HD | ForEach-Object { Estado-Modelo $_ } | Where-Object { $_.Acao })
    if ($mud.Count -eq 0) { Ok 'Modelos HD: nada alterado' }
    foreach ($e in $mud) {
        $t = if ($e.Acao -eq 'exportar') { 'reexportar o FBX do _HD.blend' } else { 'retexturizar a partir do _src.blend' }
        Info ("Modelo {0}: {1}" -f $e.Modelo, $t)
        if ($e.Conflito) { Aviso "  $($e.Modelo): o _src.blend TAMBÉM mudou; vale o _HD.blend (retexturize com -Forcar se for o caso)" }
    }
    if (Kinetic-Mudou) { Info 'Modelos antigos: feKinetic.blend alterado (reexportar)' }
    if (Bundle-Desatualizado) { Info 'Bundle do Unity: desatualizado' } else { Ok 'Bundle do Unity: em dia' }
    $ic = @(Icones-Velhos)
    if ($ic.Count -gt 0) { Info ("Ícones desatualizados: " + ($ic -join ', ')) } else { Ok 'Ícones: em dia' }
    $dll = Join-Path $mod 'FerroEngrenagem.dll'
    $cs = Get-ChildItem (Join-Path $repo 'src') -Recurse -Filter *.cs | Where-Object { $_.LastWriteTime -gt ((Hora $dll) + $Folga) } | Select-Object -First 1
    if ($cs) { Info 'DLL: o código mudou depois da última compilação' } else { Ok 'DLL: em dia' }
    if (Jogo-Aberto) { Aviso 'O jogo está aberto: feche antes de instalar o mod (os arquivos ficam presos).' }
}

# ------------------------------------------------------------------ 1. modelos
function Fazer-Modelos {
    Titulo '1. Modelos 3D'
    Exigir $Blender 'Blender'
    $lista = @(Modelos-HD | ForEach-Object { Estado-Modelo $_ } | Where-Object { $_.Acao })
    $falhas = @()
    foreach ($e in $lista) {
        $log = Join-Path $tmp "$($e.Modelo).log"
        if ($e.Conflito) { Aviso "$($e.Modelo): _src.blend e _HD.blend mudaram; reexportando o _HD.blend (a edição à mão)" }
        if ($e.Acao -eq 'exportar') {
            Info "$($e.Modelo): reexportando o FBX do _HD.blend..."
            $code = Rodar $Blender @('-b', (Q $e.Blend), '--python', (Q (Join-Path $PSScriptRoot 'blender_export_hd.py')), '--', (Q $e.Fbx)) $log
        }
        else {
            $cfg = Join-Path $IaConfigs "$($e.Modelo).json"
            if (-not (Test-Path $cfg)) { Aviso "$($e.Modelo): sem config da IA ($cfg), pulei"; $falhas += $e.Modelo; continue }
            Exigir $Texturizar 'texturizar.bat'
            Info "$($e.Modelo): retexturizando e fazendo o bake (alguns minutos)..."
            $code = Rodar 'cmd.exe' @('/c', (Q $Texturizar), (Q $cfg)) $log
        }
        if ($code -ne 0 -or (-not $Simular -and -not (Test-Path $e.Fbx))) { Aviso "$($e.Modelo): FALHOU (log: $log)"; $falhas += $e.Modelo }
        else { Ok "$($e.Modelo): ok" }
    }
    if ($lista.Count -eq 0) { Ok 'Nenhum modelo HD alterado' }
    if (Kinetic-Mudou) {
        Info 'feKinetic.blend: exportando os modelos antigos...'
        $kb = Join-Path $art 'feKinetic\feKinetic.blend'
        $code = Rodar $Blender @('-b', (Q $kb), '--python', (Q (Join-Path $art 'feKinetic\export_feKinetic.py'))) (Join-Path $tmp 'feKinetic.log')
        if ($code -ne 0) { Aviso "feKinetic: FALHOU (log: $(Join-Path $tmp 'feKinetic.log'))"; $falhas += 'feKinetic' } else { Ok 'feKinetic: ok' }
    }
    if ($Forcar -or (Bundle-Desatualizado)) {
        Exigir $Unity 'Unity'
        if (Get-Process Unity -ErrorAction SilentlyContinue) { Aviso 'O Unity está aberto: feche o projeto Art\UnityProject antes (ele trava o build).' }
        Info 'Unity: gerando o bundle (FeBuild.BuildAll, alguns minutos)...'
        $ulog = Join-Path $art 'UnityProject\Logs\febuild.log'
        $antes = Hora $bundle
        $code = Rodar $Unity @('-batchmode', '-quit', '-projectPath', (Q (Join-Path $art 'UnityProject')), '-executeMethod', 'FeBuild.BuildAll', '-logFile', (Q $ulog)) (Join-Path $tmp 'unity.log')
        if (-not $Simular -and ($code -ne 0 -or (Hora $bundle) -le $antes)) {
            Aviso "Unity: FALHOU (log: $ulog)"
            if (Test-Path $ulog) { Get-Content $ulog | Select-String -Pattern 'error|\[FE\].*missing' | Select-Object -Last 8 | ForEach-Object { Aviso ('  ' + $_.Line) } }
            $falhas += 'bundle'
        }
        else { Ok ("Bundle: ok ({0:N1} MB)" -f ((Get-Item $bundle).Length / 1MB)) }
    }
    else { Ok 'Bundle: em dia' }
    return $falhas
}

# ------------------------------------------------------------------ 2. ícones
function Fazer-Icones {
    Titulo '2. Ícones do inventário'
    Exigir $Blender 'Blender'
    $lista = @(Icones-Velhos)
    if ($lista.Count -eq 0) { Ok 'Nenhum ícone desatualizado'; return @() }
    Info ("Renderizando: " + ($lista -join ', '))
    $log = Join-Path $tmp 'icones.log'
    $code = Rodar $Blender (@('-b', '--factory-startup', '--python', (Q (Join-Path $art 'feHD\render_icons_hd.py')), '--') + $lista) $log
    if ($code -ne 0) { Aviso "Ícones: FALHOU (log: $log)"; return @('icones') }
    if (-not $Simular) { & $Python (Join-Path $PSScriptRoot 'apply_icons.py') | Select-Object -Last 2 | ForEach-Object { Info $_ } }
    Ok ("{0} ícone(s) em {1}" -f $lista.Count, $icons)
    return @()
}

# ------------------------------------------------------------------ 3. mod
function Fazer-Mod {
    Titulo '3. Mod: validar, compilar, instalar'
    $falhas = @()
    foreach ($v in 'check_xpath.py', 'check_processes.py', 'check_phase3.py', 'check_coverage.py') {
        if ($Simular) { Info "(simulação) python tools\$v"; continue }
        $out = & $Python (Join-Path $PSScriptRoot $v) 2>&1
        if ($LASTEXITCODE -ne 0) { Aviso "$($v): PROBLEMAS"; $out | Select-Object -Last 8 | ForEach-Object { Aviso ('  ' + $_) }; $falhas += $v }
        else { Ok ("$($v): " + ($out | Select-Object -Last 1)) }
    }
    if ($falhas.Count -gt 0) { Aviso 'Validação falhou: não compilei nem instalei.'; return $falhas }
    if ($Simular) { Info '(simulação) tools\build.ps1'; Info '(simulação) tools\install.ps1'; return @() }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build.ps1') | Out-Host
    if ($LASTEXITCODE -ne 0) { Aviso 'Compilação da DLL FALHOU'; return @('dll') }
    Ok 'DLL compilada'
    if (Jogo-Aberto) { Aviso 'O jogo está aberto: feche e rode "mod" de novo para instalar.'; return @('jogo aberto') }
    $inst = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'install.ps1'))
    if ($Copiar) { $inst += '-Copy' }
    & powershell @inst | Out-Host
    if ($LASTEXITCODE -ne 0) { Aviso 'Instalação FALHOU'; return @('instalar') }
    Ok ('Instalado na pasta do jogo' + $(if ($Copiar) { ' (cópia)' } else { ' (link para o repositório)' }))
    return @()
}

# ------------------------------------------------------------------ menu
if ($Acao -eq '') {
    Write-Host ''
    Write-Host 'Ferro & Engrenagem - ferramenta' -ForegroundColor Cyan
    Write-Host '  1  Modelos 3D alterados -> FBX -> bundle do Unity'
    Write-Host '  2  Ícones do inventário dos modelos alterados'
    Write-Host '  3  Mod: validar, compilar a DLL e instalar no jogo'
    Write-Host '  4  Tudo (1 + 2 + 3)'
    Write-Host '  0  Só ver o que está desatualizado'
    $r = Read-Host 'Escolha'
    $Acao = @{ '1' = 'modelos'; '2' = 'icones'; '3' = 'mod'; '4' = 'tudo'; '0' = 'estado' }[$r]
    if (-not $Acao) { Write-Host 'Opção inválida'; exit 1 }
}

$falhou = @()
$inicio = Get-Date
switch ($Acao) {
    'estado' { Mostrar-Estado }
    'modelos' { $falhou += Fazer-Modelos }
    'icones' { $falhou += Fazer-Icones }
    'mod' { $falhou += Fazer-Mod }
    'tudo' { $falhou += Fazer-Modelos; $falhou += Fazer-Icones; $falhou += Fazer-Mod }
}
Write-Host ''
$t = [int]((Get-Date) - $inicio).TotalSeconds
if ($falhou.Count -gt 0) { Write-Host ("Terminou com problemas em: " + ($falhou -join ', ') + " ($t s)") -ForegroundColor Red; exit 1 }
Write-Host "Pronto ($t s)." -ForegroundColor Green
exit 0
