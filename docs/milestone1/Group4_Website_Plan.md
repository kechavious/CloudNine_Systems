# CloudNine - Website and query plan

Status: implementation plan, not a completed website. The core model contains 20 tables. The demonstration uses synthetic data and needs two read-only pages; it does not need twenty CRUD pages, login, live monitoring or real cloud provisioning.

## Page 1: Operations

Filters: selected UTC time, report date range, region, availability zone, data center and resource type. Show location capacity summaries, resource utilization, upcoming reservation shortages, deployments, downtime and substitutions. Links expand an existing table/detail section; a separate application for every entity is unnecessary.

`data_center` supplies a useful grouping: for example, compare available capacity at two facilities in the same region. Join `resource -> data_center -> availability_zone -> region` for labels and filters. Allocation and state records determine usable capacity at the selected time. Store several synthetic facilities so the comparison has meaning; no real infrastructure connection is needed.

## Page 2: Billing

Filters: consumption period, client, payer account, service and invoice status. Show estimated versus actual consumption, final charges and credits over time, and invoice totals by payer. Draft invoices receive monetary shares before issuance. The payer of a share comes from `charge_share -> invoice -> billing_account`; do not store it again on the share.

## Eight meaningful queries

| Query | Question and output | Main tables | Owner | Page |
|---|---|---|---|---|
| Q1 | At a selected time, how much usable and allocated capacity is available in each location? Group by region/zone/data center/type; show asset count and capacity dimensions separately. | region, availability_zone, data_center, resource_type, resource, resource_state, resource_allocation | B; C reviews time logic | Operations |
| Q2 | Which resource types are most heavily allocated at a selected time? Show allocated fraction divided by usable resource count, grouped by location/type, alongside unavailable resource count. | resource_type, resource, resource_allocation, resource_state, data_center | B | Operations |
| Q3 | Which approved reservation items are underfulfilled at a selected time within their reservation window? Compare quantity with distinct valid assigned resources and show the client and required location. | client, reservation, reservation_item, deployment, resource_allocation, resource, resource_type | A; C reviews assignments | Operations |
| Q4 | How much maintenance/failure downtime occurred per location and reason in a date range? Sum clipped non-overlapping state durations. | resource_state, resource, data_center, availability_zone, region | C | Operations |
| Q5 | Which clients/deployments had resource substitutions, and why? Join predecessor/current allocations, aggregate replacement counts, and expose before/after resources in details. | client, reservation, deployment, resource_allocation, resource | C | Operations |
| Q6 | For comparable service/deployment periods, how do estimates differ from actual consumption? Show side-by-side quantities and variance, grouped by billing unit. | usage_record, deployment_service, deployment, reservation, client, service | C supplies query/data; D owns Billing display | Billing |
| Q7 | How do final charges and credits trend by consuming client and service over time? Resolve charge context, aggregate USD amounts, and report provisional totals separately. | charge, usage_record, deployment_service, deployment, reservation, client, service | D | Billing |
| Q8 | What is each payer's invoice total, and how are charges split among accounts? Aggregate shares by invoice/account; show drafts and issued totals separately with drill-down to charge. | billing_account, client, invoice, charge_share, charge | D; A reviews payer contacts | Billing |

Q1 is an absolute-capacity comparison; Q2 is a type-level allocation ratio. Keep their interpretation distinct instead of presenting the same result twice. Q3-Q8 add independent fulfillment, reliability, change, metering, spending and payer questions.

## Query correctness

- At a selected time t, use startsAt <= t and (endsAt is null or t < endsAt). Apply each table's relevant status; drafts, void charges and inactive allocations do not silently contribute to final totals.
- Preaggregate allocation fractions per resource before joining location totals. Select at most one applicable state per resource. Keep vCPU, GiB and network Gbps separate; do not add unlike dimensions.
- Define a resource with no applicable usable state as unavailable. For Q2, exclude unavailable resources from the usable denominator and flag a zero denominator as N/A. It is an asset-equivalent allocation ratio, not observed CPU utilization or actual CPU load.
- For Q3, count allocations across all deployments of the same reservation item, not one deployment at a time. Validate type, per-instance capacity and mandatory location before treating an assignment as fulfillment.
- For Q4, clip intervals to the requested window and distinguish maintenance from failure. Non-overlapping state intervals prevent double counting time.
- For Q5, count replacement rows, not every link expanded through multiple unrelated joins. Replacement chains remain within one deployment/item.
- For Q6, take the latest correction separately for each record type; align comparable time periods. Display missing estimates/actuals as missing. Never combine billing units or add estimates to actuals.
- For Q7, resolve metered charges through usage, direct fees through deploymentServiceId, and adjustments through their original charge chain. Attribute credits to the original consuming client. Use posted-charge createdAt for the financial trend and label it explicitly; Q6 uses consumption periods. Every charge enters the aggregation once.
- For Q8, total allocatedAmount rather than repeating charge.amount once per payer. Keep consuming client and paying client distinct. Draft totals are provisional; issued invoices and shares retain history.

## Data and build sequence

1. Agree on the course DBMS; implement B's location/type fixtures and A's client/user/account fixtures.
2. Implement reservations, deployments, allocations and states; validate location and interval rules.
3. Implement services, rate history and consumption; include estimates and actuals over at least one quarter.
4. Implement charges and draft invoices; allocate payer shares, validate sums, then issue invoices.
5. Build and review all eight SQL queries before attaching the page components.
6. Integrate two pages, compare displayed values with SQL results, and prepare database export/source/presentation.

Include multiple regions, zones and data centers; diverse resource types; clients with organization/team relationships; overlapping valid allocations; maintenance/failures; underfilled requests; replacements; multiple services with different units and rates; estimates/actuals; direct fees, negative credits and split payers. Records must be sufficient to make each query nontrivial; example counts are a team decision rather than an assignment rule.

## Why each table remains

| Area | Five retained tables | Website purpose |
|---|---|---|
| A | client, user_account, reservation, reservation_item, billing_account | Identify consumers/payers, staff contacts, requests and shortages. |
| B | region, availability_zone, data_center, resource_type, resource | Filter and compare locations, resource categories and capacity. |
| C | deployment, resource_allocation, resource_state, deployment_service, usage_record | Explain actual assignment, availability, replacements and consumption. |
| D | service, service_rate, charge, charge_share, invoice | Explain billable offerings, prices, costs, credits, payer splits and invoice totals. |

`user_account` provides staff/contact names in details rather than its own dashboard. `service_rate` supports price verification and detail explanations rather than a separate pricing-management page. Other retained tables participate directly in the eight planned queries.

## Three removed tables and tradeoffs

- `project`: deployments are named and grouped by reservation/client. Independent project metadata and reporting are excluded.
- `client_membership`: each user has at most one current client through user_account.clientId. Many-to-many affiliations, roles and affiliation history are excluded.
- `invoice_line`: charge_share itself is the invoice line and references invoice. Payers are derived through the invoice; draft invoices must exist before monetary shares are created.
