from typing import Optional
import resend

from src.core.config import settings


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> None:
    """Send an email via the official Resend Python SDK."""
    print(f"[RESEND] === EMAIL SEND START ===", flush=True)
    print(f"[RESEND] To: {to}, From: {settings.MAIL_FROM}", flush=True)
    print(f"[RESEND] API Key set: {'YES' if settings.RESEND_API_KEY else 'NO (EMPTY!)'}", flush=True)

    if not settings.RESEND_API_KEY:
        print("[RESEND] ERROR: RESEND_API_KEY is empty — cannot send email.", flush=True)
        raise RuntimeError("RESEND_API_KEY is not configured")

    resend.api_key = settings.RESEND_API_KEY

    params = {
        "from": f"{settings.APP_NAME} <{settings.MAIL_FROM}>",
        "to": [to],
        "subject": subject,
        "html": html_body,
    }

    if text_body:
        params["text"] = text_body

    try:
        # resend-python is synchronous, but we wrap it in our async function
        # For production with many emails, it's better to run in a threadpool
        # but for now we follow the existing pattern.
        response = resend.Emails.send(params)
        print(f"[RESEND] SUCCESS — Email sent to {to} (ID: {response.get('id')})", flush=True)
    except Exception as exc:
        print(f"[RESEND] FAILED — Exception: {exc}", flush=True)
        raise RuntimeError(f"Resend error: {exc}") from exc
