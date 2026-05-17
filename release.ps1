# release.ps1 - パッチバージョンアップ & インストーラービルド & GitHubリリース
# 使い方: .\release.ps1
# オプション: .\release.ps1 -Version 1.2.3  (バージョンを直接指定)

param(
    [string]$Version = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT   = $PSScriptRoot
$ISCC   = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$SPEC   = "$ROOT\PDFchangecombine.spec"
$ISS    = "$ROOT\installer\setup.iss"
$CONFIG = "$ROOT\src\config.py"
$DIST   = "$ROOT\dist\installer\PDFConverter-setup.exe"

# ── バージョン決定 ─────────────────────────────────────────────
if ($Version -eq "") {
    $line = Get-Content $CONFIG | Where-Object { $_ -match 'APP_VERSION\s*=' }
    if ($line -match '"(\d+)\.(\d+)\.(\d+)"') {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]; $patch = [int]$Matches[3]
        $Version = "$major.$minor.$($patch + 1)"
    } else {
        Write-Error "config.py からバージョンを読み取れませんでした"
        exit 1
    }
}

Write-Host "=== リリース: v$Version ===" -ForegroundColor Cyan

# ── バージョン書き換え ─────────────────────────────────────────
Write-Host "バージョン更新中..." -ForegroundColor Yellow
$configContent = Get-Content $CONFIG -Raw
$configContent = $configContent -replace 'APP_VERSION\s*=\s*"[\d.]+"', "APP_VERSION = `"$Version`""
Set-Content $CONFIG $configContent -NoNewline

$issContent = Get-Content $ISS -Raw
$issContent = $issContent -replace 'AppVersion=[\d.]+', "AppVersion=$Version"
Set-Content $ISS $issContent -NoNewline

Write-Host "  config.py / setup.iss -> v$Version" -ForegroundColor Green

# ── PyInstaller ビルド ─────────────────────────────────────────
Write-Host "PyInstaller ビルド中..." -ForegroundColor Yellow
Push-Location $ROOT
python -m PyInstaller $SPEC --clean --noconfirm 2>&1 | ForEach-Object {
    if ($_ -match "Building COLLECT|Build complete|ERROR") { Write-Host "  $_" }
}
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller ビルド失敗"; exit 1 }
Write-Host "  PyInstaller ビルド完了" -ForegroundColor Green

# ── Inno Setup インストーラービルド ────────────────────────────
Write-Host "インストーラービルド中..." -ForegroundColor Yellow
if (-not (Test-Path $ISCC)) { Write-Error "ISCC.exe が見つかりません: $ISCC"; exit 1 }
& $ISCC $ISS /Q
if ($LASTEXITCODE -ne 0) { Write-Error "Inno Setup ビルド失敗"; exit 1 }
if (-not (Test-Path $DIST)) { Write-Error "インストーラーが生成されませんでした: $DIST"; exit 1 }
$sizeMB = [math]::Round((Get-Item $DIST).Length / 1MB, 1)
Write-Host "  インストーラービルド完了: $sizeMB MB" -ForegroundColor Green

# ── Git コミット・タグ・プッシュ ────────────────────────────────
Write-Host "Git コミット中..." -ForegroundColor Yellow
Pop-Location
Set-Location $ROOT
git add src/config.py installer/setup.iss
git commit -m "chore: バージョン v$Version にアップデート"
git tag "v$Version"
git push origin main
git push origin "v$Version"
Write-Host "  Git push 完了 (v$Version)" -ForegroundColor Green

# ── GitHub Release 作成 & アップロード ──────────────────────────
Write-Host "GitHub Release 作成中..." -ForegroundColor Yellow
gh release create "v$Version" `
    --title "v$Version" `
    --generate-notes `
    $DIST
Write-Host "  GitHub Release 完了" -ForegroundColor Green

Write-Host ""
Write-Host "=== リリース完了: v$Version ===" -ForegroundColor Cyan
gh release view "v$Version" --json url -q ".url"
