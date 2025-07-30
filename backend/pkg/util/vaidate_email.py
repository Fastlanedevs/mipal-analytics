def is_company_email(email: str) -> bool:
    # List of common generic email providers
    generic_providers = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "protonmail.com",
        "proton.me",
        "mail.com",
        "zoho.com",
        "yandex.com",
        "live.com",
        "msn.com",
    }

    # Basic email format validation
    if not email or "@" not in email:
        raise ValueError("Invalid email format")

    # Extract the domain part of the email
    try:
        domain = email.lower().split("@")[1]
    except IndexError:
        raise ValueError("Invalid email format")

    # Check if the domain is in the list of generic providers
    return domain not in generic_providers


def get_domain(email: str) -> str | None:
    if is_company_email(email):
        return email.split("@")[1]
