import subprocess
import time
import urllib.request
import json
import os
import sys
import argparse

def start_ngrok(port: int = 8000):
    authtoken = "3FAbA9nGXcCzkUj1jiUr92QYZym_DJ5ku1gfuRYEQrSPKfw8"
    local_ngrok = os.path.expandvars(r"%LOCALAPPDATA%\ngrok\ngrok.exe")
    if os.path.exists(local_ngrok):
        ngrok_bin = local_ngrok
    else:
        ngrok_bin = "ngrok"
        
    cmd = [ngrok_bin, "http", str(port), "--authtoken", authtoken, "--log", "stdout"]
    
    print(f"Starting ngrok process for port {port}: {' '.join(cmd)}")
    log_file = open("ngrok.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Let it initialize
    print("Waiting for ngrok to initialize and request tunnel...")
    for i in range(20):
        time.sleep(1)
        # Check if process died
        poll = process.poll()
        if poll is not None:
            log_file.close()
            with open("ngrok.log", "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            print(f"Ngrok process exited with code {poll}\nOutput:\n{content}")
            sys.exit(1)
            
        # Try to query the local API
        try:
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                tunnels = data.get("tunnels", [])
                if tunnels and len(tunnels) > 0:
                    public_url = tunnels[0].get("public_url")
                    if public_url:
                        print(f"\n==========================================", flush=True)
                        print(f"NGROK TUNNEL STARTED SUCCESSFULLY!", flush=True)
                        print(f"Public URL: {public_url}", flush=True)
                        print(f"==========================================\n", flush=True)
                        # Save to file
                        with open("ngrok_url.txt", "w", encoding="utf-8") as f:
                            f.write(public_url)
                            f.flush()
                        # Keep script running to maintain the process
                        while True:
                            if process.poll() is not None:
                                print("Ngrok process ended.", flush=True)
                                break
                            time.sleep(2)
                        return
                print(f"[tunnels={len(tunnels)}]", end="", flush=True)
        except Exception as e:
            # Not ready yet
            print(f"[{type(e).__name__}]", end="", flush=True)
            
    print("\nTimeout: Ngrok did not start or API is not responding on port 4040.")
    log_file.close()
    with open("ngrok.log", "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    print(f"Ngrok Log Output:\n{content}")
    process.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start ngrok tunnel for NutriX")
    parser.add_argument("--port", type=int, default=8000, help="Port to tunnel (default: 8000)")
    args = parser.parse_args()
    start_ngrok(port=args.port)

