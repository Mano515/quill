#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quill - Runner de tests automatise

.DESCRIPTION
    Lance la suite de tests complete avec :
      Rapport HTML interactif  (logs\report_TIMESTAMP.html)
      Journal texte complet    (logs\run_TIMESTAMP.log)
      Rapport de couverture    (logs\coverage_TIMESTAMP\index.html)

.PARAMETER NoCoverage
    Desactive la mesure de couverture (plus rapide).

.PARAMETER Filter
    Expression pytest (-k) pour ne lancer qu'un sous-ensemble de tests.
    Exemple : .\run_tests.ps1 -Filter "test_basic or test_security"

.PARAMETER OpenReport
    Ouvre le rapport HTML dans le navigateur par defaut apres l'execution.

.EXAMPLE
    .\run_tests.ps1
    .\run_tests.ps1 -NoCoverage -OpenReport
    .\run_tests.ps1 -Filter "test_api"
#>

param(
    [switch] $NoCoverage,
    [string] $Filter      = "",
    [switch] $OpenReport
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# =====================================================================
# Chemins
# =====================================================================

$root        = $PSScriptRoot
$timestamp   = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logsDir     = Join-Path $root "logs"
$htmlReport  = Join-Path $logsDir "report_$timestamp.html"
$logFile     = Join-Path $logsDir "run_$timestamp.log"
$coverageDir = Join-Path $logsDir "coverage_$timestamp"
$coverageXml = Join-Path $logsDir "coverage_$timestamp.xml"

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

# =====================================================================
# En-tete
# =====================================================================

$sep = "=" * 66

Write-Host ""
Write-Host "  $sep" -ForegroundColor Cyan
Write-Host "  QUILL  TEST RUNNER                      $timestamp" -ForegroundColor White
Write-Host "  $sep" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Rapport HTML   : $htmlReport"  -ForegroundColor DarkGray
Write-Host "  Journal        : $logFile"      -ForegroundColor DarkGray

if (-not $NoCoverage) {
    Write-Host "  Couverture     : $coverageDir\index.html" -ForegroundColor DarkGray
}

if ($Filter) {
    Write-Host "  Filtre actif   : $Filter" -ForegroundColor Yellow
}

Write-Host ""

# =====================================================================
# Construction des arguments pytest
# =====================================================================

$pytestArgs = @(
    "tests/"
    "--html=$htmlReport"
    "--self-contained-html"
    "--log-file=$logFile"
    "--log-file-level=DEBUG"
    "--log-file-format=%(asctime)s  %(levelname)-8s  %(name)s - %(message)s"
    "--log-file-date-format=%Y-%m-%d %H:%M:%S"
)

if (-not $NoCoverage) {
    $pytestArgs += @(
        "--cov=quill"
        "--cov-report=html:$coverageDir"
        "--cov-report=xml:$coverageXml"
        "--cov-report=term-missing:skip-covered"
    )
}

if ($Filter) {
    $pytestArgs += "-k", $Filter
}

# =====================================================================
# Execution
# =====================================================================

$startTime = Get-Date
python -m pytest @pytestArgs
$exitCode = $LASTEXITCODE
$elapsed  = ((Get-Date) - $startTime).TotalSeconds

# =====================================================================
# Resultat final
# =====================================================================

Write-Host ""
Write-Host "  $sep" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "  OK  Tous les tests ont passe." -ForegroundColor Green
} elseif ($exitCode -eq 5) {
    Write-Host "  --  Aucun test collecte (verifier le filtre -Filter)." -ForegroundColor Yellow
} else {
    Write-Host "  KO  Des tests ont echoue  (code de sortie : $exitCode)." -ForegroundColor Red
}

$elapsedStr = "{0:F1}" -f $elapsed
Write-Host "  Duree totale : ${elapsedStr}s" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Rapport complet    : $htmlReport" -ForegroundColor Cyan

if ((-not $NoCoverage) -and (Test-Path (Join-Path $coverageDir "index.html"))) {
    Write-Host "  Couverture de code : $coverageDir\index.html" -ForegroundColor Cyan
}

Write-Host "  $sep" -ForegroundColor Cyan
Write-Host ""

# =====================================================================
# Ouverture automatique du rapport
# =====================================================================

if ($OpenReport -and (Test-Path $htmlReport)) {
    Write-Host "  Ouverture du rapport HTML..." -ForegroundColor DarkGray
    Start-Process $htmlReport
}

exit $exitCode
