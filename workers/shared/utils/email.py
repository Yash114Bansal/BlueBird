"""
Email utilities for workers.
Provides email sending functionality and templates using WorkersConfig.
"""

import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Import WorkersConfig
from ..config.celery_config import workers_config


class EmailService:
    """Service for sending email notifications."""
    
    def __init__(self):
        self.config = None
        self._load_config()
    
    def _load_config(self):
        """Load email configuration from WorkersConfig."""
        email_config = asyncio.run(workers_config.get_email_config())
        self.config = email_config
    
    def _get_smtp_connection(self) -> smtplib.SMTP:
        """Get SMTP connection."""
        if self.config["smtp_use_tls"]:
            server = smtplib.SMTP(self.config["smtp_host"], self.config["smtp_port"])
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(self.config["smtp_host"], self.config["smtp_port"])
        
        if self.config["smtp_username"] and self.config["smtp_password"]:
            server.login(self.config["smtp_username"], self.config["smtp_password"])
        
        return server
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send email notification.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            attachments: List of attachment dictionaries with 'filename' and 'content' keys
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if not self.config:
                raise ValueError("Email configuration not loaded")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.config['from_name']} <{self.config['from_email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename')
                    content = attachment.get('content')
                    if filename and content:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)
            
            # Send email
            with self._get_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False




# Global email service instance
email_service = EmailService()