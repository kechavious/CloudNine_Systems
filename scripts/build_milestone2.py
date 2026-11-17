"""Build the initial SQLite export, query evidence, and HTML wireframe."""
from collections import Counter, defaultdict
import csv
from html import escape
from pathlib import Path
import re
import sqlite3

from seed_milestone2 import ATLAS, main as seed_main

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql/milestone2"
DOCS = ROOT / "docs/milestone2"
EXPORT = ROOT / "output/db/Group4_Initial_Export.sql"
PARAMS = {
    "as_of": "2026-09-10 12:00:00",
    "from_utc": "2026-05-01 00:00:00",
    "to_utc": "2026-11-01 00:00:00",
}
RECOVERY = "2026-09-11 00:00:00"

FOCAL_USAGE = """
SELECT c.chargeId AS charge_id, e.quantity AS estimate, u.quantity AS actual,
       s.billingUnit AS unit, rate.unitPrice AS rate_cents, c.amount AS charge_cents
FROM deployment d
JOIN deployment_service ds USING (deploymentId)
JOIN service s USING (serviceId)
JOIN usage_record u USING (deploymentServiceId)
JOIN usage_record e ON e.deploymentServiceId = u.deploymentServiceId
    AND e.allocationId = u.allocationId AND e.periodStart = u.periodStart
    AND e.periodEnd = u.periodEnd AND e.recordType = 'estimate'
JOIN charge c ON c.usageId = u.usageId
JOIN service_rate rate USING (serviceRateId)
WHERE d.name = ? AND u.recordType = 'actual' AND s.name = 'Compute'
  AND u.periodStart = '2026-09-11 00:00:00'
  AND NOT EXISTS (SELECT 1 FROM usage_record n WHERE n.supersedesUsageId = u.usageId)
  AND NOT EXISTS (SELECT 1 FROM usage_record n WHERE n.supersedesUsageId = e.usageId);
"""

FOCAL_SHARES = """
SELECT c.chargeType AS charge_type, c.chargeId AS charge_id, consuming.name AS consumer,
       payer.name AS payer_account, i.invoiceId AS invoice_id, i.status,
       cs.allocatedAmount / 100.0 AS share_usd
FROM charge_share cs
JOIN charge c USING (chargeId)
JOIN invoice i USING (invoiceId)
JOIN billing_account payer USING (billingAccountId)
JOIN charge root ON root.chargeId = coalesce(c.adjustmentOfChargeId, c.chargeId)
JOIN usage_record u ON u.usageId = root.usageId
JOIN deployment_service ds ON ds.deploymentServiceId = u.deploymentServiceId
JOIN deployment d USING (deploymentId)
JOIN reservation r USING (reservationId)
JOIN client consuming USING (clientId)
WHERE root.chargeId = ?
ORDER BY c.chargeId, payer.name;
"""


def connection():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def queries():
    source = (SQL / "03_queries.sql").read_text()
    sections = re.split(r"^-- (Q\d+) \| (.+)\n", source, flags=re.M)
    return {
        sections[i]: (sections[i + 1], sections[i + 2].strip())
        for i in range(1, len(sections), 3)
    }


def query_all(db, statements, **filters):
    return {
        key: db.execute(sql, PARAMS | filters).fetchall()
        for key, (_, sql) in statements.items()
    }


def validate(db):
    check = (SQL / "04_validate.sql").read_text()
    violations = [tuple(row) for row in db.execute(check)]
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if violations or integrity != "ok":
        raise ValueError(f"Integrity check: {integrity}, business checks: {violations}")


def table_counts(db):
    with (ROOT / "docs/milestone1/Group4_ERD_Fields.csv").open(newline="") as source:
        expected = defaultdict(list)
        for row in csv.DictReader(source):
            expected[row["table"]].append(row["attribute"])
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name")]
    assert set(tables) == set(expected), tables
    for name in tables:
        columns = [row["name"] for row in db.execute(f'PRAGMA table_info("{name}")')]
        assert columns == expected[name], (name, columns)
    return {name: db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}


def reject(db, message, sql, *args):
    try:
        db.execute(sql, args)
    except sqlite3.IntegrityError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected rejection: {message}")
    finally:
        db.rollback()


def check_scenarios(db, statements, results, focal, shares):
    during, = [row for row in results["Q3"] if row["client"] == "Atlas Labs"]
    assert (during["requested"], during["fulfilled"], during["shortfall"]) == (2, 1, 1)
    assert not db.execute(statements["Q3"][1], PARAMS | {"as_of": RECOVERY}).fetchall()
    assert (focal["estimate"], focal["actual"], focal["rate_cents"], focal["charge_cents"]) == (100, 120, 50, 6000)
    assert [row["share_usd"] for row in shares] == [36, 24, -3.6, -2.4]
    september_atlas = next(row for row in results["Q7"]
                           if row["posting_month"] == "2026-09" and row["consuming_client"] == "Atlas Labs"
                           and row["service"] == "Compute")
    assert september_atlas["credits_usd"] == -6
    assert all(row["credits_usd"] == 0 for row in results["Q7"] if row != september_atlas)
    assert sum(row["resource_hours"] for row in results["Q4"] if row["event"] == "failed") == 288
    assert sum(row["resource_hours"] for row in results["Q4"] if row["event"] == "maintenance") == 96
    assert len(results["Q5"]) == 12
    assert sum(row["missing_estimates"] for row in results["Q6"]) > 0
    assert sum(row["missing_actuals"] for row in results["Q6"]) == 1
    assert Counter(row["issue"] for row in results["Q9"]) == {"Unallocated": 1, "Underallocated": 1}
    assert all(row["issued_share_count"] == 0 for row in results["Q9"])
    clipped = db.execute(statements["Q4"][1], PARAMS | {
        "from_utc": "2026-09-10 12:00:00", "to_utc": RECOVERY
    }).fetchall()
    assert sum(row["resource_hours"] for row in clipped) == 12

    incomplete = results["Q9"][1]["charge_id"]
    invoice, allocated = db.execute(
        "SELECT invoiceId, allocatedAmount FROM charge_share WHERE chargeId = ?", (incomplete,),
    ).fetchone()
    reject(db, "fully allocated posted charges",
           "UPDATE invoice SET status = 'issued', issuedAt = '2026-11-02 00:00:00' WHERE invoiceId = ?", invoice)
    db.execute("UPDATE charge_share SET allocatedAmount = ? WHERE chargeId = ?", (allocated + 100, incomplete))
    db.execute("UPDATE invoice SET status = 'issued', issuedAt = '2026-11-02 00:00:00' WHERE invoiceId = ?", (invoice,))
    db.rollback()
    reject(db, "Issued invoice is immutable",
           "UPDATE invoice SET dueAt = '2026-11-01 00:00:00' WHERE invoiceId = ?", shares[0]["invoice_id"])
    reject(db, "Shares are frozen after any related invoice is issued",
           "UPDATE charge_share SET allocatedAmount = 0 WHERE chargeId = ?", focal["charge_id"])
    reject(db, "Correct posted charges with adjustments",
           "UPDATE charge SET amount = 0 WHERE chargeId = ?", focal["charge_id"])


def value(raw):
    if raw is None:
        return "—"
    if isinstance(raw, float):
        return f"{raw:,.2f}"
    return str(raw)


def markdown_table(rows, columns=None):
    columns = list(rows[0].keys()) if columns is None else columns
    body = ["| " + " | ".join(column.replace("_", " ") for column in columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |"]
    body.extend("| " + " | ".join(value(row[column]).replace("|", "\\|") for column in columns) + " |"
                for row in rows)
    return "\n".join(body)


def write_evidence(results, statements, counts, focal, shares):
    capacity = [row for row in results["Q1"] if row["data_center"] in ("Ashburn DC", "Newark DC")
                and row["resource_type"] == "Compute"]
    utilization = [row for row in results["Q2"] if row["resource_type"] == "Compute"]
    downtime = [row for row in results["Q4"] if row["month"] == "2026-09"]
    substitutions = [row for row in results["Q5"] if row["client"] == "Atlas Labs"]
    compute = [row for row in results["Q6"] if row["service"] == "Compute"]
    atlas = [row for row in results["Q7"] if row["consuming_client"] == "Atlas Labs"]
    atlas_invoices = [row for row in results["Q8"] if row["invoice_id"] in {s["invoice_id"] for s in shares}]
    ashburn, newark = capacity
    ratios = ", ".join(f'{r["region"]} {r["allocation_pct"]:.2f}%' for r in utilization)
    highest_variance = max(compute, key=lambda row: row["variance_pct"])
    sections = {
        "Q1": (capacity, ("data_center", "usable_assets", "usable_vcpu", "allocated_vcpu", "free_vcpu"),
               f'Newark had {newark["free_vcpu"]:.0f} free vCPUs versus {ashburn["free_vcpu"]:.0f} in Ashburn. '
               "A flexible workload could use Newark. A request restricted to Ashburn still needs eligible local capacity."),
        "Q2": (utilization, None,
               f"The regional compute ratios were {ratios}. An unavailable host reduces the usable denominator. "
               "The percentages measure reservations of asset capacity."),
        "Q3": (results["Q3"], None,
               "Atlas Labs was short one eligible compute asset at noon UTC on September 10. "
               "Rerunning Q3 at 2026-09-11 00:00:00 UTC returns zero shortages when the replacement starts."),
        "Q4": (downtime, ("month", "data_center", "event", "reason", "resource_hours"),
               "September lost 72 resource-hours to failures and 16 to planned maintenance. "
               "These are asset-hours summed across locations. The September 10 noon-to-midnight test counts 12 hours."),
        "Q5": (substitutions, None,
               "The Atlas deployment replaced Ashburn CMP-01 with CMP-04 at 00:00 UTC on September 11. "
               "Across the full period, 12 replacements were recorded."),
        "Q6": (compute, ("month", "unit", "paired_periods", "missing_estimates", "missing_actuals",
                         "paired_estimate", "paired_actual", "variance_pct"),
               f'Compute had its highest positive paired variance in {highest_variance["month"]} '
               f'({highest_variance["variance_pct"]:.2f}%). The focal September 11 reading was '
               f'{focal["estimate"]:.0f} estimated and {focal["actual"]:.0f} actual vCPU-hours after correction. '
               "Periods missing either value are counted separately from the paired comparison."),
        "Q7": (atlas, None,
               "All $6.00 in posted credits belong to Atlas Labs Compute in September. "
               "The sponsor's payment share does not change the consuming-client attribution."),
        "Q8": (atlas_invoices, None,
               "Both payer invoices include split charges. The $60.00 focal metered charge contributes $36.00 to "
               "Atlas Labs and $24.00 to the sponsor. The invoices also contain other shares, so their totals differ "
               "from this one split."),
        "Q9": (results["Q9"], None,
               "Two October charges need action before reconciliation: one has no share and one is short by $1.00. "
               "Neither appears on an issued invoice."),
    }
    lines = ["# Group 4 · Query evidence", "",
             "Source: Group4_Initial_Export.sql. Timestamps are UTC.",
             "Snapshot: 2026-09-10 12:00:00. Report period: May 1 through October 31, 2026.", "",
             "| Tables | Total rows | Reservations | Deployments | Usage records | Posted charges |",
             "| --- | --- | --- | --- | --- | --- |",
             f'| {len(counts)} | {sum(counts.values()):,} | {counts["reservation"]:,} | {counts["deployment"]:,} '
             f'| {counts["usage_record"]:,} | {counts["charge"]:,} |', ""]
    for key, (rows, columns, interpretation) in sections.items():
        question = statements[key][0]
        lines += [f"## {key} · {question}", "",
                  f'{len(results[key]):,} result rows. {"Selected rows below." if len(rows) < len(results[key]) else "Full result below."}', "",
                  markdown_table(rows, columns), "", interpretation, ""]
    lines += ["## Atlas Labs · Invoice line detail", "", markdown_table(shares), "",
              "The -$6.00 credit reuses the original 60/40 split. The two shares sum to -$6.00.", ""]
    (DOCS / "Group4_Query_Evidence.md").write_text("\n".join(lines), encoding="utf-8")


def html_table(rows, columns):
    head = "".join(f"<th scope='col'>{escape(label)}</th>" for _, label in columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(value(row[key]))}</td>" for key, _ in columns) + "</tr>"
                   for row in rows)
    return f"<div class='scroll' tabindex='0'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def stat(label, number, note):
    return f"<div class='stat'><span>{label}</span><strong>{number}</strong><small>{note}</small></div>"


def bars(rows, first, second, unit):
    maximum = max(a + b for _, a, b in rows)
    return "".join(
        f"<div class='bar-row'><span>{escape(label)}</span>"
        f"<div class='track' aria-hidden='true'><i style='width:{100 * a / maximum:.3f}%'></i>"
        f"<i style='width:{100 * b / maximum:.3f}%'></i></div>"
        f"<small aria-label='{a:g} {unit} {first}, {b:g} {unit} {second}'>{a:g} / {b:g}</small></div>"
        for label, a, b in rows
    )


def wireframe(results, focal, shares):
    compute_capacity = [r for r in results["Q1"] if r["resource_type"] == "Compute"]
    capacity_map = sorted(((r["data_center"], r["allocated_vcpu"], r["free_vcpu"])
                          for r in compute_capacity), key=lambda row: -row[2])
    downtime = defaultdict(Counter)
    for row in results["Q4"]:
        downtime[row["month"]][row["event"]] += row["resource_hours"]
    posting = defaultdict(Counter)
    for row in results["Q7"]:
        for key in ("fees_usd", "credits_usd", "net_usd"):
            posting[row["posting_month"]][key] += round(row[key] * 100)
    invoice_total = defaultdict(list)
    for row in results["Q8"]:
        invoice_total[row["status"]].append(row)
    compute_usage = [r for r in results["Q6"] if r["service"] == "Compute"]
    variance_scale = max((abs(r["variance_pct"]) for r in compute_usage if r["variance_pct"] is not None),
                         default=0) or 1
    variance_rows = []
    for row in compute_usage:
        percent = row["variance_pct"]
        if percent is None:
            bar, label = "", "—"
        else:
            direction = "below" if percent < 0 else "above"
            bar = f"<i class='{direction}' style='width:{50 * abs(percent) / variance_scale:.3f}%'></i>"
            label = f"{percent:+.2f}%"
        variance_rows.append(f"<div class='bar-row'><span>{escape(row['month'])}</span>"
                             f"<div class='track variance' aria-hidden='true'>{bar}</div><small>{label}</small></div>")
    replacements = [r for r in results["Q5"] if r["client"] == "Atlas Labs"]
    total_vcpu = sum(r["free_vcpu"] for r in compute_capacity)
    failure_hours = sum(month["failed"] for month in downtime.values())
    net = sum(month["net_usd"] for month in posting.values()) / 100
    credits = sum(month["credits_usd"] for month in posting.values()) / 100
    month_totals = [{"month": month, **{k: v / 100 for k, v in totals.items()}}
                    for month, totals in sorted(posting.items())]

    sections = {
        "OPS_STATS": "".join((
            stat("Free compute capacity", f"{total_vcpu:,.0f}", "vCPUs · 9 data centers"),
            stat("Unfulfilled reservation items", str(len(results["Q3"])), "At the selected snapshot"),
            stat("Failure impact", f"{failure_hours:,.0f} h", "Resource-hours · May–October"),
        )),
        "CAPACITY": bars(capacity_map, "allocated", "free", "vCPU"),
        "DOWNTIME": bars([(month, counts["failed"], counts["maintenance"]) for month, counts in downtime.items()],
                         "failure", "maintenance", "h"),
        "RATIOS": html_table(results["Q2"], (("region", "Region"), ("resource_type", "Resource"),
                                           ("usable_assets", "Usable assets"), ("unavailable_assets", "Unavailable"),
                                           ("allocation_pct", "Allocated (%)"))),
        "SHORTFALLS": html_table(results["Q3"], (("client", "Client"), ("requested_location", "Location"),
                                                ("resource_type", "Resource"), ("requested", "Requested"),
                                                ("fulfilled", "Fulfilled"), ("shortfall", "Shortfall"))),
        "REPLACEMENTS": html_table(replacements, (("deployment", "Deployment"), ("resource_pairs", "Replacement"),
                                                   ("first_replacement_utc", "Start (UTC)"), ("reason", "Cause"))),
        "BILL_STATS": "".join((
            stat("Posted net charges", f"${net:,.2f}", "USD · May–October"),
            stat("Posted credits", f"−${abs(credits):,.2f}", "USD · May–October"),
            stat("Charges to review", str(len(results["Q9"])), "Draft reconciliation queue"),
        )),
        "USAGE": html_table(compute_usage, (("month", "Month"), ("paired_estimate", "Estimated"),
                                           ("paired_actual", "Actual"), ("variance_pct", "Variance (%)"))),
        "VARIANCE": "".join(variance_rows),
        "POSTING": html_table(month_totals, (("month", "Month"), ("fees_usd", "Fees"),
                                            ("credits_usd", "Credits"), ("net_usd", "Net"))),
        "INVOICE_SUMMARY": " · ".join(
            f'{status.title()} ({len(rows)}): ${sum(r["invoice_total_usd"] for r in rows):,.2f}'
            for status, rows in sorted(invoice_total.items(), reverse=True)
        ),
        "FOCAL_TEXT": (f'11 September, Compute: {focal["estimate"]:.0f} vCPU-hours estimated, '
                       f'{focal["actual"]:.0f} actual · Charge #{focal["charge_id"]}, '
                       f'${focal["charge_cents"] / 100:,.2f} before credit.'),
        "SHARES": html_table(shares, (("charge_type", "Line type"), ("payer_account", "Payer account"),
                                     ("invoice_id", "Invoice"), ("status", "Status"), ("share_usd", "Share (USD)"))),
        "REVIEW": html_table(results["Q9"], (("charge_id", "Charge"), ("charge_usd", "Charge (USD)"),
                                           ("allocated_usd", "Allocated"), ("difference_usd", "Difference"),
                                           ("issue", "Issue"))),
    }
    template = (Path(__file__).with_name("milestone2_wireframe.html")).read_text(encoding="utf-8")
    page = re.sub(r"@@([A-Z_]+)@@", lambda match: sections[match.group(1)], template)
    (DOCS / "Group4_Wireframe.html").write_text(page, encoding="utf-8")


def main():
    if sqlite3.sqlite_version_info < (3, 38):
        raise SystemExit("SQLite 3.38 or newer is required.")
    DOCS.mkdir(parents=True, exist_ok=True)
    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    seed_main()
    source = connection()
    for file in ("01_schema.sql", "02_seed.sql"):
        source.executescript((SQL / file).read_text())
    counts = table_counts(source)
    validate(source)

    # Dump order can load children before parents. Validate foreign keys after restore.
    dump = ("-- Group 4 / CloudNine Systems / SQLite initial export\n"
            "PRAGMA foreign_keys = OFF;\n" + "\n".join(source.iterdump()) +
            "\nPRAGMA foreign_keys = ON;\n")
    restored = connection()
    restored.executescript(dump)
    assert restored.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert table_counts(restored) == counts
    validate(restored)
    statements = queries()
    assert len(statements) == 9
    results = query_all(restored, statements)
    assert query_all(source, statements) == results
    focal = restored.execute(FOCAL_USAGE, (ATLAS,)).fetchone()
    shares = restored.execute(FOCAL_SHARES, (focal["charge_id"],)).fetchall()
    check_scenarios(restored, statements, results, focal, shares)

    EXPORT.write_text(dump, encoding="utf-8")
    write_evidence(results, statements, counts, focal, shares)
    wireframe(results, focal, shares)
    print(f"Restored {len(counts)} tables and {sum(counts.values()):,} rows. Zero integrity violations.")
    print("Query rows:", ", ".join(f"{key}={len(rows)}" for key, rows in results.items()))
    print("Checked outage/recovery, interval clipping, correction/pricing, split shares and invoice issuance.")


if __name__ == "__main__":
    main()
