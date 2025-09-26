import requests

try:
    response = requests.get('http://localhost:8000/admin/logs.html')
    print(f"Admin logs page status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Admin logs page is accessible")
    else:
        print("❌ Admin logs page is not accessible")
except Exception as e:
    print(f"Error: {e}")