# 📱 Cài Đặt WebView Cho AgriSense App - Quick Start

## 📋 Các File Cần Copy

```
MainActivity.java          → app/src/main/java/com/agrisense/app/
activity_main.xml          → app/src/main/res/layout/
strings.xml                → app/src/main/res/values/
AndroidManifest.xml        → app/src/main/
build.gradle               → app/ (merge với file hiện tại)
```

## ⚡ Bước Thực Hiện Nhanh

### 1. Mở Android Studio

```bash
File > New > New Project...
Select: Phone and Tablet > Empty Activity
Name: AgriSense
Package: com.agrisense.app
```

### 2. Copy File `MainActivity.java`

- Vào `app/src/main/java/com/agrisense/app/`
- Xóa `MainActivity.java` cũ (nếu có)
- Copy `MainActivity.java` đã tạo vào đó

### 3. Copy Layout File

- Vào `app/src/main/res/layout/`
- Xóa `activity_main.xml` cũ
- Copy `activity_main.xml` đã tạo vào đó

### 4. Copy AndroidManifest.xml

- Vào `app/src/main/`
- Replace hoàn toàn `AndroidManifest.xml` cũ bằng file mới

### 5. Update build.gradle

- Vào `app/build.gradle` (Module: app)
- Copy toàn bộ nội dung từ file `build.gradle` đã tạo
- Không merge, **replace toàn bộ**

### 6. Sync & Build

```
Android Studio > File > Sync Now
hoặc Ctrl+Alt+Y
```

Chờ Gradle build xong (không có lỗi)

### 7. Run App

```
Run > Run 'app'
hoặc Shift+F10
```

Chọn device hoặc emulator → chạy

## 🔍 Kiểm Tra Trang Hiển Thị

### ✅ Nếu trang hiển thị bình thường
- Trang index sẽ show ngay khi app khởi động
- Scroll được, click được
- Tất cả hành động bình thường

### ❌ Nếu trang vẫn trắng
1. **Xem Log Console** (Logcat - dưới cùng Android Studio)
2. **Mở Chrome DevTools** (chrome://inspect)
3. **Kiểm tra Network** xem resource load được không
4. **Thử URL khác** (localhost, test server)

## 📱 Debug Lỗi

### Xem Console Log

```bash
# Trong Chrome
chrome://inspect/#devices

# Chọn device
# Xem console log, network, elements
```

### Xem Logcat

```bash
# Android Studio - Tab "Logcat" dưới cùng
# Filter: "WebView"
# Tìm ERROR hoặc WARNING
```

### Kiểm Tra URL

```java
// Trong MainActivity.java, dòng 48
private static final String WEB_URL = "https://agrichat.site";

// Thay bằng:
// private static final String WEB_URL = "http://192.168.1.100:5000";
```

## 🎨 Tùy Chỉnh

### Thay Đổi Package Name

- Nếu package khác, sửa trong:
  - `MainActivity.java` - dòng 1: `package com.agrisense.app;`
  - `AndroidManifest.xml` - `package="com.agrisense.app"`
  - Directory `app/src/main/java/` - rename folder

### Thay Đổi URL Web

```java
// MainActivity.java - dòng 48
private static final String WEB_URL = "https://agrichat.site";
```

### Thêm App Icon

- Thay file trong `app/src/main/res/mipmap/ic_launcher.png`

## 🚀 Chạy Trên Device Thật

### Bước 1: Bật USB Debug

```
Device Settings > Developer Options > USB Debugging
```

### Bước 2: Kết Nối USB

```
Laptop > Device (đồng ý truy cập)
```

### Bước 3: Chạy

```
Android Studio > Run > Select device > OK
```

## 📊 Cấu Hình Min/Target SDK

Nếu lỗi SDK version, sửa trong `build.gradle`:

```gradle
minSdk 21              // Android 5.0+
targetSdk 33           // Android 13
```

## ✨ Kết Quả

- ✅ Trang index hiển thị (không trắng)
- ✅ JavaScript chạy
- ✅ CSS/Font load từ CDN
- ✅ Cookies & localStorage hoạt động
- ✅ Có thể debug trong Chrome DevTools

---

**Hỗ trợ**: Nếu còn lỗi, kiểm tra:
1. Internet connection
2. URL correct
3. Server đang chạy
4. Firebase/API keys đúng
5. CORS setting nếu API
