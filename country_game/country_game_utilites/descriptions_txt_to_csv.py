import os
import csv
import re
from typing import Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT_PATH = os.path.join(BASE_DIR, 'CG5_Country_Descriptions.txt')
OUT_CSV = os.path.join(BASE_DIR, 'cg5_countries.csv')


def _extract_label(line: str, label: str) -> Optional[str]:
    """
    Extract a value following a labeled segment like "<Label> - value - NextLabel" or at end of line.
    Returns None if not found.
    """
    # Capture text after label up to the next " - <KnownLabel>" or end of line
    pattern = rf"{label}\s*-\s*(.*?)(?=\s*-\s*(?:Country name|Government description|Nations? societal alignment|Nation description)\b|$)"
    m = re.search(pattern, line, flags=re.IGNORECASE)
    if m:
        val = (m.group(1) or '').strip()
        return re.sub(r"\s+", " ", val)
    return None


def parse_numbered_line(line: str) -> Optional[Dict[str, str]]:
    line = line.strip()
    if not line:
        return None
    num_m = re.match(r"^(\d+)\.\s*(.*)$", line)
    if not num_m:
        return None
    rest = num_m.group(2)

    # Try standard extraction
    country_name = _extract_label(rest, 'Country name')
    gov_desc = _extract_label(rest, 'Government description')
    alignment = _extract_label(rest, 'Nations? societal alignment') or _extract_label(rest, 'Nations societal alignment')
    description = _extract_label(rest, 'Nation description')

    # Handle anomaly where Country name is empty (e.g., line 16)
    if not country_name:
        # If immediately after Country name - we see Government description, use the first value after Government description as the name
        m = re.search(r"Country name\s*-\s*Government description\s*-\s*([^\-]+)", rest, flags=re.IGNORECASE)
        if m:
            country_name = m.group(1).strip()

    # Some malformed lines may repeat labels; if description is missing but we have leftovers, attempt a broad fallback
    if not description:
        # Take everything after the last occurrence of "Nation description -"
        m = re.search(r"Nation description\s*-\s*(.*)$", rest, flags=re.IGNORECASE)
        if m:
            description = m.group(1).strip()

    # Normalize whitespace
    def norm(x: Optional[str]) -> str:
        x = (x or '').strip()
        return re.sub(r"\s+", " ", x)

    data = {
        'index': num_m.group(1),
        'country_name': norm(country_name),
        'government_description': norm(gov_desc),
        'alignment': norm(alignment),
        'description': norm(description),
    }
    return data


def build_csv(input_path: str = TXT_PATH, output_path: str = OUT_CSV) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    rows = []
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            rec = parse_numbered_line(raw)
            if rec:
                rows.append(rec)

    # Write CSV
    fieldnames = ['index', 'country_name', 'government_description', 'alignment', 'description']
    with open(output_path, 'w', newline='', encoding='utf-8') as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fieldnames})

    print(f"Wrote {len(rows)} rows to {output_path}")
    return output_path


if __name__ == '__main__':
    build_csv()
