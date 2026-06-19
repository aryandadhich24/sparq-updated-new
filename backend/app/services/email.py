"""Email notification service — SES for production, SMTP fallback, logging for dev."""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models

logger = logging.getLogger("sparqai.email")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@sparqai.com")
FROM_NAME = os.getenv("FROM_NAME", "SparqAI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

_ses_client = None


def _get_ses():
    global _ses_client
    if _ses_client is None:
        try:
            import boto3
            _ses_client = boto3.client("ses", region_name=AWS_REGION)
        except Exception:
            logger.warning("AWS SES not available — trying SMTP fallback")
            return None
    return _ses_client


def _send_via_smtp(to: str, subject: str, html_body: str) -> bool:
    """Send email via SMTP as fallback."""
    if not SMTP_HOST:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(subject, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        return False


def send_email(to: str, subject: str, html_body: str, user_id: int = None, email_type: str = "general", db: Session = None):
    """Send an email via SES, SMTP fallback, or log it."""
    sent = False
    ses = _get_ses()

    if ses:
        try:
            ses.send_email(
                Source=f"{FROM_NAME} <{FROM_EMAIL}>",
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            logger.info(f"Email sent via SES to {to}: {subject}")
            sent = True
        except Exception as e:
            logger.warning(f"SES failed for {to}: {e}, trying SMTP fallback")

    if not sent and SMTP_HOST:
        sent = _send_via_smtp(to, subject, html_body)
        if sent:
            logger.info(f"Email sent via SMTP to {to}: {subject}")

    if not sent:
        logger.info(f"[DEV EMAIL] To: {to} | Subject: {subject}")
        if db and user_id:
            db.add(models.EmailLog(
                user_id=user_id, email_type=email_type,
                subject=subject, status="dev_logged"
            ))
            db.commit()
            return

    if db and user_id:
        db.add(models.EmailLog(
            user_id=user_id, email_type=email_type,
            subject=subject, status="sent" if sent else "failed"
        ))
        db.commit()


def send_weekly_digest(db: Session, user: models.User):
    """Send weekly ROI digest to a user."""
    if not user.email_weekly_digest:
        return

    org_id = user.organization_id
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Get this week's decisions
    decisions = db.query(models.Decision).filter(
        models.Decision.organization_id == org_id,
        models.Decision.status == "ACTIVE"
    ).all()

    if not decisions:
        return

    # Get attributions
    decision_ids = [d.id for d in decisions]
    attrs = db.query(models.Attribution).filter(
        models.Attribution.decision_id.in_(decision_ids),
        models.Attribution.outcome_id == None
    ).all()
    attr_map = {a.decision_id: a for a in attrs}

    # Build top performers and action items
    top_performers = []
    action_items = []

    for d in decisions:
        attr = attr_map.get(d.id)
        if not attr:
            continue
        item = {
            "name": d.description,
            "roi": f"{attr.roi_multiple:.1f}x",
            "value": f"${attr.attributed_value:,.0f}",
            "action": attr.recommendation,
        }
        if attr.recommendation in ("KILL", "INVESTIGATE"):
            action_items.append(item)
        elif attr.roi_multiple > 1.0:
            top_performers.append(item)

    top_performers.sort(key=lambda x: float(x["roi"].rstrip("x")), reverse=True)

    # Totals
    total_invested = sum(a.total_cost for a in attrs)
    total_revenue = sum(a.attributed_value for a in attrs)

    # Build email HTML
    rows_html = ""
    for p in top_performers[:5]:
        rows_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{p['name']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#16a34a;font-weight:bold">{p['roi']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{p['value']}</td>
        </tr>"""

    alerts_html = ""
    for a in action_items[:5]:
        color = "#dc2626" if a["action"] == "KILL" else "#f59e0b"
        alerts_html += f"""
        <div style="padding:8px 12px;margin-bottom:8px;background:#fef2f2;border-radius:6px;border-left:3px solid {color}">
            <strong>{a['name']}</strong> — {a['action']} (ROI: {a['roi']})
        </div>"""

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#4f46e5;color:white;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="margin:0;font-size:20px">SparqAI Weekly ROI Digest</h1>
            <p style="margin:8px 0 0;opacity:0.8;font-size:14px">{datetime.utcnow().strftime('%B %d, %Y')}</p>
        </div>

        <div style="background:white;padding:24px;border:1px solid #e5e7eb">
            <div style="display:flex;gap:16px;margin-bottom:24px">
                <div style="flex:1;background:#f9fafb;padding:16px;border-radius:8px;text-align:center">
                    <div style="font-size:12px;color:#6b7280">Total Invested</div>
                    <div style="font-size:24px;font-weight:bold;color:#111827">${total_invested:,.0f}</div>
                </div>
                <div style="flex:1;background:#f0fdf4;padding:16px;border-radius:8px;text-align:center">
                    <div style="font-size:12px;color:#6b7280">Attributed Revenue</div>
                    <div style="font-size:24px;font-weight:bold;color:#16a34a">${total_revenue:,.0f}</div>
                </div>
            </div>

            {'<h3 style="margin:0 0 12px;font-size:16px;color:#111827">Action Required</h3>' + alerts_html if alerts_html else ''}

            <h3 style="margin:24px 0 12px;font-size:16px;color:#111827">Top Performers</h3>
            <table style="width:100%;border-collapse:collapse;font-size:14px">
                <thead>
                    <tr style="border-bottom:2px solid #e5e7eb">
                        <th style="padding:8px;text-align:left;color:#6b7280">Decision</th>
                        <th style="padding:8px;text-align:left;color:#6b7280">ROI</th>
                        <th style="padding:8px;text-align:left;color:#6b7280">Revenue</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>

            <div style="text-align:center;margin-top:24px">
                <a href="{FRONTEND_URL}" style="display:inline-block;background:#4f46e5;color:white;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:500">
                    View Dashboard
                </a>
            </div>
        </div>

        <div style="padding:16px;text-align:center;font-size:12px;color:#9ca3af">
            <p>You're receiving this because you have weekly digests enabled.</p>
            <a href="{FRONTEND_URL}/settings" style="color:#6366f1">Manage notification preferences</a>
        </div>
    </div>
    """

    send_email(
        to=user.email,
        subject=f"Your Weekly ROI Report — ${total_revenue:,.0f} attributed",
        html_body=html,
        user_id=user.id,
        email_type="weekly_digest",
        db=db,
    )


def send_action_alert(db: Session, user: models.User, decision: models.Decision, recommendation: str, roi: float):
    """Send alert when a decision needs urgent action."""
    if not user.email_action_alerts:
        return

    color = "#dc2626" if recommendation == "KILL" else "#f59e0b"
    action_text = "should be terminated" if recommendation == "KILL" else "needs investigation"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:{color};color:white;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="margin:0;font-size:20px">Action Required: {decision.description}</h1>
        </div>
        <div style="background:white;padding:24px;border:1px solid #e5e7eb">
            <p style="font-size:16px;color:#111827">
                <strong>{decision.description}</strong> {action_text}.
            </p>
            <div style="background:#f9fafb;padding:16px;border-radius:8px;margin:16px 0">
                <div><strong>Type:</strong> {decision.decision_type}</div>
                <div><strong>ROI:</strong> {roi:.2f}x</div>
                <div><strong>Recommendation:</strong> <span style="color:{color};font-weight:bold">{recommendation}</span></div>
            </div>
            <div style="text-align:center;margin-top:24px">
                <a href="{FRONTEND_URL}/decisions/{decision.id}" style="display:inline-block;background:#4f46e5;color:white;padding:10px 24px;border-radius:6px;text-decoration:none">
                    View Decision
                </a>
            </div>
        </div>
    </div>
    """

    send_email(
        to=user.email,
        subject=f"Action Required: {decision.description} — {recommendation}",
        html_body=html,
        user_id=user.id,
        email_type="action_alert",
        db=db,
    )


def send_sync_summary(db: Session, user: models.User, provider: str, created: int, skipped: int):
    """Send sync completion summary."""
    if not user.email_sync_summaries:
        return

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#4f46e5;color:white;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="margin:0;font-size:20px">{provider} Sync Complete</h1>
        </div>
        <div style="background:white;padding:24px;border:1px solid #e5e7eb">
            <div style="display:flex;gap:16px;margin-bottom:16px">
                <div style="flex:1;background:#f0fdf4;padding:16px;border-radius:8px;text-align:center">
                    <div style="font-size:12px;color:#6b7280">New Records</div>
                    <div style="font-size:28px;font-weight:bold;color:#16a34a">{created}</div>
                </div>
                <div style="flex:1;background:#f9fafb;padding:16px;border-radius:8px;text-align:center">
                    <div style="font-size:12px;color:#6b7280">Skipped (duplicates)</div>
                    <div style="font-size:28px;font-weight:bold;color:#6b7280">{skipped}</div>
                </div>
            </div>
            <p style="font-size:14px;color:#6b7280">Attribution has been recalculated automatically.</p>
            <div style="text-align:center;margin-top:16px">
                <a href="{FRONTEND_URL}" style="display:inline-block;background:#4f46e5;color:white;padding:10px 24px;border-radius:6px;text-decoration:none">
                    View Updated Dashboard
                </a>
            </div>
        </div>
    </div>
    """

    send_email(
        to=user.email,
        subject=f"{provider} Sync: {created} new records imported",
        html_body=html,
        user_id=user.id,
        email_type="sync_summary",
        db=db,
    )


def send_invitation(db: Session, from_user: models.User, to_email: str, invite_token: str, role: str):
    """Send a team invitation email."""
    org = db.query(models.Organization).filter(
        models.Organization.id == from_user.organization_id
    ).first()
    org_name = org.name if org else "your team"
    link = f"{FRONTEND_URL}/register?invite={invite_token}&email={to_email}"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#4f46e5;color:white;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="margin:0;font-size:20px">You're invited to join {org_name}</h1>
        </div>
        <div style="background:white;padding:24px;border:1px solid #e5e7eb">
            <p style="font-size:16px;color:#111827">
                <strong>{from_user.full_name or from_user.email}</strong> has invited you to join
                <strong>{org_name}</strong> on SparqAI as a <strong>{role}</strong>.
            </p>
            <p style="font-size:14px;color:#6b7280;">
                SparqAI helps teams measure the ROI of business decisions — from hires and tools to ad campaigns and vendors.
            </p>
            <div style="text-align:center;margin:32px 0">
                <a href="{link}" style="display:inline-block;background:#4f46e5;color:white;padding:12px 32px;border-radius:6px;text-decoration:none;font-weight:600">
                    Accept Invitation
                </a>
            </div>
            <p style="font-size:12px;color:#9ca3af;text-align:center">This invitation expires in 7 days.</p>
        </div>
    </div>
    """

    send_email(
        to=to_email,
        subject=f"Join {org_name} on SparqAI",
        html_body=html,
        user_id=from_user.id,
        email_type="invitation",
        db=db,
    )


def send_password_reset(db: Session, email: str, reset_token: str):
    """Send a branded password reset email with a tokenized link."""
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#4f46e5;color:white;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="margin:0;font-size:20px">Reset Your Password</h1>
        </div>
        <div style="background:white;padding:24px;border:1px solid #e5e7eb">
            <p style="font-size:16px;color:#111827">
                We received a request to reset your password. Click the button below to choose a new one.
            </p>
            <div style="text-align:center;margin:32px 0">
                <a href="{reset_link}" style="display:inline-block;background:#4f46e5;color:white;padding:12px 32px;border-radius:6px;text-decoration:none;font-weight:600">
                    Reset Password
                </a>
            </div>
            <p style="font-size:14px;color:#6b7280;">
                This link will expire in <strong>1 hour</strong>. If you did not request a password reset, you can safely ignore this email.
            </p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0" />
            <p style="font-size:12px;color:#9ca3af;">
                If the button above doesn't work, copy and paste this URL into your browser:<br/>
                <a href="{reset_link}" style="color:#6366f1;word-break:break-all">{reset_link}</a>
            </p>
        </div>
        <div style="padding:16px;text-align:center;font-size:12px;color:#9ca3af">
            <p>SparqAI &mdash; Business Decision Attribution</p>
        </div>
    </div>
    """

    # Look up the user to log the email; may be None if email doesn't exist
    user = db.query(models.User).filter(models.User.email == email).first()

    send_email(
        to=email,
        subject="Reset your SparqAI password",
        html_body=html,
        user_id=user.id if user else None,
        email_type="password_reset",
        db=db,
    )


def send_email_verification(db: Session, user: "models.User", verify_token: str):
    """Send a branded email verification email with a tokenized link."""
    verify_link = f"{FRONTEND_URL}/verify-email?token={verify_token}"
    display_name = user.full_name or user.email

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#4f46e5;color:white;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="margin:0;font-size:20px">Verify Your Email Address</h1>
        </div>
        <div style="background:white;padding:24px;border:1px solid #e5e7eb">
            <p style="font-size:16px;color:#111827">
                Hi {display_name}, welcome to SparqAI! Please verify your email address to get started.
            </p>
            <div style="text-align:center;margin:32px 0">
                <a href="{verify_link}" style="display:inline-block;background:#16a34a;color:white;padding:12px 32px;border-radius:6px;text-decoration:none;font-weight:600">
                    Verify Email
                </a>
            </div>
            <p style="font-size:14px;color:#6b7280;">
                This link will expire in <strong>24 hours</strong>. If you did not create an account, you can safely ignore this email.
            </p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0" />
            <p style="font-size:12px;color:#9ca3af;">
                If the button above doesn't work, copy and paste this URL into your browser:<br/>
                <a href="{verify_link}" style="color:#6366f1;word-break:break-all">{verify_link}</a>
            </p>
        </div>
        <div style="padding:16px;text-align:center;font-size:12px;color:#9ca3af">
            <p>SparqAI &mdash; Business Decision Attribution</p>
        </div>
    </div>
    """

    send_email(
        to=user.email,
        subject="Verify your SparqAI email address",
        html_body=html,
        user_id=user.id,
        email_type="email_verification",
        db=db,
    )


def run_weekly_digests(db: Session):
    """Run weekly digest for all users who have it enabled. Call from scheduler."""
    users = db.query(models.User).filter(
        models.User.is_active == True,
        models.User.email_weekly_digest == True,
    ).all()

    sent = 0
    for user in users:
        try:
            send_weekly_digest(db, user)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send digest to {user.email}: {e}")

    logger.info(f"Weekly digest sent to {sent}/{len(users)} users")
    return sent
