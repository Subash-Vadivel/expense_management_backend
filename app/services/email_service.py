from __future__ import annotations

import html
import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

BRAND = "Ledgerline"


def send_email(to: str, subject: str, html_body: str, text_body: str) -> None:
    """Send a transactional email. Never raises: failures are logged so callers' requests still succeed.

    Synchronous on purpose; schedule via FastAPI BackgroundTasks so it runs in the threadpool.
    """
    if not settings.resend_emails_api_key:
        logger.warning("RESEND_EMAILS_API_KEY not set; email not sent. to=%s subject=%s\n%s", to, subject, text_body)
        return
    resend.api_key = settings.resend_emails_api_key
    try:
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
        )
    except Exception:  # noqa: BLE001 - email must never break the request flow
        logger.exception("Failed to send email to=%s subject=%s", to, subject)


def _layout(heading: str, intro_html: str, button_label: str, url: str, footer: str) -> str:
    safe_url = html.escape(url, quote=True)
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#f4f6f3;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1f2a1f;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:12px;padding:32px;">
      <tr><td>
        <p style="margin:0 0 24px;font-size:18px;font-weight:700;color:#2f6b3a;">{BRAND}</p>
        <h1 style="margin:0 0 16px;font-size:22px;">{html.escape(heading)}</h1>
        <div style="font-size:15px;line-height:1.6;">{intro_html}</div>
        <p style="margin:28px 0;">
          <a href="{safe_url}" style="display:inline-block;background:#2f6b3a;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;">{html.escape(button_label)}</a>
        </p>
        <p style="font-size:13px;color:#5b665b;line-height:1.5;">If the button doesn't work, copy this link into your browser:<br>
          <a href="{safe_url}" style="color:#2f6b3a;word-break:break-all;">{safe_url}</a></p>
        <p style="font-size:13px;color:#5b665b;margin-top:24px;">{html.escape(footer)}</p>
      </td></tr>
    </table>
  </body>
</html>"""


def frontend_link(path: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{path}"


def send_verification_email(to: str, name: str, url: str) -> None:
    hours = settings.email_verification_expire_hours
    send_email(
        to,
        f"Verify your email for {BRAND}",
        _layout(
            "Verify your email",
            f"<p>Hi {html.escape(name)},</p><p>Thanks for signing up. Confirm your email address to start using {BRAND}.</p>",
            "Verify email",
            url,
            f"This link expires in {hours} hours. If you didn't create an account, you can ignore this email.",
        ),
        f"Hi {name},\n\nConfirm your email address to start using {BRAND}:\n{url}\n\n"
        f"This link expires in {hours} hours. If you didn't create an account, ignore this email.",
    )


def send_password_reset_email(to: str, name: str, url: str) -> None:
    minutes = settings.password_reset_expire_minutes
    send_email(
        to,
        f"Reset your {BRAND} password",
        _layout(
            "Reset your password",
            f"<p>Hi {html.escape(name)},</p><p>We received a request to reset your password. Click below to choose a new one.</p>",
            "Reset password",
            url,
            f"This link expires in {minutes} minutes and can be used once. If you didn't request this, you can ignore this email.",
        ),
        f"Hi {name},\n\nReset your password here:\n{url}\n\n"
        f"This link expires in {minutes} minutes. If you didn't request this, ignore this email.",
    )


def send_invitation_email(to: str, business_name: str, inviter_name: str, role: str, url: str) -> None:
    send_email(
        to,
        f"{inviter_name} invited you to {business_name} on {BRAND}",
        _layout(
            f"Join {business_name}",
            f"<p><strong>{html.escape(inviter_name)}</strong> invited you to join "
            f"<strong>{html.escape(business_name)}</strong> on {BRAND} as <strong>{html.escape(role)}</strong>.</p>"
            f"<p>Sign in or create an account with <strong>{html.escape(to)}</strong> to accept.</p>",
            "Accept invitation",
            url,
            "This invitation expires in 14 days.",
        ),
        f"{inviter_name} invited you to join {business_name} on {BRAND} as {role}.\n\n"
        f"Accept the invitation with {to}:\n{url}\n\nThis invitation expires in 14 days.",
    )
