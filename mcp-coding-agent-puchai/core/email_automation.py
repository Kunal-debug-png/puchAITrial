"""
Email automation system for invoice PDF generator

Handles email sending for invoice delivery, payment notifications, and reminders.
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional
import aiosmtplib
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)


class EmailTemplate:
    """Email template model."""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        subject: str,
        html_body: str,
        text_body: str = "",
        template_type: str = "invoice"
    ):
        self.template_id = template_id
        self.name = name
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body or self._html_to_text(html_body)
        self.template_type = template_type
        self.created_at = datetime.now().isoformat()
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (basic implementation)."""
        # Remove HTML tags and decode entities
        import re
        text = re.sub('<[^<]+?>', '', html)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        return text.strip()
    
    def render(self, variables: Dict[str, str]) -> Dict[str, str]:
        """Render template with variables."""
        subject = self.subject
        html_body = self.html_body
        text_body = self.text_body
        
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            subject = subject.replace(placeholder, str(var_value))
            html_body = html_body.replace(placeholder, str(var_value))
            text_body = text_body.replace(placeholder, str(var_value))
        
        return {
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body
        }


class EmailManager:
    """Manages email sending and automation."""
    
    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        from_email: str = "",
        from_name: str = "Invoice System"
    ):
        """Initialize email manager."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email or username
        self.from_name = from_name
        
        self.data_dir = Path("data")
        self.templates_file = self.data_dir / "email_templates.json"
        self.email_log_file = self.data_dir / "email_log.json"
        self._ensure_data_directory()
        
        self.templates: Dict[str, EmailTemplate] = {}
        self.email_log: List[Dict] = []
        self.load_data()
        self._create_default_templates()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_data(self):
        """Load templates and email log."""
        # Load templates
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    templates_data = json.load(f)
                self.templates = {
                    tid: EmailTemplate(**data)
                    for tid, data in templates_data.items()
                }
            except Exception as e:
                logger.error(f"Failed to load email templates: {e}")
                self.templates = {}
        
        # Load email log
        if self.email_log_file.exists():
            try:
                with open(self.email_log_file, 'r', encoding='utf-8') as f:
                    self.email_log = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load email log: {e}")
                self.email_log = []
    
    def save_data(self):
        """Save templates and email log."""
        try:
            # Save templates
            templates_data = {
                tid: {
                    "template_id": template.template_id,
                    "name": template.name,
                    "subject": template.subject,
                    "html_body": template.html_body,
                    "text_body": template.text_body,
                    "template_type": template.template_type,
                    "created_at": template.created_at
                }
                for tid, template in self.templates.items()
            }
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, indent=2, ensure_ascii=False)
            
            # Save email log (keep only last 1000 entries)
            with open(self.email_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.email_log[-1000:], f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save email data: {e}")
            raise
    
    def _create_default_templates(self):
        """Create default email templates if they don't exist."""
        default_templates = [
            {
                "template_id": "invoice_delivery",
                "name": "Invoice Delivery",
                "subject": "Invoice {{invoice_number}} from {{company_name}}",
                "html_body": """
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="background-color: #2c3e50; color: white; padding: 20px;">
                            <h1 style="margin: 0; font-size: 24px;">Invoice from {{company_name}}</h1>
                        </div>
                        <div style="padding: 30px;">
                            <p style="margin: 0 0 20px; font-size: 16px;">Dear {{customer_name}},</p>
                            
                            <p style="margin: 0 0 20px; color: #666;">Thank you for your business! Please find your invoice attached to this email.</p>
                            
                            <div style="background-color: #f8f9fa; border-radius: 6px; padding: 20px; margin: 20px 0;">
                                <h3 style="margin: 0 0 15px; color: #2c3e50;">Invoice Details</h3>
                                <p style="margin: 5px 0; color: #666;"><strong>Invoice Number:</strong> {{invoice_number}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Date:</strong> {{invoice_date}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Amount:</strong> {{currency}}{{total_amount}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Due Date:</strong> {{due_date}}</p>
                            </div>
                            
                            {{#payment_link}}
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{{payment_link}}" style="background-color: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Pay Now</a>
                            </div>
                            {{/payment_link}}
                            
                            <p style="margin: 20px 0 0; color: #666;">If you have any questions about this invoice, please don't hesitate to contact us.</p>
                            
                            <hr style="margin: 30px 0; border: none; height: 1px; background-color: #eee;">
                            
                            <p style="margin: 0; font-size: 14px; color: #999;">
                                Best regards,<br>
                                {{company_name}}<br>
                                <em>This is an automated message. Please do not reply to this email.</em>
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "template_type": "invoice"
            },
            {
                "template_id": "payment_confirmation",
                "name": "Payment Confirmation",
                "subject": "Payment Received - Invoice {{invoice_number}}",
                "html_body": """
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="background-color: #27ae60; color: white; padding: 20px;">
                            <h1 style="margin: 0; font-size: 24px;">✓ Payment Received</h1>
                        </div>
                        <div style="padding: 30px;">
                            <p style="margin: 0 0 20px; font-size: 16px;">Dear {{customer_name}},</p>
                            
                            <p style="margin: 0 0 20px; color: #666;">Thank you! We have successfully received your payment.</p>
                            
                            <div style="background-color: #f8f9fa; border-radius: 6px; padding: 20px; margin: 20px 0;">
                                <h3 style="margin: 0 0 15px; color: #2c3e50;">Payment Details</h3>
                                <p style="margin: 5px 0; color: #666;"><strong>Invoice Number:</strong> {{invoice_number}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Amount Paid:</strong> {{currency}}{{paid_amount}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Payment Method:</strong> {{payment_method}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Confirmation Code:</strong> {{confirmation_code}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Payment Date:</strong> {{payment_date}}</p>
                            </div>
                            
                            <p style="margin: 20px 0 0; color: #666;">Your invoice has been marked as paid. Thank you for your prompt payment!</p>
                            
                            <hr style="margin: 30px 0; border: none; height: 1px; background-color: #eee;">
                            
                            <p style="margin: 0; font-size: 14px; color: #999;">
                                Best regards,<br>
                                {{company_name}}
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "template_type": "payment"
            },
            {
                "template_id": "payment_reminder",
                "name": "Payment Reminder",
                "subject": "Payment Reminder - Invoice {{invoice_number}} is Due",
                "html_body": """
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="background-color: #f39c12; color: white; padding: 20px;">
                            <h1 style="margin: 0; font-size: 24px;">Payment Reminder</h1>
                        </div>
                        <div style="padding: 30px;">
                            <p style="margin: 0 0 20px; font-size: 16px;">Dear {{customer_name}},</p>
                            
                            <p style="margin: 0 0 20px; color: #666;">This is a friendly reminder that your invoice payment is due.</p>
                            
                            <div style="background-color: #fef9e7; border-left: 4px solid #f39c12; padding: 20px; margin: 20px 0;">
                                <h3 style="margin: 0 0 15px; color: #2c3e50;">Invoice Details</h3>
                                <p style="margin: 5px 0; color: #666;"><strong>Invoice Number:</strong> {{invoice_number}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Amount Due:</strong> {{currency}}{{total_amount}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Due Date:</strong> {{due_date}}</p>
                                <p style="margin: 5px 0; color: #666;"><strong>Days Overdue:</strong> {{days_overdue}}</p>
                            </div>
                            
                            {{#payment_link}}
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{{payment_link}}" style="background-color: #e74c3c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Pay Now</a>
                            </div>
                            {{/payment_link}}
                            
                            <p style="margin: 20px 0 0; color: #666;">Please process this payment as soon as possible to avoid any late fees. If you have already paid, please disregard this reminder.</p>
                            
                            <hr style="margin: 30px 0; border: none; height: 1px; background-color: #eee;">
                            
                            <p style="margin: 0; font-size: 14px; color: #999;">
                                Best regards,<br>
                                {{company_name}}
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "template_type": "reminder"
            }
        ]
        
        for template_data in default_templates:
            if template_data["template_id"] not in self.templates:
                template = EmailTemplate(**template_data)
                self.templates[template.template_id] = template
        
        self.save_data()
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address."""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    async def send_invoice_email(
        self,
        to_email: str,
        invoice_data: Dict,
        pdf_attachment: bytes = None,
        template_id: str = "invoice_delivery"
    ) -> Dict:
        """Send invoice email with PDF attachment."""
        if not self.validate_email_address(to_email):
            return {"success": False, "error": "Invalid email address"}
        
        template = self.templates.get(template_id)
        if not template:
            return {"success": False, "error": f"Template {template_id} not found"}
        
        try:
            # Prepare template variables
            variables = {
                "customer_name": invoice_data.get("buyer_name", "Valued Customer"),
                "company_name": invoice_data.get("company_name", "Your Company"),
                "invoice_number": invoice_data.get("invoice_number", "INV-001"),
                "invoice_date": invoice_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "total_amount": f"{invoice_data.get('total_amount', 0):.2f}",
                "currency": invoice_data.get("currency", "₹"),
                "due_date": invoice_data.get("due_date", ""),
                "payment_link": invoice_data.get("payment_link", "")
            }
            
            # Render template
            rendered = template.render(variables)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = rendered["subject"]
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(rendered["text_body"], 'plain', 'utf-8')
            html_part = MIMEText(rendered["html_body"], 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add PDF attachment if provided
            if pdf_attachment:
                pdf_part = MIMEApplication(pdf_attachment, _subtype="pdf")
                pdf_filename = f"{variables['invoice_number']}.pdf"
                pdf_part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=pdf_filename
                )
                msg.attach(pdf_part)
            
            # Send email
            result = await self._send_email_async(msg, to_email)
            
            # Log email
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "to_email": to_email,
                "template_id": template_id,
                "subject": rendered["subject"],
                "invoice_id": invoice_data.get("invoice_id", ""),
                "success": result["success"],
                "error": result.get("error", "")
            }
            self.email_log.append(log_entry)
            self.save_data()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_payment_confirmation(
        self,
        to_email: str,
        payment_data: Dict,
        template_id: str = "payment_confirmation"
    ) -> Dict:
        """Send payment confirmation email."""
        if not self.validate_email_address(to_email):
            return {"success": False, "error": "Invalid email address"}
        
        template = self.templates.get(template_id)
        if not template:
            return {"success": False, "error": f"Template {template_id} not found"}
        
        try:
            # Prepare template variables
            variables = {
                "customer_name": payment_data.get("customer_name", "Valued Customer"),
                "company_name": payment_data.get("company_name", "Your Company"),
                "invoice_number": payment_data.get("invoice_number", "INV-001"),
                "paid_amount": f"{payment_data.get('amount', 0):.2f}",
                "currency": payment_data.get("currency", "₹"),
                "payment_method": payment_data.get("payment_method", "Card"),
                "confirmation_code": payment_data.get("confirmation_code", "N/A"),
                "payment_date": payment_data.get("payment_date", datetime.now().strftime("%Y-%m-%d %H:%M"))
            }
            
            # Render and send
            rendered = template.render(variables)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = rendered["subject"]
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            text_part = MIMEText(rendered["text_body"], 'plain', 'utf-8')
            html_part = MIMEText(rendered["html_body"], 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            result = await self._send_email_async(msg, to_email)
            
            # Log email
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "to_email": to_email,
                "template_id": template_id,
                "subject": rendered["subject"],
                "payment_id": payment_data.get("transaction_id", ""),
                "success": result["success"],
                "error": result.get("error", "")
            }
            self.email_log.append(log_entry)
            self.save_data()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_email_async(self, msg: MIMEMultipart, to_email: str) -> Dict:
        """Send email using async SMTP."""
        if not self.username or not self.password:
            # Simulate email sending for demo
            logger.info(f"DEMO: Would send email to {to_email} with subject: {msg['Subject']}")
            return {
                "success": True,
                "message": f"Demo email sent to {to_email}",
                "demo_mode": True
            }
        
        try:
            # Use aiosmtplib for async email sending
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.username,
                password=self.password,
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return {"success": True, "message": f"Email sent to {to_email}"}
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_email_templates(self) -> List[Dict]:
        """Get all email templates."""
        return [
            {
                "template_id": template.template_id,
                "name": template.name,
                "subject": template.subject,
                "template_type": template.template_type,
                "created_at": template.created_at
            }
            for template in self.templates.values()
        ]
    
    def get_email_log(self, limit: int = 50, email_filter: str = "") -> List[Dict]:
        """Get recent email log entries."""
        log_entries = self.email_log[-limit:]
        
        if email_filter:
            log_entries = [
                entry for entry in log_entries
                if email_filter.lower() in entry.get("to_email", "").lower()
            ]
        
        return sorted(log_entries, key=lambda x: x["timestamp"], reverse=True)
    
    def get_email_stats(self, days: int = 30) -> Dict:
        """Get email sending statistics."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        total_sent = 0
        successful_sent = 0
        failed_sent = 0
        template_usage = {}
        
        for entry in self.email_log:
            entry_date = datetime.fromisoformat(entry["timestamp"])
            if entry_date < cutoff_date:
                continue
            
            total_sent += 1
            
            if entry["success"]:
                successful_sent += 1
            else:
                failed_sent += 1
            
            template_id = entry.get("template_id", "unknown")
            template_usage[template_id] = template_usage.get(template_id, 0) + 1
        
        success_rate = (successful_sent / total_sent * 100) if total_sent > 0 else 0
        
        return {
            "period_days": days,
            "total_sent": total_sent,
            "successful_sent": successful_sent,
            "failed_sent": failed_sent,
            "success_rate": round(success_rate, 2),
            "template_usage": template_usage
        }
