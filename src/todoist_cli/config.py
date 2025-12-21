"""Configuration management for Todoist CLI."""

import os
from pathlib import Path
from datetime import datetime

import yaml

from todoist_cli.models import Config, ShortcutConfig, CachedData, Project, Label

# Environment variable for API token (preferred for security)
ENV_API_TOKEN = "TODOIST_API_TOKEN"


class ConfigManager:
    """Manages loading and saving of configuration."""

    DEFAULT_CONFIG_NAME = "config.yml"

    def __init__(self, config_path: Path | None = None):
        """Initialize config manager.

        Args:
            config_path: Explicit path to config file. If None, searches:
                1. ./config.yml (current directory)
                2. ~/.config/todoist-cli/config.yml
        """
        self._config_path = config_path or self._find_config_path()
        self._config: Config | None = None

    def _find_config_path(self) -> Path:
        """Find config file, preferring local over user config."""
        # Check current directory first
        local_config = Path.cwd() / self.DEFAULT_CONFIG_NAME
        if local_config.exists():
            return local_config

        # Check user config directory
        user_config = Path.home() / ".config" / "todoist-cli" / self.DEFAULT_CONFIG_NAME
        if user_config.exists():
            return user_config

        # Default to local if nothing exists
        return local_config

    @property
    def config_path(self) -> Path:
        """Get the config file path."""
        return self._config_path

    def load(self) -> Config:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        # Check if we have env var token (config file optional in this case)
        env_token = os.environ.get(ENV_API_TOKEN)

        if not self._config_path.exists():
            if env_token:
                # Create minimal config with env token
                self._config = Config(
                    api_token=env_token,
                    shortcuts=ShortcutConfig(),
                    cached=CachedData(),
                )
                return self._config
            raise FileNotFoundError(
                f"Config file not found: {self._config_path}\n"
                "Either:\n"
                "  1. Set TODOIST_API_TOKEN environment variable, or\n"
                "  2. Create config.yml with: api-token: your_token"
            )

        with open(self._config_path) as f:
            data = yaml.safe_load(f) or {}

        # Handle config without api-token (using env var)
        if "api-token" not in data:
            if env_token:
                data["api-token"] = env_token
            else:
                raise ValueError(
                    "No API token found.\n"
                    "Either:\n"
                    "  1. Set TODOIST_API_TOKEN environment variable, or\n"
                    "  2. Add 'api-token: your_token' to config.yml"
                )

        # Handle legacy config with just api-token
        if "shortcuts" not in data:
            data["shortcuts"] = {}
        if "cached" not in data:
            data["cached"] = {}

        self._config = Config.model_validate(data)
        return self._config

    def save(self, config: Config | None = None) -> None:
        """Save configuration to file.

        Note: API token is NOT saved if it came from environment variable.
        """
        if config is not None:
            self._config = config

        if self._config is None:
            raise ValueError("No config to save")

        # Ensure parent directory exists
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if token is from environment (don't save it to file)
        env_token = os.environ.get(ENV_API_TOKEN)
        save_token = env_token is None  # Only save if NOT using env var

        # Convert to dict with proper key names
        data: dict = {}

        # Only include api-token if not using environment variable
        if save_token:
            data["api-token"] = self._config.api_token

        data["shortcuts"] = {
            "labels": self._config.shortcuts.labels,
            "projects": self._config.shortcuts.projects,
            "priorities": self._config.shortcuts.priorities,
        }
        data["cached"] = {
            "projects": [p.model_dump() for p in self._config.cached.projects],
            "labels": [l.model_dump() for l in self._config.cached.labels],
            "last_sync": (
                self._config.cached.last_sync.isoformat()
                if self._config.cached.last_sync
                else None
            ),
        }

        # Remove empty sections for cleaner config
        if not any(data["shortcuts"].values()):
            del data["shortcuts"]
        if not data["cached"]["projects"] and not data["cached"]["labels"]:
            del data["cached"]

        with open(self._config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_api_token(self) -> str:
        """Get API token from environment variable or config file.

        Environment variable TODOIST_API_TOKEN takes precedence.
        """
        # Check environment variable first (preferred for security)
        env_token = os.environ.get(ENV_API_TOKEN)
        if env_token:
            return env_token

        # Fall back to config file
        return self.load().api_token

    def get_shortcuts(self) -> ShortcutConfig:
        """Get shortcut configuration."""
        return self.load().shortcuts

    def get_cached_projects(self) -> list[Project]:
        """Get cached projects."""
        return self.load().cached.projects

    def get_cached_labels(self) -> list[Label]:
        """Get cached labels."""
        return self.load().cached.labels

    def update_cached_data(
        self, projects: list[Project], labels: list[Label]
    ) -> None:
        """Update cached API data."""
        config = self.load()
        config.cached.projects = projects
        config.cached.labels = labels
        config.cached.last_sync = datetime.now()
        self.save()

    def add_shortcut(
        self, shortcut_type: str, key: str, value: str
    ) -> None:
        """Add a shortcut mapping.

        Args:
            shortcut_type: One of 'labels', 'projects', 'priorities'
            key: The shortcut key (e.g., 'w')
            value: The expanded value (e.g., 'work')
        """
        config = self.load()
        shortcuts = config.shortcuts

        if shortcut_type == "labels":
            shortcuts.labels[key] = value
        elif shortcut_type == "projects":
            shortcuts.projects[key] = value
        elif shortcut_type == "priorities":
            shortcuts.priorities[key] = value
        else:
            raise ValueError(f"Unknown shortcut type: {shortcut_type}")

        self.save()
