from database import SessionLocal
from models import SupportIntent, SupportResponse
from sqlalchemy.exc import SQLAlchemyError

def add_data_usage_info():
    db = SessionLocal()
    try:
        # Add data usage intent
        data_usage_intent = SupportIntent(
            intent_name="check data usage",
            description="Information about checking data usage",
            category="account"
        )
        db.add(data_usage_intent)
        db.flush()  # Flush to get the intent_id

        # Add comprehensive response for data usage
        data_usage_response = SupportResponse(
            intent_id=data_usage_intent.intent_id,
            response_text="""You can check your data usage in several ways:
1. Mobile App: Open our mobile app and go to 'Account' > 'Data Usage'
2. Web Portal: Log in to your account at portal.example.com and view 'Usage Statistics'
3. SMS Check: Send 'DATA' to 12345 for an instant usage update
4. Customer Dashboard: Visit dashboard.example.com/usage for detailed usage analytics
5. Monthly Statement: Review your monthly statement for complete usage details

Your data usage is updated in real-time for the mobile app and web portal. SMS updates may have a delay of up to 15 minutes.""",
            response_type="text"
        )
        db.add(data_usage_response)
        db.commit()
        print("Successfully added data usage information")
        
    except SQLAlchemyError as e:
        print(f"Error adding data usage information: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_data_usage_info()
