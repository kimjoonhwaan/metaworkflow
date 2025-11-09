"""Email MCP Server - Sends emails via SMTP"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from src.utils import settings, get_logger

logger = get_logger("email_mcp")


class EmailMCPServer:
    """MCP Server for sending emails via SMTP"""
    
    def __init__(self):
        """Initialize email MCP server with SMTP configuration"""
        self.smtp_host = getattr(settings, 'smtp_host', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.from_email = getattr(settings, 'from_email', self.smtp_user)
        
        logger.info(f"EmailMCPServer initialized with SMTP: {self.smtp_host}:{self.smtp_port}")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Send email via SMTP
        
        Args:
            to: Recipient email address (or comma-separated for multiple)
            subject: Email subject
            body: Email body content
            cc: CC recipient (optional)
            bcc: BCC recipient (optional)
            html: Whether body is HTML (default: False)
        
        Returns:
            Dict with status and message
        """
        try:
            logger.info(f"Sending email to: {to}, subject: {subject}")
            
            # Validate SMTP configuration
            if not self.smtp_user or not self.smtp_password:
                logger.error("SMTP credentials not configured")
                return {
                    "status": "error",
                    "error": "SMTP credentials not configured in settings"
                }
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to
            
            if cc:
                msg['Cc'] = cc
            
            # Add body (HTML or plain text)
            if html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Prepare recipient list
            recipients = [to]
            if cc:
                recipients.extend([email.strip() for email in cc.split(',')])
            if bcc:
                recipients.extend([email.strip() for email in bcc.split(',')])
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to {to}")
            
            return {
                "status": "success",
                "message": f"Email sent to {to}",
                "recipients": recipients
            }
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {
                "status": "error",
                "error": f"SMTP authentication failed: {str(e)}"
            }
        
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                "status": "error",
                "error": f"SMTP error: {str(e)}"
            }
        
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Error sending email: {str(e)}"
            }
    
    async def send_email_with_template(
        self,
        to: str,
        subject: str,
        template_name: str,
        template_vars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send email using a template
        
        Args:
            to: Recipient email address
            subject: Email subject
            template_name: Name of the template (future enhancement)
            template_vars: Variables to substitute in template
        
        Returns:
            Dict with status and message
        """
        logger.warning("Email templates not yet implemented, using plain text")
        
        # For now, just format template_vars as plain text
        body = "\n".join([f"{k}: {v}" for k, v in template_vars.items()])
        
        return await self.send_email(to=to, subject=subject, body=body)


# Global instance
email_mcp = EmailMCPServer()

