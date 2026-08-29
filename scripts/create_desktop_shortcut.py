import os
import sys

desktop_dir = os.path.expanduser(r"~\Desktop")
if not os.path.exists(desktop_dir):
    desktop_dir = os.path.expandvars(r"%USERPROFILE%\Desktop")

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Start_NutriX_Server.bat on Desktop
bat_path = os.path.join(desktop_dir, "Start_NutriX_Server.bat")
bat_content = f"""@echo off
title NutriX Server & Ngrok Launcher
cd /d "{project_dir}"
python start_server_and_ngrok.py
if errorlevel 1 (
    echo.
    echo Server stopped with an error.
    pause
)
"""
with open(bat_path, "w", encoding="utf-8") as f:
    f.write(bat_content)
print(f"[OK] Created: {bat_path}")

# 2. Start_NutriX_Server.py on Desktop
py_path = os.path.join(desktop_dir, "Start_NutriX_Server.py")
py_content = f'''#!/usr/bin/env python3
import os
import sys

PROJECT_DIR = r"{project_dir}"

if __name__ == "__main__":
    if not os.path.exists(PROJECT_DIR):
        print(f"Error: Project directory not found at {{PROJECT_DIR}}")
        input("\\nPress Enter to exit...")
        sys.exit(1)
    
    os.chdir(PROJECT_DIR)
    sys.path.insert(0, PROJECT_DIR)
    
    try:
        import start_server_and_ngrok
        start_server_and_ngrok.main()
    except Exception as e:
        print(f"Error starting NutriX server: {{e}}")
        input("\\nPress Enter to exit...")
'''
with open(py_path, "w", encoding="utf-8") as f:
    f.write(py_content)
print(f"[OK] Created: {py_path}")

# 3. Create Windows Shortcut (.lnk) on Desktop
try:
    import subprocess
    ps_cmd = f'''
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut('{os.path.join(desktop_dir, "NutriX Ngrok Server.lnk")}')
    $shortcut.TargetPath = '{bat_path}'
    $shortcut.WorkingDirectory = '{project_dir}'
    $shortcut.Description = 'Start NutriX Backend and Ngrok Tunnel'
    $shortcut.Save()
    '''
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
    print(f"[OK] Created Windows Shortcut: {os.path.join(desktop_dir, 'NutriX Ngrok Server.lnk')}")
except Exception as e:
    print(f"Shortcut notice: {e}")

print("All Desktop items created successfully!")
