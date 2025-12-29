package com.agrisense.app

import android.content.Context
import android.os.Build
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.MixedContentHandlingStrategy
import android.webkit.URLUtil
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import android.util.Log

/**
 * MainActivity (Kotlin version) - Hiển thị Flask Web App trong WebView
 * 
 * Vấn đề trang index bị trắng:
 * - Trang /login, /profile, /news hoạt động nhưng trang index (trang chủ) không hiển thị
 * - Nguyên nhân: WebView không bật JavaScript, DOM Storage, hoặc mixed content
 * 
 * Giải pháp:
 * - webSettings.javaScriptEnabled = true - bật JavaScript
 * - webSettings.domStorageEnabled = true - bật DOM Storage
 * - webSettings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW - cho phép mixed content
 * - WebView.setWebContentsDebuggingEnabled(true) - bật debug mode
 * - webView.clearCache(true) - xóa cache cũ
 * - onReceivedError handler - show thông báo lỗi
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    companion object {
        private const val WEB_URL = "https://agrichat.site"
        // Hoặc: "http://192.168.1.100:5000"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Khởi tạo WebView
        webView = findViewById(R.id.webView)

        // Cấu hình WebSettings để khắc phục trang index trắng
        webView.settings.apply {
            // === KHẮC PHỤC LỖI 1: Bật JavaScript ===
            javaScriptEnabled = true

            // === KHẮC PHỤC LỖI 2: Bật DOM Storage ===
            domStorageEnabled = true

            // === KHẮC PHỤC LỖI 3: Bật Mixed Content ===
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }

            // === Cấu hình khác ===
            useWideViewPort = true
            loadWithOverviewMode = true
            defaultTextEncodingName = "utf-8"
            geolocationEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
        }

        // === KHẮC PHỤC LỖI 4: Bật WebView Debugging ===
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(true)
        }

        // === KHẮC PHỤC LỖI 5: Xóa cache cũ ===
        webView.clearCache(true)
        webView.clearHistory()

        // Cấu hình cookies
        val cookieManager = CookieManager.getInstance()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            cookieManager.setAcceptThirdPartyCookies(webView, true)
        }

        // === Gán WebViewClient để xử lý lỗi ===
        webView.webViewClient = object : WebViewClient() {
            /**
             * Phương thức này được gọi khi có lỗi load trang
             */
            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: WebResourceError
            ) {
                super.onReceivedError(view, request, error)

                val errorMessage = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    "Lỗi tải trang: ${error.description}"
                } else {
                    "Lỗi tải trang"
                }

                // Log lỗi
                Log.e("WebView", errorMessage)

                // Show Toast
                Toast.makeText(
                    this@MainActivity,
                    errorMessage,
                    Toast.LENGTH_LONG
                ).show()

                // Load trang lỗi custom
                val htmlError = """
                    <html>
                        <head>
                            <meta charset='utf-8'>
                            <style>
                                body {
                                    font-family: Arial, sans-serif;
                                    text-align: center;
                                    padding: 20px;
                                    background-color: #f5f5f5;
                                }
                                h2 { color: #d32f2f; }
                                p { color: #555; }
                                button {
                                    background-color: #4CAF50;
                                    color: white;
                                    padding: 10px 20px;
                                    border: none;
                                    border-radius: 4px;
                                    cursor: pointer;
                                }
                                button:hover { background-color: #45a049; }
                            </style>
                        </head>
                        <body>
                            <h2>⚠️ Không thể tải trang</h2>
                            <p>$errorMessage</p>
                            <p>URL yêu cầu: ${request.url}</p>
                            <button onclick='location.reload()'>Tải lại</button>
                        </body>
                    </html>
                """.trimIndent()

                view.loadData(htmlError, "text/html; charset=utf-8", "utf-8")
            }

            /**
             * Phương thức này được gọi khi page finished loading
             */
            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                Log.d("WebView", "Page loaded: $url")
                Toast.makeText(
                    this@MainActivity,
                    "Trang đã tải: $url",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

        // === Gán WebChromeClient để xử lý console, dialogs ===
        webView.webChromeClient = object : WebChromeClient() {
            /**
             * Log JavaScript console messages để debug
             */
            override fun onConsoleMessage(consoleMessage: android.webkit.ConsoleMessage?): Boolean {
                consoleMessage?.let {
                    Log.d(
                        "WebView.Console",
                        "${it.message()} (line ${it.lineNumber()})"
                    )
                }
                return true
            }
        }

        // === Load trang chủ ===
        webView.loadUrl(WEB_URL)
    }

    /**
     * Xử lý nút back trong app
     */
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
