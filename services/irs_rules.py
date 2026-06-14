import re


def clean_amount(amount):
    try:
        if isinstance(amount, str):
            # Remove currency words and symbols
            amount = amount.replace(",", "")
            amount = re.sub(r"[A-Za-zRs$€£ ]", "", amount)
        return float(amount)
    except:
        return 0.0


def apply_tax_rules(
    category,
    amount,
    jurisdiction="US"
):
    amount = clean_amount(amount)

    category = (category or "").lower()

    # Default values
    irs_category = "Schedule C - Other Expenses"
    deductible_percent = 100
    rule_applied = "general_expense_rule"

    # IRS RULES
    if "meal" in category or "restaurant" in category or "food" in category:

     if jurisdiction == "US":
        deductible_percent = 50

    elif jurisdiction == "UK":
        deductible_percent = 100

    elif jurisdiction == "AU":
        deductible_percent = 100

    elif jurisdiction == "CA":
        deductible_percent = 50

    elif "uber" in category or "lyft" in category or "transport" in category or "vehicle" in category:
        irs_category = "Schedule C - Car and Truck Expenses"
        deductible_percent = 100
        rule_applied = "vehicle_expense_rule"

    elif "software" in category or "subscription" in category or "saas" in category:
        irs_category = "Schedule C - Office Expenses"
        deductible_percent = 100
        rule_applied = "software_rule"

    elif "office" in category or "supplies" in category:
        irs_category = "Schedule C - Office Expenses"
        deductible_percent = 100
        rule_applied = "office_expense_rule"

    # ✅ NEW UTILITY RULE ADDED HERE
    elif "utility" in category or "internet" in category or "phone" in category or "electric" in category:
        irs_category = "Schedule C - Utilities"
        deductible_percent = 100
        rule_applied = "utilities_rule"

    elif "travel" in category or "hotel" in category or "flight" in category:
        irs_category = "Schedule C - Travel"
        deductible_percent = 100
        rule_applied = "travel_rule"

    elif "transfer" in category:
        # Internal transfers are NOT deductible
        irs_category = "Non-Deductible"
        deductible_percent = 0
        rule_applied = "internal_transfer_rule"

    deductible_amount = round(amount * (deductible_percent / 100), 2)

    return {
        "irs_category": irs_category,
        "deductible_percent": deductible_percent,
        "deductible_amount": deductible_amount,
        "rule_applied": rule_applied
    }