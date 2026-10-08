import re
from typing import Dict, Any, List

# Regex patterns for sensitive information detection
PHONE_REGEX = re.compile(r'(?:\+?91[\s-]?)?[6-9]\d{9}|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b|\b\d{5}[-.\s]\d{5}\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PAN_REGEX = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')
AADHAAR_REGEX = re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b')
CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
UPI_REGEX = re.compile(r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b')

def mask_text(text: str, visible_start: int = 2, visible_end: int = 2) -> str:
    """Masks a sensitive string preserving first and last few characters."""
    s = str(text).strip()
    if len(s) <= (visible_start + visible_end):
        return "*" * len(s)
    masked_len = len(s) - visible_start - visible_end
    return s[:visible_start] + ("*" * masked_len) + s[-visible_end:]

def detect_sensitive_data_in_text(raw_text: str) -> List[Dict[str, Any]]:
    """Detects PII / sensitive information in a string."""
    findings = []
    if not raw_text or not isinstance(raw_text, str):
        return findings

    # Phone numbers
    phones = PHONE_REGEX.findall(raw_text)
    if phones:
        findings.append({
            "type": "Phone Number",
            "count": len(phones),
            "masked_sample": mask_text(phones[0], 3, 2),
            "warning": "Contains phone number(s)."
        })

    # Emails
    emails = EMAIL_REGEX.findall(raw_text)
    if emails:
        # Filter out common false positives like noreply or example
        valid_emails = [e for e in emails if not e.endswith('@docsnap')]
        if valid_emails:
            findings.append({
                "type": "Email Address",
                "count": len(valid_emails),
                "masked_sample": mask_text(valid_emails[0], 2, 3),
                "warning": "Contains email address(es)."
            })

    # PAN Card
    pans = PAN_REGEX.findall(raw_text)
    if pans:
        findings.append({
            "type": "Government ID (PAN Card)",
            "count": len(pans),
            "masked_sample": mask_text(pans[0], 2, 1),
            "warning": "Contains Indian PAN Card number."
        })

    # Aadhaar Number
    aadhaars = AADHAAR_REGEX.findall(raw_text)
    if aadhaars:
        findings.append({
            "type": "Government ID (Aadhaar)",
            "count": len(aadhaars),
            "masked_sample": mask_text(aadhaars[0], 2, 2),
            "warning": "Contains 12-digit Aadhaar number format."
        })

    # Payment Card
    cards = CARD_REGEX.findall(raw_text)
    if cards:
        findings.append({
            "type": "Payment Card / Account",
            "count": len(cards),
            "masked_sample": mask_text(cards[0], 4, 4),
            "warning": "Contains 16-digit card / account format."
        })

    return findings

def scan_document_for_sensitive_data(data: Any) -> Dict[str, Any]:
    """
    Recursively scans document dictionary or text for sensitive personal data.
    Returns:
        {
            "has_sensitive_data": bool,
            "findings": [ { "type": str, "count": int, "masked_sample": str, "warning": str } ],
            "alert_message": str
        }
    """
    all_text = []

    def extract_text(node):
        if isinstance(node, str):
            all_text.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                extract_text(v)
        elif isinstance(node, list):
            for item in node:
                extract_text(item)

    extract_text(data)
    combined = " \n ".join(all_text)
    
    findings = detect_sensitive_data_in_text(combined)
    has_sensitive = len(findings) > 0
    
    alert_message = ""
    if has_sensitive:
        types_str = ", ".join([f['type'] for f in findings])
        alert_message = f"Sensitive Information Detected ({types_str}). Be careful before sharing or exporting this document."

    return {
        "has_sensitive_data": has_sensitive,
        "findings": findings,
        "alert_message": alert_message
    }
