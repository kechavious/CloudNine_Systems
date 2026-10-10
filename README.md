# Group 4 - CloudNine Systems

Milestone 1 design package for a database-driven cloud infrastructure information system.

Repository URL: https://github.com/kechavious/CloudNine_Systems

## Milestone 1 deliverables

1. [3NF ERD (PDF)](output/pdf/Group4_ERD.pdf) - 50 tables, with seven detailed module diagrams, keys, nullability and relationship multiplicities.
2. [Draft analysis report (PDF)](output/pdf/Group4_Analysis_Draft.pdf) - scenario, schema, assumptions, normalization rationale, integrity rules and limitations.
3. [Team statement (PDF)](output/pdf/Group4_Team_Statement.pdf) - proposed equitable work packages, accountability, peer review, support and workload rebalancing.

The ERD is a logical design. Database implementation, data exports, queries and the web interface are subsequent work.

## Editable sources

- [Analysis draft](docs/milestone1/Group4_Analysis_Draft.md)
- [Team statement](docs/milestone1/Group4_Team_Statement.md)
- [Mermaid ERD](docs/milestone1/Group4_ERD.mmd)
- [Canonical schema JSON](docs/milestone1/Group4_Schema.json)
- [Data dictionary](docs/milestone1/Group4_Data_Dictionary.md)
- [Document generation script](scripts/build_milestone1.py)

## Before submitting the repository URL

- Replace provisional Member A-D slots with the actual roster, GitHub usernames, owners and reviewers. Four work packages do not establish the actual group size.
- Confirm the team's agreement, communication schedule, course deadline and internal review date.
- Confirm every member has collaborator access and the instructor can open the repository.
- Review the proposed assumptions and the 50-table scope together. The team statement is a proposed plan until members confirm it.

These confirmations require the team's input; they have not been represented as completed.

## Source and prior design

The scenario comes from [CloudNine Systems](Group%20Project_%20CloudNine%20Systems.pdf); general project requirements come from [the course project handout](Group%20Project%20-%20DB.pdf).

Earlier files `docs/CloudNine_Complete_ERD.md`, `docs/CloudNine_Complete_ERD.mmd`, and `docs/CloudNine_ERD_Modules.md` are preserved as the original 42-table proposal. They are superseded by the Milestone 1 package above and should not be used as its schema source.

## Regeneration

The generator requires Python with reportlab, svglib and pypdfium2 for PDF verification, plus Node.js and @viz-js/viz for Graphviz rendering. Its bundled-runtime paths reflect the authoring environment and may need adjustment on another computer. Run `python scripts/build_milestone1.py` from this repository after installing or locating those dependencies. The generator contains the report and team-statement source text; update that text as well when changing the editable Markdown so regeneration preserves revisions.
