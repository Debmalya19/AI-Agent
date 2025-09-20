# Twitter Webhook Setup Guide

## Getting a Webhook URL

### Production Setup
If you have a production server:
1. Ensure you have a domain name pointing to your server
2. Install an SSL certificate (you can use Let's Encrypt for free)
3. Your webhook URL will be: `https://your-domain.com/webhook/twitter`

### Development Setup using ngrok
For local development and testing:

1. Install ngrok:
```bash
# Using npm
npm install -g ngrok

# Or download from ngrok.com
```

2. Start your FastAPI server:
```bash
# From your project root
uvicorn main:app --host 0.0.0.0 --port 8000
```

3. In a new terminal, start ngrok:
```bash
ngrok http 8000
```

4. Ngrok will display a URL like:
```
Forwarding https://random-string.ngrok.io -> http://localhost:8000
```

5. Your webhook URL will be:
```
https://random-string.ngrok.io/webhook/twitter
```

## Configuring the Webhook

1. Update your `twitter_config.json`:
```json
{
    "twitter": {
        "api_key": "your_api_key",
        "api_key_secret": "your_api_secret",
        "access_token": "your_access_token",
        "access_token_secret": "your_access_token_secret",
        "bearer_token": "your_bearer_token",
        "webhook_url": "https://your-domain.com/webhook/twitter",
        "webhook_environment": "production"
    }
}
```

2. Register your webhook URL in Twitter Developer Portal:
   - Go to https://developer.twitter.com
   - Navigate to your app settings
   - Under "App Settings" > "Account Activity API" > "Dev environments"
   - Add your webhook URL

## Important Notes

1. The webhook URL must be:
   - Publicly accessible
   - Using HTTPS (not HTTP)
   - Responding to Twitter's CRC (Challenge Response Check)

2. For development:
   - Ngrok URLs change every time you restart ngrok
   - You'll need to update both `twitter_config.json` and Twitter Developer Portal
   - Consider a paid ngrok account for persistent URLs

3. For production:
   - Use a stable domain name
   - Ensure proper SSL/TLS configuration
   - Configure proper security headers and rate limiting