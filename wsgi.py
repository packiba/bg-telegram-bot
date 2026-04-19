from webhook_app import app
import asyncio

# For gunicorn
application = app

# For direct run
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5000))
    from aiohttp import web
    web.run_app(app, host="0.0.0.0", port=port)