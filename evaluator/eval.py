import re
import sys
from dataclasses import dataclass

@dataclass
class ParsedSymbol:
    """Holds the full lines that define a symbol and its context."""
    output_section_line: str
    input_section_line: str
    symbol_line: str

def parse_map_file_by_positional_logic(filepath: str) -> list[ParsedSymbol]:
    """
    Parses a map file based on matching the position of the first non-numeric
    text on a line to the starting position of the 'Out', 'In', or 'Symbol'
    header fields.
    """
    results = []
    lines = []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # --- Step 1: Find header and the positions of the key fields ---
    header_fields_to_find = ['Out', 'In', 'Symbol']
    field_positions = {}
    header_line_index = -1

    for i, line in enumerate(lines):
        if 'VMA' in line and 'Symbol' in line:
            header_line_index = i
            for field in header_fields_to_find:
                try:
                    field_positions[field] = line.index(field)
                except ValueError:
                    print(f"Warning: Header field '{field}' not found.", file=sys.stderr)
            break

    if not field_positions:
        print("Error: Could not find a valid header line to determine column positions.", file=sys.stderr)
        return []

    # --- Step 2: Process data lines using positional logic and a state machine ---
    current_out_line = ""
    current_in_line = ""

    for line in lines[header_line_index + 1:]:
        line = line.rstrip()
        if not line.strip():
            continue

        # Find the starting position of the first meaningful text on the line.
        # This searches for the first character that isn't a digit, hex char, or space.
        match = re.search(r'[^0-9a-fA-Fx\s]', line)
        if not match:
            continue
        data_start_pos = match.start()

        # Determine which field ('Out', 'In', 'Symbol') is closest to this position.
        closest_field = min(
            field_positions.keys(),
            key=lambda field: abs(data_start_pos - field_positions[field])
        )

        # --- Step 3: Update state or record the symbol based on the line type ---
        line_content = line.strip()

        if closest_field == 'Out':
            # This line defines the new 'Out' context.
            current_out_line = line_content
            current_in_line = ""  # An 'Out' update resets the 'In' context.
        elif closest_field == 'In':
            # This line defines the new 'In' context.
            current_in_line = line_content
        elif closest_field == 'Symbol':
            # This line is a symbol. Record it with the current context.
            results.append(ParsedSymbol(
                output_section_line=current_out_line,
                input_section_line=current_in_line,
                symbol_line=line_content
            ))

    return results

def print_parsed_symbols(parsed_data: list[ParsedSymbol]):
    """Prints the results of the parsing."""
    print("--- Parsed Symbol Contexts ---")
    if not parsed_data:
        print("No symbols were parsed.")
        return

    for i, item in enumerate(parsed_data):
        print(f"\n[Symbol #{i+1}]")
        print(f"  OUT CONTEXT : {item.output_section_line}")
        print(f"  IN CONTEXT  : {item.input_section_line}")
        print(f"  SYMBOL LINE : {item.symbol_line}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_map.py <map_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    parsed_results = parse_map_file_by_positional_logic(filepath)
    print_parsed_symbols(parsed_results)
