import streamlit as st

# -----------------------------
# PAGE CONFIG (controls install name + icon)
# -----------------------------
st.set_page_config(
    page_title="Phelps Deal Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("Phelps Holdings — Deal Analyzer")

# -----------------------------
# FUNCTIONS
# -----------------------------

def sba_guarantee_fee(guaranteed_amount: float) -> float:
    return 0.035 * guaranteed_amount


def annual_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0:
        return 0.0
    if annual_rate == 0:
        return principal / years
    r = annual_rate
    n = years
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def money(x):
    return f"${x:,.0f}"


# -----------------------------
# INPUTS
# -----------------------------

col1, col2 = st.columns(2)

with col1:
    purchase_price = st.number_input("Purchase Price", value=1_600_000)
    sde = st.number_input("Seller's Discretionary Earnings (SDE)", value=516_000)
    management_salary = st.number_input("Management Replacement (GM Salary)", value=100_000)
    down_payment = st.number_input("Down Payment (Cash In)", value=160_000)

with col2:
    seller_note_pct = st.slider("Seller Note %", 0, 50, 10) / 100
    seller_note_interest = st.slider("Seller Note Interest %", 0, 15, 6) / 100
    seller_note_term = st.slider("Seller Note Term (Years)", 1, 10, 5)

st.divider()

col3, col4 = st.columns(2)

with col3:
    bank_interest = st.slider("Bank / SBA Interest %", 0, 15, 10) / 100
    bank_term = st.slider("Bank / SBA Term (Years)", 5, 25, 10)

with col4:
    working_cap = st.number_input("Working Capital Added to Loan", value=0)
    sba_guarantee_pct = st.slider("SBA Guarantee %", 50, 90, 75) / 100
    target_dscr = st.number_input("Target DSCR", value=1.25)

# -----------------------------
# CALCULATIONS
# -----------------------------

normalized_earnings = sde - management_salary
seller_note = purchase_price * seller_note_pct
bank_base_loan = max(purchase_price - down_payment - seller_note, 0)

guaranteed_amount = bank_base_loan * sba_guarantee_pct
fee = sba_guarantee_fee(guaranteed_amount)

bank_loan = bank_base_loan + working_cap + fee

bank_annual = annual_payment(bank_loan, bank_interest, bank_term)
seller_annual = annual_payment(seller_note, seller_note_interest, seller_note_term)

total_debt = bank_annual + seller_annual
dscr = normalized_earnings / total_debt if total_debt > 0 else float("inf")
after_debt = normalized_earnings - total_debt

# -----------------------------
# OUTPUT
# -----------------------------

st.divider()
st.subheader("Deal Summary")

col5, col6, col7, col8 = st.columns(4)

col5.metric("DSCR", round(dscr, 2))
col6.metric("After Debt Cash Flow", money(after_debt))
col7.metric("Total Annual Debt", money(total_debt))
col8.metric("Total Bank Loan", money(bank_loan))

# Verdict
if dscr >= target_dscr:
    st.success("SBA-Ready 🟢")
elif dscr >= 1.10:
    st.warning("Tight but possible 🟡")
else:
    st.error("Risky 🔴")

# -----------------------------
# STRESS TEST
# -----------------------------

st.subheader("Stress Test")

for drop in [0, 0.10, 0.20]:
    stressed_earnings = normalized_earnings * (1 - drop)
    stressed_dscr = stressed_earnings / total_debt if total_debt > 0 else float("inf")
    stressed_after = stressed_earnings - total_debt

    st.write(
        f"{int(drop*100)}% Drop | "
        f"DSCR: {round(stressed_dscr,2)} | "
        f"After Debt: {money(stressed_after)}"
    )
