import pathlib
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ReaderProfile:
    name: str
    cluster: str
    content: str
    path: pathlib.Path


class ProfileLoader:

    def __init__(self, profiles_dir: str = "readers_profiles"):
        self.profiles_dir = pathlib.Path(profiles_dir)

    def load_all(self) -> List[ReaderProfile]:
        profiles = []
        if not self.profiles_dir.exists():
            return profiles

        for cluster_dir in self.profiles_dir.iterdir():
            if not cluster_dir.is_dir():
                continue
            for profile_file in cluster_dir.glob("*.md"):
                profiles.append(ReaderProfile(
                    name=profile_file.stem,
                    cluster=cluster_dir.name,
                    content=profile_file.read_text(encoding="utf-8"),
                    path=profile_file,
                ))
        return profiles
