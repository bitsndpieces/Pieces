import os
import re
import json
import clang
from clang import cindex

# Define known ECK/ECC qualifiers and their metadata
QUALIFIERS = {
    "OPAQUE":  {"target": "Function argument",  "input": None,      "usage": "Pointer type"},
    "STRING":  {"target": "Function argument",  "input": None,      "usage": "strlen used"},
    "LEN":     {"target": "Function argument",  "input": "Integer", "usage": "Uses AR-th argument"},
    "SIZE":    {"target": "Function argument",  "input": "Integer", "usage": "Copies SI bytes"},
    "UTILITY": {"target": "Function prototype", "input": None,      "usage": "Utility access"},
    "USER":    {"target": "Function prototype", "input": None,      "usage": "Global access"},
    "SHARED":  {"target": "Global Object",      "input": None,      "usage": "Shared across compartments"},
    "CUSTOM":  {"target": "Function prototype", "input": None,      "usage": "Custom bridge"},
}

# Regex to match all qualifiers including optional parameters (e.g., LEN(2), SIZE(3))
QUALIFIER_REGEX = re.compile(r'\b(' + '|'.join(QUALIFIERS.keys()) + r')(?:\(([^)]+)\))?')

def extract_qualifiers_from_line(line):
    """Extract qualifiers and parameters from a line of code."""
    return [
        {"qualifier": match.group(1), "param": match.group(2)}
        for match in QUALIFIER_REGEX.finditer(line)
    ]

def visit_node(node, results, file_cache):
    """Recursively visit AST nodes and extract qualifier metadata."""
    if node.location.file is None:
        return
    file_path = node.location.file.name
    line_no = node.location.line

    if file_path not in file_cache:
        with open(file_path, 'r') as f:
            file_cache[file_path] = f.readlines()

    line = file_cache[file_path][line_no - 1]
    qualifiers = extract_qualifiers_from_line(line)

    for q in qualifiers:
        entry = {
            "qualifier": q["qualifier"],
            "target": QUALIFIERS[q["qualifier"]]["target"],
            "input": QUALIFIERS[q["qualifier"]]["input"],
            "usage": QUALIFIERS[q["qualifier"]]["usage"],
            "details": {
                "name": node.spelling,
                "param": q["param"],
                "location": f"{file_path}:{line_no}"
            }
        }
        results.append(entry)

    for child in node.get_children():
        if child.kind in (
            cindex.CursorKind.FUNCTION_DECL,
            cindex.CursorKind.VAR_DECL,
            cindex.CursorKind.PARM_DECL
        ):
            visit_node(child, results, file_cache)

def parse_project(path):
    """Parse all C/C++ files in a given path."""
    index = cindex.Index.create()
    results = []
    file_cache = {}

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(('.c', '.cpp', '.h', '.hpp')):
                full_path = os.path.join(root, file)
                try:
                    tu = index.parse(full_path, args=['-std=c11'])
                    visit_node(tu.cursor, results, file_cache)
                except Exception as e:
                    print(f"Error parsing {full_path}: {e}")

    return results

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(description="Parse ECK/ECC qualifiers from C/C++ project")
    parser.add_argument("project", help="Path to C/C++ project")
    parser.add_argument("--output", help="Output JSON file", default="eck_output.json")
    args = parser.parse_args()
    clang.cindex.Config.set_library_path(os.environ["LIBCLANG"])
    print("Libclang version:", cindex.conf.lib.clang_Version)

    result = parse_project(args.project)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {len(result)} entries to {args.output}")

