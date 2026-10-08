"""AI evidence is distinct from a clipped Customer display excerpt."""
from typing import Literal
from pydantic import Field
from app.schemas.customer import PublicModel, CustomerSource, CustomerProperty, CustomerProduct, CustomerMortgage, CustomerCandidate, CustomerStaffCall


class EvidenceItem(PublicModel):
    text: str
    scope: Literal['general', 'company', 'property']
    references: list[CustomerSource] = Field(default_factory=list)


class CustomerDeclaration(PublicModel):
    loan_amount: float | None = None
    property_price: float | None = None
    origin: str = '顧客申告。会社・物件資料の事実ではありません。'


class EvidenceError(PublicModel):
    code: str
    message: str = 'この処理を完了できませんでした。必要な条件を確認するか、スタッフにご相談ください。'


class EvidenceProduct(CustomerProduct):
    loan_to_value_conditions: str
    estimate_input_rule: str = '物件未選択の場合は顧客申告借入額・年数・明示商品選択が必要です。取得価格は融資率条件のある商品だけに必要です。'


class AiEvidence(PublicModel):
    version: int | None = None
    property_selected: bool = False
    company_material_available: bool = False
    customer_declared: CustomerDeclaration | None = None
    property: CustomerProperty | None = None
    property_scope_conditions: list[str] = Field(default_factory=list)
    properties: list[CustomerCandidate] = Field(default_factory=list)
    items: list[EvidenceItem] = Field(default_factory=list)
    rates: list[EvidenceProduct] = Field(default_factory=list)
    mortgage: CustomerMortgage | None = None
    staff_call: CustomerStaffCall | None = None
    error: EvidenceError | None = None
