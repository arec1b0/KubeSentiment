# Script for formatting all project code (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🎨 Auto-formatting code with Black & isort" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check for tools
try {
    black --version | Out-Null
}
catch {
    Write-Host "❌ Black not installed. Run: pip install -r requirements-dev.txt" -ForegroundColor Red
    exit 1
}

try {
    isort --version | Out-Null
}
catch {
    Write-Host "❌ isort not installed. Run: pip install -r requirements-dev.txt" -ForegroundColor Red
    exit 1
}

# Define directories to format
$Dirs = @("app", "tests", "scripts", "run.py")

Write-Host "📝 Formatting with Black..." -ForegroundColor Yellow
black @Dirs
Write-Host "✅ Black formatting complete" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Sorting imports with isort..." -ForegroundColor Yellow
isort @Dirs
Write-Host "✅ Import sorting complete" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🎉 Code formatting complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Review changes: git diff" -ForegroundColor Gray
Write-Host "  2. Run linting: make lint" -ForegroundColor Gray
Write-Host "  3. Run tests: make test" -ForegroundColor Gray
Write-Host "  4. Commit: git commit -am 'style: format code'" -ForegroundColor Gray
