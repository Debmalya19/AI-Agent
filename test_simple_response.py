"""
Simple test script to verify chat endpoint returns clean responses
"""
import requests
import json

def test_chat_response():
    """Test the chat endpoint to ensure it returns clean responses"""
    
    # Test data
    test_query = "How can I contact customer support?"
    
    # Make request to chat endpoint
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"query": test_query},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Check if summary is clean and not structured
            summary = data.get('summary', '')
            if 'summary:' in summary.lower() or 'topic:' in summary.lower():
                print("❌ ERROR: Response still contains structured format")
                return False
            else:
                print("✅ SUCCESS: Response is clean and user-friendly")
                return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to server. Make sure the server is running on port 8000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Testing chat endpoint response format...")
    success = test_chat_response()
    
    if success:
        print("\n🎉 Test passed! The chat endpoint now returns clean, user-friendly responses.")
    else:
        print("\n💥 Test failed! The response still contains structured formatting.")
