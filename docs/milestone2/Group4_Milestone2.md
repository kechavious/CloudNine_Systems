# Group 4 · CloudNine Systems · Milestone 2

CloudNine rents shared compute, block storage and network capacity. The database connects customer reservations to infrastructure allocations, usage, charges and payer invoices. Operations helps staff track fulfillment and outages. Billing helps staff compare measured usage with estimates and reconcile invoice shares.

## Submission files

| Assignment requirement | Submitted evidence |
| --- | --- |
| Database implementation and 3NF | [DDL](../../sql/milestone2/01_schema.sql) defines the 20 tables. [DML](../../sql/milestone2/02_seed.sql) loads 24,459 rows spanning May through October 2026. See [Schema and normalization](#schema-and-normalization) for the design rationale. |
| Proposed queries and interpretation | [Q1–Q9 SQL](../../sql/milestone2/03_queries.sql) and [executed results with interpretation](Group4_Query_Evidence.md). |
| Initial database export | [Populated SQLite SQL dump](../../output/db/Group4_Initial_Export.sql). The submission ZIP in the repository README also includes the populated `.sqlite3` file. |
| Web interface wireframe | [Download the interactive HTML](Group4_Wireframe.html) and open it locally in a browser. The [PDF report](../../output/pdf/Group4_Milestone2.pdf) includes screenshots of both views on pages 4–5. |

## Queries in the wireframe

| View | What the recorded query results show |
| --- | --- |
| Operations | Q1 compares available capacity by site. Q2 compares allocation ratios by region and resource. Q3 identifies reservation shortfalls. Q4 measures failure and maintenance hours. Q5 traces replacement equipment. |
| Billing | Q6 compares usage with estimates. Q7 summarizes fees and credits. Q8 shows invoice totals and split payments. Q9 flags charges that need reconciliation. |

The mockup uses fixed query results from the initial export. The two views cross-link the Atlas Labs case so a reviewer can follow the resource replacement and the related invoice split.

## Schema and normalization

The implementation retains all 20 entities and their ERD column names. Use SQLite 3.38 or newer and enable foreign keys on each connection. Dates use UTC text in sortable ISO format. All effective intervals are half-open. For example, an allocation whose end timestamp matches the snapshot has already ended.

Each attribute describes its table's key or another candidate key. Composite natural identifiers distinguish a zone within its region, a data center within its zone and an asset within its data center. Names of parent locations are sourced by joining those relationships. Resource capacity is a fact about a particular asset. Allocation fraction, timing and reason are facts about a particular assignment. Service billing units belong to the service, while prices belong to individual effective rate rows. Usage measurements reference a deployment service and can point to a superseded measurement. A charge stores the posted monetary fact so invoice and adjustment history remains reproducible. The invoice identifies the paying account, and the reservation identifies the consuming client. Each share stores one amount for a particular invoice and charge pair. Invoice totals are computed from those amounts.

Two physical choices clarify the implementation:

- `invoice.issuedAt` is nullable while the invoice is a draft and required on issuance. The DML creates a draft, inserts its shares and then updates eligible invoices to issued.
- `unitPrice`, `amount` and `allocatedAmount` store integer USD cents. SQL formats monetary outputs in USD. The fixture uses prices in whole cents per billing unit.

Keys, local constraints and issuance triggers run in the database. Triggers block changes to issued invoices, posted charges and shares of charges linked to an issued invoice. Issuance requires a nonempty invoice whose charges are posted and fully allocated. Cross-table audit rules such as time windows, resource capacity and valid rate selection are checked by [the integrity audit](../../sql/milestone2/04_validate.sql) during the build.

## Data design

The synthetic activity runs from May through October 2026. The dataset covers three regions, six zones, nine data centers, 108 assets, 24 clients and three billing units. Bookings follow recurring deployment windows with distinct workloads and varying demand. Some deployments share an asset at the same time. Compute and network rates change on August 1. Missing estimates and a pending actual measurement test incomplete input. The seed includes parent organizations with team clients and a sponsor that pays part of selected invoices.

The Atlas Labs scenario can be followed across the two pages:

1. On September 10 at noon UTC, the two-instance Ashburn reservation has one eligible assignment. Q3 reports one shortfall.
2. At midnight UTC on September 11, CMP-04 takes over from CMP-01 and the shortfall clears. Q4 measures outage time and Q5 identifies the original and replacement resources.
3. For the September 11 compute period, estimated usage was 100 vCPU-hours. A corrected measurement supersedes the earlier actual and records 120. The effective rate of $0.50 produces charge 3606 for $60.00.
4. Atlas Labs and Northstar Research Foundation pay $36.00 and $24.00 respectively. The $6.00 service credit follows the same split. Q7 attributes the credit to Atlas Labs as the consumer, while the payer detail shows each invoice share.

Q9 also demonstrates two October exceptions that have yet to be fully assigned to draft invoices. They are included intentionally. The integrity audit checks issued invoices separately and returns zero violations.

## Restore and run

From the repository root, run the following to restore the export into a fresh in-memory database, validate it, and execute Q1–Q9.

```sh
sqlite3 -bail :memory: <<'SQL'
.read output/db/Group4_Initial_Export.sql
PRAGMA foreign_key_check;
PRAGMA integrity_check;
.read sql/milestone2/04_validate.sql
.headers on
.mode column
.parameter init
.parameter set :as_of "'2026-09-10 12:00:00'"
.parameter set :from_utc "'2026-05-01 00:00:00'"
.parameter set :to_utc "'2026-11-01 00:00:00'"
.read sql/milestone2/03_queries.sql
SQL
```

The foreign key and business checks return zero rows. The database integrity check prints `ok`. For a schema-and-seed build on an empty database, apply `01_schema.sql` then `02_seed.sql`. For a full reproducibility check, run `python3 scripts/build_milestone2.py` using Python 3.10+ with SQLite 3.38+. The script regenerates the seed, export, evidence and wireframe. It verifies restore equivalence for all nine query results, checks the outage boundary and date clipping, tests missing and corrected measurements, and confirms incomplete invoices are blocked and immutable records reject edits. Q1–Q3 use the snapshot. Q4–Q7 and Q9 use the activity range. Q8 reports all invoices in the initial export.

## Design and build references

- [Milestone 1 ERD](../../output/pdf/Group4_ERD.pdf)
- [Analysis and business rules](../milestone1/Group4_Analysis_Draft.md)
- [Team responsibilities](../milestone1/Group4_Team_Statement.md)
- [Reproducible build script](../../scripts/build_milestone2.py)
