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

# --- Structured attributes migration (no Alembic) ---
# Adds color/brand/shape/material columns to lost_items and found_items.
# Safe to re-run: checks INFORMATION_SCHEMA before altering.

function Add-ColumnIfMissing {
    param(
        [string]$Table,
        [string]$Column,
        [string]$Definition
    )

    $check = @"
SELECT COUNT(*) AS c
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = '$Table'
  AND COLUMN_NAME = '$Column';
"@

    $result = & mysql @mysqlArgs -N -e $check
    if ([int]$result -eq 0) {
        Write-Host "Adding $Table.$Column ..." -ForegroundColor Yellow
        & mysql @mysqlArgs -e "ALTER TABLE $Table ADD COLUMN $Column $Definition;"
    } else {
        Write-Host "Already exists: $Table.$Column" -ForegroundColor DarkGray
    }
}

# Expect mysql CLI accessible + env vars used above in this script
# (DB_HOST/DB_USER/DB_PASS/DB_NAME) or adjust mysqlArgs accordingly.

Add-ColumnIfMissing -Table 'lost_items'  -Column 'color'    -Definition 'VARCHAR(50) NULL'
Add-ColumnIfMissing -Table 'lost_items'  -Column 'brand'    -Definition 'VARCHAR(120) NULL'
Add-ColumnIfMissing -Table 'lost_items'  -Column 'shape'    -Definition 'VARCHAR(50) NULL'
Add-ColumnIfMissing -Table 'lost_items'  -Column 'material' -Definition 'VARCHAR(50) NULL'

Add-ColumnIfMissing -Table 'found_items' -Column 'color'    -Definition 'VARCHAR(50) NULL'
Add-ColumnIfMissing -Table 'found_items' -Column 'brand'    -Definition 'VARCHAR(120) NULL'
Add-ColumnIfMissing -Table 'found_items' -Column 'shape'    -Definition 'VARCHAR(50) NULL'
Add-ColumnIfMissing -Table 'found_items' -Column 'material' -Definition 'VARCHAR(50) NULL'

Write-Host "`n[DONE] Migration complete!" -ForegroundColor Green
