"""Explicit Customer wire contract. No dict/Any or open nested payloads."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class PublicModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class CustomerSource(PublicModel):
    label: str
    url: str | None = None


class CustomerProperty(PublicModel):
    property_id: str
    property_name: str
    lot: str | None = None
    price: float | None = None
    address: str | None = None
    layout: str | None = None
    station: str | None = None
    walking_minutes: float | None = None
    land_area: float | None = None
    building_area: float | None = None
    completion_date: str | None = None
    parking: str | None = None
    equipment: list[str] = Field(default_factory=list)
    surroundings: list[str] = Field(default_factory=list)
    scope_notices: list[str] = Field(default_factory=list)
    checked_at: str | None = None
    effective_date: str | None = None
    valid_until: str | None = None
    references: list[CustomerSource] = Field(default_factory=list)


class CustomerCandidate(PublicModel):
    property_id: str
    property_name: str


class CustomerProduct(PublicModel):
    id: str
    bank: str
    product: str
    rate_type: str
    rate: float
    rate_over_90_percent: float | None = None
    effective_date: str
    valid_until: str
    years_min: int | None = None
    years_max: int | None = None
    loan_amount_min: float | None = None
    loan_amount_max: float | None = None
    max_loan_to_value: float | None = None
    notes: str = ''
    conditions: list[str] = Field(default_factory=list)
    requires_acquisition_price_for_estimate: bool = False
    references: list[CustomerSource] = Field(default_factory=list)


class CustomerMortgage(PublicModel):
    version: int
    rate_id: str
    bank: str | None = None
    product: str | None = None
    rate_type: str | None = None
    property_price: float | None = None
    down_payment: float | None = None
    loan_amount: float
    annual_interest_rate: float
    years: int
    monthly_payment: int
    calculation_date: str
    effective_date: str
    valid_until: str
    rate_basis: str | None = None
    price_basis: str | None = None
    loan_to_value: float | None = None
    loan_to_value_percent: float | None = None
    conditions: list[str] = Field(default_factory=list)
    product_notes: str = ''
    notes: str = ''
    references: list[CustomerSource] = Field(default_factory=list)


class CustomerHit(PublicModel):
    text: str
    scope: Literal['general', 'company', 'property']
    references: list[CustomerSource] = Field(default_factory=list)


class PropertyDisplay(PublicModel):
    event_id: int
    kind: Literal['property'] = 'property'
    property: CustomerProperty


class CandidatesDisplay(PublicModel):
    event_id: int
    kind: Literal['properties'] = 'properties'
    properties: list[CustomerCandidate]


class SourcesDisplay(PublicModel):
    event_id: int
    kind: Literal['sources'] = 'sources'
    items: list[CustomerHit]


class ProductsDisplay(PublicModel):
    event_id: int
    kind: Literal['products'] = 'products'
    products: list[CustomerProduct]


class MortgageDisplay(PublicModel):
    event_id: int
    kind: Literal['mortgage'] = 'mortgage'
    result: CustomerMortgage


CustomerDisplay = Annotated[PropertyDisplay | CandidatesDisplay | SourcesDisplay | ProductsDisplay | MortgageDisplay,
                            Field(discriminator='kind')]


class CustomerMessage(PublicModel):
    event_id: int
    role: Literal['user', 'assistant']
    text: str
    created_at: str | None = None
    channel: Literal['text', 'voice', 'policy'] | None = None
    references: list[CustomerSource] = Field(default_factory=list)
    historical: bool = True


class CustomerStaffCall(PublicModel):
    id: str
    status: Literal['pending', 'accepted', 'completed']
    customer_message: str
    created_at: str | None = None
    accepted_at: str | None = None
    completed_at: str | None = None


class CustomerVoiceError(PublicModel):
    code: Literal['VOICE_CONNECTION_ERROR'] = 'VOICE_CONNECTION_ERROR'
    message: str = '音声接続を確認できません。接客を終了して再接続してください。'


class CustomerRealtime(PublicModel):
    status: Literal['not_started', 'connecting', 'connected', 'closing', 'closed', 'error', 'disconnected']
    error: CustomerVoiceError | None = None


class CustomerSession(PublicModel):
    id: str
    version: int | None
    mode: Literal['text', 'voice']
    property_id: str | None
    status: Literal['active', 'ended']
    created_at: str
    ended_at: str | None = None
    property: CustomerProperty | None = None
    products: list[CustomerProduct] = Field(default_factory=list)
    messages: list[CustomerMessage] = Field(default_factory=list)
    display_events: list[CustomerDisplay] = Field(default_factory=list)
    staff_calls: list[CustomerStaffCall] = Field(default_factory=list)
    realtime: CustomerRealtime


class CustomerSessionCreated(CustomerSession):
    token: str


class CustomerAnswer(PublicModel):
    answer: str
    version: int | None
    references: list[CustomerSource] = Field(default_factory=list)
    display_events: list[CustomerDisplay] = Field(default_factory=list)
    staff_call: CustomerStaffCall | None = None


class CustomerGreeting(PublicModel):
    status: Literal['greeting_requested']


class CustomerVoiceAnswer(PublicModel):
    assistant_event_id: int
    display_text: str


class CustomerSpeechInput(PublicModel):
    assistant_event_id: int = Field(gt=0)


class CustomerVoiceOutput(PublicModel):
    provider: Literal['openai_realtime', 'azure_tts']


class CustomerSpeechCancelled(PublicModel):
    status: Literal['cancelled'] = 'cancelled'
