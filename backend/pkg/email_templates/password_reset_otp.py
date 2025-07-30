def get_email_template(otp):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MIPAL - Password Reset</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background-color: #ffffff;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
        }}
        .header {{
            text-align: center;
            padding: 20px 0;
            background-color: #000000;
        }}
        .header h1 {{
            color: #ffffff;
            margin: 0;
            font-size: 24px;
            letter-spacing: 2px;
        }}
        .content {{
            padding: 30px;
            text-align: center;
        }}
        .otp-box {{
            background-color: #f5f5f5;
            border: 2px solid #000000;
            border-radius: 4px;
            padding: 20px;
            margin: 20px 0;
            font-size: 32px;
            letter-spacing: 5px;
            font-weight: bold;
            color: #000000;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666666;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                width: 100%;
                border: none;
            }}
            .content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MIPAL</h1>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>Hello,</p>
            <p>We received a request to reset your password. Please use the following OTP to complete the process:</p>
            <div class="otp-box">
                {otp}
            </div>
            <p>This OTP will expire in 10 minutes.</p>
            <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
        </div>
        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
            <p>&copy; 2025 MIPAL. All rights reserved.</p>
        </div>
    </div>
</body>
</html>"""


def get_email_subject(otp):
    return f"MIPAL Password Reset - Security Code: {otp}" 