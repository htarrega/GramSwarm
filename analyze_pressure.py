import os
import re
import sys
from collections import defaultdict

def parse_trace(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    chunks = re.split(r'## Chunk \d+', content)
    chunk_data = []
    for chunk_text in chunks[1:]:
        pressure_match = re.search(r'Continue pressure:.*?(\d)/5', chunk_text)
        abandon_match = re.search(r'Would abandon:.*?(yes|no)', chunk_text, re.IGNORECASE)
        if abandon_match:
            abandoned = abandon_match.group(1).lower() == 'yes'
        else:
            json_abandon = re.search(r'{"abandon":\s*(true|false)}', chunk_text, re.IGNORECASE)
            abandoned = json_abandon.group(1).lower() == 'true' if json_abandon else False
        pressure = int(pressure_match.group(1)) if pressure_match else None
        chunk_data.append({'pressure': pressure, 'abandoned': abandoned})
    return chunk_data

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_pressure.py <run_folder>")
        sys.exit(1)

    root_dir = sys.argv[1]
    if not os.path.exists(root_dir):
        alt_dir = os.path.join("runs", root_dir)
        if os.path.exists(alt_dir):
            root_dir = alt_dir
        else:
            print(f"Error: Run folder '{root_dir}' not found.")
            sys.exit(1)

    cluster_pressures = defaultdict(lambda: defaultdict(list))
    cluster_abandon = defaultdict(lambda: defaultdict(bool))

    try:
        clusters = sorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])
    except Exception as e:
        print(f"Error accessing {root_dir}: {e}")
        sys.exit(1)

    for cluster in clusters:
        cluster_path = os.path.join(root_dir, cluster)
        try:
            readers = os.listdir(cluster_path)
        except Exception:
            continue
            
        for reader in readers:
            trace_path = os.path.join(cluster_path, reader, 'trace.md')
            if os.path.exists(trace_path):
                data = parse_trace(trace_path)
                if data:
                    for i, chunk in enumerate(data):
                        if chunk['pressure'] is not None:
                            cluster_pressures[cluster][i].append(chunk['pressure'])
                        if chunk['abandoned']:
                            cluster_abandon[cluster][i] = True

    if not cluster_pressures:
        print("No valid trace data found in the specified run.")
        return

    for cluster in sorted(cluster_pressures.keys()):
        print(f"\n{cluster}\n" + "=" * len(cluster))
        pressures_dict = cluster_pressures[cluster]
        abandon_dict = cluster_abandon[cluster]
        max_chunk = max(pressures_dict.keys()) + 1 if pressures_dict else 0
        
        for i in range(max_chunk):
            pressures = pressures_dict.get(i, [])
            mean_pressure = sum(pressures) / len(pressures) if pressures else 0
            abandoned = abandon_dict.get(i, False)
            
            bar_length = int(mean_pressure * 2)
            bar = "█" * bar_length + " " * (10 - bar_length)
            
            if abandoned:
                stop_reading_sign = " !"
            else:
                stop_reading_sign = " "
            
            print(f"C{i+1:02}: [{bar}] {mean_pressure:.1f}{stop_reading_sign}")

if __name__ == "__main__":
    main()
