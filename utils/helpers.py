def ensure_directory(path):
    """Simple helper to ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)
