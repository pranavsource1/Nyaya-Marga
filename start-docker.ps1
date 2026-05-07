# Nyaya Marga Docker Startup Script
# Run this in PowerShell to start all services

Write-Host "🚀 Starting Nyaya Marga Docker Services..." -ForegroundColor Green

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env with NVIDIA_NIM_API_KEY=" -ForegroundColor Yellow
    exit 1
}

# Check if NVIDIA_NIM_API_KEY is set
$envContent = Get-Content ".env"
if ($envContent -notmatch "NVIDIA_NIM_API_KEY") {
    Write-Host "⚠️  Warning: NVIDIA_NIM_API_KEY not found in .env" -ForegroundColor Yellow
    Write-Host "Add it: NVIDIA_NIM_API_KEY=your-key-from-https://build.nvidia.com" -ForegroundColor Yellow
}

Write-Host "`n📦 Building Docker images..." -ForegroundColor Cyan
docker-compose build --no-cache

Write-Host "`n▶️  Starting services..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "`n⏳ Waiting for services to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "`n📊 Service Status:" -ForegroundColor Green
docker-compose ps

Write-Host "`n✅ Services started!" -ForegroundColor Green
Write-Host "`n📍 Access Points:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor Yellow
Write-Host "  API:       http://localhost:8000" -ForegroundColor Yellow
Write-Host "  Docs:      http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Health:    http://localhost:8000/api/v1/health" -ForegroundColor Yellow

Write-Host "`n📋 View Logs:" -ForegroundColor Cyan
Write-Host "  docker-compose logs -f" -ForegroundColor DarkGray
Write-Host "  docker-compose logs -f backend" -ForegroundColor DarkGray
Write-Host "  docker-compose logs -f celery_worker" -ForegroundColor DarkGray

Write-Host "`n🛑 Stop Services:" -ForegroundColor Cyan
Write-Host "  docker-compose down" -ForegroundColor DarkGray
