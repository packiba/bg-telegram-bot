# Skill: deployment

## Overview

Use this skill when deploying the Bulgarian-Russian translator bot to any platform. Provides step-by-step instructions for each deployment target.

## When to Use

- User asks to deploy the bot
- User asks about hosting options
- User needs help with deployment configuration
- User encounters deployment-related issues

## Pre-deployment Checklist

1. [ ] `TELEGRAM_BOT_TOKEN` obtained from @BotFather
2. [ ] `OPENROUTER_API_KEY` obtained from openrouter.ai
3. [ ] `.env` file created with all required variables
4. [ ] `requirements.txt` is up to date
5. [ ] Bot works locally in polling mode
6. [ ] Database directory exists (`data/`)

## Deployment: Local (Testing)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env
# Edit .env with your tokens

# 3. Run bot (polling mode - no WEBHOOK_URL in .env)
python bot.py
```

**Notes:**
- Simplest method, good for development
- Bot runs in foreground (use `nohup` or `tmux` for background)
- No HTTPS required

## Deployment: PythonAnywhere (Free, Webhook)

### Step 1: Account Setup
1. Register at https://www.pythonanywhere.com
2. Create a new Web App (Flask framework)
3. Note your username and domain: `https://<username>.pythonanywhere.com`

### Step 2: Upload Code
1. Open Bash console
2. Clone repo or upload files to home directory
3. Install dependencies:
   ```bash
   pip3.10 install --user -r requirements.txt
   ```

### Step 3: Configure Environment
1. Go to Web tab
2. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL` (optional)
   - `WEBHOOK_URL=https://<username>.pythonanywhere.com`
   - `DATABASE_PATH=/home/<username>/data/bot.db`

### Step 4: Configure WSGI
Edit `/var/www/<username>_pythonanywhere_com_wsgi.py`:
```python
import sys
path = '/home/<username>/bg-telegram-bot'
if path not in sys.path:
    sys.path.append(path)

from webhook_app import app as application
```

### Step 5: Set Webhook
Run in console:
```python
import requests
requests.post(
    f"https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook",
    data={"url": "https://<username>.pythonanywhere.com/webhook"}
)
```

### Step 6: Reload Web App
- Go to Web tab → Click "Reload"

**Important:**
- Free accounts expire every 3 months - must click "Run until 3 months" button
- Webhook URL must match exactly (including `/webhook` path)
- Database path must be absolute

## Deployment: Oracle Cloud Free Tier (VM, Polling)

### Step 1: Create VM
1. Go to Oracle Cloud Console
2. Create VM instance:
   - Image: Ubuntu 22.04
   - Shape: VM.Standard.E2.1.Micro (Always Free)
   - Add SSH key
   - Open ports 22 (SSH)

### Step 2: Connect and Setup
```bash
ssh -i <your-key> ubuntu@<vm-public-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Clone repo
git clone <repo-url>
cd bg-telegram-bot

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
nano .env
# Add your tokens
```

### Step 3: Create Systemd Service
```bash
sudo nano /etc/systemd/system/bg-bot.service
```

Content:
```ini
[Unit]
Description=Bulgarian-Russian Translator Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bg-telegram-bot
Environment=PATH=/home/ubuntu/bg-telegram-bot/venv/bin
ExecStart=/home/ubuntu/bg-telegram-bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Step 4: Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable bg-bot
sudo systemctl start bg-bot

# Check status
sudo systemctl status bg-bot

# View logs
sudo journalctl -u bg-bot -f
```

**Notes:**
- Bot runs as systemd service (auto-restart on crash)
- No webhook needed (polling mode)
- Use `WEBHOOK_URL` not set in `.env`

## Deployment: Koyeb (Webhook)

### Step 1: Connect Repository
1. Go to https://app.koyeb.com
2. Click "Create Service"
3. Connect GitHub repository
4. Select branch (main/master)

### Step 2: Configure
- **Builder:** Buildpack (auto-detect Python)
- **Run command:** `python webhook_app.py`
- **Environment variables:**
  - `TELEGRAM_BOT_TOKEN`
  - `OPENROUTER_API_KEY`
  - `WEBHOOK_URL=https://<service-url>.koyeb.app`
  - `PORT=8000` (Koyeb sets this automatically)

### Step 3: Deploy
1. Click "Deploy"
2. Wait for deployment to complete
3. Note the service URL

### Step 4: Set Webhook
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d "url=https://<service-url>.koyeb.app/webhook"
```

**Notes:**
- Free tier may have cold starts
- Webhook URL must use HTTPS (Koyeb provides this)
- Database should use persistent volume or external DB

## Deployment: Render (Webhook)

### Step 1: Connect Repository
1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect GitHub repository

### Step 2: Configure
- **Name:** bg-telegram-bot
- **Environment:** Python 3
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python webhook_app.py`
- **Environment variables:**
  - `TELEGRAM_BOT_TOKEN`
  - `OPENROUTER_API_KEY`
  - `WEBHOOK_URL=https://<service-url>.onrender.com`

### Step 3: Deploy
1. Click "Create Web Service"
2. Wait for deployment
3. Set webhook via curl (same as Koyeb step 4)

**Notes:**
- Free tier spins down after 15 minutes of inactivity
- First request after spin-down will be slow
- Consider paid tier for production

## Troubleshooting

### Webhook not receiving updates
```bash
# Check webhook status
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"

# Expected: {"ok":true,"result":{"url":"...","has_custom_certificate":false,"pending_update_count":0}}
```

### Bot not responding
```bash
# Check logs (systemd)
sudo journalctl -u bg-bot -n 50

# Check logs (PythonAnywhere)
See Error log in Web tab

# Check logs (Koyeb/Render)
See deployment logs in dashboard
```

### Database errors
- Ensure `data/` directory exists and is writable
- Check `DATABASE_PATH` is absolute path
- Verify file permissions

### API key errors
- Verify `OPENROUTER_API_KEY` is correct
- Check API key has not expired
- Test API key with curl:
  ```bash
  curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"google/gemini-3-flash-preview","messages":[{"role":"user","content":"test"}]}'
  ```

## Migration Between Platforms

### Polling → Webhook
1. Set `WEBHOOK_URL` in `.env`
2. Deploy with webhook mode
3. Bot will auto-detect and use webhook

### Webhook → Polling
1. Remove `WEBHOOK_URL` from `.env`
2. Delete webhook from Telegram:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook"
   ```
3. Run in polling mode

## Cost Comparison

| Platform | Cost | Renewal | HTTPS | Persistence |
|----------|------|---------|-------|-------------|
| Local | Free | N/A | No | Yes |
| PythonAnywhere | Free | 3 months | Yes | Yes |
| Oracle Cloud | Free | Never | Manual | Yes |
| Koyeb | Free | N/A | Yes | Limited |
| Render | Free | N/A | Yes | Limited |
