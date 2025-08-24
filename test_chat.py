"""
Test script for chat functionality
"""
from fastapi.testclient import TestClient
from main import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chat():
    client = TestClient(app)

    # Test support ticket creation
    print("\n1. Testing support ticket creation...")
    support_response = client.post(
        "/chat",
        json={"query": "My broadband is not working properly"}
    )
    print(f"Status code: {support_response.status_code}")
    print("Response:", support_response.json())

    print("\n2. Testing general information query...")
    info_response = client.post(
        "/chat",
        json={"query": "How can I contact customer support?"}
    )
    print(f"Status code: {info_response.status_code}")
    print("Response:", info_response.json())

    print("\n3. Testing error handling...")
    error_response = client.post(
        "/chat",
        json={"invalid_field": "This should cause an error"}
    )
    print(f"Status code: {error_response.status_code}")
    try:
        print("Response:", error_response.json())
    except:
        print("Response: Could not parse JSON (expected for error)")

if __name__ == "__main__":
    test_chat()
