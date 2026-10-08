import sqlite3
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_PATH = Path(__file__).parent / 'docsnap.db'

def get_db_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database tables if they do not exist."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_hash TEXT,
                doc_type TEXT NOT NULL,
                language TEXT DEFAULT 'English',
                ai_confidence REAL DEFAULT 0.95,
                verification_status TEXT DEFAULT 'ai_generated',
                ai_extracted_data TEXT NOT NULL,
                user_corrected_data TEXT,
                verified_data TEXT,
                verification_report TEXT,
                summary TEXT,
                sensitive_data_info TEXT,
                thumbnail TEXT,
                feedback TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Document versions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                version_label TEXT NOT NULL,
                data TEXT NOT NULL,
                change_type TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                changed_fields TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        ''')
        
        # Indexes for fast search and filtering
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_type ON documents (doc_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_verification_status ON documents (verification_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON documents (created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON documents (file_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_versions ON document_versions (document_id, version_number)')
        
        conn.commit()
    finally:
        conn.close()
    seed_default_documents_if_empty()

def compute_field_diff(old_data: Any, new_data: Any, prefix: str = "") -> List[Dict[str, Any]]:
    """Recursively computes changed fields between two data structures."""
    diffs = []
    
    if old_data == new_data:
        return diffs
        
    if isinstance(old_data, dict) and isinstance(new_data, dict):
        all_keys = set(old_data.keys()).union(set(new_data.keys()))
        for k in sorted(all_keys):
            field_name = f"{prefix}.{k}" if prefix else k
            if k not in old_data:
                diffs.append({
                    "field": field_name,
                    "old_value": None,
                    "new_value": new_data[k],
                    "change": "added"
                })
            elif k not in new_data:
                diffs.append({
                    "field": field_name,
                    "old_value": old_data[k],
                    "new_value": None,
                    "change": "removed"
                })
            elif old_data[k] != new_data[k]:
                if isinstance(old_data[k], (dict, list)):
                    diffs.extend(compute_field_diff(old_data[k], new_data[k], prefix=field_name))
                else:
                    diffs.append({
                        "field": field_name,
                        "old_value": old_data[k],
                        "new_value": new_data[k],
                        "change": "modified"
                    })
    elif isinstance(old_data, list) and isinstance(new_data, list):
        max_len = max(len(old_data), len(new_data))
        for i in range(max_len):
            idx_name = f"{prefix}[{i}]"
            if i >= len(old_data):
                diffs.append({
                    "field": idx_name,
                    "old_value": None,
                    "new_value": new_data[i],
                    "change": "added"
                })
            elif i >= len(new_data):
                diffs.append({
                    "field": idx_name,
                    "old_value": old_data[i],
                    "new_value": None,
                    "change": "removed"
                })
            elif old_data[i] != new_data[i]:
                if isinstance(old_data[i], (dict, list)):
                    diffs.extend(compute_field_diff(old_data[i], new_data[i], prefix=idx_name))
                else:
                    diffs.append({
                        "field": idx_name,
                        "old_value": old_data[i],
                        "new_value": new_data[i],
                        "change": "modified"
                    })
    else:
        diffs.append({
            "field": prefix or "value",
            "old_value": old_data,
            "new_value": new_data,
            "change": "modified"
        })
        
    return diffs

def create_document(
    filename: str,
    doc_type: str,
    ai_extracted_data: Dict[str, Any],
    language: str = "English",
    ai_confidence: float = 0.95,
    verification_status: str = "ai_generated",
    verification_report: Optional[Dict[str, Any]] = None,
    sensitive_data_info: Optional[Dict[str, Any]] = None,
    file_hash: Optional[str] = None,
    thumbnail: Optional[str] = None,
    doc_id: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new document record and its initial Version 1 (AI Generated)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_id = doc_id or str(uuid.uuid4())
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documents (
                id, filename, file_hash, doc_type, language, ai_confidence,
                verification_status, ai_extracted_data, user_corrected_data,
                verified_data, verification_report, summary, sensitive_data_info,
                thumbnail, feedback, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            doc_id,
            filename,
            file_hash or "",
            doc_type,
            language,
            float(ai_confidence),
            verification_status,
            json.dumps(ai_extracted_data),
            None,
            None,
            json.dumps(verification_report or {}),
            None,
            json.dumps(sensitive_data_info or {}),
            thumbnail or "",
            None,
            now,
            now
        ))
        
        # Version 1: AI Generated
        v1_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO document_versions (
                id, document_id, version_number, version_label, data,
                change_type, changed_by, changed_fields, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            v1_id,
            doc_id,
            1,
            "🤖 AI Generated",
            json.dumps(ai_extracted_data),
            "ai_generated",
            "AI Vision Engine",
            json.dumps([]),
            now
        ))
        
        conn.commit()
        return get_document_by_id(doc_id)
    finally:
        conn.close()

def update_document_data(
    doc_id: str,
    updated_data: Dict[str, Any],
    changed_by: str = "User",
    change_type: str = "user_edit",
    version_label: str = "👤 User Edited",
    verification_status: Optional[str] = None,
    verification_report: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Updates document data and records a new version with changed fields diff."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            return None
            
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Get highest version number
        cursor.execute("SELECT MAX(version_number) FROM document_versions WHERE document_id = ?", (doc_id,))
        max_ver = cursor.fetchone()[0] or 1
        new_version_num = max_ver + 1
        
        # Current data before update
        current_data = None
        if doc_row['verified_data']:
            current_data = json.loads(doc_row['verified_data'])
        elif doc_row['user_corrected_data']:
            current_data = json.loads(doc_row['user_corrected_data'])
        else:
            current_data = json.loads(doc_row['ai_extracted_data'])
            
        diffs = compute_field_diff(current_data, updated_data)
        
        # Create new version
        v_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO document_versions (
                id, document_id, version_number, version_label, data,
                change_type, changed_by, changed_fields, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            v_id,
            doc_id,
            new_version_num,
            version_label,
            json.dumps(updated_data),
            change_type,
            changed_by,
            json.dumps(diffs),
            now
        ))
        
        # Update documents table
        new_status = verification_status or doc_row['verification_status']
        user_corrected = json.dumps(updated_data)
        verified = doc_row['verified_data']
        if change_type == 'verified':
            verified = json.dumps(updated_data)
            new_status = 'verified'
            
        report_str = json.dumps(verification_report) if verification_report is not None else doc_row['verification_report']
        
        cursor.execute('''
            UPDATE documents SET
                user_corrected_data = ?,
                verified_data = ?,
                verification_status = ?,
                verification_report = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            user_corrected,
            verified,
            new_status,
            report_str,
            now,
            doc_id
        ))
        
        conn.commit()
        return get_document_by_id(doc_id)
    finally:
        conn.close()

def verify_and_save_document(
    doc_id: str,
    verified_data: Dict[str, Any],
    verification_report: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Marks document as Final Verified Data, saves Version 3 (or latest verified)."""
    return update_document_data(
        doc_id=doc_id,
        updated_data=verified_data,
        changed_by="Human Verifier",
        change_type="verified",
        version_label="✅ Verified",
        verification_status="verified",
        verification_report=verification_report
    )

def save_document_summary(doc_id: str, summary_data: Any) -> bool:
    """Saves generated summary to the document record."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        summary_str = json.dumps(summary_data) if isinstance(summary_data, (dict, list)) else str(summary_data)
        cursor.execute("UPDATE documents SET summary = ?, updated_at = ? WHERE id = ?", (
            summary_str,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            doc_id
        ))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def save_document_feedback(doc_id: str, feedback_data: Dict[str, Any]) -> bool:
    """Saves user feedback for extraction accuracy."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        feedback_str = json.dumps(feedback_data)
        cursor.execute("UPDATE documents SET feedback = ?, updated_at = ? WHERE id = ?", (
            feedback_str,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            doc_id
        ))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves single document with all deserialized JSON fields and versions."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if not row:
            return None
            
        doc = dict(row)
        doc['ai_extracted_data'] = json.loads(doc['ai_extracted_data']) if doc['ai_extracted_data'] else None
        doc['user_corrected_data'] = json.loads(doc['user_corrected_data']) if doc['user_corrected_data'] else None
        doc['verified_data'] = json.loads(doc['verified_data']) if doc['verified_data'] else None
        doc['verification_report'] = json.loads(doc['verification_report']) if doc['verification_report'] else {}
        doc['summary'] = json.loads(doc['summary']) if doc['summary'] and doc['summary'].startswith(('{', '[')) else doc['summary']
        doc['sensitive_data_info'] = json.loads(doc['sensitive_data_info']) if doc['sensitive_data_info'] else {}
        doc['feedback'] = json.loads(doc['feedback']) if doc['feedback'] else None
        
        # Get versions
        cursor.execute("SELECT * FROM document_versions WHERE document_id = ? ORDER BY version_number ASC", (doc_id,))
        versions = []
        for v_row in cursor.fetchall():
            v_dict = dict(v_row)
            v_dict['data'] = json.loads(v_dict['data']) if v_dict['data'] else None
            v_dict['changed_fields'] = json.loads(v_dict['changed_fields']) if v_dict['changed_fields'] else []
            versions.append(v_dict)
            
        doc['versions'] = versions
        return doc
    finally:
        conn.close()

def get_documents(
    query: Optional[str] = None,
    doc_type: Optional[str] = None,
    language: Optional[str] = None,
    verification_status: Optional[str] = None,
    sort_order: str = "newest",
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieves list of documents with filtering, searching, and sorting."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        if doc_type and doc_type != 'all':
            sql += " AND doc_type = ?"
            params.append(doc_type)
            
        if language and language != 'all':
            sql += " AND language = ?"
            params.append(language)
            
        if verification_status and verification_status != 'all':
            sql += " AND verification_status = ?"
            params.append(verification_status)
            
        if query:
            sql += " AND (filename LIKE ? OR ai_extracted_data LIKE ? OR user_corrected_data LIKE ? OR verified_data LIKE ?)"
            q_param = f"%{query}%"
            params.extend([q_param, q_param, q_param, q_param])
            
        if sort_order == "oldest":
            sql += " ORDER BY created_at ASC"
        else:
            sql += " ORDER BY created_at DESC"
            
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
        
        cursor.execute(sql, params)
        docs = []
        for row in cursor.fetchall():
            d = dict(row)
            d['ai_extracted_data'] = json.loads(d['ai_extracted_data']) if d['ai_extracted_data'] else None
            d['user_corrected_data'] = json.loads(d['user_corrected_data']) if d['user_corrected_data'] else None
            d['verified_data'] = json.loads(d['verified_data']) if d['verified_data'] else None
            d['verification_report'] = json.loads(d['verification_report']) if d['verification_report'] else {}
            d['summary'] = json.loads(d['summary']) if d['summary'] and d['summary'].startswith(('{', '[')) else d['summary']
            d['sensitive_data_info'] = json.loads(d['sensitive_data_info']) if d['sensitive_data_info'] else {}
            d['feedback'] = json.loads(d['feedback']) if d['feedback'] else None
            docs.append(d)
            
        return docs
    finally:
        conn.close()

def delete_document(doc_id: str) -> bool:
    """Deletes a document and its version history."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM document_versions WHERE document_id = ?", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def find_duplicate_document(file_hash: str = None, title: str = None, doc_type: str = None) -> Optional[Dict[str, Any]]:
    """Checks if identical or very similar document already exists in history."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if file_hash:
            cursor.execute("SELECT id, filename, doc_type, created_at, verification_status FROM documents WHERE file_hash = ? ORDER BY created_at DESC LIMIT 1", (file_hash,))
            row = cursor.fetchone()
            if row:
                return dict(row)
                
        if title and doc_type:
            cursor.execute(
                "SELECT id, filename, doc_type, created_at, verification_status FROM documents WHERE doc_type = ? AND (ai_extracted_data LIKE ? OR user_corrected_data LIKE ?) ORDER BY created_at DESC LIMIT 1",
                (doc_type, f"%{title}%", f"%{title}%")
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
                
        return None
    finally:
        conn.close()

def get_analytics_metrics() -> Dict[str, Any]:
    """Computes aggregate analytics statistics."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE verification_status = 'verified'")
        verified_docs = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE user_corrected_data IS NOT NULL")
        corrected_docs = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE verification_status = 'needs_review'")
        needs_review_docs = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE verification_status = 'warning'")
        warning_docs = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(ai_confidence) FROM documents")
        avg_conf = cursor.fetchone()[0]
        avg_confidence = round(float(avg_conf or 0.92) * 100, 1)
        
        # Document types distribution
        cursor.execute("SELECT doc_type, COUNT(*) as cnt FROM documents GROUP BY doc_type")
        type_counts = {}
        for row in cursor.fetchall():
            type_counts[row['doc_type']] = row['cnt']
            
        verification_rate = round((verified_docs / total_docs * 100), 1) if total_docs > 0 else 0.0
        
        return {
            "total_documents": total_docs,
            "verified_count": verified_docs,
            "corrected_count": corrected_docs,
            "needs_review_count": needs_review_docs,
            "warning_count": warning_docs,
            "avg_confidence": avg_confidence,
            "verification_rate": verification_rate,
            "type_counts": type_counts
        }
    finally:
        conn.close()

def seed_default_documents_if_empty():
    """Seeds 3 curated, verified documents if the database has 0 documents."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        count = cur.fetchone()[0]
        if count > 0:
            return
    except Exception:
        return
    finally:
        conn.close()

    # 1. Seed Timetable
    timetable_data = {
        "title": "Computer Science Dept - Semester IV Weekly Schedule",
        "entries": [
            {"day": "Monday", "subject": "Data Structures & Algorithms", "room": "Room 302", "start_time": "09:00", "end_time": "10:30", "faculty": "Prof. Sharma"},
            {"day": "Monday", "subject": "Computer Networks", "room": "Room 204", "start_time": "11:00", "end_time": "12:30", "faculty": "Dr. Patel"},
            {"day": "Tuesday", "subject": "Data Structures & Algorithms", "room": "Room 204", "start_time": "11:00", "end_time": "12:30", "faculty": "Prof. Sharma"},
            {"day": "Wednesday", "subject": "Operating Systems", "room": "Lab 3", "start_time": "09:00", "end_time": "11:00", "faculty": "Prof. Gupta"},
            {"day": "Thursday", "subject": "Database Management Systems", "room": "Room 302", "start_time": "10:00", "end_time": "11:30", "faculty": "Dr. Mehta"},
            {"day": "Friday", "subject": "Artificial Intelligence", "room": "Auditorium A", "start_time": "14:00", "end_time": "16:00", "faculty": "Dr. Rao"}
        ]
    }
    t_doc = create_document(
        filename="sample_timetable.png",
        doc_type="timetable",
        ai_extracted_data=timetable_data,
        language="English",
        ai_confidence=0.98,
        verification_status="verified",
        verification_report={
            "status": "verified",
            "score": 100,
            "passed_checks": [
                "Timetable format verified with 6 class sessions",
                "Chronological start/end times consistent across all days",
                "No overlapping room slot conflicts detected",
                "All assigned professors verified with department roster"
            ],
            "warnings": [],
            "conflicts": []
        },
        thumbnail="/static/samples/sample_timetable.png"
    )
    update_document_data(
        doc_id=t_doc["id"],
        updated_data=timetable_data,
        changed_by="Department Admin",
        change_type="verified",
        version_label="✅ Verified",
        verification_status="verified",
        verification_report={
            "status": "verified",
            "score": 100,
            "passed_checks": ["All schedule slots audited and approved"],
            "warnings": [],
            "conflicts": []
        }
    )

    # 2. Seed Receipt
    receipt_data = {
        "merchant": "The Daily Roast Cafe & Bookstore",
        "date": "2026-10-05",
        "items": [
            {"name": "Cold Brew Coffee", "qty": 2, "price": 180.0},
            {"name": "Blueberry Muffin", "qty": 1, "price": 120.0},
            {"name": "Tech Notebook Spiral", "qty": 1, "price": 250.0},
            {"name": "Espresso Roast Beans (250g)", "qty": 1, "price": 90.0}
        ],
        "subtotal": 820.0,
        "tax": 41.0,
        "tax_rate": 5.0,
        "total": 861.0,
        "currency": "₹",
        "category": "Food & Dining"
    }
    r_doc = create_document(
        filename="sample_receipt.png",
        doc_type="receipt",
        ai_extracted_data=receipt_data,
        language="English",
        ai_confidence=0.99,
        verification_status="verified",
        verification_report={
            "status": "verified",
            "score": 100,
            "passed_checks": [
                "Mathematical cross-check: 2*180 + 1*120 + 1*250 + 1*90 = 820.0",
                "Tax calculation verified: 5% of 820.0 = 41.0",
                "Final grand total matches: 820.0 + 41.0 = 861.0",
                "Receipt date format verified (2026-10-05)"
            ],
            "warnings": [],
            "conflicts": []
        },
        thumbnail="/static/samples/sample_receipt.png"
    )
    update_document_data(
        doc_id=r_doc["id"],
        updated_data=receipt_data,
        changed_by="Finance Auditor",
        change_type="verified",
        version_label="✅ Verified",
        verification_status="verified",
        verification_report={
            "status": "verified",
            "score": 100,
            "passed_checks": ["Arithmetic verified and tax validated"],
            "warnings": [],
            "conflicts": []
        }
    )

    # 3. Seed Notice
    notice_data = {
        "title": "HackSprint 2026: AI & Sustainability Hackathon",
        "date": "2026-10-24",
        "start_time": "09:00",
        "end_time": "18:30",
        "venue": "Main Convention Center, Hall B, Tech Park Campus",
        "description": "Annual 24-hour hackathon on AI Solutions for Social Impact & Sustainability. Open to all students with cash prizes up to INR 1,50,000.",
        "registration_deadline": "2026-10-20"
    }
    n_doc = create_document(
        filename="sample_notice.png",
        doc_type="notice",
        ai_extracted_data=notice_data,
        language="English",
        ai_confidence=0.97,
        verification_status="verified",
        verification_report={
            "status": "verified",
            "score": 100,
            "passed_checks": [
                "Notice date verified (2026-10-24 is a future scheduled event)",
                "Event timing valid: 09:00 to 18:30 (9.5 hour session)",
                "Physical venue specified and verified on campus map",
                "Registration deadline precedes event start"
            ],
            "warnings": [],
            "conflicts": []
        },
        thumbnail="/static/samples/sample_notice.png"
    )
    update_document_data(
        doc_id=n_doc["id"],
        updated_data=notice_data,
        changed_by="Event Coordinator",
        change_type="verified",
        version_label="✅ Verified",
        verification_status="verified",
        verification_report={
            "status": "verified",
            "score": 100,
            "passed_checks": ["Event schedule and venue verified"],
            "warnings": [],
            "conflicts": []
        }
    )

# Auto-initialize on module import
init_db()
