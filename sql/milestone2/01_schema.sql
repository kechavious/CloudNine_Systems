-- Group 4 / CloudNine Systems / SQLite 3.38+
-- Timestamp columns use ISO 8601 UTC text (YYYY-MM-DD HH:MM:SS).
-- Monetary columns amount, allocatedAmount and unitPrice are integer US cents.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE client (
    clientId INTEGER PRIMARY KEY,
    parentClientId INTEGER REFERENCES client(clientId),
    name TEXT NOT NULL,
    clientType TEXT NOT NULL,
    contactEmail TEXT NOT NULL,
    qualificationNote TEXT,
    CHECK (clientType IN ('organization', 'team', 'individual')),
    CHECK (parentClientId IS NOT clientId)
) STRICT;

CREATE TABLE user_account (
    userId INTEGER PRIMARY KEY,
    clientId INTEGER REFERENCES client(clientId),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    accountKind TEXT NOT NULL,
    staffRole TEXT,
    status TEXT NOT NULL,
    UNIQUE (email),
    CHECK (status IN ('active', 'inactive')),
    CHECK ((accountKind = 'staff' AND staffRole IS NOT NULL)
        OR (accountKind = 'client' AND clientId IS NOT NULL AND staffRole IS NULL))
) STRICT;

CREATE TABLE region (
    regionId INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    regulatoryNote TEXT NOT NULL,
    UNIQUE (name)
) STRICT;

CREATE TABLE availability_zone (
    zoneId INTEGER PRIMARY KEY,
    regionId INTEGER NOT NULL REFERENCES region(regionId),
    name TEXT NOT NULL,
    redundancyNote TEXT NOT NULL,
    connectivityNote TEXT NOT NULL,
    UNIQUE (regionId, name)
) STRICT;

CREATE TABLE data_center (
    dataCenterId INTEGER PRIMARY KEY,
    zoneId INTEGER NOT NULL REFERENCES availability_zone(zoneId),
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    UNIQUE (zoneId, name)
) STRICT;

CREATE TABLE resource_type (
    resourceTypeId INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    intendedWorkload TEXT NOT NULL,
    UNIQUE (name)
) STRICT;

CREATE TABLE resource (
    resourceId INTEGER PRIMARY KEY,
    resourceTypeId INTEGER NOT NULL REFERENCES resource_type(resourceTypeId),
    dataCenterId INTEGER NOT NULL REFERENCES data_center(dataCenterId),
    localIdentifier TEXT NOT NULL,
    performanceTier TEXT NOT NULL,
    vcpuCount INTEGER NOT NULL,
    memoryGib REAL NOT NULL,
    storageGib REAL NOT NULL,
    networkGbps REAL NOT NULL,
    UNIQUE (dataCenterId, localIdentifier),
    CHECK (min(vcpuCount, memoryGib, storageGib, networkGbps) >= 0)
) STRICT;

CREATE TABLE resource_state (
    stateId INTEGER PRIMARY KEY,
    resourceId INTEGER NOT NULL REFERENCES resource(resourceId),
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    startsAt TEXT NOT NULL CHECK (datetime(startsAt, '+0 seconds') IS startsAt),
    endsAt TEXT CHECK (datetime(endsAt, '+0 seconds') IS endsAt),
    recordedByUserId INTEGER REFERENCES user_account(userId),
    CHECK (status IN ('usable', 'maintenance', 'failed', 'retired')),
    CHECK (endsAt IS NULL OR startsAt < endsAt)
) STRICT;

CREATE TABLE reservation (
    reservationId INTEGER PRIMARY KEY,
    clientId INTEGER NOT NULL REFERENCES client(clientId),
    createdAt TEXT NOT NULL CHECK (datetime(createdAt, '+0 seconds') IS createdAt),
    startTime TEXT NOT NULL CHECK (datetime(startTime, '+0 seconds') IS startTime),
    endTime TEXT NOT NULL CHECK (datetime(endTime, '+0 seconds') IS endTime),
    status TEXT NOT NULL,
    agreementNote TEXT,
    approvedByUserId INTEGER REFERENCES user_account(userId),
    CHECK (status IN ('pending', 'approved', 'cancelled', 'rejected')),
    CHECK (createdAt <= startTime AND startTime < endTime),
    CHECK (status <> 'approved' OR approvedByUserId IS NOT NULL)
) STRICT;

CREATE TABLE reservation_item (
    reservationItemId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL REFERENCES reservation(reservationId),
    resourceTypeId INTEGER NOT NULL REFERENCES resource_type(resourceTypeId),
    quantity INTEGER NOT NULL,
    minVcpu INTEGER NOT NULL,
    minMemoryGib REAL NOT NULL,
    minStorageGib REAL NOT NULL,
    minNetworkGbps REAL NOT NULL,
    preferredRegionId INTEGER REFERENCES region(regionId),
    preferredZoneId INTEGER REFERENCES availability_zone(zoneId),
    preferredDataCenterId INTEGER REFERENCES data_center(dataCenterId),
    locationMode TEXT NOT NULL,
    CHECK (quantity > 0),
    CHECK (min(minVcpu, minMemoryGib, minStorageGib, minNetworkGbps) >= 0),
    CHECK ((preferredRegionId IS NOT NULL) + (preferredZoneId IS NOT NULL)
        + (preferredDataCenterId IS NOT NULL) = CASE WHEN locationMode = 'any' THEN 0 ELSE 1 END),
    CHECK (locationMode IN ('any', 'preferred', 'mandatory'))
) STRICT;

CREATE TABLE deployment (
    deploymentId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL REFERENCES reservation(reservationId),
    name TEXT NOT NULL,
    workloadNote TEXT NOT NULL,
    startedAt TEXT CHECK (datetime(startedAt, '+0 seconds') IS startedAt),
    endedAt TEXT CHECK (datetime(endedAt, '+0 seconds') IS endedAt),
    confidentialityLevel TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL,
    scalingMode TEXT NOT NULL,
    CHECK (status IN ('planned', 'running', 'completed', 'cancelled')),
    CHECK (endedAt IS NULL OR (startedAt IS NOT NULL AND startedAt < endedAt)),
    CHECK (priority > 0)
) STRICT;

CREATE TABLE resource_allocation (
    allocationId INTEGER PRIMARY KEY,
    deploymentId INTEGER NOT NULL REFERENCES deployment(deploymentId),
    reservationItemId INTEGER NOT NULL REFERENCES reservation_item(reservationItemId),
    resourceId INTEGER NOT NULL REFERENCES resource(resourceId),
    capacityFraction REAL NOT NULL,
    startsAt TEXT NOT NULL CHECK (datetime(startsAt, '+0 seconds') IS startsAt),
    endsAt TEXT CHECK (datetime(endsAt, '+0 seconds') IS endsAt),
    allocationStatus TEXT NOT NULL,
    supersedesAllocationId INTEGER REFERENCES resource_allocation(allocationId),
    changeReason TEXT NOT NULL,
    assignedByUserId INTEGER REFERENCES user_account(userId),
    CHECK (capacityFraction > 0 AND capacityFraction <= 1),
    CHECK (allocationStatus IN ('planned', 'assigned', 'cancelled')),
    CHECK (endsAt IS NULL OR startsAt < endsAt),
    CHECK (supersedesAllocationId IS NOT allocationId)
) STRICT;

CREATE TABLE deployment_service (
    deploymentServiceId INTEGER PRIMARY KEY,
    deploymentId INTEGER NOT NULL REFERENCES deployment(deploymentId),
    serviceId INTEGER NOT NULL REFERENCES service(serviceId),
    startsAt TEXT NOT NULL CHECK (datetime(startsAt, '+0 seconds') IS startsAt),
    endsAt TEXT CHECK (datetime(endsAt, '+0 seconds') IS endsAt),
    CHECK (endsAt IS NULL OR startsAt < endsAt)
) STRICT;

CREATE TABLE service (
    serviceId INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    serviceType TEXT NOT NULL,
    billingUnit TEXT NOT NULL,
    UNIQUE (name)
) STRICT;

CREATE TABLE service_rate (
    serviceRateId INTEGER PRIMARY KEY,
    serviceId INTEGER NOT NULL REFERENCES service(serviceId),
    validFrom TEXT NOT NULL CHECK (datetime(validFrom, '+0 seconds') IS validFrom),
    validTo TEXT CHECK (datetime(validTo, '+0 seconds') IS validTo),
    unitPrice INTEGER NOT NULL,
    UNIQUE (serviceId, validFrom),
    CHECK (validTo IS NULL OR validFrom < validTo),
    CHECK (unitPrice >= 0)
) STRICT;

CREATE TABLE usage_record (
    usageId INTEGER PRIMARY KEY,
    deploymentServiceId INTEGER NOT NULL REFERENCES deployment_service(deploymentServiceId),
    allocationId INTEGER REFERENCES resource_allocation(allocationId),
    quantity REAL NOT NULL,
    periodStart TEXT NOT NULL CHECK (datetime(periodStart, '+0 seconds') IS periodStart),
    periodEnd TEXT NOT NULL CHECK (datetime(periodEnd, '+0 seconds') IS periodEnd),
    recordType TEXT NOT NULL,
    recordedAt TEXT NOT NULL CHECK (datetime(recordedAt, '+0 seconds') IS recordedAt),
    supersedesUsageId INTEGER REFERENCES usage_record(usageId),
    UNIQUE (supersedesUsageId),
    CHECK (quantity >= 0 AND periodStart < periodEnd),
    CHECK (recordType IN ('estimate', 'actual')),
    CHECK (recordType <> 'actual' OR recordedAt >= periodEnd),
    CHECK (supersedesUsageId IS NOT usageId)
) STRICT;

CREATE TABLE billing_account (
    billingAccountId INTEGER PRIMARY KEY,
    responsibleClientId INTEGER NOT NULL REFERENCES client(clientId),
    name TEXT NOT NULL,
    billingContactUserId INTEGER REFERENCES user_account(userId)
) STRICT;

CREATE TABLE invoice (
    invoiceId INTEGER PRIMARY KEY,
    billingAccountId INTEGER NOT NULL REFERENCES billing_account(billingAccountId),
    issuedAt TEXT CHECK (datetime(issuedAt, '+0 seconds') IS issuedAt),
    dueAt TEXT NOT NULL CHECK (datetime(dueAt, '+0 seconds') IS dueAt),
    status TEXT NOT NULL,
    CHECK (status IN ('draft', 'issued')),
    CHECK ((status = 'draft' AND issuedAt IS NULL)
        OR (status = 'issued' AND issuedAt IS NOT NULL AND issuedAt <= dueAt))
) STRICT;

CREATE TABLE charge (
    chargeId INTEGER PRIMARY KEY,
    usageId INTEGER REFERENCES usage_record(usageId),
    deploymentServiceId INTEGER REFERENCES deployment_service(deploymentServiceId),
    serviceRateId INTEGER REFERENCES service_rate(serviceRateId),
    adjustmentOfChargeId INTEGER REFERENCES charge(chargeId),
    authorizedByUserId INTEGER REFERENCES user_account(userId),
    chargeType TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    createdAt TEXT NOT NULL CHECK (datetime(createdAt, '+0 seconds') IS createdAt),
    UNIQUE (usageId),
    CHECK (status IN ('provisional', 'posted', 'void')),
    CHECK (adjustmentOfChargeId IS NOT chargeId),
    CHECK (
        (chargeType = 'metered' AND usageId IS NOT NULL AND serviceRateId IS NOT NULL
            AND deploymentServiceId IS NULL AND adjustmentOfChargeId IS NULL AND amount >= 0)
        OR (chargeType = 'direct' AND deploymentServiceId IS NOT NULL
            AND usageId IS NULL AND serviceRateId IS NULL AND adjustmentOfChargeId IS NULL AND amount >= 0)
        OR (chargeType = 'credit' AND adjustmentOfChargeId IS NOT NULL
            AND usageId IS NULL AND serviceRateId IS NULL AND amount < 0
            AND authorizedByUserId IS NOT NULL AND length(trim(reason)) > 0)
    )
) STRICT;

CREATE TABLE charge_share (
    chargeShareId INTEGER PRIMARY KEY,
    chargeId INTEGER NOT NULL REFERENCES charge(chargeId),
    invoiceId INTEGER NOT NULL REFERENCES invoice(invoiceId),
    allocatedAmount INTEGER NOT NULL,
    UNIQUE (chargeId, invoiceId)
) STRICT;

CREATE INDEX idx_state_resource_time ON resource_state(resourceId, startsAt, endsAt);
CREATE INDEX idx_alloc_resource_time ON resource_allocation(resourceId, startsAt, endsAt);
CREATE INDEX idx_alloc_item_time ON resource_allocation(reservationItemId, startsAt, endsAt);
CREATE INDEX idx_usage_service_period ON usage_record(deploymentServiceId, periodStart, periodEnd);
CREATE INDEX idx_charge_status_time ON charge(status, createdAt);
CREATE INDEX idx_charge_adjustment ON charge(adjustmentOfChargeId);
CREATE INDEX idx_share_invoice ON charge_share(invoiceId);
CREATE INDEX idx_invoice_payer ON invoice(billingAccountId, status);

-- Invoice issue is a database-enforced transition. Draft discrepancies can be reviewed in Q9.
CREATE TRIGGER invoice_starts_draft
BEFORE INSERT ON invoice WHEN NEW.status = 'issued'
BEGIN
    SELECT RAISE(ABORT, 'Create invoice as draft before allocation');
END;

CREATE TRIGGER invoice_issue_reconciles
BEFORE UPDATE OF status, issuedAt ON invoice
WHEN OLD.status = 'draft' AND NEW.status = 'issued'
BEGIN
    SELECT RAISE(ABORT, 'Issuance requires at least one share')
    WHERE NOT EXISTS (SELECT 1 FROM charge_share WHERE invoiceId = OLD.invoiceId);
    SELECT RAISE(ABORT, 'Issuance requires fully allocated posted charges')
    WHERE EXISTS (
        SELECT 1
        FROM charge_share own_share
        JOIN charge c USING (chargeId)
        WHERE own_share.invoiceId = OLD.invoiceId AND (
            c.status <> 'posted' OR c.createdAt > NEW.issuedAt OR
            c.amount <> (SELECT SUM(allocatedAmount) FROM charge_share WHERE chargeId = c.chargeId)
        )
    );
END;

CREATE TRIGGER issued_invoice_no_update
BEFORE UPDATE ON invoice WHEN OLD.status = 'issued'
BEGIN
    SELECT RAISE(ABORT, 'Issued invoice is immutable');
END;

CREATE TRIGGER issued_invoice_no_delete
BEFORE DELETE ON invoice WHEN OLD.status = 'issued'
BEGIN
    SELECT RAISE(ABORT, 'Issued invoice is immutable');
END;

CREATE TRIGGER charge_share_insert_guard
BEFORE INSERT ON charge_share
BEGIN
    SELECT RAISE(ABORT, 'Share requires a posted charge with a matching sign')
    WHERE NOT EXISTS (
        SELECT 1 FROM charge c WHERE c.chargeId = NEW.chargeId AND c.status = 'posted'
        AND (c.amount >= 0 AND NEW.allocatedAmount >= 0 OR c.amount < 0 AND NEW.allocatedAmount <= 0)
    );
    SELECT RAISE(ABORT, 'Shares are frozen after any related invoice is issued')
    WHERE EXISTS (
        SELECT 1 FROM invoice i WHERE i.status = 'issued' AND
        (i.invoiceId = NEW.invoiceId OR i.invoiceId IN (
            SELECT invoiceId FROM charge_share WHERE chargeId = NEW.chargeId
        ))
    );
END;

CREATE TRIGGER charge_share_update_guard
BEFORE UPDATE ON charge_share
BEGIN
    SELECT RAISE(ABORT, 'Share requires a posted charge with a matching sign')
    WHERE NOT EXISTS (
        SELECT 1 FROM charge c WHERE c.chargeId = NEW.chargeId AND c.status = 'posted'
        AND (c.amount >= 0 AND NEW.allocatedAmount >= 0 OR c.amount < 0 AND NEW.allocatedAmount <= 0)
    );
    SELECT RAISE(ABORT, 'Shares are frozen after any related invoice is issued')
    WHERE EXISTS (
        SELECT 1 FROM invoice i WHERE i.status = 'issued' AND
        (i.invoiceId IN (OLD.invoiceId, NEW.invoiceId) OR i.invoiceId IN (
            SELECT invoiceId FROM charge_share WHERE chargeId IN (OLD.chargeId, NEW.chargeId)
        ))
    );
END;

CREATE TRIGGER charge_share_delete_guard
BEFORE DELETE ON charge_share
WHEN EXISTS (
    SELECT 1 FROM charge_share s JOIN invoice i USING (invoiceId)
    WHERE s.chargeId = OLD.chargeId AND i.status = 'issued'
)
BEGIN
    SELECT RAISE(ABORT, 'Shares are frozen after any related invoice is issued');
END;

CREATE TRIGGER posted_charge_no_update
BEFORE UPDATE ON charge WHEN OLD.status = 'posted'
BEGIN
    SELECT RAISE(ABORT, 'Correct posted charges with adjustments');
END;

CREATE TRIGGER posted_charge_no_delete
BEFORE DELETE ON charge WHEN OLD.status = 'posted'
BEGIN
    SELECT RAISE(ABORT, 'Correct posted charges with adjustments');
END;

COMMIT;
