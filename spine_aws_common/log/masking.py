"""
Created 18th June 2019
"""
import re


# SPII-15583 Match both direct Werkzeug output and Flask application log
# messages
TICKET_PATTERN = re.compile("(.*)/ticket([^ ]+)(.*)")

# SPII-22963 Ensure Tornado messages are redacted, this might also contain
# new lines
GP_PROVIDER_PATTERN = re.compile(r"(.*)'GPPROVIDER_\S+'(.*)", re.DOTALL)
# Ensure nhsNumbers in fhir messages in Tornado messages are redacted, this
# might also contain new lines
# fhir.nhs.uk/Id/nhs-number|
NHS_NUMBER_PATTERN = re.compile(r"(.*fhir.nhs.uk.*)nhs-number\%7C\d+(.*)", re.DOTALL)

# flake8: noqa: E501
# pylint:disable=line-too-long
URL_PID_PATTERN = (
    "([?&])(nhs[nN]umber|identifier|forename|surname|othername|title|suffix|dateOfBirth|"
    + "timeOfBirth|address_doornumbername_Holder_Field|address_street_Holder_Field|address_town_Holder_Field|"
    + "address_locality_Holder_Field|address_county_Holder_Field|address_postcode_Holder_Field|"
    + "address_pafKey_Holder_Field)=[^& ]+"
)
# pylint:enable=line-too-long
URL_PID_REPL = r"\1\2=___MASKED___"
URL_PID_RE_COMPILED = re.compile(URL_PID_PATTERN)


def mask_ticket(val):
    """
    Mask the ticket (eg. "/demographicspineapplication/ticket?id=123... "
    would become:
    "/demographicspineapplication/ticket ___TICKET_MASKED___ "
    """
    match = TICKET_PATTERN.match(val)
    if match:
        masked_val = match.group(1) + "/ticket ___TICKET_MASKED___ "
        if match.lastindex > 2:
            return masked_val + match.group(3)
        return masked_val
    return val


def mask_gp_provider(val):
    """
    Mask the GPProvider part as it contains PID.
    """
    match = GP_PROVIDER_PATTERN.match(val)
    if match:
        masked_val = match.group(1) + "'GPPROVIDER___MASKED___'"
        if match.lastindex > 1:
            return masked_val + match.group(2)
        return masked_val
    return val


def mask_nhs_number(val):
    """
    Mask the GPProvider part as it contains PID.
    """
    match = NHS_NUMBER_PATTERN.match(val)
    if match:
        masked_val = match.group(1) + "nhs-number%7C___MASKED___"
        if match.lastindex > 1:
            return masked_val + match.group(2)
        return masked_val
    return val


def mask_sensitive_url_data(val):
    """
    Mask any true patient-identifying data from the query string of a URL,
    including NHS number.
    This is initially based on a number allocation request in DSA rest
    """
    return URL_PID_RE_COMPILED.sub(URL_PID_REPL, val)


def mask_pid(val):
    """
    Mask any PID info
    """
    masked = mask_ticket(val)
    masked = mask_gp_provider(masked)
    masked = mask_nhs_number(masked)
    masked = mask_sensitive_url_data(masked)
    return masked


def mask_url(log_row_dict):
    """
    Mask out everything after a "ticket" or nhsNumber substring in the URL
    """

    def mask(key, val):
        """
        Mask only the relevant key values
        """
        if key in ["url", "requestUrl"]:
            return mask_pid(val)
        return val

    return {key: mask(key, value) for (key, value) in log_row_dict.items()}
