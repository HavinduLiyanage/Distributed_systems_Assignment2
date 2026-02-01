import subprocess
import time
import sys
import os

def launch_system():
    # Get the project root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    scripts = [
        ("Nameserver", ["python", "server/start_nameserver.py"]),
        ("Database Server (BDB)", ["python", "server/bdb_server.py"]),
        ("Application Server (BAS)", ["python", "server/bas_server.py"]),
        ("Client", ["python", "client/bc_client.py"])
    ]
    
    print("=" * 50)
    print("Starting Distributed Banking System Launcher")
    print("=" * 50)
    
    # We use 'start' on Windows to open in a new console window
    for name, cmd in scripts:
        print(f"[*] Launching {name}...")
        
        # 'cmd /c' followed by 'start' command specifically for Windows terminals
        # The first "" after start is the window title
        full_command = f'start "{name}" ' + " ".join(cmd)
        
        try:
            subprocess.Popen(full_command, shell=True, cwd=root_dir)
            # Short delay between launches to allow servers to initialize sequence
            if name != "Client":
                time.sleep(2)
        except Exception as e:
            print(f"[!] Error launching {name}: {e}")

    print("\n[✔] All components have been triggered.")
    print("[i] Check the individual terminal windows for logs and interaction.")
    print("=" * 50)

if __name__ == "__main__":
    launch_system()
