"""
Email notifications for the CloudIA agent system.

All notification functions return bool: True if sent, False if SMTP not configured.
SMTP failures never crash the pipeline — logged as warnings only.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from backend.config import settings

log = structlog.get_logger()


def _send(subject: str, body_html: str, to: str | None = None) -> bool:
    """Core send function. Returns False if SMTP not configured."""
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        log.warning("smtp_not_configured", subject=subject)
        return False

    recipient = to or settings.smtp_user
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[CloudIA] {subject}"
        msg["From"] = settings.notification_from
        msg["To"] = recipient
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

        log.info("email_sent", subject=subject, recipient=recipient)
        return True

    except smtplib.SMTPException as e:
        log.warning("email_send_failed", subject=subject, error=str(e))
        return False
    except OSError as e:
        log.warning("email_smtp_connection_failed", host=settings.smtp_host, error=str(e))
        return False


def notify_content_ready(project_id: int, client_name: str, page_count: int) -> bool:
    """Notify operator that content is ready for review."""
    subject = f"Content ready for review — {client_name}"
    body = f"""
    <h2>Content ready for your review</h2>
    <p>The content agent has generated copy for <strong>{client_name}</strong> (Project #{project_id}).</p>
    <p><strong>{page_count} pages</strong> are ready for your review and approval.</p>
    <p><a href="http://localhost:5173/projects/{project_id}/content"
          style="background:#2563EB;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
       Review Content
    </a></p>
    <p style="color:#666;font-size:12px">Once you approve, the build pipeline will continue automatically.</p>
    """
    return _send(subject, body)


def notify_gate_pending(project_id: int, client_name: str, gate_name: str) -> bool:
    """Notify operator that a gate requires approval."""
    gate_label = gate_name.replace("_", " ").title()
    subject = f"Approval required — {client_name} — {gate_label}"
    body = f"""
    <h2>Action required: {gate_label}</h2>
    <p>Project <strong>{client_name}</strong> (#{project_id}) is waiting for your approval.</p>
    <p><a href="http://localhost:5173/projects/{project_id}"
          style="background:#2563EB;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
       Review & Approve
    </a></p>
    """
    return _send(subject, body)


def notify_task_failed(project_id: int, agent_name: str, error: str) -> bool:
    """Notify operator that an agent task failed."""
    subject = f"Agent failed — {agent_name} — Project #{project_id}"
    body = f"""
    <h2>Agent task failed</h2>
    <p>Agent <strong>{agent_name}</strong> failed on project #{project_id}.</p>
    <pre style="background:#f4f4f4;padding:12px;border-radius:4px;font-size:13px">{error[:500]}</pre>
    <p><a href="http://localhost:5173/projects/{project_id}"
          style="background:#DC2626;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
       View Project
    </a></p>
    """
    return _send(subject, body)


def notify_project_complete(project_id: int, client_name: str, site_url: str) -> bool:
    """Notify operator that a project is fully complete."""
    subject = f"Project complete — {client_name}"
    body = f"""
    <h2>Site is live!</h2>
    <p><strong>{client_name}</strong> (Project #{project_id}) has been approved and is complete.</p>
    <p><a href="{site_url}" style="background:#16A34A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
       View Live Site
    </a></p>
    """
    return _send(subject, body)
