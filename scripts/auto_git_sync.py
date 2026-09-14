# -*- coding: utf-8 -*-
"""
A TuBe - Continuous Real-Time Git Auto-Sync Daemon
Monitors the codebase for any modifications or new files,
automatically commits them, and pushes them to GitHub in real-time.
"""

import os
import sys
import time
import subprocess
import threading

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AutoGitSync:
    _running = False
    _lock = threading.Lock()

    @classmethod
    def get_status(cls):
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            return res.stdout.strip()
        except Exception:
            return ""

    @classmethod
    def sync_once(cls):
        with cls._lock:
            # Check if there are changes
            status = cls.get_status()
            if not status:
                return False

            print(f"\n[AutoSync] Detected code changes:\n{status}")
            print("[AutoSync] Staging and syncing to GitHub...")

            try:
                # 1. Add all changed files except cache/locks
                subprocess.run(["git", "add", "-A"], cwd=BASE_DIR, check=True)

                # 2. Commit with meaningful timestamp
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                msg = f"auto(sync): update codebase and assets [{now_str}]"
                subprocess.run(["git", "commit", "-m", msg], cwd=BASE_DIR, check=True)

                # 3. Pull rebase to handle remote bot updates
                subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=BASE_DIR, check=False)

                # 4. Push to origin main
                push_res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True)
                if push_res.returncode == 0:
                    print(f"[AutoSync] ✓ Successfully pushed updates to GitHub at {now_str}")
                    return True
                else:
                    print(f"[AutoSync] ⚠️ Push notice: {push_res.stderr.strip()}")
                    return False
            except Exception as e:
                print(f"[AutoSync] Error during sync: {e}")
                return False

    @classmethod
    def start_watcher(cls, interval_seconds: int = 25):
        """Watches for changes continuously in a background loop."""
        cls._running = True
        print(f"=== A TuBe Real-Time Git Auto-Sync Active ===")
        print(f"Watching for code modifications every {interval_seconds}s...")

        while cls._running:
            try:
                if cls.get_status():
                    # Debounce 10 seconds to allow all file writes in a batch to settle
                    time.sleep(10)
                    cls.sync_once()
            except Exception as e:
                print(f"[AutoSync] Watcher loop note: {e}")

            time.sleep(interval_seconds)

    @classmethod
    def stop(cls):
        cls._running = False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A TuBe Auto Git Sync")
    parser.add_argument("--once", action="store_true", help="Sync once if changes exist and exit")
    parser.add_argument("--interval", type=int, default=25, help="Check interval in seconds (default 25s)")
    args = parser.parse_args()

    if args.once:
        synced = AutoGitSync.sync_once()
        print("Done." if synced else "No changes to sync.")
    else:
        AutoGitSync.start_watcher(interval_seconds=args.interval)
