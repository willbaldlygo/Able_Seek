#!/usr/bin/env python3
"""
Setup script for Able2.
Guides user through initial configuration.
"""

import os
import sys
from pathlib import Path
import shutil


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def check_python_version():
    """Check Python version."""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        sys.exit(1)
    print("✓ Python version OK")


def create_directories():
    """Create necessary directories."""
    print_header("Creating Directories")

    directories = [
        "Able2/data/vector_store",
        "Able2/data/graph_store",
        "Able2/data/uploads",
        "Able2/logs",
        "Able2/temp",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}")


def setup_env_file():
    """Setup .env file from example."""
    print_header("Setting Up Environment File")

    env_example = Path("Able2/.env.example")
    env_file = Path("Able2/.env")

    if env_file.exists():
        response = input(".env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Skipping .env setup")
            return

    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✓ Created .env file from template")

        # Get Anthropic API key
        print("\n📝 Configuration:")
        print("1. Edit Able2/.env")
        print("2. Add your ANTHROPIC_API_KEY")
        print("3. Adjust other settings as needed")

        api_key = input("\nEnter your Anthropic API key (or press Enter to skip): ").strip()

        if api_key:
            # Update .env file with API key
            with open(env_file, 'r') as f:
                content = f.read()

            content = content.replace(
                'ANTHROPIC_API_KEY=your-anthropic-api-key-here',
                f'ANTHROPIC_API_KEY={api_key}'
            )

            with open(env_file, 'w') as f:
                f.write(content)

            print("✓ API key configured")
        else:
            print("⚠️  Remember to add your API key to .env later")
    else:
        print("❌ .env.example not found")


def check_dependencies():
    """Check if dependencies are installed."""
    print_header("Checking Dependencies")

    try:
        import fastapi
        print("✓ FastAPI installed")
    except ImportError:
        print("❌ FastAPI not installed. Run: pip install -r requirements.txt")
        return False

    try:
        import anthropic
        print("✓ Anthropic SDK installed")
    except ImportError:
        print("❌ Anthropic SDK not installed. Run: pip install -r requirements.txt")
        return False

    try:
        import chromadb
        print("✓ ChromaDB installed")
    except ImportError:
        print("❌ ChromaDB not installed. Run: pip install -r requirements.txt")
        return False

    return True


def setup_database():
    """Initialize database."""
    print_header("Setting Up Database")

    print("Database setup requires:")
    print("1. PostgreSQL running (see docker-compose.yml)")
    print("2. Correct DATABASE_URL in .env")
    print("\nTo initialize database, run:")
    print("  python -c \"from backend.core import init_database; init_database()\"")


def download_ollama_models():
    """Guide user to download Ollama models."""
    print_header("Ollama Models")

    print("If using Ollama for local models:")
    print("\n1. Install Ollama: https://ollama.ai")
    print("2. Pull models:")
    print("   ollama pull llama3.2")
    print("   ollama pull nomic-embed-text")
    print("\nOr use docker-compose.yml to run Ollama in container")


def print_next_steps():
    """Print next steps."""
    print_header("Setup Complete!")

    print("📋 Next Steps:\n")
    print("1. Start services:")
    print("   cd Able2/docker")
    print("   docker-compose up -d")
    print()
    print("2. Initialize database:")
    print("   python -c \"from backend.core import init_database; init_database()\"")
    print()
    print("3. Start backend:")
    print("   cd Able2")
    print("   uvicorn backend.api.main:app --reload")
    print()
    print("4. Open frontend:")
    print("   http://localhost:3001")
    print()
    print("5. Upload documents and start chatting!")
    print()
    print("📚 Documentation:")
    print("   - MIGRATION_NOTES.md - Architecture overview")
    print("   - docs/MIGRATION_FROM_ABLE1.md - Migration guide")
    print()
    print("🎉 Happy building!")


def main():
    """Main setup function."""
    print_header("Able2 Setup Script")

    check_python_version()
    create_directories()
    setup_env_file()

    if not check_dependencies():
        print("\n⚠️  Install dependencies first:")
        print("   pip install -r requirements.txt")
        return

    setup_database()
    download_ollama_models()
    print_next_steps()


if __name__ == "__main__":
    main()
