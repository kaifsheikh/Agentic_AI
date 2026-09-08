import json
import os
import imaplib
import email
from email.header import decode_header
from langchain_core.tools import tool

@tool
def search_emails(query: str, folder: str = "INBOX", limit: int = 5) -> str:
    """
    Search emails in the specified folder based on a query (sender name, subject, or keyword).
    Returns matching emails (sender, subject, date, snippet).
    """
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")

    if not email_addr or not password:
        return json.dumps({"status": "error", "error": "Email credentials not set in .env"})

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, password)
        mail.select(folder)

        # Search criteria: FROM, SUBJECT, TEXT mein query dhoondo
        search_criteria = f'(OR (FROM "{query}") (SUBJECT "{query}") (TEXT "{query}"))'
        status, messages = mail.search(None, search_criteria)

        if status != "OK" or not messages[0]:
            return json.dumps({"status": "success", "output": f"'{query}' se koi email nahi mili."})

        email_ids = messages[0].split()[-limit:]
        result = []
        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            sender = msg.get("From")
            date = msg.get("Date")

            body_snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_snippet = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:200]
                        break
            else:
                body_snippet = msg.get_payload(decode=True).decode('utf-8', errors='ignore')[:200]

            result.append(f"From: {sender}\nSubject: {subject}\nDate: {date}\nSnippet: {body_snippet}\n---")

        mail.logout()
        return json.dumps({"status": "success", "output": "\n".join(result)})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})