from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https"}
PRIVATE_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "::1/128",
    )
]


def is_public_host(host: str) -> bool:
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for _fam, _typ, _pro, _nam, sa in infos:
        ip = ipaddress.ip_address(sa[0])
        if any(ip in net for net in PRIVATE_NETS):
            return False
    return True


def validate_target(url: str) -> str:
    sp = urlsplit(url)
    if sp.scheme not in ALLOWED_SCHEMES:
        raise ValueError("unsupported scheme")
    if not is_public_host(sp.hostname or ""):
        raise ValueError("blocked host")
    # could canonicalize host case and drop default ports here if needed
    return url

