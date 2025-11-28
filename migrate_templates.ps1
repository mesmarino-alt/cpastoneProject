$ErrorActionPreference = "Stop"
Write-Host "Starting template file migration..." -ForegroundColor Green

# Define source and destination paths
$sourceTemplates = "C:\Users\Admin\cap_new\templates"
$sourceAdmin = "C:\Users\Admin\cap_new\admin\templates"
$projectRoot = "C:\Users\Admin\cap_new\project"

Write-Host "Source: $sourceTemplates" -ForegroundColor Cyan
Write-Host "Project: $projectRoot" -ForegroundColor Cyan

# 1. Copy auth templates
Write-Host "`n[1/5] Copying auth templates..." -ForegroundColor Yellow
if (Test-Path "$sourceTemplates\auth") {
    Copy-Item "$sourceTemplates\auth\*" "$projectRoot\templates\auth\" -Force -Recurse
    Write-Host "[OK] Auth templates copied" -ForegroundColor Green
    Get-ChildItem "$projectRoot\templates\auth\" | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "[SKIP] No auth templates found" -ForegroundColor Yellow
}

# 2. Copy layout templates
Write-Host "`n[2/5] Copying layout templates..." -ForegroundColor Yellow
if (Test-Path "$sourceTemplates\layouts") {
    Copy-Item "$sourceTemplates\layouts\*" "$projectRoot\templates\layouts\" -Force -Recurse
    Write-Host "[OK] Layout templates copied" -ForegroundColor Green
    Get-ChildItem "$projectRoot\templates\layouts\" | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "[SKIP] No layout templates found" -ForegroundColor Yellow
}

# 3. Copy user templates
Write-Host "`n[3/5] Copying user templates..." -ForegroundColor Yellow
if (Test-Path "$sourceTemplates\user") {
    Copy-Item "$sourceTemplates\user\*" "$projectRoot\user\templates\user\" -Force -Recurse
    Write-Host "[OK] User templates copied" -ForegroundColor Green
    Get-ChildItem "$projectRoot\user\templates\user\" | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "[SKIP] No user templates found" -ForegroundColor Yellow
}

# 4. Copy admin templates
Write-Host "`n[4/5] Copying admin templates..." -ForegroundColor Yellow
if (Test-Path "$sourceAdmin\admin") {
    Copy-Item "$sourceAdmin\admin\*" "$projectRoot\admin\templates\admin\" -Force -Recurse
    Write-Host "[OK] Admin templates copied" -ForegroundColor Green
    Get-ChildItem "$projectRoot\admin\templates\admin\" | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "[SKIP] No admin templates found" -ForegroundColor Yellow
}

# 5. Verify all directories exist and have content
Write-Host "`n[5/5] Verifying migration..." -ForegroundColor Yellow
$dirs = @(
    "$projectRoot\templates\layouts",
    "$projectRoot\templates\auth",
    "$projectRoot\user\templates\user",
    "$projectRoot\admin\templates\admin"
)

foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        $count = @(Get-ChildItem $dir -Recurse -File).Count
        Write-Host "[OK] $dir - $count files" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $dir - MISSING" -ForegroundColor Red
    }
}

Write-Host "`n[DONE] Migration complete!" -ForegroundColor Green
