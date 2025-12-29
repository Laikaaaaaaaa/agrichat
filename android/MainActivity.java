package com.agrisense.app;

import android.content.Context;
import android.os.Build;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.MixedContentHandlingStrategy;
import android.webkit.URLUtil;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

/**
 * MainActivity - Hiển thị Flask Web App trong WebView
 * 
 * Vấn đề trang index bị trắng:
 * - Trang /login, /profile, /news hoạt động nhưng trang index (trang chủ) không hiển thị
 * - Nguyên nhân: WebView không bật JavaScript, DOM Storage, hoặc mixed content
 * - Lỗi này xảy ra khi:
 *   1. JavaScript bị tắt → trang chủ (index.html) có thể dùng async/fetch
 *   2. DOM Storage bị tắt → IndexedDB hoặc localStorage không hoạt động
 *   3. Mixed content bị chặn → CDN (Tailwind, Google Fonts) được tải qua HTTP/HTTPS
 *   4. WebView cache không được xóa trước đó
 * 
 * Giải pháp trong code:
 * - Dòng 68-70: setJavaScriptEnabled(true) - bật JavaScript
 * - Dòng 72-73: setDomStorageEnabled(true) - bật DOM Storage
 * - Dòng 75-76: setMixedContentMode(MIXED_CONTENT_ALWAYS_ALLOW) - cho phép mixed content
 * - Dòng 79-80: setWebContentsDebuggingEnabled(true) - bật debug mode để xem console
 * - Dòng 83-84: clearCache(true) - xóa cache cũ
 * - onReceivedError handler (dòng 120+) - show thông báo lỗi
 */
public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private static final String WEB_URL = "https://agrichat.site";
    // Hoặc dùng localhost để test: "http://192.168.1.100:5000"

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Khởi tạo WebView
        webView = findViewById(R.id.webView);

        // Cấu hình WebSettings để khắc phục trang index trắng
        WebSettings webSettings = webView.getSettings();

        // === KHẮC PHỤC LỖI 1: Bật JavaScript ===
        // Trang index có thể dùng JavaScript cho async operations
        webSettings.setJavaScriptEnabled(true);

        // === KHẮC PHỤC LỖI 2: Bật DOM Storage ===
        // localStorage, sessionStorage, IndexedDB cần bật để trang hoạt động đầy đủ
        webSettings.setDomStorageEnabled(true);

        // === KHẮC PHỤC LỖI 3: Bật Mixed Content ===
        // Trang dùng CDN ngoài (Tailwind CSS, Google Fonts, Font Awesome)
        // Có thể được tải qua HTTP trong khi main page là HTTPS
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        // === KHẮC PHỤC LỖI 4: Bật WebView Debugging ===
        // Cho phép xem console log trong Chrome DevTools (chrome://inspect)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        // === Cấu hình khác ===
        webSettings.setUseWideViewPort(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setDefaultTextEncodingName("utf-8");
        webSettings.setGeolocationEnabled(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // === KHẮC PHỤC LỖI 5: Xóa cache cũ ===
        // Nếu lần trước trang index bị cache sai, xóa cache để load lại
        webView.clearCache(true);
        webView.clearHistory();

        // Cấu hình cookies
        CookieManager cookieManager = CookieManager.getInstance();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            cookieManager.setAcceptThirdPartyCookies(webView, true);
        }

        // === Gán WebViewClient để xử lý lỗi ===
        webView.setWebViewClient(new WebViewClient() {
            /**
             * Phương thức này được gọi khi có lỗi load trang
             * Giúp debug tại sao trang index trắng (thường là lỗi network hoặc mixed content)
             */
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                
                String errorMessage = "Lỗi tải trang";
                
                // Lấy chi tiết lỗi (API 23+)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    errorMessage = "Lỗi tải trang: " + error.getDescription();
                }
                
                // Log lỗi
                android.util.Log.e("WebView", errorMessage);
                
                // Show Toast để user biết lỗi gì
                Toast.makeText(MainActivity.this, errorMessage, Toast.LENGTH_LONG).show();
                
                // Load trang lỗi custom (tùy chọn)
                String htmlError = "<html><head><meta charset='utf-8'></head><body style='font-family: Arial; text-align: center; padding: 20px;'>"
                        + "<h2>⚠️ Không thể tải trang</h2>"
                        + "<p>" + errorMessage + "</p>"
                        + "<p>URL yêu cầu: " + request.getUrl() + "</p>"
                        + "<button onclick='location.reload()'>Tải lại</button>"
                        + "</body></html>";
                
                view.loadData(htmlError, "text/html; charset=utf-8", "utf-8");
            }

            /**
             * Phương thức này được gọi khi page finished loading
             * Dùng để kiểm tra xem trang đã load thành công không
             */
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                android.util.Log.d("WebView", "Page loaded: " + url);
                Toast.makeText(MainActivity.this, "Trang đã tải: " + url, Toast.LENGTH_SHORT).show();
            }
        });

        // === Gán WebChromeClient để xử lý console, dialogs ===
        webView.setWebChromeClient(new WebChromeClient() {
            /**
             * Log JavaScript console messages để debug
             * Nếu trang index còn trắng, xem console log sẽ giúp tìm lỗi JavaScript
             */
            @Override
            public boolean onConsoleMessage(android.webkit.ConsoleMessage consoleMessage) {
                android.util.Log.d("WebView.Console", 
                    consoleMessage.message() + " (line " + consoleMessage.lineNumber() + ")");
                return true;
            }
        });

        // === Load trang chủ ===
        webView.loadUrl(WEB_URL);
    }

    /**
     * Xử lý nút back trong app
     * Nếu WebView có history, quay lại trang trước
     * Nếu không, thoát app
     */
    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
