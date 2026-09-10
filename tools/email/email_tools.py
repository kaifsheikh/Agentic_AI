import os
import re
import json
import logging
import functools
from datetime import datetime
from typing import Optional, List, Dict, Any
import imaplib
import email
from email.header import decode_header, Header
from email.utils import parsedate_to_datetime
from langchain_core.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Helper Functions
# ============================================================

def _decode_mime_header(header_value: Optional[str]) -> str:
    """Decode MIME-encoded header to readable UTF-8 string."""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            # Decode with fallback encodings
            encodings = [encoding, 'utf-8', 'latin-1', 'cp1252']
            decoded = None
            for enc in encodings:
                if not enc:
                    continue
                try:
                    decoded = part.decode(enc)
                    break
                except (LookupError, UnicodeDecodeError):
                    continue
            if decoded is None:
                decoded = part.decode('utf-8', errors='replace')
            result.append(decoded)
        else:
            result.append(part)
    return ''.join(result)

def _get_email_body(msg: email.message.Message) -> str:
    """Extract plain text body from email, handling multipart and nested parts."""
    body_parts = []

    if msg.is_multipart():
        # Walk through all parts
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Skip attachments
            if "attachment" in content_disposition:
                continue
                
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_parts.append(payload.decode(charset, errors='replace'))
                except Exception as e:
                    logger.warning(f"Could not decode text/plain part: {e}")
            elif content_type == "text/html" and not body_parts:
                # Fallback to HTML if no plain text found yet
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html = payload.decode(charset, errors='replace')
                        # Simple tag stripping (better than nothing)
                        text = re.sub(r'<[^>]+>', ' ', html)
                        body_parts.append(text)
                except Exception as e:
                    logger.warning(f"Could not decode text/html part: {e}")
    else:
        # Single part email
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                if content_type == "text/html":
                    html = payload.decode(charset, errors='replace')
                    text = re.sub(r'<[^>]+>', ' ', html)
                    body_parts.append(text)
                else:
                    body_parts.append(payload.decode(charset, errors='replace'))
        except Exception as e:
            logger.warning(f"Could not decode body: {e}")
    
    return '\n\n'.join(part.strip() for part in body_parts if part.strip())


def _build_search_criteria(query: str, folder: str, 
                           search_type: str = "ALL",
                           date_since: Optional[str] = None,
                           date_before: Optional[str] = None) -> str:
    """
    Build IMAP search criteria string.
    search_type: ALL, FROM, SUBJECT, BODY, TEXT, UNSEEN, etc.
    """
    # Sanitize query to prevent IMAP injection
    # Remove quotes and backslashes that could break the query
    clean_query = re.sub(r'["\\]', ' ', query).strip()
    
    if search_type.upper() == "ALL":
        # Search in FROM, SUBJECT, and BODY
        criteria = f'(OR (OR (FROM "{clean_query}") (SUBJECT "{clean_query}")) (BODY "{clean_query}"))'
    elif search_type.upper() in ["FROM", "SUBJECT", "BODY", "TEXT"]:
        criteria = f'({search_type.upper()} "{clean_query}")'
    else:
        # Default to ALL
        criteria = f'(OR (OR (FROM "{clean_query}") (SUBJECT "{clean_query}")) (BODY "{clean_query}"))'
    
    # Add date filters if provided
    if date_since:
        # Format: DD-MMM-YYYY (e.g., 01-Jan-2024)
        criteria += f' SINCE "{date_since}"'
    if date_before:
        criteria += f' BEFORE "{date_before}"'
    
    return criteria


# ============================================================
# Error Handling Decorator
# ============================================================

def _handle_errors(func):
    """Decorator to standardize error responses."""
    @functools.wraps(func)  # Preserves original signature so @tool builds a correct schema
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict):
                return json.dumps({"status": "success", **result}, default=str)
            else:
                return json.dumps({"status": "success", "output": str(result)})
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error in {func.__name__}: {e}")
            return json.dumps({"status": "error", "error": f"IMAP error: {str(e)}", "error_type": "imap_error"})
        except ConnectionError as e:
            logger.error(f"Connection error in {func.__name__}: {e}")
            return json.dumps({"status": "error", "error": f"Connection error: {str(e)}", "error_type": "connection_error"})
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "unknown"})
    return wrapper


# ============================================================
# Main Tool
# ============================================================

@tool
@_handle_errors
def search_emails(
    query: str,
    folder: str = "INBOX",
    limit: int = 5,
    search_type: str = "ALL",
    date_since: Optional[str] = None,
    date_before: Optional[str] = None,
    include_body: bool = False,
    body_snippet_length: int = 200
) -> dict:
    """
    Search emails in a specified folder based on a query.
    
    Parameters:
    - query: Text to search (sender name, subject, keyword, etc.)
    - folder: IMAP folder name (default: INBOX)
    - limit: Maximum number of emails to return (default: 5, max: 50)
    - search_type: Type of search: ALL (default), FROM, SUBJECT, BODY, TEXT
    - date_since: Filter emails after this date (format: DD-MMM-YYYY, e.g., "01-Jan-2024")
    - date_before: Filter emails before this date (format: DD-MMM-YYYY)
    - include_body: If True, include full body text in output (default: False)
    - body_snippet_length: Length of snippet to include if include_body is False (default: 200)
    
    Returns:
    A list of emails with sender, subject, date, and snippet/full body.
    """
    # Load configuration
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    
    if not email_addr or not password:
        raise ValueError("Email credentials not set. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in .env file.")
    
    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        limit = 5
    limit = min(limit, 50)  # Cap to 50 emails
    
    # Build search criteria
    search_criteria = _build_search_criteria(
        query=query,
        folder=folder,
        search_type=search_type,
        date_since=date_since,
        date_before=date_before
    )
    
    # Connect to IMAP with context manager for proper cleanup
    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port, timeout=30)
        mail.login(email_addr, password)
        mail.select(folder)  # Raises error if folder doesn't exist
        
        # Search
        status, messages = mail.search(None, search_criteria)
        if status != "OK":
            raise imaplib.IMAP4.error(f"Search failed with status: {status}")
        
        # Get email IDs
        email_ids = messages[0].split()
        if not email_ids:
            return {"message": f"'{query}' se koi email nahi mili.", "emails": [], "count": 0}
        
        # Process in reverse chronological order (latest first if sorted by date)
        # IMAP returns in ascending order (oldest first), so reverse to get newest first
        email_ids = list(reversed(email_ids))[:limit]
        
        emails = []
        for e_id in email_ids:
            # Fetch email (RFC822 = full message)
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Decode subject
            subject = _decode_mime_header(msg.get("Subject", ""))
            
            # Decode sender
            sender = _decode_mime_header(msg.get("From", ""))
            
            # Decode date
            date_str = msg.get("Date", "")
            try:
                dt = parsedate_to_datetime(date_str)
                date_formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                date_formatted = date_str  # Keep original if parsing fails
            
            # Get body
            full_body = _get_email_body(msg)
            
            # Prepare snippet or full body
            if include_body:
                body_output = full_body
            else:
                body_output = full_body[:body_snippet_length] + "..." if len(full_body) > body_snippet_length else full_body
            
            email_obj = {
                "id": e_id.decode('utf-8', errors='replace'),
                "sender": sender,
                "subject": subject,
                "date": date_formatted,
                "snippet" if not include_body else "body": body_output,
                # Fixed: check leaf (non-multipart) parts for the actual attachment
                # disposition instead of the multipart containers, which never
                # carry a Content-Disposition of "attachment" themselves.
                "has_attachments": any(
                    part.get_content_disposition() == "attachment"
                    for part in msg.walk() if not part.is_multipart()
                )
            }
            emails.append(email_obj)
        
        # Close connection (logout)
        try:
            mail.logout()
        except:
            pass
        
        return {
            "message": f"{len(emails)} email(s) mili '{query}' ke liye.",
            "emails": emails,
            "count": len(emails),
            "folder": folder
        }
        
    except imaplib.IMAP4.error as e:
        # Re-raise to be caught by decorator
        raise
    except Exception as e:
        raise


# ============================================================
# Additional Helper Tools (Optional)
# ============================================================

@tool
@_handle_errors
def list_email_folders() -> dict:
    """
    List all available email folders (IMAP mailboxes).
    """
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    
    if not email_addr or not password:
        raise ValueError("Email credentials not set.")
    
    mail = imaplib.IMAP4_SSL(imap_server, imap_port, timeout=30)
    mail.login(email_addr, password)
    
    status, folders = mail.list()
    if status != "OK":
        raise imaplib.IMAP4.error(f"Failed to list folders: {status}")
    
    folder_list = []
    for folder_info in folders:
        # Parse folder name
        parts = folder_info.decode('utf-8', errors='replace').split(' "')
        if len(parts) >= 3:
            folder_name = parts[-1].strip('"')
            folder_list.append(folder_name)
    
    mail.logout()
    return {"folders": folder_list, "count": len(folder_list)}
