"""
Verify Twitter webhook configuration and accessibility
"""

import requests
import json
from pathlib import Path
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """Load Twitter configuration"""
    config_path = Path(__file__).parent.parent / 'backend' / 'config' / 'twitter_config.json'
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in configuration file")
        sys.exit(1)

def verify_webhook_url(url):
    """Verify webhook URL is accessible and using HTTPS"""
    if not url.startswith('https://'):
        logger.error("Webhook URL must use HTTPS")
        return False
        
    try:
        response = requests.get(url)
        logger.info(f"Webhook endpoint response status: {response.status_code}")
        
        if response.status_code == 404:
            logger.warning("Webhook endpoint returns 404 - This is OK if the server only accepts POST requests")
            return True
            
        return response.status_code < 500
        
    except requests.exceptions.SSLError:
        logger.error("SSL certificate verification failed")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to webhook URL")
        return False

def main():
    """Main verification function"""
    logger.info("Loading configuration...")
    config = load_config()
    
    webhook_url = config['twitter']['webhook_url']
    if not webhook_url:
        logger.error("Webhook URL not configured in twitter_config.json")
        sys.exit(1)
        
    logger.info(f"Verifying webhook URL: {webhook_url}")
    
    if verify_webhook_url(webhook_url):
        logger.info("✓ Webhook URL is accessible")
        logger.info("Next steps:")
        logger.info("1. Register this URL in your Twitter Developer Portal")
        logger.info("2. Ensure your server is handling CRC requests")
        logger.info("3. Subscribe to account activity events")
    else:
        logger.error("✗ Webhook URL verification failed")
        logger.error("Please check your configuration and server accessibility")

if __name__ == "__main__":
    main()