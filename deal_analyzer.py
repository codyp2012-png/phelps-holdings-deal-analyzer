# Deal Analyzer v3 - Phelps Holdings
# Adds:
# - Management replacement / normalized earnings
# - Auto-min down payment to hit DSCR target (base & stress)
# - Stress tests (0, -10, -20)

from dataclasses import dataclass

def sba_guarantee_fee(guaranteed_amount: float) -> float:
    # Practical placeholder estimate (~3.5% of guaranteed portion)
    return 0.035 * guaranteed_amount

def annual_payment(principal: float, annual_rate: float, years: int) -> float:
    r = annual_rate
    n = years
    if principal <= 0:
        return 0.0
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

def money(x: float) -> str:
    return f"${x:,.2f}"

@dataclass
class DealInputs:
    purchase_price: float
    sde: float
    management_salary: float

    seller_note_pct: float
    seller_note_interest: float
    seller_note_term: int

    bank_interest: float
    bank_term: int

    working_cap: float
    sba_guarantee_pct: float

def compute(deal: DealInputs, down_payment: float, stress_mult: float = 1.0):
    # Normalized earnings (replace owner/operator)
    normalized_earnings = (deal.sde - deal.management_salary) * stress_mult

    seller_note = deal.purchase_price * deal.seller_note_pct

    bank_base_loan = deal.purchase_price - down_payment - seller_note
    if bank_base_loan < 0:
        bank_base_loan = 0.0

    guaranteed_amount = bank_base_loan * deal.sba_guarantee_pct
    fee = sba_guarantee_fee(guaranteed_amount)

    bank_loan = bank_base_loan + deal.working_cap + fee

    bank_annual = annual_payment(bank_loan, deal.bank_interest, deal.bank_term)
    seller_annual = annual_payment(seller_note, deal.seller_note_interest, deal.seller_note_term) if seller_note > 0 else 0.0

    total_annual_debt = bank_annual + seller_annual

    dscr = normalized_earnings / total_annual_debt if total_annual_debt > 0 else float("inf")
    after_debt = normalized_earnings - total_annual_debt
    coc = (after_debt / down_payment) * 100 if down_payment > 0 else float("inf")

    return {
        "normalized_earnings": normalized_earnings,
        "seller_note": seller_note,
        "bank_base_loan": bank_base_loan,
        "fee": fee,
        "bank_loan": bank_loan,
        "bank_annual": bank_annual,
        "seller_annual": seller_annual,
        "total_annual_debt": total_annual_debt,
        "dscr": dscr,
        "after_debt": after_debt,
        "coc": coc,
    }

def min_down_for_target_dscr(deal: DealInputs, target_dscr: float, stress_mult: float):
    """
    Binary search for minimum down payment to hit DSCR target at a given stress multiplier.
    Searches between 0% and 80% of purchase price.
    """
    lo = 0.0
    hi = deal.purchase_price * 0.80

    # If even at 80% down you can't hit DSCR, return None
    if compute(deal, hi, stress_mult)["dscr"] < target_dscr:
        return None

    # If at 0 down it already hits it, return 0
    if compute(deal, lo, stress_mult)["dscr"] >= target_dscr:
        return 0.0

    for _ in range(60):  # enough precision
        mid = (lo + hi) / 2
        dscr_mid = compute(deal, mid, stress_mult)["dscr"]
        if dscr_mid >= target_dscr:
            hi = mid
        else:
            lo = mid
    return hi

def verdict(dscr: float) -> str:
    if dscr >= 1.25:
        return "SBA-Ready 🟢"
    if dscr >= 1.10:
        return "Tight but possible 🟡"
    return "Risky 🔴"

if __name__ == "__main__":
    print("Phelps Holdings Deal Analyzer v3\n")

    purchase_price = float(input("Purchase price: "))
    sde = float(input("Seller's Discretionary Earnings (SDE): "))
    management_salary = float(input("Management replacement / GM salary (0 if none): "))

    down_payment = float(input("Down payment (cash in): "))

    seller_note_pct = float(input("Seller note % of purchase price (e.g., 10): ")) / 100
    seller_note_interest = float(input("Seller note interest % (e.g., 6): ")) / 100
    seller_note_term = int(input("Seller note term (years, e.g., 5): "))

    bank_interest = float(input("Bank/SBA interest % (e.g., 10): ")) / 100
    bank_term = int(input("Bank/SBA term (years, e.g., 10): "))

    working_cap = float(input("Working capital to add to loan (0 if none): "))

    sba_guarantee_pct = float(input("SBA guarantee % (typical 75): ")) / 100

    target_dscr = float(input("Target DSCR (typical 1.25): "))

    deal = DealInputs(
        purchase_price=purchase_price,
        sde=sde,
        management_salary=management_salary,
        seller_note_pct=seller_note_pct,
        seller_note_interest=seller_note_interest,
        seller_note_term=seller_note_term,
        bank_interest=bank_interest,
        bank_term=bank_term,
        working_cap=working_cap,
        sba_guarantee_pct=sba_guarantee_pct,
    )

    # Base / stress outputs
    cases = [("Base (0%)", 1.00), ("-10% earnings", 0.90), ("-20% earnings", 0.80)]
    base = compute(deal, down_payment, 1.00)

    print("\n--- Structure ---")
    print(f"Purchase Price: {money(purchase_price)}")
    print(f"Down Payment:   {money(down_payment)}")
    print(f"Mgmt Salary:    {money(management_salary)}  (Normalized Earnings = SDE - Mgmt)")
    print(f"Seller Note:    {money(base['seller_note'])} ({seller_note_pct*100:.1f}%)")
    print(f"Bank Base Loan: {money(base['bank_base_loan'])}")
    print(f"Working Cap:    {money(working_cap)}")
    print(f"SBA Fee (est):  {money(base['fee'])}")
    print(f"Total Bank Loan:{money(base['bank_loan'])}")

    print("\n--- Annual Debt Service ---")
    print(f"Bank Annual Payment:   {money(base['bank_annual'])}")
    print(f"Seller Annual Payment: {money(base['seller_annual'])}")
    print(f"Total Annual Debt:     {money(base['total_annual_debt'])}")

    print("\n--- Performance (Normalized) ---")
    print(f"Normalized Earnings (Base): {money(base['normalized_earnings'])}")
    print(f"DSCR (Base): {base['dscr']:.2f}  | Verdict: {verdict(base['dscr'])}")
    print(f"After Debt (Base): {money(base['after_debt'])}")
    print(f"Cash-on-Cash (Base): {base['coc']:.2f}%")

    print("\n--- Stress Test (Normalized) ---")
    for label, mult in cases:
        r = compute(deal, down_payment, mult)
        print(f"{label:14} | Earnings: {money(r['normalized_earnings']):>12} | DSCR: {r['dscr']:>5.2f} | After Debt: {money(r['after_debt'])}")

    # Min down payment solver
    min_down_base = min_down_for_target_dscr(deal, target_dscr, 1.00)
    min_down_stress20 = min_down_for_target_dscr(deal, target_dscr, 0.80)

    print("\n--- Minimum Down Payment Needed ---")
    if min_down_base is None:
        print(f"Base:   Cannot reach DSCR {target_dscr:.2f} even with 80% down.")
    else:
        print(f"Base:   {money(min_down_base)}  ({(min_down_base/purchase_price)*100:.1f}%) to hit DSCR {target_dscr:.2f}")

    if min_down_stress20 is None:
        print(f"-20%:   Cannot reach DSCR {target_dscr:.2f} even with 80% down.")
    else:
        print(f"-20%:   {money(min_down_stress20)}  ({(min_down_stress20/purchase_price)*100:.1f}%) to hit DSCR {target_dscr:.2f} under -20%")