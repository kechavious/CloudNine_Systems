# Group 4 - CloudNine Systems

Milestone 1: a proposed 23-table, 3NF logical design for a cloud infrastructure information system.

## Submission documents

1. [ERD PDF](output/pdf/Group4_ERD.pdf): a core workflow overview and six detailed module diagrams with attributes, keys, nullability and relationship multiplicities.
2. [Draft analysis report](output/pdf/Group4_Analysis_Draft.pdf): scenario, organizational schema, design decisions, assumptions, 3NF rationale and scope limitations.
3. [Team statement](output/pdf/Group4_Team_Statement.pdf): proposed four-person division of work, accountability, support and workload balancing.

Submit this repository URL: https://github.com/kechavious/CloudNine_Systems

## Core scope

The model keeps requests, resource allocations, usage, direct cost sharing and invoices. Reservation revisions, resource dependency/configuration-history tables, deployment event logs and automatic sharing rules have been removed. The analysis report explains these tradeoffs. This version supersedes earlier designs, which remain available in Git history.

## Before submission

Replace member placeholders and confirm work owners, reviewers and the team plan. Ensure all four members have repository access and the instructor can open the URL. Review the final PDFs together. Pending confirmations are not represented as completed.

## Editable sources

- [Analysis report](docs/milestone1/Group4_Analysis_Draft.md)
- [Team statement](docs/milestone1/Group4_Team_Statement.md)
- [Mermaid ERD](docs/milestone1/Group4_ERD.mmd)
- [PDF and ERD generator](scripts/build_milestone1.py): canonical table definitions are maintained here.

The course [project requirements](Group%20Project%20-%20DB.pdf) and [CloudNine scenario](Group%20Project_%20CloudNine%20Systems.pdf) are retained as references. Database implementation, exports, queries and the web interface belong to later milestones.

## Regenerate

Run `python scripts/build_milestone1.py` with reportlab and svglib installed. Graphviz rendering uses Node.js and @viz-js/viz; the bundled runtime paths in the script may need adjustment on another computer. Edit the Markdown files for report text, and the generator for schema changes. Temporary render files are ignored by Git.
