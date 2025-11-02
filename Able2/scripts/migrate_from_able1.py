#!/usr/bin/env python3
"""
Migration script from Able mk I to Able2.
Copies vector stores, graph data, and documents.
"""

import shutil
from pathlib import Path
import sys


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def migrate_data(able1_path: str):
    """
    Migrate data from Able mk I to Able2.

    Args:
        able1_path: Path to Able mk I installation
    """
    print_header("Migrating from Able mk I to Able2")

    able1_path = Path(able1_path)

    if not able1_path.exists():
        print(f"❌ Able mk I path not found: {able1_path}")
        sys.exit(1)

    print(f"Source: {able1_path}")
    print(f"Target: Able2/")

    # Migrate vector store
    print("\n📦 Migrating vector store...")
    able1_vector = able1_path / "data" / "vector_store"
    able2_vector = Path("Able2/data/vector_store")

    if able1_vector.exists():
        shutil.copytree(able1_vector, able2_vector, dirs_exist_ok=True)
        print(f"✓ Copied vector store ({count_files(able1_vector)} files)")
    else:
        print("⚠️  No vector store found in Able mk I")

    # Migrate graph store
    print("\n🕸️  Migrating graph store...")
    able1_graph = able1_path / "data" / "graph_store"
    able2_graph = Path("Able2/data/graph_store")

    if able1_graph.exists():
        shutil.copytree(able1_graph, able2_graph, dirs_exist_ok=True)
        print(f"✓ Copied graph store ({count_files(able1_graph)} files)")
    else:
        print("⚠️  No graph store found in Able mk I")

    # Migrate uploads
    print("\n📄 Migrating uploaded documents...")
    able1_uploads = able1_path / "data" / "uploads"
    able2_uploads = Path("Able2/data/uploads")

    if able1_uploads.exists():
        shutil.copytree(able1_uploads, able2_uploads, dirs_exist_ok=True)
        print(f"✓ Copied uploads ({count_files(able1_uploads)} files)")
    else:
        print("⚠️  No uploads found in Able mk I")

    # Migrate config
    print("\n⚙️  Migrating configuration...")
    able1_config = able1_path / "config" / "config.yaml"
    able2_config = Path("Able2/config/config.yaml")

    if able1_config.exists():
        print("✓ Able mk I config found")
        print("  Note: Able2 has expanded config. Review and merge manually:")
        print(f"    {able1_config} → {able2_config}")
    else:
        print("⚠️  No config.yaml found in Able mk I")

    print_header("Migration Complete!")

    print("✅ Data migrated successfully!\n")
    print("Next steps:")
    print("1. Review migrated config: Able2/config/config.yaml")
    print("2. Update .env with any new settings")
    print("3. Initialize Able2 database (new in Able2):")
    print("   python -c \"from backend.core import init_database; init_database()\"")
    print("4. Start Able2:")
    print("   uvicorn backend.api.main:app --reload")
    print("\n📚 See MIGRATION_NOTES.md for detailed changes")


def count_files(path: Path) -> int:
    """Count files in directory."""
    return sum(1 for _ in path.rglob("*") if _.is_file())


def main():
    """Main migration function."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_from_able1.py <path-to-able-mk1>")
        print("\nExample:")
        print("  python migrate_from_able1.py /path/to/Able-mk1")
        sys.exit(1)

    able1_path = sys.argv[1]
    migrate_data(able1_path)


if __name__ == "__main__":
    main()
