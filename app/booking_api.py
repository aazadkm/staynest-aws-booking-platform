"""
StayNest Booking API
Flask backend handling property bookings, storing them in RDS MySQL,
and sending notifications via SNS (owner) and SES (customer).

Environment variables required (see .env.example):
  DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
  ADMIN_PASSWORD
  SES_SENDER_EMAIL
  AWS_REGION
"""

import os
import uuid
from datetime import datetime

import boto3
import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---- Config (from environment, never hardcoded) ----
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "staynest")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

ses = boto3.client("ses", region_name=AWS_REGION)
sns = boto3.client("sns", region_name=AWS_REGION)


def get_db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


# ---------------------------------------------------------------------
# POST /api/bookings — create a new booking
# ---------------------------------------------------------------------
@app.route("/api/bookings", methods=["POST"])
def create_booking():
    d = request.get_json(force=True)

    required = ["name", "email", "property", "location", "checkin", "checkout", "guests", "total"]
    missing = [f for f in required if f not in d]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    booking_id = str(uuid.uuid4())

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO bookings
                (id, guest_name, email, property, location, checkin, checkout, guests, total, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                booking_id,
                d["name"],
                d["email"],
                d["property"],
                d["location"],
                d["checkin"],
                d["checkout"],
                d["guests"],
                d["total"],
                datetime.utcnow(),
            ),
        )
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Notify site owner via SNS
    try:
        sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
        if sns_topic_arn:
            sns.publish(
                TopicArn=sns_topic_arn,
                Subject="New StayNest Booking",
                Message=(
                    f"New booking confirmed!\n"
                    f"Booking ID: {booking_id}\n"
                    f"Guest: {d['name']}\n"
                    f"Email: {d['email']}\n"
                    f"Property: {d['property']}\n"
                    f"Location: {d['location']}\n"
                    f"Check-in: {d['checkin']}\n"
                    f"Check-out: {d['checkout']}\n"
                    f"Guests: {d['guests']}\n"
                    f"Total: {d['total']}"
                ),
            )
    except Exception as e:
        print("SNS error:", e)

    # Send confirmation email to customer via SES
    try:
        ses.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [d["email"]]},
            Message={
                "Subject": {"Data": "StayNest Booking Confirmed!"},
                "Body": {
                    "Text": {
                        "Data": (
                            f"Hi {d['name']}, your booking is confirmed!\n"
                            f"Booking ID: {booking_id}\n"
                            f"Property: {d['property']}\n"
                            f"Check-in: {d['checkin']}\n"
                            f"Check-out: {d['checkout']}\n"
                            f"Guests: {d['guests']}\n"
                            f"Total: {d['total']}\n"
                            f"Thank you for choosing StayNest!"
                        )
                    }
                },
            },
        )
    except Exception as e:
        print("SES error:", e)

    return jsonify({"booking_id": booking_id})


# ---------------------------------------------------------------------
# GET /api/admin/bookings — password-protected view of all bookings
# ---------------------------------------------------------------------
@app.route("/api/admin/bookings", methods=["GET"])
def admin_bookings():
    password = request.args.get("password")
    if not ADMIN_PASSWORD or password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        db.close()

        for row in rows:
            for key, value in row.items():
                if hasattr(value, "isoformat"):
                    row[key] = value.isoformat()

        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
