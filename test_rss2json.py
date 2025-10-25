#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test rss2json service - Kiểm tra xem có lấy được bài báo nông nghiệp không
"""
import requests
import json

# Test URLs
test_feeds = [
    {
        "name": "Nông nghiệp Môi trường - Chăn nuôi",
        "url": "https://nongnghiepmoitruong.vn/chan-nuoi.rss"
    },
    {
        "name": "Nông nghiệp Môi trường - Nông nghiệp",
        "url": "https://nongnghiepmoitruong.vn/tai-co-cau-nong-nghiep.rss"
    }
]

def test_rss2json(feed_url, feed_name):
    """Test rss2json service"""
    print(f"\n{'='*60}")
    print(f"Test: {feed_name}")
    print(f"URL: {feed_url}")
    print('='*60)
    
    # Service 1: api.rss2json.com
    print("\n[1] Thử api.rss2json.com...")
    url1 = f"https://api.rss2json.com/v1/api.json?rss_url={requests.utils.quote(feed_url)}&count=10"
    
    try:
        response = requests.get(url1, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            
            if data.get('status') == 'ok':
                items = data.get('items', [])
                print(f"  Items found: {len(items)}")
                
                if items:
                    print(f"\n  Sample articles:")
                    for i, item in enumerate(items[:3], 1):
                        print(f"\n    {i}. {item.get('title', 'N/A')[:60]}")
                        print(f"       Link: {item.get('link', 'N/A')}")
                        print(f"       Has image: {bool(item.get('thumbnail'))}")
                    return True
            else:
                print(f"  Error: {data.get('message')}")
        else:
            print(f"  HTTP {response.status_code}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    # Service 2: rss2json.com
    print("\n[2] Thử rss2json.com (backup)...")
    url2 = f"https://rss2json.com/api.json?rss_url={requests.utils.quote(feed_url)}&api_key=bhqojjrpwu79kwhljjcj20c2c3s7ycpwmq0ldyjb&count=10"
    
    try:
        response = requests.get(url2, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            
            if data.get('status') == 'ok':
                items = data.get('items', [])
                print(f"  Items found: {len(items)}")
                
                if items:
                    print(f"\n  Sample articles:")
                    for i, item in enumerate(items[:3], 1):
                        print(f"\n    {i}. {item.get('title', 'N/A')[:60]}")
                        print(f"       Link: {item.get('link', 'N/A')}")
                        print(f"       Has image: {bool(item.get('thumbnail'))}")
                    return True
            else:
                print(f"  Error: {data.get('message')}")
        else:
            print(f"  HTTP {response.status_code}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    return False

if __name__ == '__main__':
    print("\n" + "="*60)
    print("TEST RSS2JSON - Lấy Bài Báo Nông Nghiệp")
    print("="*60)
    
    success_count = 0
    for feed in test_feeds:
        if test_rss2json(feed['url'], feed['name']):
            success_count += 1
    
    print("\n" + "="*60)
    print(f"Kết quả: {success_count}/{len(test_feeds)} thành công")
    print("="*60)
    
    if success_count == len(test_feeds):
        print("\n✅ RSS2JSON hoạt động, bài báo nông nghiệp lấy được!")
    else:
        print("\n⚠️ Một số feed không lấy được, cần kiểm tra")
