"""OBO identity capture (PLAN 9.2).

The app authenticates as its service principal for system actions but records
approvals with on-behalf-of-user identity so the audit trail names the human.
In a Databricks App the user identity arrives in a forwarded header; locally it
falls back to a dev identity so contract tests run without the proxy.
"""

from __future__ import annotations

from fastapi import Request

# Databricks Apps forwards the end-user identity in this header.
_OBO_HEADER = "x-forwarded-email"
_OBO_USER_HEADER = "x-forwarded-user"
_DEV_IDENTITY = "dev-user@tesco-demo.example"


def resolver_identity(request: Request) -> str:
    """Return the human identity to stamp on an approve/reject action."""
    email = request.headers.get(_OBO_HEADER)
    if email:
        return email
    user = request.headers.get(_OBO_USER_HEADER)
    if user:
        return user
    return _DEV_IDENTITY
