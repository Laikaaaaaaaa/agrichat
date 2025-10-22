package com.example.agrichat

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.*
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import android.util.Log
import android.net.Uri
import android.content.Intent
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

class MainActivity : ComponentActivity() {
    
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null
    
    // Permission launcher
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        permissions.entries.forEach {
            Log.d("PERMISSION", "Permission ${it.key} = ${it.value}")
        }
    }
    
    // File chooser launcher
    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val data = result.data
            val uris = if (data?.clipData != null) {
                // Multiple files
                val clipData = data.clipData!!
                Array(clipData.itemCount) { i -> clipData.getItemAt(i).uri }
            } else if (data?.data != null) {
                // Single file
                arrayOf(data.data!!)
            } else {
                null
            }
            fileUploadCallback?.onReceiveValue(uris)
        } else {
            fileUploadCallback?.onReceiveValue(null)
        }
        fileUploadCallback = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Request permissions
        requestPermissions()
        
        setContent {
            AndroidView(
                factory = { context ->
                    WebView(context).apply {
                        // ============ CRITICAL: WebView Settings ============
                        settings.apply {
                            javaScriptEnabled = true
                            domStorageEnabled = true
                            databaseEnabled = true
                            
                            // Allow mixed content (HTTP + HTTPS)
                            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                            
                            // Enable broader compatibility
                            allowFileAccess = true
                            allowContentAccess = true
                            
                            // Enable geolocation
                            setGeolocationEnabled(true)
                            
                            // Better rendering
                            useWideViewPort = true
                            loadWithOverviewMode = true
                            
                            // Enable zooming (but we disable via meta tag)
                            setSupportZoom(true)
                            builtInZoomControls = true
                            displayZoomControls = false
                            
                            // Cache settings
                            cacheMode = WebSettings.LOAD_DEFAULT
                        }
                        
                        // ============ CRITICAL: WebViewClient ============
                        webViewClient = object : WebViewClient() {
                            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                                super.onPageStarted(view, url, favicon)
                                Log.d("WEBVIEW", "⏳ Bắt đầu load: $url")
                            }
                            
                            override fun onPageFinished(view: WebView?, url: String?) {
                                super.onPageFinished(view, url)
                                Log.d("WEBVIEW", "✅ Đã load xong: $url")
                                
                                // Force visibility
                                view?.visibility = android.view.View.VISIBLE
                            }
                            
                            override fun onReceivedError(
                                view: WebView?,
                                request: WebResourceRequest?,
                                error: WebResourceError?
                            ) {
                                super.onReceivedError(view, request, error)
                                Log.e("WEBVIEW", "❌ LỖI: ${error?.description} - URL: ${request?.url}")
                                
                                // Only show toast for main frame errors
                                if (request?.isForMainFrame == true) {
                                    Toast.makeText(
                                        this@MainActivity,
                                        "Lỗi tải trang: ${error?.description}",
                                        Toast.LENGTH_LONG
                                    ).show()
                                }
                            }
                            
                            override fun shouldOverrideUrlLoading(
                                view: WebView?,
                                request: WebResourceRequest?
                            ): Boolean {
                                val url = request?.url.toString()
                                Log.d("WEBVIEW", "🔗 Navigation to: $url")
                                
                                // Handle relative URLs (like /news, /history)
                                val finalUrl = when {
                                    url.startsWith("/") -> "https://agrichat.site$url"
                                    url.startsWith("http") -> url
                                    else -> "https://agrichat.site/$url"
                                }
                                
                                Log.d("WEBVIEW", "📍 Final URL: $finalUrl")
                                
                                // Keep agrichat.site URLs inside WebView
                                return if (finalUrl.contains("agrichat.site")) {
                                    view?.loadUrl(finalUrl)
                                    true
                                } else {
                                    // External links - keep default behavior
                                    false
                                }
                            }
                        }
                        
                        // ============ CRITICAL: WebChromeClient (FOR RENDERING!) ============
                        webChromeClient = object : WebChromeClient() {
                            // Required for console.log visibility
                            override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
                                consoleMessage?.let {
                                    Log.d(
                                        "WebViewConsole",
                                        "${it.message()} -- From line ${it.lineNumber()} of ${it.sourceId()}"
                                    )
                                }
                                return true
                            }
                            
                            // Required for file uploads
                            override fun onShowFileChooser(
                                webView: WebView?,
                                filePathCallback: ValueCallback<Array<Uri>>?,
                                fileChooserParams: FileChooserParams?
                            ): Boolean {
                                fileUploadCallback?.onReceiveValue(null)
                                fileUploadCallback = filePathCallback
                                
                                val intent = fileChooserParams?.createIntent()
                                try {
                                    fileChooserLauncher.launch(intent)
                                } catch (e: Exception) {
                                    Log.e("WEBVIEW", "❌ File chooser error: ${e.message}")
                                    fileUploadCallback = null
                                    return false
                                }
                                return true
                            }
                            
                            // Required for geolocation
                            override fun onGeolocationPermissionsShowPrompt(
                                origin: String?,
                                callback: GeolocationPermissions.Callback?
                            ) {
                                callback?.invoke(origin, true, false)
                            }
                            
                            // Progress tracking
                            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                                super.onProgressChanged(view, newProgress)
                                Log.d("WEBVIEW", "📊 Loading progress: $newProgress%")
                            }
                        }
                        
                        // ============ LOAD URL ============
                        Log.d("WEBVIEW", "🚀 Loading URL: https://agrichat.site/")
                        loadUrl("https://agrichat.site/")
                    }
                },
                modifier = Modifier.fillMaxSize()
            )
        }
    }
    
    private fun requestPermissions() {
        val permissions = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.READ_EXTERNAL_STORAGE
        )
        
        val permissionsToRequest = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (permissionsToRequest.isNotEmpty()) {
            requestPermissionLauncher.launch(permissionsToRequest.toTypedArray())
        }
    }
    
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        // Handle back button in WebView
        val webView = window.decorView.findViewById<WebView>(android.R.id.content)
        if (webView?.canGoBack() == true) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
