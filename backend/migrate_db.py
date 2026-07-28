"""Apply the Supabase schema for the monolithic DataForge app."""

from pathlib import Path


def run() -> None:
    schema = Path(__file__).resolve().parent / "database" / "schema.sql"
    print(f"Apply this schema in your Supabase SQL editor: {schema}")


if __name__ == "__main__":
    run()
