import requests

test_urls = [
    ('VNExpress - Nông nghiệp', 'https://vnexpress.net/tag/nong-nghiep.rss'),
    ('VNExpress - Khoa học', 'https://vnexpress.net/rss/khoa-hoc.rss'),
    ('Tuổi Trẻ - Khoa học', 'https://tuoitre.vn/rss/khoa-hoc.rss'),
    ('Nông nghiệp Môi trường', 'https://nongnghiepmoitruong.vn/khuyen-nong.rss'),
    ('Dân Trí RSS', 'https://dantri.com.vn/rss/'),
    ('Thanh Niên RSS', 'https://thanhnien.vn/rss/'),
]

print("🔍 Testing RSS Feed URLs:\n")

for name, url in test_urls:
    try:
        r = requests.get(url, timeout=10)
        is_xml = 'xml' in r.headers.get('Content-Type', '').lower() or r.text.strip().startswith('<')
        is_rss = '<rss' in r.text[:500].lower() or '<feed' in r.text[:500].lower()
        
        status = "✅ OK" if is_xml and is_rss else "⚠️ Wrong format" if r.status_code == 200 else f"❌ {r.status_code}"
        print(f"{status} | {name:30} | Type: {r.headers.get('Content-Type', 'unknown')[:30]:30}")
        
        if is_rss:
            # Count items
            item_count = r.text.count('<item>') + r.text.count('<entry>')
            print(f"     └─ Items: {item_count}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️  TIMEOUT | {name:30}")
    except Exception as e:
        print(f"❌ ERROR  | {name:30} | {str(e)[:40]}")
    
    print()
