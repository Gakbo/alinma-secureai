# Copies the freshly trained SMS model from ml-training into backend/.
# Run this AFTER every retrain, or the backend keeps serving the old model.
#
#   .\scripts\copy_model.ps1
#
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root "ml-training\saved_models\transformer_sms_classifier"
$dst  = Join-Path $root "backend\saved_models\transformer_sms_classifier"

if (-not (Test-Path $src)) {
    Write-Error "No trained model at $src`nRun: python sms_model\train_transformer.py (from ml-training)"
    exit 1
}

Write-Host "Copying model..." -ForegroundColor Cyan
Write-Host "  from $src"
Write-Host "  to   $dst"

if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
New-Item -ItemType Directory -Path $dst -Force | Out-Null

# Copy the model only -- skip 'checkpoints' (per-epoch training snapshots,
# not needed to serve predictions, and several GB).
Get-ChildItem $src -Exclude "checkpoints" | Copy-Item -Destination $dst -Recurse -Force

$size = (Get-ChildItem $dst -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ("Done. {0:N1} MB copied." -f $size) -ForegroundColor Green
Write-Host "Restart the backend, then check http://localhost:8000/ -- it should report backend=transformer." -ForegroundColor Yellow
