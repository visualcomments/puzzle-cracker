# Puzzle Cracker - Kaggle kernel helpers (Windows wrapper)
#   .\kaggle_ops.ps1 status                 - poll all 3 kernels
#   .\kaggle_ops.ps1 logs <kernel-slug>     - tail kernel logs
#   .\kaggle_ops.ps1 output <kernel-slug>   - download kernel output to outputs/
#   .\kaggle_ops.ps1 submit <file.csv> <msg> - submit with the DATA token
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("status", "logs", "output", "submit")]
    [string]$Op,
    [string]$Kernel = "diffusion",
    [string]$File = "",
    [string]$Msg = "puzzle-cracker run"
)

$Root = $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Kag = Join-Path $Root ".venv\Scripts\kaggle.exe"
$ComputeTok = "KGAT_7dfb30df891fb9bdb144544123e0602d"   # single account: data + compute + submission
$DataTok = $ComputeTok
$K = @{
    diffusion = "apollinariat/puzzle-cracker-megaminx-diffusion-cayleypy"
    beam      = "apollinariat/puzzle-cracker-megaminx-beam-cayleypy"
    tpu       = "apollinariat/puzzle-cracker-megaminx-tpu-train-cayleypy"
    trainlong = "apollinariat/puzzle-cracker-megaminx-long-train-cayleypy"
    solve     = "apollinariat/puzzle-cracker-megaminx-solve-cayleypy"
}
$env:KAGGLE_API_TOKEN = $ComputeTok

switch ($Op) {
    "status" {
        foreach ($name in $K.Keys) {
            $s = & $Kag kernels status -k $K[$name] 2>&1 | Out-String
            Write-Host "$name -> $s"
        }
    }
    "logs" {
        $full = if ($Kernel -in $K.Keys) { $K[$Kernel] } else { $Kernel }
        & $Kag kernels logs -k $full 2>&1
    }
    "output" {
        $full = if ($Kernel -in $K.Keys) { $K[$Kernel] } else { $Kernel }
        $outDir = Join-Path $Root "outputs\kernel-$Kernel"
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
        & $Kag kernels output -k $full -p $outDir 2>&1
        Get-ChildItem $outDir -ErrorAction SilentlyContinue | Select-Object Name, Length
    }
    "submit" {
        if (-not $File) { Write-Error "submit needs -File <submission.csv>"; exit 1 }
        $env:KAGGLE_API_TOKEN = $DataTok
        & $Kag competitions submit -c cayley-py-megaminx -f $File -m $Msg 2>&1
    }
}
exit $LASTEXITCODE