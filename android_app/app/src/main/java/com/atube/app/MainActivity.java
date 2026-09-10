package com.atube.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.JavascriptInterface;
import android.widget.FrameLayout;
import android.widget.Toast;
import androidx.activity.ComponentActivity;
import androidx.activity.OnBackPressedCallback;
import androidx.core.splashscreen.SplashScreen;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;

public class MainActivity extends ComponentActivity {
    private WebView mWebView;
    
    // Variables for Fullscreen Video
    private View mCustomView;
    private WebChromeClient.CustomViewCallback mCustomViewCallback;
    private FrameLayout mFullscreenContainer;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // 1. Modern Android 12+ Splash Screen API
        SplashScreen.installSplashScreen(this);
        
        super.onCreate(savedInstanceState);

        // 2. Cinematic Fullscreen Immersive Mode & Edge-to-Edge for Smart TVs & Mobile
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        
        // Hide System Bars completely (Immersive Sticky Mode)
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        WindowInsetsControllerCompat windowInsetsController = new WindowInsetsControllerCompat(getWindow(), getWindow().getDecorView());
        windowInsetsController.hide(WindowInsetsCompat.Type.systemBars());
        windowInsetsController.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);

        mWebView = new WebView(this);
        mWebView.setBackgroundColor(Color.parseColor("#04090e"));

        WebSettings settings = mWebView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setTextZoom(100);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        
        // Performance caching optimizations
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        
        // Native JavaScript Bridge (Allows the web app to trigger Android functions)
        mWebView.addJavascriptInterface(new ATubeNativeBridge(), "AndroidBridge");

        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                view.loadUrl(url);
                return true;
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                try {
                    view.loadUrl("file:///android_asset/index.html");
                } catch (Exception ignored) {}
            }
        });

        mWebView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onShowCustomView(View view, CustomViewCallback callback) {
                if (mCustomView != null) {
                    callback.onCustomViewHidden();
                    return;
                }
                
                mCustomView = view;
                mCustomView.setBackgroundColor(Color.BLACK);
                mCustomViewCallback = callback;
                
                if (mFullscreenContainer == null) {
                    mFullscreenContainer = new FrameLayout(MainActivity.this);
                    mFullscreenContainer.setBackgroundColor(Color.BLACK);
                    ViewGroup decor = (ViewGroup) getWindow().getDecorView();
                    decor.addView(mFullscreenContainer, new ViewGroup.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT));
                }
                
                mFullscreenContainer.addView(mCustomView, new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT));
                mFullscreenContainer.setVisibility(View.VISIBLE);
                mWebView.setVisibility(View.GONE);
            }

            @Override
            public void onHideCustomView() {
                if (mCustomView == null) {
                    return;
                }
                
                mCustomView.setVisibility(View.GONE);
                mFullscreenContainer.removeView(mCustomView);
                mCustomView = null;
                mFullscreenContainer.setVisibility(View.GONE);
                
                if (mCustomViewCallback != null) {
                    mCustomViewCallback.onCustomViewHidden();
                    mCustomViewCallback = null;
                }
                
                mWebView.setVisibility(View.VISIBLE);
            }
        });

        // Modern Back Button Handling (replaces deprecated onKeyDown)
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (mCustomView != null) {
                    // Exit fullscreen video first
                    mWebView.getWebChromeClient().onHideCustomView();
                } else if (mWebView != null && mWebView.canGoBack()) {
                    // Go back in webview history
                    mWebView.goBack();
                } else {
                    // Exit app
                    finish();
                }
            }
        });

        // Load assets natively using the new sourceSets
        mWebView.loadUrl("file:///android_asset/index.html");

        setContentView(mWebView);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (mWebView != null) mWebView.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (mWebView != null) mWebView.onPause();
    }
    
    /**
     * Native Bridge to allow Web JS to communicate with Android seamlessly.
     * Use in JS: AndroidBridge.showToast("Hello"); or AndroidBridge.closeApp();
     */
    public class ATubeNativeBridge {
        @JavascriptInterface
        public void showToast(String message) {
            Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show();
        }

        @JavascriptInterface
        public void closeApp() {
            finish();
        }
    }
}
