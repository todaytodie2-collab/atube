#!/usr/bin/env python3
"""
Automated Web-to-APK Assets Synchronizer & Packager for A TuBe
Synchronizes root web assets (HTML, CSS, JS, data, assets) into:
  1. android_app/app/src/main/assets/
  2. Atube_mopile.apk & Atube_tv.apk
  3. android_app/app/build/outputs/apk/
"""

import os
import shutil
import zipfile

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_src = os.path.join(root_dir, 'android_app', 'app', 'src', 'main', 'assets')

    print("[*] Synchronizing web assets into android_app/app/src/main/assets...")
    os.makedirs(assets_src, exist_ok=True)
    for item in ['index.html', 'catalog.json']:
        src = os.path.join(root_dir, item)
        dst = os.path.join(assets_src, item)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    for folder in ['css', 'js', 'data', 'assets']:
        src = os.path.join(root_dir, folder)
        dst = os.path.join(assets_src, folder)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # Build injection mapping
    files_to_inject = {}
    for r, _, files in os.walk(assets_src):
        for f in files:
            full_path = os.path.join(r, f)
            rel_path = os.path.relpath(full_path, assets_src).replace('\\', '/')
            files_to_inject['assets/' + rel_path] = full_path

    target_apks = [
        os.path.join(root_dir, 'Atube_mopile.apk'),
        os.path.join(root_dir, 'Atube_tv.apk'),
        os.path.join(root_dir, 'android_app', 'app', 'build', 'outputs', 'apk', 'mobile', 'debug', 'app-mobile-debug.apk'),
        os.path.join(root_dir, 'android_app', 'app', 'build', 'outputs', 'apk', 'tv', 'debug', 'app-tv-debug.apk'),
        os.path.join(root_dir, 'android_app', 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk'),
    ]

    for apk in target_apks:
        if not os.path.exists(apk):
            continue
        temp_apk = apk + '.tmp'
        file_contents = {}
        with zipfile.ZipFile(apk, 'r') as zin:
            for name in zin.namelist():
                file_contents[name] = zin.read(name)

        # Update / add files
        for apk_path, disk_path in files_to_inject.items():
            with open(disk_path, 'rb') as f:
                file_contents[apk_path] = f.read()

        with zipfile.ZipFile(temp_apk, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in file_contents.items():
                zout.writestr(name, data)

        os.replace(temp_apk, apk)
        print(f"[+] Successfully packaged {os.path.basename(apk)} ({os.path.getsize(apk):,} bytes)")

    print("[OK] All APKs synchronized and ready!")

if __name__ == '__main__':
    main()
