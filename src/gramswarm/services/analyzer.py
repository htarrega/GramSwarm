import json
import pathlib
from typing import List, Dict
from ..core.models import ChunkTrace


class RunAnalyzer:
    """
    Analyzes completed runs to extract narrative signals.
    """
    def __init__(self, run_dir: str):
        self.run_dir = pathlib.Path(run_dir)

    def analyze_pressure(self) -> Dict[str, List[float]]:
        """
        Calculates the average continue_pressure per chunk across clusters.
        Returns {cluster_name: [mean_pressure_chunk_0, ...]}
        """
        cluster_data: Dict[str, List[List[int]]] = {}

        for cluster_dir in self.run_dir.iterdir():
            if not cluster_dir.is_dir():
                continue

            cluster_name = cluster_dir.name
            all_reader_pressures: List[List[int]] = []

            for reader_dir in cluster_dir.iterdir():
                if not reader_dir.is_dir():
                    continue

                chunks = sorted(reader_dir.glob("chunk_*.json"))
                reader_pressures = []
                for chunk_file in chunks:
                    try:
                        data = json.loads(chunk_file.read_text(encoding="utf-8"))
                        trace = ChunkTrace.model_validate(data)
                        reader_pressures.append(trace.continue_pressure)
                    except Exception:
                        continue

                if reader_pressures:
                    all_reader_pressures.append(reader_pressures)

            if all_reader_pressures:
                num_chunks = len(all_reader_pressures[0])
                means = []
                for i in range(num_chunks):
                    vals = [r[i] for r in all_reader_pressures if i < len(r)]
                    means.append(sum(vals) / len(vals))
                cluster_data[cluster_name] = means

        return cluster_data

    def analyze_abandons(self) -> Dict[str, List[bool]]:
        """
        Returns {cluster_name: [any_reader_abandons_chunk_0, ...]}
        """
        cluster_data: Dict[str, List[List[bool]]] = {}

        for cluster_dir in self.run_dir.iterdir():
            if not cluster_dir.is_dir():
                continue

            cluster_name = cluster_dir.name
            all_reader_abandons: List[List[bool]] = []

            for reader_dir in cluster_dir.iterdir():
                if not reader_dir.is_dir():
                    continue

                chunks = sorted(reader_dir.glob("chunk_*.json"))
                reader_abandons = []
                for chunk_file in chunks:
                    try:
                        data = json.loads(chunk_file.read_text(encoding="utf-8"))
                        trace = ChunkTrace.model_validate(data)
                        reader_abandons.append(trace.would_abandon)
                    except Exception:
                        reader_abandons.append(False)

                if reader_abandons:
                    all_reader_abandons.append(reader_abandons)

            if all_reader_abandons:
                num_chunks = len(all_reader_abandons[0])
                cluster_data[cluster_name] = [
                    any(r[i] for r in all_reader_abandons if i < len(r))
                    for i in range(num_chunks)
                ]

        return cluster_data

    def render_ascii_chart(self, cluster_data: Dict[str, List[float]], abandon_data: Dict[str, List[bool]] = None):
        """
        Renders a dense ASCII bar chart of the pressure.
        """
        print("\n--- CONTINUITY PRESSURE ANALYSIS ---")

        if not cluster_data:
            print("\n  No analysis data found for this run.")
            print("\nPossible reasons:")
            print("  - The run directory is empty or contains no reader folders.")
            print("  - The trace files (.json) do not exist or could not be parsed.")
            print("  - The metrics in the files are malformed.")
            print("\nCheck the files in the run directory to verify the output format.")
            return

        max_scale = 5
        for cluster, pressures in cluster_data.items():
            print(f"\nCluster: {cluster}")
            abandons = (abandon_data or {}).get(cluster, [])
            for i, p in enumerate(pressures):
                filled = int(round(p))
                bar = "█" * filled + "░" * (max_scale - filled)
                danger = "  !!" if i < len(abandons) and abandons[i] else ""
                print(f"  Chunk {i + 1}: {bar}  ({p:.1f}){danger}")
