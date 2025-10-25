# 🚀 WebView Configuration Guide - Khắc Phục Trang Index Trắng

## 🔴 Vấn Đề
- Trang `/login`, `/profile`, `/news` hoạt động bình thường
- Trang index (trang chủ `/`) bị **màn hình trắng**, không hiển thị gì

## 🎯 Nguyên Nhân

Trang index có thể bị trắng vì:

1. **JavaScript bị tắt** (❌ Lỗi chính)
   - Trang chủ index.html dùng async/await, fetch API, hoặc các thư viện JS
   - Nếu JavaScript disabled, mọi code JS không chạy → trang trắng

2. **DOM Storage bị tắt**
   - Trang dùng `localStorage`, `sessionStorage`, hoặc `IndexedDB`
   - Không bật → lỗi JavaScript → trang trắng

3. **Mixed Content bị chặn** (⚠️ Lỗi phổ biến)
   - Trang HTTPS (https://agrichat.site) nhưng CDN HTTP
   - Ví dụ: Tailwind CSS, Google Fonts, Font Awesome từ CDN có thể là HTTP
   - Android sẽ block → CSS/Font không load → trang trắng hoặc xấu

4. **Cache cũ**
   - Lần trước trang index cache sai → load lại vẫn sai

5. **Cookie/Auth issue**
   - Trang index yêu cầu session/cookie nhưng WebView không cho phép
   - Trang /login được duyệt nhưng index bị chặn

## ✅ Giải Pháp (Trong MainActivity.java)

### 1️⃣ Bật JavaScript (Dòng 68-70)
```java
webSettings.setJavaScriptEnabled(true);
```
**Lý do**: Cho phép tất cả JS code chạy, khắc phục trang index trắng

### 2️⃣ Bật DOM Storage (Dòng 72-73)
```java
webSettings.setDomStorageEnabled(true);
```
**Lý do**: localStorage, sessionStorage hoạt động → trang có thể lưu data

### 3️⃣ Cho Phép Mixed Content (Dòng 75-76)
```java
webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
```
**Lý do**: Cho phép CDN/resource HTTP khi page là HTTPS → CSS, font load được

### 4️⃣ Bật WebView Debugging (Dòng 79-80)
```java
WebView.setWebContentsDebuggingEnabled(true);
```
**Lý do**: Xem console, network log trong Chrome DevTools (chrome://inspect)

### 5️⃣ Xóa Cache Cũ (Dòng 83-84)
```java
webView.clearCache(true);
webView.clearHistory();
```
**Lý do**: Xóa dữ liệu cache sai từ lần trước

### 6️⃣ Xử Lý Lỗi (Dòng 103-140)
```java
@Override
public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
    // Show lỗi cho user
    // Log để debug
}
```
**Lý do**: Khi trang thất bại, show thông báo thay vì trắng toàn

## 📱 Cách Setup trong Android Studio

### Bước 1: Copy file vào project
```
app/src/main/java/com/agrisense/app/MainActivity.java
app/src/main/res/layout/activity_main.xml
app/src/main/AndroidManifest.xml
```

### Bước 2: Sửa package name
- Thay `com.agrisense.app` bằng package name của project bạn
- Ví dụ: `com.mycompany.myapp`

### Bước 3: Copy build.gradle
- Dán nội dung `build.gradle` vào `app/build.gradle` (module level)

### Bước 4: Sync & Run
```bash
# Trong Android Studio
Build > Rebuild Project
Run > Run 'app'
```

## 🔧 Debugging Trang Index Trắng

### Cách 1: Xem Log Console
```bash
# Mở Chrome
chrome://inspect/#devices

# Xem console log, network tab từ WebView
```

### Cách 2: Xem Toast Messages
- MainActivity sẽ show Toast khi:
  - Trang tải thành công (onPageFinished)
  - Có lỗi (onReceivedError)

### Cách 3: Kiểm Tra Network
- Xem request/response trong DevTools
- Nếu CSS/JS file 404 → vấn đề server
- Nếu Mixed Content warning → cần cấu hình HTTPS

### Cách 4: Test URL Khác
```java
// Nếu https://agrichat.site không được, test localhost
String WEB_URL = "http://192.168.1.100:5000";
```

## 🔐 Cấp Phép Cần Thiết (AndroidManifest.xml)

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" /> <!-- Tùy chọn -->
```

## 🎨 Tùy Chỉnh Thêm

### Thay đổi URL
```java
private static final String WEB_URL = "https://agrichat.site";
// Hoặc: "http://192.168.1.100:5000"
```

### Tắt Debug Mode (Production)
```java
// Xóa hoặc comment dòng này trước release:
WebView.setWebContentsDebuggingEnabled(false);
```

### Thêm Loading Screen
```java
// Thêm ProgressBar trong layout activity_main.xml
// Ẩn khi page finished loading
```

### Thêm Header Custom
```java
Map<String, String> headers = new HashMap<>();
headers.put("User-Agent", "AgriSense-Mobile/1.0");
webView.loadUrl(WEB_URL, headers);
```

## 📊 Checklist Kiểm Tra

- [ ] JavaScript enabled (`setJavaScriptEnabled(true)`)
- [ ] DOM Storage enabled (`setDomStorageEnabled(true)`)
- [ ] Mixed Content allowed (`setMixedContentMode(MIXED_CONTENT_ALWAYS_ALLOW)`)
- [ ] Debug enabled (`setWebContentsDebuggingEnabled(true)`)
- [ ] Cache cleared (`clearCache(true)`)
- [ ] INTERNET permission trong manifest
- [ ] MainActivity.java package name đúng
- [ ] activity_main.xml có WebView
- [ ] build.gradle có dependencies
- [ ] Sync & Build thành công

## 🐛 Lỗi Phổ Biến

| Lỗi | Nguyên Nhân | Cách Fix |
|-----|-----------|---------|
| Trang trắng | JS disabled | Bật `setJavaScriptEnabled(true)` |
| CSS không load | Mixed content | Bật `MIXED_CONTENT_ALWAYS_ALLOW` |
| No internet | Quên permission | Thêm `INTERNET` permission |
| Cookie mất | Third party disabled | Bật `setAcceptThirdPartyCookies` |
| Error 404 | URL sai hoặc server down | Test URL trước qua browser |

## 💡 Tips

1. **Luôn bật debug mode khi develop** → dễ debug lỗi
2. **Kiểm tra Chrome DevTools khi có lỗi** → xem exact error
3. **Clear cache thường xuyên** → tránh cache cũ
4. **Test trên real device** → emulator có thể khác
5. **Kiểm tra server log** → nếu request đến server có lỗi

---

**Tác giả**: GitHub Copilot
**Ngày**: October 25, 2025
**Version**: 1.0
