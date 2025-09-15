"""
Convert 'CG5 resources (outdated).docx' into a CSV file.

Usage (from repository root or this directory):
    python -m projects.country_game.country_game_utilites.convert_cg5_resources_docx_to_csv

Output:
    Creates 'cg5_resources.csv' in the same folder as the source DOCX.

Notes:
- This script tries two strategies:
  1) Table-based extraction (preferred): reads all tables in the DOCX and
     attempts to normalize header names and rows.
  2) Paragraph-based fallback: scans paragraphs for lines that look like
     resource records in patterns like `Name: X, Type: Y, Tier: Z, ...`.
- The document is labeled 'outdated'; the structure may be inconsistent.
  The script is resilient: unknown columns are preserved as extra fields.
- No external CLI args needed; edit DOCX_FILENAME below if the file is renamed.

Dependencies:
    - python-docx ("docx" package). If not installed, the script will try a
      very naive text-based extraction and produce a best-effort CSV.
"""
from __future__ import annotations
import os
import csv
import re
from typing import List, Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCX_FILENAME = os.path.join(SCRIPT_DIR, 'CG5 resources (outdated).docx')
CSV_FILENAME = os.path.join(SCRIPT_DIR, 'cg5_resources.csv')

PREFERRED_HEADERS = [
    'name',
    'type',
    'tier',
    'natively_produced',
    'trade',
    'committed',
    'not_developed',
    'available',
    'notes'
]

HEADER_ALIASES = {
    'resource': 'name',
    'resource name': 'name',
    'name': 'name',
    'type': 'type',
    'category': 'type',
    'tier': 'tier',
    'native': 'natively_produced',
    'natively produced': 'natively_produced',
    'trade': 'trade',
    'committed': 'committed',
    'not developed': 'not_developed',
    'available': 'available',
    'notes': 'notes',
}


def normalize_header(h: str) -> str:
    key = (h or '').strip().lower()
    key = re.sub(r'\s+', ' ', key)
    return HEADER_ALIASES.get(key, key)


def to_int(val: Any) -> int:
    try:
        if val is None:
            return 0
        s = str(val).strip()
        if s == '':
            return 0
        # Extract first integer-like token
        m = re.search(r'-?\d+', s)
        if m:
            return int(m.group(0))
        return 0
    except Exception:
        return 0


def write_csv(rows: List[Dict[str, Any]], path: str) -> None:
    # Collect all keys seen to avoid losing unexpected columns
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    # Order: preferred headers first, then the rest alphabetically
    ordered = [h for h in PREFERRED_HEADERS if h in all_keys]
    for k in sorted(all_keys):
        if k not in ordered:
            ordered.append(k)

    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ordered)
        writer.writeheader()
        for r in rows:
            # Coerce known numeric columns
            for k in ('tier','natively_produced','trade','committed','not_developed','available'):
                if k in r:
                    r[k] = to_int(r[k])
            writer.writerow(r)


def extract_tables(doc) -> List[Dict[str, Any]]:  # type: ignore
    rows_out: List[Dict[str, Any]] = []
    for t in getattr(doc, 'tables', []):
        if not t.rows:
            continue
        # Build header row from first non-empty row
        header_cells = None
        for row in t.rows:
            texts = [cell.text.strip() for cell in row.cells]
            if any(texts):
                header_cells = texts
                break
        if not header_cells:
            continue
        headers = [normalize_header(h) for h in header_cells]
        # Subsequent rows are data
        started = False
        for row in t.rows:
            texts = [cell.text.strip() for cell in row.cells]
            if not any(texts):
                continue
            if not started:
                # This is the header row we already used
                started = True
                continue
            rec: Dict[str, Any] = {}
            for i, val in enumerate(texts):
                key = headers[i] if i < len(headers) else f'extra_{i}'
                rec[key] = val
            # Only keep rows that look like a resource (must have a name or type)
            if rec.get('name') or rec.get('type'):
                rows_out.append(rec)
    return rows_out


def extract_paragraphs_best_effort(doc) -> List[Dict[str, Any]]:  # type: ignore
    rows_out: List[Dict[str, Any]] = []
    paras = getattr(doc, 'paragraphs', [])
    # Pattern like: Name: Iron, Type: Metal, Tier: 1, Native: 2, Trade: 1, Notes: ...
    kv_pattern = re.compile(r'([A-Za-z ]+):\s*([^,;\n]+)')
    for p in paras:
        line = (getattr(p, 'text', '') or '').strip()
        if not line:
            continue
        # Heuristic: if the line contains at least two key:value pairs, treat as record
        matches = kv_pattern.findall(line)
        if len(matches) >= 2:
            rec: Dict[str, Any] = {}
            for k, v in matches:
                normk = normalize_header(k)
                rec[normk] = v.strip()
            if rec.get('name') or rec.get('type'):
                rows_out.append(rec)
        else:
            # Fallback: lines like "Iron (Metal) - Tier 1 - Native 2, Trade 1"
            m = re.match(r'^([^\-\(]+)\s*(?:\(([^\)]+)\))?\s*-\s*(.*)$', line)
            if m:
                name = m.group(1).strip()
                typ = (m.group(2) or '').strip()
                rest = m.group(3).strip()
                rec: Dict[str, Any] = {'name': name}
                if typ:
                    rec['type'] = typ
                # Parse rest segments for known tokens
                for seg in re.split(r'\s*-\s*|,', rest):
                    seg = seg.strip()
                    if not seg:
                        continue
                    if seg.lower().startswith('tier'):
                        rec['tier'] = to_int(seg)
                    elif seg.lower().startswith('native') or 'natively' in seg.lower():
                        rec['natively_produced'] = to_int(seg)
                    elif seg.lower().startswith('trade'):
                        rec['trade'] = to_int(seg)
                    else:
                        rec['notes'] = (rec.get('notes', '') + ('; ' if 'notes' in rec else '') + seg).strip()
                rows_out.append(rec)
    return rows_out


def convert_docx_to_csv(docx_path: str, csv_path: str) -> int:
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX not found: {docx_path}")

    rows: List[Dict[str, Any]] = []

    try:
        from docx import Document  # type: ignore
        doc = Document(docx_path)
        # First try tables
        rows = extract_tables(doc)
        # If nothing from tables, try paragraphs
        if not rows:
            rows = extract_paragraphs_best_effort(doc)
    except Exception as e:
        # Fallback: naive text read using zipfile if python-docx unavailable
        try:
            import zipfile
            with zipfile.ZipFile(docx_path) as z:
                xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
            # Very rough extraction of text nodes
            texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml)
            lines = []
            cur = ''
            for t in texts:
                t = re.sub(r'\s+', ' ', t)
                if t.endswith('\n'):
                    cur += t
                    lines.append(cur)
                    cur = ''
                else:
                    cur += t + ' '
            if cur.strip():
                lines.append(cur.strip())
            # Build a pseudo-doc for paragraph parsing
            class P:  # minimal shim
                def __init__(self, text):
                    self.text = text
            pseudo = type('D', (), {'paragraphs': [P(l) for l in lines], 'tables': []})
            rows = extract_paragraphs_best_effort(pseudo)
        except Exception as e2:
            raise RuntimeError(f"Failed to parse DOCX (docx={e!r}, fallback={e2!r})")

    if not rows:
        # still create empty csv with headers to satisfy the requirement
        rows = []

    write_csv(rows, csv_path)
    return len(rows)


def main() -> None:
    count = convert_docx_to_csv(DOCX_FILENAME, CSV_FILENAME)
    print(f"Wrote {count} row(s) to {CSV_FILENAME}")


if __name__ == '__main__':
    main()
