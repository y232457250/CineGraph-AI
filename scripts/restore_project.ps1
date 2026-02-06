# CineGraph-AI Project Restore Script
# Usage: .\scripts\restore_project.ps1 backup_20260206_230549.zip

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

if (!(Test-Path $BackupFile)) {
    # Try backup directory
    $BackupFile = "backup/$BackupFile"
    if (!(Test-Path $BackupFile)) {
        Write-Error "Backup file not found: $BackupFile"
        exit 1
    }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tempDir = "backup/restore_temp_$timestamp"

Write-Host "================================"
Write-Host "RESTORING FROM BACKUP"
Write-Host "================================"
Write-Host "Backup file: $BackupFile"
Write-Host "Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
Write-Host ""

# Extract ZIP
Write-Host "[1/4] Extracting backup archive..."
Expand-Archive -Path $BackupFile -DestinationPath $tempDir -Force
$extractedDir = Get-ChildItem $tempDir | Select-Object -First 1
Write-Host "      OK: Extracted to $extractedDir"

# Check backup info
Write-Host "[2/4] Checking backup info..."
$infoFile = "$extractedDir/backup_info.json"
if (Test-Path $infoFile) {
    $info = Get-Content $infoFile | ConvertFrom-Json
    Write-Host "      Backup time: $($info.backup_time)"
    Write-Host "      DB initialized: $($info.database_initialized)"
    Write-Host "      ChromaDB initialized: $($info.chromadb_initialized)"
} else {
    Write-Host "      WARN: No backup info found"
}

# Restore database
Write-Host "[3/4] Restoring databases..."
if (Test-Path "$extractedDir/backend/cinegraph.db") {
    Copy-Item "$extractedDir/backend/cinegraph.db" "backend/data/cinegraph.db" -Force
    Write-Host "      OK: SQLite database restored"
} else {
    Write-Host "      SKIP: SQLite DB not in backup"
}

if (Test-Path "$extractedDir/data/chroma_db") {
    if (Test-Path "data/chroma_db") {
        Remove-Item "data/chroma_db" -Recurse -Force
    }
    Copy-Item "$extractedDir/data/chroma_db" "data/chroma_db" -Recurse -Force
    Write-Host "      OK: ChromaDB restored"
} else {
    Write-Host "      SKIP: ChromaDB not in backup"
}

# Restore config files
Write-Host "[4/4] Restoring config files..."
$configFiles = @(
    "config/config.yaml",
    "backend/requirements.txt",
    "backend/.env"
)

foreach ($file in $configFiles) {
    $src = "$extractedDir/$file"
    if (Test-Path $src) {
        $destDir = Split-Path $file -Parent
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        Copy-Item $src $file -Force
        Write-Host "      OK: $file"
    }
}

# Cleanup
Remove-Item $tempDir -Recurse -Force

Write-Host ""
Write-Host "================================"
Write-Host "RESTORE COMPLETE!"
Write-Host "================================"
Write-Host "Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
Write-Host ""
Write-Host "Note: Please restart backend and frontend to apply changes."
