# DocSnap 📸 ➔ ⚡

> **Screenshots in. Structured data out.**  
> Hackathon-winning web application that converts screenshots and photos of **timetables**, **receipts**, and **notices/posters** into structured, editable data, then triggers one-click actions: **recurring weekly calendar sync (.ics)**, **event calendar export (.ics)**, or **itemized CSV spreadsheets**.

---

## 🌟 Key Features

- **Multimodal AI Vision Extraction**: Powered by **Google Gemini 2.5 Flash** via the official `google-genai` Python SDK. One single vision call performs document classification, multilingual OCR (English, Hindi हिंदी, Gujarati ગુજરાતી), and strict schema structuring.
- **Strict Anti-Hallucination & Confidence Scoring**:
  - The model never invents data, uses `null` for non-visible fields, and retains original text without translation.
  - Computes an overall confidence score and **per-field confidence scores**. Low-confidence fields (`< 0.70`) are highlighted with an amber border and a *"Please verify"* badge in the UI.
- **Split-View Visual Editor**:
  - **Left**: Document image viewer with pan, zoom controls (`-`, `+`, `100%`), and high-resolution inspection.
  - **Right**: Metadata badges (document type, detected language, confidence %), summary stat cards, and dynamic editable tables/forms.
  - **Live Two-Way Data Binding**: Edit any field, add rows, or delete rows.
  - **Interactive Raw JSON**: Live syntax-formatted JSON inspector with one-click **Copy JSON**.
- **Context-Aware Action Panel**:
  - **Timetable**: Exports recurring weekly calendar events (`RRULE:FREQ=WEEKLY`) for `Asia/Kolkata` timezone starting from the next occurrence of each weekday.
  - **Notice/Poster**: Exports a single, pinpoint calendar event (`.ics`) with venue and description.
  - **Receipt**: Exports an itemized CSV with columns for merchant, date, category, currency, item name, quantity, price, and total.
  - **Always uses your edited values**, ensuring 100% accuracy before syncing.
- **Multiple Ingestion Methods**:
  - Drag & drop zone with active drop styling.
  - Click to browse files (`.png`, `.jpg`, `.jpeg`, `.webp`, max 5MB).
  - **Direct clipboard paste (`Ctrl+V` / `Cmd+V`)**: Take a screenshot and paste directly!
  - **1-Click Curated Samples**: Built-in sample timetable, cafe receipt, and hackathon notice for instant zero-friction testing.
- **Premium SaaS Aesthetic**: Built with modern Inter typography, sleek indigo design tokens (`#4F46E5`), clean cards, rounded corners, responsive layout, accessible keyboard navigation, and smooth micro-animations.

---

## 📁 Project Architecture

```
Code_Wizards/
│
├── app.py                   # Flask backend (routes: GET /, POST /extract, POST /export/ics, POST /export/csv)
├── requirements.txt         # Python dependencies (flask, google-genai, python-dotenv, ics, pillow)
├── .env.example             # Template for environment configuration
├── .env                     # Local environment settings (GEMINI_API_KEY)
├── README.md                # Documentation & setup instructions
│
├── templates/
│   └── index.html           # Single-page application HTML5 interface
│
└── static/
    ├── style.css            # Custom CSS design system (Linear / Notion SaaS aesthetic)
    ├── app.js               # Reactive JavaScript client (stepper, zoom, two-way binding, exports)
    └── samples/             # Curated sample document images
        ├── sample_timetable.png
        ├── sample_receipt.png
        └── sample_notice.png
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.13)
- Google Gemini API key (obtainable free from [Google AI Studio](https://aistudio.google.com/))

### 2. Installation

Clone or open the repository folder, then install dependencies:

```bash
pip install -r requirements.txt
```

*(Or if using Python 3 launcher on Windows)*:
```bash
python -m pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example environment file to `.env`:

```bash
# On Linux / macOS / Git Bash:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```

Open `.env` and insert your Gemini API Key:

```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
PORT=5000
FLASK_DEBUG=1
```

> **Note on Demo Mode**: If `GEMINI_API_KEY` is not set yet, DocSnap includes a built-in demo mode for the 3 sample documents so you can immediately explore and test the UI, editor, ICS recurring calendar generator, and CSV exporter without waiting for an API key!

### 4. Run the Application

Start the Flask application:

```bash
python app.py
```

Then open your browser at:
👉 **`http://localhost:5000`**

---

## 🧪 Testing & Verification

1. **Test Timetable**: Click the **"Weekly Class Schedule"** sample or upload a photo of your college timetable.
   - Observe the 3-step animated processing stepper.
   - Inspect the extracted lecture entries, rooms, and professors.
   - Click **"Add to Calendar (.ics)"** to download the recurring weekly `.ics` calendar file.
2. **Test Receipt**: Click the **"Cafe & Bistro Receipt"** sample.
   - Notice the itemized table with prices and total calculation.
   - Click **"Export CSV"** to download the structured spreadsheet.
3. **Test Notice**: Click the **"Hackathon Event Notice"** sample.
   - Review event date, start/end time, venue, and description.
   - Click **"Add Event to Calendar (.ics)"**.
4. **Test Live Editing**: Modify any cell in the table or form; observe that the exported `.ics` or `.csv` reflects your edited values.

---

## 🛡️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the single-page web interface. |
| `POST` | `/extract` | Accepts `multipart/form-data` with `image` file (max 5MB). Returns detected `doc_type`, `language`, `confidence`, `field_confidence`, and structured `data`. |
| `POST` | `/export/ics` | Accepts edited JSON payload. Generates recurring weekly events for timetables or a single event for notices in `Asia/Kolkata` timezone. Returns `.ics` download. |
| `POST` | `/export/csv` | Accepts edited JSON payload for receipts. Returns itemized `.csv` download. |

---

## 🏆 Hackathon Winning Edge

- **Zero-Friction Ingestion**: Supports drag-and-drop, file browsing, clipboard paste (`Ctrl+V`), and instant 1-click sample loading.
- **Production-Grade Resilience**: Built-in 2-second retry mechanism on rate limits, defensive JSON cleaning for markdown fences, and schema validation.
- **Confidence-Aware UX**: Visually alerts users to verify any uncertain field, saving hours of manual data entry while maintaining 100% data integrity.
