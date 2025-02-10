import json
import sys
import argparse
from collections import defaultdict
from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import Terminal256Formatter

def load_coverage(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def read_file_content(filename):
    try:
        with open(filename, 'r') as f:
            return f.readlines()
    except FileNotFoundError:
        return None

def extract_line_coverage(file_data):
    line_coverage = {}
    for segment in file_data['segments']:
        line = segment[0]
        count = segment[2]
        line_coverage[line] = count
    return line_coverage

def compare_coverages(coverage1, coverage2):
    diff = defaultdict(lambda: defaultdict(dict))
    
    files1 = {file['filename']: file for file in coverage1['data'][0]['files']}
    files2 = {file['filename']: file for file in coverage2['data'][0]['files']}
    
    for filename, file1 in files1.items():
        if filename not in files2:
            continue
        
        file2 = files2[filename]
        
        lines1 = extract_line_coverage(file1)
        lines2 = extract_line_coverage(file2)
        
        different_lines = [line for line in set(lines1.keys()) | set(lines2.keys())
                           if lines1.get(line, 0) != lines2.get(line, 0)]
        
        if different_lines:
            diff[filename]['lines'] = sorted(different_lines)
            diff[filename]['coverage1'] = lines1
            diff[filename]['coverage2'] = lines2
    
    return diff

def print_code_with_diff(filename, file_diff, context=10):
    content = read_file_content(filename)
    if content is None:
        print(f"Error: Could not read file {filename}")
        return

    lexer = guess_lexer_for_filename(filename, ''.join(content))
    formatter = Terminal256Formatter()
    
    print(f"\n=== File: {filename} ===")
    print("Lines with coverage differences:")
    
    # Group differences by type
    only_in_1 = []
    only_in_2 = []
    count_diff = []
    
    for line in file_diff['lines']:
        cov1 = file_diff['coverage1'].get(line, 0)
        cov2 = file_diff['coverage2'].get(line, 0)
        if cov1 == 0:
            only_in_2.append(line)
        elif cov2 == 0:
            only_in_1.append(line)
        else:
            count_diff.append(line)
    
    if only_in_1:
        print("\nLines covered only in first run:", ', '.join(map(str, only_in_1)))
    if only_in_2:
        print("\nLines covered only in second run:", ', '.join(map(str, only_in_2)))
    if count_diff:
        print("\nLines with different hit counts:", ', '.join(map(str, count_diff)))
    
    # Print the actual code context
    print("\nDetailed differences with context:")
    print("=" * 60)
    
    ranges_to_print = []
    current_range = None
    for line in sorted(file_diff['lines']):
        if current_range is None or line > current_range[1] + context:
            if current_range:
                ranges_to_print.append(current_range)
            current_range = [max(1, line - context), min(len(content), line + context)]
        else:
            current_range[1] = min(len(content), line + context)
    if current_range:
        ranges_to_print.append(current_range)

    for i, (start, end) in enumerate(ranges_to_print):
        if i > 0:
            print("\n" + "." * 40 + "\n")  # Visual separator between sections

        for j in range(start, end + 1):
            cov1 = file_diff['coverage1'].get(j, 0)
            cov2 = file_diff['coverage2'].get(j, 0)

            if j in file_diff['lines']:
                prefix = f"\033[91m→ {j:4d} [{cov1:3d} → {cov2:3d}]:\033[0m "  # Red arrow for changed lines
                highlighted_line = highlight(content[j-1].rstrip(), lexer, formatter).rstrip()
                print(f"{prefix}\033[91m{highlighted_line}\033[0m")
            else:
                prefix = f"  {j:4d}           : "  # Aligned with the format above
                highlighted_line = highlight(content[j-1].rstrip(), lexer, formatter).rstrip()
                print(f"{prefix}{highlighted_line}")

def print_summary(diff):
    print("\nCoverage Difference Summary")
    print("==========================")
    total_files = len(diff)
    total_lines = sum(len(file_diff['lines']) for file_diff in diff.values())
    
    print(f"\nFound differences in {total_files} files, total of {total_lines} lines differ\n")
    
    for filename, file_diff in diff.items():
        diff_lines = len(file_diff['lines'])
        print(f"\n{filename}:")
        print(f"  {diff_lines} lines with coverage differences")

def main():
    parser = argparse.ArgumentParser(description="Compare LLVM coverage data")
    parser.add_argument("coverage1", help="First coverage JSON file")
    parser.add_argument("coverage2", help="Second coverage JSON file")
    parser.add_argument("-c", "--context", type=int, default=5, help="Number of context lines (default: 5)")
    args = parser.parse_args()

    coverage1 = load_coverage(args.coverage1)
    coverage2 = load_coverage(args.coverage2)
    
    diff = compare_coverages(coverage1, coverage2)
    print_summary(diff)
    for filename, file_diff in diff.items():
        print_code_with_diff(filename, file_diff, context=args.context)

if __name__ == '__main__':
    main()
