"""Taxonomy YAML loader with Pydantic validation."""

from pathlib import Path

import yaml

from app.taxonomy.schemas import TaxonomyConfig


def load_taxonomy(path: str | Path) -> TaxonomyConfig:
    """Load and validate taxonomy from YAML file.

    Reads the taxonomy configuration from a YAML file and validates it
    against the Pydantic schema. Any validation errors will raise an
    exception to fail fast at application startup.

    Args:
        path: Path to the taxonomy YAML file (string or Path object)

    Returns:
        TaxonomyConfig: Validated taxonomy configuration

    Raises:
        FileNotFoundError: If the taxonomy file does not exist
        yaml.YAMLError: If the YAML is malformed
        pydantic.ValidationError: If the schema is invalid
        UnicodeDecodeError: If the file cannot be read as UTF-8

    Example:
        >>> config = load_taxonomy("config/taxonomy.yaml")
        >>> print(config.topics[0].label)
        'Vivienda'
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {p.resolve()}")

    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Taxonomy file is empty or contains only comments: {p.resolve()}")

    return TaxonomyConfig.model_validate(raw)
