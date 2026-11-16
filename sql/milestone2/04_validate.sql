-- One row per integrity violation. A valid milestone build returns zero rows.
-- Draft allocation differences are operational exceptions and appear in Q9.
WITH RECURSIVE client_ancestors(clientId, ancestorId) AS (
    SELECT clientId, parentClientId FROM client WHERE parentClientId IS NOT NULL
    UNION
    SELECT a.clientId, c.parentClientId
    FROM client_ancestors a JOIN client c ON c.clientId = a.ancestorId
    WHERE c.parentClientId IS NOT NULL
), booking_states AS (
    SELECT a.*, d.reservationId, d.startedAt, d.endedAt
    FROM resource_allocation a JOIN deployment d USING (deploymentId)
    WHERE a.allocationStatus IN ('planned', 'assigned')
), allocation_points AS (
    SELECT DISTINCT resourceId, startsAt FROM booking_states
), item_points AS (
    SELECT DISTINCT reservationItemId, startsAt FROM booking_states
), latest_usage AS (
    SELECT u.* FROM usage_record u
    WHERE NOT EXISTS (SELECT 1 FROM usage_record n WHERE n.supersedesUsageId = u.usageId)
), share_totals AS (
    SELECT c.chargeId, c.amount, SUM(cs.allocatedAmount) AS allocated,
           MAX(i.status = 'issued') AS issued
    FROM charge c
    JOIN charge_share cs USING (chargeId)
    JOIN invoice i USING (invoiceId)
    GROUP BY c.chargeId
)
SELECT 'foreign_key' AS rule, "table" || ':' || rowid AS entity FROM pragma_foreign_key_check
UNION ALL
SELECT 'client_cycle', clientId FROM client_ancestors WHERE clientId = ancestorId
UNION ALL
SELECT 'billing_contact', b.billingAccountId
FROM billing_account b JOIN user_account u ON u.userId = b.billingContactUserId
WHERE u.accountKind <> 'client' OR u.clientId IS NOT b.responsibleClientId
UNION ALL
SELECT 'reservation_approval', r.reservationId
FROM reservation r LEFT JOIN user_account u ON u.userId = r.approvedByUserId
WHERE r.status = 'approved' AND (
    u.staffRole IS NOT 'operations'
    OR NOT EXISTS (SELECT 1 FROM reservation_item i WHERE i.reservationId = r.reservationId)
)
UNION ALL
SELECT 'deployment_window', d.deploymentId FROM deployment d JOIN reservation r USING (reservationId)
WHERE d.status IN ('running', 'completed') AND (
    r.status <> 'approved' OR d.startedAt IS NULL OR d.startedAt < r.startTime
    OR d.startedAt >= r.endTime OR d.endedAt > r.endTime
    OR (d.status = 'completed' AND d.endedAt IS NULL)
)
UNION ALL
SELECT 'state_overlap', x.stateId FROM resource_state x JOIN resource_state y
ON x.resourceId = y.resourceId AND x.stateId < y.stateId
AND (y.endsAt IS NULL OR x.startsAt < y.endsAt)
AND (x.endsAt IS NULL OR y.startsAt < x.endsAt)
UNION ALL
SELECT 'state_actor', s.stateId FROM resource_state s JOIN user_account u ON u.userId = s.recordedByUserId
WHERE u.staffRole IS NOT 'operations'
UNION ALL
SELECT 'allocation_capacity', p.resourceId
FROM allocation_points p JOIN booking_states a ON a.resourceId = p.resourceId
AND a.startsAt <= p.startsAt AND (a.endsAt IS NULL OR a.endsAt > p.startsAt)
GROUP BY p.resourceId, p.startsAt HAVING SUM(a.capacityFraction) > 1.000000001
UNION ALL
SELECT 'item_overfilled', p.reservationItemId
FROM item_points p JOIN booking_states a ON a.reservationItemId = p.reservationItemId
AND a.startsAt <= p.startsAt AND (a.endsAt IS NULL OR a.endsAt > p.startsAt)
JOIN reservation_item i ON i.reservationItemId = p.reservationItemId
GROUP BY p.reservationItemId, p.startsAt
HAVING COUNT(*) > i.quantity OR COUNT(*) <> COUNT(DISTINCT a.resourceId)
UNION ALL
SELECT 'allocation_match', a.allocationId
FROM booking_states a
JOIN reservation r ON r.reservationId = a.reservationId
JOIN reservation_item i ON i.reservationItemId = a.reservationItemId
JOIN resource x USING (resourceId)
JOIN data_center dc USING (dataCenterId)
JOIN availability_zone z USING (zoneId)
LEFT JOIN user_account u ON u.userId = a.assignedByUserId
WHERE a.reservationId <> i.reservationId
   OR a.startsAt < r.startTime OR a.endsAt IS NULL OR a.endsAt > r.endTime
   OR (a.allocationStatus = 'assigned' AND (
       a.startedAt IS NULL OR a.startsAt < a.startedAt OR a.endsAt > a.endedAt
       OR NOT EXISTS (
           SELECT 1 FROM resource_state s
           WHERE s.resourceId = a.resourceId AND s.status = 'usable'
             AND s.startsAt <= a.startsAt AND (s.endsAt IS NULL OR s.endsAt >= a.endsAt)
       )
   ))
   OR (a.assignedByUserId IS NOT NULL AND u.staffRole IS NOT 'operations')
   OR x.resourceTypeId <> i.resourceTypeId OR x.vcpuCount * a.capacityFraction < i.minVcpu
   OR x.memoryGib * a.capacityFraction < i.minMemoryGib
   OR x.storageGib * a.capacityFraction < i.minStorageGib
   OR x.networkGbps * a.capacityFraction < i.minNetworkGbps
   OR ((i.preferredRegionId IS NOT NULL AND i.preferredRegionId <> z.regionId
       OR i.preferredZoneId IS NOT NULL AND i.preferredZoneId <> z.zoneId
       OR i.preferredDataCenterId IS NOT NULL AND i.preferredDataCenterId <> dc.dataCenterId)
       AND (i.locationMode = 'mandatory' OR length(trim(a.changeReason)) = 0))
UNION ALL
SELECT 'replacement_chain', a.allocationId
FROM resource_allocation a JOIN resource_allocation p ON p.allocationId = a.supersedesAllocationId
WHERE a.deploymentId <> p.deploymentId OR a.reservationItemId <> p.reservationItemId
   OR a.resourceId = p.resourceId OR p.endsAt IS NULL OR p.endsAt > a.startsAt
   OR length(trim(a.changeReason)) = 0 OR a.assignedByUserId IS NULL
UNION ALL
SELECT 'service_window', ds.deploymentServiceId
FROM deployment_service ds JOIN deployment d USING (deploymentId)
WHERE d.startedAt IS NULL OR ds.startsAt < d.startedAt
   OR (d.endedAt IS NOT NULL AND (ds.endsAt IS NULL OR ds.endsAt > d.endedAt))
UNION ALL
SELECT 'rate_overlap', x.serviceRateId FROM service_rate x JOIN service_rate y
ON x.serviceId = y.serviceId AND x.serviceRateId < y.serviceRateId
AND (y.validTo IS NULL OR x.validFrom < y.validTo)
AND (x.validTo IS NULL OR y.validFrom < x.validTo)
UNION ALL
SELECT 'usage_window', u.usageId
FROM usage_record u JOIN deployment_service ds USING (deploymentServiceId)
JOIN service s USING (serviceId)
LEFT JOIN resource_allocation a USING (allocationId)
WHERE u.periodStart < ds.startsAt OR u.periodEnd > ds.endsAt
   OR (s.serviceType IN ('compute', 'storage', 'network') AND a.allocationId IS NULL)
   OR (a.allocationId IS NOT NULL AND (
       a.deploymentId <> ds.deploymentId OR a.allocationStatus <> 'assigned'
       OR u.periodStart < a.startsAt OR u.periodEnd > a.endsAt
   ))
UNION ALL
SELECT 'usage_version', u.usageId FROM usage_record u JOIN usage_record p ON p.usageId = u.supersedesUsageId
WHERE u.deploymentServiceId <> p.deploymentServiceId OR u.allocationId IS NOT p.allocationId
   OR u.periodStart <> p.periodStart OR u.periodEnd <> p.periodEnd OR u.recordType <> p.recordType
   OR u.recordedAt <= p.recordedAt
UNION ALL
SELECT 'usage_duplicate', MIN(usageId) FROM latest_usage
GROUP BY deploymentServiceId, allocationId, periodStart, periodEnd, recordType
HAVING COUNT(*) > 1
UNION ALL
SELECT 'metered_charge', c.chargeId FROM charge c
JOIN usage_record u USING (usageId) JOIN deployment_service ds ON ds.deploymentServiceId = u.deploymentServiceId
JOIN service_rate rate USING (serviceRateId)
WHERE c.status <> 'void' AND (
    ds.serviceId <> rate.serviceId OR u.periodStart < rate.validFrom OR u.periodEnd > rate.validTo
    OR c.amount <> ROUND(u.quantity * rate.unitPrice) OR c.createdAt < u.recordedAt
    OR (c.status = 'posted' AND u.recordType <> 'actual')
    OR (c.status = 'provisional' AND u.recordType <> 'estimate')
)
UNION ALL
SELECT 'credit_authorization', c.chargeId
FROM charge c JOIN charge p ON p.chargeId = c.adjustmentOfChargeId
JOIN user_account u ON u.userId = c.authorizedByUserId
WHERE p.status <> 'posted' OR c.createdAt <= p.createdAt OR u.staffRole IS NOT 'billing'
UNION ALL
SELECT 'issued_unbalanced_charge', chargeId FROM share_totals WHERE issued = 1 AND allocated <> amount
UNION ALL
SELECT 'share_sign_or_status', cs.chargeShareId
FROM charge_share cs JOIN charge c USING (chargeId) JOIN invoice i USING (invoiceId)
WHERE c.status <> 'posted' OR c.createdAt > i.issuedAt
   OR (c.amount >= 0 AND cs.allocatedAmount < 0) OR (c.amount < 0 AND cs.allocatedAmount > 0)
UNION ALL
SELECT 'empty_issued_invoice', invoiceId FROM invoice i WHERE i.status = 'issued'
AND NOT EXISTS (SELECT 1 FROM charge_share cs WHERE cs.invoiceId = i.invoiceId)
ORDER BY rule, entity;
