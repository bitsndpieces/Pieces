import sys
import os
import json
import re
from clang.cindex import Index, CursorKind, Config

# --- Library Configuration ---
# If libclang is not in your system's default path, you MUST specify its location.
# Config.set_library_file("/path/to/your/libclang.so")

def get_annotate_qualifiers(cursor):
    """
    Extracts and parses __attribute__((annotate("..."))) qualifiers.
    Handles both simple ("USER") and complex ("LEN(2)") annotations,
    returning a structured list of dictionaries.
    """
    qualifiers = []
    for child in cursor.get_children():
        if child.kind == CursorKind.ANNOTATE_ATTR:
            raw_text = child.spelling  # This is the string inside annotate(), e.g., "USER" or "LEN(2)"

            # Use a regular expression to capture the name and optional arguments.
            # This robustly handles both NAME and NAME(ARGS) formats.
            match = re.match(r"([A-Z_a-z]+)(?:\((.*?)\))?$", raw_text)

            if match:
                name = match.group(1)
                args_str = match.group(2)

                parsed_qualifier = {"name": name}
                if args_str is not None:
                    # If arguments exist, split them by comma and strip whitespace
                    args = [arg.strip() for arg in args_str.split(',')]
                    parsed_qualifier["args"] = args
                else:
                    # If no arguments, use an empty list
                    parsed_qualifier["args"] = []

                qualifiers.append(parsed_qualifier)

    return qualifiers

def process_function(cursor):
    """Builds a dictionary containing key information about a function."""
    return {
        "name": cursor.spelling,
        "location": f"{os.path.basename(str(cursor.location.file))}:{cursor.location.line}",
        "is_definition": cursor.is_definition(),
        "return_type": cursor.result_type.spelling,
        "qualifiers": get_annotate_qualifiers(cursor),
        "args": [
            {
                "name": arg.spelling or "unnamed",
                "type": arg.type.spelling,
                "qualifiers": get_annotate_qualifiers(arg)
            }
            for arg in cursor.get_arguments()
        ]
    }

def parse_directory(directory, clang_args):
    """
    Parses source files in a directory using the provided clang arguments.
    """
    index = Index.create()
    functions = []

    if not os.path.isdir(directory):
        print(f"❌ Error: Directory '{directory}' not found.", file=sys.stderr)
        return None

    print(f"🔍 Starting analysis in directory: {directory}")
    for root, _, files in os.walk(directory):
        for filename in files:
            if not filename.endswith((".c", ".cpp", ".cc", ".h", ".hpp")):
                continue

            filepath = os.path.join(root, filename)
            
            if filename.endswith(".c"):
                current_args = ['-x', 'c', '-std=c11'] + clang_args
            else:
                current_args = ['-x', 'c++', '-std=c++11'] + clang_args

            try:
                print(f"   Parsing {filepath}...")
                tu = index.parse(filepath, args=current_args)

                errors = [d for d in tu.diagnostics if d.severity >= d.Error]
                if errors:
                    print(f"   -> ❗️ Skipping due to {len(errors)} parsing error(s):", file=sys.stderr)
                    for diag in errors:
                        print(f"      - {diag.spelling}", file=sys.stderr)
                    continue

                for node in tu.cursor.walk_preorder():
                    if (node.kind == CursorKind.FUNCTION_DECL and
                            node.location.file and
                            node.location.file.name == filepath):
                        functions.append(process_function(node))

            except Exception as e:
                print(f"   -> 🚨 An unexpected error occurred: {e}", file=sys.stderr)

    return functions

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <source_directory> [clang_flags...]")
        print(f"Example: python {sys.argv[0]} ./src -isystem /usr/include -I./local/include")
        sys.exit(1)

    source_directory = sys.argv[1]
    clang_flags = sys.argv[2:]

    results = parse_directory(source_directory, clang_flags)
    if results is not None:
        output_filename = "out/eck_output.json"
        output_dir = os.path.dirname(output_filename)
        os.makedirs(output_dir, exist_ok=True)

        with open(output_filename, "w") as out_file:
            json.dump(results, out_file, indent=2)
            print(f"\n✅ Success! Wrote {len(results)} function declarations to {output_filename}")
