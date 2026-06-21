# ==============================================
# Upload project to VPS - Run locally in PowerShell
# Modify these three lines:
# ==============================================

$VPS_HOST = "65.49.201.211"
$VPS_USER = "root"
$VPS_PORT = "22"

Write-Host "Packing project..." -ForegroundColor Green
$tempDir = "$env:TEMP\deepseek-gateway-deploy"
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $tempDir | Out-Null

# Copy files BUT exclude:
#   .venv, __pycache__, db.sqlite3, data/ (to protect remote database)
Get-ChildItem "E:\Projects\deepseek-gateway" -Recurse -File |
    Where-Object {
        $_.FullName -notlike "*\.venv\*" -and
        $_.FullName -notlike "*\__pycache__\*" -and
        $_.Name -ne "db.sqlite3" -and
        $_.FullName -notlike "*\data\*"
    } |
    ForEach-Object {
        $rel = $_.FullName.Replace("E:\Projects\deepseek-gateway\", "")
        $dest = Join-Path $tempDir $rel
        $destDir = Split-Path $dest -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force $destDir | Out-Null }
        Copy-Item $_.FullName $dest -Force
    }

Write-Host "Uploading code to $VPS_HOST ..." -ForegroundColor Green
scp -P $VPS_PORT -r "$tempDir\*" "${VPS_USER}@${VPS_HOST}:/opt/deepseek-gateway/"

Write-Host "Running deploy.sh on VPS..." -ForegroundColor Green
ssh -p $VPS_PORT "${VPS_USER}@${VPS_HOST}" "cd /opt/deepseek-gateway && chmod +x deploy.sh && bash deploy.sh"

Write-Host "Cleaning up..." -ForegroundColor Green
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue

Write-Host "Done! Test: curl http://$VPS_HOST/health" -ForegroundColor Green
Write-Host "NOTE: First run creates 'data/' on the VPS. Subsequent uploads will NOT overwrite db.sqlite3." -ForegroundColor Yellow