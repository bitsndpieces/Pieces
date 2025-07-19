import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SymbolEntry:
    vma: int
    lma: int
    size: int
    align: int
    out_section: Optional[str]
    in_object: Optional[str]
    symbol: Optional[str]


@dataclass
class MapFile:
    entries: List[SymbolEntry] = field(default_factory=list)

    def parse(self, path: str):
        section = None
        current_entry = None
        map_path = Path(path)

        if not map_path.exists():
            raise FileNotFoundError(f"Map file '{path}' does not exist.")

        with open(map_path) as f:
            lines = f.readlines()

        pattern = re.compile(
            r"^\s*(?P<vma>[0-9a-fA-F]+)?\s+(?P<lma>[0-9a-fA-F]+)?\s+(?P<size>[0-9a-fA-F]+)?\s+(?P<align>\d+)?\s*(?P<out>\S+)?\s*(?P<in>\S+)?\s*(?P<symbol>\S+)?"
        )

        for line in lines:
            if line.strip().startswith("Linker script and memory map"):
                continue

            match = pattern.match(line)
            if not match:
                continue

            groups = match.groupdict()
            try:
                vma = int(groups["vma"], 16) if groups["vma"] else 0
                lma = int(groups["lma"], 16) if groups["lma"] else 0
                size = int(groups["size"], 16) if groups["size"] else 0
                align = int(groups["align"]) if groups["align"] else 0
            except ValueError:
                continue

            entry = SymbolEntry(
                vma=vma,
                lma=lma,
                size=size,
                align=align,
                out_section=groups["out"],
                in_object=groups["in"],
                symbol=groups["symbol"],
            )
            self.entries.append(entry)

    def dump(self, limit=10):
        for i, e in enumerate(self.entries[:limit]):
            print(
                f"{i}: {e.out_section or '':10s} | {e.symbol or '':20s} | "
                f"VMA: 0x{e.vma:08x} | Size: {e.size:6d} | File: {e.in_object or ''}"
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <map_file>")
        sys.exit(1)

    map_file_path = sys.argv[1]
    parser = MapFile()
    try:
        parser.parse(map_file_path)
        parser.dump(20)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
