import ipaddress
import os

from mitmproxy import dns, http

STARPOINT_HOST = os.environ.get("STARPOINT_HOST", "starpoint")
STARPOINT_PORT = int(os.environ.get("STARPOINT_PORT", "8000"))
STARPOINT_SCHEME = os.environ.get("STARPOINT_SCHEME", "http")

# Reserved documentation subnet; black-holed after CNAME rewrite.
API_DNS_REDIRECT_HOST = ipaddress.IPv4Address("198.51.100.140")
DNS_TTL = 600
MAGIC_DOMAIN_SUFFIX = ".mitm.it"

prefixes = ["/openapi", "/infodesk", "", "/patch"]

# hostname: prefix_index
hosts = {
    # openapi
    "openapi-zinny3.game.kakao.com": 0,
    "openapi-zinny3.game.kakaogames.com": 0,
    "gc-openapi-zinny3.kakaogames.com": 0,

    # infodesk
    "gc-infodesk-zinny3.kakaogames.com": 1,

    # na server
    "na.wdfp.kakaogames.com": 2,

    # patch / CDN
    "patch.wdfp.kakaogames.com": 3,
}


def dns_request(flow: dns.DNSFlow):
    if not flow.request.query or flow.request.questions is None:
        return

    for question in flow.request.questions:
        prefix_type = hosts.get(question.name) if question.type == 1 else None
        if prefix_type is None:
            continue

        flow.response.answers = [
            answer for answer in flow.response.answers if answer.name != question.name
        ]
        domain_redirect = f"{question.name}{MAGIC_DOMAIN_SUFFIX}"
        cname_rec = dns.ResourceRecord.CNAME(question.name, domain_redirect, ttl=DNS_TTL)
        a_rec = dns.ResourceRecord.A(domain_redirect, API_DNS_REDIRECT_HOST, ttl=DNS_TTL)
        flow.response.answers.append(cname_rec)
        flow.response.answers.append(a_rec)


def request(flow: http.HTTPFlow):
    prefix_type = hosts.get(flow.request.pretty_host)
    if prefix_type is None:
        return

    flow.request.host = STARPOINT_HOST
    flow.request.port = STARPOINT_PORT
    flow.request.scheme = STARPOINT_SCHEME

    prefix = prefixes[prefix_type]
    if prefix != "":
        flow.request.path = f"{prefix}{flow.request.path}"
