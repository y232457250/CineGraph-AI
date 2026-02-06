# CineGraph-AI Project Backup Script
# Backup Time: $((Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "backup/backup_$timestamp"
$logFile = "$backupDir/backup_log.txt"

Write-Host "Starting backup..."
Write-Host "Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
Write-Host "Backup dir: $backupDir"
Write-Host ""

# Create backup directories
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
New-Item -ItemType Directory -Force -Path "$backupDir/data" | Out-Null
New-Item -ItemType Directory -Force -Path "$backupDir/backend" | Out-Null
New-Item -ItemType Directory -Force -Path "$backupDir/config" | Out-Null
New-Item -ItemType Directory -Force -Path "$backupDir/frontend-ui" | Out-Null

# Log header
"CineGraph-AI Backup Log" | Out-File -FilePath $logFile -Encoding UTF8
"========================" | Out-File -FilePath $logFile -Append -Encoding UTF8
"Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")" | Out-File -FilePath $logFile -Append -Encoding UTF8
"Version: $timestamp" | Out-File -FilePath $logFile -Append -Encoding UTF8
"" | Out-File -FilePath $logFile -Append -Encoding UTF8

# 1. Backup SQLite DB
Write-Host "[1/6] Backup SQLite database..."
if (Test-Path "backend/data/cinegraph.db") {
    Copy-Item "backend/data/cinegraph.db" "$backupDir/backend/cinegraph.db" -Force
    $dbSize = (Get-Item "backend/data/cinegraph.db").Length / 1KB
    "[OK] SQLite DB: backend/data/cinegraph.db ($([math]::Round($dbSize, 2)) KB)" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Write-Host "      OK: cinegraph.db ($([math]::Round($dbSize, 2)) KB)"
} else {
    "[WARN] SQLite DB not found" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Write-Host "      WARN: DB not found"
}

# 2. Backup ChromaDB
Write-Host "[2/6] Backup ChromaDB..."
if (Test-Path "data/chroma_db") {
    Copy-Item "data/chroma_db" "$backupDir/data/chroma_db" -Recurse -Force
    $chromaSize = (Get-ChildItem "data/chroma_db" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    "[OK] ChromaDB: data/chroma_db ($([math]::Round($chromaSize, 2)) MB)" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Write-Host "      OK: chroma_db ($([math]::Round($chromaSize, 2)) MB)"
} else {
    "[WARN] ChromaDB not found" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Write-Host "      WARN: ChromaDB not found"
}

# 3. Backup config files
Write-Host "[3/6] Backup config files..."
$configFiles = @(
    "config/config.yaml",
    "backend/requirements.txt",
    "backend/.env",
    "requirements.txt",
    "package.json"
)

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        $destDir = Split-Path "$backupDir/$file" -Parent
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        Copy-Item $file "$backupDir/$file" -Force
        "[OK] Config: $file" | Out-File -FilePath $logFile -Append -Encoding UTF8
        Write-Host "      OK: $file"
    } else {
        "[SKIP] Not found: $file" | Out-File -FilePath $logFile -Append -Encoding UTF8
    }
}

# 4. Backup data files
Write-Host "[4/6] Backup data files..."
$dataPatterns = @(
    "data/analysis/*.json",
    "data/annotations/**/*",
    "data/media/*",
    "data/subtitles/*"
)

foreach ($pattern in $dataPatterns) {
    $files = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
        $destPath = "$backupDir/$relativePath"
        $destDir = Split-Path $destPath -Parent
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        Copy-Item $file.FullName $destPath -Force
    }
}
$dataFileCount = (Get-ChildItem "$backupDir/data" -Recurse -File -ErrorAction SilentlyContinue).Count
"[OK] Data files: $dataFileCount files" | Out-File -FilePath $logFile -Append -Encoding UTF8
Write-Host "      OK: $dataFileCount data files"

# 5. Backup source code
Write-Host "[5/6] Backup source code..."
$sourcePatterns = @(
    "backend/app/**/*.py",
    "backend/main.py",
    "frontend-ui/src/**/*",
    "frontend-ui/*.html",
    "frontend-ui/*.js",
    "frontend-ui/*.css"
)

foreach ($pattern in $sourcePatterns) {
    $files = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
        $destPath = "$backupDir/$relativePath"
        $destDir = Split-Path $destPath -Parent
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        Copy-Item $file.FullName $destPath -Force
    }
}

$backendFileCount = if (Test-Path "$backupDir/backend") { (Get-ChildItem "$backupDir/backend" -Recurse -File).Count } else { 0 }
$frontendFileCount = if (Test-Path "$backupDir/frontend-ui") { (Get-ChildItem "$backupDir/frontend-ui" -Recurse -File).Count } else { 0 }
"[OK] Backend: $backendFileCount files" | Out-File -FilePath $logFile -Append -Encoding UTF8
"[OK] Frontend: $frontendFileCount files" | Out-File -FilePath $logFile -Append -Encoding UTF8
Write-Host "      OK: $backendFileCount backend files"
Write-Host "      OK: $frontendFileCount frontend files"

# 6. Create backup info JSON
$backupInfo = @{
    backup_time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    backup_version = $timestamp
    project_name = "CineGraph-AI"
    database_initialized = Test-Path "backend/data/cinegraph.db"
    chromadb_initialized = Test-Path "data/chroma_db"
}
$backupInfo | ConvertTo-Json | Out-File -FilePath "$backupDir/backup_info.json" -Encoding UTF8

# Calculate total size
$totalSize = (Get-ChildItem $backupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
"" | Out-File -FilePath $logFile -Append -Encoding UTF8
"========================" | Out-File -FilePath $logFile -Append -Encoding UTF8
"Total backup size: $([math]::Round($totalSize, 2)) MB" | Out-File -FilePath $logFile -Append -Encoding UTF8
"Completed: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")" | Out-File -FilePath $logFile -Append -Encoding UTF8

# Create ZIP
Write-Host ""
Write-Host "[6/6] Creating ZIP archive..."
$zipPath = "backup/backup_$timestamp.zip"
Compress-Archive -Path $backupDir -DestinationPath $zipPath -Force
$zipSize = (Get-Item $zipPath).Length / 1MB
Write-Host "      OK: $zipPath ($([math]::Round($zipSize, 2)) MB)"

# Cleanup temp dir
Remove-Item $backupDir -Recurse -Force

# Summary
Write-Host ""
Write-Host "========================"
Write-Host "BACKUP COMPLETE!"
Write-Host "========================"
Write-Host "File: $zipPath"
Write-Host "Size: $([math]::Round($zipSize, 2)) MB"
Write-Host "Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
Write-Host ""
