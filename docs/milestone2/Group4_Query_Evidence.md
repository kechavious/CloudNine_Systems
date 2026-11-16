# Group 4 · Query evidence

Source: Group4_Initial_Export.sql. Timestamps are UTC.
Snapshot: 2026-09-10 12:00:00. Report period: May 1 through October 31, 2026.

| Tables | Total rows | Reservations | Deployments | Usage records | Posted charges |
| --- | --- | --- | --- | --- | --- |
| 20 | 24,459 | 444 | 432 | 9,523 | 5,089 |

## Q1 · Where is capacity available at the selected time?

27 result rows. Selected rows below.

| data center | usable assets | usable vcpu | allocated vcpu | free vcpu |
| --- | --- | --- | --- | --- |
| Ashburn DC | 3 | 64 | 16.00 | 48.00 |
| Newark DC | 4 | 80 | 16.00 | 64.00 |

Newark had 64 free vCPUs versus 48 in Ashburn. A flexible workload could use Newark. A request restricted to Ashburn still needs eligible local capacity.

## Q2 · Which regions and resource types have the highest allocation ratios?

9 result rows. Selected rows below.

| region | resource type | usable assets | unavailable assets | allocated asset equivalents | allocation pct |
| --- | --- | --- | --- | --- | --- |
| US East | Compute | 11 | 1 | 3.00 | 27.27 |
| EU Central | Compute | 12 | 0 | 3.00 | 25.00 |
| US West | Compute | 12 | 0 | 3.00 | 25.00 |

The regional compute ratios were US East 27.27%, EU Central 25.00%, US West 25.00%. An unavailable host reduces the usable denominator. The percentages measure reservations of asset capacity.

## Q3 · Which approved requests are short of valid usable resources?

1 result rows. Full result below.

| reservation id | item id | client | resource type | location mode | requested location | requested | fulfilled | shortfall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 315 | 723 | Atlas Labs | Compute | mandatory | Ashburn DC | 2 | 1 | 1 |

Atlas Labs was short one eligible compute asset at noon UTC on September 10. Rerunning Q3 at 2026-09-11 00:00:00 UTC returns zero shortages when the replacement starts.

## Q4 · How many resource-hours were lost to maintenance and failure?

24 result rows. Selected rows below.

| month | data center | event | reason | resource hours |
| --- | --- | --- | --- | --- |
| 2026-09 | Amsterdam DC | failed | Hardware failure | 24.00 |
| 2026-09 | Ashburn DC | failed | Hardware failure | 24.00 |
| 2026-09 | Newark DC | maintenance | Firmware rollout | 8.00 |
| 2026-09 | Portland DC | failed | Hardware failure | 24.00 |
| 2026-09 | Seattle DC | maintenance | Firmware rollout | 8.00 |

September lost 72 resource-hours to failures and 16 to planned maintenance. These are asset-hours summed across locations. The September 10 noon-to-midnight test counts 12 hours.

## Q5 · Which workloads were assigned replacement resources and for what reasons?

12 result rows. Selected rows below.

| client | deployment | reason | replacements | first replacement utc | resource pairs |
| --- | --- | --- | --- | --- | --- |
| Atlas Labs | Atlas Analytics / September | Hardware failure | 1 | 2026-09-11 00:00:00 | Ashburn DC/CMP-01 → Ashburn DC/CMP-04 |

The Atlas deployment replaced Ashburn CMP-01 with CMP-04 at 00:00 UTC on September 11. Across the full period, 12 replacements were recorded.

## Q6 · Which services are running above or below their usage estimates?

18 result rows. Selected rows below.

| month | unit | paired periods | missing estimates | missing actuals | paired estimate | paired actual | variance pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05 | vCPU-hours | 331 | 28 | 0 | 34,109.00 | 34,932.00 | 2.41 |
| 2026-06 | vCPU-hours | 323 | 36 | 0 | 32,820.00 | 33,684.00 | 2.63 |
| 2026-07 | vCPU-hours | 318 | 40 | 0 | 33,336.00 | 33,929.00 | 1.78 |
| 2026-08 | vCPU-hours | 318 | 40 | 0 | 31,839.00 | 32,349.00 | 1.60 |
| 2026-09 | vCPU-hours | 317 | 40 | 0 | 32,183.00 | 32,709.00 | 1.63 |
| 2026-10 | vCPU-hours | 316 | 40 | 1 | 32,615.00 | 33,686.00 | 3.28 |

Compute had its highest positive paired variance in 2026-10 (3.28%). The focal September 11 reading was 100 estimated and 120 actual vCPU-hours after correction. Periods missing either value are counted separately from the paired comparison.

## Q7 · How do posted fees and credits trend by consuming client and service?

361 result rows. Selected rows below.

| posting month | consuming client | service | posted charges | fees usd | credits usd | net usd |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09 | Atlas Labs | Block Storage | 5 | 44.07 | 0.00 | 44.07 |
| 2026-09 | Atlas Labs | Compute | 6 | 231.50 | -6.00 | 225.50 |
| 2026-09 | Atlas Labs | Network Egress | 5 | 134.73 | 0.00 | 134.73 |

All $6.00 in posted credits belong to Atlas Labs Compute in September. The sponsor's payment share does not change the consuming-client attribution.

## Q8 · What are payer invoice totals and which invoices contain split charges?

147 result rows. Selected rows below.

| invoice id | payer account | status | issued at utc | invoice lines | split charge lines | invoice total usd |
| --- | --- | --- | --- | --- | --- | --- |
| 109 | Atlas Labs Billing | issued | 2026-10-02 00:00:00 | 16 | 16 | 242.58 |
| 110 | Northstar Research Foundation Billing | issued | 2026-10-02 00:00:00 | 51 | 51 | 609.38 |

Both payer invoices include split charges. The $60.00 focal metered charge contributes $36.00 to Atlas Labs and $24.00 to the sponsor. The invoices also contain other shares, so their totals differ from this one split.

## Q9 · Which posted charges are still out of balance before invoice issuance?

2 result rows. Full result below.

| charge id | posted at utc | share count | issued share count | charge usd | allocated usd | difference usd | issue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4816 | 2026-10-17 04:00:00 | 0 | 0 | 68.00 | 0.00 | 68.00 | Unallocated |
| 4727 | 2026-10-17 04:00:00 | 1 | 0 | 51.50 | 50.50 | 1.00 | Underallocated |

Two October charges need action before reconciliation: one has no share and one is short by $1.00. Neither appears on an issued invoice.

## Atlas Labs · Invoice line detail

| charge type | charge id | consumer | payer account | invoice id | status | share usd |
| --- | --- | --- | --- | --- | --- | --- |
| metered | 3606 | Atlas Labs | Atlas Labs Billing | 109 | issued | 36.00 |
| metered | 3606 | Atlas Labs | Northstar Research Foundation Billing | 110 | issued | 24.00 |
| credit | 3607 | Atlas Labs | Atlas Labs Billing | 109 | issued | -3.60 |
| credit | 3607 | Atlas Labs | Northstar Research Foundation Billing | 110 | issued | -2.40 |

The -$6.00 credit reuses the original 60/40 split. The two shares sum to -$6.00.
