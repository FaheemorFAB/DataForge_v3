"""
dataforge/api/utils/ssrf.py
───────────────────────────
SSRF-safe HTTP client with DNS pinning and redirect validation.
Protects against:
  1. Internal / private IP scanning (RFC 1918, RFC 3927, RFC 6890, loopback, link-local, multicast).
  2. Cloud metadata extraction (AWS, GCP, Azure metadata endpoints).
  3. DNS rebinding (TOCTOU) via IP-pinned TCP/TLS sockets.
  4. Malicious redirect hops to internal services.
  5. Unsupported protocol schemes (file://, gopher://, dict://).
  6. Response size exhaustion DoS (streaming byte cap).
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin


class SSRFSecurityError(ValueError):
    """Raised when an external request violates network security boundaries."""
    pass


_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space / CGNAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("172.16.0.0/12"),      # Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # Private
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

_NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")


def is_safe_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Determine whether an IP address is a safe, routable public address."""
    # Handle IPv6 NAT64/DNS64 synthesis prefix (RFC 6052)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj in _NAT64_PREFIX:
        embedded_ipv4 = ipaddress.IPv4Address(ip_obj.packed[-4:])
        return is_safe_ip(embedded_ipv4)

    # Handle all forms of IPv4-mapped IPv6 (::ffff:0:0/96)
    if isinstance(ip_obj, ipaddress.IPv6Address):
        if ip_obj.ipv4_mapped:
            return is_safe_ip(ip_obj.ipv4_mapped)
        if ip_obj in ipaddress.ip_network("::ffff:0:0/96"):
            embedded_ipv4 = ipaddress.IPv4Address(ip_obj.packed[-4:])
            return is_safe_ip(embedded_ipv4)
        # Handle deprecated IPv4-compatible IPv6 (::/96)
        if ip_obj in ipaddress.ip_network("::/96"):
            if ip_obj != ipaddress.ip_address("::") and ip_obj != ipaddress.ip_address("::1"):
                embedded_ipv4 = ipaddress.IPv4Address(ip_obj.packed[-4:])
                return is_safe_ip(embedded_ipv4)

    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return False

    for blocked in _BLOCKED_NETWORKS:
        if isinstance(ip_obj, ipaddress.IPv4Address) and isinstance(blocked, ipaddress.IPv4Network):
            if ip_obj in blocked:
                return False
        elif isinstance(ip_obj, ipaddress.IPv6Address) and isinstance(blocked, ipaddress.IPv6Network):
            if ip_obj in blocked:
                return False

    return True


def validate_and_resolve_host(hostname: str, port: int) -> str:
    """
    Resolve target hostname and ensure EVERY resolved IP address is a safe public IP.
    Returns the first validated public IP string for socket pinning.
    """
    if not hostname:
        raise SSRFSecurityError("Missing hostname")

    lower_host = hostname.lower()
    if lower_host in ("localhost", "metadata.google.internal", "instance-data"):
        raise SSRFSecurityError(f"Access to host '{hostname}' is prohibited")

    # If hostname is already an IP literal
    try:
        ip = ipaddress.ip_address(hostname.strip("[]"))
        if not is_safe_ip(ip):
            raise SSRFSecurityError(f"Access to private/internal IP '{hostname}' is prohibited")
        return str(ip)
    except ValueError:
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFSecurityError(f"Could not resolve hostname '{hostname}': {e}") from e

    if not addr_info:
        raise SSRFSecurityError(f"No IP addresses resolved for hostname '{hostname}'")

    first_safe_ip = None
    for entry in addr_info:
        raw_ip = entry[4][0]
        ip = ipaddress.ip_address(raw_ip)
        if not is_safe_ip(ip):
            raise SSRFSecurityError(
                f"Hostname '{hostname}' resolved to disallowed private/internal IP '{raw_ip}'"
            )
        if first_safe_ip is None:
            first_safe_ip = str(ip)

    return first_safe_ip


def safe_fetch_url(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
    max_bytes: int = 50 * 1024 * 1024,  # 50 MB
    max_redirects: int = 3,
) -> Tuple[int, Dict[str, str], bytes]:
    """
    Safely fetch a remote HTTP or HTTPS URL with:
      - Scheme restriction (http/https only)
      - Pinned IP socket connection (defeating DNS rebinding)
      - Re-validated redirect chain
      - Streaming response body byte cap (defeating decompression/download bombs)
    """
    current_url = url
    redirect_count = 0

    import time
    start_time = time.monotonic()
    deadline = start_time + timeout

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SSRFSecurityError("Request overall timeout exceeded")

        parsed = urlparse(current_url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            raise SSRFSecurityError(f"Prohibited URL scheme '{scheme}'. Only http and https are permitted.")

        if parsed.username or parsed.password:
            raise SSRFSecurityError("Credentials embedded in URL are not allowed")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityError("Invalid URL: missing hostname")

        port = parsed.port or (443 if scheme == "https" else 80)
        if port not in (80, 443, 8080, 8443):
            raise SSRFSecurityError(f"Prohibited destination port '{port}'. Only standard web ports allowed.")

        # Resolve and validate IP
        pinned_ip = validate_and_resolve_host(hostname, port)

        # Build path and query
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        # Connect directly to the validated IP to defeat DNS rebinding (ignores ambient proxy vars)
        raw_sock = socket.create_connection((pinned_ip, port), timeout=remaining)
        raw_sock.settimeout(remaining)
        try:
            if scheme == "https":
                ctx = ssl.create_default_context()
                # Wrap socket validating that certificate matches original hostname
                secure_sock = ctx.wrap_socket(raw_sock, server_hostname=hostname)
                conn = http.client.HTTPSConnection(hostname, port=port, timeout=remaining)
                conn.sock = secure_sock
            else:
                conn = http.client.HTTPConnection(hostname, port=port, timeout=remaining)
                conn.sock = raw_sock

            req_headers = {
                "User-Agent": "DataForge/3.0 (Security-Enforced)",
                "Accept": "application/json, text/plain, */*",
                "Host": hostname if port in (80, 443) else f"{hostname}:{port}",
            }
            if headers:
                for k, v in headers.items():
                    if k.lower() != "host":
                        req_headers[k] = v

            conn.request("GET", path, headers=req_headers)
            resp = conn.getresponse()

            # Handle redirects safely
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location")
                if not location:
                    raise SSRFSecurityError(f"HTTP {resp.status} redirect without Location header")

                redirect_count += 1
                if redirect_count > max_redirects:
                    raise SSRFSecurityError(f"Too many redirects (exceeded limit of {max_redirects})")

                # Resolve relative redirect URLs safely
                current_url = urljoin(current_url, location)
                conn.close()
                continue

            # Read response body with streaming byte cap and deadline check
            accumulated = bytearray()
            while True:
                rem_time = deadline - time.monotonic()
                if rem_time <= 0:
                    raise SSRFSecurityError("Request overall timeout exceeded during body download")
                raw_sock.settimeout(rem_time)

                chunk = resp.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                accumulated.extend(chunk)
                if len(accumulated) > max_bytes:
                    raise SSRFSecurityError(
                        f"Response payload exceeds maximum allowed size ({max_bytes // (1024 * 1024)}MB)"
                    )

            resp_headers = dict(resp.getheaders())
            return resp.status, resp_headers, bytes(accumulated)

        finally:
            try:
                conn.close()
            except Exception:
                pass
