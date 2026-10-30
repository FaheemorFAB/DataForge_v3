"""
dataforge/api/services/mailer.py
────────────────────────────────
Production Outbound Email & Notification Dispatch Service.
Exclusively uses Resend API (HTTP) for transactional and collaboration emails,
with graceful simulated fallback for local development when credentials are absent.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Dict, Optional

from dataforge.api.config import get_settings

log = logging.getLogger(__name__)


class EmailDeliveryService:
    """Dispatches transactional emails for collaboration invites, notifications, and alerts via Resend."""

    @classmethod
    def send_collaborator_invite(
        cls,
        recipient_email: str,
        role: str,
        dataset_name: str,
        upload_id: str,
        inviter_name_or_email: str,
        share_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends an official email invitation to access a dataset in DataForge via Resend.
        """
        settings = get_settings()
        subject = f"Invitation: {inviter_name_or_email} shared dataset '{dataset_name}' with you on DataForge"
        
        # Build access link
        base_url = settings.FRONTEND_URL.rstrip("/")
        access_url = f"{base_url}/workspace?upload_id={upload_id}"
        if share_token:
            access_url += f"&share_token={share_token}"

        text_body = (
            f"Hello,\n\n"
            f"{inviter_name_or_email} has invited you to collaborate on the dataset '{dataset_name}' "
            f"with role: {role}.\n\n"
            f"Click the link below to open the dataset in DataForge:\n"
            f"{access_url}\n\n"
            f"Role capabilities:\n"
            f"- {role}: Full access in accordance with workspace governance.\n\n"
            f"— The DataForge Team\n"
        )

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 32px; }}
            .header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 24px; }}
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700; background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4); }}
            h2 {{ color: #ffffff; margin-top: 0; font-size: 20px; }}
            p {{ color: #9ca3af; line-height: 1.6; font-size: 14px; }}
            .cta-btn {{ display: inline-block; background: #6366f1; color: #ffffff !important; text-decoration: none; font-weight: 700; padding: 12px 24px; border-radius: 10px; margin: 20px 0; font-size: 14px; }}
            .footer {{ border-top: 1px solid #1f2937; margin-top: 24px; padding-top: 16px; font-size: 12px; color: #6b7280; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="badge">DataForge Collaboration</div>
            <h2>You've been invited to collaborate</h2>
            <p><strong style="color:#ffffff;">{inviter_name_or_email}</strong> has granted you <strong style="color:#818cf8;">{role}</strong> access to dataset <strong style="color:#ffffff;">'{dataset_name}'</strong>.</p>
            <p>You can now inspect distributions, run SQL queries, review audit logs, and trigger AutoML pipelines.</p>
            <div>
              <a href="{access_url}" class="cta-btn" target="_blank">Open Dataset in Workspace →</a>
            </div>
            <p style="font-size:12px; color:#6b7280;">Direct URL: <a href="{access_url}" style="color:#818cf8;">{access_url}</a></p>
            <div class="footer">
              DataForge Secure Engine · Enterprise Lakehouse & Analytics
            </div>
          </div>
        </body>
        </html>
        """

        # Exclusively use Resend HTTP API
        if settings.RESEND_API_KEY:
            try:
                resend_payload = json.dumps({
                    "from": settings.MAIL_FROM,
                    "to": [recipient_email],
                    "subject": subject,
                    "text": text_body,
                    "html": html_body,
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.resend.com/emails",
                    data=resend_payload,
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                        "User-Agent": "DataForge-Backend/3.0",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    log.info("[mailer/resend] Successfully sent invite email to %s (id=%s)", recipient_email, resp_data.get("id"))
                    return {
                        "sent": True,
                        "transport": "resend",
                        "recipient": recipient_email,
                        "email_id": resp_data.get("id"),
                        "access_url": access_url,
                    }
            except Exception as e:
                log.error("[mailer/resend] Failed to send email via Resend: %s", e)
                return {
                    "sent": False,
                    "transport": "resend",
                    "error": str(e),
                    "recipient": recipient_email,
                    "access_url": access_url,
                }

        # Simulated fallback for local dev when RESEND_API_KEY is omitted
        log.info(
            "[mailer/simulated] (No RESEND_API_KEY configured) Simulated email to %s for dataset %s with access link: %s",
            recipient_email, upload_id, access_url
        )
        return {
            "sent": False,
            "transport": "simulated",
            "reason": "Missing RESEND_API_KEY in .env (configure RESEND_API_KEY to send real emails)",
            "recipient": recipient_email,
            "access_url": access_url,
        }
