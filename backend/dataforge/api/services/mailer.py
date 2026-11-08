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
        
        # Build access link (uses public production URL for live recipient access)
        base_url = settings.FRONTEND_URL.rstrip("/")
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "https://numan-10.site"

        access_url = f"{base_url}/workspace?upload_id={upload_id}"
        if share_token:
            access_url += f"&share_token={share_token}"

        text_body = (
            f"Hello,\n\n"
            f"{inviter_name_or_email} has invited you to collaborate on dataset '{dataset_name}' "
            f"with {role} access on DataForge.\n\n"
            f"Open Dataset in Workspace:\n"
            f"{access_url}\n\n"
            f"Dataset: {dataset_name}\n"
            f"Role: {role}\n"
            f"Invited by: {inviter_name_or_email}\n\n"
            f"— The DataForge Team\n"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Invitation to Collaborate</title>
</head>
<body style="margin: 0; padding: 32px 16px; background-color: #090d16; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9; -webkit-font-smoothing: antialiased;">
  <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <!-- Brand Header -->
    <tr>
      <td style="padding: 28px 32px 20px 32px; border-bottom: 1px solid #1e293b;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td style="vertical-align: middle;">
              <span style="font-size: 21px; font-weight: 800; letter-spacing: -0.03em; color: #ffffff;">
                Data<span style="color: #6366f1;">Forge</span>
              </span>
            </td>
            <td style="vertical-align: middle; text-align: right;">
              <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b;">
                Workspace Invite
              </span>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Main Content -->
    <tr>
      <td style="padding: 32px;">
        <h1 style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -0.02em; line-height: 1.3;">
          You've been invited to collaborate
        </h1>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
          <strong style="color: #f1f5f9;">{inviter_name_or_email}</strong> has invited you to inspect and analyze a dataset on DataForge with <strong style="color: #818cf8;">{role}</strong> permissions.
        </p>

        <!-- Metadata Spec Box -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background: #162032; border: 1px solid #24324a; border-radius: 12px; margin-bottom: 28px;">
          <tr>
            <td style="padding: 14px 18px; border-bottom: 1px solid #1f2c42;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Dataset</td>
                  <td style="color: #f8fafc; font-size: 13px; font-weight: 700; text-align: right;">{dataset_name}</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding: 14px 18px; border-bottom: 1px solid #1f2c42;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Assigned Role</td>
                  <td style="text-align: right;">
                    <span style="display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.35);">{role}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding: 14px 18px;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Invited by</td>
                  <td style="color: #cbd5e1; font-size: 13px; font-weight: 600; text-align: right;">{inviter_name_or_email}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <!-- Primary CTA Button -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0 20px 0;">
          <tr>
            <td align="center">
              <a href="{access_url}" target="_blank" style="display: inline-block; background: #6366f1; color: #ffffff !important; font-size: 14px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35); letter-spacing: -0.01em;">
                Open Dataset in Workspace &rarr;
              </a>
            </td>
          </tr>
        </table>

        <!-- Direct URL Fallback -->
        <p style="font-size: 12px; color: #64748b; line-height: 1.6; margin: 20px 0 0 0; text-align: center;">
          Or copy and paste this link in your browser:<br>
          <a href="{access_url}" style="color: #818cf8; text-decoration: underline; word-break: break-all;">{access_url}</a>
        </p>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="padding: 20px 32px 28px 32px; border-top: 1px solid #1e293b; text-align: center;">
        <p style="font-size: 11px; color: #475569; line-height: 1.6; margin: 0;">
          This invitation was sent by DataForge Secure Analytics to <strong style="color: #64748b;">{recipient_email}</strong>.<br>
          If you were not expecting this invitation, you can safely ignore this email.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        return cls._dispatch_via_resend(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            context_url=access_url,
        )

    @classmethod
    def send_team_workspace_invite(
        cls,
        recipient_email: str,
        role: str,
        org_name: str,
        inviter_name_or_email: str,
        org_id: str = "",
    ) -> Dict[str, Any]:
        """
        Sends an official email notification when a user is added to an Organization/Team Workspace via Resend.
        """
        settings = get_settings()
        subject = f"Invitation: {inviter_name_or_email} added you to {org_name} on DataForge"

        base_url = settings.FRONTEND_URL.rstrip("/")
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "https://numan-10.site"

        workspace_url = f"{base_url}/dashboard?workspace={org_id}" if org_id else f"{base_url}/dashboard"

        text_body = (
            f"Hello,\n\n"
            f"{inviter_name_or_email} has added you to the '{org_name}' Team Workspace "
            f"with {role} permissions on DataForge.\n\n"
            f"Open Team Workspace:\n"
            f"{workspace_url}\n\n"
            f"Workspace: {org_name}\n"
            f"Assigned Role: {role}\n"
            f"Added by: {inviter_name_or_email}\n\n"
            f"— The DataForge Team\n"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Team Workspace Invitation</title>
</head>
<body style="margin: 0; padding: 32px 16px; background-color: #090d16; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9; -webkit-font-smoothing: antialiased;">
  <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <!-- Brand Header -->
    <tr>
      <td style="padding: 28px 32px 20px 32px; border-bottom: 1px solid #1e293b;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td style="vertical-align: middle;">
              <span style="font-size: 21px; font-weight: 800; letter-spacing: -0.03em; color: #ffffff;">
                Data<span style="color: #6366f1;">Forge</span>
              </span>
            </td>
            <td style="vertical-align: middle; text-align: right;">
              <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #10b981; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 8px; border-radius: 6px;">
                Team Workspace
              </span>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Main Content -->
    <tr>
      <td style="padding: 32px;">
        <h1 style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -0.02em; line-height: 1.3;">
          You've been added to a Team Workspace
        </h1>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
          <strong style="color: #f1f5f9;">{inviter_name_or_email}</strong> has added you to the <strong style="color: #f1f5f9;">{org_name}</strong> workspace on DataForge with <strong style="color: #818cf8;">{role}</strong> privileges.
        </p>

        <!-- Metadata Spec Box -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background: #162032; border: 1px solid #24324a; border-radius: 12px; margin-bottom: 28px;">
          <tr>
            <td style="padding: 14px 18px; border-bottom: 1px solid #1f2c42;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Workspace</td>
                  <td style="color: #f8fafc; font-size: 13px; font-weight: 700; text-align: right;">{org_name}</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding: 14px 18px; border-bottom: 1px solid #1f2c42;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Assigned Role</td>
                  <td style="text-align: right;">
                    <span style="display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.35);">{role}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding: 14px 18px;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Added by</td>
                  <td style="color: #cbd5e1; font-size: 13px; font-weight: 600; text-align: right;">{inviter_name_or_email}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <!-- Primary CTA Button -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0 20px 0;">
          <tr>
            <td align="center">
              <a href="{workspace_url}" target="_blank" style="display: inline-block; background: #6366f1; color: #ffffff !important; font-size: 14px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35); letter-spacing: -0.01em;">
                Open Team Workspace &rarr;
              </a>
            </td>
          </tr>
        </table>

        <!-- Direct URL Fallback -->
        <p style="font-size: 12px; color: #64748b; line-height: 1.6; margin: 20px 0 0 0; text-align: center;">
          Or copy and paste this link in your browser:<br>
          <a href="{workspace_url}" style="color: #818cf8; text-decoration: underline; word-break: break-all;">{workspace_url}</a>
        </p>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="padding: 20px 32px 28px 32px; border-top: 1px solid #1e293b; text-align: center;">
        <p style="font-size: 11px; color: #475569; line-height: 1.6; margin: 0;">
          This invitation was sent by DataForge Secure Analytics to <strong style="color: #64748b;">{recipient_email}</strong>.<br>
          Sign in to access your organization's datasets, shared analysis sessions, and trained models.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return cls._dispatch_via_resend(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            context_url=workspace_url,
        )

    @classmethod
    def send_password_reset_email(
        cls,
        recipient_email: str,
        reset_url: str,
    ) -> Dict[str, Any]:
        """
        Sends an official, branded password reset email via Resend.
        """
        settings = get_settings()
        subject = "Reset your DataForge password"

        text_body = (
            f"Hello,\n\n"
            f"We received a request to reset the password for your DataForge account ({recipient_email}).\n\n"
            f"To choose a new password, click the link below (valid for 1 hour):\n"
            f"{reset_url}\n\n"
            f"If you did not make this request, you can safely ignore this email. Your account remains secure.\n\n"
            f"— The DataForge Team\n"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password</title>
</head>
<body style="margin: 0; padding: 32px 16px; background-color: #090d16; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9; -webkit-font-smoothing: antialiased;">
  <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <!-- Brand Header -->
    <tr>
      <td style="padding: 28px 32px 20px 32px; border-bottom: 1px solid #1e293b;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td style="vertical-align: middle;">
              <span style="font-size: 21px; font-weight: 800; letter-spacing: -0.03em; color: #ffffff;">
                Data<span style="color: #6366f1;">Forge</span>
              </span>
            </td>
            <td style="vertical-align: middle; text-align: right;">
              <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #f59e0b; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 4px 8px; border-radius: 6px;">
                Security
              </span>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Main Content -->
    <tr>
      <td style="padding: 32px;">
        <h1 style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -0.02em; line-height: 1.3;">
          Reset your password
        </h1>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
          We received a request to reset the password for your DataForge account associated with <strong style="color: #f1f5f9;">{recipient_email}</strong>.
        </p>

        <!-- Security Note Box -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background: #162032; border: 1px solid #24324a; border-radius: 12px; margin-bottom: 28px;">
          <tr>
            <td style="padding: 14px 18px;">
              <p style="margin: 0; font-size: 13px; color: #94a3b8; line-height: 1.5;">
                ⏱️ <strong style="color: #f1f5f9;">This link will expire in 1 hour</strong> and can only be used once. If you did not request this change, please ignore this email.
              </p>
            </td>
          </tr>
        </table>

        <!-- Primary CTA Button -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0 20px 0;">
          <tr>
            <td align="center">
              <a href="{reset_url}" target="_blank" style="display: inline-block; background: #6366f1; color: #ffffff !important; font-size: 14px; font-weight: 700; text-decoration: none; padding: 14px 36px; border-radius: 10px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35); letter-spacing: -0.01em;">
                Reset My Password &rarr;
              </a>
            </td>
          </tr>
        </table>

        <!-- Direct URL Fallback -->
        <p style="font-size: 12px; color: #64748b; line-height: 1.6; margin: 20px 0 0 0; text-align: center;">
          Or copy and paste this link in your browser:<br>
          <a href="{reset_url}" style="color: #818cf8; text-decoration: underline; word-break: break-all;">{reset_url}</a>
        </p>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="padding: 20px 32px 28px 32px; border-top: 1px solid #1e293b; text-align: center;">
        <p style="font-size: 11px; color: #475569; line-height: 1.6; margin: 0;">
          DataForge Secure Analytics &bull; Sent to <strong style="color: #64748b;">{recipient_email}</strong>.<br>
          If you have questions, please contact our support team.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return cls._dispatch_via_resend(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            context_url=reset_url,
        )

    @classmethod
    def _dispatch_via_resend(
        cls,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str,
        context_url: str,
    ) -> Dict[str, Any]:
        """Helper to dispatch email via Resend HTTP API or simulate locally."""
        settings = get_settings()
        if settings.RESEND_API_KEY:
            try:
                sender = (
                    getattr(settings, "RESEND_FROM_EMAIL", None)
                    or getattr(settings, "MAIL_FROM", None)
                    or "notifications@numan-10.site"
                )
                from_field = sender if "<" in sender else f"DataForge <{sender}>"

                resend_payload = json.dumps({
                    "from": from_field,
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
                    log.info("[mailer/resend] Successfully sent email to %s (id=%s)", recipient_email, resp_data.get("id"))
                    return {
                        "sent": True,
                        "transport": "resend",
                        "recipient": recipient_email,
                        "email_id": resp_data.get("id"),
                        "access_url": context_url,
                    }
            except Exception as e:
                log.error("[mailer/resend] Failed to send email via Resend: %s", e)
                return {
                    "sent": False,
                    "transport": "resend",
                    "error": str(e),
                    "recipient": recipient_email,
                    "access_url": context_url,
                }

        # Simulated fallback for local dev when RESEND_API_KEY is omitted
        log.info(
            "[mailer/simulated] (No RESEND_API_KEY configured) Simulated email to %s with context link: %s",
            recipient_email, context_url
        )
        return {
            "sent": False,
            "transport": "simulated",
            "reason": "Missing RESEND_API_KEY in .env (configure RESEND_API_KEY to send real emails)",
            "recipient": recipient_email,
            "access_url": context_url,
        }
