# 🚀 Hướng dẫn Deploy lên Heroku

## Bước 1: Tạo app trên Heroku

```bash
# Login vào Heroku
heroku login

# Tạo app mới (tên app phải unique)
heroku create agrisense-ai

# Hoặc nếu đã có app:
heroku git:remote -a agrisense-ai
```

## Bước 2: Thêm Environment Variables

**Vào Heroku Dashboard:** https://dashboard.heroku.com/apps/agrisense-ai/settings

Hoặc dùng CLI:

```bash
# PRIMARY API - OpenAI
heroku config:set OPENAI_API_KEY="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"
heroku config:set OPENAI_MODEL="gpt-4o-mini"
heroku config:set OPENAI_TEMPERATURE="0.7"

# FALLBACK API 1 - Gemini
heroku config:set GEMINI_API_KEYS="AIzaSyBCpGb-NRs71RawPqqZkxpO1HzNdhxzjcQ,AIzaSyD5xaUUqNFWvYgxuyx-mJsxuemPo3La6mU"

# FALLBACK API 2 - DeepSeek
heroku config:set DEEPSEEK_API_KEY="sk-c4a6f765412149bdaeb568d1e86bbf91"
heroku config:set DEEPSEEK_MODEL="deepseek-chat"
heroku config:set DEEPSEEK_TEMPERATURE="0.7"

# Weather API (Optional)
heroku config:set WEATHER_API_KEY="your_weather_api_key_here"

# Default Weather Location
heroku config:set DEFAULT_WEATHER_CITY="Hồ Chí Minh"
heroku config:set DEFAULT_WEATHER_REGION="Hồ Chí Minh"
heroku config:set DEFAULT_WEATHER_COUNTRY="Việt Nam"
heroku config:set DEFAULT_WEATHER_COUNTRY_CODE="VN"
heroku config:set DEFAULT_WEATHER_LAT="10.762622"
heroku config:set DEFAULT_WEATHER_LON="106.660172"
heroku config:set DEFAULT_WEATHER_TZ="Asia/Ho_Chi_Minh"

# Stock Photo APIs (Optional)
heroku config:set UNSPLASH_ACCESS_KEY="ZfwQ5Iudz6W37frBanPIzZOGHq5PkGz9TMe4cAHc1Ak"
heroku config:set PIXABAY_API_KEY="39087680-04da84c644093fba8655dea55"
heroku config:set PEXELS_API_KEY="xiv75UOnS8uuHb3vgU8cS5av5fDodAd0jsXBpGMXF2gBexowzSdZctDW"

# Cache settings
heroku config:set IP_LOOKUP_CACHE_TTL="900"
heroku config:set WEATHER_CACHE_TTL="300"
```

## Bước 3: Deploy

```bash
# Push code lên Heroku
git push heroku main

# Hoặc nếu đang ở branch khác:
git push heroku your-branch:main
```

## Bước 4: Kiểm tra logs

```bash
# Xem logs real-time
heroku logs --tail

# Kiểm tra app đã chạy chưa
heroku open
```

## Bước 5: Scale dyno (nếu cần)

```bash
# Bật web dyno
heroku ps:scale web=1

# Kiểm tra status
heroku ps
```

## Troubleshooting

### Lỗi: "Application error"
```bash
# Xem logs chi tiết
heroku logs --tail
```

### Lỗi: "No web processes running"
```bash
# Scale web dyno
heroku ps:scale web=1
```

### Lỗi: "Module not found"
```bash
# Kiểm tra requirements.txt có đầy đủ dependencies
# Restart app
heroku restart
```

### Kiểm tra config variables
```bash
# Xem tất cả config
heroku config

# Xem config cụ thể
heroku config:get OPENAI_API_KEY
```

## Files quan trọng đã có:

✅ `Procfile` - Định nghĩa web process
✅ `requirements.txt` - Python dependencies
✅ `runtime.txt` - Python version (3.11.9)
✅ `app.py` - Flask app với PORT từ env variable

## URL sau khi deploy:

https://agrisense-ai.herokuapp.com (hoặc tên app bạn chọn)

## Lưu ý:

- ⚠️ Heroku Free tier đã bị discontinued. Cần dùng paid plan.
- ✅ Eco Dyno ($5/month) hoặc Basic ($7/month) là lựa chọn rẻ nhất.
- 🔒 Environment variables an toàn, không lộ trên GitHub.
- 🚀 Auto-deploy từ GitHub: Settings → Deploy → Connect GitHub repo.
