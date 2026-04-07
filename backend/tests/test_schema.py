"""Tests for database schema definition and structure."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.schema import MetaData

from app.db.base import Base
from app.db.session import engine
from app.models.raw_post import RawPost
from app.models.processed_post import ProcessedPost


def test_raw_post_model_defined():
    """Test that RawPost model is properly defined."""
    assert hasattr(RawPost, "__tablename__")
    assert RawPost.__tablename__ == "raw_posts"

    # Check columns exist
    mapper = inspect(RawPost)
    column_names = [c.name for c in mapper.columns]

    expected_columns = [
        "id",
        "source",
        "platform",
        "original_text",
        "author",
        "created_at",
        "metadata",
        "ingested_at",
    ]

    for col in expected_columns:
        assert col in column_names, f"Column {col} missing from RawPost"


def test_processed_post_model_defined():
    """Test that ProcessedPost model is properly defined."""
    assert hasattr(ProcessedPost, "__tablename__")
    assert ProcessedPost.__tablename__ == "processed_posts"

    # Check columns exist
    mapper = inspect(ProcessedPost)
    column_names = [c.name for c in mapper.columns]

    expected_columns = [
        "id",
        "raw_post_id",
        "topic",
        "subtopic",
        "sentiment",
        "target",
        "intensity",
        "embedding",
        "processed_at",
        "model_version",
    ]

    for col in expected_columns:
        assert col in column_names, f"Column {col} missing from ProcessedPost"


def test_raw_post_column_types():
    """Test that RawPost columns have correct types."""
    mapper = inspect(RawPost)

    # Check a few key columns
    id_col = mapper.columns["id"]
    assert "UUID" in str(id_col.type)

    source_col = mapper.columns["source"]
    assert "VARCHAR" in str(source_col.type)

    original_text_col = mapper.columns["original_text"]
    assert "TEXT" in str(original_text_col.type)


def test_processed_post_column_types():
    """Test that ProcessedPost columns have correct types."""
    mapper = inspect(ProcessedPost)

    # Check key columns
    id_col = mapper.columns["id"]
    assert "UUID" in str(id_col.type)

    raw_post_id_col = mapper.columns["raw_post_id"]
    assert "UUID" in str(raw_post_id_col.type)

    intensity_col = mapper.columns["intensity"]
    assert "FLOAT" in str(intensity_col.type).upper()


def test_raw_post_foreign_key():
    """Test that ProcessedPost has foreign key to RawPost."""
    mapper = inspect(ProcessedPost)
    fks = mapper.mapped_table.foreign_keys

    # Check we have a foreign key
    assert len(fks) > 0, "ProcessedPost should have foreign key constraints"

    # Check it points to raw_posts
    fk_columns = [str(fk.column) for fk in fks]
    assert any("raw_posts" in col for col in fk_columns), "FK should reference raw_posts table"


def test_base_metadata_includes_models():
    """Test that Base metadata includes both models."""
    # The models should be registered with the Base
    assert Base.metadata is not None

    # Check that table definitions are in metadata
    table_names = [table.name for table in Base.metadata.tables.values()]
    assert "raw_posts" in table_names
    assert "processed_posts" in table_names


def test_raw_post_nullable_columns():
    """Test which RawPost columns are nullable."""
    mapper = inspect(RawPost)
    columns_by_name = {c.name: c for c in mapper.columns}

    # These should be nullable
    nullable_cols = ["author", "metadata"]
    for col_name in nullable_cols:
        if col_name in columns_by_name:
            col = columns_by_name[col_name]
            assert col.nullable, f"Column {col_name} should be nullable"

    # These should NOT be nullable
    not_nullable = ["source", "platform", "original_text", "created_at", "ingested_at"]
    for col_name in not_nullable:
        if col_name in columns_by_name:
            col = columns_by_name[col_name]
            assert not col.nullable, f"Column {col_name} should be NOT NULL"


def test_raw_post_metadata_column_alias():
    """Test that metadata column is properly aliased."""
    # Column is named 'metadata_' in Python but 'metadata' in DB
    assert hasattr(RawPost, "metadata_"), "RawPost should have metadata_ attribute"

    # Check the actual column in the table
    mapper = inspect(RawPost)
    col_names = [c.name for c in mapper.columns]
    assert "metadata" in col_names, f"RawPost should have 'metadata' column in DB. Found: {col_names}"


def test_processed_post_nullable_columns():
    """Test which ProcessedPost columns are nullable."""
    mapper = inspect(ProcessedPost)

    # These should be nullable
    nullable_cols = ["subtopic", "target", "intensity", "embedding", "model_version"]
    for col_name in nullable_cols:
        col = mapper.columns[col_name]
        assert col.nullable, f"Column {col_name} should be nullable"

    # These should NOT be nullable
    not_nullable = ["id", "raw_post_id", "topic", "sentiment", "processed_at"]
    for col_name in not_nullable:
        col = mapper.columns[col_name]
        assert not col.nullable, f"Column {col_name} should be NOT NULL"


def test_raw_post_relationship():
    """Test that RawPost has relationship to ProcessedPost."""
    # Check relationship in mapper
    mapper = inspect(RawPost)
    relationships = [rel.key for rel in mapper.relationships]
    assert "processed_posts" in relationships, f"RawPost should have processed_posts relationship. Found: {relationships}"


def test_processed_post_relationship():
    """Test that ProcessedPost has relationship to RawPost."""
    assert hasattr(ProcessedPost, "raw_post"), "ProcessedPost should have raw_post relationship"
