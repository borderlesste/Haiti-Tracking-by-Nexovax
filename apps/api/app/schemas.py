import math
import unicodedata
from datetime import datetime
from typing import Annotated, Literal, Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    @field_validator("*", mode="before")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            value = unicodedata.normalize("NFC", value)
            if any(unicodedata.category(c) == "Cc" and c not in "\n\t" for c in value):
                raise ValueError("Control characters are not allowed")
        return value


class Register(StrictModel):
    display_name: str = Field(min_length=2, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)
    phone: str | None = Field(default=None, max_length=25, pattern=r"^\+?[0-9 ()-]{7,25}$")
    profile: Literal["collaborator", "business", "developer"] = "collaborator"
    terms_accepted: Literal[True]
    privacy_accepted: Literal[True]


class Login(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    otp: str | None = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")


class EmailRequest(StrictModel):
    email: EmailStr


class TokenRequest(StrictModel):
    token: str = Field(min_length=30, max_length=200)


class ResetPassword(TokenRequest):
    password: str = Field(min_length=12, max_length=128)


class Coordinates(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class GPSObservation(Coordinates):
    accuracy_m: float = Field(gt=0, le=10000)
    captured_at: datetime
    source: Literal["browser_geolocation"] = "browser_geolocation"


class Address(StrictModel):
    neighborhood: str = Field(default="", max_length=120)
    street: str | None = Field(default=None, max_length=160)
    house_number: str | None = Field(default=None, max_length=40)
    reference: str = Field(default="", max_length=500)
    unit_label: str | None = Field(default=None, max_length=80)
    access_notes: str | None = Field(default=None, max_length=500)


PlaceType = Literal["business", "public", "landmark", "road", "access"]


class DuplicateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    type: PlaceType
    territory_id: str = Field(min_length=1, max_length=40)
    selected_point: Coordinates


class DuplicateResolution(StrictModel):
    choice: Literal["distinct_place", "update_existing", "no_match"]
    justification: str = Field(default="", max_length=1000)


class ContributionCreate(DuplicateRequest):
    mode: Literal["on_site", "remote", "draft"] = "on_site"
    address: Address = Field(default_factory=Address)
    description: str = Field(default="", max_length=1000)
    gps_observation: GPSObservation | None = None
    pin_adjustment_reason: str = Field(default="", max_length=1000)
    duplicate_resolution: DuplicateResolution | None = None
    target_location_code: str | None = Field(default=None, max_length=30)
    parent_location_code: str | None = Field(default=None, max_length=30)
    access_point_code: str | None = Field(default=None, max_length=30)
    aliases: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(default_factory=list, max_length=10)
    knowledge_source: Literal["own_observation", "local_representative", "community_reference"] = "own_observation"
    source_declaration_accepted: bool = False
    version: int | None = Field(default=None, ge=1)

    @field_validator("aliases")
    @classmethod
    def clean_aliases(cls, values):
        cleaned = list(dict.fromkeys(unicodedata.normalize("NFC", value.strip()) for value in values))
        if any(not value or any(unicodedata.category(c).startswith("C") for c in value) for value in cleaned):
            raise ValueError("Aliases must be visible names")
        return cleaned


ContributionInput = ContributionCreate


class Suggestion(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    type: PlaceType
    territory_id: str = Field(min_length=1, max_length=40)
    reference: str = Field(min_length=5, max_length=500)
    website: str = Field(default="", max_length=0, description="Honeypot: must remain empty")
    source_declaration_accepted: Literal[True]


class Report(StrictModel):
    category: Literal["error", "duplicate", "privacy", "closed", "other"]
    description: str = Field(min_length=5, max_length=1000)


class Decision(StrictModel):
    decision: Literal["approve", "reject", "request_changes", "merge"]
    reason: str = Field(min_length=10, max_length=1000)
    canonical_code: str | None = Field(default=None, max_length=30)
    version: int = Field(ge=1)
    corroboration: str = Field(default="", max_length=1000)


class ContributionVersion(StrictModel):
    version: int = Field(ge=1)


class SuggestionDecision(StrictModel):
    decision: Literal["reviewed", "rejected"]
    reason: str = Field(min_length=10, max_length=1000)


class Merge(StrictModel):
    canonical_code: str = Field(min_length=10, max_length=30)
    reason: str = Field(min_length=10, max_length=1000)


class AppInput(StrictModel):
    name: str = Field(min_length=2, max_length=100)
    environment: Literal["test", "live"] = "test"


class NewKey(StrictModel):
    password: str = Field(min_length=1, max_length=128)


class ProfileInput(StrictModel):
    display_name: str = Field(min_length=2, max_length=100)


class PhotoInput(StrictModel):
    content_base64: str = Field(min_length=10, max_length=7_000_000)


class TerritoryData(StrictModel):
    name: str = Field(min_length=2, max_length=100)
    aliases: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(default_factory=list, max_length=20)
    source_version: str = Field(min_length=1, max_length=200)
    source_url: str = Field(min_length=8, max_length=1000, pattern=r"^https://")
    license: str = Field(min_length=3, max_length=1000)

    @field_validator("source_url")
    @classmethod
    def public_source_url(cls, value):
        try:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in value) or parsed.port == 0:
                raise ValueError()
        except ValueError:
            raise ValueError("Source URL must be a public HTTPS URL without credentials")
        return value


class TerritoryInput(TerritoryData):
    id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    parent_id: str | None = Field(default=None, max_length=40)
    level: Literal["country", "department", "commune", "section"]


class TerritoryUpdate(TerritoryData):
    expected_source_version: str = Field(min_length=1, max_length=200)


class PublicAddress(BaseModel):
    country_code: Literal["HT"] = "HT"
    department: str = ""
    commune: str = ""
    communal_section: str | None = None
    neighborhood: str = ""
    street: str | None = None
    house_number: str | None = None
    reference: str = ""
    unit_label: str | None = None
    access_notes: str | None = None


class PublicLocation(BaseModel):
    id: str
    code: str
    name: str
    type: PlaceType
    aliases: list[str] = Field(default_factory=list)
    parent_location_code: str | None = None
    access_point_code: str | None = None
    address: PublicAddress
    territory_id: str
    coordinates: Coordinates
    description: str
    verification_status: Literal["verified", "demonstration"]
    is_demo: bool
    confidence_score: float = Field(ge=0, le=1)
    last_verified_at: datetime
    version: int
    requested_code: str | None = None
    canonical_code: str | None = None
    was_redirected: bool = False
    distance_m: float | None = None


class Pagination(BaseModel):
    limit: int
    next_cursor: str | None


class LocationListResponse(BaseModel):
    success: Literal[True]
    data: list[PublicLocation]
    pagination: Pagination
    request_id: str


class LocationResponse(BaseModel):
    success: Literal[True]
    data: PublicLocation
    request_id: str


class Territory(BaseModel):
    id: str
    parent_id: str | None
    country_code: Literal["HT"]
    name: str
    level: Literal["country", "department", "commune", "section"]
    aliases: list[str]
    source_version: str
    source_url: str
    license: str


class TerritoryResponse(BaseModel):
    success: Literal[True]
    data: Territory
    request_id: str


class TerritoryListResponse(BaseModel):
    success: Literal[True]
    data: list[Territory]
    pagination: Pagination
    request_id: str


class ContributionResponse(BaseModel):
    id: str
    contribution_id: str
    status: Literal["draft", "submitted", "needs_review", "changes_requested", "approved", "rejected", "merged", "withdrawn"]
    version: int
    payload: dict[str, Any]
    review_reason: str | None
    published_code: str | None
    created_at: datetime
    eligible_for_automatic_payment: Literal[False]


class ContributionEnvelope(BaseModel):
    success: Literal[True]
    data: ContributionResponse
    request_id: str


class ContributionListEnvelope(BaseModel):
    success: Literal[True]
    data: list[ContributionResponse]
    request_id: str


class DuplicateCandidate(BaseModel):
    code: str
    name: str
    type: PlaceType
    distance_m: float = Field(ge=0)
    similarity_score: float = Field(ge=0, le=1)
    reasons: list[str]


class DuplicateResult(BaseModel):
    decision: Literal["manual_review_recommended", "no_match"]
    candidates: list[DuplicateCandidate]


class DuplicateEnvelope(BaseModel):
    success: Literal[True]
    data: DuplicateResult
    request_id: str


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class ApiErrorResponse(BaseModel):
    success: Literal[False]
    error: ApiError
    request_id: str
