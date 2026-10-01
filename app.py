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
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from dotenv import load_dotenv
from PIL import Image, ImageOps

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
TIMEZONE_KOLKATA = zoneinfo.ZoneInfo("Asia/Kolkata")

# In-memory cache for extraction results by SHA-256 image hash
EXTRACTION_CACHE = {}

# Current status for UI retry notifications
CURRENT_RETRY_STATUS = ""


# Predefined curated mock responses for built-in sample images for instant demo testing
SAMPLE_MOCKS = {
    "timetable": {
        "doc_type": "timetable",
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

# Pre-cache built-in samples by image hash so demo testing is instant and reliable
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
  "doc_type": "timetable" | "receipt" | "notice" | "unknown",
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

- If doc_type is "notice":
  "data": {
    "title": "Notice/Event headline",
    "date": "YYYY-MM-DD" or null,
    "start_time": "HH:MM" or null,
    "end_time": "HH:MM" or null,
    "venue": "Event location/venue or null",
    "description": "Concise summary of event/notice details"
  }

CRITICAL RULES:
- Never hallucinate or invent values. Use null for any details not clearly visible.
- Support English, Hindi (हिंदी), and Gujarati (ગુજરાતી) text accurately.
- DO NOT TRANSLATE; preserve the original text and spelling exactly as seen in the image.
- Provide a confidence score between 0.0 and 1.0 for each extracted field in "field_confidence".
- If the image is not a timetable, receipt, or notice, set "doc_type" to "unknown" and "data" to null.
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

def is_retryable_error(err):
    """
    Checks if an API error is a retryable 503, 429, or timeout error.
    """
    code = getattr(err, 'code', None) or getattr(err, 'status_code', None)
    if code in (429, 503, 504):
        return True
    err_str = str(err).lower()
    if "503" in err_str or "unavailable" in err_str:
        return True
    if "429" in err_str or "resource_exhausted" in err_str or "rate limit" in err_str or "quota" in err_str or "too many requests" in err_str:
        return True
    if "timeout" in err_str or "timed out" in err_str or "deadline" in err_str or "504" in err_str:
        return True
    if isinstance(err, (TimeoutError,)):
        return True
    return False

def generate_docsnap_ics(doc_type, data):
    """
    Generates an RFC 5545 compliant .ics calendar string with:
    - DTSTAMP on every VEVENT
    - CRLF (\\r\\n) line endings
    - TZID=Asia/Kolkata with a standard VTIMEZONE block
    - X-WR-CALNAME:DocSnap Timetable
    - For recurring timetable classes, starts on the next upcoming occurrence of each weekday.
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
        s = str(text)
        s = s.replace('\\', '\\\\')
        s = s.replace(';', '\\;')
        s = s.replace(',', '\\,')
        s = s.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
        return s
    
    weekday_map = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6
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
            
            # Start on the next upcoming occurrence of its weekday
            if days_ahead == 0 and start_dt <= now:
                start_dt += datetime.timedelta(days=7)
                
            end_dt = datetime.datetime(start_dt.year, start_dt.month, start_dt.day, eh, em, tzinfo=TIMEZONE_KOLKATA)
            if end_dt <= start_dt:
                end_dt = start_dt + datetime.timedelta(hours=1)
                
            dtstart_val = start_dt.strftime("%Y%m%dT%H%M%S")
            dtend_val = end_dt.strftime("%Y%m%dT%H%M%S")
            
            summary = f"{subject} ({room})" if room else subject
            desc_items = []
            if faculty:
                desc_items.append(f"Faculty: {faculty}")
            if room:
                desc_items.append(f"Room: {room}")
            description = " | ".join(desc_items)
            
            event_uid = f"timetable-{idx}-{int(start_dt.timestamp())}-{uuid.uuid4().hex[:8]}@docsnap"
            
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{event_uid}")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"SUMMARY:{escape_ics(summary)}")
            if description:
                lines.append(f"DESCRIPTION:{escape_ics(description)}")
            if room:
                lines.append(f"LOCATION:{escape_ics(room)}")
            lines.append(f"DTSTART;TZID=Asia/Kolkata:{dtstart_val}")
            lines.append(f"DTEND;TZID=Asia/Kolkata:{dtend_val}")
            lines.append("RRULE:FREQ=WEEKLY")
            lines.append("END:VEVENT")
            
    elif doc_type == 'notice':
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
        if description:
            lines.append(f"DESCRIPTION:{escape_ics(description)}")
        if venue:
            lines.append(f"LOCATION:{escape_ics(venue)}")
        lines.append(f"DTSTART;TZID=Asia/Kolkata:{dtstart_val}")
        lines.append(f"DTEND;TZID=Asia/Kolkata:{dtend_val}")
        lines.append("END:VEVENT")
    else:
        return None, f"Export to ICS is not supported for document type '{doc_type}'."
        
    lines.append("END:VCALENDAR")
    
    # Strictly join with CRLF line endings
    ics_text = "\r\n".join(lines) + "\r\n"
    return ics_text, None

@app.route('/')
def index():
    """Serves the DocSnap web interface with retry status polling."""
    rendered = render_template('index.html')
    status_script = """
<script>
(function() {
  const defaultSubtitle = "Performing one-shot OCR, classification, and schema extraction...";
  setInterval(async () => {
    try {
      const procScreen = document.getElementById('screen-processing');
      const sub = document.querySelector('.processing-subtitle');
      if (procScreen && !procScreen.classList.contains('hidden')) {
        const res = await fetch('/extract/status');
        if (res.ok) {
          const data = await res.json();
          if (sub && data.status) {
            sub.textContent = data.status;
          }
        }
      } else if (sub && sub.textContent && sub.textContent.startsWith('Gemini is busy')) {
        sub.textContent = defaultSubtitle;
      }
    } catch (e) {}
  }, 300);
})();
</script>
</body>
"""
    return rendered.replace('</body>', status_script)

@app.route('/extract/status', methods=['GET'])
def extract_status():
    """Returns the current Gemini retry status for real-time UI updates."""
    global CURRENT_RETRY_STATUS
    return jsonify({"status": CURRENT_RETRY_STATUS})

@app.route('/static/samples/<filename>')
def serve_sample(filename):
    """Serves sample image files."""
    return send_from_directory('static/samples', filename)

@app.route('/extract', methods=['POST'])
def extract_document():
    """
    Accepts an uploaded image, sends it to Gemini AI (gemini-2.5-flash with fallback to gemini-2.5-flash-lite),
    and returns detected doc_type and structured JSON data.
    Retries up to 4 times on 503, 429, and timeouts with exponential backoff (2s, 4s, 8s, 16s).
    Shows retry status in UI, resizes images > 2000px, and caches results by image hash.
    """
    global CURRENT_RETRY_STATUS, EXTRACTION_CACHE
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided in request."}), 400
    
    file = request.files['image']
    raw_filename = file.filename or 'upload.png'
    if '.' not in raw_filename:
        filename = f"{raw_filename}.png"
    else:
        filename = raw_filename
    
    if not allowed_file(filename):
        return jsonify({"error": "Invalid file format. Supported formats are PNG, JPG, JPEG, and WEBP."}), 400
    
    raw_image_bytes = file.read()
    if len(raw_image_bytes) > 5 * 1024 * 1024:
        return jsonify({"error": "Image file exceeds the 5MB size limit. Please upload a smaller image."}), 400
    
    # 1. Cache lookup by image hash
    raw_image_hash = hashlib.sha256(raw_image_bytes).hexdigest()
    if raw_image_hash in EXTRACTION_CACHE:
        return jsonify(EXTRACTION_CACHE[raw_image_hash])
    
    # Validate image integrity with PIL
    try:
        pil_img = Image.open(io.BytesIO(raw_image_bytes))
        pil_img.verify()
        pil_img = Image.open(io.BytesIO(raw_image_bytes))
    except Exception:
        return jsonify({"error": "Corrupted or invalid image file. Please upload a valid image."}), 400
    
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass
    
    # 2. Resize images larger than 2000px on the longest side before sending
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
            if pil_img.mode in ('RGBA', 'LA', 'P'):
                pil_img = pil_img.convert('RGB')
            pil_img.save(out_buf, format='JPEG', quality=90)
            mime_type = 'image/jpeg'
        elif fmt == 'PNG':
            pil_img.save(out_buf, format='PNG')
            mime_type = 'image/png'
        elif fmt == 'WEBP':
            pil_img.save(out_buf, format='WEBP', quality=90)
            mime_type = 'image/webp'
        else:
            if pil_img.mode in ('RGBA', 'LA', 'P'):
                pil_img = pil_img.convert('RGB')
            pil_img.save(out_buf, format='JPEG', quality=90)
            mime_type = 'image/jpeg'
        image_bytes = out_buf.getvalue()
    else:
        fmt = (pil_img.format or 'JPEG').lower()
        mime_type = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
        image_bytes = raw_image_bytes

    resized_image_hash = hashlib.sha256(image_bytes).hexdigest()
    if resized_image_hash in EXTRACTION_CACHE:
        return jsonify(EXTRACTION_CACHE[resized_image_hash])
    
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    
    # Check if this is a sample image request or sample filename
    filename_lower = filename.lower()
    is_sample_timetable = 'sample_timetable' in filename_lower
    is_sample_receipt = 'sample_receipt' in filename_lower
    is_sample_notice = 'sample_notice' in filename_lower
    
    # If no valid API key is configured
    if not api_key or api_key == 'your_gemini_api_key_here':
        if is_sample_timetable:
            mock = dict(SAMPLE_MOCKS["timetable"])
            mock["_demo_mode"] = True
            mock["_note"] = "Extracted using DocSnap sample demo mode. To process custom images with live AI, add GEMINI_API_KEY in .env."
            EXTRACTION_CACHE[raw_image_hash] = mock
            EXTRACTION_CACHE[resized_image_hash] = mock
            return jsonify(mock)
        elif is_sample_receipt:
            mock = dict(SAMPLE_MOCKS["receipt"])
            mock["_demo_mode"] = True
            mock["_note"] = "Extracted using DocSnap sample demo mode. To process custom images with live AI, add GEMINI_API_KEY in .env."
            EXTRACTION_CACHE[raw_image_hash] = mock
            EXTRACTION_CACHE[resized_image_hash] = mock
            return jsonify(mock)
        elif is_sample_notice:
            mock = dict(SAMPLE_MOCKS["notice"])
            mock["_demo_mode"] = True
            mock["_note"] = "Extracted using DocSnap sample demo mode. To process custom images with live AI, add GEMINI_API_KEY in .env."
            EXTRACTION_CACHE[raw_image_hash] = mock
            EXTRACTION_CACHE[resized_image_hash] = mock
            return jsonify(mock)
        else:
            return jsonify({
                "error": "GEMINI_API_KEY is not configured in .env. Please set your Gemini API key in the .env file to enable live AI vision extraction."
            }), 400
    
    # 3. Gemini retry and fallback strategy
    # Try gemini-2.5-flash first; if it still fails, fall back to gemini-2.5-flash-lite (with gemini-3.8-flash safeguard)
    MODELS_TO_TRY = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.8-flash"]
    BACKOFF_DELAYS = [2, 4, 8, 16]
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        last_error = None
        result_json = None
        CURRENT_RETRY_STATUS = ""
        
        for model_name in MODELS_TO_TRY:
            # 1 initial attempt + up to 4 retries with exponential backoff [2, 4, 8, 16]
            for attempt in range(len(BACKOFF_DELAYS) + 1):
                if attempt > 0:
                    delay = BACKOFF_DELAYS[attempt - 1]
                    CURRENT_RETRY_STATUS = f"Gemini is busy, retrying ({attempt}/4)..."
                    time.sleep(delay)
                    
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            "Extract and structure this document into JSON strictly following the system instructions."
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.1,
                            response_mime_type="application/json"
                        )
                    )
                    
                    raw_text = response.text or ""
                    cleaned = clean_json_text(raw_text)
                    
                    try:
                        result_json = json.loads(cleaned)
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
                    
                    # If model not found (404) or deprecated, immediately switch to next model without delay
                    if "404" in err_str or "not_found" in err_str or "no longer available" in err_str:
                        CURRENT_RETRY_STATUS = ""
                        break
                        
                    # Retry up to 4 times on 503, 429, and timeouts
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
        
        if result_json is None:
            # Fallback for sample images if live Gemini quota is exhausted after retries
            if is_sample_timetable:
                mock = dict(SAMPLE_MOCKS["timetable"])
                mock["_demo_mode"] = True
                mock["_note"] = "Gemini quota reached. Loaded sample timetable."
                EXTRACTION_CACHE[raw_image_hash] = mock
                EXTRACTION_CACHE[resized_image_hash] = mock
                return jsonify(mock)
            elif is_sample_receipt:
                mock = dict(SAMPLE_MOCKS["receipt"])
                mock["_demo_mode"] = True
                mock["_note"] = "Gemini quota reached. Loaded sample receipt."
                EXTRACTION_CACHE[raw_image_hash] = mock
                EXTRACTION_CACHE[resized_image_hash] = mock
                return jsonify(mock)
            elif is_sample_notice:
                mock = dict(SAMPLE_MOCKS["notice"])
                mock["_demo_mode"] = True
                mock["_note"] = "Gemini quota reached. Loaded sample notice."
                EXTRACTION_CACHE[raw_image_hash] = mock
                EXTRACTION_CACHE[resized_image_hash] = mock
                return jsonify(mock)
                
            return jsonify({
                "error": f"Failed to process document with Gemini AI after retry: {last_error}"
            }), 502
            
        # Ensure confidence scores exist
        if 'confidence' not in result_json or not isinstance(result_json['confidence'], (int, float)):
            result_json['confidence'] = 0.95
        if 'field_confidence' not in result_json or not isinstance(result_json['field_confidence'], dict):
            result_json['field_confidence'] = {}
            
        # Check if model detected image as not a valid document
        if result_json.get('doc_type') == 'unknown' or not result_json.get('data'):
            return jsonify({
                "error": "The uploaded image does not appear to be a timetable, receipt, or notice. Please upload a clear document photo or screenshot."
            }), 422
            
        # Cache successful extraction by image hash
        EXTRACTION_CACHE[raw_image_hash] = result_json
        EXTRACTION_CACHE[resized_image_hash] = result_json
        
        return jsonify(result_json)
        
    except Exception as e:
        CURRENT_RETRY_STATUS = ""
        return jsonify({
            "error": f"An unexpected error occurred during extraction: {str(e)}"
        }), 500
    finally:
        CURRENT_RETRY_STATUS = ""

@app.route('/export/ics', methods=['POST'])
def export_ics():
    """
    Exports structured Timetable (recurring weekly events) or Notice (single event)
    to a downloadable RFC 5545 .ics file in timezone Asia/Kolkata.
    Includes DTSTAMP on every VEVENT, CRLF line endings, VTIMEZONE block for Asia/Kolkata,
    and X-WR-CALNAME:DocSnap Timetable.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided."}), 400
        
        doc_type = payload.get('doc_type')
        data = payload.get('data', {})
        
        if not data:
            return jsonify({"error": "No document data found to export."}), 400
            
        ics_text, err = generate_docsnap_ics(doc_type, data)
        if err:
            return jsonify({"error": err}), 400
            
        if doc_type == 'timetable':
            title = data.get('title') or "Timetable Schedule"
            filename = f"timetable_{re.sub(r'[^a-zA-Z0-9_]+', '_', title.lower())[:30]}"
        elif doc_type == 'notice':
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
    Exports structured Receipt data into a clean CSV format
    with one row per item plus merchant, date, total, and category.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided."}), 400
        
        data = payload.get('data', {})
        merchant = data.get('merchant') or "Receipt"
        date = data.get('date') or ""
        total = data.get('total') or ""
        currency = data.get('currency') or ""
        category = data.get('category') or ""
        items = data.get('items', [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            "Merchant",
            "Date",
            "Category",
            "Currency",
            "Item Name",
            "Quantity",
            "Price",
            "Total Amount"
        ])
        
        if items:
            for item in items:
                name = item.get('name') or ""
                qty = item.get('qty', 1)
                price = item.get('price', "")
                writer.writerow([merchant, date, category, currency, name, qty, price, total])
        else:
            writer.writerow([merchant, date, category, currency, "General Expense", 1, total, total])
            
        safe_merchant = re.sub(r'[^a-zA-Z0-9_]+', '_', merchant.lower())[:30] or "receipt"
        filename = f"receipt_{safe_merchant}_{date or 'export'}.csv"
        
        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate CSV export: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    use_reloader = os.getenv('FLASK_USE_RELOADER', '0') == '1'
    print(f"Starting DocSnap server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=use_reloader)


