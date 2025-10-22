# 🐛 Debug Web Không Hiển Thị Trên Android

## Vấn đề: App mở được, permission OK, nhưng màn hình trắng

---

## Bước 1: Xem Logcat trong Android Studio

1. **Mở Logcat:**
   - Android Studio → View → Tool Windows → Logcat
   - Hoặc click tab "Logcat" ở dưới màn hình

2. **Filter logs:**
   - Trong ô "Filter", gõ: `WebView`
   - Hoặc gõ: `agrichat`
   - Hoặc gõ: `Console`

3. **Tìm lỗi màu đỏ:**
   - Scroll xuống tìm dòng màu đỏ (ERROR)
   - Hoặc tìm "Uncaught" (JavaScript error)

4. **Copy lỗi và paste cho tôi:**
   - Copy toàn bộ error message
   - Bao gồm cả stack trace

---

## Bước 2: Kiểm tra các nguyên nhân phổ biến

### Nguyên nhân 1: URL sai hoặc không load được

**Kiểm tra trong MainActivity.kt:**
```kotlin
webView.loadUrl("https://agrichat.site/")  // ← URL đúng chưa?
```

**Thử thay bằng Google để test:**
```kotlin
webView.loadUrl("https://google.com")  // ← Thử xem Google load được không
```

Nếu Google load được → Vấn đề ở URL agrichat.site
Nếu Google cũng không load → Vấn đề ở WebView config

---

### Nguyên nhân 2: Server chưa deploy code mới

**Kiểm tra web trên browser điện thoại:**
1. Mở Chrome trên điện thoại
2. Vào: https://agrichat.site/
3. Xem có load được không?
4. Mở Console (Desktop mode + F12)
5. Có lỗi JavaScript không?

**Nếu web trên Chrome cũng lỗi → Chưa push code:**
```bash
# Trên máy tính
git status
git add .
git commit -m "Fix JavaScript for Android"
git push origin main

# Đợi 2-3 phút để server deploy
# Thử lại trên điện thoại
```

---

### Nguyên nhân 3: Network Security Config sai

**Kiểm tra file: `res/xml/network_security_config.xml`**

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
    </domain-config>
</network-security-config>
```

**Kiểm tra AndroidManifest.xml có dòng này:**
```xml
android:networkSecurityConfig="@xml/network_security_config"
```

---

### Nguyên nhân 4: JavaScript bị tắt

**Kiểm tra MainActivity.kt có dòng:**
```kotlin
webView.settings.javaScriptEnabled = true  // ← PHẢI có dòng này!
```

---

### Nguyên nhân 5: Internet permission thiếu

**Kiểm tra AndroidManifest.xml có:**
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

---

## Bước 3: Test từng bước

### Test 1: Load Google
```kotlin
// Trong MainActivity.kt
webView.loadUrl("https://google.com")
```
- Run lại app
- Google hiện ra → WebView config OK
- Vẫn trắng → WebView config sai

### Test 2: Load web khác
```kotlin
webView.loadUrl("https://example.com")
```
- Hiện ra → Internet OK
- Vẫn trắng → Permission hoặc config sai

### Test 3: Load agrichat.site
```kotlin
webView.loadUrl("https://agrichat.site/")
```
- Hiện ra → XONG!
- Vẫn trắng → Vấn đề ở server hoặc JavaScript

---

## Bước 4: Console log trong MainActivity

**Thêm log để debug:**

```kotlin
// Trong MainActivity.kt, thêm vào WebViewClient
webView.webViewClient = object : WebViewClient() {
    override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
        super.onPageStarted(view, url, favicon)
        Log.d("WEBVIEW", "Bắt đầu load: $url")
    }
    
    override fun onPageFinished(view: WebView?, url: String?) {
        super.onPageFinished(view, url)
        Log.d("WEBVIEW", "Đã load xong: $url")
    }
    
    override fun onReceivedError(
        view: WebView?,
        request: WebResourceRequest?,
        error: WebResourceError?
    ) {
        super.onReceivedError(view, request, error)
        Log.e("WEBVIEW", "LỖI: ${error?.description}")
        Toast.makeText(
            this@MainActivity,
            "Lỗi: ${error?.description}",
            Toast.LENGTH_LONG
        ).show()
    }
}

// Thêm vào WebChromeClient
webView.webChromeClient = object : WebChromeClient() {
    override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
        consoleMessage?.let {
            Log.d("WebView Console", "${it.message()} -- From line ${it.lineNumber()}")
        }
        return true
    }
}
```

Run lại và xem Logcat!

---

## Bước 5: Checklist nhanh

- [ ] Internet permission có trong AndroidManifest
- [ ] JavaScript enabled: `javaScriptEnabled = true`
- [ ] Network security config đã tạo và link vào manifest
- [ ] URL đúng: `https://agrichat.site/`
- [ ] Web chạy OK trên browser điện thoại
- [ ] Code đã push lên server và deploy xong
- [ ] Đã Sync Gradle sau khi sửa code
- [ ] Đã Clean + Rebuild project

**Clean + Rebuild:**
```
Build → Clean Project
Build → Rebuild Project
Run lại app
```

---

## Bước 6: Nếu vẫn không được

**Copy và gửi cho tôi:**

1. **Logcat output** (từ Android Studio)
   - Filter "WebView" hoặc "ERROR"
   - Copy toàn bộ từ lúc app mở đến khi thấy lỗi

2. **URL bạn đang load:**
   ```kotlin
   webView.loadUrl("???")  // ← URL là gì?
   ```

3. **Web chạy OK trên browser không?**
   - Chrome trên điện thoại có mở được https://agrichat.site/ không?
   - Có lỗi JavaScript trong Console không?

4. **Screenshot màn hình:**
   - Chụp màn hình app (màn hình trắng)
   - Chụp Logcat có lỗi

---

## Quick Fix thử ngay:

### Fix 1: Thêm log chi tiết
Copy đoạn code ở **Bước 4** vào MainActivity → Run lại → Xem Logcat

### Fix 2: Test với Google
```kotlin
webView.loadUrl("https://google.com")
```
Run → Nếu Google hiện → URL agrichat.site có vấn đề

### Fix 3: Rebuild
```
Build → Clean Project
Build → Rebuild Project
Run
```

### Fix 4: Verify web trên Chrome điện thoại
Mở Chrome → https://agrichat.site/ → Có lỗi không?

---

**Gửi cho tôi Logcat output hoặc error message để debug tiếp! 🔍**
