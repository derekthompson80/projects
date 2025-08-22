import csv
import os
import re
from typing import List, Dict

# This script reads default_actions.txt and writes default_actions.csv in the same directory.
# It expects entries formatted as blocks like:
#   Project Name:
#   Stat Type
#   Points Cost
#   Resource Costs (total)
#   [Requirements]
#   [Benefits]
# Blank lines may appear between entries. Requirements and Benefits are optional.
# Any additional non-blank lines after Requirements/Benefits (before next project) are appended to Benefits with ' | '.

HEADERS = [
    "Project",
    "Stat Type",
    "Points Cost",
    "Resource Costs (total)",
    "Requirements",
    "Benefits",
]

HEADER_TOKENS = {h.lower() for h in [
    "Project",
    "Stat Type",
    "Points Cost",
    "Resource Costs (total)",
    "Requirements",
    "Benefits",
]}

PROJECT_LINE_RE = re.compile(r".+:\s*$")


def is_header_line(s: str) -> bool:
    return s.strip().lower() in HEADER_TOKENS


def read_lines(txt_path: str) -> List[str]:
    with open(txt_path, "r", encoding="utf-8") as f:
        # Normalize whitespace: strip right and keep order
        return [ln.strip() for ln in f.readlines()]


def parse_entries(lines: List[str]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []

    # Skip initial header section until the first project-like line
    i = 0
    n = len(lines)

    while i < n and (not lines[i] or is_header_line(lines[i])):
        i += 1

    while i < n:
        line = lines[i]

        # Find the next project line
        if not line or is_header_line(line) or not PROJECT_LINE_RE.match(line):
            i += 1
            continue

        project = line[:-1].strip()  # remove trailing colon

        # Prepare default fields
        stat_type = ""
        points_cost = ""
        resource_costs = ""
        requirements = ""
        benefits = ""

        # Helper to fetch next meaningful line index (skip blanks)
        def next_nonblank(idx: int) -> int:
            while idx < n and not lines[idx].strip():
                idx += 1
            return idx

        # Read Stat Type
        i += 1
        i = next_nonblank(i)
        if i < n and lines[i] and not PROJECT_LINE_RE.match(lines[i]) and not is_header_line(lines[i]):
            stat_type = lines[i].strip()
            i += 1
        i = next_nonblank(i)

        # Read Points Cost
        if i < n and lines[i] and not PROJECT_LINE_RE.match(lines[i]) and not is_header_line(lines[i]):
            points_cost = lines[i].strip()
            i += 1
        i = next_nonblank(i)

        # Read Resource Costs (total)
        if i < n and lines[i] and not PROJECT_LINE_RE.match(lines[i]) and not is_header_line(lines[i]):
            resource_costs = lines[i].strip()
            i += 1
        i = next_nonblank(i)

        # Read Requirements (optional)
        if i < n and lines[i] and not PROJECT_LINE_RE.match(lines[i]) and not is_header_line(lines[i]):
            requirements = lines[i].strip()
            i += 1
        i = next_nonblank(i)

        # Read Benefits (optional)
        if i < n and lines[i] and not PROJECT_LINE_RE.match(lines[i]) and not is_header_line(lines[i]):
            benefits = lines[i].strip()
            i += 1
        i = next_nonblank(i)

        # Consume any additional lines until next project-like line; append to Benefits
        extras: List[str] = []
        while i < n and lines[i] and not PROJECT_LINE_RE.match(lines[i]) and not is_header_line(lines[i]):
            extras.append(lines[i].strip())
            i += 1
            i = next_nonblank(i)
        if extras:
            benefits = (benefits + (" | " if benefits else "") + " | ".join(extras)).strip()

        entries.append({
            "Project": project,
            "Stat Type": stat_type,
            "Points Cost": points_cost,
            "Resource Costs (total)": resource_costs,
            "Requirements": requirements,
            "Benefits": benefits,
        })

        # Do not increment i here; loop continues from current i to find next project

    return entries


def write_csv(csv_path: str, rows: List[Dict[str, str]]) -> None:
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            # Ensure all keys are present
            out = {h: row.get(h, "") for h in HEADERS}
            writer.writerow(out)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(base_dir, "default_actions.txt")
    csv_path = os.path.join(base_dir, "default_actions.csv")

    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"Could not find default_actions.txt at {txt_path}")

    lines = read_lines(txt_path)
    entries = parse_entries(lines)
    if not entries:
        raise RuntimeError("No entries parsed from default_actions.txt; check the file format.")

    write_csv(csv_path, entries)
    print(f"Wrote {len(entries)} rows to {csv_path}")


if __name__ == "__main__":
    main()
