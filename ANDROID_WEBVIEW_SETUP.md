# Hướng dẫn tạo Android App với WebView - AgriSense AI

## 📱 Đã tối ưu WebView cho tất cả file:
- ✅ index.html (Trang chủ chat)
- ✅ news.html (Tin tức nông nghiệp)
- ✅ history.html (Lịch sử hội thoại)
- ✅ map_vietnam.html (Bản đồ thời tiết)

## 🔧 Các tối ưu đã thêm:

### 1. Meta Tags (Tất cả file HTML)
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
<meta name="mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="format-detection" content="telephone=no" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
```

### 2. CSS Optimization
```css
* {
  -webkit-tap-highlight-color: rgba(0, 0, 0, 0);  /* Bỏ highlight khi tap */
  -webkit-touch-callout: none;                     /* Bỏ menu khi long press */
  -webkit-overflow-scrolling: touch;               /* Smooth scroll */
}

html, body {
  -webkit-text-size-adjust: 100%;                  /* Tự động adjust font */
  -webkit-font-smoothing: antialiased;             /* Font mịn hơn */
}

img {
  -webkit-user-select: none;                       /* Không select được ảnh */
  user-select: none;
  pointer-events: none;
}
```

## 📦 Tạo Android App với Android Studio

### Bước 1: Tạo Project mới
1. Mở Android Studio
2. **File → New → New Project**
3. Chọn **Empty Activity**
4. Đặt tên: `AgriSenseAI`
5. Package name: `com.agrisense.ai`
6. Language: **Kotlin** hoặc **Java**
7. Minimum SDK: **API 24 (Android 7.0)**

### Bước 2: Cấu hình AndroidManifest.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.agrisense.ai">

    <!-- Permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    
    <!-- Hardware features (optional) -->
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.location.gps" android:required="false" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="AgriSense AI"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.AgriSenseAI"
        android:usesCleartextTraffic="true"
        android:networkSecurityConfig="@xml/network_security_config">
        
        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:exported="true"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
```

### Bước 3: Tạo network_security_config.xml
**Đường dẫn:** `res/xml/network_security_config.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
    
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">agrichat.site</domain>
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">127.0.0.1</domain>
    </domain-config>
</network-security-config>
```

### Bước 4: MainActivity Code (Kotlin)

**File:** `app/src/main/java/com/agrisense/ai/MainActivity.kt`

```kotlin
package com.agrisense.ai

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.webkit.*
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
    
    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    
    // Permission launcher
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        permissions.entries.forEach {
            if (!it.value) {
                Toast.makeText(this, "Cần cấp quyền ${it.key}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    // File chooser launcher
    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        filePathCallback?.onReceiveValue(uri?.let { arrayOf(it) })
        filePathCallback = null
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Request permissions
        checkAndRequestPermissions()
        
        // Initialize WebView
        webView = findViewById(R.id.webview)
        
        // WebView Settings
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = false
            displayZoomControls = false
            setSupportZoom(false)
            
            // Enable caching
            cacheMode = WebSettings.LOAD_DEFAULT
            
            // Geolocation
            setGeolocationEnabled(true)
            
            // Mixed content (HTTP + HTTPS)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }
            
            // Media playback
            mediaPlaybackRequiresUserGesture = false
        }
        
        // WebViewClient
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                return false
            }
            
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
                // Show loading indicator if needed
            }
            
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                // Hide loading indicator
            }
            
            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                Toast.makeText(
                    this@MainActivity,
                    "Lỗi tải trang: ${error?.description}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
        
        // WebChromeClient (for file upload, geolocation, etc.)
        webView.webChromeClient = object : WebChromeClient() {
            // File upload
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                this@MainActivity.filePathCallback?.onReceiveValue(null)
                this@MainActivity.filePathCallback = filePathCallback
                fileChooserLauncher.launch("image/*")
                return true
            }
            
            // Geolocation permission
            override fun onGeolocationPermissionsShowPrompt(
                origin: String?,
                callback: GeolocationPermissions.Callback?
            ) {
                callback?.invoke(origin, true, false)
            }
            
            // Console messages (for debugging)
            override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
                consoleMessage?.let {
                    android.util.Log.d(
                        "WebView Console",
                        "${it.message()} -- From line ${it.lineNumber()} of ${it.sourceId()}"
                    )
                }
                return true
            }
        }
        
        // Load URL
        webView.loadUrl("https://agrichat.site/")
        // For local testing: webView.loadUrl("file:///android_asset/index.html")
    }
    
    private fun checkAndRequestPermissions() {
        val permissions = mutableListOf<String>()
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.CAMERA)
        }
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
        }
        
        if (permissions.isNotEmpty()) {
            requestPermissionLauncher.launch(permissions.toTypedArray())
        }
    }
    
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
    
    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
```

### Bước 5: Layout XML

**File:** `app/src/main/res/layout/activity_main.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <WebView
        android:id="@+id/webview"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

### Bước 6: build.gradle (Module: app)

```gradle
plugins {
    id 'com.android.application'
    id 'org.jetbrains.kotlin.android'
}

android {
    namespace 'com.agrisense.ai'
    compileSdk 34

    defaultConfig {
        applicationId "com.agrisense.ai"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
    
    kotlinOptions {
        jvmTarget = '1.8'
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.11.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    implementation 'androidx.activity:activity-ktx:1.8.2'
}
```

## 🎨 Tùy chỉnh App Icon

1. **Chuẩn bị icon:** Logo AgriSense AI ở nhiều kích thước
2. **Thêm vào:** `res/mipmap-*dpi/` folders
   - mipmap-mdpi: 48x48
   - mipmap-hdpi: 72x72
   - mipmap-xhdpi: 96x96
   - mipmap-xxhdpi: 144x144
   - mipmap-xxxhdpi: 192x192

3. **Tool tự động:** Dùng Android Studio → Right click `res` → **New → Image Asset**

## 🚀 Build & Test

### Debug Build
```bash
./gradlew assembleDebug
```

### Release Build (Signed APK)
1. **Build → Generate Signed Bundle / APK**
2. Chọn **APK**
3. Create keystore mới hoặc dùng có sẵn
4. Build Release APK

### Test trên thiết bị
1. Enable **USB Debugging** trên Android device
2. Kết nối USB
3. Click **Run** (Shift+F10) trong Android Studio

## 📱 Tính năng đã tối ưu

### ✅ Hoạt động tốt trên WebView:
- Camera upload (chọn ảnh từ gallery/chụp mới)
- Geolocation (lấy vị trí thời tiết)
- Local Storage (lưu lịch sử chat)
- Touch gestures (vuốt, tap, scroll)
- Responsive design (tự động fit màn hình)
- Back button (quay lại trang trước)

### ✅ Performance:
- Hardware acceleration enabled
- Smooth scrolling với `-webkit-overflow-scrolling`
- No tap highlight delay
- Optimized font rendering

## 🐛 Troubleshooting

### Lỗi "net::ERR_CLEARTEXT_NOT_PERMITTED"
→ Đã fix bằng `network_security_config.xml`

### Camera không hoạt động
→ Kiểm tra permissions trong AndroidManifest và runtime permissions

### WebView trắng xóa
→ Check console logs: `adb logcat | grep WebView`

### Không load được HTTPS với cert tự ký
→ Thêm domain vào `network_security_config.xml`

## 📚 Tài liệu tham khảo

- [Android WebView Documentation](https://developer.android.com/develop/ui/views/layout/webapps/webview)
- [WebView Best Practices](https://developer.android.com/develop/ui/views/layout/webapps/best-practices)
- [WebSettings API](https://developer.android.com/reference/android/webkit/WebSettings)

---

**Tạo bởi:** AgriSense AI Team  
**Ngày cập nhật:** 22/10/2025  
**Version:** 1.0
