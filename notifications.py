import smtplib
import logging
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from config import Config

class NotificationService:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_telegram_notification(self, message: str) -> bool:
        """Send a notification via Telegram"""
        if not self.config.TELEGRAM_BOT_TOKEN or not self.config.TELEGRAM_CHAT_ID:
            self.logger.warning("Telegram credentials not configured, skipping notification")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": self.config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                self.logger.info("Telegram notification sent successfully")
                return True
            else:
                self.logger.error(f"Failed to send Telegram notification: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def send_email_notification(self, subject: str, body: str, attachment_path: Optional[str] = None) -> bool:
        """Send an email notification"""
        if not self.config.SMTP_USERNAME or not self.config.SMTP_PASSWORD:
            self.logger.warning("Email credentials not configured, skipping notification")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.SMTP_USERNAME
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachment if provided
            if attachment_path:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment_path.split("/")[-1]}'
                )
                msg.attach(part)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
                for recipient in self.config.EMAIL_RECIPIENTS:
                    if recipient.strip():
                        msg['To'] = recipient.strip()
                        server.send_message(msg)
                        self.logger.info(f"Email sent to {recipient}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            return False
    
    def send_mention_alert(self, mention: Dict[str, Any]) -> bool:
        """Send an alert for a new mention"""
        message = (
            f"⚠️ <b>Clone Handle Alert</b>\n\n"
            f"Handle: @{mention['handle']}\n"
            f"Author: @{mention['author']}\n"
            f"Tweet: {mention['text']}\n"
            f"Time: {mention['timestamp']}\n"
            f"Link: {mention['url']}"
        )
        
        # Send via Telegram
        telegram_success = self.send_telegram_notification(message)
        
        # Send via email
        subject = f"Alert: New mention of @{mention['handle']}"
        body = (
            f"<h2>Clone Handle Alert</h2>"
            f"<p><b>Handle:</b> @{mention['handle']}<br>"
            f"<b>Author:</b> @{mention['author']}<br>"
            f"<b>Time:</b> {mention['timestamp']}<br>"
            f"<b>Link:</b> <a href='{mention['url']}'>View Tweet</a></p>"
            f"<h3>Tweet Content:</h3>"
            f"<p>{mention['text']}</p>"
        )
        email_success = self.send_email_notification(subject, body)
        
        return telegram_success or email_success
    
    def send_weekly_report(self, report_path: str) -> bool:
        """Send the weekly report via email and Telegram"""
        # Send via email with attachment
        subject = "Weekly Twitter Clone Monitor Report"
        body = (
            "<h2>Weekly Twitter Clone Monitor Report</h2>"
            "<p>Please find the attached report for mentions of fraudulent clone handles.</p>"
        )
        email_success = self.send_email_notification(subject, body, report_path)
        
        # Send via Telegram (without attachment)
        message = (
            "📊 <b>Weekly Twitter Clone Monitor Report</b>\n\n"
            "The weekly report has been generated and sent via email."
        )
        telegram_success = self.send_telegram_notification(message)
        
        return email_success or telegram_success