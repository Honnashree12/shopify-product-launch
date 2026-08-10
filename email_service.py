import os
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

logger = logging.getLogger("email_service")

# Ensure emails output directory exists
EMAILS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "outputs", "emails"))
os.makedirs(EMAILS_DIR, exist_ok=True)

def generate_customer_email_html(customer_name: str, workshop_name: str, date: str, time: str, venue: str, order_id: str, amount: float, child_name: str, child_age: int, registration_id: str = "") -> str:
    """Generate the HTML template for the customer confirmation email."""
    ticket_id = registration_id if registration_id else order_id
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Confirmed</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #f7f9fa;
            color: #333333;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        .header p {{
            margin: 10px 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .welcome {{
            font-size: 16px;
            line-height: 1.6;
            color: #4a5568;
            margin-bottom: 20px;
        }}
        .details-box {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 25px;
        }}
        .details-box h3 {{
            margin-top: 0;
            margin-bottom: 15px;
            color: #1e3c72;
            font-size: 18px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
        }}
        .detail-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 14.5px;
        }}
        .detail-row:last-child {{
            margin-bottom: 0;
            font-weight: bold;
            color: #0f172a;
            border-top: 1px dashed #e2e8f0;
            padding-top: 10px;
            margin-top: 10px;
        }}
        .detail-label {{
            color: #64748b;
            font-weight: 500;
        }}
        .detail-value {{
            color: #334155;
            text-align: right;
        }}
        .instructions {{
            background-color: #fffbeb;
            border: 1px solid #fef3c7;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 25px;
        }}
        .instructions h4 {{
            margin-top: 0;
            margin-bottom: 10px;
            color: #b45309;
            font-size: 15px;
        }}
        .instructions ul {{
            margin: 0;
            padding-left: 20px;
            font-size: 13.5px;
            line-height: 1.5;
            color: #78350f;
        }}
        .footer {{
            background-color: #f8fafc;
            text-align: center;
            padding: 20px;
            font-size: 12px;
            color: #94a3b8;
            border-top: 1px solid #e2e8f0;
        }}
        .footer a {{
            color: #1e3c72;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MISSION TIRANGA 🚀</h1>
            <p>Your Space Mission is Confirmed!</p>
        </div>
        <div class="content">
            <p class="welcome">Dear {customer_name},</p>
            <p class="welcome">Thank you for registering for the upcoming workshop. Below are your registration and booking details. We are excited to guide your child through the magic of space communication!</p>
            
            <div class="details-box">
                <h3>Workshop Details</h3>
                <div class="detail-row">
                    <div class="detail-label">Workshop:</div>
                    <div class="detail-value">{workshop_name}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Participant:</div>
                    <div class="detail-value">{child_name} (Age: {child_age})</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Date:</div>
                    <div class="detail-value">{date}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Time:</div>
                    <div class="detail-value">{time}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Venue:</div>
                    <div class="detail-value">{venue}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Booking Ref:</div>
                    <div class="detail-value">Order #{order_id}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Paid:</div>
                    <div class="detail-value">₹{amount:.2f}</div>
                </div>
            </div>
            
            <div class="instructions">
                <h4>Important Information</h4>
                <ul>
                    <li>Please arrive 15 minutes before the scheduled start time (10:45 AM).</li>
                    <li>All satellite building model materials and STEM toolkits will be provided at the venue.</li>
                    <li>Children are recommended to bring a water bottle. Laptops are not required but kids may bring a notebook.</li>
                    <li>For any assistance, contact our support team at space-workshops@example.com.</li>
                </ul>
            </div>

            <div class="ticket-box" style="text-align: center; margin-top: 25px; border: 2px dashed #1e3c72; padding: 20px; border-radius: 8px; background-color: #f0f4f8;">
                <h3 style="margin: 0 0 10px; color: #1e3c72; font-size: 18px; font-family: sans-serif;">YOUR ENTRY TICKET</h3>
                <p style="font-size: 13px; margin: 0 0 15px; color: #64748b;">Show this QR code at the entrance check-in.</p>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={ticket_id}" alt="Ticket QR Code" style="border: 1px solid #e2e8f0; padding: 5px; border-radius: 4px; background: white;" />
                <p style="font-weight: bold; font-size: 15px; margin: 12px 0 0; color: #0f172a;">Ticket ID: {ticket_id}</p>
            </div>
            
            <p class="welcome" style="text-align: center; margin-top: 30px;">
                <strong>Get ready to build, launch, and explore! See you on August 15th! 🇮🇳</strong>
            </p>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} Shopify Workshop Launch Platform. All rights reserved.</p>
            <p>Need help? <a href="mailto:space-workshops@example.com">Contact Support</a></p>
        </div>
    </div>
</body>
</html>
"""

def generate_sales_email_html(reg_data: Dict[str, Any], workshop_data: Dict[str, Any]) -> str:
    """Generate the HTML template for the sales team notification email."""
    store_url = os.getenv("SHOPIFY_STORE_URL", "product-launch-agent.myshopify.com")
    admin_order_link = f"https://admin.shopify.com/store/{store_url.split('.')[0]}/orders/{reg_data.get('shopify_order_id', '')}"
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>New Workshop Registration</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #fafafa; padding: 20px; }}
        .card {{ max-width: 600px; margin: 0 auto; background: #fff; border: 1px solid #e1e1e1; border-radius: 5px; padding: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .header {{ border-bottom: 2px solid #3d2a98; padding-bottom: 15px; margin-bottom: 20px; }}
        .header h2 {{ margin: 0; color: #3d2a98; }}
        .meta-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .meta-table th, .meta-table td {{ border: 1px solid #e5e7eb; padding: 10px; text-align: left; font-size: 14px; }}
        .meta-table th {{ background-color: #f3f4f6; width: 150px; font-weight: bold; }}
        .admin-link {{ display: inline-block; background-color: #10b981; color: #fff; padding: 10px 18px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h2>New Registration Recieved 🎟️</h2>
            <p>Order ID: #{reg_data.get('order_id')}</p>
        </div>
        
        <p>A new seat has been purchased for <strong>{workshop_data.get('name', 'Mission Tiranga')}</strong>!</p>
        
        <h3>Registration Details</h3>
        <table class="meta-table">
            <tr>
                <th>Child Name</th>
                <td>{reg_data.get('child_name')}</td>
            </tr>
            <tr>
                <th>Child Age</th>
                <td>{reg_data.get('child_age')} Years</td>
            </tr>
            <tr>
                <th>Parent Name</th>
                <td>{reg_data.get('parent_name')}</td>
            </tr>
            <tr>
                <th>Parent Email</th>
                <td>{reg_data.get('customer_email')}</td>
            </tr>
            <tr>
                <th>Parent Phone</th>
                <td>{reg_data.get('customer_phone') or 'N/A'}</td>
            </tr>
            <tr>
                <th>Amount Paid</th>
                <td>₹{reg_data.get('amount'):.2f}</td>
            </tr>
            <tr>
                <th>Payment Status</th>
                <td>{reg_data.get('payment_status', 'paid')}</td>
            </tr>
            <tr>
                <th>Shopify Order</th>
                <td>{reg_data.get('shopify_order_number') or 'N/A'}</td>
            </tr>
        </table>
        
        <p style="margin-top:20px;">
            <a href="{admin_order_link}" target="_blank" class="admin-link">View Order in Shopify Admin</a>
        </p>
    </div>
</body>
</html>
"""

def send_email(to_email: str, subject: str, html_content: str, filename_prefix: str, order_id: str) -> bool:
    """
    Sends an HTML email.
    If SMTP credentials are provided, it sends it via SMTP.
    Otherwise, it logs it to a file under outputs/emails/ for local development verification.
    """
    # 1. Always save to local file for auditing/testing
    log_filename = f"{filename_prefix}_{order_id}.html"
    log_path = os.path.join(EMAILS_DIR, log_filename)
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("Saved email to local folder: %s", log_path)
    except Exception as e:
        logger.error("Failed to save email copy locally: %s", e)

    # 2. Check if SMTP credentials are set
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", "space-workshops@example.com")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        logger.warning(
            "SMTP credentials not fully set in .env. Email was successfully saved to: %s",
            log_path
        )
        return True

    try:
        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email
        
        part = MIMEText(html_content, "html")
        msg.attach(part)
        
        # Connect and send
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, to_email, msg.as_string())
            
        logger.info("Successfully sent email to %s", to_email)
        return True
    except Exception as e:
        logger.exception("SMTP email delivery failed to %s", to_email)
        return False
