# Group 4 - ERD ownership views
20 tables; five tables per owner. Names will be mapped to A-D later.
![All 20 entities and relationships](../../output/svg/Group4_ERD_Overview.svg)
[Submission PDF](../../output/pdf/Group4_ERD.pdf) | [Analysis and constraints](Group4_Analysis_Draft.md)

## Member A: Clients and reservations
5 owned tables. Shaded boxes show primary keys of entities owned by another member.
![Member A ERD](../../output/svg/Group4_ERD_A.svg)

<details>
<summary>Editable Mermaid source</summary>

```mermaid
erDiagram
    direction LR
    client o|--o{ client : has child client
    client o|--o{ user_account : has
    client ||--o{ reservation : has
    user_account o|--o{ reservation : approves reservation
    reservation ||--o{ reservation_item : has
    resource_type ||--o{ reservation_item : classifies
    region o|--o{ reservation_item : is preferred by
    availability_zone o|--o{ reservation_item : is preferred by
    data_center o|--o{ reservation_item : is preferred by
    client ||--o{ billing_account : is responsible for
    user_account o|--o{ billing_account : is contact for
    client {
        int clientId PK
        int parentClientId FK "nullable"
        text name
        text clientType
        text contactEmail
        text qualificationNote "nullable"
    }
    user_account {
        int userId PK
        int clientId FK "nullable"
        text name
        text email
        text accountKind
        text staffRole "nullable"
        text status
    }
    reservation {
        int reservationId PK
        int clientId FK
        timestamp createdAt
        timestamp startTime
        timestamp endTime
        text status
        text agreementNote "nullable"
        int approvedByUserId FK "nullable"
    }
    reservation_item {
        int reservationItemId PK
        int reservationId FK
        int resourceTypeId FK
        int quantity
        int minVcpu
        decimal minMemoryGib
        decimal minStorageGib
        decimal minNetworkGbps
        int preferredRegionId FK "nullable"
        int preferredZoneId FK "nullable"
        int preferredDataCenterId FK "nullable"
        text locationMode
    }
    billing_account {
        int billingAccountId PK
        int responsibleClientId FK
        text name
        int billingContactUserId FK "nullable"
    }
    availability_zone {
        int zoneId PK
    }
    data_center {
        int dataCenterId PK
    }
    region {
        int regionId PK
    }
    resource_type {
        int resourceTypeId PK
    }
```
</details>

## Member B: Infrastructure
5 owned tables. Shaded boxes show primary keys of entities owned by another member.
![Member B ERD](../../output/svg/Group4_ERD_B.svg)

<details>
<summary>Editable Mermaid source</summary>

```mermaid
erDiagram
    direction LR
    region ||--o{ availability_zone : contains
    availability_zone ||--o{ data_center : contains
    resource_type ||--o{ resource : classifies
    data_center ||--o{ resource : hosts
    region {
        int regionId PK
        text name
        text regulatoryNote
    }
    availability_zone {
        int zoneId PK
        int regionId FK
        text name
        text redundancyNote
        text connectivityNote
    }
    data_center {
        int dataCenterId PK
        int zoneId FK
        text name
        text location
    }
    resource_type {
        int resourceTypeId PK
        text name
        text intendedWorkload
    }
    resource {
        int resourceId PK
        int resourceTypeId FK
        int dataCenterId FK
        text localIdentifier
        text performanceTier
        int vcpuCount
        decimal memoryGib
        decimal storageGib
        decimal networkGbps
    }
```
</details>

## Member C: Deployments and usage
5 owned tables. Shaded boxes show primary keys of entities owned by another member.
![Member C ERD](../../output/svg/Group4_ERD_C.svg)

<details>
<summary>Editable Mermaid source</summary>

```mermaid
erDiagram
    direction LR
    reservation ||--o{ deployment : has
    deployment ||--o{ resource_allocation : has
    reservation_item ||--o{ resource_allocation : is fulfilled by
    resource ||--o{ resource_allocation : has
    resource_allocation o|--o{ resource_allocation : is replaced by
    user_account o|--o{ resource_allocation : assigns allocation
    resource ||--o{ resource_state : has
    user_account o|--o{ resource_state : records resource state
    deployment ||--o{ deployment_service : has
    service ||--o{ deployment_service : has
    deployment_service ||--o{ usage_record : generates
    resource_allocation o|--o{ usage_record : supports
    usage_record o|--o| usage_record : is corrected by
    deployment {
        int deploymentId PK
        int reservationId FK
        text name
        text workloadNote
        timestamp startedAt "nullable"
        timestamp endedAt "nullable"
        text confidentialityLevel
        text status
        int priority
        text scalingMode
    }
    resource_allocation {
        int allocationId PK
        int deploymentId FK
        int reservationItemId FK
        int resourceId FK
        decimal capacityFraction
        timestamp startsAt
        timestamp endsAt "nullable"
        text allocationStatus
        int supersedesAllocationId FK "nullable"
        text changeReason
        int assignedByUserId FK "nullable"
    }
    resource_state {
        int stateId PK
        int resourceId FK
        text status
        text reason
        timestamp startsAt
        timestamp endsAt "nullable"
        int recordedByUserId FK "nullable"
    }
    deployment_service {
        int deploymentServiceId PK
        int deploymentId FK
        int serviceId FK
        timestamp startsAt
        timestamp endsAt "nullable"
    }
    usage_record {
        int usageId PK
        int deploymentServiceId FK
        int allocationId FK "nullable"
        decimal quantity
        timestamp periodStart
        timestamp periodEnd
        text recordType
        timestamp recordedAt
        int supersedesUsageId FK "nullable"
    }
    reservation {
        int reservationId PK
    }
    reservation_item {
        int reservationItemId PK
    }
    resource {
        int resourceId PK
    }
    service {
        int serviceId PK
    }
    user_account {
        int userId PK
    }
```
</details>

## Member D: Services and billing
5 owned tables. Shaded boxes show primary keys of entities owned by another member.
![Member D ERD](../../output/svg/Group4_ERD_D.svg)

<details>
<summary>Editable Mermaid source</summary>

```mermaid
erDiagram
    direction LR
    service ||--o{ service_rate : has
    usage_record o|--o| charge : produces
    deployment_service o|--o{ charge : generates
    service_rate o|--o{ charge : prices
    charge o|--o{ charge : has adjustment
    user_account o|--o{ charge : authorizes charge
    charge ||--o{ charge_share : is split into
    invoice ||--o{ charge_share : contains
    billing_account ||--o{ invoice : has
    service {
        int serviceId PK
        text name
        text serviceType
        text billingUnit
    }
    service_rate {
        int serviceRateId PK
        int serviceId FK
        timestamp validFrom
        timestamp validTo "nullable"
        decimal unitPrice
    }
    charge {
        int chargeId PK
        int usageId FK "nullable"
        int deploymentServiceId FK "nullable"
        int serviceRateId FK "nullable"
        int adjustmentOfChargeId FK "nullable"
        int authorizedByUserId FK "nullable"
        text chargeType
        decimal amount
        text status
        text reason
        timestamp createdAt
    }
    charge_share {
        int chargeShareId PK
        int chargeId FK
        int invoiceId FK
        decimal allocatedAmount
    }
    invoice {
        int invoiceId PK
        int billingAccountId FK
        timestamp issuedAt
        timestamp dueAt
        text status
    }
    billing_account {
        int billingAccountId PK
    }
    deployment_service {
        int deploymentServiceId PK
    }
    usage_record {
        int usageId PK
    }
    user_account {
        int userId PK
    }
```
</details>
