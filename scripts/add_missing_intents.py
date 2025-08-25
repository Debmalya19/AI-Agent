#!/usr/bin/env python3
"""
Script to add missing support intents for common customer queries
"""

from database import SessionLocal
from models import SupportIntent, SupportResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_intents():
    """Add missing support intents for common queries"""
    db = SessionLocal()
    
    try:
        # Define missing intents and responses
        missing_data = [
            {
                "intent_id": "upgrade_plan",
                "intent_name": "upgrade_plan",
                "description": "Customer wants to upgrade their mobile plan",
                "category": "plan_management",
                "response": """📱 **Plan Upgrade Information**

**How to Upgrade Your Plan:**

**Method 1: Online Account (Recommended)**
1. Log into your account at our website
2. Navigate to "My Plan" or "Plan Management"
3. Click "Upgrade Plan" or "Change Plan"
4. Browse available upgrade options
5. Select your preferred plan and confirm
6. Changes take effect at the start of your next billing cycle

**Method 2: Mobile App**
1. Open our mobile app
2. Go to "Account" → "My Plan"
3. Select "Upgrade Plan"
4. Choose from available upgrade options
5. Confirm your selection

**Method 3: Customer Support**
- **Phone**: Call our 24/7 customer service line
- **Live Chat**: Available on our website and mobile app
- **In-Store**: Visit any of our retail locations

**💡 Upgrade Benefits:**
- More data allowance
- Additional features (international calling, premium content)
- Better value for money
- Family plan options available

**⚠️ Important Notes:**
- Upgrades take effect at the start of your next billing cycle
- No early termination fees for upgrades
- You can upgrade at any time during your contract
- Some upgrades may require a new contract term

**🚨 Need Immediate Assistance?**
Our customer service team is available 24/7 to help you upgrade your plan."""
            },
            {
                "intent_id": "support_hours",
                "intent_name": "support_hours",
                "description": "Customer asking about customer support hours",
                "category": "customer_service",
                "response": """🕒 **Customer Support Hours**

**24/7 Customer Support Available!**

**📞 Phone Support:**
- **Available**: 24 hours a day, 7 days a week
- **No waiting**: Direct access to our support team
- **All languages**: Support available in multiple languages

**💬 Live Chat Support:**
- **Available**: 24/7 on our website and mobile app
- **Instant response**: Connect with an agent immediately
- **File sharing**: Share screenshots and documents

**📧 Email Support:**
- **Response time**: Within 2-4 hours
- **Available**: 24/7 for non-urgent inquiries
- **Follow-up**: We'll keep you updated on your case

**🏪 In-Store Support:**
- **Store hours**: 9:00 AM - 8:00 PM (local time)
- **Days**: Monday through Sunday
- **Services**: Account changes, device support, billing assistance

**🌐 Online Support:**
- **Self-service**: Available 24/7
- **Account management**: Make changes anytime
- **Knowledge base**: Find answers instantly

**🚨 Emergency Support:**
- **Network issues**: Immediate assistance available
- **Billing problems**: 24/7 support for urgent matters
- **Technical issues**: Round-the-clock technical support

**💡 Best Times to Call:**
- **Peak hours**: 9 AM - 5 PM (shorter wait times)
- **Off-peak**: 6 PM - 9 AM (often immediate assistance)
- **Weekends**: Generally shorter wait times

**📱 Quick Support Options:**
- **USSD codes**: Quick balance and usage checks
- **Mobile app**: Self-service options available 24/7
- **Website**: Full account management anytime"""
            },
            {
                "intent_id": "change_plan",
                "intent_name": "change_plan",
                "description": "Customer wants to change their mobile plan",
                "category": "plan_management",
                "response": """📱 **Plan Change Information**

**How to Change Your Plan:**

**Method 1: Online Account (Recommended)**
1. Log into your account at our website
2. Navigate to "My Plan" or "Plan Management"
3. Click "Change Plan" or "Modify Plan"
4. Browse available plans and select your preferred option
5. Review changes and confirm
6. Changes take effect at the start of your next billing cycle

**Method 2: Mobile App**
1. Open our mobile app
2. Go to "Account" → "My Plan"
3. Select "Change Plan"
4. Choose from available options
5. Confirm your selection

**Method 3: Customer Support**
- **Phone**: Call our 24/7 customer service line
- **Live Chat**: Available on our website and mobile app
- **In-Store**: Visit any of our retail locations

**📋 Plan Change Options:**
- **Upgrade**: Move to a higher-tier plan with more data/minutes
- **Downgrade**: Switch to a lower-tier plan (may have restrictions)
- **Sidegrade**: Change to a different plan at the same price point
- **Family Plan**: Combine multiple lines for better rates

**⚠️ Important Considerations:**
- **Billing Cycle**: Plan changes take effect at the start of your next billing cycle
- **Early Termination**: Some plans may have early termination fees
- **Device Compatibility**: Ensure your device supports the new plan features
- **Contract Terms**: Check if changing plans affects your contract length

**💡 Pro Tips:**
- **Compare plans** before making changes
- **Check for promotions** that might offer better deals
- **Consider family plans** if you have multiple lines
- **Review usage patterns** to choose the right plan size
- **Set up plan change reminders** for optimal timing

**🚨 Need Immediate Assistance?**
Our customer service team is available 24/7 to help you change your plan."""
            }
        ]
        
        # Check which intents already exist
        existing_intents = {intent.intent_id: intent for intent in db.query(SupportIntent).all()}
        
        added_count = 0
        for data in missing_data:
            if data["intent_id"] not in existing_intents:
                # Create new intent
                intent = SupportIntent(
                    intent_id=data["intent_id"],
                    intent_name=data["intent_name"],
                    description=data["description"],
                    category=data["category"]
                )
                db.add(intent)
                
                # Create response
                response = SupportResponse(
                    intent_id=data["intent_id"],
                    response_text=data["response"],
                    response_type="text"
                )
                db.add(response)
                
                added_count += 1
                logger.info(f"Added intent: {data['intent_name']}")
            else:
                logger.info(f"Intent already exists: {data['intent_name']}")
        
        # Commit changes
        db.commit()
        logger.info(f"Successfully added {added_count} new intents")
        
        return added_count
        
    except Exception as e:
        logger.error(f"Error adding missing intents: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    print("Adding missing support intents...")
    count = add_missing_intents()
    print(f"Added {count} new intents")
