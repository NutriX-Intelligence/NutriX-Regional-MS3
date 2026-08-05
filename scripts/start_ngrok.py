import subprocess
import time
import urllib.request
import json
import os
import sys

def start_ngrok():
    authtoken = "3FAbA9nGXcCzkUj1jiUr92QYZym_DJ5ku1gfuRYEQrSPKfw8"
    cmd = ["npx", "--yes", "ngrok", "http", "8080", "--authtoken", authtoken]
    
    print(f"Starting ngrok process: {' '.join(cmd)}")
    # Start the process headlessly
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True
    )
    
    # Let it initialize
    print("Waiting for ngrok to initialize and request tunnel...")
    for i in range(15):
        time.sleep(1)
        # Check if process died
        poll = process.poll()
        if poll is not None:
            stdout, stderr = process.communicate()
            print(f"Ngrok process exited with code {poll}")
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")
            sys.exit(1)
            
        # Try to query the local API
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
                data = json.loads(response.read().decode())
                tunnels = data.get("tunnels", [])
                if tunnels:
                    public_url = tunnels[0].get("public_url")
                    print(f"\n🎉 NGROK TUNNEL STARTED SUCCESSFULLY!")
                    print(f"Public URL: {public_url}\n")
                    # Save to file
                    with open("ngrok_url.txt", "w") as f:
                        f.write(public_url)
                    # Keep script running to maintain the process
                    while True:
                        if process.poll() is not None:
                            print("Ngrok process ended.")
                            break
                        time.sleep(2)
                    return
        except Exception as e:
            # Not ready yet
            print(".", end="", flush=True)
            
    print("\nTimeout: Ngrok did not start or API is not responding on port 4040.")
    # Read any errors
    try:
        stdout, stderr = process.communicate(timeout=2)
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
    except Exception:
        process.terminate()

if __name__ == "__main__":
    start_ngrok()
