# ============================================
# PingPro - Script d'installation FFmpeg
# ============================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installation de FFmpeg pour PingPro" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si FFmpeg est déjà installé
$ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegPath) {
    Write-Host "[OK] FFmpeg est deja installe: $($ffmpegPath.Source)" -ForegroundColor Green
    ffmpeg -version | Select-Object -First 1
    exit 0
}

Write-Host "[INFO] FFmpeg n'est pas installe. Installation en cours..." -ForegroundColor Yellow
Write-Host ""

# Méthode 1: Essayer winget (Windows 10/11)
$wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetAvailable) {
    Write-Host "[INFO] Installation via winget..." -ForegroundColor Cyan
    try {
        winget install --id=Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        
        # Rafraîchir le PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        $ffmpegCheck = Get-Command ffmpeg -ErrorAction SilentlyContinue
        if ($ffmpegCheck) {
            Write-Host "[OK] FFmpeg installe avec succes via winget!" -ForegroundColor Green
            exit 0
        }
    } catch {
        Write-Host "[WARN] Echec installation winget: $_" -ForegroundColor Yellow
    }
}

# Méthode 2: Téléchargement manuel
Write-Host ""
Write-Host "[INFO] Installation manuelle de FFmpeg..." -ForegroundColor Cyan

$ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$downloadPath = "$env:TEMP\ffmpeg.zip"
$extractPath = "$env:LOCALAPPDATA\ffmpeg"
$binPath = "$extractPath\bin"

try {
    # Télécharger FFmpeg
    Write-Host "[INFO] Telechargement de FFmpeg..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $downloadPath -UseBasicParsing
    
    # Extraire
    Write-Host "[INFO] Extraction..." -ForegroundColor Cyan
    if (Test-Path $extractPath) {
        Remove-Item -Recurse -Force $extractPath
    }
    Expand-Archive -Path $downloadPath -DestinationPath $env:LOCALAPPDATA -Force
    
    # Renommer le dossier extrait
    $extractedFolder = Get-ChildItem "$env:LOCALAPPDATA\ffmpeg-*" | Select-Object -First 1
    if ($extractedFolder) {
        Rename-Item -Path $extractedFolder.FullName -NewName "ffmpeg"
    }
    
    $binPath = "$extractPath\bin"
    
    # Ajouter au PATH utilisateur
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$binPath*") {
        Write-Host "[INFO] Ajout de FFmpeg au PATH..." -ForegroundColor Cyan
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$binPath", "User")
        $env:Path = "$env:Path;$binPath"
    }
    
    # Nettoyer
    Remove-Item $downloadPath -Force -ErrorAction SilentlyContinue
    
    # Vérifier l'installation
    $ffmpegExe = "$binPath\ffmpeg.exe"
    if (Test-Path $ffmpegExe) {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Green
        Write-Host "[OK] FFmpeg installe avec succes!" -ForegroundColor Green
        Write-Host "Emplacement: $binPath" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "[INFO] IMPORTANT: Redemarrez votre terminal PowerShell" -ForegroundColor Yellow
        Write-Host "       pour que le PATH soit mis a jour." -ForegroundColor Yellow
        & "$ffmpegExe" -version | Select-Object -First 1
    } else {
        throw "FFmpeg executable non trouve"
    }
    
} catch {
    Write-Host ""
    Write-Host "[ERREUR] Installation automatique echouee: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation manuelle:" -ForegroundColor Yellow
    Write-Host "1. Telechargez FFmpeg depuis: https://ffmpeg.org/download.html" -ForegroundColor White
    Write-Host "2. Choisissez 'Windows builds from gyan.dev'" -ForegroundColor White
    Write-Host "3. Telechargez 'ffmpeg-release-essentials.zip'" -ForegroundColor White
    Write-Host "4. Extrayez dans C:\ffmpeg" -ForegroundColor White
    Write-Host "5. Ajoutez C:\ffmpeg\bin au PATH systeme" -ForegroundColor White
    exit 1
}
