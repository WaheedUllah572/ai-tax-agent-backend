import requests

def convert_to_usd(amount, currency):
    try:
        if currency == "USD":
            return amount

        if currency == "PKR":
            # Simple live rate API (no auth)
            res = requests.get("https://api.exchangerate-api.com/v4/latest/PKR")
            data = res.json()

            rate = data["rates"]["USD"]

            return round(amount * rate, 2)

        return amount

    except:
        return amount