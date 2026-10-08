from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class SessionStart(StrictModel):
    mode: Literal['text', 'voice'] = 'text'
    property_id: str | None = None


class PropertySelection(StrictModel):
    property_id: str


class MessageInput(StrictModel):
    text: str = Field(min_length=1, max_length=2000)


class ReviewData(StrictModel):
    document: dict = Field(default_factory=dict)
    property: dict = Field(default_factory=dict)
    knowledge: list[dict] = Field(default_factory=list, max_length=100)
    rates: list[dict] = Field(default_factory=list, max_length=10)
    faq: list[dict] = Field(default_factory=list, max_length=50)


class ConfirmationInput(StrictModel):
    reviewed: ReviewData
    note: str = Field(min_length=1, max_length=2000)
    usage: Literal['customer', 'internal', 'unclassified'] = 'unclassified'


class DraftInput(StrictModel):
    document_sha256: str = Field(min_length=64, max_length=64)
    source_revision: str = Field(min_length=64, max_length=64)
    revision: int = Field(ge=0)
    reviewed: ReviewData
    usage: Literal['customer', 'internal', 'unclassified'] = 'unclassified'
    note: str = Field(default='', max_length=2000)


class DraftConfirmationInput(StrictModel):
    document_sha256: str = Field(min_length=64, max_length=64)
    source_revision: str = Field(min_length=64, max_length=64)
    revision: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=2000)


class UsageInput(StrictModel):
    usage: Literal['customer', 'internal', 'unclassified']
    note: str = Field(min_length=1, max_length=2000)


class RevisionInput(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)


class PublicationItem(StrictModel):
    document_id: str = Field(min_length=1, max_length=100)
    confirmation_id: int | None = Field(default=None, ge=1)
    replaces_document_id: str | None = None
    replaces_confirmation_id: int | None = Field(default=None, ge=1)


class PublicationDraftCreate(StrictModel):
    restore_version: int | None = Field(default=None, ge=1)


class PublicationDraftInput(StrictModel):
    revision: int = Field(ge=0)
    items: list[PublicationItem] = Field(max_length=100)
    note: str = Field(default='', max_length=2000)


class PublishInput(StrictModel):
    # The old shape is accepted solely to return an explicit no-bypass error.
    document_ids: list[str] | None = Field(default=None, max_length=100)
    draft_id: str | None = None
    draft_revision: int | None = Field(default=None, ge=0)
    preview_token: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=16, max_length=100)


class StaffInput(StrictModel):
    reason: str = Field(min_length=1, max_length=500)
    last_customer_question: str = Field(default='', max_length=2000)


class MortgageInput(StrictModel):
    down_payment: float = Field(default=0, ge=0, le=1000000000)
    loan_amount: float | None = Field(default=None, gt=0, le=1000000000)
    property_price: float | None = Field(default=None, gt=0, le=1000000000)
    years: int = Field(ge=1, le=50)
    rate_id: str = Field(min_length=1, max_length=100)
