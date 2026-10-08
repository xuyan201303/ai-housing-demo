// Customer API allowlist. Generated from backend/app/schemas/customer.py.
export type CandidatesDisplay = {
  event_id: number
  kind: "properties"
  properties: Array<CustomerCandidate>
}

export type CustomerAnswer = {
  answer: string
  version: (number | null)
  references?: Array<CustomerSource>
  display_events?: Array<(PropertyDisplay | CandidatesDisplay | SourcesDisplay | ProductsDisplay | MortgageDisplay)>
  staff_call?: (CustomerStaffCall | null)
}

export type CustomerCandidate = {
  property_id: string
  property_name: string
}

export type CustomerHit = {
  text: string
  scope: "general" | "company" | "property"
  references?: Array<CustomerSource>
}

export type CustomerMessage = {
  event_id: number
  role: "user" | "assistant"
  text: string
  created_at?: (string | null)
  channel?: ("text" | "voice" | "policy" | null)
  references?: Array<CustomerSource>
  historical?: boolean
}

export type CustomerMortgage = {
  version: number
  rate_id: string
  bank?: (string | null)
  product?: (string | null)
  rate_type?: (string | null)
  property_price?: (number | null)
  down_payment?: (number | null)
  loan_amount: number
  annual_interest_rate: number
  years: number
  monthly_payment: number
  calculation_date: string
  effective_date: string
  valid_until: string
  rate_basis?: (string | null)
  price_basis?: (string | null)
  loan_to_value?: (number | null)
  loan_to_value_percent?: (number | null)
  conditions?: Array<string>
  product_notes?: string
  notes?: string
  references?: Array<CustomerSource>
}

export type CustomerProduct = {
  id: string
  bank: string
  product: string
  rate_type: string
  rate: number
  rate_over_90_percent?: (number | null)
  effective_date: string
  valid_until: string
  years_min?: (number | null)
  years_max?: (number | null)
  loan_amount_min?: (number | null)
  loan_amount_max?: (number | null)
  max_loan_to_value?: (number | null)
  notes?: string
  conditions?: Array<string>
  requires_acquisition_price_for_estimate?: boolean
  references?: Array<CustomerSource>
}

export type CustomerProperty = {
  property_id: string
  property_name: string
  lot?: (string | null)
  price?: (number | null)
  address?: (string | null)
  layout?: (string | null)
  station?: (string | null)
  walking_minutes?: (number | null)
  land_area?: (number | null)
  building_area?: (number | null)
  completion_date?: (string | null)
  parking?: (string | null)
  equipment?: Array<string>
  surroundings?: Array<string>
  scope_notices?: Array<string>
  checked_at?: (string | null)
  effective_date?: (string | null)
  valid_until?: (string | null)
  references?: Array<CustomerSource>
}

export type CustomerRealtime = {
  status: "not_started" | "connecting" | "connected" | "closing" | "closed" | "error" | "disconnected"
  error?: (CustomerVoiceError | null)
}

export type CustomerSession = {
  id: string
  version: (number | null)
  mode: "text" | "voice"
  property_id: (string | null)
  status: "active" | "ended"
  created_at: string
  ended_at?: (string | null)
  property?: (CustomerProperty | null)
  products?: Array<CustomerProduct>
  messages?: Array<CustomerMessage>
  display_events?: Array<(PropertyDisplay | CandidatesDisplay | SourcesDisplay | ProductsDisplay | MortgageDisplay)>
  staff_calls?: Array<CustomerStaffCall>
  realtime: CustomerRealtime
}

export type CustomerSessionCreated = {
  id: string
  version: (number | null)
  mode: "text" | "voice"
  property_id: (string | null)
  status: "active" | "ended"
  created_at: string
  ended_at?: (string | null)
  property?: (CustomerProperty | null)
  products?: Array<CustomerProduct>
  messages?: Array<CustomerMessage>
  display_events?: Array<(PropertyDisplay | CandidatesDisplay | SourcesDisplay | ProductsDisplay | MortgageDisplay)>
  staff_calls?: Array<CustomerStaffCall>
  realtime: CustomerRealtime
  token: string
}

export type CustomerSource = {
  label: string
  url?: (string | null)
}

export type CustomerStaffCall = {
  id: string
  status: "pending" | "accepted" | "completed"
  customer_message: string
  created_at?: (string | null)
  accepted_at?: (string | null)
  completed_at?: (string | null)
}

export type CustomerVoiceError = {
  code?: "VOICE_CONNECTION_ERROR"
  message?: string
}

export type MortgageDisplay = {
  event_id: number
  kind: "mortgage"
  result: CustomerMortgage
}

export type ProductsDisplay = {
  event_id: number
  kind: "products"
  products: Array<CustomerProduct>
}

export type PropertyDisplay = {
  event_id: number
  kind: "property"
  property: CustomerProperty
}

export type SourcesDisplay = {
  event_id: number
  kind: "sources"
  items: Array<CustomerHit>
}

export type CustomerSessionWithToken = CustomerSession & { token: string }
export type CustomerDisplay = NonNullable<CustomerSession["display_events"]>[number]
