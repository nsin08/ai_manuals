# Reset local development state
# Removes Docker containers, volumes, and filesystem chunk storage
# Use this after Phase 1 upgrade or when data becomes inconsistent

param(
    [switch]$Full = $false,
    [switch]$Soft = $false
)

if (-not $Full -and -not $Soft) {
    Write-Host "Usage: .\scripts\reset_local_state.ps1 [-Full | -Soft]"
    Write-Host ""
    Write-Host "  -Soft  : Clear chunks/uploads, restart containers (keep DB)"
    Write-Host "  -Full  : Stop containers, remove volumes, clear filesystem (full reset)"
    exit 1
}

function Clear-Filesystem {
    Write-Host "Clearing filesystem storage..." -ForegroundColor Yellow
    
    $dirs = @("data/assets", "data/uploads", "data/chunks")
    
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            Write-Host "  Removing: $dir"
            Get-ChildItem $dir -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item $dir -Force -ErrorAction SilentlyContinue
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Host "✓ Filesystem cleared" -ForegroundColor Green
}

if ($Soft) {
    Write-Host "=== SOFT RESET (keep DB, restart containers) ===" -ForegroundColor Cyan
    
    Clear-Filesystem
    
    Write-Host "Restarting containers..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml restart worker api 2>&1 | Out-Null
    
    Write-Host "✓ Containers restarted" -ForegroundColor Green
    Write-Host ""
    Write-Host "Chunks cleared. Re-ingest documents with:" -ForegroundColor Cyan
    Write-Host "  python scripts/run_ingestion.py --doc-id <doc_id>"
}

if ($Full) {
    Write-Host "=== FULL RESET (remove DB, containers, filesystem) ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "This will:"
    Write-Host "  1. Stop and remove all Docker containers"
    Write-Host "  2. Remove PostgreSQL/Redis volumes"
    Write-Host "  3. Clear all filesystem chunk storage"
    Write-Host "  4. Restart fresh"
    Write-Host ""
    
    $confirm = Read-Host "Are you sure? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Host "Cancelled." -ForegroundColor Yellow
        exit 0
    }
    
    Write-Host "Stopping containers and removing volumes..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml down -v 2>&1 | Out-Null
    
    Clear-Filesystem
    
    Write-Host "Starting fresh..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml up --build -d 2>&1 | Out-Null
    
    Write-Host "✓ Full reset complete" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 10 seconds for startup..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host "✓ Services started" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify in admin console:" -ForegroundColor Cyan
    Write-Host "  http://localhost:8501/admin"
    Write-Host "  Should show: Ingested Docs: 0, Total Chunks: 0"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Re-ingest documents:"
    Write-Host "     python scripts/run_ingestion.py --doc-id siemens_g120_basic_positioner"
    Write-Host "  2. Test retrieval:"
    Write-Host "     python scripts/run_retrieval.py --query 'fault code' --doc-id siemens_g120_basic_positioner"
    Write-Host "  3. Open chat: http://localhost:8501/"
}
