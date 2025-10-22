# ✅ Android Deployment Checklist

## 📋 Trước khi build app

### 1. ✅ Code đã sửa xong tất cả lỗi JavaScript
- [x] Xóa `date-fns` library (gây lỗi require is not defined)
- [x] Di chuyển `chatBox.addEventListener` vào DOMContentLoaded
- [x] Di chuyển keydown listener vào DOMContentLoaded (map_vietnam.html)
- [x] Xóa `showSidebar()` call không tồn tại
- [x] Di chuyển HTML files vào folder `templates/`
- [x] Sửa `app.py` để đọc templates từ đúng folder

### 2. ✅ Test local trước
```bash
# Chạy Flask server
python app.py

# Mở http://127.0.0.1:5000 trên browser
# Kiểm tra Console (F12) xem còn lỗi không
```

### 3. ✅ Push code lên server
```bash
git add .
git commit -m "Fix all JavaScript errors for Android WebView"
git push origin main
```

### 4. ✅ Verify web hoạt động trên server
- Truy cập: https://agrichat.site/
- Mở Developer Tools (F12) → Console tab
- Kiểm tra KHÔNG còn lỗi JavaScript màu đỏ
- Test các tính năng:
  - [ ] Chat hoạt động
  - [ ] Upload ảnh hoạt động
  - [ ] Lịch sử lưu được
  - [ ] Thời tiết hiển thị

---

## 🛠️ Tạo Android App trong Android Studio

### Bước 1: Tạo Project
1. [ ] Mở Android Studio
2. [ ] File → New → New Project
3. [ ] Chọn "Empty Activity"
4. [ ] Đặt tên: `AgriSenseAI`
5. [ ] Package: `com.agrisense.ai`
6. [ ] Language: Kotlin
7. [ ] Minimum SDK: API 24 (Android 7.0)
8. [ ] Click Finish

### Bước 2: Copy code từ ANDROID_WEBVIEW_SETUP.md
9. [ ] Copy `AndroidManifest.xml` (full permissions)
10. [ ] Tạo `res/xml/network_security_config.xml`
11. [ ] Copy `MainActivity.kt` code
12. [ ] Copy `activity_main.xml` layout
13. [ ] Update `build.gradle (Module: app)` dependencies

### Bước 3: Thay đổi URL trong MainActivity
```kotlin
// Dòng cuối onCreate()
webView.loadUrl("https://agrichat.site/")  // ✅ Đổi thành domain của bạn
```

### Bước 4: Sync Gradle
14. [ ] Click "Sync Now" khi Android Studio hỏi
15. [ ] Đợi Gradle build xong (có thể mất vài phút)

---

## 📱 Test trên thiết bị thật

### Chuẩn bị điện thoại
16. [ ] Bật Developer Options:
   - Vào Settings → About Phone
   - Tap "Build Number" 7 lần
17. [ ] Bật USB Debugging:
   - Settings → Developer Options → USB Debugging
18. [ ] Kết nối USB với máy tính
19. [ ] Accept "Allow USB Debugging" trên điện thoại

### Chạy app từ Android Studio
20. [ ] Click Run (Shift+F10) hoặc icon ▶️
21. [ ] Chọn thiết bị của bạn trong danh sách
22. [ ] Đợi app cài đặt và mở

---

## 🧪 Test các tính năng trên app

### Test cơ bản
- [ ] App mở được (không crash)
- [ ] Trang web load đầy đủ (không màn hình trắng)
- [ ] Scroll mượt mà
- [ ] Tap/touch hoạt động chính xác

### Test chức năng
- [ ] **Chat**: Gửi tin nhắn được
- [ ] **Upload ảnh**: 
  - [ ] Chọn từ Gallery
  - [ ] Chụp ảnh mới (nếu là mobile)
- [ ] **Lịch sử**: Lưu và load lại conversation
- [ ] **Tin tức**: Hiển thị và search được
- [ ] **Bản đồ**: Load bản đồ Việt Nam

### Test permissions
- [ ] Camera permission hoạt động
- [ ] Storage/Gallery permission hoạt động
- [ ] Location permission hoạt động (cho thời tiết)

### Test navigation
- [ ] Back button quay lại trang trước
- [ ] Menu navigation hoạt động
- [ ] Link trong app không mở browser ngoài

---

## 🔍 Debug nếu có lỗi

### Xem logs trên Android Studio
```
View → Tool Windows → Logcat
Filter: "WebView" or "agrichat"
```

### Lệnh ADB để xem log chi tiết
```bash
adb logcat | findstr "WebView"
adb logcat | findstr "agrichat"
adb logcat | findstr "Console"
```

### Các lỗi thường gặp

#### Lỗi 1: Màn hình trắng
**Nguyên nhân**: JavaScript error hoặc server không trả về HTML
**Fix**: 
- Check Logcat tìm JavaScript errors
- Verify https://agrichat.site/ hoạt động trên browser
- Check network_security_config.xml đã add domain chưa

#### Lỗi 2: Camera không hoạt động
**Nguyên nhân**: Thiếu permission
**Fix**:
- Check AndroidManifest có `<uses-permission android:name="android.permission.CAMERA" />`
- Check runtime permission request trong MainActivity
- Accept permission khi app hỏi

#### Lỗi 3: Upload ảnh không được
**Nguyên nhân**: FileChooser chưa implement hoặc permission thiếu
**Fix**:
- Check WebChromeClient có implement onShowFileChooser
- Check READ_EXTERNAL_STORAGE permission

#### Lỗi 4: Back button không hoạt động
**Nguyên nhân**: Chưa override onBackPressed
**Fix**:
```kotlin
override fun onBackPressed() {
    if (webView.canGoBack()) {
        webView.goBack()
    } else {
        super.onBackPressed()
    }
}
```

---

## 📦 Build APK để cài trên điện thoại khác

### Debug APK (test nhanh)
1. [ ] Build → Build Bundle(s) / APK(s) → Build APK(s)
2. [ ] Đợi build xong
3. [ ] Click "locate" để mở folder chứa APK
4. [ ] File APK ở: `app/build/outputs/apk/debug/app-debug.apk`
5. [ ] Copy file này sang điện thoại khác và cài

### Release APK (chính thức)
1. [ ] Build → Generate Signed Bundle / APK
2. [ ] Chọn APK
3. [ ] Create new keystore (LƯU MẬT KHẨU CẨN THẬN!)
4. [ ] Điền thông tin: Key alias, Password
5. [ ] Chọn "release" build variant
6. [ ] Click Finish
7. [ ] APK ở: `app/build/outputs/apk/release/app-release.apk`

**⚠️ QUAN TRỌNG**: Lưu keystore file và mật khẩu an toàn! Không có keystore = không update app được!

---

## 🎉 Hoàn tất!

Nếu tất cả checklist đã ✅:
- App đã chạy trên điện thoại
- Tất cả tính năng hoạt động
- Không có lỗi JavaScript trong Logcat

→ **Xong! App sẵn sàng để phân phối! 🚀**

---

## 📞 Support

Nếu gặp vấn đề:
1. Check Logcat để xem lỗi cụ thể
2. Google error message
3. Check ANDROID_WEBVIEW_SETUP.md để xem có miss step nào không
4. Verify web hoạt động bình thường trên browser trước

**Công cụ debug:**
- Android Studio Logcat
- Chrome DevTools (kết nối qua chrome://inspect)
- ADB commands

---

**Created**: 22/10/2025
**Last Updated**: 22/10/2025
**Version**: 1.0
