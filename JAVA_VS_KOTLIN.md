# Java vs Kotlin - WebView Implementation

## 🔴 Vấn Đề: Trang Index Trắng

| Trang | Status | Ghi Chú |
|------|--------|---------|
| /login | ✅ OK | WebView cấu hình cơ bản đủ |
| /profile | ✅ OK | Không cần JS phức tạp |
| /news | ✅ OK | Load được |
| / (index) | ❌ TRẮNG | Cần bật JavaScript, DOM Storage, Mixed Content |

## 🎯 5 Cấu Hình Quan Trọng

| Cấu Hình | Java | Kotlin | Mục Đích |
|---------|------|--------|----------|
| JavaScript | `setJavaScriptEnabled(true)` | `javaScriptEnabled = true` | Chạy code JS |
| DOM Storage | `setDomStorageEnabled(true)` | `domStorageEnabled = true` | localStorage, sessionStorage |
| Mixed Content | `setMixedContentMode(MIXED_CONTENT_ALWAYS_ALLOW)` | `mixedContentMode = MIXED_CONTENT_ALWAYS_ALLOW` | CDN HTTP/HTTPS |
| Debug | `WebView.setWebContentsDebuggingEnabled(true)` | `WebView.setWebContentsDebuggingEnabled(true)` | Chrome DevTools |
| Cache | `clearCache(true)` | `clearCache(true)` | Xóa cache cũ |

## 📝 Ví Dụ Code

### Java
```java
WebSettings webSettings = webView.getSettings();
webSettings.setJavaScriptEnabled(true);
webSettings.setDomStorageEnabled(true);
webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
WebView.setWebContentsDebuggingEnabled(true);
webView.clearCache(true);
```

### Kotlin
```kotlin
webView.settings.apply {
    javaScriptEnabled = true
    domStorageEnabled = true
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
        mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
    }
}
WebView.setWebContentsDebuggingEnabled(true)
webView.clearCache(true)
```

## ✅ Cách Chọn

### Dùng Java Nếu:
- Project cũ đã viết bằng Java
- Team quen với Java
- Cần compatibility cao

### Dùng Kotlin Nếu:
- Project mới
- Android Studio mới (recommend Kotlin)
- Muốn code ngắn hơn, an toàn hơn

## 📱 File Cần Copy

```
Nếu dùng Java:
  └─ MainActivity.java

Nếu dùng Kotlin:
  └─ MainActivity.kt

Cả hai đều cần:
  ├─ activity_main.xml
  ├─ AndroidManifest.xml
  ├─ build.gradle
  ├─ strings.xml
  └─ WEBVIEW_FIX_GUIDE.md
```

## 🔍 Xem Lỗi Chi Tiết

### Cách 1: Logcat (Android Studio)
```
Dưới cùng tab "Logcat"
Tìm: ERROR hoặc WARNING liên quan đến WebView
```

### Cách 2: Chrome DevTools
```
Chrome > chrome://inspect/#devices
Chọn device > Console, Network, Elements
Xem real-time log từ WebView
```

### Cách 3: Toast Message
```
Cả Java & Kotlin có Toast khi page load/error:
Toast.makeText(this, "...", Toast.LENGTH_SHORT).show()
```

## 🚀 Bước Chạy

### 1. Copy File
```
app/src/main/java/com/agrisense/app/MainActivity.java (hoặc .kt)
app/src/main/res/layout/activity_main.xml
app/src/main/AndroidManifest.xml
```

### 2. Sync Gradle
```
File > Sync Now (hoặc Ctrl+Alt+Y)
```

### 3. Build & Run
```
Shift+F10
hoặc Run > Run 'app'
```

### 4. Kiểm Tra
- Trang index sẽ hiển thị
- Không còn trắng
- Có thể scroll, click bình thường

## ⚡ Error Handling

Cả Java & Kotlin đều có:

```
onReceivedError()     → Gọi khi request fail
onPageFinished()      → Gọi khi page load xong
onConsoleMessage()    → Gọi khi JS console.log()
```

Giúp debug lỗi khi trang không hiển thị.

## 💡 Tips

1. **Luôn bật debug khi develop**
   ```
   WebView.setWebContentsDebuggingEnabled(true)
   ```

2. **Kiểm tra Chrome DevTools ngay**
   ```
   chrome://inspect/#devices
   ```

3. **Xóa cache thường xuyên**
   ```
   webView.clearCache(true)
   ```

4. **Test trên device thật**
   - Emulator có thể khác
   - Kết nối USB debug

5. **Kiểm tra server log**
   - Nếu request đến server, xem server có lỗi gì

---

**Kết luận**: Java & Kotlin giải quyết vấn đề giống nhau, chỉ khác cú pháp. Chọn cái quen nhất!
