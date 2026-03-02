"""Configuration management for Video Translation Agent."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Config:
    """Configuration manager with YAML file and environment variable support."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to YAML config file. If None, uses default config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "glm": {
                "api_key": os.environ.get("GLM_API_KEY", ""),
                "model": "glm-4",
                "temperature": 0.3,
            },
            "ocr": {
                "use_angle_cls": True,
                "lang": "ch",
                "det_db_thresh": 0.3,
                "det_db_box_thresh": 0.5,
                "det_db_unclip_ratio": 1.6,
                "max_candidates": 1000,
            },
            "asr": {
                "model_size": "base",
                "compute_type": "int8",
                "language": "auto",
                "beam_size": 5,
            },
            "video": {
                "frame_interval": 1.0,
                "output_fps": 30,
            },
            "output": {
                "subtitle_format": "srt",
                "encoding": "utf-8-sig",
                "output_dir": "./output",
            },
            "subtitle": {
                "font_size": 24,
                "font_color": "white",
                "position": "bottom",
                "margin": 10,
            },
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path.

        Args:
            key_path: Dot-separated key path (e.g., "glm.api_key")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value by dot-separated key path.

        Args:
            key_path: Dot-separated key path (e.g., "glm.api_key")
            value: Value to set
        """
        keys = key_path.split(".")
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to save config file. If None, uses original path
        """
        save_path = path or self.config_path
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    @property
    def glm_api_key(self) -> str:
        """Get GLM API key from config or environment variable."""
        return self.get("glm.api_key", "") or os.environ.get("GLM_API_KEY", "")

    @property
    def ocr_lang(self) -> str:
        """Get OCR language setting."""
        return self.get("ocr.lang", "ch")

    @property
    def asr_model_size(self) -> str:
        """Get ASR model size."""
        return self.get("asr.model_size", "base")

    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        return Path(self.get("output.output_dir", "./output"))

    @property
    def frame_interval(self) -> float:
        """Get frame interval for OCR extraction."""
        return self.get("video.frame_interval", 1.0)


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get global configuration instance.

    Args:
        config_path: Optional path to config file

    Returns:
        Config instance
    """
    global _config
    if _config is None or config_path is not None:
        _config = Config(config_path)
    return _config
