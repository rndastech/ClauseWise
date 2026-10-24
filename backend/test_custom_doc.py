from dotenv import load_dotenv
load_dotenv()
from backend.agent.sarvam_client import get_sarvam_client, extract_json_from_response

client = get_sarvam_client()
contract_text = """
COMMERCIAL LEASE AGREEMENT
1. Rent Payment: CloudScale Ltd (Tenant) shall pay monthly rent of INR 3,50,000 to Landlord on or before the 5th of each calendar month.
2. Security Deposit: Tenant shall maintain a security deposit of INR 21,00,000 refundable within 45 days of lease termination.
3. Lock-in Period & Penalty: The lease has a 36-month lock-in. If Tenant terminates early, the entire security deposit of INR 21,00,000 shall be forfeited to Landlord.
"""

prompt = f"""You are ClauseWise Contract Intelligence Engine. Analyze the following legal document.
Extract all legal obligations, conditions, deadlines, monetary amounts, and clause references.

Document Text:
\"\"\"
{contract_text}
\"\"\"

Return ONLY a valid JSON array of objects. Each object must follow this structure:
[
  {{
    "clause_title": "string (e.g. Clause 1: Rent Payment)",
    "clause_type": "string (e.g. payment, penalty, deposit)",
    "page": "1",
    "verbatim_text": "string (exact quotation)",
    "evidence_ref": "string (e.g. Section 1)",
    "obligation_title": "string (e.g. Monthly Rent Payment)",
    "original_wording": "string",
    "condition": "string",
    "interpreted_deadline": "string",
    "party_obligated": "string",
    "party_beneficiary": "string",
    "amount": "string",
    "currency": "INR",
    "risk_level": "high | medium | low",
    "confidence": 0.95
  }}
]
"""

res = client.chat.completions(
    model='sarvam-105b-conversations',
    messages=[
        {'role': 'user', 'content': prompt}
    ]
)

raw = res.choices[0].message.content
print('RAW OUTPUT:\n', raw)
parsed = extract_json_from_response(raw)
print('\nPARSED JSON ARRAY COUNT:', len(parsed) if isinstance(parsed, list) else type(parsed))
