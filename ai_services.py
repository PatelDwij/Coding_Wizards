import os
import json
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_gemini_client():
    """Instantiates Google GenAI client if GEMINI_API_KEY is configured."""
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key == 'your_gemini_api_key_here':
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def _re_word_match(word: str, text: str) -> bool:
    """Matches a whole word/acronym in a text string."""
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE))

def ask_document_ai(document_data: Dict[str, Any], doc_type: str, question: str) -> Dict[str, Any]:
    """
    Answers a user question grounded STRICTLY in the extracted document context.
    If the requested information cannot be found:
    'I couldn't find that information in this document.'
    """
    if not question or not str(question).strip():
        return {"answer": "Please ask a specific question about this document."}
        
    doc_json_str = json.dumps(document_data, indent=2, ensure_ascii=False)
    client = get_gemini_client()
    
    if client:
        try:
            from google.genai import types
            prompt = f"""You are DocSnap AI Document Assistant.
You have access to the following extracted structured document context:
{doc_json_str}

USER QUESTION: {question}

CONSTRAINTS:
1. Answer the question accurately using ONLY the document context above. Recognize common abbreviations/acronyms (e.g., DSA = Data Structures & Algorithms, CN = Computer Networks, OS = Operating Systems, DBMS = Database Management Systems).
2. If the user asks where, when, who, how much, or what is in the document, extract the exact corresponding details (rooms, timings, faculty, prices, totals, dates).
3. Be clear, complete, and direct (1-3 sentences). Do NOT cut off mid-sentence.
4. If the requested information is genuinely not present in the document context, respond with:
"I couldn't find that information in this document." """

            models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
            for model_name in models_to_try:
                try:
                    try:
                        # gemini-3.5-flash benefits from thinking_budget=0 for instant, untruncated answers
                        cfg = types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=1500,
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=cfg
                        )
                    except Exception:
                        cfg = types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=1500
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=cfg
                        )
                        
                    ans = response.text.strip()
                    if ans:
                        return {"answer": ans, "model": model_name}
                except Exception:
                    continue
        except Exception:
            pass
            
    # Deterministic fallback search over document data
    q_lower = question.lower()
    
    # Common academic & technical acronym map
    ACRONYM_MAP = {
        'dsa': ['data structures', 'dsa', 'algorithm'],
        'cn': ['computer networks', 'networking', 'cn'],
        'os': ['operating system', 'os'],
        'dbms': ['database', 'dbms', 'sql'],
        'ai': ['artificial intelligence', 'ai'],
        'ml': ['machine learning', 'ml'],
        'wt': ['web technology', 'web tech', 'web development', 'wt'],
        'toc': ['theory of computation', 'automata', 'toc'],
        'coa': ['computer organization', 'architecture', 'coa'],
        'se': ['software engineering', 'se'],
        'maths': ['mathematics', 'math', 'discrete'],
        'math': ['mathematics', 'math', 'discrete']
    }
    
    if doc_type == 'timetable':
        entries = document_data.get('entries', [])
        
        # 1. Day-specific queries (e.g., "Monday", "What classes on Friday?")
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for d in days:
            if _re_word_match(d, q_lower):
                day_entries = [e for e in entries if str(e.get('day', '')).lower() == d]
                if day_entries:
                    desc_list = [f"{e.get('subject', 'Class')} ({e.get('start_time')}-{e.get('end_time')} in {e.get('room', 'N/A')})" for e in day_entries]
                    return {"answer": f"Classes on {d.capitalize()}: {'; '.join(desc_list)}."}

        # 2. Match subject by acronym or keyword
        matched_entries = []
        matched_subject_name = ""
        
        for acr, syns in ACRONYM_MAP.items():
            if _re_word_match(acr, q_lower):
                for e in entries:
                    s_name = str(e.get('subject', '')).lower()
                    if any(syn in s_name for syn in syns):
                        matched_entries.append(e)
                        matched_subject_name = e.get('subject')
                if matched_entries:
                    break
                    
        if not matched_entries:
            for e in entries:
                s_name = str(e.get('subject', '')).lower()
                words = [w for w in s_name.replace('&', ' ').replace('-', ' ').split() if len(w) > 2]
                if s_name in q_lower or any(_re_word_match(w, q_lower) for w in words):
                    matched_entries.append(e)
                    matched_subject_name = e.get('subject')

        if matched_entries:
            subj = matched_subject_name or matched_entries[0].get('subject', 'Subject')
            if any(w in q_lower for w in ['where', 'room', 'hall', 'venue', 'location', 'lab']):
                loc_list = [f"{e.get('room', 'N/A')} on {e.get('day')} ({e.get('start_time')}-{e.get('end_time')})" for e in matched_entries]
                return {"answer": f"{subj} is held in {', and in '.join(loc_list)}."}
            elif any(w in q_lower for w in ['when', 'time', 'timing', 'schedule', 'day', 'slot']):
                time_list = [f"{e.get('day')} from {e.get('start_time')} to {e.get('end_time')} in {e.get('room', 'N/A')}" for e in matched_entries]
                return {"answer": f"{subj} is scheduled on {', and on '.join(time_list)}."}
            elif any(w in q_lower for w in ['who', 'faculty', 'professor', 'teacher', 'instructor', 'teach']):
                facs = list(dict.fromkeys([e.get('faculty') for e in matched_entries if e.get('faculty')]))
                fac_str = ', '.join(facs) if facs else "the assigned department faculty"
                return {"answer": f"{subj} is taught by {fac_str}."}
            else:
                details = [f"{e.get('day')} {e.get('start_time')}-{e.get('end_time')} in {e.get('room', 'N/A')}" for e in matched_entries]
                return {"answer": f"{subj} is scheduled as follows: {', '.join(details)}."}

        # 3. Timetable general field queries
        if any(w in q_lower for w in ['room', 'rooms', 'where']):
            rooms = list(dict.fromkeys([e.get('room') for e in entries if e.get('room')]))
            return {"answer": f"Rooms listed in this schedule: {', '.join(rooms)}." if rooms else "No specific room numbers listed."}
        if any(w in q_lower for w in ['faculty', 'professor', 'professors', 'teacher', 'teachers', 'who']):
            facs = list(dict.fromkeys([e.get('faculty') for e in entries if e.get('faculty')]))
            return {"answer": f"Faculty members mentioned: {', '.join(facs)}." if facs else "No faculty names listed."}
        if any(w in q_lower for w in ['subject', 'subjects', 'courses', 'classes']):
            subs = list(dict.fromkeys([e.get('subject') for e in entries if e.get('subject')]))
            return {"answer": f"Subjects in this timetable: {', '.join(subs)}."}
            
    elif doc_type == 'receipt':
        curr = document_data.get('currency', '₹')
        tot = document_data.get('total')
        subtot = document_data.get('subtotal')
        tax = document_data.get('tax')
        
        # 1. Total / bill / cost
        if any(w in q_lower for w in ['total', 'how much', 'bill', 'amount', 'cost', 'pay', 'paid']):
            ans = f"The total amount on this receipt is {curr} {tot}."
            if subtot is not None:
                ans += f" (Subtotal: {curr} {subtot}"
                if tax is not None:
                    ans += f", Tax: {curr} {tax}"
                ans += ")"
            return {"answer": ans}
            
        # 2. Tax / GST / VAT
        if any(w in q_lower for w in ['tax', 'gst', 'vat']):
            if tax is not None:
                rate = document_data.get('tax_rate', '')
                rate_str = f" ({rate}%)" if rate else ""
                return {"answer": f"The tax amount is {curr} {tax}{rate_str}."}
            return {"answer": f"No separate tax amount is itemized on this receipt."}
            
        # 3. Merchant / store
        if any(w in q_lower for w in ['merchant', 'store', 'shop', 'where', 'cafe', 'restaurant', 'seller', 'vendor']):
            m = document_data.get('merchant', 'Store')
            addr = document_data.get('address')
            ans = f"The merchant name is {m}."
            if addr:
                ans += f" Address: {addr}."
            return {"answer": ans}
            
        # 4. Date
        if any(w in q_lower for w in ['date', 'when', 'day', 'time']):
            d = document_data.get('date', 'N/A')
            return {"answer": f"The receipt date is {d}."}
            
        # 5. Items
        items = document_data.get('items', [])
        # Check if asking about a specific item
        for itm in items:
            name = str(itm.get('name', '')).lower()
            if name and any(part in q_lower for part in name.split() if len(part) > 3):
                return {"answer": f"{itm.get('name')}: {itm.get('qty', 1)}x @ {curr} {itm.get('price')} (Total: {curr} {float(itm.get('qty', 1)) * float(itm.get('price', 0)):.2f})."}
                
        if any(w in q_lower for w in ['items', 'order', 'list', 'what was bought', 'products', 'bought']):
            if items:
                names = [f"{i.get('qty', 1)}x {i.get('name')} ({curr} {i.get('price')})" for i in items if i.get('name')]
                return {"answer": f"Items on receipt: {', '.join(names)}."}
            return {"answer": "No individual line items listed."}
            
    elif doc_type in ('notice', 'poster'):
        title = document_data.get('title', 'Notice')
        date_val = document_data.get('date')
        st = document_data.get('start_time')
        et = document_data.get('end_time')
        venue = document_data.get('venue')
        desc = document_data.get('description', '')
        
        if any(w in q_lower for w in ['when', 'date', 'time', 'timing', 'schedule']):
            time_part = f" from {st} to {et}" if (st and et) else (f" at {st}" if st else "")
            return {"answer": f"The event is on {date_val or 'the scheduled date'}{time_part}."}
        if any(w in q_lower for w in ['venue', 'where', 'location', 'hall', 'room', 'auditorium', 'place']):
            return {"answer": f"The venue is {venue}." if venue else "No venue is explicitly specified in this notice."}
        if any(w in q_lower for w in ['title', 'what is this', 'about', 'summary', 'topic', 'headline']):
            return {"answer": f"{title}: {desc}" if desc else f"Headline: {title}."}
        if any(w in q_lower for w in ['fee', 'registration', 'cost', 'prize', 'deadline']):
            extra = document_data.get('registration_deadline') or document_data.get('fee') or document_data.get('prizes')
            if extra:
                return {"answer": f"Information found: {extra}."}
                
    # 4. Broad scan across all string/number fields in document_data
    for k, v in document_data.items():
        if isinstance(v, (str, int, float)) and v:
            k_clean = k.replace('_', ' ').lower()
            if any(w in q_lower for w in k_clean.split()):
                return {"answer": f"{k.replace('_', ' ').title()}: {v}."}
                
    return {"answer": "I couldn't find that information in this document."}

def generate_document_summary(document_data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    """
    Generates a structured executive summary with:
    - important_points
    - date
    - time
    - venue / merchant
    - deadline / total
    - applicable_users / audience
    """
    client = get_gemini_client()
    doc_json_str = json.dumps(document_data, indent=2, ensure_ascii=False)
    
    if client:
        try:
            from google.genai import types
            prompt = f"""You are the DocSnap Smart Summary Engine.
Summarize the following document into a concise JSON object:
{doc_json_str}

OUTPUT CONSTRAINTS:
Return ONLY valid JSON with this exact structure:
{{
  "important_points": ["bullet point 1", "bullet point 2", "bullet point 3"],
  "date": "Date string or null",
  "time": "Time string or null",
  "venue": "Location, venue, or merchant name or null",
  "deadline_or_total": "Deadline or total financial amount or null",
  "applicable_users": "Applicable students, department, or audience or null"
}}"""

            models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
            for model_name in models_to_try:
                try:
                    try:
                        cfg = types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=cfg
                        )
                    except Exception:
                        cfg = types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json"
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=cfg
                        )
                    raw = response.text.strip()
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                    parsed = json.loads(raw)
                    return parsed
                except Exception:
                    continue
        except Exception:
            pass
            
    # Deterministic summary generation
    if doc_type == 'timetable':
        entries = document_data.get('entries', [])
        days = list(set([e.get('day') for e in entries if e.get('day')]))
        subjects = list(set([e.get('subject') for e in entries if e.get('subject')]))
        rooms = list(set([e.get('room') for e in entries if e.get('room')]))
        
        return {
            "important_points": [
                f"Schedule contains {len(entries)} class sessions across {len(days)} weekdays ({', '.join(days[:4])}).",
                f"Covers key courses: {', '.join(subjects[:4])}.",
                f"Conducted across venues: {', '.join(rooms[:3])}."
            ],
            "date": "Weekly Recurring",
            "time": f"{entries[0].get('start_time', '09:00')} - {entries[-1].get('end_time', '15:30')}" if entries else None,
            "venue": document_data.get('title') or "Campus Classrooms & Labs",
            "deadline_or_total": f"{len(entries)} Weekly Lectures",
            "applicable_users": "Registered Semester Students & Faculty"
        }
        
    elif doc_type == 'receipt':
        merchant = document_data.get('merchant', 'Store')
        date_val = document_data.get('date', 'Recent')
        total_val = document_data.get('total')
        curr = document_data.get('currency', '₹')
        items = document_data.get('items', [])
        
        return {
            "important_points": [
                f"Purchase from {merchant} on {date_val}.",
                f"Itemized invoice with {len(items)} line item(s).",
                f"Total payable amount is {curr} {total_val} under {document_data.get('category', 'Expense')} category."
            ],
            "date": str(date_val),
            "time": "Recorded on Invoice",
            "venue": merchant,
            "deadline_or_total": f"{curr} {total_val}",
            "applicable_users": "Expense Reimbursement & Accounting"
        }
        
    elif doc_type in ('notice', 'poster'):
        title = document_data.get('title', 'Notice Announcement')
        date_val = document_data.get('date')
        st = document_data.get('start_time')
        et = document_data.get('end_time')
        venue_val = document_data.get('venue')
        desc = document_data.get('description', '')
        
        return {
            "important_points": [
                f"Event Headline: {title}.",
                f"Schedule: {date_val or 'Upcoming'} from {st or 'TBA'} to {et or 'TBA'}.",
                f"Details: {desc[:120]}..." if len(desc) > 120 else (desc or "No additional details.")
            ],
            "date": str(date_val) if date_val else "Refer to Notice",
            "time": f"{st} - {et}" if (st and et) else (st or "Refer to Notice"),
            "venue": venue_val or "Official Campus Venue",
            "deadline_or_total": "Event Date: " + (str(date_val) if date_val else "Open"),
            "applicable_users": "All Students, Participants & Staff"
        }
        
    return {
        "important_points": ["Document extracted and structured."],
        "date": None,
        "time": None,
        "venue": None,
        "deadline_or_total": None,
        "applicable_users": "General Audience"
    }

def translate_document_content(document_data: Dict[str, Any], target_language: str = "English") -> Dict[str, Any]:
    """
    Translates text fields to target_language.
    Preserves original document data intact, returning translated version.
    """
    client = get_gemini_client()
    doc_json_str = json.dumps(document_data, indent=2, ensure_ascii=False)
    
    if client:
        try:
            from google.genai import types
            prompt = f"""You are DocSnap Translation Assistant.
Translate all text values in the following JSON into {target_language}.
Do NOT change numbers, dates, or field names. Maintain the EXACT same JSON structure.

ORIGINAL JSON:
{doc_json_str}

OUTPUT ONLY VALID JSON:"""

            models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
            for model_name in models_to_try:
                try:
                    try:
                        cfg = types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=cfg
                        )
                    except Exception:
                        cfg = types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json"
                        )
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=cfg
                        )
                    raw = response.text.strip()
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                    return json.loads(raw)
                except Exception:
                    continue
        except Exception:
            pass
            
    # Fallback translation: returns original structured document data intact
    return json.loads(doc_json_str)
