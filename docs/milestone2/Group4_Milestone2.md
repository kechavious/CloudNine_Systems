# Group 4 · CloudNine Systems · Milestone 2

CloudNine rents shared compute, block storage and network capacity. The database connects customer reservations to infrastructure allocations, usage, charges and payer invoices. Operations helps staff track fulfillment and outages. Billing helps staff compare measured usage with estimates and reconcile invoice shares.

## Submission files

| Deliverable | Files |
| --- | --- |
| Database definition and population | [DDL](../../sql/milestone2/01_schema.sql) and [DML](../../sql/milestone2/02_seed.sql) |
| Proposed and executed queries | [Q1–Q9 SQL](../../sql/milestone2/03_queries.sql) and [query outputs with interpretation](Group4_Query_Evidence.md) |
| Initial populated export | [Group4_Initial_Export.sql](../../output/db/Group4_Initial_Export.sql) |
| Web interface wireframe | [Group4_Wireframe.html](Group4_Wireframe.html). Open this file in a browser and select Operations or Billing. |
| Verification and regeneration | [Integrity SQL](../../sql/milestone2/04_validate.sql) and [build script](../../scripts/build_milestone2.py) |
| Design reference | [Milestone 1 ERD](../../output/pdf/Group4_ERD.pdf), [analysis and business rules](../milestone1/Group4_Analysis_Draft.md) and [team responsibilities](../milestone1/Group4_Team_Statement.md) |

## Schema and normalization

The implementation retains all 20 entities and their ERD column names. Use SQLite 3.38 or newer and enable foreign keys on each connection. Dates use UTC text in sortable ISO format. All effective intervals are half-open. For example, an allocation whose end timestamp matches the snapshot has already ended.

Each attribute describes its table's key or another candidate key. Composite natural identifiers distinguish a zone within its region, a data center within its zone and an asset within its data center. Names of parent locations are sourced by joining those relationships. Resource capacity is a fact about a particular asset. Allocation fraction, timing and reason are facts about a particular assignment. Service billing units belong to the service, while prices belong to individual effective rate rows. Usage measurements reference a deployment service and can point to a superseded measurement. A charge stores the posted monetary fact so invoice and adjustment history remains reproducible. The invoice identifies the paying account, and the reservation identifies the consuming client. Each share stores one amount for a particular invoice and charge pair. Invoice totals are computed from those amounts.

Two physical choices clarify the implementation:

- `invoice.issuedAt` is nullable while the invoice is a draft and required on issuance. The DML creates a draft, inserts its shares and then updates eligible invoices to issued.
- `unitPrice`, `amount` and `allocatedAmount` store integer USD cents. SQL formats monetary outputs in USD. The fixture uses prices in whole cents per billing unit.

Keys, local constraints and issuance triggers run in the database. Triggers block changes to issued invoices, posted charges and shares of charges linked to an issued invoice. Issuance requires a nonempty invoice whose charges are posted and fully allocated. Cross-table audit rules such as time windows, resource capacity and valid rate selection are checked by `04_validate.sql` during the build. The wireframe displays recorded results for fixed filters. Production workflows such as authorization, live provisioning, invoice settlement and automatic correction are outside this milestone's scope.

## Data design

The synthetic activity runs from May through October 2026. The dataset covers three regions, six zones, nine data centers, 108 assets, 24 clients and three billing units. Bookings follow recurring deployment windows with distinct workloads and varying demand. Some deployments share an asset at the same time. Compute and network rates change on August 1. Missing estimates and a pending actual measurement test incomplete input. The seed includes parent organizations with team clients and a sponsor that pays part of selected invoices.

The Atlas Labs scenario can be followed across the two pages:

1. On September 10 at noon UTC, the two-instance Ashburn reservation has one eligible assignment. Q3 reports one shortfall.
2. At midnight UTC on September 11, CMP-04 takes over from CMP-01 and the shortfall clears. Q4 measures outage time and Q5 identifies the original and replacement resources.
3. For the September 11 compute period, estimated usage was 100 vCPU-hours. A corrected measurement supersedes the earlier actual and records 120. The effective rate of $0.50 produces charge 3606 for $60.00.
4. Atlas Labs and Northstar Research Foundation pay $36.00 and $24.00 respectively. The $6.00 service credit follows the same split. Q7 attributes the credit to Atlas Labs as the consumer, while the payer detail shows each invoice share.

Q9 also demonstrates two October exceptions that have yet to be fully assigned to draft invoices. They are included intentionally. The integrity audit checks issued invoices separately and returns zero violations.

## Restore and run

From the repository root, use a fresh local database file. SQLite CLI dot commands are shown below.

```sh
mkdir -p tmp
sqlite3 -bail tmp/cloudnine_m2.db <<'SQL'
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

## Repository submission

The [course project brief](../../Group%20Project%20-%20DB.pdf) lists GitHub as the group destination for project deliverables. Put the Milestone 2 SQL, export, wireframe, results and source in the group repository. Share the GitHub commit or milestone folder link through the course submission page according to the instructor's directions. The brief references Assignment 5 for the database export format. This package uses a restorable SQLite SQL export. Check the course submission page for any additional file type or upload requirement.
