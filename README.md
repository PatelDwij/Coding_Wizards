# DocSnap 📸 ➔ 🛡️ ➔ ⚡
### AI-Powered Document Vision, Verification & History Platform

> **"AI extracts. AI checks. Humans verify. The system remembers."**  
> DocSnap converts screenshots of **timetables**, **receipts**, **notices**, **posters**, and other documents into verified, audit-trailed structured data.  
> It features a dedicated **Verification Agent**, **field-level confidence scoring**, **visual cross-checking**, **multi-version history with diff tracking**, a grounded **Ask Your Document assistant**, and one-click exports to **recurring calendar sync (.ics)**, **Excel spreadsheets (.xlsx)**, and **CSV tables**.

---

## 🌟 Key Platform Capabilities

### 1. 🤖 Multimodal AI Vision Extraction
- Powered by **Google Gemini 3.8 Flash** with resilient automatic fallback.
- Ingests screenshots via **drag-and-drop**, **file browsing**, **clipboard paste (`Ctrl+V`)**, and **curated samples**.
- Automatic layout recognition, multilingual extraction (**English**, **Hindi हिंदी**, **Gujarati ગુજરાતી**), and schema mapping.

### 2. 🛡️ Dedicated Verification Agent
- Runs automated deterministic and domain-specific validation:
  - **Receipts**: Audits line-item arithmetic ($$\text{Qty} \times \text{Price} = \text{Total}$$) and flags discrepancies between line items and receipt total.
  - **Timetables**: Detects schedule conflicts, overlapping class intervals on the same day, invalid start/end sequences, and missing rooms.
  - **Notices & Posters**: Audits date validity, timing sequences, and required headline/venue fields.
  - **General**: Flags low-confidence fields ($< 70\%$) for mandatory user review.
- Generates an **Audit Score (0–100%)** and itemized list of passed checks, warnings, and errors.

### 3. 🎯 Field-Level Confidence Auditing
- Clear visual indicators for each extracted field:
  - 🟢 **High Confidence** ($> 85\%$)
  - 🟡 **Medium Confidence** ($70\% - 84\%$)
  - 🔴 **Low Confidence** ($< 70\%$) with *"⚠️ Please verify this field"* badge.
- Explicitly distinguished from actual accuracy: labeled as **AI Confidence**, not misleading "accuracy".

### 4. 👤 Human-in-the-Loop Verification Mode
- **Split-View Visual Workspace**:
  - **Left**: Original uploaded image viewer with pan, zoom controls (50% – 300%), and pixel-level inspection.
  - **Right**: Structured metadata, audit card, and dynamic editable tables/forms.
- **"Verify Against Image"**: One-click visual cross-checking mode that highlights low-confidence fields with an animated glowing indicator and scrolls directly to them.
- **Two-Way Data Binding**: Edit any field, add rows, or remove rows in real time.

### 5. 🕘 Multi-Version History & Diff Viewer
- **Never overwrites original AI data**:
  - **Version 1**: 🤖 AI Generated (initial baseline)
  - **Version 2**: 👤 User Edited (user corrections)
  - **Version 3**: ✅ Verified (final approved data)
- **Interactive Diff Comparison**: Shows field-by-field changes (e.g. `Room: 302 ➔ 210`) with visual before/after pills.

### 6. 💬 Grounded "Ask Your Document" Assistant
- Document-scoped AI assistant that answers questions **strictly from the document context**.
- Never hallucinates: if an answer is absent, clearly responds:  
  *"I couldn't find that information in this document."*
- Pre-populated quick suggestions for exams, room numbers, prices, deadlines, and venues.

### 7. 📝 Smart Summary Engine
- Instant executive summary generating:
  - 📌 **Important Points** (concise bullets)
  - 📅 **Event / Purchase Date**
  - ⏰ **Timings**
  - 📍 **Venue / Merchant**
  - ⚠️ **Deadline / Total Amount**
  - 👥 **Applicable Audience**

### 8. 🌐 Translation Without Data Loss
- Translates fields to **English**, **Hindi**, **Gujarati**, **Marathi**, **Bengali**, or **Tamil**.
- Side-by-side display preserving original text and schema.

### 9. 📁 Multi-Image Processing (Batch Upload)
- Select multiple files simultaneously.
- Queue manager displays progress (*"Processing 2 of 5..."*) and summarizes verified vs. review-needed documents.

### 10. ⚠️ Duplicate & Sensitive Data (PII) Protection
- **Duplicate Detection**: Identifies matching documents in history by SHA-256 hash or title/date and alerts user with options to view existing or re-process.
- **Sensitive Data Scanner**: Detects phone numbers, emails, government IDs (PAN/Aadhaar), and payment cards, displaying safety warnings.

### 11. 📊 Analytics Dashboard & Persistent Storage
- Persistent storage backed by **SQLite** (`docsnap.db`) with zero external infrastructure required.
- Dashboard tracks **Documents Processed**, **Verified Count**, **Correction Rate**, **Needs Review Count**, and **Document Type Breakdown**.

### 12. 📤 Multi-Format Export Center
- **Calendar (.ics)**: Recurring weekly events (`RRULE:FREQ=WEEKLY`) in `Asia/Kolkata` timezone for timetables; single event for notices.
- **Excel Spreadsheet (.xlsx)**: Formatted workbooks with styled headers and calculations using `openpyxl`.
- **CSV Table (.csv)**: Itemized spreadsheets for accounting.
- **Structured JSON (.json)**: Clean JSON export.
- **Print / PDF**: Clean printable document view.
- Defaults to **Final Verified Data** with toggle for original AI data.

---

## 📁 Project Architecture

```
Code_Wizards/
├── app.py                   # Flask backend (API routes & server orchestration)
├── database.py              # SQLite persistence (documents, versioning, diff, analytics)
├── verification.py          # Deterministic Verification Agent (math, conflicts, dates)
├── sensitive_data.py        # PII detection (phones, emails, IDs, cards)
├── ai_services.py           # Grounded Q&A assistant, smart summary, and translation
├── requirements.txt         # Dependencies (Flask, google-genai, ics, pillow, openpyxl)
├── .env.example             # Environment configuration template
├── .env                     # Local settings (GEMINI_API_KEY, PORT)
├── vercel.json              # Vercel deployment configuration
├── api/
│   └── index.py             # Vercel serverless entry point
├── templates/
│   └── index.html           # Single-page web application interface
└── static/
    ├── style.css            # Design system (Indigo SaaS, cards, modals, diff tables)
    ├── app.js               # Client controller (verification, zoom, history, chat, export)
    └── samples/             # Curated sample document images
        ├── sample_timetable.png
        ├── sample_receipt.png
        └── sample_notice.png
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.13)
- Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))

### 2. Installation

```bash
git clone https://github.com/PatelDwij/Coding_Wizards.git
cd Coding_Wizards
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env`:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Set your Gemini API key in `.env`:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
PORT=5000
FLASK_DEBUG=1
```

> **Demo Mode**: If no Gemini API key is configured, DocSnap automatically falls back to instant offline demo mode for the 3 curated sample documents so you can explore the verification workflow immediately!

### 4. Run the Application

```bash
python app.py
```

Open your browser at:  
👉 **`http://localhost:5000`**

---

## 🧪 Testing the Complete Workflow

1. **Upload / Select Sample**: Click **"Weekly Class Schedule"** or upload a timetable.
2. **AI Extraction & Classification**: Observes automated vision extraction and document classification.
3. **Verification Agent Audit**: Inspect the Verification Agent card showing conflict checks and audit score.
4. **"Verify Against Image"**: Click the button to inspect the original screenshot alongside extracted values.
5. **Human Correction**: Edit a course room (e.g. change `Room 302` to `Room 210`). Notice status updates to *"👤 User Edited"*.
6. **Verify & Save**: Click **"Verify & Save"** to finalize the document. Status turns 🟢 **Verified**.
7. **Version History**: Click **"Version History"** to inspect Version 1 (AI) vs Version 3 (Verified) with diff comparison.
8. **Ask Your Document**: Click **"Ask Document"** and ask *"Where is the DSA lecture?"*.
9. **Smart Summary**: Click **"Smart Summary"** to view structured highlights and copy them.
10. **Export**: Export as **Calendar (.ics)**, **Excel (.xlsx)**, or **CSV**.
11. **History Page**: Navigate to **History** to search, filter, or re-open the document.

---

## 🛡️ REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the web application. |
| `POST` | `/extract` | Uploads screenshot image; runs AI extraction, verification agent, PII scan, and saves to database. |
| `GET` | `/extract/status` | Real-time status for Gemini retries and backoff. |
| `GET` | `/api/documents` | Lists historical documents with search, type/status/language filters, and sorting. |
| `GET` | `/api/documents/<id>` | Retrieves document record and full version history. |
| `PUT` | `/api/documents/<id>` | Saves user edits as Version 2 without overwriting original AI baseline. |
| `POST` | `/api/documents/<id>/verify` | Confirms document as Final Verified Data (Version 3). |
| `DELETE` | `/api/documents/<id>` | Deletes document and its version history. |
| `GET` | `/api/documents/<id>/versions` | Retrieves version timeline and field diffs. |
| `POST` | `/api/documents/<id>/feedback` | Records user extraction accuracy feedback (👍/👎). |
| `POST` | `/api/document/verify-agent` | Runs deterministic Verification Agent checks. |
| `POST` | `/api/document/ask` | Grounded Q&A answering strictly from document context. |
| `POST` | `/api/document/summary` | Generates structured summary points. |
| `POST` | `/api/translate` | Translates document fields preserving original data. |
| `GET` | `/api/analytics` | Returns throughput, verification rate, and type distribution metrics. |
| `POST` | `/api/check-duplicate` | Checks for duplicate documents by file hash or title. |
| `POST` | `/export/ics` | Exports recurring weekly (.ics) calendar events in `Asia/Kolkata` timezone. |
| `POST` | `/export/excel` | Exports styled Microsoft Excel (.xlsx) workbook. |
| `POST` | `/export/csv` | Exports itemized CSV spreadsheet. |

---

## 🌐 Deployment (Vercel)

The repository includes `vercel.json` and `api/index.py` configured for Vercel Serverless Functions:
1. Connect your repository to Vercel.
2. Set the `GEMINI_API_KEY` Environment Variable in Vercel Project Settings.
3. Deploy!
