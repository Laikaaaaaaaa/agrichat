#!/usr/bin/env python3
"""
Test script for Ratings API
This script tests the new ratings API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_ratings_api():
    """Test the ratings API endpoints"""
    
    print("=" * 50)
    print("RATINGS API TEST")
    print("=" * 50)
    
    # Test 1: Try to create a rating without authentication
    print("\n[Test 1] Creating rating without authentication...")
    response = requests.post(f"{BASE_URL}/api/ratings/create", 
        json={
            "rating": 5,
            "name": "Test User",
            "title": "Test Rating",
            "content": "This is a test rating"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test 2: Try to get ratings without authentication
    print("\n[Test 2] Getting ratings without authentication...")
    response = requests.get(f"{BASE_URL}/api/ratings/list")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test 3: Check if /rate route exists
    print("\n[Test 3] Checking /rate route...")
    response = requests.get(f"{BASE_URL}/rate")
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)} bytes")
    
    print("\n" + "=" * 50)
    print("Note: Authentication tests would require login first")
    print("=" * 50)

if __name__ == "__main__":
    print("Make sure the Flask app is running on localhost:5000")
    print("Press Enter to start tests...")
    input()
    
    try:
        test_ratings_api()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to localhost:5000")
        print("Make sure the Flask app is running!")
    except Exception as e:
        print(f"❌ Error: {e}")
