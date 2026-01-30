"""
Manual test script for authentication
手动测试认证功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_login():
    """Test login endpoint"""
    print("Testing login...")
    
    # Login with admin credentials
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"\n✅ Login successful!")
        print(f"Token: {token[:50]}...")
        return token
    else:
        print(f"\n❌ Login failed!")
        return None


def test_get_current_user(token):
    """Test get current user endpoint"""
    print("\n\nTesting get current user...")
    
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print(f"\n✅ Get current user successful!")
    else:
        print(f"\n❌ Get current user failed!")


def test_invalid_login():
    """Test login with invalid credentials"""
    print("\n\nTesting invalid login...")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={
            "username": "admin",
            "password": "wrongpassword"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print(f"\n✅ Invalid login correctly rejected!")
    else:
        print(f"\n❌ Invalid login should return 401!")


if __name__ == "__main__":
    print("=" * 60)
    print("Authentication Manual Test")
    print("=" * 60)
    print("\nMake sure the server is running:")
    print("  python3 -m uvicorn app.main:app --reload")
    print("\n" + "=" * 60 + "\n")
    
    try:
        # Test valid login
        token = test_login()
        
        if token:
            # Test get current user
            test_get_current_user(token)
        
        # Test invalid login
        test_invalid_login()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("Please start the server first:")
        print("  python3 -m uvicorn app.main:app --reload")
