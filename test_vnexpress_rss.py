import requests

# Test more VNExpress URLs
test_urls = [
    'https://vnexpress.net/rss/tin-moi-nhat.rss',
    'https://vnexpress.net/rss/thoi-su.rss',
    'https://vnexpress.net/rss/kinh-doanh.rss',
    'https://vnexpress.net/rss/du-lich.rss',
    'https://vnexpress.net/rss/khoa-hoc.rss',
    'https://vnexpress.net/rss/the-gioi.rss',
    'https://vnexpress.net/rss/suc-khoe.rss',
    'https://vnexpress.net/rss/giao-duc.rss',
    'https://vnexpress.net/rss/phap-luat.rss',
]

print('VNExpress RSS URLs check:\n')
for url in test_urls:
    try:
        r = requests.get(url, timeout=5, allow_redirects=True)
        if '<rss' in r.text[:500] or '<feed' in r.text[:500]:
            items = r.text.count('<item>')
            print(f'OK | {url.split("/")[-1]:30} -> {items} items')
        else:
            print(f'NO | {url.split("/")[-1]:30} -> Wrong format')
    except Exception as e:
        print(f'ER | {url.split("/")[-1]:30} -> {str(e)[:20]}')
