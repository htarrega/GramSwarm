import pytest
from pathlib import Path
from gramswarm.core.reader import ReaderProfile, ProfileLoader


class TestReaderProfile:
    def test_is_frozen(self):
        profile = ReaderProfile(name="Alice", cluster="Sci-Fi", content="text", path=Path("p.md"))
        with pytest.raises(Exception):
            profile.name = "Bob"  # type: ignore[misc]

    def test_stores_all_fields(self):
        p = Path("readers_profiles/SciFi/alice.md")
        profile = ReaderProfile(name="alice", cluster="SciFi", content="I love space", path=p)
        assert profile.name == "alice"
        assert profile.cluster == "SciFi"
        assert profile.content == "I love space"
        assert profile.path == p


class TestProfileLoader:
    def test_load_all_returns_empty_when_dir_missing(self, tmp_path):
        loader = ProfileLoader(profiles_dir=str(tmp_path / "nonexistent"))
        assert loader.load_all() == []

    def test_load_all_reads_profiles(self, tmp_path):
        cluster_dir = tmp_path / "Fantasy"
        cluster_dir.mkdir()
        (cluster_dir / "reader_a.md").write_text("Profile A", encoding="utf-8")
        (cluster_dir / "reader_b.md").write_text("Profile B", encoding="utf-8")

        loader = ProfileLoader(profiles_dir=str(tmp_path))
        profiles = loader.load_all()

        assert len(profiles) == 2
        names = {p.name for p in profiles}
        assert names == {"reader_a", "reader_b"}

    def test_load_all_sets_cluster_from_folder_name(self, tmp_path):
        cluster_dir = tmp_path / "Thriller"
        cluster_dir.mkdir()
        (cluster_dir / "reader_x.md").write_text("content", encoding="utf-8")

        loader = ProfileLoader(profiles_dir=str(tmp_path))
        profiles = loader.load_all()

        assert profiles[0].cluster == "Thriller"

    def test_load_all_reads_multiple_clusters(self, tmp_path):
        for cluster in ("Fantasy", "SciFi", "Horror"):
            d = tmp_path / cluster
            d.mkdir()
            (d / "r.md").write_text(f"{cluster} reader", encoding="utf-8")

        loader = ProfileLoader(profiles_dir=str(tmp_path))
        profiles = loader.load_all()

        clusters = {p.cluster for p in profiles}
        assert clusters == {"Fantasy", "SciFi", "Horror"}

    def test_load_all_ignores_non_md_files(self, tmp_path):
        cluster_dir = tmp_path / "Fantasy"
        cluster_dir.mkdir()
        (cluster_dir / "reader.md").write_text("good", encoding="utf-8")
        (cluster_dir / "notes.txt").write_text("ignored", encoding="utf-8")

        loader = ProfileLoader(profiles_dir=str(tmp_path))
        profiles = loader.load_all()

        assert len(profiles) == 1

    def test_load_all_profile_content_matches_file(self, tmp_path):
        cluster_dir = tmp_path / "SciFi"
        cluster_dir.mkdir()
        (cluster_dir / "reader.md").write_text("I love robots", encoding="utf-8")

        loader = ProfileLoader(profiles_dir=str(tmp_path))
        profiles = loader.load_all()

        assert profiles[0].content == "I love robots"

    def test_load_all_profile_path_is_absolute(self, tmp_path):
        cluster_dir = tmp_path / "Fantasy"
        cluster_dir.mkdir()
        (cluster_dir / "reader.md").write_text("content", encoding="utf-8")

        loader = ProfileLoader(profiles_dir=str(tmp_path))
        profiles = loader.load_all()

        assert profiles[0].path.is_absolute()
