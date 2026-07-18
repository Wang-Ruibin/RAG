"""Clean knowledge base markdown files.

Fixes:
1. Title line merged with first paragraph (no newline after # Title)
2. Duplicate content (full text appears 2-3 times)
3. Broken number spacing (e.g., "202 5" → "2025", "1 5" → "15")
4. Broken table formatting (repeated table headers)
"""

import os
import re
import sys
from pathlib import Path


def fix_title_merge(text: str) -> str:
    """Fix case where '# Title' is immediately followed by content without newline.

    Pattern: '# Title内容内容' or '# Title 内容内容'
    Should become: '# Title\n\n内容内容'
    """
    # Match headings (## or #) where content follows on same line
    text = re.sub(
        r'^(#{1,6}\s+.+?)([^\n#])(?!\s*http)',  # heading + immediately following content
        r'\1\n\2',
        text,
        flags=re.MULTILINE,
    )
    return text


def fix_spaced_numbers(text: str) -> str:
    """Fix broken number spacing like '202 5' -> '2025', '1 5' -> '15' in contexts where space is incorrect.

    Rules:
    - Year patterns: 202 5 -> 2025, 202 6 -> 2026, etc. (2XXX followed by space + digit)
    - Day patterns: 1 5 -> 15, 3 0 -> 30 when between digits
    - Chinese period+space+digit: 。1 -> 、1 (these are list items with 。instead of 、or .)
    
    Be careful not to break legitimate spaces.
    """
    # Fix year patterns: 202 5 -> 2025, 202 6 -> 2026, etc.
    text = re.sub(r'(?<!\d)(\d{3}) (\d)(?!\d)', r'\1\2', text)
    
    # Fix spaced decimal-like numbers: 1 5 -> 15 (when clearly a number)
    text = re.sub(r'(?<=\d) (\d)(?=\s*(?:[。，、；：年日月周星期天号时分秒]|$))', r'\1', text)
    
    # Fix "8 : 3 0" -> "8:30"
    text = re.sub(r'(\d)\s+:\s+(\d)\s+(\d)', r'\1:\2\3', text)
    
    # Fix "9 月" when it should be "9月" (but keep legitimate space before 月)
    # Actually in Chinese, numbers before units should NOT have space
    text = re.sub(r'(\d)\s+(?=[年月日周课时届号])', r'\1', text)
    
    return text


def fix_duplicate_content(text: str) -> str:
    """Remove duplicate paragraphs or repeated full text.

    Pattern: Same paragraph appears consecutively 2-3 times.
    Uses hash-based deduplication of consecutive blocks.
    """
    lines = text.split('\n')
    if len(lines) < 3:
        return text

    # Detect if first paragraph (non-empty, non-heading) appears again in first few lines
    # This handles the double/triple full-text issue
    cleaned = []
    seen_paragraphs = []
    consecutive_duplicates = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue
        
        # Normalize for comparison: collapse whitespace
        normalized = re.sub(r'\s+', ' ', stripped)
        
        if normalized in seen_paragraphs:
            consecutive_duplicates += 1
            # Skip if we've seen this exact paragraph before and it's the same context
            if consecutive_duplicates > 1:
                continue
        else:
            consecutive_duplicates = 0
            if len(stripped) > 30:  # Only track meaningful paragraphs
                seen_paragraphs.append(normalized)
        
        cleaned.append(line)
    
    return '\n'.join(cleaned)


def fix_table_formatting(text: str) -> str:
    """Fix broken markdown tables.

    1. Fix table lines with incorrect spacing
    2. Fix tables where header row appears multiple times
    """
    lines = text.split('\n')
    result = []
    
    in_table = False
    table_header = None
    header_repeated = 0
    
    for line in lines:
        if '|' in line and line.strip().startswith('|'):
            # Potential table line
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 2:
                if not in_table:
                    in_table = True
                    table_header = '|'.join(cells)
                    header_repeated = 0
                    result.append(line)
                else:
                    # Check if this is a repeated header
                    current_key = '|'.join(cells)
                    if current_key == table_header:
                        header_repeated += 1
                        if header_repeated > 1:
                            # Skip repeated header (keep separator and first header)
                            continue
                    result.append(line)
                continue
        elif in_table:
            in_table = False
            table_header = None
            header_repeated = 0
        
        result.append(line)
    
    return '\n'.join(result)


def clean_markdown(text: str) -> str:
    """Apply all cleaning steps in order."""
    # 1. Fix spaced numbers first
    text = fix_spaced_numbers(text)
    # 2. Fix title merge
    text = fix_title_merge(text)
    # 3. Fix duplicate content
    # text = fix_duplicate_content(text)  # Let's be careful with this
    # 4. Fix table formatting
    text = fix_table_formatting(text)
    return text


def process_directory(knowledge_dir: str, dry_run: bool = False):
    """Process all .md files in the knowledge directory."""
    import sys
    
    # Ensure stdout can handle Unicode
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    knowledge_path = Path(knowledge_dir)
    if not knowledge_path.exists():
        print(f"ERROR: Directory not found: {knowledge_dir}")
        return

    md_files = sorted(knowledge_path.rglob("*.md"))
    print(f"Found {len(md_files)} .md files in {knowledge_dir}")

    stats = {"fixed_title_merge": 0, "fixed_numbers": 0, "fixed_table": 0, "errors": 0}
    modified_files = []

    for fp in md_files:
        rel = str(fp.relative_to(knowledge_path))
        try:
            text = fp.read_text(encoding="utf-8")
            original = text
            
            text = clean_markdown(text)
            
            if text != original:
                diff_lines = len(text.split('\n')) - len(original.split('\n'))
                modified_files.append((rel, diff_lines))
                
                if not dry_run:
                    fp.write_text(text, encoding="utf-8")
                
                if '#' in text[:100] and '\n\n' in text[:100]:
                    stats["fixed_title_merge"] += 1
            
            # Count number fixes
            number_fixes = len(re.findall(r'(?<!\d)\d{3} \d(?!\d)', original)) - len(re.findall(r'(?<!\d)\d{3} \d(?!\d)', text))
            if number_fixes > 0:
                stats["fixed_numbers"] += 1
                
        except Exception as e:
            print(f"  [ERROR] {rel}: {e}")
            stats["errors"] += 1

    # Write report to file
    report_dir = Path(__file__).resolve().parent.parent / "data"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "clean_report.txt"
    
    with open(report_path, "w", encoding="utf-8") as report:
        report.write(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}\n")
        report.write(f"Directory: {knowledge_dir}\n")
        report.write(f"Files processed: {len(md_files)}\n\n")
        
        if modified_files:
            report.write("Modified files:\n")
            for name, changes in modified_files:
                report.write(f"  {name} ({changes} line changes)\n")
        
        report.write(f"\n=== Summary ===\n")
        report.write(f"  Files processed: {len(md_files)}\n")
        report.write(f"  Files modified: {len(modified_files)}\n")
        report.write(f"  Title-merge fixes: {stats['fixed_title_merge']}\n")
        report.write(f"  Number spacing fixes: {stats['fixed_numbers']}\n")
        report.write(f"  Table fixes: {stats['fixed_table']}\n")
        report.write(f"  Errors: {stats['errors']}\n")
    
    # Print summary only
    print(f"Files processed: {len(md_files)}")
    print(f"Files modified: {len(modified_files)}")
    print(f"Title-merge fixes: {stats['fixed_title_merge']}")
    print(f"Number spacing fixes: {stats['fixed_numbers']}")
    print(f"Table fixes: {stats['fixed_table']}")
    print(f"Errors: {stats['errors']}")
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    knowledge_dir = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else None
    
    if knowledge_dir is None:
        # Default: project root / knowledge
        script_dir = Path(__file__).resolve().parent.parent.parent  # hhu-rag/
        knowledge_dir = script_dir / "knowledge"
    else:
        knowledge_dir = Path(knowledge_dir)
    
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Directory: {knowledge_dir}")
    process_directory(knowledge_dir, dry_run=dry_run)
    
    if dry_run:
        print("\nRun without --dry-run to apply changes.")
