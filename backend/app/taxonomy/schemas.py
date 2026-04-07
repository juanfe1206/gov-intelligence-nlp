"""Pydantic schemas for political taxonomy configuration."""

from pydantic import BaseModel, field_validator


class TaxonomyTarget(BaseModel):
    """A political target (party or leader).

    Attributes:
        name: Machine identifier (lowercase, no spaces)
        label: Human-readable display name
    """

    model_config = {"extra": "forbid"}

    name: str
    label: str


class TaxonomySubtopic(BaseModel):
    """A subtopic within a topic.

    Attributes:
        name: Machine identifier (lowercase, no spaces)
        label: Human-readable display name
    """

    model_config = {"extra": "forbid"}

    name: str
    label: str


class TaxonomyTopic(BaseModel):
    """A topic with its subtopics.

    Attributes:
        name: Machine identifier (lowercase, no spaces)
        label: Human-readable display name
        subtopics: List of subtopics belonging to this topic
    """

    model_config = {"extra": "forbid"}

    name: str
    label: str
    subtopics: list[TaxonomySubtopic] = []


class TaxonomyTargets(BaseModel):
    """Collection of political targets.

    Attributes:
        parties: List of political parties
        leaders: List of political leaders
    """

    model_config = {"extra": "forbid"}

    parties: list[TaxonomyTarget] = []
    leaders: list[TaxonomyTarget] = []


class TaxonomyConfig(BaseModel):
    """Complete taxonomy configuration.

    Contains all topics with subtopics and all political targets.
    Validated at load time to ensure data integrity.
    """

    model_config = {"extra": "forbid"}

    topics: list[TaxonomyTopic]
    targets: TaxonomyTargets

    @field_validator("topics")
    @classmethod
    def no_duplicate_topic_names(cls, topics: list[TaxonomyTopic]) -> list[TaxonomyTopic]:
        """Validate that topic names are unique."""
        names = [t.name for t in topics]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate topic names found in taxonomy")
        return topics

    @field_validator("topics")
    @classmethod
    def no_duplicate_subtopic_names(
        cls, topics: list[TaxonomyTopic]
    ) -> list[TaxonomyTopic]:
        """Validate that subtopic names are unique within each topic."""
        for topic in topics:
            names = [s.name for s in topic.subtopics]
            if len(names) != len(set(names)):
                raise ValueError(
                    f"Duplicate subtopic names found in topic '{topic.name}'"
                )
        return topics

    @field_validator("targets")
    @classmethod
    def no_duplicate_target_names(cls, targets: TaxonomyTargets) -> TaxonomyTargets:
        """Validate that party and leader names are unique within their lists."""
        party_names = [p.name for p in targets.parties]
        if len(party_names) != len(set(party_names)):
            raise ValueError("Duplicate party names found in taxonomy")

        leader_names = [l.name for l in targets.leaders]
        if len(leader_names) != len(set(leader_names)):
            raise ValueError("Duplicate leader names found in taxonomy")

        return targets
