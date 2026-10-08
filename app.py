import os
import io
import csv
import json
import time
import re
import datetime
import zoneinfo
import hashlib
import uuid
import base64
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from dotenv import load_dotenv
load_dotenv()
from PIL import Image, ImageOps

# Modular DocSnap services
import database
import verification
import sensitive_data
import ai_services

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
TIMEZONE_KOLKATA = zoneinfo.ZoneInfo("Asia/Kolkata")

# Primary and fallback Gemini models
# Primary: "gemini-3.5-flash", fallbacks: "gemini-3.5-flash-lite", "gemini-3.8-flash"
MODELS_TO_TRY = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
BACKOFF_DELAYS = [2, 4, 8, 16]

# In-memory cache for extraction results by SHA-256 image hash
EXTRACTION_CACHE = {}

# Current status for UI retry notifications
CURRENT_RETRY_STATUS = ""

# Predefined curated mock responses for built-in sample images for instant demo testing
SAMPLE_MOCKS = {
    "timetable": {
        "doc_type": "timetable",
        "model_used": "gemini-3.8-flash",
        "model": "gemini-3.8-flash",
        "language": "English",
        "confidence": 0.98,
        "field_confidence": {
            "title": 0.99,
            "entries": 0.97,
            "entries.subject": 0.98,
            "entries.day": 0.99,
            "entries.start_time": 0.96,
            "entries.end_time": 0.96,
            "entries.room": 0.94,
            "entries.faculty": 0.92
        },
        "data": {
            "title": "Apex Institute of Technology - Computer Science Dept (Semester IV)",
            "entries": [
                {"subject": "Data Structures", "day": "Monday", "start_time": "09:00", "end_time": "10:00", "room": "Room 302", "faculty": "Dr. A. Verma"},
                {"subject": "Maths III", "day": "Monday", "start_time": "10:00", "end_time": "11:00", "room": "Room 302", "faculty": "Prof. R. Iyer"},
                {"subject": "Algorithms Lab", "day": "Monday", "start_time": "11:15", "end_time": "12:15", "room": "CS Lab 1", "faculty": "Dr. Verma / Neha"},
                {"subject": "Computer Networks", "day": "Monday", "start_time": "13:30", "end_time": "14:30", "room": "Room 302", "faculty": "Prof. K. Sen"},
                {"subject": "Library / Mentoring", "day": "Monday", "start_time": "14:30", "end_time": "15:30", "room": "Central Library", "faculty": "Self Study"},
                
                {"subject": "Operating Systems", "day": "Tuesday", "start_time": "09:00", "end_time": "10:00", "room": "Room 204", "faculty": "Prof. P. Patel"},
                {"subject": "Data Structures", "day": "Tuesday", "start_time": "10:00", "end_time": "11:00", "room": "Room 302", "faculty": "Dr. A. Verma"},
                {"subject": "Database Systems", "day": "Tuesday", "start_time": "11:15", "end_time": "12:15", "room": "Room 101", "faculty": "Dr. Neha Shah"},
                {"subject": "Maths III", "day": "Tuesday", "start_time": "13:30", "end_time": "14:30", "room": "Room 302", "faculty": "Prof. R. Iyer"},
                {"subject": "Tech Seminar", "day": "Tuesday", "start_time": "14:30", "end_time": "15:30", "room": "Seminar Hall A", "faculty": "Guest Speaker"},
                
                {"subject": "Computer Networks", "day": "Wednesday", "start_time": "09:00", "end_time": "10:00", "room": "Room 302", "faculty": "Prof. K. Sen"},
                {"subject": "Operating Systems", "day": "Wednesday", "start_time": "10:00", "end_time": "11:00", "room": "Room 204", "faculty": "Prof. P. Patel"},
                {"subject": "Web Dev Lab", "day": "Wednesday", "start_time": "11:15", "end_time": "12:15", "room": "Lab 3", "faculty": "Prof. K. Sen"},
                {"subject": "Software Engg", "day": "Wednesday", "start_time": "13:30", "end_time": "14:30", "room": "Room 204", "faculty": "Prof. M. Joshi"},
                
                {"subject": "Database Systems", "day": "Thursday", "start_time": "09:00", "end_time": "10:00", "room": "Room 101", "faculty": "Dr. Neha Shah"},
                {"subject": "Maths III", "day": "Thursday", "start_time": "10:00", "end_time": "11:00", "room": "Room 302", "faculty": "Prof. R. Iyer"},
                {"subject": "Data Structures", "day": "Thursday", "start_time": "11:15", "end_time": "12:15", "room": "Room 302", "faculty": "Dr. A. Verma"},
                {"subject": "Operating Systems", "day": "Thursday", "start_time": "13:30", "end_time": "14:30", "room": "Room 204", "faculty": "Prof. P. Patel"},
                
                {"subject": "Software Engg", "day": "Friday", "start_time": "09:00", "end_time": "10:00", "room": "Room 204", "faculty": "Prof. M. Joshi"},
                {"subject": "Computer Networks", "day": "Friday", "start_time": "10:00", "end_time": "11:00", "room": "Room 302", "faculty": "Prof. K. Sen"},
                {"subject": "Database Lab", "day": "Friday", "start_time": "11:15", "end_time": "12:15", "room": "Lab 2", "faculty": "Dr. Neha Shah"},
                {"subject": "Project Work", "day": "Friday", "start_time": "13:30", "end_time": "14:30", "room": "Project Lab 4", "faculty": "Mentors"}
            ]
        }
    },
    "receipt": {
        "doc_type": "receipt",
        "model_used": "gemini-3.8-flash",
        "model": "gemini-3.8-flash",
        "language": "English",
        "confidence": 0.97,
        "field_confidence": {
            "merchant": 0.99,
            "date": 0.98,
            "items": 0.96,
            "total": 0.99,
            "currency": 0.99,
            "category": 0.95
        },
        "data": {
            "merchant": "Urban Bistro & Cafe",
            "date": "2026-09-28",
            "items": [
                {"name": "Artisan Cappuccino (Grande)", "qty": 2, "price": 480.00},
                {"name": "Wild Mushroom Risotto", "qty": 1, "price": 495.00},
                {"name": "Garlic Herb Bruschetta", "qty": 1, "price": 290.00},
                {"name": "Belgian Chocolate Mousse", "qty": 1, "price": 340.00},
                {"name": "Sparkling Mineral Water 750ml", "qty": 1, "price": 160.00}
            ],
            "total": 1853.25,
            "currency": "₹",
            "category": "Food & Dining"
        }
    },
    "notice": {
        "doc_type": "notice",
        "model_used": "gemini-3.8-flash",
        "model": "gemini-3.8-flash",
        "language": "English",
        "confidence": 0.96,
        "field_confidence": {
            "title": 0.98,
            "date": 0.97,
            "start_time": 0.95,
            "end_time": 0.95,
            "venue": 0.96,
            "description": 0.94
        },
        "data": {
            "title": "HackFest 2026: 24-Hour Code Sprint",
            "date": "2026-10-24",
            "start_time": "09:30",
            "end_time": "18:30",
            "venue": "Main Convention Center, Hall B, Tech Park Campus",
            "description": "Annual 24-hour hackathon on AI Solutions for Social Impact & Sustainability. Open to all students with cash prizes up to INR 1,50,000."
        }
    }
}

# Pre-cache built-in samples by image hash
try:
    for _sk, _sf in [('timetable', 'sample_timetable.png'), ('receipt', 'sample_receipt.png'), ('notice', 'sample_notice.png')]:
        _sp = Path(__file__).parent / 'static' / 'samples' / _sf
        if _sp.exists():
            with open(_sp, 'rb') as _f:
                _h = hashlib.sha256(_f.read()).hexdigest()
                _m = dict(SAMPLE_MOCKS[_sk])
                _m["_demo_mode"] = True
                _m["_note"] = "Extracted using DocSnap sample demo mode."
                EXTRACTION_CACHE[_h] = _m
except Exception:
    pass

SYSTEM_PROMPT = """You are DocSnap AI, an advanced OCR and document intelligence engine.
Your task is to analyze the uploaded document image (which may be in English, Hindi, or Gujarati), detect its document type, and return ONLY a valid JSON object.

Follow these strict output constraints:
1. Output MUST be ONLY valid JSON. Do not include markdown code fences, backticks (```), commentary, or explanations.
2. Structure:
{
  "doc_type": "timetable" | "receipt" | "notice" | "poster" | "other",
  "language": "detected language(s)",
  "confidence": 0.0 to 1.0,
  "field_confidence": {
    "<field_name>": 0.0 to 1.0
  },
  "data": { ... } or null
}

Document Schemas:
- If doc_type is "timetable":
  "data": {
    "title": "Schedule or institute title",
    "entries": [
      {
        "subject": "Course or Subject name",
        "day": "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday",
        "start_time": "HH:MM" (24-hour format, e.g. 09:30),
        "end_time": "HH:MM" (24-hour format, e.g. 10:30),
        "room": "Room or Hall identifier or null",
        "faculty": "Faculty/Instructor name or null"
      }
    ]
  }

- If doc_type is "receipt":
  "data": {
    "merchant": "Store or merchant name",
    "date": "YYYY-MM-DD" or null,
    "items": [
      {
        "name": "Item description",
        "qty": number,
        "price": number
      }
    ],
    "total": number,
    "currency": "currency symbol or code, e.g. ₹, Rs., $, €",
    "category": "Food & Dining | Groceries | Shopping | Utilities | Travel | Electronics | Other"
  }

- If doc_type is "notice" or "poster":
  "data": {
    "title": "Notice/Event headline",
    "date": "YYYY-MM-DD" or null,
    "start_time": "HH:MM" or null,
    "end_time": "HH:MM" or null,
    "venue": "Event location/venue or null",
    "description": "Concise summary of event/notice details"
  }

- If doc_type is "other":
  "data": {
    "title": "Document Title or null",
    "summary": "Summary of document",
    "key_fields": {
      "field_name": "field_value"
    }
  }

CRITICAL RULES:
- Never hallucinate or invent values. Use null for any details not clearly visible.
- Support English, Hindi (हिंदी), and Gujarati (ગુજરાતી) text accurately.
- DO NOT TRANSLATE; preserve the original text and spelling exactly as seen in the image.
- Provide a confidence score between 0.0 and 1.0 for each extracted field in "field_confidence".
- If the image is not a recognized document, set "doc_type" to "other" and extract what text is visible.
"""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_json_text(text):
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def is_daily_quota_error(err):
    err_str = str(err).lower()
    code = getattr(err, 'code', None) or getattr(err, 'status_code', None)
    is_quota_issue = (code == 429) or ("429" in err_str) or ("resource_exhausted" in err_str) or ("quota" in err_str)
    if not is_quota_issue:
        return False
    daily_keywords = ["daily", "per day", "perday", "per_day", "day limit", "requests per day", "free-tier quota", "free tier", "day"]
    return any(k in err_str for k in daily_keywords)

def is_retryable_error(err):
    code = getattr(err, 'code', None) or getattr(err, 'status_code', None)
    if code == 404:
        return False
    err_str = str(err).lower()
    if "404" in err_str or "not_found" in err_str or "not found" in err_str or "no longer available" in err_str:
        return False
    if is_daily_quota_error(err):
        return False
    if code in (503, 504) or code == 429:
        return True
    if "503" in err_str or "unavailable" in err_str or "timeout" in err_str or "deadline" in err_str or "429" in err_str or "resource_exhausted" in err_str:
        return True
    return False

def generate_thumbnail_base64(pil_img, max_size=(240, 240)):
    """Generates an embedded JPEG thumbnail data URL."""
    try:
        thumb = pil_img.copy()
        thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        if thumb.mode in ('RGBA', 'LA', 'P'):
            thumb = thumb.convert('RGB')
        thumb.save(buf, format='JPEG', quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return ""

def generate_docsnap_ics(doc_type, data):
    """
    Generates an RFC 5545 compliant .ics calendar string in timezone Asia/Kolkata.
    """
    now = datetime.datetime.now(TIMEZONE_KOLKATA)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    dtstamp = now_utc.strftime("%Y%m%dT%H%M%SZ")
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DocSnap//DocSnap Timetable Exporter//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:DocSnap Timetable",
        "X-WR-TIMEZONE:Asia/Kolkata",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Kolkata",
        "TZURL:http://tzurl.org/zoneinfo-outlook/Asia/Kolkata",
        "X-LIC-LOCATION:Asia/Kolkata",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0530",
        "TZOFFSETTO:+0530",
        "TZNAME:IST",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE"
    ]
    
    def escape_ics(text):
        if not text:
            return ""
        s = str(text).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
        return s.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
    
    weekday_map = {
        'monday': 0, 'mon': 0, 'tuesday': 1, 'tue': 1, 'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3, 'friday': 4, 'fri': 4, 'saturday': 5, 'sat': 5, 'sunday': 6, 'sun': 6
    }
    
    if doc_type == 'timetable':
        entries = data.get('entries', [])
        if not entries:
            return None, "Timetable has no entries to export."
            
        for idx, entry in enumerate(entries):
            subject = entry.get('subject') or 'Class'
            day_str = str(entry.get('day', '')).strip().lower()
            start_str = str(entry.get('start_time', '')).strip()
            end_str = str(entry.get('end_time', '')).strip()
            room = entry.get('room') or ''
            faculty = entry.get('faculty') or ''
            
            target_weekday = weekday_map.get(day_str, 0)
            current_weekday = now.weekday()
            days_ahead = (target_weekday - current_weekday) % 7
            
            try:
                sh, sm = map(int, start_str.split(':')[:2])
            except Exception:
                sh, sm = 9, 0
                
            try:
                eh, em = map(int, end_str.split(':')[:2])
            except Exception:
                eh, em = (sh + 1) % 24, sm
                
            base_date = now.date() + datetime.timedelta(days=days_ahead)
            start_dt = datetime.datetime(base_date.year, base_date.month, base_date.day, sh, sm, tzinfo=TIMEZONE_KOLKATA)
            
            if days_ahead == 0 and start_dt <= now:
                start_dt += datetime.timedelta(days=7)
                
            end_dt = datetime.datetime(start_dt.year, start_dt.month, start_dt.day, eh, em, tzinfo=TIMEZONE_KOLKATA)
            if end_dt <= start_dt:
                end_dt = start_dt + datetime.timedelta(hours=1)
                
            dtstart_val = start_dt.strftime("%Y%m%dT%H%M%S")
            dtend_val = end_dt.strftime("%Y%m%dT%H%M%S")
            
            summary = f"{subject} ({room})" if room else subject
            desc_items = []
            if faculty: desc_items.append(f"Faculty: {faculty}")
            if room: desc_items.append(f"Room: {room}")
            description = " | ".join(desc_items)
            
            event_uid = f"timetable-{idx}-{int(start_dt.timestamp())}-{uuid.uuid4().hex[:8]}@docsnap"
            
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{event_uid}")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"SUMMARY:{escape_ics(summary)}")
            if description: lines.append(f"DESCRIPTION:{escape_ics(description)}")
            if room: lines.append(f"LOCATION:{escape_ics(room)}")
            lines.append(f"DTSTART;TZID=Asia/Kolkata:{dtstart_val}")
            lines.append(f"DTEND;TZID=Asia/Kolkata:{dtend_val}")
            lines.append("RRULE:FREQ=WEEKLY")
            lines.append("END:VEVENT")
            
    elif doc_type in ('notice', 'poster'):
        title = data.get('title') or "Notice Event"
        date_str = str(data.get('date', '')).strip()
        start_str = str(data.get('start_time', '')).strip()
        end_str = str(data.get('end_time', '')).strip()
        venue = data.get('venue') or ''
        description = data.get('description') or ''
        
        try:
            ev_date = datetime.date.fromisoformat(date_str)
        except Exception:
            ev_date = now.date()
            
        try:
            sh, sm = map(int, start_str.split(':')[:2])
        except Exception:
            sh, sm = 9, 30
            
        try:
            eh, em = map(int, end_str.split(':')[:2])
        except Exception:
            eh, em = 17, 30
            
        start_dt = datetime.datetime(ev_date.year, ev_date.month, ev_date.day, sh, sm, tzinfo=TIMEZONE_KOLKATA)
        end_dt = datetime.datetime(ev_date.year, ev_date.month, ev_date.day, eh, em, tzinfo=TIMEZONE_KOLKATA)
        if end_dt <= start_dt:
            end_dt = start_dt + datetime.timedelta(hours=2)
            
        dtstart_val = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend_val = end_dt.strftime("%Y%m%dT%H%M%S")
        
        event_uid = f"notice-{int(start_dt.timestamp())}-{uuid.uuid4().hex[:8]}@docsnap"
        
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{event_uid}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"SUMMARY:{escape_ics(title)}")
        if description: lines.append(f"DESCRIPTION:{escape_ics(description)}")
        if venue: lines.append(f"LOCATION:{escape_ics(venue)}")
        lines.append(f"DTSTART;TZID=Asia/Kolkata:{dtstart_val}")
        lines.append(f"DTEND;TZID=Asia/Kolkata:{dtend_val}")
        lines.append("END:VEVENT")
    else:
        return None, f"Export to ICS is not supported for document type '{doc_type}'."
        
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n", None

# ==============================================================================
# ROUTES
# ==============================================================================

@app.route('/')
def index():
    """Serves the DocSnap web interface with retry status polling and dynamic model badge update."""
    rendered = render_template('index.html')
    status_script = """
<script>
(function() {
  const defaultSubtitle = "Performing one-shot OCR, classification, and schema extraction...";
  
  function formatModelName(name) {
    if (!name) return "Gemini 3.8 Flash";
    const lower = name.toLowerCase();
    if (lower.includes("3.8") && lower.includes("flash")) return "Gemini 3.8 Flash";
    if (lower.includes("3.5") && lower.includes("lite")) return "Gemini 3.5 Flash Lite";
    if (lower.includes("2.5") && lower.includes("flash")) return "Gemini 2.5 Flash";
    return name;
  }

  function updateModelBadges(modelName) {
    const formatted = formatModelName(modelName);
    const navBadgeText = document.querySelector('.model-badge .badge-text');
    if (navBadgeText) navBadgeText.textContent = formatted;
    const navBadge = document.querySelector('.model-badge');
    if (navBadge) navBadge.title = 'Powered by Google ' + formatted + ' Vision OCR';
    
    let resModelBadge = document.getElementById('badge-model-used');
    if (!resModelBadge) {
      const badgeGroup = document.querySelector('.meta-badges-row .badge-group');
      if (badgeGroup) {
        resModelBadge = document.createElement('span');
        resModelBadge.id = 'badge-model-used';
        resModelBadge.className = 'badge badge-outline';
        badgeGroup.appendChild(resModelBadge);
      }
    }
    if (resModelBadge) {
      resModelBadge.textContent = formatted;
      resModelBadge.title = 'Active Model: ' + formatted;
    }
  }

  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    try {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url);
      if (url && url.includes('/extract') && !url.includes('/extract/status')) {
        const clone = response.clone();
        clone.json().then(data => {
          if (data && (data.model_used || data.model)) {
            const m = data.model_used || data.model;
            sessionStorage.setItem('docsnap_model_used', m);
            updateModelBadges(m);
          }
        }).catch(() => {});
      }
    } catch (e) {}
    return response;
  };

  const storedModel = sessionStorage.getItem('docsnap_model_used') || 'gemini-3.8-flash';
  updateModelBadges(storedModel);

  setInterval(async () => {
    try {
      const procScreen = document.getElementById('screen-processing');
      const sub = document.querySelector('.processing-subtitle');
      if (procScreen && !procScreen.classList.contains('hidden')) {
        const res = await originalFetch('/extract/status');
        if (res.ok) {
          const data = await res.json();
          if (sub && data.status) sub.textContent = data.status;
        }
      }
    } catch (e) {}
  }, 400);
})();
</script>
</body>
"""
    return rendered.replace('</body>', status_script)

@app.route('/extract/status', methods=['GET'])
def extract_status():
    global CURRENT_RETRY_STATUS
    return jsonify({"status": CURRENT_RETRY_STATUS})

@app.route('/static/samples/<filename>')
def serve_sample(filename):
    return send_from_directory('static/samples', filename)

@app.route('/extract', methods=['POST'])
def extract_document():
    """
    Accepts an uploaded image, runs Gemini AI vision extraction with automatic fallback,
    runs Verification Agent and Sensitive Data detection, persists to database history,
    and returns rich structured results.
    """
    global CURRENT_RETRY_STATUS, EXTRACTION_CACHE
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided in request."}), 400
    
    file = request.files['image']
    raw_filename = file.filename or 'upload.png'
    filename = f"{raw_filename}.png" if '.' not in raw_filename else raw_filename
    
    if not allowed_file(filename):
        return jsonify({"error": "Invalid file format. Supported formats are PNG, JPG, JPEG, and WEBP."}), 400
    
    raw_image_bytes = file.read()
    if len(raw_image_bytes) > 5 * 1024 * 1024:
        return jsonify({"error": "Image file exceeds the 5MB size limit. Please upload a smaller image."}), 400
    
    raw_image_hash = hashlib.sha256(raw_image_bytes).hexdigest()
    
    # Check duplicate against existing history
    duplicate_info = database.find_duplicate_document(file_hash=raw_image_hash)
    
    # PIL validation & thumbnail generation
    try:
        pil_img = Image.open(io.BytesIO(raw_image_bytes))
        pil_img.verify()
        pil_img = Image.open(io.BytesIO(raw_image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        return jsonify({"error": "Corrupted or invalid image file. Please upload a valid image."}), 400
    
    thumbnail_data_url = generate_thumbnail_base64(pil_img)
    
    # Resize images larger than 2000px
    orig_w, orig_h = pil_img.size
    longest_side = max(orig_w, orig_h)
    if longest_side > 2000:
        scale = 2000.0 / longest_side
        new_w = max(1, int(round(orig_w * scale)))
        new_h = max(1, int(round(orig_h * scale)))
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        out_buf = io.BytesIO()
        fmt = (pil_img.format or 'JPEG').upper()
        if fmt in ('JPG', 'JPEG'):
            if pil_img.mode in ('RGBA', 'LA', 'P'): pil_img = pil_img.convert('RGB')
            pil_img.save(out_buf, format='JPEG', quality=90)
            mime_type = 'image/jpeg'
        elif fmt == 'PNG':
            pil_img.save(out_buf, format='PNG')
            mime_type = 'image/png'
        else:
            if pil_img.mode in ('RGBA', 'LA', 'P'): pil_img = pil_img.convert('RGB')
            pil_img.save(out_buf, format='JPEG', quality=90)
            mime_type = 'image/jpeg'
        image_bytes = out_buf.getvalue()
    else:
        fmt = (pil_img.format or 'JPEG').lower()
        mime_type = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
        image_bytes = raw_image_bytes

    resized_image_hash = hashlib.sha256(image_bytes).hexdigest()
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    
    filename_lower = filename.lower()
    is_sample_timetable = 'sample_timetable' in filename_lower
    is_sample_receipt = 'sample_receipt' in filename_lower
    is_sample_notice = 'sample_notice' in filename_lower
    
    # 1. Cache hit check
    if raw_image_hash in EXTRACTION_CACHE:
        res = dict(EXTRACTION_CACHE[raw_image_hash])
        attach_post_processing(res, raw_filename, raw_image_hash, thumbnail_data_url, duplicate_info)
        return jsonify(res)
        
    # If no valid API key is configured, fallback to sample mocks
    if not api_key or api_key == 'your_gemini_api_key_here':
        if is_sample_timetable or is_sample_receipt or is_sample_notice:
            key = 'timetable' if is_sample_timetable else ('receipt' if is_sample_receipt else 'notice')
            mock = dict(SAMPLE_MOCKS[key])
            mock["_demo_mode"] = True
            mock["_note"] = "Extracted using DocSnap sample demo mode. To process custom images with live AI, add GEMINI_API_KEY in .env."
            mock["model_used"] = "gemini-3.8-flash"
            mock["model"] = "gemini-3.8-flash"
            EXTRACTION_CACHE[raw_image_hash] = mock
            attach_post_processing(mock, raw_filename, raw_image_hash, thumbnail_data_url, duplicate_info)
            return jsonify(mock)
        else:
            return jsonify({
                "error": "GEMINI_API_KEY is not configured in .env. Please set your Gemini API key in the .env file to enable live AI vision extraction."
            }), 400

    # Live Gemini Vision AI Extraction with retry and fallback
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        last_error = None
        result_json = None
        CURRENT_RETRY_STATUS = ""
        
        for model_name in MODELS_TO_TRY:
            for attempt in range(len(BACKOFF_DELAYS) + 1):
                if attempt > 0:
                    delay = BACKOFF_DELAYS[attempt - 1]
                    CURRENT_RETRY_STATUS = f"Gemini is busy, retrying ({attempt}/4)..."
                    time.sleep(delay)
                    
                try:
                    try:
                        cfg = types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.1,
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                                "Extract and structure this document into JSON strictly following the system instructions."
                            ],
                            config=cfg
                        )
                    except Exception:
                        cfg = types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.1,
                            response_mime_type="application/json"
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                                "Extract and structure this document into JSON strictly following the system instructions."
                            ],
                            config=cfg
                        )
                    
                    raw_text = response.text or ""
                    cleaned = clean_json_text(raw_text)
                    
                    try:
                        result_json = json.loads(cleaned)
                        result_json["model_used"] = model_name
                        result_json["model"] = model_name
                        CURRENT_RETRY_STATUS = ""
                        break
                    except json.JSONDecodeError as je:
                        if attempt == 0:
                            time.sleep(1)
                            continue
                        last_error = f"Model response could not be parsed as valid JSON: {str(je)}"
                except Exception as api_err:
                    last_error = str(api_err)
                    err_str = str(api_err).lower()
                    err_code = getattr(api_err, 'code', None) or getattr(api_err, 'status_code', None)
                    
                    if err_code == 404 or "404" in err_str or "not_found" in err_str or "no longer available" in err_str:
                        CURRENT_RETRY_STATUS = ""
                        break
                    if is_daily_quota_error(api_err):
                        CURRENT_RETRY_STATUS = ""
                        break
                    if is_retryable_error(api_err):
                        if attempt < len(BACKOFF_DELAYS):
                            continue
                        else:
                            CURRENT_RETRY_STATUS = ""
                            break
                    else:
                        CURRENT_RETRY_STATUS = ""
                        break
                        
            if result_json is not None:
                break
                
        CURRENT_RETRY_STATUS = ""
        
        # Sample fallbacks on quota exhaustion
        if result_json is None:
            if is_sample_timetable or is_sample_receipt or is_sample_notice:
                key = 'timetable' if is_sample_timetable else ('receipt' if is_sample_receipt else 'notice')
                mock = dict(SAMPLE_MOCKS[key])
                mock["_demo_mode"] = True
                mock["_note"] = "Gemini quota reached. Loaded sample document."
                mock["model_used"] = "gemini-3.8-flash"
                mock["model"] = "gemini-3.8-flash"
                EXTRACTION_CACHE[raw_image_hash] = mock
                attach_post_processing(mock, raw_filename, raw_image_hash, thumbnail_data_url, duplicate_info)
                return jsonify(mock)
                
            return jsonify({
                "error": f"Failed to process document with Gemini AI after retry: {last_error}"
            }), 502
            
        # Ensure confidence scores exist
        if 'confidence' not in result_json or not isinstance(result_json['confidence'], (int, float)):
            result_json['confidence'] = 0.95
        if 'field_confidence' not in result_json or not isinstance(result_json['field_confidence'], dict):
            result_json['field_confidence'] = {}
            
        # Cache successful extraction
        EXTRACTION_CACHE[raw_image_hash] = dict(result_json)
        EXTRACTION_CACHE[resized_image_hash] = dict(result_json)
        
        attach_post_processing(result_json, raw_filename, raw_image_hash, thumbnail_data_url, duplicate_info)
        return jsonify(result_json)
        
    except Exception as e:
        CURRENT_RETRY_STATUS = ""
        return jsonify({"error": f"An unexpected error occurred during extraction: {str(e)}"}), 500
    finally:
        CURRENT_RETRY_STATUS = ""

def attach_post_processing(result_dict, filename, file_hash, thumbnail_data_url, duplicate_info=None):
    """
    Applies Verification Agent rules, Sensitive Data scanning,
    generates summary preview, and creates persistent database record.
    """
    doc_type = result_dict.get('doc_type', 'other')
    data = result_dict.get('data') or {}
    field_conf = result_dict.get('field_confidence') or {}
    
    # 1. Verification Agent
    ver_report = verification.verify_document(doc_type, data, field_conf)
    result_dict['verification_report'] = ver_report
    result_dict['verification_status'] = ver_report['status']
    
    # 2. Sensitive Data Detection
    sens_info = sensitive_data.scan_document_for_sensitive_data(data)
    result_dict['sensitive_data_info'] = sens_info
    
    # 3. Duplicate Info
    if duplicate_info:
        result_dict['duplicate_info'] = {
            "found": True,
            "existing_id": duplicate_info['id'],
            "existing_filename": duplicate_info['filename'],
            "created_at": duplicate_info['created_at'],
            "verification_status": duplicate_info['verification_status']
        }
    else:
        result_dict['duplicate_info'] = {"found": False}
        
    result_dict['thumbnail'] = thumbnail_data_url
    
    # 4. Save to persistent SQLite Database (Version 1: AI Generated)
    try:
        saved_doc = database.create_document(
            filename=filename,
            file_hash=file_hash,
            doc_type=doc_type,
            language=result_dict.get('language', 'English'),
            ai_confidence=float(result_dict.get('confidence', 0.95)),
            verification_status=ver_report['status'],
            ai_extracted_data=data,
            verification_report=ver_report,
            sensitive_data_info=sens_info,
            thumbnail=thumbnail_data_url
        )
        if saved_doc:
            result_dict['id'] = saved_doc['id']
            result_dict['created_at'] = saved_doc['created_at']
            result_dict['versions'] = saved_doc.get('versions', [])
    except Exception as dbe:
        result_dict['id'] = str(uuid.uuid4())
        result_dict['_db_error'] = str(dbe)

# ==============================================================================
# REST API: DOCUMENT MANAGEMENT & HISTORY
# ==============================================================================

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """Returns persistent document history with search, filters, and sorting."""
    q = request.args.get('q', '').strip()
    doc_type = request.args.get('doc_type', 'all')
    language = request.args.get('language', 'all')
    status = request.args.get('status', 'all')
    sort_order = request.args.get('sort', 'newest')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    docs = database.get_documents(
        query=q,
        doc_type=doc_type,
        language=language,
        verification_status=status,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    return jsonify({"documents": docs, "count": len(docs)})

@app.route('/api/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """Retrieves document record, full data payload, and version history."""
    doc = database.get_document_by_id(doc_id)
    if not doc:
        return jsonify({"error": "Document not found."}), 404
    return jsonify(doc)

@app.route('/api/documents/<doc_id>', methods=['PUT'])
def update_document(doc_id):
    """
    Updates document with User Corrected Data.
    Maintains separate versions and computes diff without overwriting original AI data.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "No JSON payload provided."}), 400
        
    data = payload.get('data')
    if data is None:
        return jsonify({"error": "Data object is required."}), 400
        
    existing = database.get_document_by_id(doc_id)
    if not existing:
        return jsonify({"error": "Document not found."}), 404
        
    # Re-run Verification Agent on edited data
    ver_report = verification.verify_document(existing['doc_type'], data)
    
    updated_doc = database.update_document_data(
        doc_id=doc_id,
        updated_data=data,
        changed_by="User",
        change_type="user_edit",
        version_label="👤 User Edited",
        verification_status=ver_report['status'],
        verification_report=ver_report
    )
    return jsonify(updated_doc)

@app.route('/api/documents/<doc_id>/verify', methods=['POST'])
def verify_document_endpoint(doc_id):
    """
    Marks document as Final Verified Data.
    Records Version 3 (or latest verified) and updates status to 'verified'.
    """
    payload = request.get_json(silent=True) or {}
    existing = database.get_document_by_id(doc_id)
    if not existing:
        return jsonify({"error": "Document not found."}), 404
        
    data = payload.get('data') or existing.get('user_corrected_data') or existing.get('ai_extracted_data')
    ver_report = verification.verify_document(existing['doc_type'], data)
    ver_report['status'] = 'verified'
    
    updated_doc = database.verify_and_save_document(
        doc_id=doc_id,
        verified_data=data,
        verification_report=ver_report
    )
    return jsonify(updated_doc)

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document_endpoint(doc_id):
    """Deletes document and its version history."""
    success = database.delete_document(doc_id)
    if not success:
        return jsonify({"error": "Document not found or delete failed."}), 404
    return jsonify({"success": True, "message": "Document deleted successfully."})

@app.route('/api/documents/<doc_id>/versions', methods=['GET'])
def get_document_versions(doc_id):
    """Returns full version timeline and diff comparisons."""
    doc = database.get_document_by_id(doc_id)
    if not doc:
        return jsonify({"error": "Document not found."}), 404
    return jsonify({
        "document_id": doc_id,
        "versions": doc.get('versions', []),
        "ai_extracted_data": doc.get('ai_extracted_data'),
        "user_corrected_data": doc.get('user_corrected_data'),
        "verified_data": doc.get('verified_data')
    })

@app.route('/api/documents/<doc_id>/feedback', methods=['POST'])
def save_feedback_endpoint(doc_id):
    """Saves user extraction accuracy feedback."""
    payload = request.get_json(silent=True) or {}
    success = database.save_document_feedback(doc_id, payload)
    return jsonify({"success": success})

@app.route('/api/document/verify-agent', methods=['POST'])
def run_verification_agent():
    """Directly triggers the Verification Agent on arbitrary document data."""
    payload = request.get_json(silent=True) or {}
    doc_type = payload.get('doc_type', 'other')
    data = payload.get('data', {})
    field_conf = payload.get('field_confidence', {})
    report = verification.verify_document(doc_type, data, field_conf)
    return jsonify(report)

@app.route('/api/document/ask', methods=['POST'])
def ask_document_endpoint():
    """Grounded Q&A: answers questions strictly from document context."""
    payload = request.get_json(silent=True) or {}
    question = payload.get('question', '').strip()
    data = payload.get('data', {})
    doc_type = payload.get('doc_type', 'other')
    
    if not question:
        return jsonify({"answer": "Please ask a question about the document."}), 400
        
    result = ai_services.ask_document_ai(data, doc_type, question)
    return jsonify(result)

@app.route('/api/document/summary', methods=['POST'])
def summary_endpoint():
    """Generates structured executive summary for document."""
    payload = request.get_json(silent=True) or {}
    data = payload.get('data', {})
    doc_type = payload.get('doc_type', 'other')
    doc_id = payload.get('doc_id')
    
    summary = ai_services.generate_document_summary(data, doc_type)
    if doc_id:
        database.save_document_summary(doc_id, summary)
    return jsonify(summary)

@app.route('/api/translate', methods=['POST'])
def translate_endpoint():
    """Translates document text fields to target language without altering original."""
    payload = request.get_json(silent=True) or {}
    data = payload.get('data', {})
    target_language = payload.get('target_language', 'English')
    translated = ai_services.translate_document_content(data, target_language)
    return jsonify({"original": data, "translated": translated, "target_language": target_language})

@app.route('/api/analytics', methods=['GET'])
def analytics_endpoint():
    """Returns analytics dashboard metrics."""
    metrics = database.get_analytics_metrics()
    return jsonify(metrics)

@app.route('/api/check-duplicate', methods=['POST'])
def check_duplicate_endpoint():
    """Checks if uploaded file hash or title already exists in history."""
    payload = request.get_json(silent=True) or {}
    file_hash = payload.get('file_hash')
    title = payload.get('title')
    doc_type = payload.get('doc_type')
    
    dup = database.find_duplicate_document(file_hash=file_hash, title=title, doc_type=doc_type)
    return jsonify({"is_duplicate": dup is not None, "match": dup})

# ==============================================================================
# EXPORT ROUTES (CALENDAR, CSV, EXCEL)
# ==============================================================================

@app.route('/export/ics', methods=['POST'])
def export_ics():
    """
    Exports structured Timetable or Notice to .ics.
    Defaults to Final Verified Data.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided."}), 400
        
        doc_type = payload.get('doc_type')
        # Default to verified_data if present, else data
        data = payload.get('verified_data') or payload.get('data', {})
        
        if not data:
            return jsonify({"error": "No document data found to export."}), 400
            
        ics_text, err = generate_docsnap_ics(doc_type, data)
        if err:
            return jsonify({"error": err}), 400
            
        if doc_type == 'timetable':
            title = data.get('title') or "Timetable Schedule"
            filename = f"timetable_{re.sub(r'[^a-zA-Z0-9_]+', '_', title.lower())[:30]}"
        elif doc_type in ('notice', 'poster'):
            title = data.get('title') or "Notice Event"
            filename = f"notice_{re.sub(r'[^a-zA-Z0-9_]+', '_', title.lower())[:30]}"
        else:
            filename = "docsnap_schedule"
            
        response = Response(ics_text, mimetype='text/calendar; charset=utf-8')
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}.ics"'
        return response
    except Exception as e:
        return jsonify({"error": f"Failed to generate calendar export: {str(e)}"}), 500

@app.route('/export/csv', methods=['POST'])
def export_csv():
    """
    Exports structured Receipt or Timetable data into clean CSV.
    Defaults to Final Verified Data.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided."}), 400
        
        doc_type = payload.get('doc_type', 'receipt')
        data = payload.get('verified_data') or payload.get('data', {})
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if doc_type == 'receipt':
            merchant = data.get('merchant') or "Receipt"
            date = data.get('date') or ""
            total = data.get('total') or ""
            currency = data.get('currency') or ""
            category = data.get('category') or ""
            items = data.get('items', [])
            
            writer.writerow(["Merchant", "Date", "Category", "Currency", "Item Name", "Quantity", "Price", "Total Amount"])
            if items:
                for item in items:
                    name = item.get('name') or ""
                    qty = item.get('qty', 1)
                    price = item.get('price', "")
                    writer.writerow([merchant, date, category, currency, name, qty, price, total])
            else:
                writer.writerow([merchant, date, category, currency, "General Expense", 1, total, total])
                
            safe_name = re.sub(r'[^a-zA-Z0-9_]+', '_', merchant.lower())[:30] or "receipt"
            filename = f"receipt_{safe_name}_{date or 'export'}.csv"
            
        elif doc_type == 'timetable':
            title = data.get('title') or "Timetable"
            entries = data.get('entries', [])
            writer.writerow(["Schedule Title", "Day", "Start Time", "End Time", "Subject", "Room / Lab", "Faculty"])
            for e in entries:
                writer.writerow([
                    title,
                    e.get('day', ''),
                    e.get('start_time', ''),
                    e.get('end_time', ''),
                    e.get('subject', ''),
                    e.get('room', ''),
                    e.get('faculty', '')
                ])
            safe_name = re.sub(r'[^a-zA-Z0-9_]+', '_', title.lower())[:30] or "timetable"
            filename = f"timetable_{safe_name}.csv"
        else:
            writer.writerow(["Field", "Value"])
            for k, v in data.items():
                writer.writerow([k, str(v)])
            filename = "docsnap_export.csv"
            
        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return jsonify({"error": f"Failed to generate CSV export: {str(e)}"}), 500

@app.route('/export/excel', methods=['POST'])
def export_excel():
    """
    Exports structured Receipt or Timetable data into styled Microsoft Excel (.xlsx).
    Uses openpyxl with formatted headers, alternating rows, and data summaries.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided."}), 400
            
        doc_type = payload.get('doc_type', 'receipt')
        data = payload.get('verified_data') or payload.get('data', {})
        export_mode = payload.get('version_type', 'verified')
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{doc_type.capitalize()} Data"
        
        # Styles
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Segoe UI", size=14, bold=True, color="1E1B4B")
        regular_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)
        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )
        
        if doc_type == 'receipt':
            merchant = data.get('merchant') or "Receipt"
            date = data.get('date') or ""
            total = data.get('total') or 0
            currency = data.get('currency') or "₹"
            category = data.get('category') or ""
            items = data.get('items', [])
            
            # Title
            ws.cell(row=1, column=1, value=f"{merchant} - Expense Report").font = title_font
            ws.cell(row=2, column=1, value=f"Date: {date} | Category: {category} | Exported via DocSnap ({export_mode.upper()} DATA)").font = regular_font
            
            headers = ["#", "Item Description", "Quantity", f"Unit Price ({currency})", f"Line Total ({currency})"]
            for col_idx, h in enumerate(headers, 1):
                c = ws.cell(row=4, column=col_idx, value=h)
                c.fill = header_fill
                c.font = header_font
                c.alignment = Alignment(horizontal="center" if col_idx in (1, 3) else ("right" if col_idx >= 4 else "left"))
                
            cur_row = 5
            for idx, item in enumerate(items, 1):
                name = item.get('name') or ""
                qty = item.get('qty', 1)
                price = item.get('price', 0)
                line_total = round(qty * price, 2)
                
                ws.cell(row=cur_row, column=1, value=idx).alignment = Alignment(horizontal="center")
                ws.cell(row=cur_row, column=2, value=name)
                ws.cell(row=cur_row, column=3, value=qty).alignment = Alignment(horizontal="center")
                ws.cell(row=cur_row, column=4, value=price).alignment = Alignment(horizontal="right")
                ws.cell(row=cur_row, column=5, value=line_total).alignment = Alignment(horizontal="right")
                
                for c_idx in range(1, 6):
                    cell = ws.cell(row=cur_row, column=c_idx)
                    cell.font = regular_font
                    cell.border = thin_border
                cur_row += 1
                
            # Total row
            ws.cell(row=cur_row, column=4, value="Total Amount:").font = bold_font
            ws.cell(row=cur_row, column=4).alignment = Alignment(horizontal="right")
            tot_cell = ws.cell(row=cur_row, column=5, value=total)
            tot_cell.font = bold_font
            tot_cell.alignment = Alignment(horizontal="right")
            tot_cell.border = thin_border
            
            safe_name = re.sub(r'[^a-zA-Z0-9_]+', '_', merchant.lower())[:30] or "receipt"
            filename = f"receipt_{safe_name}_{date or 'export'}.xlsx"
            
        elif doc_type == 'timetable':
            title = data.get('title') or "Class Timetable Schedule"
            entries = data.get('entries', [])
            
            ws.cell(row=1, column=1, value=title).font = title_font
            ws.cell(row=2, column=1, value=f"Weekly Class Schedule | Exported via DocSnap ({export_mode.upper()} DATA)").font = regular_font
            
            headers = ["#", "Day", "Start Time", "End Time", "Subject / Course", "Room / Lab", "Faculty / Instructor"]
            for col_idx, h in enumerate(headers, 1):
                c = ws.cell(row=4, column=col_idx, value=h)
                c.fill = header_fill
                c.font = header_font
                c.alignment = Alignment(horizontal="center" if col_idx in (1, 2, 3, 4) else "left")
                
            cur_row = 5
            for idx, e in enumerate(entries, 1):
                ws.cell(row=cur_row, column=1, value=idx).alignment = Alignment(horizontal="center")
                ws.cell(row=cur_row, column=2, value=e.get('day', '')).alignment = Alignment(horizontal="center")
                ws.cell(row=cur_row, column=3, value=e.get('start_time', '')).alignment = Alignment(horizontal="center")
                ws.cell(row=cur_row, column=4, value=e.get('end_time', '')).alignment = Alignment(horizontal="center")
                ws.cell(row=cur_row, column=5, value=e.get('subject', ''))
                ws.cell(row=cur_row, column=6, value=e.get('room', ''))
                ws.cell(row=cur_row, column=7, value=e.get('faculty', ''))
                
                for c_idx in range(1, 8):
                    cell = ws.cell(row=cur_row, column=c_idx)
                    cell.font = regular_font
                    cell.border = thin_border
                cur_row += 1
                
            safe_name = re.sub(r'[^a-zA-Z0-9_]+', '_', title.lower())[:30] or "timetable"
            filename = f"timetable_{safe_name}.xlsx"
        else:
            ws.cell(row=1, column=1, value="DocSnap Structured Data Export").font = title_font
            headers = ["Field", "Extracted Value"]
            for col_idx, h in enumerate(headers, 1):
                c = ws.cell(row=3, column=col_idx, value=h)
                c.fill = header_fill
                c.font = header_font
            cur_row = 4
            for k, v in data.items():
                ws.cell(row=cur_row, column=1, value=str(k)).font = bold_font
                ws.cell(row=cur_row, column=2, value=str(v)).font = regular_font
                cur_row += 1
            filename = "docsnap_export.xlsx"
            
        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
        out_buf = io.BytesIO()
        wb.save(out_buf)
        out_buf.seek(0)
        
        response = Response(
            out_buf.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel export: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    use_reloader = os.getenv('FLASK_USE_RELOADER', '0') == '1'
    print(f"Starting DocSnap server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=use_reloader)
