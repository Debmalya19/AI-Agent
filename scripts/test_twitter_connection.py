"""
Test Twitter account connection and configuration
"""

import os
import sys
import tweepy
import json
from pathlib import Path
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.twitter_client import TwitterClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_twitter_connection():
    """Test Twitter API connection and account access"""
    try:
        logger.info("Loading configuration...")
        # Initialize Twitter client
        client = TwitterClient()
        
        # Test API connection
        logger.info("\nTesting Twitter API connection...")
        user = client.api.verify_credentials()
        
        logger.info("\n Account Information:")
        logger.info("-" * 50)
        logger.info(f"Username: @{user.screen_name}")
        logger.info(f"Display Name: {user.name}")
        logger.info(f"Account ID: {user.id}")
        logger.info(f"Followers: {user.followers_count}")
        logger.info(f"Account Created: {user.created_at}")
        logger.info("-" * 50)
        
        # Verify configured account matches
        config_handle = client.config['twitter']['account']['handle']
        if config_handle != user.screen_name:
            logger.warning(f"\n Warning: Configured handle '@{config_handle}' doesn't match authenticated account '@{user.screen_name}'")
        else:
            logger.info("\n Account handle verification successful")
        
        # Test reading mentions
        logger.info("\nTesting mention retrieval...")
        try:
            mentions = client.get_mentions(limit=1)
            if mentions:
                logger.info(" Successfully retrieved mentions")
                mention = mentions[0]
                logger.info(f"Latest mention from: @{mention['user']['screen_name']}")
                logger.info(f"Content: {mention['text']}")
            else:
                logger.info(" API working but no recent mentions found")
        except Exception as e:
            logger.error(f"Error retrieving mentions: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f" Error testing Twitter connection: {str(e)}")
        return False

def main():
    """Main test function"""
    success = test_twitter_connection()
    
    if success:
        logger.info("\n Twitter account setup is complete and working!")
        logger.info("You can now start the server to begin processing mentions")
    else:
        logger.error("\n Twitter account setup needs attention")
        logger.error("Please verify your configuration and account credentials")

if __name__ == "__main__":
    main()