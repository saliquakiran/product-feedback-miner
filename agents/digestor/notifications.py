"""
Notification system for the Digestor Agent.

This module provides functionality for sending notifications
via email, Slack, webhooks, and other channels.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import aiohttp
from dataclasses import asdict

from agents.digestor.report_models import (
    NotificationChannel, PriorityLevel, NotificationConfig,
    NotificationTemplates
)

logger = logging.getLogger(__name__)

class NotificationSender:
    """Base class for notification senders."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize notification sender."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def send(self, message: str, recipients: List[str], priority: PriorityLevel = PriorityLevel.MEDIUM) -> bool:
        """
        Send notification.
        
        Args:
            message: Message content
            recipients: List of recipient addresses
            priority: Message priority
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError

class EmailNotificationSender(NotificationSender):
    """Email notification sender."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize email sender."""
        super().__init__(config)
        self.smtp_server = config.get('smtp_server', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.from_email = config.get('from_email', 'noreply@example.com')
        self.use_tls = config.get('use_tls', True)
    
    async def send(self, message: str, recipients: List[str], priority: PriorityLevel = PriorityLevel.MEDIUM) -> bool:
        """Send email notification."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[{priority.value.upper()}] Product Feedback Alert"
            
            # Add body
            msg.attach(MIMEText(message, 'html' if '<html>' in message else 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                text = msg.as_string()
                server.sendmail(self.from_email, recipients, text)
            
            self.logger.info(f"Email sent to {len(recipients)} recipients")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

class SlackNotificationSender(NotificationSender):
    """Slack notification sender."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Slack sender."""
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.channel = config.get('channel', '#general')
        self.username = config.get('username', 'Feedback Bot')
        self.icon_emoji = config.get('icon_emoji', ':robot_face:')
    
    async def send(self, message: str, recipients: List[str], priority: PriorityLevel = PriorityLevel.MEDIUM) -> bool:
        """Send Slack notification."""
        try:
            # Format message for Slack
            slack_message = self._format_slack_message(message, priority)
            
            # Send to webhook
            async with aiohttp.ClientSession() as session:
                payload = {
                    'text': slack_message,
                    'channel': self.channel,
                    'username': self.username,
                    'icon_emoji': self.icon_emoji
                }
                
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack message sent to {self.channel}")
                        return True
                    else:
                        self.logger.error(f"Slack API error: {response.status}")
                        return False
        
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False
    
    def _format_slack_message(self, message: str, priority: PriorityLevel) -> str:
        """Format message for Slack."""
        # Add priority emoji
        priority_emojis = {
            PriorityLevel.LOW: '🟢',
            PriorityLevel.MEDIUM: '🟡',
            PriorityLevel.HIGH: '🟠',
            PriorityLevel.CRITICAL: '🚨'
        }
        
        emoji = priority_emojis.get(priority, '📢')
        return f"{emoji} {message}"

class WebhookNotificationSender(NotificationSender):
    """Webhook notification sender."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize webhook sender."""
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.headers = config.get('headers', {'Content-Type': 'application/json'})
    
    async def send(self, message: str, recipients: List[str], priority: PriorityLevel = PriorityLevel.MEDIUM) -> bool:
        """Send webhook notification."""
        try:
            payload = {
                'message': message,
                'recipients': recipients,
                'priority': priority.value,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, 
                    json=payload, 
                    headers=self.headers
                ) as response:
                    if response.status in [200, 201, 202]:
                        self.logger.info(f"Webhook notification sent")
                        return True
                    else:
                        self.logger.error(f"Webhook error: {response.status}")
                        return False
        
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return False

class ConsoleNotificationSender(NotificationSender):
    """Console notification sender (for testing)."""
    
    async def send(self, message: str, recipients: List[str], priority: PriorityLevel = PriorityLevel.MEDIUM) -> bool:
        """Send console notification."""
        try:
            print(f"\n{'='*60}")
            print(f"NOTIFICATION [{priority.value.upper()}]")
            print(f"Recipients: {', '.join(recipients)}")
            print(f"Time: {datetime.utcnow()}")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}\n")
            
            self.logger.info(f"Console notification sent")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send console notification: {e}")
            return False

class NotificationManager:
    """Manages multiple notification channels."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize notification manager."""
        self.config = config
        self.senders = {}
        self.rate_limits = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize senders
        self._initialize_senders()
    
    def _initialize_senders(self):
        """Initialize notification senders based on config."""
        # Email sender
        if 'email' in self.config:
            self.senders[NotificationChannel.EMAIL] = EmailNotificationSender(
                self.config['email']
            )
        
        # Slack sender
        if 'slack' in self.config:
            self.senders[NotificationChannel.SLACK] = SlackNotificationSender(
                self.config['slack']
            )
        
        # Webhook sender
        if 'webhook' in self.config:
            self.senders[NotificationChannel.WEBHOOK] = WebhookNotificationSender(
                self.config['webhook']
            )
        
        # Console sender (always available for testing)
        self.senders[NotificationChannel.CONSOLE] = ConsoleNotificationSender({})
    
    async def send_notification(
        self,
        message: str,
        channels: List[NotificationChannel],
        recipients: List[str],
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        template: Optional[str] = None
    ) -> Dict[NotificationChannel, bool]:
        """
        Send notification to multiple channels.
        
        Args:
            message: Message content
            channels: List of channels to send to
            recipients: List of recipient addresses
            priority: Message priority
            template: Optional template to use
            
        Returns:
            Dictionary of channel -> success status
        """
        results = {}
        
        # Apply template if provided
        if template:
            message = self._apply_template(template, message, priority)
        
        # Check rate limits
        if not self._check_rate_limits(channels, priority):
            self.logger.warning("Rate limit exceeded, skipping notification")
            return {channel: False for channel in channels}
        
        # Send to each channel
        for channel in channels:
            if channel in self.senders:
                try:
                    success = await self.senders[channel].send(message, recipients, priority)
                    results[channel] = success
                    
                    if success:
                        self._update_rate_limit(channel)
                    
                except Exception as e:
                    self.logger.error(f"Error sending to {channel}: {e}")
                    results[channel] = False
            else:
                self.logger.warning(f"No sender configured for {channel}")
                results[channel] = False
        
        return results
    
    async def send_critical_alert(
        self,
        title: str,
        description: str,
        component: str,
        impact: str,
        actions_taken: List[str],
        next_steps: List[str]
    ) -> Dict[NotificationChannel, bool]:
        """Send critical alert notification."""
        template = NotificationTemplates.get_critical_alert_template()
        
        message = template.format(
            title=title,
            priority=PriorityLevel.CRITICAL.value,
            component=component,
            impact=impact,
            description=description,
            actions_taken='\n'.join(f"• {action}" for action in actions_taken),
            next_steps='\n'.join(f"• {step}" for step in next_steps),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        # Send to all available channels for critical alerts
        channels = list(self.senders.keys())
        recipients = self._get_critical_alert_recipients()
        
        return await self.send_notification(
            message, channels, recipients, PriorityLevel.CRITICAL
        )
    
    async def send_trend_alert(
        self,
        trend_type: str,
        current_value: float,
        previous_value: float,
        change_percentage: float,
        description: str,
        recommendation: str
    ) -> Dict[NotificationChannel, bool]:
        """Send trend alert notification."""
        template = NotificationTemplates.get_trend_alert_template()
        
        message = template.format(
            trend_type=trend_type,
            current_value=current_value,
            previous_value=previous_value,
            change_percentage=change_percentage,
            description=description,
            recommendation=recommendation,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        # Determine priority based on change magnitude
        if abs(change_percentage) >= 50:
            priority = PriorityLevel.HIGH
        elif abs(change_percentage) >= 20:
            priority = PriorityLevel.MEDIUM
        else:
            priority = PriorityLevel.LOW
        
        channels = [NotificationChannel.SLACK, NotificationChannel.EMAIL]
        recipients = self._get_trend_alert_recipients()
        
        return await self.send_notification(
            message, channels, recipients, priority
        )
    
    async def send_daily_summary(
        self,
        date: str,
        total_feedback: int,
        high_priority: int,
        tickets_created: int,
        resolved: int,
        top_issues: List[str],
        critical_alerts: List[str]
    ) -> Dict[NotificationChannel, bool]:
        """Send daily summary notification."""
        template = NotificationTemplates.get_daily_summary_template()
        
        message = template.format(
            date=date,
            total_feedback=total_feedback,
            high_priority=high_priority,
            tickets_created=tickets_created,
            resolved=resolved,
            top_issues='\n'.join(f"• {issue}" for issue in top_issues),
            critical_alerts='\n'.join(f"• {alert}" for alert in critical_alerts),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        channels = [NotificationChannel.EMAIL, NotificationChannel.SLACK]
        recipients = self._get_daily_summary_recipients()
        
        return await self.send_notification(
            message, channels, recipients, PriorityLevel.MEDIUM
        )
    
    def _apply_template(self, template: str, message: str, priority: PriorityLevel) -> str:
        """Apply template to message."""
        # This could be enhanced with more sophisticated templating
        return template.format(
            message=message,
            priority=priority.value,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
    
    def _check_rate_limits(self, channels: List[NotificationChannel], priority: PriorityLevel) -> bool:
        """Check if rate limits allow sending."""
        now = datetime.utcnow()
        
        for channel in channels:
            if channel not in self.rate_limits:
                self.rate_limits[channel] = {'count': 0, 'reset_time': now}
            
            # Reset counter if needed
            if now >= self.rate_limits[channel]['reset_time']:
                self.rate_limits[channel] = {'count': 0, 'reset_time': now + timedelta(hours=1)}
            
            # Check rate limit
            max_per_hour = self.config.get('rate_limits', {}).get(channel.value, 10)
            if self.rate_limits[channel]['count'] >= max_per_hour:
                return False
        
        return True
    
    def _update_rate_limit(self, channel: NotificationChannel):
        """Update rate limit counter."""
        if channel in self.rate_limits:
            self.rate_limits[channel]['count'] += 1
    
    def _get_critical_alert_recipients(self) -> List[str]:
        """Get recipients for critical alerts."""
        return self.config.get('critical_alert_recipients', ['admin@example.com'])
    
    def _get_trend_alert_recipients(self) -> List[str]:
        """Get recipients for trend alerts."""
        return self.config.get('trend_alert_recipients', ['analytics@example.com'])
    
    def _get_daily_summary_recipients(self) -> List[str]:
        """Get recipients for daily summaries."""
        return self.config.get('daily_summary_recipients', ['team@example.com'])
    
    async def test_connections(self) -> Dict[NotificationChannel, bool]:
        """Test connections to all configured channels."""
        results = {}
        
        for channel, sender in self.senders.items():
            try:
                # Send test message
                test_message = f"Test notification from Product Feedback Miner - {datetime.utcnow()}"
                success = await sender.send(
                    test_message, 
                    ['test@example.com'], 
                    PriorityLevel.LOW
                )
                results[channel] = success
            except Exception as e:
                self.logger.error(f"Test failed for {channel}: {e}")
                results[channel] = False
        
        return results

