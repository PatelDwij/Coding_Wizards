import re
import datetime
from typing import Dict, Any, List, Tuple

def parse_time_to_minutes(time_str: str) -> int:
    """Parses 'HH:MM' string to minutes since midnight."""
    if not time_str:
        return -1
    clean = re.sub(r'[^0-9:]', '', str(time_str).strip())
    parts = clean.split(':')
    if len(parts) >= 2:
        try:
            h = int(parts[0])
            m = int(parts[1])
            return h * 60 + m
        except (ValueError, IndexError):
            pass
    return -1

def verify_document(doc_type: str, data: Dict[str, Any], field_confidence: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Dedicated Verification Agent for extracted document data.
    Performs deterministic and domain-specific consistency checks, mathematical validations,
    timetable overlap detection, date/time logic, and field confidence audits.
    
    Returns:
        {
            "status": "verified" | "needs_review" | "warning",
            "score": int (0 - 100),
            "summary_text": str,
            "issues": [ {"field": str, "severity": "error"|"warning"|"info", "message": str, "details": str} ],
            "passed_checks": [ str ]
        }
    """
    issues = []
    passed_checks = []
    field_confidence = field_confidence or {}
    
    if not data or not isinstance(data, dict):
        return {
            "status": "warning",
            "score": 0,
            "summary_text": "Empty or invalid document payload",
            "issues": [{"field": "data", "severity": "error", "message": "No structured data found in extraction result."}],
            "passed_checks": []
        }
        
    # Check 1: Audit field-level confidence scores
    for field_name, conf_val in field_confidence.items():
        if isinstance(conf_val, (int, float)):
            if conf_val < 0.70:
                issues.append({
                    "field": field_name,
                    "severity": "warning",
                    "message": f"Low AI confidence on '{field_name}' ({round(conf_val * 100)}%).",
                    "details": f"AI confidence score is below 70%. Please verify this field against the original image."
                })
            elif conf_val < 0.85:
                issues.append({
                    "field": field_name,
                    "severity": "info",
                    "message": f"Medium confidence on '{field_name}' ({round(conf_val * 100)}%).",
                    "details": "Moderate confidence. Quick visual review recommended."
                })
                
    if not any(i['severity'] == 'warning' for i in issues if 'confidence' in i['message']):
        passed_checks.append("All field-level AI confidence scores are at or above 70%.")

    # Document-specific verification rules
    if doc_type == 'timetable':
        verify_timetable(data, issues, passed_checks)
    elif doc_type == 'receipt':
        verify_receipt(data, issues, passed_checks)
    elif doc_type in ('notice', 'poster'):
        verify_notice(data, issues, passed_checks)
    else:
        verify_general(data, issues, passed_checks)
        
    # Determine overall status and score
    error_count = sum(1 for i in issues if i['severity'] == 'error')
    warning_count = sum(1 for i in issues if i['severity'] == 'warning')
    info_count = sum(1 for i in issues if i['severity'] == 'info')
    
    # Calculate verification score
    base_score = 100
    base_score -= (error_count * 30)
    base_score -= (warning_count * 15)
    base_score -= (info_count * 5)
    score = max(10, min(100, base_score))
    
    if error_count > 0 or warning_count >= 2:
        status = "warning" # 🔴 Verification Warning
        summary_text = f"Verification Warning: {error_count + warning_count} issue(s) detected. User review strongly recommended."
    elif warning_count > 0 or score < 85:
        status = "needs_review" # 🟡 Needs Review
        summary_text = f"Needs Review: {warning_count} potential discrepancy or low-confidence field found."
    else:
        status = "verified" # 🟢 Verified
        summary_text = "All verification checks passed with high confidence."
        
    return {
        "status": status,
        "score": score,
        "summary_text": summary_text,
        "issues": issues,
        "passed_checks": passed_checks,
        "stats": {
            "errors": error_count,
            "warnings": warning_count,
            "infos": info_count,
            "passed": len(passed_checks)
        }
    }

def verify_timetable(data: Dict[str, Any], issues: List[Dict[str, Any]], passed_checks: List[str]):
    """Validates timetable entries, detects overlapping classes, and checks time ranges."""
    entries = data.get('entries', [])
    if not entries:
        issues.append({
            "field": "entries",
            "severity": "error",
            "message": "Timetable has no schedule entries.",
            "details": "Could not identify any classes or lectures."
        })
        return
        
    passed_checks.append(f"Successfully identified {len(entries)} timetable class sessions.")
    
    # Group entries by day
    by_day = {}
    time_issues_found = False
    
    for idx, e in enumerate(entries):
        subject = e.get('subject') or 'Unnamed Class'
        day = str(e.get('day') or 'Monday').strip().capitalize()
        start = str(e.get('start_time') or '').strip()
        end = str(e.get('end_time') or '').strip()
        
        # Check required fields
        if not e.get('subject'):
            issues.append({
                "field": f"entries[{idx}].subject",
                "severity": "warning",
                "message": f"Class entry on {day} has missing subject name.",
                "details": "Please provide the course or subject title."
            })
            
        start_min = parse_time_to_minutes(start)
        end_min = parse_time_to_minutes(end)
        
        if start_min < 0 or end_min < 0:
            time_issues_found = True
            issues.append({
                "field": f"entries[{idx}].time",
                "severity": "warning",
                "message": f"Invalid time format in '{subject}' ({start} - {end}).",
                "details": "Expected 24-hour time format like '09:30' or '14:00'."
            })
        elif end_min <= start_min:
            time_issues_found = True
            issues.append({
                "field": f"entries[{idx}].end_time",
                "severity": "error",
                "message": f"Class '{subject}' ends ({end}) before or at start time ({start}).",
                "details": "End time must be later than start time."
            })
            
        by_day.setdefault(day, []).append({
            "idx": idx,
            "subject": subject,
            "start": start,
            "end": end,
            "start_min": start_min,
            "end_min": end_min,
            "room": e.get('room') or ''
        })
        
    if not time_issues_found:
        passed_checks.append("All class start and end time sequences are chronologically valid.")
        
    # Detect overlapping classes on the same day
    has_overlaps = False
    for day, day_entries in by_day.items():
        n = len(day_entries)
        for i in range(n):
            for j in range(i + 1, n):
                e1 = day_entries[i]
                e2 = day_entries[j]
                
                # Check overlap if both have valid times
                if e1['start_min'] >= 0 and e1['end_min'] > 0 and e2['start_min'] >= 0 and e2['end_min'] > 0:
                    overlap_start = max(e1['start_min'], e2['start_min'])
                    overlap_end = min(e1['end_min'], e2['end_min'])
                    
                    if overlap_end > overlap_start:
                        has_overlaps = True
                        overlap_duration = overlap_end - overlap_start
                        issues.append({
                            "field": "entries",
                            "severity": "warning",
                            "message": f"Timetable conflict on {day}: '{e1['subject']}' ({e1['start']}-{e1['end']}) and '{e2['subject']}' ({e2['start']}-{e2['end']}) overlap by {overlap_duration} mins.",
                            "details": f"Both classes are scheduled at the same time on {day}. Please verify if one is an elective or lab batch."
                        })
                        
    if not has_overlaps:
        passed_checks.append("No conflicting or overlapping lecture intervals detected.")

def verify_receipt(data: Dict[str, Any], issues: List[Dict[str, Any]], passed_checks: List[str]):
    """Validates receipt math (items sum vs total), price sanity, and date validity."""
    merchant = data.get('merchant')
    currency = data.get('currency') or '₹'
    total = data.get('total')
    items = data.get('items', [])
    date_str = data.get('date')
    
    if not merchant:
        issues.append({
            "field": "merchant",
            "severity": "warning",
            "message": "Merchant / store name was not detected.",
            "details": "Please verify the store name from the receipt header."
        })
    else:
        passed_checks.append(f"Merchant identified: '{merchant}'.")
        
    # Mathematical validation of line items
    if items:
        calculated_total = 0.0
        has_invalid_price = False
        
        for idx, item in enumerate(items):
            try:
                qty = float(item.get('qty', 1))
            except (ValueError, TypeError):
                qty = 1.0
                
            try:
                price = float(item.get('price', 0))
            except (ValueError, TypeError):
                price = 0.0
                
            if price <= 0:
                has_invalid_price = True
                issues.append({
                    "field": f"items[{idx}].price",
                    "severity": "info",
                    "message": f"Item '{item.get('name', f'Item {idx+1}')}' has zero or negative price ({price}).",
                    "details": "Verify if this was a complimentary item or coupon."
                })
                
            calculated_total += (qty * price)
            
        calculated_total = round(calculated_total, 2)
        
        if total is not None:
            try:
                ext_total = round(float(total), 2)
                diff = round(abs(ext_total - calculated_total), 2)
                
                # Allow minor tolerance (tax, service charge, tip, rounding) up to 2.0 or 15%
                if diff > 1.5 and diff > (0.15 * ext_total):
                    issues.append({
                        "field": "total",
                        "severity": "warning",
                        "message": f"Arithmetic discrepancy: Extracted Total is {currency} {ext_total:,.2f}, but line items sum to {currency} {calculated_total:,.2f} (Difference: {currency} {diff:,.2f}).",
                        "details": "Line items do not add up to the receipt total. Taxes, discounts, or an unextracted item may account for the difference."
                    })
                else:
                    passed_checks.append(f"Receipt line item arithmetic matches total ({currency} {ext_total:,.2f}).")
            except (ValueError, TypeError):
                issues.append({
                    "field": "total",
                    "severity": "error",
                    "message": f"Receipt total is not a valid numeric amount ({total}).",
                    "details": "Please enter a valid numeric total amount."
                })
        else:
            issues.append({
                "field": "total",
                "severity": "warning",
                "message": "Receipt total amount is missing.",
                "details": f"Line items sum to {currency} {calculated_total:,.2f}. Please confirm the total."
            })
    else:
        if total is not None:
            passed_checks.append(f"Receipt total amount recorded: {currency} {total}.")
        else:
            issues.append({
                "field": "items",
                "severity": "warning",
                "message": "No itemized line items or total found on the receipt.",
                "details": "Please check if the receipt was clearly legible."
            })
            
    # Check date validity
    if date_str:
        try:
            r_date = datetime.date.fromisoformat(str(date_str).strip())
            today = datetime.date.today()
            if r_date > today + datetime.timedelta(days=1):
                issues.append({
                    "field": "date",
                    "severity": "warning",
                    "message": f"Receipt date ({date_str}) is in the future.",
                    "details": "Please verify if the year or day was misrecognized."
                })
            else:
                passed_checks.append(f"Receipt date ({date_str}) is valid.")
        except Exception:
            issues.append({
                "field": "date",
                "severity": "info",
                "message": f"Receipt date '{date_str}' is not in standard YYYY-MM-DD format.",
                "details": "Format as YYYY-MM-DD for best spreadsheet compatibility."
            })

def verify_notice(data: Dict[str, Any], issues: List[Dict[str, Any]], passed_checks: List[str]):
    """Validates notice dates, start/end intervals, headline, and venue."""
    title = data.get('title')
    date_str = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    venue = data.get('venue')
    
    if not title:
        issues.append({
            "field": "title",
            "severity": "warning",
            "message": "Notice headline / title is missing.",
            "details": "Please provide an event headline or notice subject."
        })
    else:
        passed_checks.append("Event title identified.")
        
    if not venue:
        issues.append({
            "field": "venue",
            "severity": "info",
            "message": "No location or venue specified in notice.",
            "details": "Add a location if an in-person or online venue is mentioned."
        })
    else:
        passed_checks.append(f"Venue specified: '{venue}'.")
        
    if date_str:
        try:
            ev_date = datetime.date.fromisoformat(str(date_str).strip())
            passed_checks.append(f"Event date verified: {date_str}.")
        except Exception:
            issues.append({
                "field": "date",
                "severity": "info",
                "message": f"Date '{date_str}' could not be parsed as standard YYYY-MM-DD.",
                "details": "Please verify date format."
            })
    else:
        issues.append({
            "field": "date",
            "severity": "warning",
            "message": "No specific event date was extracted.",
            "details": "Check if an event date or deadline is visible on the notice."
        })
        
    if start_time and end_time:
        s_min = parse_time_to_minutes(start_time)
        e_min = parse_time_to_minutes(end_time)
        if s_min >= 0 and e_min >= 0:
            if e_min <= s_min:
                issues.append({
                    "field": "end_time",
                    "severity": "warning",
                    "message": f"Event end time ({end_time}) is earlier than start time ({start_time}).",
                    "details": "End time must be later than start time on the same date."
                })
            else:
                passed_checks.append(f"Event duration confirmed ({start_time} to {end_time}).")

def verify_general(data: Dict[str, Any], issues: List[Dict[str, Any]], passed_checks: List[str]):
    """General verification checks for other or unclassified documents."""
    if not data:
        issues.append({
            "field": "data",
            "severity": "warning",
            "message": "No key-value fields detected.",
            "details": "Check document legibility."
        })
    else:
        passed_checks.append(f"Extracted {len(data)} document fields.")
