"""
Twitter API Client
Handles all interactions with the Twitter API
"""

import tweepy
import json
import logging
import os
from typing import Dict, Optional, List, Any
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TwitterClient:
    """Client for interacting with Twitter API"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Twitter client with API credentials
        
        Args:
            config_path: Path to the Twitter configuration file
        """
        self.config = self._load_config(config_path)
        self.api = self._initialize_api()
        self.webhook_url = self.config['twitter']['webhook_url']
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load Twitter API configuration"""
        if not config_path:
            config_path = Path(__file__).parent.parent / 'config' / 'twitter_config.json'
            
        try:
            with open(config_path) as f:
                config = json.load(f)
                
            # Override credentials with environment variables if they exist
            env_mappings = {
                'api_key': 'TWITTER_API_KEY',
                'api_key_secret': 'TWITTER_API_SECRET',
                'access_token': 'TWITTER_ACCESS_TOKEN',
                'access_token_secret': 'TWITTER_ACCESS_SECRET',
                'bearer_token': 'TWITTER_BEARER_TOKEN'
            }
            
            for config_key, env_key in env_mappings.items():
                if os.getenv(env_key):
                    config['twitter'][config_key] = os.getenv(env_key)
                    
            self._validate_config(config)
            return config
        except FileNotFoundError:
            raise Exception(f"Twitter configuration file not found at {config_path}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON in Twitter configuration file")
            
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate that all required configuration fields are present"""
        required_fields = [
            'api_key',
            'api_key_secret',
            'access_token',
            'access_token_secret',
            'bearer_token'
        ]
        
        for field in required_fields:
            if not config['twitter'].get(field):
                raise Exception(f"Missing required Twitter configuration field: {field}")
                
    def _initialize_api(self) -> tweepy.API:
        """Initialize Twitter API client"""
        auth = tweepy.OAuthHandler(
            self.config['twitter']['api_key'],
            self.config['twitter']['api_key_secret']
        )
        auth.set_access_token(
            self.config['twitter']['access_token'],
            self.config['twitter']['access_token_secret']
        )
        
        api = tweepy.API(auth)
        
        # Get and update the numeric account ID if needed
        try:
            if not self.config['twitter']['account']['id'].isdigit():
                user = api.verify_credentials()
                self.config['twitter']['account']['id'] = str(user.id)
                # Save the updated config
                config_path = Path(__file__).parent / 'config' / 'twitter_config.json'
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.warning(f"Could not update numeric account ID: {e}")
        
        return api
        
    def register_webhook(self) -> bool:
        """
        Register webhook URL for account activity updates
        
        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            # Using Twitter Account Activity API to register webhook
            webhook_id = self.api.register_webhook(
                self.webhook_url,
                env_name=self.config['twitter']['webhook_environment']
            )
            logger.info(f"Successfully registered webhook with ID: {webhook_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register webhook: {str(e)}")
            return False
            
    def subscribe_to_user_activity(self) -> bool:
        """
        Subscribe to account activity events
        
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            self.api.subscribe_to_webhook(
                env_name=self.config['twitter']['webhook_environment']
            )
            logger.info("Successfully subscribed to account activity")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to account activity: {str(e)}")
            return False
            
    def get_mentions(self, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent mentions of the authenticated account
        
        Args:
            since_id: Only return mentions newer than this ID
            
        Returns:
            List of mention objects
        """
        try:
            mentions = self.api.mentions_timeline(since_id=since_id)
            return [self._format_tweet(mention) for mention in mentions]
        except Exception as e:
            logger.error(f"Failed to get mentions: {str(e)}")
            return []
            
    def reply_to_tweet(self, tweet_id: str, message: str) -> bool:
        """
        Reply to a tweet
        
        Args:
            tweet_id: ID of the tweet to reply to
            message: Reply message content
            
        Returns:
            bool: True if reply successful, False otherwise
        """
        try:
            self.api.update_status(
                status=message,
                in_reply_to_status_id=tweet_id,
                auto_populate_reply_metadata=True
            )
            logger.info(f"Successfully replied to tweet {tweet_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reply to tweet: {str(e)}")
            return False
            
    def _format_tweet(self, tweet) -> Dict[str, Any]:
        """Format tweet object for internal use"""
        return {
            'id': tweet.id_str,
            'text': tweet.text,
            'created_at': tweet.created_at.replace(tzinfo=timezone.utc),
            'user': {
                'id': tweet.user.id_str,
                'screen_name': tweet.user.screen_name,
                'name': tweet.user.name,
                'followers_count': tweet.user.followers_count,
                'created_at': tweet.user.created_at.replace(tzinfo=timezone.utc)
            },
            'entities': tweet.entities
        }