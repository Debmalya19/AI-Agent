import requests

try:
    response = requests.get('http://localhost:8000/logs.html', allow_redirects=False)
    print(f"Status: {response.status_code}")
    print(f"Location: {response.headers.get('location', 'None')}")
except Exception as e:
    print(f"Error: {e}")