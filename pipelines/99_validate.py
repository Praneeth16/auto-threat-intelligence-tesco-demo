# Databricks notebook source
# MAGIC %md
# MAGIC # 99 - Pre-demo validation gate
# MAGIC
# MAGIC Hard asserts against the loaded Unity Catalog tables (PLAN Section 13.1).
# MAGIC Row counts, named domains, feed-gap, AP invariants, counterexamples,
# MAGIC filler routing, and reference-output rank order. Run after `00_load_world`
# MAGIC and before every rehearsal. Any failure blocks the demo.
# MAGIC
# MAGIC Reads tables through Spark when run in-workspace. The pure-Python invariant
# MAGIC suite (`datagen/tests`) is the build-time twin of this notebook; this one
# MAGIC proves the data actually landed in Unity Catalog correctly.

# COMMAND ----------

import sys
from pathlib import Path

_REPO = None
for _cand in (".", "..", "/Workspace/Repos"):
    if (Path(_cand) / "datagen").exists():
        _REPO = str(Path(_cand).resolve())
        break
if _REPO and _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from datagen import config  # noqa: E402
from pipelines.workspace_config import fq  # noqa: E402

spark  # noqa: F821

_FAILURES: list[str] = []
_WARNINGS: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        msg = f"FAIL  {name}" + (f"  ({detail})" if detail else "")
        print(msg)
        _FAILURES.append(msg)


def warn(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        msg = f"WARN  {name}" + (f"  ({detail})" if detail else "")
        print(msg)
        _WARNINGS.append(msg)


def tbl(table: str):
    return spark.table(fq(table))


def count(table: str) -> int:
    return tbl(table).count()

# COMMAND ----------

# MAGIC %md ## Row counts within +/-2%

# COMMAND ----------

_TOL = config.ROW_COUNT_TOLERANCE
for table, target in [
    ("bronze_dns_logs", config.BRONZE_DNS_ROWS),
    ("bronze_proxy_logs", config.BRONZE_PROXY_ROWS),
    ("bronze_email_events", config.BRONZE_EMAIL_ROWS),
    ("bronze_auth_logs", config.BRONZE_AUTH_ROWS),
]:
    n = count(table)
    check(f"row count {table}", target * (1 - _TOL) <= n <= target * (1 + _TOL),
          f"{n} vs {target}")

check("employee count", count("ref_employees") == config.N_EMPLOYEES)
check("structured IOC count", count("structured_iocs") == config.TOTAL_STRUCTURED_IOCS)
check("report count", count("bronze_reports") == config.N_REPORTS)

# COMMAND ----------

# MAGIC %md ## Named domains exist in their sources; feed-gap absent

# COMMAND ----------

ioc_vals = {r["indicator_value"] for r in tbl("structured_iocs").select("indicator_value").collect()}
for d in (config.CAMPAIGN_A_NAMED_DOMAINS + config.CAMPAIGN_B_NAMED_DOMAINS
          + config.CAMPAIGN_C_NAMED_DOMAINS + [config.DECOY_DOMAIN]):
    check(f"named domain present: {d}", d in ioc_vals)

# Feed-gap domain absent from all structured feeds.
check("feed-gap domain absent from structured feeds",
      config.REPORT_ONLY_DOMAIN not in ioc_vals)

# Feed-gap present in DNS with exactly 2 distinct employees.
dns = tbl("bronze_dns_logs")
gap_emps = (dns.filter(dns.query_domain == config.REPORT_ONLY_DOMAIN)
            .select("employee_id").distinct().count())
check("feed-gap DNS distinct employees == 2", gap_emps == 2, f"got {gap_emps}")

# COMMAND ----------

# MAGIC %md ## AP1 hero invariants

# COMMAND ----------

from pyspark.sql import functions as F  # noqa: E402

email = tbl("bronze_email_events")
proxy = tbl("bronze_proxy_logs")
auth = tbl("bronze_auth_logs")

# 17 distinct clickers on the hero subject.
clickers = (email.filter((email.subject == config.AP1_EMAIL_SUBJECT)
                         & (email.action == "clicked"))
            .select("employee_id").distinct().count())
check("AP1 distinct clickers == 17", clickers == config.AP1_CLICKERS, f"got {clickers}")

# 3 credential POSTs to the hero.
posts = (proxy.filter((proxy.domain == config.HERO_DOMAIN) & (proxy.method == "POST"))
         .select("employee_id").distinct().count())
check("AP1 credential POSTs == 3", posts == config.AP1_CREDENTIAL_SUBMITTERS, f"got {posts}")

# Priya RO success.
priya_ro = auth.filter((auth.employee_id == "E0001") & (auth.result == "success")
                       & (auth.country == "RO")).count()
check("AP1 Priya RO success present", priya_ro == 1, f"got {priya_ro}")

# Priya is privileged.
emp = tbl("ref_employees")
priya_priv = emp.filter((emp.employee_id == "E0001") & (emp.is_privileged)).count()
check("Priya is privileged", priya_priv == 1)

# Failed-login bursts: 3 submitters each with >=5 failures.
submitter_ids = [r["employee_id"] for r in
                 proxy.filter((proxy.domain == config.HERO_DOMAIN) & (proxy.method == "POST"))
                 .select("employee_id").distinct().collect()]
bursts_ok = 0
for emp_id in submitter_ids:
    n_fail = auth.filter((auth.employee_id == emp_id) & (auth.result == "failure")).count()
    if config.AP1_FAILED_LOGIN_MIN <= n_fail <= config.AP1_FAILED_LOGIN_MAX + 3:
        bursts_ok += 1
check("AP1 failed-login bursts for all 3 submitters", bursts_ok == 3, f"got {bursts_ok}")

# COMMAND ----------

# MAGIC %md ## AP2 / AP4 / AP5 and counterexamples

# COMMAND ----------

# AP2 BEC: POST by E0002, RO success.
ap2_post = (proxy.filter((proxy.domain == "tesco-supplier-billing.com")
                        & (proxy.method == "POST"))
            .select("employee_id").distinct().collect())
check("AP2 POST by Mark only", {r["employee_id"] for r in ap2_post} == {"E0002"})
ap2_ro = auth.filter((auth.employee_id == "E0002") & (auth.country == "RO")
                     & (auth.result == "success")).count()
check("AP2 RO success present", ap2_ro == 1)

# AP4: 4 distinct DNS users on tescobank-secure-auth.
ap4 = (dns.filter(dns.query_domain == "tescobank-secure-auth.com")
       .select("employee_id").distinct().count())
check("AP4 distinct DNS users == 4", ap4 == 4, f"got {ap4}")

# AP5: Sophie 9 visits.
ap5 = proxy.filter((proxy.domain == "tesco-rewards-login.com")
                   & (proxy.employee_id == "E0003")).count()
check("AP5 Sophie visits == 9", ap5 == config.AP5_VISITS, f"got {ap5}")

# Counterexamples.
cv = dns.filter(dns.query_domain == "tesco-careers-verify.com").count()
check("careers-verify 1 DNS hit", cv == config.CAREERS_VERIFY_DNS_HITS, f"got {cv}")
ff = (proxy.filter(proxy.domain == config.DECOY_DOMAIN)
      .select("employee_id").distinct().count())
check("fans-forum 3 distinct visitors", ff == config.FANS_FORUM_VISITS, f"got {ff}")

# Noise IOCs: zero internal hits.
noise_domains = {r["indicator_value"] for r in
                 tbl("structured_iocs")
                 .filter((F.col("campaign_id") == "N") & (F.col("indicator_type") == "domain"))
                 .select("indicator_value").collect()}
dns_domains = {r["query_domain"] for r in dns.select("query_domain").distinct().collect()}
check("noise IOCs have zero DNS hits", noise_domains.isdisjoint(dns_domains))

# COMMAND ----------

# MAGIC %md ## Ground-truth rank order and filler routing

# COMMAND ----------

# Expected findings: hero is #1.
gef = tbl("gt_expected_findings").orderBy("rank").collect()
check("expected finding rank 1 is hero",
      gef[0]["domain"] == config.HERO_DOMAIN and gef[0]["rank"] == 1)

# Filler routing: every pool row routes to its expected lane.
from datagen.filler import route_filler  # noqa: E402
filler_rows = tbl("filler_pool").collect()
mis = 0
for row in filler_rows:
    d = row.asDict()
    if route_filler(d) != d["expected_route"]:
        mis += 1
check("every filler routes to expected lane", mis == 0, f"{mis} mismatches")

# Feed overlap present.
check("feed overlap set non-empty", count("gt_feed_overlap") > 0)

# COMMAND ----------

# MAGIC %md ## Result

# COMMAND ----------

print(f"\n{'=' * 60}")
print(f"VALIDATION: {len(_FAILURES)} failures, {len(_WARNINGS)} warnings")
print(f"{'=' * 60}")
for f in _FAILURES:
    print(f)
for w in _WARNINGS:
    print(w)

if _FAILURES:
    raise AssertionError(f"{len(_FAILURES)} validation failures block the demo")
print("\nALL HARD CHECKS PASSED. Demo data is safe.")
