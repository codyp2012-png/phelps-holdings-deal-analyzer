import streamlit as st

def sba_guarantee_fee(guaranteed_amount: float) -> float:
    return 0.035 * guaranteed_amount

def annual_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0:
        return 0.0
    r = annual_rate
    n = years
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

def compute(purchase_price, sde, management_salary, down_payment,
            seller_note_pct, seller_note_interest, seller_note_term,
            bank_interest, bank_term, working_cap, sba_guarantee_pct,
            stress_mult):
    normalized_earnings = (sde - management_salary) * stress_mult
    seller_note = purchase_price * seller_note_pct

    bank_base_loan = purchase_price - down_payment - seller_note
    bank_base_loan = max(bank_base_loan, 0.0)

    guaranteed_amount = bank_base_loan * sba_guarantee_pct
    fee = sba_guarantee_fee(guaranteed_amount)

    bank_loan = bank_base_loan + working_cap + fee

    bank_annual = annual_payment(bank_loan, bank_interest, bank_term)
    seller_annual = annual_payment(seller_note, seller_note_interest, seller_note_term) if seller_note > 0 else 0.0

    total_debt = bank_annual + seller_annual
    dscr = normalized_earnings / total_debt if total_debt > 0 else float("inf")
    after_debt = normalized_earnings - total_debt

    return {
        "normalized_earnings": normalized_earnings,
        "seller_note": seller_note,
        "bank_base_loan": bank_base_loan,
        "fee": fee,
        "bank_loan": bank_loan,
        "bank_annual": bank_annual,
        "seller_annual": seller_annual,
        "total_debt": total_debt,
        "dscr": dscr,
        "after_debt": after_debt,
    }

def min_down_for_target(purchase_price, sde, management_salary,
                        seller_note_pct, seller_note_interest, seller_note_term,
                        bank_interest, bank_term, working_cap, sba_guarantee_pct,
                        target_dscr, stress_mult):
    lo = 0.0
    hi = purchase_price * 0.80

    def dscr_at(down):
        return compute(purchase_price, sde, management_salary, down,
                       seller_note_pct, seller_note_interest, seller_note_term,
                       bank_interest, bank_term, working_cap, sba_guarantee_pct,
                       stress_mult)["dscr"]

    if dscr_at(hi) < target_dscr:
        return None
    if dscr_at(lo) >= target_dscr:
        return 0.0

    for _ in range(60):
        mid = (lo + hi) / 2
        if dscr_at(mid) >= target_dscr:
            hi = mid
        else:
            lo = mid
    return hi

st.set_page_config(page_title="Phelps Holdings Deal Analyzer", layout="wide")
st.title("Phelps Holdings — Deal Analyzer Dashboard")

left, right = st.columns(2)

with left:
    st.subheader("Deal Inputs")
    purchase_price = st.number_input("Purchase Price", min_value=0.0, value=1600000.0, step=10000.0)
    sde = st.number_input("SDE", min_value=0.0, value=516000.0, step=1000.0)
    management_salary = st.number_input("Management Replacement / GM Salary", min_value=0.0, value=0.0, step=5000.0)

    down_payment = st.number_input("Down Payment (Cash In)", min_value=0.0, value=160000.0, step=5000.0)

    st.subheader("Seller Note")
    seller_note_pct = st.slider("Seller Note %", 0.0, 30.0, 10.0, 0.5) / 100
    seller_note_interest = st.slider("Seller Note Interest %", 0.0, 15.0, 6.0, 0.25) / 100
    seller_note_term = st.slider("Seller Note Term (years)", 1, 10, 5)

with right:
    st.subheader("Bank / SBA")
    bank_interest = st.slider("Bank/SBA Interest %", 0.0, 20.0, 10.0, 0.25) / 100
    bank_term = st.slider("Bank/SBA Term (years)", 5, 25, 10)
    working_cap = st.number_input("Working Capital Added to Loan", min_value=0.0, value=0.0, step=5000.0)
    sba_guarantee_pct = st.slider("SBA Guarantee %", 50.0, 90.0, 75.0, 1.0) / 100
    target_dscr = st.number_input("Target DSCR", min_value=1.0, value=1.25, step=0.05)

st.divider()

cases = [("Base (0%)", 1.00), ("-10%", 0.90), ("-20%", 0.80)]
rows = []
base = compute(purchase_price, sde, management_salary, down_payment,
               seller_note_pct, seller_note_interest, seller_note_term,
               bank_interest, bank_term, working_cap, sba_guarantee_pct, 1.0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("DSCR (Base)", f"{base['dscr']:.2f}")
col2.metric("After Debt (Base)", f"${base['after_debt']:,.0f}")
col3.metric("Total Annual Debt", f"${base['total_debt']:,.0f}")
col4.metric("Bank Loan (incl fee+WC)", f"${base['bank_loan']:,.0f}")

st.subheader("Stress Test (Normalized)")
for label, mult in cases:
    r = compute(purchase_price, sde, management_salary, down_payment,
                seller_note_pct, seller_note_interest, seller_note_term,
                bank_interest, bank_term, working_cap, sba_guarantee_pct, mult)
    rows.append((label, r["normalized_earnings"], r["dscr"], r["after_debt"]))

st.table({
    "Scenario": [r[0] for r in rows],
    "Normalized Earnings": [f"${r[1]:,.0f}" for r in rows],
    "DSCR": [f"{r[2]:.2f}" for r in rows],
    "After Debt": [f"${r[3]:,.0f}" for r in rows],
})

st.subheader("Minimum Down Payment Needed (for DSCR Target)")
min_base = min_down_for_target(purchase_price, sde, management_salary,
                               seller_note_pct, seller_note_interest, seller_note_term,
                               bank_interest, bank_term, working_cap, sba_guarantee_pct,
                               target_dscr, 1.0)
min_20 = min_down_for_target(purchase_price, sde, management_salary,
                             seller_note_pct, seller_note_interest, seller_note_term,
                             bank_interest, bank_term, working_cap, sba_guarantee_pct,
                             target_dscr, 0.8)

c1, c2 = st.columns(2)
if min_base is None:
    c1.error(f"Base: can't reach DSCR {target_dscr:.2f} even with 80% down.")
else:
    c1.success(f"Base: ${min_base:,.0f} ({(min_base/purchase_price)*100:.1f}%)")

if min_20 is None:
    c2.error(f"-20%: can't reach DSCR {target_dscr:.2f} even with 80% down.")
else:
    c2.success(f"-20%: ${min_20:,.0f} ({(min_20/purchase_price)*100:.1f}%)")