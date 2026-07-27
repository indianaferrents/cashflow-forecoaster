# Set output encoding
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "============================================================"
Write-Host "    CashFlow Forecaster - Launch Application"
Write-Host "============================================================"
Write-Host ""

# === Автоматический выбор версии Python ===
Write-Host "[1/3] Searching for compatible Python (3.9 - 3.11)..."

$versions = py -0 | ForEach-Object {
    if ($_ -match '(\d+\.\d+)') {
        [version]$Matches[1]
    }
} | Where-Object { $_ -ge [version]"3.9" -and $_ -le [version]"3.11" }

if ($versions.Count -eq 0) {
    Write-Host "   [ERROR] No suitable Python version found (3.9-3.11)!"
    Write-Host "   Install Python 3.9-3.11 from python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

$selectedVersion = $versions | Sort-Object -Descending | Select-Object -First 1
Write-Host "   [OK] Selected Python version: $selectedVersion (latest available)"

# === Проверка виртуального окружения ===
Write-Host "[2/3] Checking virtual environment..."

if (-not (Test-Path "venv\")) {
    Write-Host "   Creating virtual environment with Python $selectedVersion..."
    py -$selectedVersion -m venv venv
    Write-Host "   Virtual environment created"
} else {
    Write-Host "   Virtual environment already exists"
}

& .\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   [ERROR] Activation failed!"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "   [OK] Activation successful"

# === Установка зависимостей ===
Write-Host "[3/3] Installing dependencies..."
Write-Host "   Checking and installing (this may take a few minutes)..."

$installCmd = "python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --timeout 300 --retries 5 --no-cache-dir"
Invoke-Expression $installCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "    ERROR installing dependencies!"
    Write-Host "    Check your internet connection"
    Write-Host "    Or install manually:"
    Write-Host "    pip install -r requirements.txt -i mirror"
    Write-Host "============================================================"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "   [OK] Dependencies installed"

# === Запуск приложения ===
Write-Host ""
Write-Host "============================================================"
Write-Host "    Application launched"
Write-Host "    Browser will open with CashFlow Forecaster interface"
Write-Host "    If browser doesn't open, go to:"
Write-Host "    http://localhost:8501"
Write-Host "============================================================"
Write-Host "    To stop the application, close this window"
Write-Host "============================================================"
Write-Host ""

$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
streamlit run dashboard/app.py --theme.base dark