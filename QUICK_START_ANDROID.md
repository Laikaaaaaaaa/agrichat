# 🚀 Quick Start Guide - Android App

## Bước 1: Đảm bảo web không lỗi (5 phút)

```bash
# Test local
python app.py
# Mở http://127.0.0.1:5000 và check Console (F12)

# Push code
git add .
git commit -m "Ready for Android deployment"
git push origin main

# Test trên server
# Mở https://agrichat.site/ và check Console
```

**✅ Yêu cầu**: KHÔNG có lỗi JavaScript màu đỏ trong Console!

---

## Bước 2: Tạo app Android Studio (10 phút)

### 2.1 New Project
- Empty Activity
- Name: `AgriSenseAI`
- Package: `com.agrisense.ai`
- Language: Kotlin
- Min SDK: API 24

### 2.2 Copy 4 files từ ANDROID_WEBVIEW_SETUP.md:

**File 1:** `AndroidManifest.xml` (permissions)
**File 2:** `res/xml/network_security_config.xml` (cho phép HTTP)
**File 3:** `MainActivity.kt` (WebView code)
**File 4:** `activity_main.xml` (layout)

### 2.3 Sửa URL trong MainActivity.kt
```kotlin
webView.loadUrl("https://agrichat.site/")  // ← Thay domain của bạn
```

### 2.4 Sync Gradle
Click "Sync Now" và đợi

---

## Bước 3: Chạy trên điện thoại (2 phút)

### 3.1 Bật USB Debugging trên điện thoại:
1. Settings → About Phone → Tap "Build Number" 7 lần
2. Settings → Developer Options → USB Debugging ON
3. Kết nối USB với máy tính

### 3.2 Run app:
- Click ▶️ Run trong Android Studio
- Chọn thiết bị
- Accept permission khi app hỏi

---

## ✅ Kiểm tra nhanh

App phải:
- [ ] Mở được (không crash)
- [ ] Load trang web đầy đủ
- [ ] Chat được
- [ ] Upload ảnh được
- [ ] Back button hoạt động

---

## 🐛 Lỗi thường gặp

### Màn hình trắng?
```bash
# Xem log
adb logcat | findstr "WebView Console"
# Nếu thấy JavaScript error → sửa trong code web, push lại
```

### Camera không hoạt động?
- Accept permission khi app hỏi
- Check AndroidManifest có CAMERA permission

### Upload ảnh không được?
- Check MainActivity có implement onShowFileChooser
- Accept STORAGE permission

---

## 📦 Build APK để share

### Debug APK (test):
```
Build → Build APK
File ở: app/build/outputs/apk/debug/app-debug.apk
```

### Release APK (chính thức):
```
Build → Generate Signed Bundle / APK
Tạo keystore mới (LƯU MẬT KHẨU!)
File ở: app/build/outputs/apk/release/app-release.apk
```

---

## 🎯 Tổng kết

**Thời gian tổng**: ~17 phút
1. Web không lỗi: 5 phút
2. Tạo app: 10 phút  
3. Test điện thoại: 2 phút

**Chi tiết đầy đủ**: Xem `ANDROID_WEBVIEW_SETUP.md` và `ANDROID_DEPLOYMENT_CHECKLIST.md`

---

**Last Updated**: 22/10/2025
