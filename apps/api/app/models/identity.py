"""Request and response models for the structured Life Profile."""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


IDENTITY_FIELDS = frozenset({
    "full_name", "preferred_name", "date_of_birth", "gender", "pronouns",
    "occupation", "education", "nationality", "religion", "languages",
    "hometown", "current_city", "biography", "spouse", "children", "parents",
    "siblings", "grandchildren", "pets", "website", "social_links", "email",
    "values", "motto", "favorite_quote", "favorite_song", "favorite_book",
    "favorite_food", "favorite_place", "blood_group", "allergies", "medical_notes",
})

LIST_FIELDS = frozenset({"languages", "children", "parents", "siblings", "grandchildren", "pets", "values"})
JSON_FIELDS = LIST_FIELDS | {"social_links", "privacy_settings"}


class IdentityPrivacySettings(BaseModel):
    """The explicit allow-list of Life Profile fields visible to group members."""

    shared_fields: list[str] = Field(default_factory=list, max_length=len(IDENTITY_FIELDS))

    @field_validator("shared_fields")
    @classmethod
    def valid_fields(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        invalid = sorted(set(cleaned) - IDENTITY_FIELDS)
        if invalid:
            raise ValueError(f"Unknown Life Profile fields: {', '.join(invalid)}")
        return cleaned


class IdentityProfileUpdate(BaseModel):
    """Partial update; unset fields are preserved and explicit null clears text fields."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, max_length=160)
    preferred_name: str | None = Field(default=None, max_length=120)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=80)
    pronouns: str | None = Field(default=None, max_length=80)
    occupation: str | None = Field(default=None, max_length=200)
    education: str | None = Field(default=None, max_length=500)
    nationality: str | None = Field(default=None, max_length=120)
    religion: str | None = Field(default=None, max_length=120)
    languages: list[str] | None = Field(default=None, max_length=25)
    hometown: str | None = Field(default=None, max_length=160)
    current_city: str | None = Field(default=None, max_length=160)
    biography: str | None = Field(default=None, max_length=8_000)
    spouse: str | None = Field(default=None, max_length=160)
    children: list[str] | None = Field(default=None, max_length=50)
    parents: list[str] | None = Field(default=None, max_length=20)
    siblings: list[str] | None = Field(default=None, max_length=30)
    grandchildren: list[str] | None = Field(default=None, max_length=100)
    pets: list[str] | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=500)
    social_links: dict[str, str] | None = None
    email: str | None = Field(default=None, max_length=320)
    values: list[str] | None = Field(default=None, max_length=30)
    motto: str | None = Field(default=None, max_length=500)
    favorite_quote: str | None = Field(default=None, max_length=2_000)
    favorite_song: str | None = Field(default=None, max_length=300)
    favorite_book: str | None = Field(default=None, max_length=300)
    favorite_food: str | None = Field(default=None, max_length=300)
    favorite_place: str | None = Field(default=None, max_length=300)
    blood_group: str | None = Field(default=None, max_length=16)
    allergies: str | None = Field(default=None, max_length=2_000)
    medical_notes: str | None = Field(default=None, max_length=4_000)
    privacy_settings: IdentityPrivacySettings | None = None

    @field_validator(*LIST_FIELDS, mode="before")
    @classmethod
    def clean_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return list(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))

    @field_validator("social_links", mode="before")
    @classmethod
    def clean_social_links(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        return {str(key).strip(): str(link).strip() for key, link in value.items() if str(key).strip() and str(link).strip()}

    @model_validator(mode="after")
    def trim_text(self) -> "IdentityProfileUpdate":
        for field_name in IDENTITY_FIELDS - LIST_FIELDS - {"social_links", "date_of_birth"}:
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name, value.strip() or None)
        return self


class IdentityProfileResponse(BaseModel):
    """A complete owner response, or a field-filtered group-member response."""

    model_config = ConfigDict(extra="allow")

    user_id: str
    full_name: str | None = None
    preferred_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    pronouns: str | None = None
    occupation: str | None = None
    education: str | None = None
    nationality: str | None = None
    religion: str | None = None
    languages: list[str] = Field(default_factory=list)
    hometown: str | None = None
    current_city: str | None = None
    biography: str | None = None
    spouse: str | None = None
    children: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)
    siblings: list[str] = Field(default_factory=list)
    grandchildren: list[str] = Field(default_factory=list)
    pets: list[str] = Field(default_factory=list)
    website: str | None = None
    social_links: dict[str, str] = Field(default_factory=dict)
    email: str | None = None
    values: list[str] = Field(default_factory=list)
    motto: str | None = None
    favorite_quote: str | None = None
    favorite_song: str | None = None
    favorite_book: str | None = None
    favorite_food: str | None = None
    favorite_place: str | None = None
    blood_group: str | None = None
    allergies: str | None = None
    medical_notes: str | None = None
    privacy_settings: IdentityPrivacySettings = Field(default_factory=IdentityPrivacySettings)
    created_at: Any | None = None
    updated_at: Any | None = None
