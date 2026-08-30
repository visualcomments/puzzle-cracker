# Server-based Kaggle ops (local IP is blocked by Kaggle; the ubuntu-server
# at 10.0.0.2 is not).  Usage:
#   .\kaggle_server.ps1 status <kernel-key>
#   .\kaggle_server.ps1 output <kernel-key> <local-dest>
#   .\kaggle_server.ps1 submit <file.csv> <message>
#   .\kaggle_server.ps1 submissions
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("status", "output", "submit", "submissions")]
    [string]$Op,
    [Parameter(Position = 1)]
    [string]$Kernel = "trainlong",
    [Parameter(Position = 2)]
    [string]$File = "",
    [Parameter(Position = 3)]
    [string]$Msg = "puzzle-cracker",
    [Parameter(Position = 4)]
    [string]$Dest = "outputs"
)
$Root = $PSScriptRoot
$Kag = "/home/zzz/kvenv/bin/kaggle"
$Tok = "KGAT_7dfb30df891fb9bdb144544123e0602d"
$K = @{
    trainlong = "apollinariat/puzzle-cracker-megaminx-long-train-cayleypy"
    diffusion = "apollinariat/puzzle-cracker-megaminx-diffusion-cayleypy"
    beam      = "apollinariat/puzzle-cracker-megaminx-beam-cayleypy"
    tpu       = "apollinariat/puzzle-cracker-megaminx-tpu-train-cayleypy"
    solve     = "apollinariat/puzzle-cracker-megaminx-solve-cayleypy"
}
$ref = if ($Kernel -in $K.Keys) { $K[$Kernel] } else { $Kernel }
switch ($Op) {
    "status" {
        ssh server "KAGGLE_API_TOKEN=$Tok $Kag kernels status -k $ref" 2>&1
    }
    "output" {
        $remote = "/home/zzz/kout-$(Get-Random)"
        ssh server "mkdir -p $remote; KAGGLE_API_TOKEN=$Tok $Kag kernels output -k $ref -p $remote" 2>&1
        New-Item -ItemType Directory -Force -Path $Dest | Out-Null
        scp "server:$remote/*" $Dest 2>&1
        ssh server "rm -rf $remote" 2>&1
        Get-ChildItem $Dest | Select-Object Name, Length
    }
    "submit" {
        if (-not $File) { Write-Error "submit needs -File"; exit 1 }
        $remote = "/home/zzz/sub-$(Get-Random).csv"
        scp $File "server:$remote" 2>&1
        ssh server "KAGGLE_API_TOKEN=$Tok $Kag competitions submit -c cayley-py-megaminx -f $remote -m `"$Msg`"" 2>&1
        ssh server "rm -f $remote" 2>&1
    }
    "submissions" {
        ssh server "KAGGLE_API_TOKEN=$Tok $Kag competitions submissions -c cayley-py-megaminx" 2>&1
    }
}