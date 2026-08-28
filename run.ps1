# Puzzle Cracker - Windows wrapper for the Makefile targets (make is not
# installed on this machine).  Run from the project root:
#   .\run.ps1 demo | verify | run | data | data-all | scorecard | improve | setup
# Options for `run`: -REF <name> -METHOD <staged|bibfs|beam|auto> -PUZZLE <pz> -LIMIT <n> -BUDGET <sec>

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("setup", "data", "data-all", "demo", "run", "verify", "improve", "scorecard", "help")]
    [string]$Target,
    [string]$REF = "santa-2023",
    [string]$METHOD = "auto",
    [string]$PUZZLE = "",
    [string]$LIMIT = "",
    [int]$BUDGET = 30
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error ".venv missing - run: python -m venv $Root\.venv ; & `"$Root\.venv\Scripts\pip.exe`" install -e ."
    exit 1
}

switch ($Target) {
    "setup" {
        & $Py -m pip install --upgrade pip -q
        & $Py -m pip install -e $Root -q
        if (Test-Path "$HOME\.kaggle\kaggle.json") { Write-Host "kaggle.json present" }
        else { Write-Host "no ~/.kaggle/kaggle.json - set KAGGLE_KEY then: .\run.ps1 data" }
    }
    "data" {
        if (-not $env:KAGGLE_KEY) { Write-Error "KAGGLE_KEY not set (KGAT_...)" ; exit 1 }
        & $Py -c "import sys; sys.path.insert(0,'.'); from puzzle_cracker import kaggle_client as k; print('ready:', k.ensure_data('data'))"
    }
    "data-all" {
        if (-not $env:KAGGLE_KEY) { Write-Error "KAGGLE_KEY not set (KGAT_...)" ; exit 1 }
        & $Py -c "from puzzle_cracker import competitions as c; print('ready:', len(c.fetch_all('data')))"
    }
    "demo" { & $Py scripts/demo.py }
    "verify" { & $Py scripts/verify.py }
    "run" {
        $args = @("--ref", $REF, "--method", $METHOD, "--data-dir", "data", "--out-dir", "outputs", "--budget", "$BUDGET")
        if ($PUZZLE) { $args += @("--puzzle", $PUZZLE) }
        if ($LIMIT) { $args += @("--limit", $LIMIT) }
        & $Py -m puzzle_cracker.harness @args
    }
    "improve" {
        $args = @("--ref", $REF, "--method", $METHOD, "--data-dir", "data", "--out-dir", "outputs", "--budget", "$BUDGET", "--improve")
        if ($LIMIT) { $args += @("--limit", $LIMIT) }
        & $Py -m puzzle_cracker.harness @args
    }
    "scorecard" {
        $d = Join-Path $Root "docs\scorecards"
        New-Item -ItemType Directory -Force -Path $d | Out-Null
        $f = Join-Path $d ("{0}-{1}.md" -f $REF, (Get-Date -Format yyyyMMdd))
        if (-not (Test-Path $f)) { Set-Content -LiteralPath $f -Value ("## " + (Get-Date -Format yyyy-MM-dd) + " " + $REF) }
        Write-Host "scorecard: $f"
    }
    "help" {
        Get-Content -LiteralPath $MyInvocation.MyCommand.Path | Select-Object -First 6
    }
}
exit $LASTEXITCODE