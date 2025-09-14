"""
Email notification tasks using Celery.
Handles all email notifications for the Evently platform.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from celery import Celery

# Import shared configuration
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.config.celery_config import create_celery_app

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = create_celery_app()




# Import utilities
from shared.utils.database import get_user_email
from shared.utils.email import email_service

# Celery tasks
@celery_app.task(bind=True, name='email_workers.tasks.send_booking_confirmation')
def send_booking_confirmation(self, user_id: int, booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send booking confirmation email.
    
    Args:
        user_id: User ID (email will be fetched)
        booking_data: Booking information
        
    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting booking confirmation email for user {user_id}")
        
        # Get user email address using direct database query
        user_email = get_user_email(user_id)
        if not user_email:
            error_msg = f"Could not find email for user {user_id}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'User email not found',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate email content
        event_name = booking_data.get('event_name', 'Event')
        booking_id = booking_data.get('booking_id', 'N/A')
        quantity = booking_data.get('quantity', 1)
        total_price = booking_data.get('total_price', 0)
        booking_date = booking_data.get('booking_date', datetime.now().strftime('%Y-%m-%d'))
        
        subject = f"Booking Confirmation - {event_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Booking Confirmed!</h2>
                
                <p>Hello,</p>
                
                <p>Your booking has been successfully confirmed. Here are the details:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">Booking Details</h3>
                    <p><strong>Event:</strong> {event_name}</p>
                    <p><strong>Booking ID:</strong> {booking_id}</p>
                    <p><strong>Quantity:</strong> {quantity} ticket(s)</p>
                    <p><strong>Total Price:</strong> ${total_price}</p>
                    <p><strong>Booking Date:</strong> {booking_date}</p>
                </div>
                
                <p>Thank you for using Evently! We look forward to seeing you at the event.</p>
                
                <p>Best regards,<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Booking Confirmed!
        
        Hello,
        
        Your booking has been successfully confirmed. Here are the details:
        
        Event: {event_name}
        Booking ID: {booking_id}
        Quantity: {quantity} ticket(s)
        Total Price: ${total_price}
        Booking Date: {booking_date}
        
        Thank you for using Evently! We look forward to seeing you at the event.
        
        Best regards,
        The Evently Team
        """
        
        # Send email using email service
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"Booking confirmation email sent successfully to {user_email}")
        else:
            logger.error(f"Failed to send booking confirmation email to {user_email}")
        
        result = {
            'success': success,
            'user_id': user_id,
            'email': user_email,
            'booking_id': booking_id,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Booking confirmation email task completed for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error sending booking confirmation email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying booking confirmation email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='email_workers.tasks.send_waitlist_notification')
def send_waitlist_notification(self, user_id: int, waitlist_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send waitlist notification email.
    
    Args:
        user_id: User ID (email will be fetched)
        waitlist_data: Waitlist information
        
    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting waitlist notification email for user {user_id}")
        
        # Get user email address
        user_email = get_user_email(user_id)
        if not user_email:
            logger.error(f"Could not find email for user {user_id}")
            return {
                'success': False,
                'error': 'User email not found',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate email content
        event_name = waitlist_data.get('event_name', 'Event')
        waitlist_position = waitlist_data.get('position', 1)
        expiry_minutes = waitlist_data.get('expiry_minutes', 30)
        
        subject = f"Waitlist Spot Available - {event_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Waitlist Spot Available!</h2>
                
                <p>Hello,</p>
                
                <p>Great news! A spot has become available for <strong>{event_name}</strong> and you're next in line!</p>
                
                <div style="background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3 style="color: #856404; margin-top: 0;">⚠️ Time Limited Offer</h3>
                    <p><strong>Position:</strong> #{waitlist_position}</p>
                    <p><strong>Expires in:</strong> {expiry_minutes} minutes</p>
                    <p><strong>Action Required:</strong> Complete your booking within the time limit to secure your spot.</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Complete Booking Now</a>
                </div>
                
                <p>If you don't complete your booking within {expiry_minutes} minutes, your spot will be offered to the next person on the waitlist.</p>
                
                <p>Best regards,<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Waitlist Spot Available!
        
        Hello,
        
        Great news! A spot has become available for {event_name} and you're next in line!
        
        Position: #{waitlist_position}
        Expires in: {expiry_minutes} minutes
        
        Action Required: Complete your booking within the time limit to secure your spot.
        
        If you don't complete your booking within {expiry_minutes} minutes, your spot will be offered to the next person on the waitlist.
        
        Best regards,
        The Evently Team
        """
        
        # Send email
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"Waitlist notification email sent successfully to {user_email}")
        else:
            logger.error(f"Failed to send waitlist notification email to {user_email}")
        
        return {
            'success': success,
            'user_id': user_id,
            'email': user_email,
            'waitlist_position': waitlist_position,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending waitlist notification email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying waitlist notification email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='email_workers.tasks.send_booking_cancellation')
def send_booking_cancellation(self, user_id: int, cancellation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send booking cancellation email.
    
    Args:
        user_id: User ID (email will be fetched)
        cancellation_data: Cancellation information
        
    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting booking cancellation email for user {user_id}")
        
        # Get user email address
        user_email = get_user_email(user_id)
        if not user_email:
            logger.error(f"Could not find email for user {user_id}")
            return {
                'success': False,
                'error': 'User email not found',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate email content
        event_name = cancellation_data.get('event_name', 'Event')
        booking_id = cancellation_data.get('booking_id', 'N/A')
        refund_amount = cancellation_data.get('refund_amount', 0)
        cancellation_reason = cancellation_data.get('reason', 'User request')
        
        subject = f"Booking Cancelled - {event_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc3545;">Booking Cancelled</h2>
                
                <p>Hello,</p>
                
                <p>Your booking has been cancelled as requested. Here are the details:</p>
                
                <div style="background-color: #f8d7da; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
                    <h3 style="color: #721c24; margin-top: 0;">Cancellation Details</h3>
                    <p><strong>Event:</strong> {event_name}</p>
                    <p><strong>Booking ID:</strong> {booking_id}</p>
                    <p><strong>Reason:</strong> {cancellation_reason}</p>
                    <p><strong>Refund Amount:</strong> ${refund_amount}</p>
                </div>
                
                <p>Your refund will be processed within 3-5 business days to your original payment method.</p>
                
                <p>We're sorry to see you go, but we hope you'll consider booking with us again in the future!</p>
                
                <p>Best regards,<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Booking Cancelled
        
        Hello,
        
        Your booking has been cancelled as requested. Here are the details:
        
        Event: {event_name}
        Booking ID: {booking_id}
        Reason: {cancellation_reason}
        Refund Amount: ${refund_amount}
        
        Your refund will be processed within 3-5 business days to your original payment method.
        
        We're sorry to see you go, but we hope you'll consider booking with us again in the future!
        
        Best regards,
        The Evently Team
        """
        
        # Send email
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"Booking cancellation email sent successfully to {user_email}")
        else:
            logger.error(f"Failed to send booking cancellation email to {user_email}")
        
        return {
            'success': success,
            'user_id': user_id,
            'email': user_email,
            'booking_id': booking_id,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending booking cancellation email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying booking cancellation email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='email_workers.tasks.send_waitlist_joined')
def send_waitlist_joined(self, user_id: int, waitlist_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send waitlist joined confirmation email.
    
    Args:
        user_id: User ID (email will be fetched)
        waitlist_data: Waitlist information
        
    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting waitlist joined email for user {user_id}")
        
        # Get user email address
        user_email = get_user_email(user_id)
        if not user_email:
            logger.error(f"Could not find email for user {user_id}")
            return {
                'success': False,
                'error': 'User email not found',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate email content
        event_name = waitlist_data.get('event_name', 'Event')
        position = waitlist_data.get('position', 1)
        joined_date = waitlist_data.get('joined_date', datetime.now().strftime('%Y-%m-%d'))
        
        subject = f"Added to Waitlist - {event_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3498db;">Added to Waitlist!</h2>
                
                <p>Hello,</p>
                
                <p>You have been successfully added to the waitlist for <strong>{event_name}</strong>.</p>
                
                <div style="background-color: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db;">
                    <h3 style="color: #2980b9; margin-top: 0;">Waitlist Details</h3>
                    <p><strong>Event:</strong> {event_name}</p>
                    <p><strong>Your Position:</strong> #{position}</p>
                    <p><strong>Date Added:</strong> {joined_date}</p>
                </div>
                
                <p>We'll notify you immediately when a spot becomes available. Keep an eye on your email for updates!</p>
                
                <p>Best regards,<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Added to Waitlist!
        
        Hello,
        
        You have been successfully added to the waitlist for {event_name}.
        
        Waitlist Details:
        Event: {event_name}
        Your Position: #{position}
        Date Added: {joined_date}
        
        We'll notify you immediately when a spot becomes available. Keep an eye on your email for updates!
        
        Best regards,
        The Evently Team
        """
        
        # Send email
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"Waitlist joined email sent successfully to {user_email}")
        else:
            logger.error(f"Failed to send waitlist joined email to {user_email}")
        
        return {
            'success': success,
            'user_id': user_id,
            'email': user_email,
            'position': position,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending waitlist joined email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying waitlist joined email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='email_workers.tasks.send_waitlist_cancellation')
def send_waitlist_cancellation(self, user_id: int, waitlist_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send waitlist cancellation email.
    
    Args:
        user_id: User ID (email will be fetched)
        waitlist_data: Waitlist information
        
    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting waitlist cancellation email for user {user_id}")
        
        # Get user email address
        user_email = get_user_email(user_id)
        if not user_email:
            logger.error(f"Could not find email for user {user_id}")
            return {
                'success': False,
                'error': 'User email not found',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate email content
        event_name = waitlist_data.get('event_name', 'Event')
        cancellation_date = waitlist_data.get('cancellation_date', datetime.now().strftime('%Y-%m-%d'))
        
        subject = f"Removed from Waitlist - {event_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Removed from Waitlist</h2>
                
                <p>Hello,</p>
                
                <p>You have been removed from the waitlist for <strong>{event_name}</strong>.</p>
                
                <div style="background-color: #fdf2f2; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #e74c3c;">
                    <h3 style="color: #c0392b; margin-top: 0;">Cancellation Details</h3>
                    <p><strong>Event:</strong> {event_name}</p>
                    <p><strong>Date Removed:</strong> {cancellation_date}</p>
                </div>
                
                <p>You can join the waitlist again at any time if spots become available.</p>
                
                <p>Thank you for using Evently!</p>
                
                <p>Best regards,<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Removed from Waitlist
        
        Hello,
        
        You have been removed from the waitlist for {event_name}.
        
        Cancellation Details:
        Event: {event_name}
        Date Removed: {cancellation_date}
        
        You can join the waitlist again at any time if spots become available.
        
        Thank you for using Evently!
        
        Best regards,
        The Evently Team
        """
        
        # Send email
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"Waitlist cancellation email sent successfully to {user_email}")
        else:
            logger.error(f"Failed to send waitlist cancellation email to {user_email}")
        
        return {
            'success': success,
            'user_id': user_id,
            'email': user_email,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending waitlist cancellation email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying waitlist cancellation email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }


# Health check task
@celery_app.task(name='email_workers.tasks.health_check')
def health_check() -> Dict[str, Any]:
    """
    Health check task for email workers.
    
    Returns:
        Health status dictionary
    """
    try:
        config_loaded = email_service.config is not None
        
        return {
            'status': 'healthy',
            'service': 'email_workers',
            'config_loaded': config_loaded,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'service': 'email_workers',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='email_workers.tasks.send_otp_verification_email')
def send_otp_verification_email(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send OTP verification email.
    
    Args:
        task_data: Task data containing email, OTP, and user info
        
    Returns:
        Task result dictionary
    """
    try:
        email = task_data.get('email')
        otp = task_data.get('otp')
        user_data = task_data.get('user_data', {})
        
        if not email or not otp:
            error_msg = "Email or OTP missing in task data"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Missing required data',
                'timestamp': datetime.now().isoformat()
            }
        
        logger.info(f"Starting OTP verification email for {email}")
        
        # Generate email content
        username = user_data.get('username', 'User')
        full_name = user_data.get('full_name', username)
        
        subject = "Verify Your Email - Evently"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Verify Your Email Address</h2>
                
                <p>Hello {full_name},</p>
                
                <p>Welcome to Evently! Please verify your email address to complete your registration.</p>
                
                <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px; margin: 30px 0; text-align: center; border: 2px solid #3498db;">
                    <h3 style="color: #2c3e50; margin-top: 0;">Your Verification Code</h3>
                    <div style="font-size: 36px; font-weight: bold; color: #3498db; letter-spacing: 8px; margin: 20px 0;">
                        {otp}
                    </div>
                    <p style="color: #666; margin: 0;">This code will expire in 10 minutes</p>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <p style="margin: 0; color: #856404;">
                        <strong>Security Notice:</strong> Never share this code with anyone. Evently will never ask for your verification code.
                    </p>
                </div>
                
                <p>If you didn't create an account with Evently, you can safely ignore this email.</p>
                
                <p>Best regards,<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Verify Your Email Address
        
        Hello {full_name},
        
        Welcome to Evently! Please verify your email address to complete your registration.
        
        Your Verification Code: {otp}
        
        This code will expire in 10 minutes.
        
        Security Notice: Never share this code with anyone. Evently will never ask for your verification code.
        
        If you didn't create an account with Evently, you can safely ignore this email.
        
        Best regards,
        The Evently Team
        """
        
        # Send email using email service
        success = email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"OTP verification email sent successfully to {email}")
        else:
            logger.error(f"Failed to send OTP verification email to {email}")
        
        result = {
            'success': success,
            'email': email,
            'otp_sent': success,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"OTP verification email task completed for {email}")
        return result
        
    except Exception as e:
        logger.error(f"Error sending OTP verification email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying OTP verification email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='email_workers.tasks.send_welcome_email')
def send_welcome_email(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send welcome email after successful registration.
    
    Args:
        task_data: Task data containing email and user info
        
    Returns:
        Task result dictionary
    """
    try:
        email = task_data.get('email')
        user_data = task_data.get('user_data', {})
        
        if not email:
            error_msg = "Email missing in task data"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Missing required data',
                'timestamp': datetime.now().isoformat()
            }
        
        logger.info(f"Starting welcome email for {email}")
        
        # Generate email content
        username = user_data.get('username', 'User')
        full_name = user_data.get('full_name', username)
        
        subject = "Welcome to Evently!"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #27ae60;">Welcome to Evently!</h2>
                
                <p>Hello {full_name},</p>
                
                <p>Thank you for joining Evently! Your account has been successfully created and verified.</p>
                
                <div style="background-color: #e8f8f5; padding: 30px; border-radius: 10px; margin: 30px 0; border-left: 4px solid #27ae60;">
                    <h3 style="color: #27ae60; margin-top: 0;">🎉 Account Verified!</h3>
                    <p>Your email address has been verified and your account is now active.</p>
                    <p><strong>Username:</strong> {username}</p>
                    <p><strong>Email:</strong> {email}</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">What's Next?</h3>
                    <ul style="color: #555;">
                        <li>Browse and discover amazing events</li>
                        <li>Book tickets for events you're interested in</li>
                        <li>Create your own events (coming soon)</li>
                        <li>Join our community and stay updated</li>
                    </ul>
                </div>
                
                <p>If you have any questions, feel free to reach out to our support team.</p>
                
                <p>Happy eventing!<br>The Evently Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Evently!
        
        Hello {full_name},
        
        Thank you for joining Evently! Your account has been successfully created and verified.
        
        Account Verified!
        Your email address has been verified and your account is now active.
        Username: {username}
        Email: {email}
        
        What's Next?
        - Browse and discover amazing events
        - Book tickets for events you're interested in
        - Create your own events (coming soon)
        - Join our community and stay updated
        
        If you have any questions, feel free to reach out to our support team.
        
        Happy eventing!
        The Evently Team
        """
        
        # Send email using email service
        success = email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Log email result
        if success:
            logger.info(f"Welcome email sent successfully to {email}")
        else:
            logger.error(f"Failed to send welcome email to {email}")
        
        result = {
            'success': success,
            'email': email,
            'welcome_sent': success,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Welcome email task completed for {email}")
        return result
        
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        
        # Retry logic
        max_retries = 3
        retry_delay = 60
        
        if self.request.retries < max_retries:
            logger.info(f"Retrying welcome email (attempt {self.request.retries + 1}/{max_retries})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


if __name__ == '__main__':
    celery_app.start()