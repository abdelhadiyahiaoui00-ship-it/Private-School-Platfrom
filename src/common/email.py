"""
Email helper — sends via Vercel relay → Resend.
Never raises; failures are logged and swallowed so email never
blocks a business transaction.
"""
import logging

import httpx

from src.core.config import settings

logger = logging.getLogger(settings.APP_NAME)


async def send_email(type: str, to: str, **kwargs) -> bool:
    """
    Fire-and-forget email dispatch.
    Returns True on success, False on any failure.
    """
    if not settings.VERCEL_EMAIL_URL or not settings.EMAIL_API_SECRET:
        logger.warning("Email not configured — skipping %s to %s", type, to)
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.VERCEL_EMAIL_URL,
                json={"type": type, "to": to, **kwargs},
                headers={"x-api-secret": settings.EMAIL_API_SECRET},
                timeout=10.0,
            )
        if resp.status_code == 200:
            return True
        logger.error("Email relay returned %s for type=%s", resp.status_code, type)
        return False
    except Exception as exc:
        logger.error("Email send failed for type=%s: %s", type, exc)
        return False
