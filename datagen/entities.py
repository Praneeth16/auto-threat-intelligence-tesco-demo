"""Employees, groups, and brand reference.

Builds ref_employees (200 rows) with the three scripted characters at fixed
IDs, then Faker-fills the rest deterministically. Also builds ref_brand_assets
from the protected-brand reference.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from faker import Faker

from datagen import config
from datagen.common import rng


@dataclass
class Employee:
    employee_id: str
    full_name: str
    email: str
    department: str
    job_title: str
    ad_groups: list[str]
    is_privileged: bool
    is_vip: bool
    office_location: str
    usual_country: str


def _email_for(full_name: str, employee_id: str) -> str:
    """first.last@domain, disambiguated by employee_id suffix to stay unique."""
    parts = full_name.lower().replace(".", "").split()
    slug = ".".join(p for p in parts if p) or "user"
    # Suffix keeps duplicates (common Faker collisions) unique.
    return f"{slug}.{employee_id[-3:]}@{config.EMPLOYEE_EMAIL_DOMAIN}"


def build_employees() -> pd.DataFrame:
    """Return the ref_employees table (PLAN 5.3)."""
    faker = Faker("en_GB")
    faker.seed_instance(config.SEED)
    r = rng("employees")

    rows: list[Employee] = []
    named_ids = set()

    # 1. Scripted characters first, at their exact IDs.
    for ne in config.NAMED_EMPLOYEES:
        usual_country = config.OFFICES[ne.office_location]
        rows.append(
            Employee(
                employee_id=ne.employee_id,
                full_name=ne.full_name,
                email=_email_for(ne.full_name, ne.employee_id),
                department=ne.department,
                job_title=ne.job_title,
                ad_groups=list(ne.ad_groups),
                is_privileged=ne.is_privileged,
                is_vip=ne.is_vip,
                office_location=ne.office_location,
                usual_country=usual_country,
            )
        )
        named_ids.add(ne.employee_id)

    # 2. Faker-fill the remainder up to N_EMPLOYEES.
    office_names = list(config.OFFICES.keys())
    idx = len(rows) + 1
    while len(rows) < config.N_EMPLOYEES:
        emp_id = f"E{idx:04d}"
        idx += 1
        if emp_id in named_ids:
            continue
        office = r.choice(office_names)
        rows.append(
            Employee(
                employee_id=emp_id,
                full_name=faker.name(),
                email="",  # filled after, needs id
                department=r.choice(config.DEPARTMENTS),
                job_title=faker.job(),
                ad_groups=[],  # filled below
                is_privileged=False,
                is_vip=False,
                office_location=office,
                usual_country=config.OFFICES[office],
            )
        )

    for e in rows:
        if not e.email:
            e.email = _email_for(e.full_name, e.employee_id)

    # 3. Assign privileged and VIP among the Faker-filled rows so the exact
    #    counts hold. Named characters keep their scripted flags.
    fillable = [e for e in rows if e.employee_id not in named_ids]
    named_privileged = sum(1 for e in rows if e.employee_id in named_ids and e.is_privileged)
    named_vip = sum(1 for e in rows if e.employee_id in named_ids and e.is_vip)

    n_more_priv = config.N_PRIVILEGED - named_privileged
    priv_pick = r.sample(fillable, k=n_more_priv)
    for e in priv_pick:
        e.is_privileged = True
        e.ad_groups = [r.choice(config.PRIVILEGED_GROUPS)]

    # Give the non-privileged fillers a plausible department group.
    for e in fillable:
        if not e.ad_groups:
            e.ad_groups = [f"{e.department.split()[0]}-Team"]

    vip_pool = [e for e in fillable if e not in priv_pick]
    n_more_vip = config.N_VIP - named_vip
    for e in r.sample(vip_pool, k=n_more_vip):
        e.is_vip = True

    df = pd.DataFrame([e.__dict__ for e in rows])
    return df.sort_values("employee_id").reset_index(drop=True)


def build_brand_assets() -> pd.DataFrame:
    """Return ref_brand_assets: the legitimate brand reference (PLAN 5.6)."""
    rows = []
    for d in config.PROTECTED_BRAND_DOMAINS:
        rows.append({"asset_type": "domain", "value": d})
    for t in config.PROTECTED_BRAND_TOKENS:
        rows.append({"asset_type": "token", "value": t})
    return pd.DataFrame(rows)
