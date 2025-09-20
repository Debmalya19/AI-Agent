"""
Twitter Webhook Handler
Handles incoming webhooks from Twitter's Account Activity API
"""

from fastapi import APIRouter, Request, HTTPException, Header, Response
from typing import Optional, Dict, Any, List
import hmac
import hashlib
import json
import logging
import os
from dotenv import load_dotenv
from .twitter_client import TwitterClient
from .social_media_integration import SocialMediaMonitor
from .database import SessionLocal

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["twitter"])

class TwitterWebhookHandler:
    def __init__(self):
        self.db = SessionLocal()
        self.twitter_client = TwitterClient()
        self.social_media_monitor = SocialMediaMonitor(self.db)
        self.verify_token = os.getenv("TWITTER_WEBHOOK_VERIFY_TOKEN", "default_token")
        
    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """
        Verify that the webhook request came from Twitter
        
        Args:
            payload: Raw request body
            signature_header: Twitter signature from headers
        """
        if not signature_header:
            logger.warning("No signature header present in request")
            return False
            
        try:
            # Get consumer secret from config
            consumer_secret = self.twitter_client.config['twitter']['api_key_secret']
            
            # Parse signature header
            # Format: sha256=SIGNATURE
            if '=' not in signature_header:
                logger.warning("Invalid signature header format")
                return False
                
            signature_type, signature = signature_header.split('=')
            if signature_type.lower() != 'sha256':
                logger.warning(f"Unsupported signature type: {signature_type}")
                return False
            
            # Create expected signature
            expected_signature = hmac.new(
                consumer_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(
                expected_signature,
                signature
            )
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False
            
    async def handle_challenge_response(self, crc_token: str) -> Dict[str, str]:
        """
        Handle Twitter's Challenge Response Check (CRC)
        """
        consumer_secret = self.twitter_client.config['twitter']['api_key_secret']
        
        # Create response token
        sha256_hash_digest = hmac.new(
            consumer_secret.encode('utf-8'),
            crc_token.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return {
            'response_token': f'sha256={sha256_hash_digest.hex()}'
        }

@router.get("/webhook/twitter")
async def twitter_crc_check(request: Request, crc_token: Optional[str] = None):
    """
    Handle Twitter Account Activity API CRC check
    This endpoint is used by Twitter to verify webhook ownership
    """
    logger.info("Received CRC check from Twitter")
    
    # Check for crc_token in query parameters if not in header
    if not crc_token:
        crc_token = request.query_params.get("crc_token")
        
    if not crc_token:
        logger.error("Missing crc_token in request")
        raise HTTPException(status_code=400, detail="Missing crc_token")
        
    try:
        handler = TwitterWebhookHandler()
        response = await handler.handle_challenge_response(crc_token)
        logger.info("Successfully responded to CRC check")
        return response
    except Exception as e:
        logger.error(f"Error handling CRC check: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing CRC check")

@router.post("/webhook/twitter")
async def twitter_webhook(
    request: Request,
    x_twitter_webhooks_signature: Optional[str] = Header(None)
):
    """
    Handle incoming webhooks from Twitter Activity API
    Processes various webhook events including tweets, direct messages, etc.
    """
    handler = TwitterWebhookHandler()
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    if not handler.verify_signature(body, x_twitter_webhooks_signature):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        # Parse webhook payload
        payload = json.loads(body)
        
        # Log webhook event type
        event_type = next(iter(payload.keys())) if payload else "unknown"
        logger.info(f"Received webhook event type: {event_type}")
        
        # Handle different types of events
        if "tweet_create_events" in payload:
            await handle_tweet_events(handler, payload["tweet_create_events"])
        elif "direct_message_events" in payload:
            await handle_dm_events(handler, payload["direct_message_events"])
        elif "favorite_events" in payload:
            await handle_favorite_events(handler, payload["favorite_events"])
            
        return {"status": "success", "message": f"Processed {event_type} event"}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def handle_tweet_events(handler: TwitterWebhookHandler, tweets: List[Dict[str, Any]]):
    """Handle tweet creation events"""
    for tweet in tweets:
        # Skip our own tweets
        if tweet.get("user", {}).get("id_str") == handler.twitter_client.config["twitter"]["account"]["id"]:
            logger.debug("Skipping own tweet")
            continue
            
        try:
            # Process the tweet
            ticket_id = handler.social_media_monitor.process_tweet(tweet)
            if ticket_id:
                logger.info(f"Created ticket #{ticket_id} for tweet {tweet['id_str']}")
            else:
                logger.info(f"No ticket created for tweet {tweet['id_str']} (positive sentiment)")
        except Exception as e:
            logger.error(f"Error processing tweet {tweet.get('id_str')}: {str(e)}")

async def handle_dm_events(handler: TwitterWebhookHandler, dms: List[Dict[str, Any]]):
    """Handle direct message events"""
    logger.info(f"Received {len(dms)} direct message events")
    # Implement DM handling if needed

async def handle_favorite_events(handler: TwitterWebhookHandler, favorites: List[Dict[str, Any]]):
    """Handle tweet favorite events"""
    logger.info(f"Received {len(favorites)} favorite events")
    # Implement favorite handling if needed
    handler = TwitterWebhookHandler()
    
    # Get raw request body
    payload = await request.body()
    
    # Verify webhook signature
    if not handler.verify_signature(payload, x_twitter_webhooks_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
        
    # Parse webhook data
    try:
        webhook_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    # Process tweet_create_events
    if 'tweet_create_events' in webhook_data:
        for tweet in webhook_data['tweet_create_events']:
            # Skip tweets created by us
            if tweet.get('user', {}).get('id_str') == handler.twitter_client.config['twitter'].get('account_id'):
                continue
                
            # Format tweet data
            tweet_data = handler.twitter_client._format_tweet(tweet)
            
            # Process mention through social media monitor
            try:
                ticket_id = handler.social_media_monitor.process_tweet(tweet_data)
                
                if ticket_id:
                    # Create a reply with the ticket information
                    reply = f"Thanks for reaching out! We've created ticket #{ticket_id} to help you. We'll keep you updated on the progress."
                    handler.twitter_client.reply_to_tweet(tweet['id_str'], reply)
                    
            except Exception as e:
                logger.error(f"Error processing tweet {tweet['id_str']}: {str(e)}")
                
    return {"success": True}