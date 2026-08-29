#!/usr/bin/env python3
"""
NutriX - Double-Click Server & Ngrok Launcher
=============================================
This script starts both the NutriX backend server and the ngrok tunnel,
prints the public URL, and keeps running until you close the window.
"""

import os
import sys
import time
import json
import signal
import socket
import subprocess
import urllib.request
import urllib.error

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure working directory is always the script's folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

AUTHTOKEN = "3FAbA9nGXcCzkUj1jiUr92QYZym_DJ5ku1gfuRYEQrSPKfw8"
PORT = 8000

backend_process = None
ngrok_process = None


def is_port_in_use(port: int) -> bool:
    """Check if a local TCP port is already open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_ngrok_binary() -> str:
    """Find the path to the ngrok executable."""
    local_ngrok = os.path.expandvars(r"%LOCALAPPDATA%\ngrok\ngrok.exe")
    if os.path.exists(local_ngrok):
        return local_ngrok
    
    # Check if ngrok is on system PATH
    try:
        res = subprocess.run(["where", "ngrok"], capture_output=True, text=True, shell=False, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().splitlines()[0]
    except Exception:
        pass
    
    return "ngrok"


def start_backend():
    """Start the NutriX FastAPI / Uvicorn server if not already running."""
    global backend_process
    if is_port_in_use(PORT):
        print(f"[+] NutriX backend is already running on port {PORT}.")
        return

    print(f"[*] Starting NutriX backend server on port {PORT}...")
    backend_cmd = [sys.executable, "run.py", "--port", str(PORT)]
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait for backend to come online
    print("    Waiting for backend to respond...", end="", flush=True)
    for _ in range(30):
        time.sleep(1)
        if is_port_in_use(PORT):
            print(" Ready!")
            return
        print(".", end="", flush=True)
    
    print("\n[!] Warning: Backend server took longer than expected to start.")


def start_ngrok_tunnel(ngrok_bin: str) -> str:
    """Start ngrok and return the public URL."""
    global ngrok_process
    
    # Check if ngrok API is already running
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            tunnels = data.get("tunnels", [])
            if tunnels:
                return tunnels[0].get("public_url", "")
    except Exception:
        pass

    log_path = os.path.join(BASE_DIR, "ngrok.log")
    log_file = open(log_path, "w", encoding="utf-8")

    cmd = [ngrok_bin, "http", str(PORT), "--authtoken", AUTHTOKEN, "--log", "stdout"]
    print(f"[*] Starting ngrok tunnel on port {PORT}...")
    
    ngrok_process = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True
    )

    print("    Waiting for ngrok tunnel creation...", end="", flush=True)
    for _ in range(25):
        time.sleep(1)
        
        # Check if process terminated unexpectedly
        if ngrok_process.poll() is not None:
            log_file.close()
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                err_content = f.read()
            raise RuntimeError(f"Ngrok exited with code {ngrok_process.poll()}.\nLog:\n{err_content}")

        try:
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                tunnels = data.get("tunnels", [])
                if tunnels and len(tunnels) > 0:
                    public_url = tunnels[0].get("public_url")
                    if public_url:
                        print(" Ready!")
                        # Save URL to file
                        with open(os.path.join(BASE_DIR, "ngrok_url.txt"), "w", encoding="utf-8") as f:
                            f.write(public_url)
                        return public_url
        except Exception:
            print(".", end="", flush=True)

    raise TimeoutError("Timeout: ngrok did not return a tunnel URL within 25 seconds.")


def cleanup():
    """Clean up running child processes."""
    print("\n[*] Shutting down servers...")
    if ngrok_process:
        try:
            ngrok_process.terminate()
            ngrok_process.wait(timeout=2)
        except Exception:
            pass
    if backend_process:
        try:
            backend_process.terminate()
            backend_process.wait(timeout=2)
        except Exception:
            pass
    print("[+] Stopped all processes.")


def main():
    try:
        # Title for Windows Command Prompt window
        if sys.platform == "win32":
            os.system("title NutriX Server & Ngrok Tunnel")

        border = "=" * 62
        print(f"\n{border}")
        print("          NUTRIX AI DIET PLANNER - SERVER LAUNCHER          ")
        print(f"{border}\n")

        # 1. Start Backend
        start_backend()

        # 2. Find Ngrok
        ngrok_bin = find_ngrok_binary()

        # 3. Start Ngrok Tunnel
        public_url = start_ngrok_tunnel(ngrok_bin)

        # 4. Display Status Dashboard
        print(f"\n{border}")
        print("                 NGROK SERVER IS RUNNING!                  ")
        print(f"{border}")
        print(f"  * Public Ngrok URL : {public_url}")
        print(f"  * API Swagger Docs : {public_url}/docs")
        print(f"  * Local Server     : http://127.0.0.1:{PORT}")
        print(f"  * Ngrok Inspector  : http://127.0.0.1:4040")
        print(f"  * URL saved to     : ngrok_url.txt")
        print(f"{border}")
        print("\n [INFO] Leave this process running to keep the server online.")
        print(" [INFO] Press Ctrl+C anytime to stop.\n")

        # Keep alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Stopping by user request...")
    except Exception as e:
        print(f"\n[X] Error: {e}")
    finally:
        cleanup()
        if sys.stdin and sys.stdin.isatty():
            try:
                input("\nPress Enter to exit...")
            except Exception:
                pass


if __name__ == "__main__":
    main()

