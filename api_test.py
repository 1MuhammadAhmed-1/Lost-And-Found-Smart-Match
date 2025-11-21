import requests
import json

# Base URL for the running Django server
BASE_URL = "http://127.0.0.1:8000/api/ninja/core"
AUTH_URL = "http://127.0.0.1:8000/api/token-auth/"

# Test User Data
TEST_USERNAME = "testuser_smartmatch"
TEST_PASSWORD = "Password123"
TEST_EMAIL = "test_smartmatch@example.com"

def print_result(title, response):
    """Prints request result details clearly."""
    try:
        data = response.json()
    except:
        data = response.text
        
    print(f"\n--- {title} ---")
    print(f"Status Code: {response.status_code}")
    print("Response Data:")
    print(json.dumps(data, indent=4))
    print("-" * 30)

def main():
    token = None
    
    # --- 1. Register a new user ---
    print("STEP 1: Attempting to register a new user...")
    register_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "email": TEST_EMAIL
    }
    
    # Note: /core/register is NOT protected by authentication
    try:
        register_response = requests.post(f"{BASE_URL}/register", json=register_data)
        print_result("Registration Result", register_response)

        if register_response.status_code != 201 and "already taken" not in register_response.text:
             print("Registration failed unexpectedly. Cannot proceed.")
             return
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Is Django running at http://127.0.0.1:8000/ ?")
        return
        
    # --- 2. Get an authentication token ---
    print("STEP 2: Attempting to obtain an authentication token...")
    login_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    # This endpoint is provided by rest_framework.authtoken.views.obtain_auth_token
    token_response = requests.post(AUTH_URL, json=login_data)
    print_result("Token Authentication Result", token_response)
    
    if token_response.status_code == 200:
        token = token_response.json().get('token')
        print(f"SUCCESS: Received Token: {token[:8]}...")
    else:
        print("ERROR: Failed to retrieve token. Check username/password.")
        return

    # --- 3. Call the protected chat endpoint ---
    if token:
        print("\nSTEP 3: Calling protected /core/chat endpoint with token...")
        
        headers = {
            # Format MUST be 'Token <space> <actual_token>'
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
        
        chat_data = {
            "message": "Hi, I just found a pair of reading glasses near the library. How do I report it?",
            "history": []
        }
        
        chat_response = requests.post(f"{BASE_URL}/chat", headers=headers, json=chat_data)
        print_result("Chat Endpoint Result (Protected)", chat_response)
        
        if chat_response.status_code == 200:
            print("SUCCESS: Chat endpoint accessed successfully!")
        else:
            print(f"FAILURE: Chat endpoint returned status code {chat_response.status_code}. Authentication failed.")

    # --- 4. Call the protected chat endpoint WITHOUT token (Expected 401) ---
    print("\nSTEP 4: Calling protected /core/chat endpoint WITHOUT token (Expecting 401)...")
    
    unauthorized_response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    print_result("Unauthorized Chat Result", unauthorized_response)
    
    if unauthorized_response.status_code == 401:
        print("SUCCESS: Unauthorized request was correctly rejected with 401.")
    else:
        print(f"FAILURE: Unauthorized request should have been 401, got {unauthorized_response.status_code}.")


if __name__ == "__main__":
    main()