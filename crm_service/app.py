import json
import os
import smtplib
import time
from email.message import EmailMessage

from kafka import KafkaConsumer


def _topic() -> str:
    andrew_id = (os.environ.get("ANDREW_ID") or "").strip()
    return f"{andrew_id}.customer.evt" if andrew_id else "customer.evt"


def _consumer() -> KafkaConsumer:
    brokers = (os.environ.get("KAFKA_BROKERS") or "localhost:9092").strip()
    return KafkaConsumer(
        _topic(),
        bootstrap_servers=[b.strip() for b in brokers.split(",") if b.strip()],
        auto_offset_reset="earliest",
        group_id=(os.environ.get("CRM_CONSUMER_GROUP") or "crm-service"),
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        enable_auto_commit=True,
    )


def _send_email(customer: dict) -> None:
    to_addr = (customer.get("userId") or "").strip()
    if not to_addr:
        return
    customer_name = (customer.get("name") or "Customer").strip()
    andrew_id = (os.environ.get("ANDREW_ID") or "").strip()
    sender = (os.environ.get("SMTP_SENDER_EMAIL") or os.environ.get("SMTP_USERNAME") or "").strip()
    if not sender:
        return

    msg = EmailMessage()
    msg["Subject"] = "Activate your book store account"
    msg["From"] = sender
    msg["To"] = to_addr
    msg.set_content(
        f"Dear {customer_name},\n"
        f"Welcome to the Book store created by {andrew_id}.\n"
        "Exceptionally this time we won't ask you to click a link to activate your account.\n"
    )

    host = (os.environ.get("SMTP_HOST") or "").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = (os.environ.get("SMTP_USERNAME") or "").strip()
    password = (os.environ.get("SMTP_PASSWORD") or "").strip()
    use_tls = (os.environ.get("SMTP_STARTTLS", "true").strip().lower() in ("1", "true", "yes"))

    with smtplib.SMTP(host=host, port=port, timeout=20) as server:
        if use_tls:
            server.starttls()
        if username:
            server.login(username, password)
        server.send_message(msg)


def main() -> None:
    while True:
        try:
            consumer = _consumer()
            for message in consumer:
                payload = message.value if isinstance(message.value, dict) else {}
                try:
                    _send_email(payload)
                except Exception:
                    # Keep consuming even when one email fails.
                    pass
        except Exception:
            time.sleep(5)


if __name__ == "__main__":
    main()
