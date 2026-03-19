#!/usr/bin/env python3
"""
Parse ACT model output files into a CSV.

Usage:
    python parse_outputs_to_csv.py <output_file1> [output_file2 ...] -o results.csv

The script extracts total_carbon and per-category values from each output file
and writes one row per file to a CSV.

Category → CSV column mapping mirrors the reference table:
    IC            ← FABRICATION
    PCB           ← PCB
    Resistor      ← RESISTOR
    Capacitor     ← CAPACITOR
    Inductor      ← INDUCTOR
    Connector     ← CONNECTOR
    Switch        ← SWITCH
    Diode         ← DIODE
    Timing Device ← ACTIVE  (timing / crystal devices)
    Transistor (MOSFET) ← from result_by_device ACTIVE category filtered by MOSFET
    Ferrite Bead  ← OTHER
"""

import argparse
import csv
import os
import re
import sys

# Maps CSV column name → YAML category key(s) to sum
CATEGORY_MAP = {
    "IC": ["FABRICATION"],
    "PCB": ["PCB"],
    "Resistor": ["RESISTOR"],
    "Capacitor": ["CAPACITOR"],
    "Inductor": ["INDUCTOR"],
    "Connector": ["CONNECTOR"],
    "Switch": ["SWITCH"],
    "Diode": ["DIODE"],
    "Others": ["ACTIVE", "OTHER"],  # Timing Device + Transistor (MOSFET) + Ferrite Bead
}

CSV_COLUMNS = [
    "",  # row label (device name derived from filename)
    "Total",
    "IC",
    "PCB",
    "Resistor",
    "Capacitor",
    "Inductor",
    "Connector",
    "Switch",
    "Diode",
    "Others",
]

# Regex patterns
_KG_VALUE = r"([\d.]+)\s+kilogram"


def extract_value(text, key):
    """Return float value (kg) for a YAML scalar key (any indentation level), or 0."""
    pattern = rf"^\s*{re.escape(key)}:\s+{_KG_VALUE}"
    m = re.search(pattern, text, re.MULTILINE)
    return float(m.group(1)) if m else 0.0


def extract_device_block(text, device_key):
    """
    Return the text block for a device entry under result_by_device > passives_results,
    keyed by device_key (substring match on the device label line).
    """
    # Find lines like "    active.Q1.MOSFET_N:" and grab the indented content after
    pattern = rf"^\s+({re.escape(device_key)}[^:\n]*):\n((?:\s+\S.*\n)*)"
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches


def device_name_from_path(filepath):
    """Derive a human-readable device name from the file path."""
    base = os.path.basename(filepath)
    # Strip common suffixes
    name = re.sub(r"_output$", "", base)
    print("Derived name from path:", name)
    return name


def parse_file(filepath):
    """Parse one output file and return a dict of column → value."""
    with open(filepath, "r") as fh:
        text = fh.read()

    total = extract_value(text, "total_carbon")

    # Simple category totals
    categories = {}
    for col, keys in CATEGORY_MAP.items():
        categories[col] = sum(extract_value(text, k) for k in keys)

    return {
        "name": device_name_from_path(filepath),
        "Total": total,
        **categories,
    }


def write_csv(rows, output_path):
    header = CSV_COLUMNS[:]  # copy
    with open(output_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            line = [row["name"]] + [row.get(col, 0) for col in header[1:]]
            writer.writerow(line)
    print(f"Wrote {len(rows)} row(s) to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert ACT output files to CSV.")
    parser.add_argument("files", nargs="+", help="One or more output files to parse.")
    parser.add_argument(
        "-o", "--output", default="results.csv", help="Output CSV path (default: results.csv)"
    )
    args = parser.parse_args()

    rows = []
    for filepath in args.files:
        if not os.path.isfile(filepath):
            print(f"Warning: file not found, skipping: {filepath}", file=sys.stderr)
            continue
        try:
            rows.append(parse_file(filepath))
        except Exception as exc:
            print(f"Error parsing {filepath}: {exc}", file=sys.stderr)

    if not rows:
        print("No rows parsed – nothing to write.", file=sys.stderr)
        sys.exit(1)

    write_csv(rows, args.output)


if __name__ == "__main__":
    main()