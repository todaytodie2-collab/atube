# -*- coding: utf-8 -*-
"""
A TuBe Automated Git Sync Engine
Automatically stages, commits, and pushes updates to GitHub repository.
"""

import subprocess
import os
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sync_repo(commit_message=None):
    if not commit_message:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto-Sync Update: {now_str} [A TuBe Engine]"

    try:
        print(f"[Git Sync] Staging files in {BASE_DIR}...")
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True)

        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        if not status.stdout.strip():
            print("[Git Sync] Everything is already up to date. Nothing to commit.")
            return True

        print(f"[Git Sync] Committing with message: '{commit_message}'...")
        subprocess.run(["git", "commit", "-m", commit_message], cwd=BASE_DIR, check=True)

        print("[Git Sync] Pushing to GitHub (origin main)...")
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True)
        if push_res.returncode == 0:
            print("[Git Sync] Successfully synced and pushed to GitHub! 🚀")
            return True
        else:
            print(f"[Git Sync] Push warning: {push_res.stderr}")
            return False

    except Exception as e:
        print(f"[Git Sync] Error during sync: {e}")
        return False

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else None
    sync_repo(msg)
