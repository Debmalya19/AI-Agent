"""
Script to register Twitter webhook
"""

import asyncio
from backend.twitter_client import TwitterClient

async def register_webhook():
    client = TwitterClient()
    try:
        # Register webhook
        result = await client.register_webhook()
        if result:
            print(" Webhook registered successfully")
            print(f"URL: {client.config['twitter']['webhook']['url']}")
        else:
            print(" Failed to register webhook")
    except Exception as e:
        print(f" Error registering webhook: {str(e)}")

if __name__ == "__main__":
    asyncio.run(register_webhook())