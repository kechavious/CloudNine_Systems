# Group 4 - CloudNine Systems

A 20-table database design for a cloud infrastructure information system, organized around a practical two-page Operations and Billing website. This repository currently contains the Milestone 1 design and implementation plan; the database, sample data, SQL queries and website are later work.

## Current documents

- [ERD PDF](output/pdf/Group4_ERD.pdf): four domain diagrams, five owned tables each; complete attributes, PK/FK markers, named relationships and cardinalities.
- [Draft analysis PDF](output/pdf/Group4_Analysis_Draft.pdf): scope, simplifications, 3NF reasoning, integrity rules and scenario coverage.
- [Team statement PDF](output/pdf/Group4_Team_Statement.pdf): five tables per member, query/page responsibilities and review duties.
- [Website and query plan](docs/milestone1/Group4_Website_Plan.md): two pages, eight meaningful queries, data requirements and build sequence.

Repository URL for submission: https://github.com/kechavious/CloudNine_Systems

## What the website will demonstrate

**Operations:** capacity by region/zone/data center, utilization by resource type, reservation shortages, downtime and resource substitutions.

**Billing:** estimated versus actual consumption, client charges and credits, payer splits and invoice totals.

Location tables support filters, joins and capacity comparisons; they do not require separate website pages. Data is synthetic. The demonstration does not need real servers, provisioning, live monitoring, authentication or twenty CRUD screens.

## Twenty-table core and ownership

| Owner | Five tables | Main implementation responsibility | Reviewed by |
|---|---|---|---|
| A | client, user_account, reservation, reservation_item, billing_account | Clients, requests, payer contacts; Q3 and reservation sections | B |
| B | region, availability_zone, data_center, resource_type, resource | Infrastructure; Q1-Q2 and Operations location/capacity sections | C |
| C | deployment, resource_allocation, resource_state, deployment_service, usage_record | Assignment, availability and metering; Q4-Q5 and Q6 with D | D |
| D | service, service_rate, charge, charge_share, invoice | Rates, charges, draft invoices and splits; Q7-Q8, Q6 display, Billing page | A |

Table counts are balanced, and documentation/integration tasks offset the heavier temporal and billing logic. A assembles the report, B integrates the schema/shared layout, C coordinates generated documents, and D coordinates submission checks. Names and member acceptance are pending.

## Simplification decisions

The previous 23-table version is reduced to 20:

- Remove `project`: group named deployments by client and reservation.
- Remove `client_membership`: a user has at most one current client through `user_account.clientId`; many-to-many affiliation and affiliation history are outside scope.
- Remove `invoice_line`: `charge_share` itself is the invoice line and references `invoice`; derive its payer from the invoice instead of duplicating billingAccountId. Create a draft invoice before allocating shares.

Keep `region`, `availability_zone` and `data_center`: the scenario distinguishes these locations, reservation restrictions can target them, and the website compares their capacity. Keep allocation/state/rate/usage history because it supports meaningful queries. Detailed tradeoffs and deferred scenario features are in analysis sections 3-5.

The 20-table count meets the assignment's table threshold for A-level consideration; it does not guarantee a grade. Normalization, realistic activity, correct queries, interpretation and the final interface still matter.

## Editable sources and diagrams

- [Analysis source](docs/milestone1/Group4_Analysis_Draft.md)
- [Team statement source](docs/milestone1/Group4_Team_Statement.md)
- [Four-domain overview](output/svg/Group4_ERD_Overview.svg)
- Individual SVG diagrams: [A](output/svg/Group4_ERD_A.svg), [B](output/svg/Group4_ERD_B.svg), [C](output/svg/Group4_ERD_C.svg), [D](output/svg/Group4_ERD_D.svg)
- [Domain views and editable Mermaid](docs/milestone1/Group4_ERD_Views.md)
- [Full Mermaid source](docs/milestone1/Group4_ERD.mmd)
- [Field inventory](docs/milestone1/Group4_ERD_Fields.csv)
- [Generator and canonical table definitions](scripts/build_milestone1.py)

The diagrams follow the supplied Assignment 3 example's restrained table-and-relationship layout: singular lower_case table names, camelCase attributes, headings and clear PK/FK markers. Additional uniqueness rules belong in analysis R9. Shaded reference boxes repeat existing entities rather than adding tables. GitHub views and the PDF use the same SVGs; the overview combines those four diagrams.

## Regeneration and checks

Run `python scripts/build_milestone1.py` with reportlab and svglib installed. Graphviz rendering uses Node.js and @viz-js/viz; the bundled runtime paths in the generator may need adjustment on another computer. Edit the generator for schema changes and Markdown sources for document text. All three PDFs, four diagram SVGs, the overview, Mermaid sources and CSV are regenerated together. PDF output is deterministic for unchanged source. Temporary renders are ignored by Git.

## Milestones and remaining work

Milestone 1: ERD PDF, draft analysis and clear team planning. Later milestones: all 20 tables, meaningful synthetic activity over at least one quarter, eight aggregate/join queries, two read-only pages, database export, complete source and presentation. The [website plan](docs/milestone1/Group4_Website_Plan.md) specifies responsibilities and verification rules.

Before submission, add member names/GitHub accounts, obtain acceptance of assignments, confirm shared access and ensure the instructor can open the repository. Course deadline, meeting times and member acknowledgment remain pending; they are not claimed as completed.

The original [project requirements](Group%20Project%20-%20DB.pdf) and [CloudNine scenario](Group%20Project_%20CloudNine%20Systems.pdf) are retained unchanged. Earlier designs remain in Git history.
