#!/usr/bin/env python
"""
Test script to verify the profile API returns correct is_own_profile flag
"""
import requests
import json

# Test URLs
BASE_URL = 'http://localhost:5000'

print("🔍 Testing Profile API is_own_profile flag\n")

# Test 1: Get current user profile (should be own profile)
print("Test 1: Getting current user profile...")
response = requests.get(f"{BASE_URL}/api/auth/profile")
if response.status_code == 200:
    data = response.json()
    if data.get('success') and data.get('user'):
        current_user_id = data['user']['id']
        print(f"✅ Current user: ID={current_user_id}, Name={data['user']['name']}")
    else:
        print("❌ Failed to get current user profile")
        print(f"Response: {json.dumps(data, indent=2)}")
        exit(1)
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)
    exit(1)

# Test 2: Get own profile by ID (should have is_own_profile=true)
print(f"\nTest 2: Fetching own profile by ID ({current_user_id})...")
response = requests.get(f"{BASE_URL}/api/profile/user/{current_user_id}")
if response.status_code == 200:
    data = response.json()
    is_own = data.get('is_own_profile', None)
    print(f"Response: is_own_profile={is_own}")
    if is_own is True:
        print("✅ Correctly returns is_own_profile=true for own profile")
    else:
        print(f"❌ Expected is_own_profile=true but got {is_own}")
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)

# Test 3: Logout and test anonymous access to own profile (should have is_own_profile=false)
print("\nTest 3: Testing profile access after logout...")
session = requests.Session()
response = session.get(f"{BASE_URL}/api/auth/profile")
if response.status_code == 200:
    data = response.json()
    if data.get('success') and data.get('user'):
        current_user_id = data['user']['id']
        
        # Logout
        logout_response = session.get(f"{BASE_URL}/logout")
        print(f"Logged out: {logout_response.status_code}")
        
        # Try to fetch own profile as anonymous
        profile_response = session.get(f"{BASE_URL}/api/profile/user/{current_user_id}")
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            is_own = profile_data.get('is_own_profile', None)
            print(f"Anonymous access to own profile: is_own_profile={is_own}")
            if is_own is False:
                print("✅ Correctly returns is_own_profile=false for anonymous access")
            else:
                print(f"❌ Expected is_own_profile=false but got {is_own}")

print("\n✅ Profile API tests complete!")
