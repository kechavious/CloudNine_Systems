-- Bind UTC values before running. See docs/milestone2/Group4_Milestone2.md.
-- :as_of = '2026-09-10 12:00:00'
-- :from_utc = '2026-05-01 00:00:00'
-- :to_utc = '2026-11-01 00:00:00' (exclusive)

-- Q1 | Where is capacity available at the selected time?
WITH asset_load AS (
    SELECT resourceId, SUM(capacityFraction) AS fraction
    FROM resource_allocation
    WHERE allocationStatus = 'assigned' AND startsAt <= :as_of
      AND (endsAt IS NULL OR endsAt > :as_of)
    GROUP BY resourceId
), usable_asset AS (
    SELECT r.*, COALESCE(al.fraction, 0) AS fraction
    FROM resource r
    LEFT JOIN asset_load al USING (resourceId)
    WHERE EXISTS (
        SELECT 1 FROM resource_state s
        WHERE s.resourceId = r.resourceId AND s.status = 'usable'
          AND s.startsAt <= :as_of AND (s.endsAt IS NULL OR s.endsAt > :as_of)
    )
)
SELECT g.name AS region, z.name AS zone, dc.name AS data_center, t.name AS resource_type,
       COUNT(*) AS usable_assets,
       SUM(a.vcpuCount) AS usable_vcpu,
       ROUND(SUM(a.vcpuCount * a.fraction), 2) AS allocated_vcpu,
       ROUND(SUM(a.vcpuCount * (1 - a.fraction)), 2) AS free_vcpu,
       ROUND(SUM(a.memoryGib), 2) AS usable_memory_gib,
       ROUND(SUM(a.memoryGib * a.fraction), 2) AS allocated_memory_gib,
       ROUND(SUM(a.memoryGib * (1 - a.fraction)), 2) AS free_memory_gib,
       ROUND(SUM(a.storageGib), 2) AS usable_storage_gib,
       ROUND(SUM(a.storageGib * a.fraction), 2) AS allocated_storage_gib,
       ROUND(SUM(a.storageGib * (1 - a.fraction)), 2) AS free_storage_gib,
       ROUND(SUM(a.networkGbps), 2) AS usable_network_gbps,
       ROUND(SUM(a.networkGbps * a.fraction), 2) AS allocated_network_gbps,
       ROUND(SUM(a.networkGbps * (1 - a.fraction)), 2) AS free_network_gbps
FROM usable_asset a
JOIN data_center dc USING (dataCenterId)
JOIN availability_zone z USING (zoneId)
JOIN region g USING (regionId)
JOIN resource_type t USING (resourceTypeId)
GROUP BY g.regionId, z.zoneId, dc.dataCenterId, t.resourceTypeId
ORDER BY g.name, dc.name, t.name;

-- Q2 | Which regions and resource types have the highest allocation ratios?
WITH asset_load AS (
    SELECT resourceId, SUM(capacityFraction) AS fraction
    FROM resource_allocation
    WHERE allocationStatus = 'assigned' AND startsAt <= :as_of
      AND (endsAt IS NULL OR endsAt > :as_of)
    GROUP BY resourceId
), asset AS (
    SELECT r.resourceId, r.dataCenterId, r.resourceTypeId,
           COALESCE(al.fraction, 0) AS fraction,
           EXISTS (
               SELECT 1 FROM resource_state s
               WHERE s.resourceId = r.resourceId AND s.status = 'usable'
                 AND s.startsAt <= :as_of AND (s.endsAt IS NULL OR s.endsAt > :as_of)
           ) AS usable
    FROM resource r
    LEFT JOIN asset_load al USING (resourceId)
)
SELECT g.name AS region, t.name AS resource_type,
       SUM(a.usable) AS usable_assets, COUNT(*) - SUM(a.usable) AS unavailable_assets,
       ROUND(SUM(a.usable * a.fraction), 2) AS allocated_asset_equivalents,
       ROUND(100.0 * SUM(a.usable * a.fraction) / NULLIF(SUM(a.usable), 0), 2) AS allocation_pct
FROM asset a
JOIN data_center dc USING (dataCenterId)
JOIN availability_zone z USING (zoneId)
JOIN region g USING (regionId)
JOIN resource_type t USING (resourceTypeId)
GROUP BY g.regionId, t.resourceTypeId
ORDER BY allocation_pct DESC, g.name, t.name;

-- Q3 | Which approved requests are short of valid usable resources?
WITH valid_assignment AS (
    SELECT a.reservationItemId, r.resourceId
    FROM resource_allocation a
    JOIN deployment d USING (deploymentId)
    JOIN reservation_item i ON i.reservationItemId = a.reservationItemId
                           AND i.reservationId = d.reservationId
    JOIN resource r ON r.resourceId = a.resourceId
    JOIN data_center dc ON dc.dataCenterId = r.dataCenterId
    JOIN availability_zone z USING (zoneId)
    WHERE a.allocationStatus = 'assigned' AND a.startsAt <= :as_of
      AND (a.endsAt IS NULL OR a.endsAt > :as_of)
      AND d.status IN ('running', 'completed') AND d.startedAt <= :as_of
      AND (d.endedAt IS NULL OR d.endedAt > :as_of)
      AND r.resourceTypeId = i.resourceTypeId
      AND r.vcpuCount * a.capacityFraction >= i.minVcpu
      AND r.memoryGib * a.capacityFraction >= i.minMemoryGib
      AND r.storageGib * a.capacityFraction >= i.minStorageGib
      AND r.networkGbps * a.capacityFraction >= i.minNetworkGbps
      AND (i.locationMode <> 'mandatory' OR (
          (i.preferredRegionId IS NULL OR i.preferredRegionId = z.regionId)
          AND (i.preferredZoneId IS NULL OR i.preferredZoneId = z.zoneId)
          AND (i.preferredDataCenterId IS NULL OR i.preferredDataCenterId = dc.dataCenterId)
      ))
      AND EXISTS (
          SELECT 1 FROM resource_state s
          WHERE s.resourceId = r.resourceId AND s.status = 'usable'
            AND s.startsAt <= :as_of AND (s.endsAt IS NULL OR s.endsAt > :as_of)
      )
)
SELECT r.reservationId AS reservation_id, i.reservationItemId AS item_id, c.name AS client,
       t.name AS resource_type, i.locationMode AS location_mode,
       COALESCE(dc.name, z.name, g.name, 'Any location') AS requested_location,
       i.quantity AS requested, COUNT(DISTINCT a.resourceId) AS fulfilled,
       i.quantity - COUNT(DISTINCT a.resourceId) AS shortfall
FROM reservation r
JOIN client c USING (clientId)
JOIN reservation_item i USING (reservationId)
JOIN resource_type t USING (resourceTypeId)
LEFT JOIN data_center dc ON dc.dataCenterId = i.preferredDataCenterId
LEFT JOIN availability_zone z ON z.zoneId = i.preferredZoneId
LEFT JOIN region g ON g.regionId = i.preferredRegionId
LEFT JOIN valid_assignment a USING (reservationItemId)
WHERE r.status = 'approved' AND r.startTime <= :as_of AND r.endTime > :as_of
GROUP BY i.reservationItemId
HAVING COUNT(DISTINCT a.resourceId) < i.quantity
ORDER BY shortfall DESC, item_id;

-- Q4 | How many resource-hours were lost to maintenance and failure?
WITH RECURSIVE months(month_start) AS (
    SELECT datetime(:from_utc, 'start of month') WHERE :from_utc < :to_utc
    UNION ALL
    SELECT datetime(month_start, '+1 month')
    FROM months
    WHERE datetime(month_start, '+1 month') < :to_utc
), windows AS (
    SELECT substr(month_start, 1, 7) AS month, max(month_start, :from_utc) AS window_start,
           min(datetime(month_start, '+1 month'), :to_utc) AS window_end
    FROM months
)
SELECT w.month, g.name AS region, dc.name AS data_center, s.status AS event, s.reason,
       COUNT(*) AS intervals_in_month,
       ROUND(SUM(unixepoch(min(COALESCE(s.endsAt, w.window_end), w.window_end))
               - unixepoch(max(s.startsAt, w.window_start))) / 3600.0, 2) AS resource_hours
FROM windows w
JOIN resource_state s ON s.startsAt < w.window_end
                     AND (s.endsAt IS NULL OR s.endsAt > w.window_start)
JOIN resource r USING (resourceId)
JOIN data_center dc USING (dataCenterId)
JOIN availability_zone z USING (zoneId)
JOIN region g USING (regionId)
WHERE s.status IN ('maintenance', 'failed')
GROUP BY w.month, g.regionId, dc.dataCenterId, s.status, s.reason
ORDER BY w.month, g.name, dc.name, s.status, s.reason;

-- Q5 | Which workloads were assigned replacement resources and for what reasons?
SELECT c.name AS client, d.name AS deployment, a.changeReason AS reason,
       COUNT(*) AS replacements, MIN(a.startsAt) AS first_replacement_utc,
       GROUP_CONCAT(DISTINCT old_dc.name || '/' || old_resource.localIdentifier
                    || ' → ' || new_dc.name || '/' || new_resource.localIdentifier) AS resource_pairs
FROM resource_allocation a
JOIN resource_allocation previous ON previous.allocationId = a.supersedesAllocationId
JOIN deployment d ON d.deploymentId = a.deploymentId
JOIN reservation r USING (reservationId)
JOIN client c USING (clientId)
JOIN resource old_resource ON old_resource.resourceId = previous.resourceId
JOIN resource new_resource ON new_resource.resourceId = a.resourceId
JOIN data_center old_dc ON old_dc.dataCenterId = old_resource.dataCenterId
JOIN data_center new_dc ON new_dc.dataCenterId = new_resource.dataCenterId
WHERE a.allocationStatus = 'assigned' AND a.startsAt >= :from_utc AND a.startsAt < :to_utc
GROUP BY c.clientId, d.deploymentId, a.changeReason
ORDER BY replacements DESC, c.name, d.name, a.changeReason;

-- Q6 | Which services are running above or below their usage estimates?
WITH latest AS (
    SELECT u.*
    FROM usage_record u
    WHERE u.periodStart >= :from_utc AND u.periodEnd <= :to_utc
      AND NOT EXISTS (SELECT 1 FROM usage_record next WHERE next.supersedesUsageId = u.usageId)
), paired AS (
    SELECT deploymentServiceId, allocationId, periodStart, periodEnd,
           SUM(CASE WHEN recordType = 'estimate' THEN quantity END) AS estimate,
           SUM(CASE WHEN recordType = 'actual' THEN quantity END) AS actual
    FROM latest
    GROUP BY deploymentServiceId, allocationId, periodStart, periodEnd
), monthly AS (
    SELECT substr(p.periodStart, 1, 7) AS month, s.name AS service, s.billingUnit AS unit,
           COUNT(*) FILTER (WHERE estimate IS NOT NULL AND actual IS NOT NULL) AS paired_periods,
           COUNT(*) FILTER (WHERE estimate IS NULL) AS missing_estimates,
           COUNT(*) FILTER (WHERE actual IS NULL) AS missing_actuals,
           SUM(estimate) FILTER (WHERE actual IS NOT NULL) AS paired_estimate,
           SUM(actual) FILTER (WHERE estimate IS NOT NULL) AS paired_actual
    FROM paired p
    JOIN deployment_service ds USING (deploymentServiceId)
    JOIN service s USING (serviceId)
    GROUP BY substr(p.periodStart, 1, 7), s.serviceId
)
SELECT *, ROUND(paired_actual - paired_estimate, 2) AS variance,
       ROUND(100.0 * (paired_actual - paired_estimate) / NULLIF(paired_estimate, 0), 2) AS variance_pct
FROM monthly
ORDER BY month, service;

-- Q7 | How do posted fees and credits trend by consuming client and service?
WITH RECURSIVE charge_context(chargeId, deploymentServiceId) AS (
    SELECT c.chargeId, COALESCE(c.deploymentServiceId, u.deploymentServiceId)
    FROM charge c
    LEFT JOIN usage_record u USING (usageId)
    WHERE c.adjustmentOfChargeId IS NULL
    UNION ALL
    SELECT c.chargeId, parent.deploymentServiceId
    FROM charge c
    JOIN charge_context parent ON parent.chargeId = c.adjustmentOfChargeId
)
SELECT substr(ch.createdAt, 1, 7) AS posting_month, c.name AS consuming_client, s.name AS service,
       COUNT(*) AS posted_charges,
       ROUND(SUM(CASE WHEN ch.amount > 0 THEN ch.amount ELSE 0 END) / 100.0, 2) AS fees_usd,
       ROUND(SUM(CASE WHEN ch.amount < 0 THEN ch.amount ELSE 0 END) / 100.0, 2) AS credits_usd,
       ROUND(SUM(ch.amount) / 100.0, 2) AS net_usd
FROM charge_context cc
JOIN charge ch USING (chargeId)
JOIN deployment_service ds ON ds.deploymentServiceId = cc.deploymentServiceId
JOIN service s USING (serviceId)
JOIN deployment d USING (deploymentId)
JOIN reservation r USING (reservationId)
JOIN client c USING (clientId)
WHERE ch.status = 'posted' AND ch.createdAt >= :from_utc AND ch.createdAt < :to_utc
GROUP BY substr(ch.createdAt, 1, 7), c.clientId, s.serviceId
ORDER BY posting_month, c.name, s.name;

-- Q8 | What are payer invoice totals and which invoices contain split charges?
WITH split_charge AS (
    SELECT cs.chargeId
    FROM charge_share cs
    JOIN invoice i USING (invoiceId)
    GROUP BY cs.chargeId
    HAVING COUNT(DISTINCT i.billingAccountId) > 1
)
SELECT i.invoiceId AS invoice_id, b.name AS payer_account, i.status, i.issuedAt AS issued_at_utc,
       COUNT(cs.chargeId) AS invoice_lines, COUNT(sc.chargeId) AS split_charge_lines,
       ROUND(COALESCE(SUM(cs.allocatedAmount), 0) / 100.0, 2) AS invoice_total_usd
FROM invoice i
JOIN billing_account b USING (billingAccountId)
LEFT JOIN charge_share cs USING (invoiceId)
LEFT JOIN split_charge sc USING (chargeId)
GROUP BY i.invoiceId
ORDER BY i.status, i.issuedAt, b.name, i.invoiceId;

-- Q9 | Which posted charges are still out of balance before invoice issuance?
WITH reconciliation AS (
    SELECT ch.chargeId, ch.createdAt, ch.amount, COUNT(cs.invoiceId) AS share_count,
           COALESCE(SUM(cs.allocatedAmount), 0) AS allocated,
           COUNT(*) FILTER (WHERE i.status = 'issued') AS issued_share_count
    FROM charge ch
    LEFT JOIN charge_share cs USING (chargeId)
    LEFT JOIN invoice i USING (invoiceId)
    WHERE ch.status = 'posted' AND ch.createdAt >= :from_utc AND ch.createdAt < :to_utc
    GROUP BY ch.chargeId
)
SELECT chargeId AS charge_id, createdAt AS posted_at_utc, share_count, issued_share_count,
       ROUND(amount / 100.0, 2) AS charge_usd,
       ROUND(allocated / 100.0, 2) AS allocated_usd,
       ROUND((amount - allocated) / 100.0, 2) AS difference_usd,
       CASE WHEN share_count = 0 THEN 'Unallocated'
            WHEN abs(allocated) < abs(amount) THEN 'Underallocated'
            ELSE 'Overallocated' END AS issue
FROM reconciliation
WHERE share_count = 0 OR allocated <> amount
ORDER BY abs(amount - allocated) DESC, chargeId;
