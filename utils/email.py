"""
Email utilities for sending emails via ProtonMail SMTP.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, render_template_string


def send_email(to_email: str, subject: str, body_text: str, body_html: str = None):
    """
    Send an email via ProtonMail SMTP.
    
    Supports both:
    - Direct SMTP with app password/token (paid plans)
    - ProtonMail Bridge (free/paid plans)
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body (optional)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv('PROTON_SMTP_SERVER', 'smtp.protonmail.ch')
        smtp_port = int(os.getenv('PROTON_SMTP_PORT', '587'))
        smtp_username = os.getenv('PROTON_EMAIL')
        smtp_password = os.getenv('PROTON_PASSWORD')  # Can be app password or SMTP token
        from_email = os.getenv('PROTON_FROM_EMAIL', smtp_username)
        use_tls = os.getenv('PROTON_USE_TLS', 'true').lower() == 'true'
        
        if not smtp_username or not smtp_password:
            print("❌ ProtonMail credentials not configured in .env file")
            print("   Set PROTON_EMAIL and PROTON_PASSWORD in your .env file")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Attach text and HTML parts
        part1 = MIMEText(body_text, 'plain')
        msg.attach(part1)
        
        if body_html:
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.ehlo()  # Identify ourselves
            
            # Use TLS for ProtonMail direct SMTP (not needed for Bridge on localhost)
            if use_tls and smtp_server not in ['127.0.0.1', 'localhost']:
                server.starttls()
                server.ehlo()  # Re-identify after TLS
            
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email sent to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
        print("   Check your PROTON_EMAIL and PROTON_PASSWORD in .env")
        print("   For paid plans: Use your app password or SMTP token")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_password_reset_email(user_email: str, reset_url: str, username: str):
    """
    Send password reset email.
    
    Args:
        user_email: User's email address
        reset_url: Password reset URL with token
        username: User's username
    """
    subject = "Reset Your Password - Movie Recommender"
    
    # Plain text version
    body_text = f"""
Hello {username},

You recently requested to reset your password for your Movie Recommender account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email or contact support if you have concerns.

Best regards,
Movie Recommender Team
    """
    
    # HTML version
    body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #0d6efd;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background-color: #0d6efd;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🎬 Movie Recommender</h2>
        </div>
        <div class="content">
            <h3>Hello {username},</h3>
            <p>You recently requested to reset your password for your Movie Recommender account.</p>
            <p>Click the button below to reset your password:</p>
            <center>
                <a href="{reset_url}" class="button">Reset Password</a>
            </center>
            <p><small>Or copy this link: <a href="{reset_url}">{reset_url}</a></small></p>
            <p><strong>This link will expire in 1 hour.</strong></p>
            <div class="footer">
                <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
                <p>Best regards,<br>Movie Recommender Team</p>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    return send_email(user_email, subject, body_text.strip(), body_html)


def send_welcome_email(user_email: str, username: str):
    """
    Send welcome email to new users.
    
    Args:
        user_email: User's email address
        username: User's username
    """
    subject = "Welcome to Movie Recommender! 🎬"
    
    # Plain text version
    body_text = f"""
Hello {username},

Welcome to Movie Recommender!

We're excited to have you on board. Get started by:
- Browsing our collection of movies
- Rating movies you've watched
- Getting personalized recommendations

Happy watching!

Best regards,
Movie Recommender Team
    """
    
    # HTML version
    body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #0d6efd;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }}
        .feature {{
            margin: 15px 0;
            padding: 10px;
            background-color: white;
            border-left: 4px solid #0d6efd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🎬 Welcome to Movie Recommender!</h2>
        </div>
        <div class="content">
            <h3>Hello {username},</h3>
            <p>We're excited to have you on board!</p>
            <p><strong>Get started with:</strong></p>
            <div class="feature">📽️ Browse our collection of movies</div>
            <div class="feature">⭐ Rate movies you've watched</div>
            <div class="feature">🎯 Get personalized recommendations</div>
            <p style="margin-top: 30px;">Happy watching!</p>
            <p>Best regards,<br>Movie Recommender Team</p>
        </div>
    </div>
</body>
</html>
    """
    
    return send_email(user_email, subject, body_text.strip(), body_html)


def send_account_deleted_email(user_email: str, username: str):
    """
    Send account deletion confirmation email.
    
    Args:
        user_email: User's email address
        username: User's username
    """
    subject = "Your Account Has Been Deleted - Movie Recommender"
    
    # Plain text version
    body_text = f"""
Hello {username},

Your Movie Recommender account has been permanently deleted.

All your data including:
- Watch history
- Ratings
- Preferences

has been removed from our system.

If you deleted your account by mistake, you can create a new account at any time.

Thank you for using Movie Recommender.

Best regards,
Movie Recommender Team
    """
    
    # HTML version
    body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #dc3545;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Account Deleted</h2>
        </div>
        <div class="content">
            <h3>Hello {username},</h3>
            <p>Your Movie Recommender account has been permanently deleted.</p>
            <p><strong>All your data has been removed:</strong></p>
            <ul>
                <li>Watch history</li>
                <li>Ratings</li>
                <li>Preferences</li>
            </ul>
            <p>If you deleted your account by mistake, you can create a new account at any time.</p>
            <p>Thank you for using Movie Recommender.</p>
            <p>Best regards,<br>Movie Recommender Team</p>
        </div>
    </div>
</body>
</html>
    """
    
    return send_email(user_email, subject, body_text.strip(), body_html)
