from fastapi import HTTPException
import smtplib
import os
import secrets
import time
import jwt
import hashlib

from email.mime.multipart import MIMEMultipart
from pydantic import EmailStr
from dotenv import load_dotenv
from email.mime.text import MIMEText

SECRET_KEY = "CHANGE_THIS_TO_A_STRONG_SECRET"  # use environment variable
ALGORITHM = "HS256"

load_dotenv()


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def generate_email_otp_token(
    email: str, type: str, expiry_seconds: int = 300
) -> tuple[str, str, str]:
    otp = str(secrets.randbelow(100000)).zfill(5)
    otp_hash = hash_otp(otp)
    iat = int(time.time())
    exp = iat + expiry_seconds

    payload = {
        "type": type,
        "user": email,
        "otp": otp_hash,
        "iat": iat,
        "exp": exp,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return otp, token


def decode_email_otp_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def send_otp_email_verification(recipient_email: EmailStr, otp: str):
    sender_email = os.getenv("SENDER_EMAIL")
    password = os.getenv("EMAIL_PASSWORD")
    subject = "OTP Verification"
    body = f"Your OTP for verification is: {otp}"
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, message.as_string())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send OTP email: {str(e)}",
            headers={"message": "OTP Send"},
        )
