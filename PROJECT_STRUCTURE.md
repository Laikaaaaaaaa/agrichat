# AgriSense AI - Cấu trúc dự án

## 📁 Cấu trúc thư mục

```
agrichat/
├── 📱 android/              # Files cho Android app
│   ├── MainActivity.java
│   ├── MainActivity.kt
│   ├── AndroidManifest.xml
│   ├── activity_main.xml
│   ├── network_security_config.xml
│   └── strings.xml
│
├── 🎨 templates/            # HTML templates
│   ├── index.html           # Trang chủ chatbot
│   ├── login.html           # Đăng nhập
│   ├── register.html        # Đăng ký
│   ├── profile.html         # Hồ sơ người dùng
│   ├── forum.html           # Diễn đàn
│   ├── news.html            # Tin tức
│   ├── history.html         # Lịch sử chat
│   ├── rate.html            # Đánh giá
│   ├── map_vietnam.html     # Bản đồ VN
│   ├── forgot_password.html # Quên mật khẩu
│   ├── otp.html             # Xác thực OTP
│   └── error.html           # Trang lỗi
│
├── 📜 js/                   # JavaScript modules
│   ├── cameraManager.js     # Quản lý camera
│   ├── cameraDevice.js      # Device camera
│   ├── cameraUtils.js       # Camera utilities
│   ├── chat.js              # Chat functionality
│   ├── flashController.js   # Flash control
│   ├── imageViewer.js       # Image viewer
│   ├── livestockStats.js    # Thống kê gia súc
│   ├── photoCapture.js      # Chụp ảnh
│   └── videoDisplay.js      # Video display
│
├── 📦 static/               # Static assets
│   ├── favicon logo/        # Favicons
│   ├── logo/                # Logo images
│   ├── history.js           # History JS
│   ├── history-dialog.html  # History dialog
│   └── profile-extended.js  # Profile extended JS
│
├── 🔧 services/             # Service modules package
│   └── __init__.py          # Service exports
│
├── 🧠 modes/                # AI response modes
│   ├── __init__.py
│   ├── mode_manager.py
│   ├── basic_mode.py
│   ├── normal_mode.py
│   └── expert_mode.py
│
├── 🤖 models/               # ML models
│   ├── image_intent_classifier.pkl
│   └── image_intent_classifier_v2.pkl
│
├── 🛠️ tools/                # Development tools
│   └── check_py311_compat.py
│
├── ⚙️ Backend Python Files (Root)
│   ├── app.py                    # 🚀 Main Flask application
│   ├── auth.py                   # 🔐 Authentication module
│   ├── error_handlers.py         # ❌ Error handling
│   ├── prompt_manager.py         # 💬 Prompt management
│   ├── model_config.py           # ⚙️ Model configuration
│   │
│   ├── 🖼️ Image Services:
│   │   ├── image_search.py       # Image search engine
│   │   ├── image_search_memory.py# Search memory
│   │   ├── image_request_handler.py # Request handler
│   │   ├── image_intent_classifier.py # ML classifier
│   │   ├── wikimedia_api.py      # Wikimedia API
│   │   └── google_images.py      # Google Images
│   │
│   ├── 📰 News Services:
│   │   ├── news_classifier.py    # News classification
│   │   └── rss_api.py            # RSS feed API
│   │
│   ├── 🎤 Speech Services:
│   │   └── speech_processor.py   # Speech-to-text
│   │
│   ├── 📊 Data Services:
│   │   └── data_analyzer.py      # Data analysis
│   │
│   └── 🔒 Security:
│       └── security.py           # Security utilities
│
├── 📋 Configuration Files
│   ├── requirements.txt          # Python dependencies
│   ├── Procfile                  # Heroku config
│   ├── runtime.txt               # Python version
│   ├── .env.example              # Environment template
│   └── .gitignore                # Git ignore
│
└── 💾 Database Files
    ├── database.db               # Main database
    ├── users.db                  # Users database
    └── news_classifier_model.pkl # News ML model
```

## 🔄 Import Structure

Các service có thể được import từ:
- Trực tiếp từ file: `from image_search import ImageSearchEngine`
- Từ package: `from services import ImageSearchEngine`

## 🚀 Chạy ứng dụng

```bash
# Development
python app.py

# Production (Heroku)
gunicorn app:app
```

## 📝 Notes

- Files HTML đã được chuyển vào `templates/`
- Files Android đã được chuyển vào `android/`
- Các Python service files giữ nguyên ở root để tránh breaking imports
- Package `services/` cung cấp interface thống nhất cho imports
