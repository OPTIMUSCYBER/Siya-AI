import os
import subprocess
import sys

def register_startup():
    current_dir = os.path.abspath(os.path.dirname(__file__))
    # Try to find pythonw.exe, fallback to python.exe if not found (though it should be next to it)
    python_exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable
        
    script_path = os.path.join(current_dir, "main.py")
    
    # We need to wrap the whole command nicely. 
    # To set working directory for a scheduled task via schtasks is tricky via CLI alone.
    # An alternative is a batch file or modifying XML, but since this script uses absolute paths, 
    # it might be okay. However, config.yaml expects to be in the current directory.
    # So we'll run cmd /c start /d "current_dir" pythonw.exe main.py
    
    # Actually, let's just make main.py change its working dir to its own location.
    
    command = [
        "schtasks", "/Create",
        "/TN", "SiyaPCAI",
        "/TR", f'"{python_exe}" "{script_path}"',
        "/SC", "ONLOGON",
        "/F"
    ]
    
    print(f"Executing: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
        print("Task 'SiyaPCAI' successfully registered to run at logon.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to register task: {e}")

def remove_startup():
    command = ["schtasks", "/Delete", "/TN", "SiyaPCAI", "/F"]
    try:
        subprocess.run(command, check=True)
        print("Task 'SiyaPCAI' successfully removed.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to remove task: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_startup()
    else:
        print("Run 'python install_startup.py remove' to remove the task.")
        register_startup()
