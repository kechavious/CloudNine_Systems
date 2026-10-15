# Group 4 - CloudNine Systems

Milestone 1: a proposed 23-table, 3NF logical design for a cloud infrastructure information system.

## Submission documents

1. [ERD PDF](output/pdf/Group4_ERD.pdf): four domain diagrams covering all 23 tables in an assignment-style table-and-relationship layout. Every attribute and foreign key is shown, with labelled relationships and explicit cardinalities. Only PK/FK markers appear; uniqueness rules are documented in analysis R9.
2. [Draft analysis report](output/pdf/Group4_Analysis_Draft.pdf): scenario, organizational schema, design decisions, assumptions, 3NF rationale and scope limitations.
3. [Team statement](output/pdf/Group4_Team_Statement.pdf): proposed four-person division of work, accountability, support and workload balancing.

Submit this repository URL: https://github.com/kechavious/CloudNine_Systems

## Milestone 1 requirements

| Assignment requirement | Location |
|---|---|
| ERD as a PDF, normalized to 3NF | ERD PDF; normalization reasoning and integrity assumptions in analysis sections 3-4 |
| Draft analysis of the scenario, organizational schema and assumptions | Analysis report sections 1-5 |
| Team understanding, equitable division, accountability and mutual support | Team Statement; member confirmation is pending |
| GitHub repository shared by all team members | This repository; all four members must confirm access before submission |

This submission is design-only. Database implementation, sample data, queries and web pages are planned for later milestones. The PDF generator is a documentation tool, not an implemented cloud management application. The team statement is a proposed plan until the members confirm it.

## Core scope

The model keeps requests, resource allocations, usage, direct cost sharing and invoices. Reservation revisions, resource dependency/configuration-history tables, deployment event logs and automatic sharing rules have been removed. The analysis report explains these tradeoffs. This version supersedes earlier designs, which remain available in Git history.

## ERD work packages

| Owner | Tables | Primary area | Reviewed by |
|---|---:|---|---|
| Member A | 6 | Clients and reservations | Member B |
| Member B | 6 | Infrastructure and availability | Member C |
| Member C | 5 | Deployments and services | Member D |
| Member D | 6 | Metering and billing | Member A |

A-D work packages match the PDF and [ownership diagrams](docs/milestone1/Group4_ERD_Views.md). Each diagram uses consistent table boxes with separate key, attribute and type columns. Names will be supplied later; each member must acknowledge their assignment.

## Before submission

Add English names and map the four members to the assigned A-D work packages. Owners, review duties and document responsibilities are specified in the Team Statement; obtain member acknowledgment of the plan. Ensure all four members have repository access and the instructor can open the URL. Review the final PDFs together. Pending confirmations are not represented as completed.

## Editable sources

- [Analysis report](docs/milestone1/Group4_Analysis_Draft.md)
- [Team statement](docs/milestone1/Group4_Team_Statement.md)
- [Four-domain overview](output/svg/Group4_ERD_Overview.svg)
- Individual diagrams: [A](output/svg/Group4_ERD_A.svg), [B](output/svg/Group4_ERD_B.svg), [C](output/svg/Group4_ERD_C.svg), [D](output/svg/Group4_ERD_D.svg)
- [Four ERD ownership views](docs/milestone1/Group4_ERD_Views.md): the same SVG diagrams used by the PDF, with editable Mermaid sources.
- [Full Mermaid ERD](docs/milestone1/Group4_ERD.mmd)
- [PDF and ERD generator](scripts/build_milestone1.py): canonical table definitions are maintained here.

The course [project requirements](Group%20Project%20-%20DB.pdf) and [CloudNine scenario](Group%20Project_%20CloudNine%20Systems.pdf) are retained as references. Database implementation, exports, queries and the web interface belong to later milestones.

## Regenerate

Run `python scripts/build_milestone1.py` with reportlab and svglib installed. Graphviz rendering uses Node.js and @viz-js/viz; the bundled runtime paths in the script may need adjustment on another computer. Edit the Markdown files for report text, and the generator for schema changes. Temporary render files are ignored by Git.

## Assignment 3 formatting reference

The supplied Assignment 3 requirements and GChau example guide presentation: singular lower_case table names, camelCase attributes, clear headings, PK/FK markers, labelled relationships, cardinalities and documented assumptions. CloudNine remains the project domain; the travel and DVD exercises are not additional project requirements. Unique business identifiers are described in analysis R9; the diagrams display only PK/FK markers.

The PDF contains four domain diagrams with complete attributes and labelled relationship cardinalities. It follows the supplied reference's simple table boxes and restrained black-and-white styling. Gray boxes repeat external entities by primary key; they do not represent additional tables.

- [Field inventory CSV](docs/milestone1/Group4_ERD_Fields.csv)

## Version consistency

All three PDFs, four SVG diagrams, the combined overview, Mermaid sources and the field inventory are generated together. The overview reuses the four final domain diagrams. The reports and team work packages use the same 23 table names and 42 foreign-key relationships. Course reference PDFs are retained unchanged. Member names, access and acknowledgment remain pending until the team supplies them.
