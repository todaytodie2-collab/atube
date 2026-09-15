# -*- coding: utf-8 -*-
"""
A TuBe Native APK Compiler Engine
Builds 2 Dedicated Production APKs:
1. ATuBe-Mobile-v1.0.apk (Smartphones & Tablets - Touch Optimized + Full HD Playback)
2. ATuBe-TV-v1.0.apk (Android TV & Smart Box - Leanback Banner + Full D-Pad Remote Navigation)
"""

import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import shutil
import subprocess
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDK_DIR = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or r"C:\Android\Sdk"
BUILD_TOOLS_DIR = os.path.join(SDK_DIR, "build-tools", "35.0.0")
PLATFORM_JAR = os.path.join(SDK_DIR, "platforms", "android-35", "android.jar")

java_home = os.environ.get("JAVA_HOME")
if java_home and os.path.exists(os.path.join(java_home, "bin")):
    JDK_BIN = os.path.join(java_home, "bin")
else:
    JDK_BIN = r"C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot\bin"

AAPT2 = os.path.join(BUILD_TOOLS_DIR, "aapt2.exe")
D8 = os.path.join(BUILD_TOOLS_DIR, "d8.bat")
ZIPALIGN = os.path.join(BUILD_TOOLS_DIR, "zipalign.exe")
APKSIGNER = os.path.join(BUILD_TOOLS_DIR, "apksigner.bat")
JAVAC = os.path.join(JDK_BIN, "javac.exe")
KEYTOOL = os.path.join(JDK_BIN, "keytool.exe")

KEYSTORE_PATH = os.path.join(BASE_DIR, "scripts", "atube_release.keystore")
KS_PASS = "atube2026"
KS_ALIAS = "atube"


def ensure_keystore():
    if not os.path.exists(KEYSTORE_PATH):
        print("[Keystore] Generating Android Release Keystore...")
        cmd = [
            KEYTOOL, "-genkeypair", "-v",
            "-keystore", KEYSTORE_PATH,
            "-alias", KS_ALIAS,
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-storepass", KS_PASS,
            "-keypass", KS_PASS,
            "-dname", "CN=ATuBe, OU=Media, O=ATuBe, L=Cairo, ST=Cairo, C=EG"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print("[Keystore] Keystore generated successfully.")


def generate_png_icon(filepath, width, height, bg_color=(4, 9, 14), text_color=(0, 229, 255)):
    """Creates a raw uncompressed PNG image without external dependencies."""
    import zlib
    import struct

    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # filter type 0 (None)
        for x in range(width):
            is_border = (x < 4 or x >= width - 4 or y < 4 or y >= height - 4)
            cx, cy = width // 2, height // 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            is_center = (dist < min(width, height) // 3)

            if is_border:
                raw_data.extend(text_color)
                raw_data.append(255)
            elif is_center:
                raw_data.extend(text_color)
                raw_data.append(255)
            else:
                raw_data.extend(bg_color)
                raw_data.append(255)

    compressed = zlib.compress(raw_data)
    
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    png.extend(struct.pack('>I', len(ihdr_data)))
    png.extend(b'IHDR')
    png.extend(ihdr_data)
    png.extend(ihdr_crc)
    
    idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff)
    png.extend(struct.pack('>I', len(compressed)))
    png.extend(b'IDAT')
    png.extend(compressed)
    png.extend(idat_crc)
    
    iend_crc = struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    png.extend(struct.pack('>I', 0))
    png.extend(b'IEND')
    png.extend(iend_crc)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(png)


def build_variant(is_tv=False):
    target_name = "ATuBe-TV-v1.0.apk" if is_tv else "ATuBe-Mobile-v1.0.apk"
    app_label = "A TuBe TV" if is_tv else "A TuBe"
    pkg_name = "com.atube.tv" if is_tv else "com.atube.media"
    
    print(f"\n=================================================================")
    print(f"[Build] Building {app_label} ({target_name})...")
    print(f"=================================================================")

    build_dir = os.path.join(BASE_DIR, "build", "tv" if is_tv else "mobile")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir, exist_ok=True)

    res_dir = os.path.join(build_dir, "res")
    values_dir = os.path.join(res_dir, "values")
    drawable_dir = os.path.join(res_dir, "drawable")
    os.makedirs(values_dir, exist_ok=True)
    os.makedirs(drawable_dir, exist_ok=True)

    # 1. Generate Icons & Banners
    icon_path = os.path.join(drawable_dir, "ic_launcher.png")
    generate_png_icon(icon_path, 192, 192, bg_color=(6, 19, 24), text_color=(0, 229, 255))

    banner_path = os.path.join(drawable_dir, "tv_banner.png")
    generate_png_icon(banner_path, 320, 180, bg_color=(6, 19, 24), text_color=(255, 42, 68))

    # 2. Generate strings.xml and styles.xml
    with open(os.path.join(values_dir, "strings.xml"), "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{app_label}</string>
</resources>''')

    with open(os.path.join(values_dir, "styles.xml"), "w", encoding="utf-8") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.NoTitleBar.Fullscreen">
        <item name="android:windowBackground">@android:color/black</item>
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowFullscreen">true</item>
    </style>
</resources>''')

    # 3. AndroidManifest.xml
    manifest_path = os.path.join(build_dir, "AndroidManifest.xml")
    tv_features = '''
    <uses-feature android:name="android.software.leanback" android:required="false" />
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />
    <uses-feature android:name="android.hardware.gamepad" android:required="false" />
    ''' if is_tv else ''

    leanback_intent = '''
                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
    ''' if is_tv else ''

    banner_attr = 'android:banner="@drawable/tv_banner"' if is_tv else ''

    manifest_content = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg_name}"
    android:versionCode="1"
    android:versionName="1.0.0">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    {tv_features}

    <application
        android:label="@string/app_name"
        android:icon="@drawable/ic_launcher"
        {banner_attr}
        android:theme="@style/AppTheme"
        android:hardwareAccelerated="true"
        android:usesCleartextTraffic="true"
        android:largeHeap="true">
        <activity
            android:name="{pkg_name}.MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden|smallestScreenSize|screenLayout"
            android:screenOrientation="{'sensorLandscape' if is_tv else 'unspecified'}"
            android:windowSoftInputMode="adjustPan">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
                {leanback_intent}
            </intent-filter>
        </activity>
    </application>
</manifest>'''

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    # 4. Copy Web Assets into assets/
    assets_dir = os.path.join(build_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Copy files
    for item in ["index.html", "manifest.json", "sw.js"]:
        src = os.path.join(BASE_DIR, item)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(assets_dir, item))

    # Copy directories
    for folder in ["css", "js", "data", "assets"]:
        src_dir = os.path.join(BASE_DIR, folder)
        dst_dir = os.path.join(assets_dir, folder)
        if os.path.exists(src_dir):
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    print("[Assets] Web assets assembled into APK bundle.")

    # 5. Compile Android Resources (aapt2 compile)
    compiled_res_zip = os.path.join(build_dir, "compiled_res.zip")
    cmd_compile = [AAPT2, "compile", "--dir", res_dir, "-o", compiled_res_zip]
    subprocess.run(cmd_compile, check=True)

    # 6. Link Resources (aapt2 link)
    unaligned_apk = os.path.join(build_dir, "app-unaligned.apk")
    gen_src_dir = os.path.join(build_dir, "gen")
    os.makedirs(gen_src_dir, exist_ok=True)

    cmd_link = [
        AAPT2, "link",
        "-I", PLATFORM_JAR,
        "-A", assets_dir,
        "--manifest", manifest_path,
        "--java", gen_src_dir,
        "-o", unaligned_apk,
        "--auto-add-overlay",
        compiled_res_zip
    ]
    subprocess.run(cmd_link, check=True)
    print("[AAPT2] Android resources linked successfully.")

    # 7. Write MainActivity.java
    src_pkg_dir = os.path.join(build_dir, "src", *pkg_name.split("."))
    os.makedirs(src_pkg_dir, exist_ok=True)
    java_file = os.path.join(src_pkg_dir, "MainActivity.java")

    java_template = """package __PKG_NAME__;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;
    private FrameLayout customViewContainer;
    private WebChromeClient.CustomViewCallback customViewCallback;
    private View customView;
    private static final boolean IS_TV = __IS_TV__;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().getDecorView().setBackgroundColor(Color.parseColor("#04090e"));

        FrameLayout rootLayout = new FrameLayout(this);
        rootLayout.setBackgroundColor(Color.parseColor("#04090e"));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#04090e"));

        customViewContainer = new FrameLayout(this);
        customViewContainer.setVisibility(View.GONE);
        customViewContainer.setBackgroundColor(Color.BLACK);

        rootLayout.addView(webView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        rootLayout.addView(customViewContainer, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        setContentView(rootLayout);
        setupWebView();
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUserAgentString("Mozilla/5.0 (Linux; Android 14; Mobile; rv:124.0) Gecko/124.0 Firefox/124.0 A-TuBe-Player/1.0");

        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void showToast(final String message) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show();
                    }
                });
            }

            @JavascriptInterface
            public boolean isAndroidTV() {
                return IS_TV;
            }

            @JavascriptInterface
            public void closeApp() {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        finish();
                    }
                });
            }
        }, "AndroidBridge");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                request.grant(request.getResources());
            }

            @Override
            public void onShowCustomView(View view, CustomViewCallback callback) {
                if (customView != null) {
                    callback.onCustomViewHidden();
                    return;
                }
                customView = view;
                customViewCallback = callback;
                webView.setVisibility(View.GONE);
                customViewContainer.addView(view);
                customViewContainer.setVisibility(View.VISIBLE);
            }

            @Override
            public void onHideCustomView() {
                if (customView == null) return;
                customViewContainer.removeView(customView);
                customView = null;
                customViewContainer.setVisibility(View.GONE);
                if (customViewCallback != null) customViewCallback.onCustomViewHidden();
                webView.setVisibility(View.VISIBLE);
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                return true;
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }
        });
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (customView != null) {
                customViewContainer.removeView(customView);
                customView = null;
                customViewContainer.setVisibility(View.GONE);
                webView.setVisibility(View.VISIBLE);
                return true;
            }
            webView.evaluateJavascript("if (typeof window.onAndroidBackPressed === 'function') { window.onAndroidBackPressed(); } else if (window.history.length > 1) { window.history.back(); }", null);
            return true;
        }

        String jsKey = null;
        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_UP: jsKey = "ArrowUp"; break;
            case KeyEvent.KEYCODE_DPAD_DOWN: jsKey = "ArrowDown"; break;
            case KeyEvent.KEYCODE_DPAD_LEFT: jsKey = "ArrowLeft"; break;
            case KeyEvent.KEYCODE_DPAD_RIGHT: jsKey = "ArrowRight"; break;
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
            case KeyEvent.KEYCODE_NUMPAD_ENTER: jsKey = "Enter"; break;
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
            case KeyEvent.KEYCODE_MEDIA_PLAY:
            case KeyEvent.KEYCODE_MEDIA_PAUSE: jsKey = " "; break;
            case KeyEvent.KEYCODE_MEDIA_FAST_FORWARD: jsKey = "ArrowRight"; break;
            case KeyEvent.KEYCODE_MEDIA_REWIND: jsKey = "ArrowLeft"; break;
        }

        if (jsKey != null) {
            final String k = jsKey;
            final int code = keyCode;
            webView.evaluateJavascript("window.dispatchEvent(new KeyboardEvent('keydown', { key: '" + k + "', keyCode: " + code + ", bubbles: true }));", null);
            return true;
        }

        return super.onKeyDown(keyCode, event);
    }
}"""
    java_code = java_template.replace("__PKG_NAME__", pkg_name).replace("__IS_TV__", str(is_tv).lower())

    with open(java_file, "w", encoding="utf-8") as f:
        f.write(java_code)

    # 8. Compile Java Sources (javac)
    classes_dir = os.path.join(build_dir, "classes")
    os.makedirs(classes_dir, exist_ok=True)

    java_files = []
    for root, _, files in os.walk(build_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))

    cmd_javac = [
        JAVAC,
        "-cp", PLATFORM_JAR,
        "-d", classes_dir,
        *java_files
    ]
    subprocess.run(cmd_javac, check=True)
    print("[JAVAC] Java code compiled to bytecode.")

    # 9. Convert Bytecode to DEX (d8)
    dex_dir = os.path.join(build_dir, "dex")
    os.makedirs(dex_dir, exist_ok=True)

    class_files = []
    for root, _, files in os.walk(classes_dir):
        for file in files:
            if file.endswith(".class"):
                class_files.append(os.path.join(root, file))

    cmd_d8 = [
        D8,
        "--lib", PLATFORM_JAR,
        "--output", dex_dir,
        *class_files
    ]
    subprocess.run(cmd_d8, check=True, shell=True)
    print("[D8] Classes converted to Dalvik Executable (classes.dex).")

    # 10. Inject classes.dex into unaligned APK
    dex_file = os.path.join(dex_dir, "classes.dex")
    with zipfile.ZipFile(unaligned_apk, "a") as z:
        z.write(dex_file, "classes.dex")

    # 11. Zipalign APK
    aligned_apk = os.path.join(build_dir, "app-aligned.apk")
    cmd_zipalign = [ZIPALIGN, "-f", "-p", "4", unaligned_apk, aligned_apk]
    subprocess.run(cmd_zipalign, check=True)
    print("[ZIPALIGN] APK 4-byte zipaligned.")

    # 12. Sign APK with apksigner
    final_apk = os.path.join(BASE_DIR, target_name)
    if os.path.exists(final_apk):
        os.remove(final_apk)

    cmd_sign = [
        APKSIGNER, "sign",
        "--ks", KEYSTORE_PATH,
        "--ks-pass", f"pass:{KS_PASS}",
        "--ks-key-alias", KS_ALIAS,
        "--key-pass", f"pass:{KS_PASS}",
        "--out", final_apk,
        aligned_apk
    ]
    subprocess.run(cmd_sign, check=True, shell=True)
    print(f"[SUCCESS] Generated Signed Production APK: {final_apk}")
    print(f"[SIZE] File Size: {os.path.getsize(final_apk) / (1024 * 1024):.2f} MB\n")
    return final_apk


def main():
    ensure_keystore()
    
    # 1. Build Mobile APK
    mobile_apk = build_variant(is_tv=False)
    
    # 2. Build Android TV APK
    tv_apk = build_variant(is_tv=True)

    print("=================================================================")
    print("ALL PRODUCTION APKS BUILT & SIGNED SUCCESSFULLY:")
    print(f"1. Mobile & Tablet APK: {mobile_apk}")
    print(f"2. Android TV & Box APK: {tv_apk}")
    print("=================================================================")


if __name__ == "__main__":
    main()
