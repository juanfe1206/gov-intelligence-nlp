"""Tests for taxonomy YAML loader and Pydantic validation."""

import pytest
from pathlib import Path

from pydantic import ValidationError
import yaml

from app.taxonomy.loader import load_taxonomy
from app.taxonomy.schemas import (
    TaxonomyConfig,
    TaxonomyTopic,
    TaxonomySubtopic,
    TaxonomyTarget,
    TaxonomyTargets,
)


class TestLoadTaxonomy:
    """Tests for load_taxonomy function."""

    def test_load_valid_taxonomy_yaml(self, tmp_path: Path):
        """Test loading a valid taxonomy YAML file."""
        # Create a valid taxonomy YAML file
        yaml_content = """
topics:
  - name: "vivienda"
    label: "Vivienda"
    subtopics:
      - name: "alquiler"
        label: "Alquiler"
      - name: "hipotecas"
        label: "Hipotecas"

targets:
  parties:
    - name: "pp"
      label: "Partido Popular"
    - name: "psoe"
      label: "PSOE"
  leaders:
    - name: "sanchez"
      label: "Pedro Sánchez"
"""
        yaml_file = tmp_path / "taxonomy.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        # Load the taxonomy
        result = load_taxonomy(yaml_file)

        # Verify the loaded taxonomy
        assert isinstance(result, TaxonomyConfig)
        assert len(result.topics) == 1
        assert result.topics[0].name == "vivienda"
        assert result.topics[0].label == "Vivienda"
        assert len(result.topics[0].subtopics) == 2
        assert result.topics[0].subtopics[0].name == "alquiler"

        # Verify targets
        assert len(result.targets.parties) == 2
        assert result.targets.parties[0].name == "pp"
        assert len(result.targets.leaders) == 1
        assert result.targets.leaders[0].name == "sanchez"

    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        """Test that loading a non-existent file raises FileNotFoundError."""
        non_existent_file = tmp_path / "non_existent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_taxonomy(non_existent_file)

        assert "Taxonomy file not found" in str(exc_info.value)
        assert str(non_existent_file.name) in str(exc_info.value)

    def test_malformed_yaml_raises_yaml_error(self, tmp_path: Path):
        """Test that malformed YAML raises YAMLError."""
        yaml_content = "topics:\n  - name: [unclosed bracket\n"
        yaml_file = tmp_path / "malformed.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(yaml.YAMLError):
            load_taxonomy(yaml_file)

    def test_empty_yaml_raises_value_error(self, tmp_path: Path):
        """Test that an empty or comment-only YAML file raises ValueError."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("# only a comment\n", encoding="utf-8")

        with pytest.raises(ValueError, match="empty or contains only comments"):
            load_taxonomy(yaml_file)

    def test_invalid_schema_raises_validation_error(self, tmp_path: Path):
        """Test that invalid schema raises Pydantic ValidationError."""
        # Create a YAML file with missing required fields
        yaml_content = """
topics:
  - name: "vivienda"
    # Missing 'label' field which is required
    subtopics: []

targets:
  parties: []
  leaders: []
"""
        yaml_file = tmp_path / "invalid_schema.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ValidationError) as exc_info:
            load_taxonomy(yaml_file)

        assert "label" in str(exc_info.value) or "TaxonomyTopic" in str(exc_info.value)

    def test_empty_topics_list_is_valid(self, tmp_path: Path):
        """Test that empty topics list is valid (schema allows empty lists)."""
        yaml_content = """
topics: []

targets:
  parties: []
  leaders: []
"""
        yaml_file = tmp_path / "empty_topics.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        # Empty list for topics is allowed by the schema
        result = load_taxonomy(yaml_file)
        assert result.topics == []
        assert result.targets.parties == []
        assert result.targets.leaders == []

    def test_unknown_fields_are_rejected(self, tmp_path: Path):
        """Test that unknown/extra fields are rejected by Pydantic."""
        yaml_content = """
topics:
  - name: "vivienda"
    label: "Vivienda"
    unknown_field: "this should be rejected"
    subtopics: []

targets:
  parties: []
  leaders: []
"""
        yaml_file = tmp_path / "unknown_fields.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        # Pydantic v2 by default rejects extra fields
        with pytest.raises(ValidationError) as exc_info:
            load_taxonomy(yaml_file)

        assert "unknown_field" in str(exc_info.value) or "extra fields" in str(exc_info.value).lower()


class TestTaxonomySchemaValidation:
    """Tests for Pydantic schema validation rules."""

    def test_duplicate_topic_names_rejected(self):
        """Test that duplicate topic names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TaxonomyConfig(
                topics=[
                    TaxonomyTopic(name="vivienda", label="Vivienda", subtopics=[]),
                    TaxonomyTopic(name="vivienda", label="Housing", subtopics=[]),  # Duplicate
                ],
                targets=TaxonomyTargets(parties=[], leaders=[]),
            )

        assert "Duplicate topic names" in str(exc_info.value)

    def test_duplicate_subtopic_names_rejected(self):
        """Test that duplicate subtopic names within a topic are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TaxonomyConfig(
                topics=[
                    TaxonomyTopic(
                        name="vivienda",
                        label="Vivienda",
                        subtopics=[
                            TaxonomySubtopic(name="alquiler", label="Alquiler"),
                            TaxonomySubtopic(name="alquiler", label="Rent"),  # Duplicate
                        ],
                    ),
                ],
                targets=TaxonomyTargets(parties=[], leaders=[]),
            )

        assert "Duplicate subtopic names" in str(exc_info.value)

    def test_duplicate_party_names_rejected(self):
        """Test that duplicate party names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TaxonomyConfig(
                topics=[
                    TaxonomyTopic(name="vivienda", label="Vivienda", subtopics=[]),
                ],
                targets=TaxonomyTargets(
                    parties=[
                        TaxonomyTarget(name="pp", label="Partido Popular"),
                        TaxonomyTarget(name="pp", label="People's Party"),  # Duplicate
                    ],
                    leaders=[],
                ),
            )

        assert "Duplicate party names" in str(exc_info.value)

    def test_duplicate_leader_names_rejected(self):
        """Test that duplicate leader names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TaxonomyConfig(
                topics=[
                    TaxonomyTopic(name="vivienda", label="Vivienda", subtopics=[]),
                ],
                targets=TaxonomyTargets(
                    parties=[],
                    leaders=[
                        TaxonomyTarget(name="sanchez", label="Pedro Sánchez"),
                        TaxonomyTarget(name="sanchez", label="PM"),  # Duplicate
                    ],
                ),
            )

        assert "Duplicate leader names" in str(exc_info.value)

    def test_valid_taxonomy_passes_validation(self):
        """Test that a valid taxonomy passes all validation."""
        config = TaxonomyConfig(
            topics=[
                TaxonomyTopic(
                    name="vivienda",
                    label="Vivienda",
                    subtopics=[
                        TaxonomySubtopic(name="alquiler", label="Alquiler"),
                        TaxonomySubtopic(name="hipotecas", label="Hipotecas"),
                    ],
                ),
                TaxonomyTopic(
                    name="sanidad",
                    label="Sanidad",
                    subtopics=[
                        TaxonomySubtopic(name="atencion_primaria", label="Atención Primaria"),
                    ],
                ),
            ],
            targets=TaxonomyTargets(
                parties=[
                    TaxonomyTarget(name="pp", label="Partido Popular"),
                    TaxonomyTarget(name="psoe", label="PSOE"),
                    TaxonomyTarget(name="vox", label="VOX"),
                ],
                leaders=[
                    TaxonomyTarget(name="sanchez", label="Pedro Sánchez"),
                    TaxonomyTarget(name="feijoo", label="Alberto Núñez Feijóo"),
                ],
            ),
        )

        assert len(config.topics) == 2
        assert len(config.targets.parties) == 3
        assert len(config.targets.leaders) == 2


class TestTaxonomyModelDump:
    """Tests for model serialization."""

    def test_model_dump_returns_dict(self):
        """Test that model_dump returns a serializable dictionary."""
        config = TaxonomyConfig(
            topics=[
                TaxonomyTopic(
                    name="vivienda",
                    label="Vivienda",
                    subtopics=[
                        TaxonomySubtopic(name="alquiler", label="Alquiler"),
                    ],
                ),
            ],
            targets=TaxonomyTargets(
                parties=[TaxonomyTarget(name="pp", label="Partido Popular")],
                leaders=[],
            ),
        )

        dumped = config.model_dump()
        assert isinstance(dumped, dict)
        assert "topics" in dumped
        assert "targets" in dumped
        assert dumped["topics"][0]["name"] == "vivienda"
