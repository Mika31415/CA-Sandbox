"""
Clone the Repo for Pydroid
"""
import os
from dulwich import porcelain

REPO_URL = "https://github.com/Mika31415/CA-Sandbox.git"
LOCAL_PATH = "/storage/emulated/0/Download/CA-Sandbox/CA-Sandbox-main" 

if os.path.isdir(os.path.join(LOCAL_PATH, ".git")):
    print("Repo exists, get updated version...")
    porcelain.pull(LOCAL_PATH, REPO_URL)
    print("Ready!")
else:
    print("Clone Repo...")
    porcelain.clone(REPO_URL, LOCAL_PATH)
    print("Ready!")

input("Ready, Press enter to close...")