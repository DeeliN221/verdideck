"""Configuration management for VerdiDeck."""

from pathlib import Path
from typing import Any

import yaml


def resolve_config_dir(home: Path) -> Path:
    """Prefer VerdiDeck configuration, then reuse an existing lazyverdi file."""
    current = home / ".config" / "verdideck"
    legacy = home / ".config" / "lazyverdi"
    if not (current / "config.yaml").exists() and (legacy / "config.yaml").is_file():
        return legacy
    return current


CONFIG_DIR = resolve_config_dir(Path.home())
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    # Theme and appearance
    "theme": "monokai",
    # Auto-refresh settings
    # Auto-refresh interval in seconds (supports float, 0 or negative to disable)
    "auto_refresh_interval": 10,
    "auto_refresh_on_startup": True,  # Enable auto-refresh when app starts
    # Panel layout settings
    "left_panel_width_percent": 40,  # Width percentage of left panels (1-99)
    "results_panel_height_percent": 80,  # Height percentage of results panel (1-99)
    # Panel behavior
    "focused_panel_height_percent": 50,  # Height percentage when a panel is focused (1-99)
    "show_line_numbers": False,  # Show line numbers in text areas
    "soft_wrap": True,  # Enable soft wrap for long lines
    # Scrollbar settings
    "scrollbar_vertical_width": 1,  # Vertical scrollbar width (1-3)
    "scrollbar_horizontal_height": 1,  # Horizontal scrollbar height (1-3)
    # Startup behavior
    "show_welcome_message": True,  # Show welcome message on startup
    "initial_focus_panel": 0,  # Panel to focus on startup (0-6)
}


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load configuration from YAML file.

    Returns:
        Configuration dictionary. Falls back to default if file doesn't exist or is invalid.
    """
    if not CONFIG_FILE.exists():
        # First run - create default config
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        # Merge with defaults to ensure all keys exist
        return {**DEFAULT_CONFIG, **config}
    except Exception:
        # Config file is corrupted - return defaults
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration dictionary to save
    """
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
    except Exception:
        # Fail silently - don't crash the app
        pass


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a single configuration value.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """Set a single configuration value.

    Args:
        key: Configuration key
        value: Value to set
    """
    config = load_config()
    config[key] = value
    save_config(config)
