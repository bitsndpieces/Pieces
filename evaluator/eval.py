import re
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class SectionInfo:
    """Holds the parsed data for an In or Out section header."""
    Type: str
    Name: str
    VMA: int
    LMA: int
    Size: int
    Align: int

@dataclass
class Symbol:
    """Holds the parsed components of a symbol and its context."""
    VMA: int
    LMA: int
    Size: int
    Align: int
    Out: Optional[SectionInfo]
    In: Optional[SectionInfo]  # Now also a SectionInfo object
    Section: str # The specific sub-section from the input, e.g., '(.text.main)'
    Symbol: str

def parse_map_file(filepath: str) -> Tuple[List[SectionInfo], List[Symbol]]:
    """
    Parses a map file, capturing both detailed section information and symbols,
    and links each symbol to its parent input and output section objects.
    """
    sections, symbols, lines = [], [], []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # --- Step 1: Find header and dynamically calculate reference spacings ---
    header_line = ""
    header_line_index = -1
    for i, line in enumerate(lines):
        if 'VMA' in line and 'Align' in line and 'Symbol' in line:
            header_line = line
            header_line_index = i
            break
    if not header_line:
        print("Error: Could not find a valid header line.", file=sys.stderr)
        return [], []
    try:
        align_header_end = header_line.index('Align') + len('Align')
        ref_spaces_out = header_line.index('Out') - align_header_end
        ref_spaces_in = header_line.index('In') - align_header_end
        ref_spaces_symbol = header_line.index('Symbol') - align_header_end
    except ValueError as e:
        print(f"Error: A required field is missing from the header: {e}", file=sys.stderr)
        return [], []

    # --- Step 2: Process data lines with state machine ---
    current_out_section_obj: Optional[SectionInfo] = None
    current_in_section_obj: Optional[SectionInfo] = None
    current_sub_section_name = "" # e.g., the '(.text.main)' part
    
    line_parser_re = re.compile(r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)')

    for line in lines[header_line_index + 1:]:
        line = line.rstrip()
        if not line.strip() or ". = ALIGN" in line: continue

        component_match = line_parser_re.match(line)
        if not component_match: continue

        vma_str, lma_str, size_str, align_str = component_match.groups()
        align_data_end_pos = component_match.end(4)

        remainder_text_start_pos = -1
        for i in range(align_data_end_pos, len(line)):
            if not line[i].isspace():
                remainder_text_start_pos = i
                break
        if remainder_text_start_pos == -1: continue

        remainder = line[remainder_text_start_pos:]
        actual_spaces = remainder_text_start_pos - align_data_end_pos

        dist_to_out = abs(actual_spaces - ref_spaces_out)
        dist_to_in = abs(actual_spaces - ref_spaces_in)
        dist_to_symbol = abs(actual_spaces - ref_spaces_symbol)
        min_dist = min(dist_to_out, dist_to_in, dist_to_symbol)

        line_type = 'Symbol'
        if min_dist == dist_to_out and min_dist <= 2: line_type = 'Out'
        elif min_dist == dist_to_in and min_dist <= 2: line_type = 'In'

        try:
            vma, lma, size = int(vma_str, 16), int(lma_str, 16), int(size_str, 16)
            align = int(align_str, 10)
        except (ValueError, TypeError):
            vma, lma, size, align = 0, 0, 0, 0

        if line_type == 'Out':
            section_obj = SectionInfo('Out', remainder, vma, lma, size, align)
            sections.append(section_obj)
            current_out_section_obj = section_obj
            current_in_section_obj = None # Reset In context when Out changes
            current_sub_section_name = ""
        elif line_type == 'In':
            section_obj = SectionInfo('In', remainder, vma, lma, size, align)
            sections.append(section_obj)
            current_in_section_obj = section_obj
            # Try to parse the sub-section like '(.text)' from the name
            in_match = re.search(r'\((.*)\)', remainder)
            current_sub_section_name = in_match.group(1) if in_match else ""
        else: # line_type == 'Symbol'
            symbols.append(Symbol(vma, lma, size, align, current_out_section_obj, current_in_section_obj, current_sub_section_name, remainder))

    return sections, symbols

def print_output_sections(all_sections: List[SectionInfo]):
    out_sections = [s for s in all_sections if s.Type == 'Out']
    if not out_sections: return
    print("## Output Memory Sections")
    print("-" * 75)
    print(f"{'Name':<40} {'VMA':<12} {'LMA':<12} {'Size':<8}")
    print("-" * 75)
    for sec in out_sections:
        if (sec.Size) == 0:
            continue
        print(f"{sec.Name:<40} {sec.VMA:<#12x} {sec.LMA:<#12x} {sec.Size:<#8x}")
    print("-" * 75)

def print_input_sections(all_sections: List[SectionInfo]):
    in_sections = [s for s in all_sections if s.Type == 'In']
    if not in_sections: return
    print("\n## Input Memory Sections")
    print("-" * 75)
    print(f"{'Name':<40} {'VMA':<12} {'LMA':<12} {'Size':<8}")
    print("-" * 75)
    for sec in in_sections:
        print(f"{sec.Name:<40} {sec.VMA:<#12x} {sec.LMA:<#12x} {sec.Size:<#8x}")
    print("-" * 75)

def print_symbols(symbols: List[Symbol]):
    if not symbols:
        print("\n## Symbols\n-- No symbols found --")
        return
    print("\n## Symbols")
    print("-" * 160)
    print(f"{'VMA':<12} {'LMA':<12} {'Size':<8} {'Align':<6} {'Out':<30} {'In':<40} {'Section':<20} Symbol")
    print("-" * 160)
    for sym in symbols:
        out_name = sym.Out.Name if sym.Out else "N/A"
        in_name = sym.In.Name if sym.In else "N/A"
        print(f"{sym.VMA:<#12x} {sym.LMA:<#12x} {sym.Size:<#8x} {sym.Align:<6d} {out_name:<30} {in_name:<40} {sym.Section:<20} {sym.Symbol}")
    print("-" * 160)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_map.py <map_file>")
        sys.exit(1)
    filepath = sys.argv[1]
    parsed_sections, parsed_symbols = parse_map_file(filepath)


    #Get data reduction
    total_out_size = 0
    for section in parsed_sections:
        if section.Type == 'Out':
            total_out_size += section.Size

    FreeRTOS = False
    for sym in parsed_symbols:
        if "xTaskCreate" in sym.Symbol:
            FreeRTOS= True


    for sec in parsed_sections:
        if re.fullmatch(r'\.osection\d+', sec.Name) or re.fullmatch(r'\.osection\d+data', sec.Name):
            #TODO: or maybe hack but in FreeRTOS 4K of stack is silently mapped, account here if FreeRTOS
            if (FreeRTOS):
                    sec.Size = sec.Size + 4096
            print(f"{sec.Name} reduced from {total_out_size} to {sec.Size}")
            print(f"Reduction:    {((total_out_size-sec.Size)/total_out_size * 100.0)} %")


    
        

