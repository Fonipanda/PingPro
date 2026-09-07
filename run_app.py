#!/usr/bin/env python3
"""
PingPro - Script de lancement unifié
Lance le backend FastAPI et le frontend React simultanément.
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path
import threading
import platform

ROOT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

IS_WINDOWS = platform.system() == "Windows"

processes = []


def print_banner():
    """Affiche la bannière PingPro"""
    print("\n" + "=" * 60)
    print("""
    🏓 PingPro - Analyse Video Tennis de Table
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)
    print("=" * 60 + "\n")


def check_requirements():
    """Vérifie que les prérequis sont installés"""
    errors = []
    
    if not BACKEND_DIR.exists():
        errors.append(f"Dossier backend introuvable: {BACKEND_DIR}")
    
    if not FRONTEND_DIR.exists():
        errors.append(f"Dossier frontend introuvable: {FRONTEND_DIR}")
    
    server_py = BACKEND_DIR / "server.py"
    if not server_py.exists():
        errors.append(f"Fichier server.py introuvable: {server_py}")
    
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        errors.append(f"Fichier package.json introuvable: {package_json}")
    
    if errors:
        print("❌ Erreurs de configuration:")
        for e in errors:
            print(f"   - {e}")
        return False
    
    return True


def run_backend():
    """Lance le serveur backend FastAPI"""
    print("🚀 Démarrage du backend FastAPI sur http://localhost:8080")
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    venv_python = BACKEND_DIR / "venv" / "Scripts" / "python.exe" if IS_WINDOWS else BACKEND_DIR / "venv" / "bin" / "python"
    
    if venv_python.exists():
        python_exe = str(venv_python)
    else:
        python_exe = "python"
    
    cmd = [python_exe, "-m", "uvicorn", "server:app", "--reload", "--port", "8080", "--host", "0.0.0.0"]
    
    process = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(process)
    
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"[BACKEND] {line.rstrip()}")
    
    return process


def run_frontend():
    """Lance le serveur frontend React"""
    print("🎨 Démarrage du frontend React sur http://localhost:3000")
    
    env = os.environ.copy()
    env["BROWSER"] = "none"
    env["CI"] = "true"
    
    if IS_WINDOWS:
        cmd = ["cmd", "/c", "yarn", "start"]
    else:
        cmd = ["yarn", "start"]
    
    process = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=IS_WINDOWS
    )
    processes.append(process)
    
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"[FRONTEND] {line.rstrip()}")
    
    return process


def cleanup(signum=None, frame=None):
    """Nettoie les processus à l'arrêt"""
    print("\n\n🛑 Arrêt de PingPro...")
    
    for proc in processes:
        try:
            if IS_WINDOWS:
                proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
    
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    
    print("✅ PingPro arrêté proprement.")
    sys.exit(0)


def main():
    """Point d'entrée principal"""
    print_banner()
    
    if not check_requirements():
        sys.exit(1)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("📦 Lancement des services...\n")
    
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    time.sleep(3)
    
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()
    
    print("\n" + "=" * 60)
    print("""
    ✅ PingPro est prêt !
    
    🌐 Frontend : http://localhost:3000
    🔧 Backend  : http://localhost:8080
    📚 API Docs : http://localhost:8080/docs
    
    Appuyez sur Ctrl+C pour arrêter.
    """)
    print("=" * 60 + "\n")
    
    try:
        while True:
            time.sleep(1)
            
            for proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️ Un processus s'est arrêté (code: {proc.returncode})")
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
