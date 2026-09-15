"""
Email service — sends HTML emails via the Vercel relay route to Resend.
Swallows all exceptions silently; email failures never propagate.
"""
from __future__ import annotations

import logging

import httpx
import jinja2

from src.core.config import settings
from src.infrastructure.mail.email_templates import get_email_template

logger = logging.getLogger(settings.APP_NAME)

# ─── Localized subject lines ──────────────────────────────────────────────────

_SUBJECTS: dict[str, dict[str, str]] = {
    "ar": {
        "enrollment_approved": "تم قبول التسجيل ✅",
        "enrollment_rejected": "تم رفض التسجيل",
        "subscription_expiring": "اشتراكك ينتهي قريباً ⚠️",
        "subscription_expired": "انتهى اشتراكك 🔴",
        "payment_confirmed": "تم تأكيد الدفع ✅",
        "assignment_submitted": "تم استلام واجب جديد 📝",
        "enrollment_group_transferred": "تم نقل تسجيلك 🔄",
    },
    "en": {
        "enrollment_approved": "Enrollment Approved ✅",
        "enrollment_rejected": "Enrollment Not Approved",
        "subscription_expiring": "Subscription Expiring Soon ⚠️",
        "subscription_expired": "Subscription Expired 🔴",
        "payment_confirmed": "Payment Confirmed ✅",
        "assignment_submitted": "Assignment Submitted 📝",
        "enrollment_group_transferred": "Enrollment Transferred 🔄",
    },
    "fr": {
        "enrollment_approved": "Inscription approuvée ✅",
        "enrollment_rejected": "Inscription non approuvée",
        "subscription_expiring": "Abonnement expirant bientôt ⚠️",
        "subscription_expired": "Abonnement expiré 🔴",
        "payment_confirmed": "Paiement confirmé ✅",
        "assignment_submitted": "Devoir soumis 📝",
        "enrollment_group_transferred": "Inscription transférée 🔄",
    },
}


class EmailService:
    """
    Sends HTML emails via the Vercel relay (→ Resend).

    Usage::

        service = EmailService()
        await service.send_email(
            to="student@example.com",
            notification_type="enrollment_approved",
            template_vars={"firstName": "Ali", "className": "Maths S3", ...},
            locale="ar",
        )
    """

    def __init__(self) -> None:
        self._vercel_url = settings.VERCEL_EMAIL_URL
        self._api_secret = settings.EMAIL_API_SECRET

    # ── Public API ────────────────────────────────────────────────────────────

    async def send_email(
        self,
        to: str,
        notification_type: str,
        template_vars: dict,
        locale: str = "ar",
    ) -> bool:
        """
        Render and send one email.

        Returns True on HTTP 200; False on any other outcome.
        Never raises — email is a best-effort side-channel.
        """
        if not self._vercel_url or not to:
            return False

        template_html = get_email_template(notification_type, locale)
        if not template_html:
            logger.warning("EmailService: no template for type=%s locale=%s", notification_type, locale)
            return False

        try:
            rendered_html = jinja2.Template(template_html).render(**template_vars)
        except Exception as exc:
            logger.error("EmailService: template render failed type=%s: %s", notification_type, exc)
            return False

        subject = self._get_subject(notification_type, locale)

        payload = {
            "to": to,
            "subject": subject,
            "html": rendered_html,
            "type": notification_type,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._vercel_url,
                    json=payload,
                    headers={"x-api-secret": self._api_secret},
                    timeout=10.0,
                )
            success = resp.status_code == 200
            if not success:
                logger.warning(
                    "EmailService: relay returned %s for type=%s to=%s",
                    resp.status_code, notification_type, to,
                )
            return success
        except Exception as exc:
            logger.error("EmailService: HTTP error type=%s to=%s: %s", notification_type, to, exc)
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_subject(self, notification_type: str, locale: str) -> str:
        locale_subjects = _SUBJECTS.get(locale) or _SUBJECTS["ar"]
        return locale_subjects.get(notification_type, "إشعار")
