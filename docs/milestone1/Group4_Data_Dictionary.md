# Group 4 - Data dictionary
Canonical Milestone 1 schema: 30 tables. PK = primary key; FK = foreign key; UK = additional unique key. All fields required unless marked Yes. All money is USD; decimal amounts use fixed precision. Timestamps are UTC.

## Clients and people
### CLIENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| client_id | int | PK | No |
| parent_client_id | int | FK -> CLIENT | Yes |
| name | text |  | No |
| client_type | text |  | No |
| contact_email | text |  | No |
| qualification_note | text |  | Yes |
### USER_ACCOUNT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| user_id | int | PK | No |
| name | text |  | No |
| email | text | UK | No |
| account_kind | text |  | No |
| staff_role | text |  | Yes |
| status | text |  | No |
### CLIENT_MEMBERSHIP
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| membership_id | int | PK | No |
| client_id | int | FK -> CLIENT | No |
| user_id | int | FK -> USER_ACCOUNT | No |
| role | text |  | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
### PROJECT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| project_id | int | PK | No |
| client_id | int | FK -> CLIENT | No |
| name | text |  | No |
## Infrastructure and history
### REGION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| region_id | int | PK | No |
| name | text | UK | No |
| regulatory_note | text |  | No |
### AVAILABILITY_ZONE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| zone_id | int | PK | No |
| region_id | int | FK -> REGION | No |
| name | text |  | No |
| redundancy_note | text |  | No |
| connectivity_note | text |  | No |
### DATA_CENTER
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| data_center_id | int | PK | No |
| zone_id | int | FK -> AVAILABILITY_ZONE | No |
| name | text |  | No |
| location | text |  | No |
### RESOURCE_TYPE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| resource_type_id | int | PK | No |
| name | text | UK | No |
| intended_workload | text |  | No |
### RESOURCE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| resource_id | int | PK | No |
| resource_type_id | int | FK -> RESOURCE_TYPE | No |
| data_center_id | int | FK -> DATA_CENTER | No |
| local_identifier | text |  | No |
| is_logical | boolean |  | No |
### RESOURCE_CONFIGURATION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| configuration_id | int | PK | No |
| resource_id | int | FK -> RESOURCE | No |
| performance_tier | text |  | No |
| vcpu_count | int |  | No |
| memory_gib | decimal |  | No |
| storage_gib | decimal |  | No |
| network_gbps | decimal |  | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
### RESOURCE_STATE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| state_id | int | PK | No |
| resource_id | int | FK -> RESOURCE | No |
| status | text |  | No |
| reason | text |  | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
| recorded_by_user_id | int | FK -> USER_ACCOUNT | Yes |
### RESOURCE_RELATIONSHIP
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| relationship_id | int | PK | No |
| source_resource_id | int | FK -> RESOURCE | No |
| target_resource_id | int | FK -> RESOURCE | No |
| relationship_type | text |  | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
## Reservations and revisions
### RESERVATION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_id | int | PK | No |
| client_id | int | FK -> CLIENT | No |
| created_at | timestamp |  | No |
| status | text |  | No |
| agreement_note | text |  | Yes |
### RESERVATION_REVISION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| revision_id | int | PK | No |
| reservation_id | int | FK -> RESERVATION | No |
| revision_number | int |  | No |
| start_time | timestamp |  | No |
| end_time | timestamp |  | No |
| change_reason | text |  | No |
| created_at | timestamp |  | No |
| changed_by_user_id | int | FK -> USER_ACCOUNT | No |
| approved_by_user_id | int | FK -> USER_ACCOUNT | Yes |
### RESERVATION_ITEM
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_item_id | int | PK | No |
| revision_id | int | FK -> RESERVATION_REVISION | No |
| resource_type_id | int | FK -> RESOURCE_TYPE | No |
| quantity | int |  | No |
| min_vcpu | int |  | No |
| min_memory_gib | decimal |  | No |
| min_storage_gib | decimal |  | No |
| min_network_gbps | decimal |  | No |
| preferred_region_id | int | FK -> REGION | Yes |
| preferred_zone_id | int | FK -> AVAILABILITY_ZONE | Yes |
| preferred_data_center_id | int | FK -> DATA_CENTER | Yes |
| location_mode | text |  | No |
### RESERVATION_SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_item_id | int | PK; FK -> RESERVATION_ITEM | No |
| service_id | int | PK; FK -> SERVICE | No |
| quantity | decimal |  | No |
## Deployments and assignments
### DEPLOYMENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| deployment_id | int | PK | No |
| reservation_id | int | FK -> RESERVATION | No |
| project_id | int | FK -> PROJECT | Yes |
| name | text |  | No |
| workload_note | text |  | No |
| started_at | timestamp |  | Yes |
| ended_at | timestamp |  | Yes |
| confidentiality_level | text |  | No |
### DEPLOYMENT_EVENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| event_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| event_type | text |  | No |
| priority_after | int |  | Yes |
| scaling_mode_after | text |  | Yes |
| event_time | timestamp |  | No |
| reason | text |  | No |
| actor_user_id | int | FK -> USER_ACCOUNT | Yes |
### RESOURCE_ALLOCATION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| allocation_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| reservation_item_id | int | FK -> RESERVATION_ITEM | No |
| configuration_id | int | FK -> RESOURCE_CONFIGURATION | No |
| capacity_fraction | decimal |  | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
| allocation_status | text |  | No |
| supersedes_allocation_id | int | FK -> RESOURCE_ALLOCATION | Yes |
| change_reason | text |  | No |
| assigned_by_user_id | int | FK -> USER_ACCOUNT | Yes |
### DEPLOYMENT_SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| deployment_service_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| service_id | int | FK -> SERVICE | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
## Services, rates and metering
### SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| service_id | int | PK | No |
| name | text | UK | No |
| service_type | text |  | No |
| billing_unit | text |  | No |
### SERVICE_RATE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| service_rate_id | int | PK | No |
| service_id | int | FK -> SERVICE | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
| unit_price | decimal |  | No |
### USAGE_RECORD
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| usage_id | int | PK | No |
| deployment_service_id | int | FK -> DEPLOYMENT_SERVICE | No |
| allocation_id | int | FK -> RESOURCE_ALLOCATION | Yes |
| quantity | decimal |  | No |
| period_start | timestamp |  | No |
| period_end | timestamp |  | No |
| record_type | text |  | No |
| recorded_at | timestamp |  | No |
| supersedes_usage_id | int | UK; FK -> USAGE_RECORD | Yes |
## Billing and invoices
### BILLING_ACCOUNT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| billing_account_id | int | PK | No |
| responsible_client_id | int | FK -> CLIENT | No |
| name | text |  | No |
| billing_contact_user_id | int | FK -> USER_ACCOUNT | Yes |
### BILLING_RULE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| billing_rule_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
| rule_note | text |  | No |
### BILLING_RULE_SHARE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| billing_rule_id | int | PK; FK -> BILLING_RULE | No |
| billing_account_id | int | PK; FK -> BILLING_ACCOUNT | No |
| share_fraction | decimal |  | No |
### CHARGE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| charge_id | int | PK | No |
| usage_id | int | UK; FK -> USAGE_RECORD | Yes |
| deployment_service_id | int | FK -> DEPLOYMENT_SERVICE | Yes |
| service_rate_id | int | FK -> SERVICE_RATE | Yes |
| adjustment_of_charge_id | int | FK -> CHARGE | Yes |
| authorized_by_user_id | int | FK -> USER_ACCOUNT | Yes |
| charge_type | text |  | No |
| amount | decimal |  | No |
| status | text |  | No |
| reason | text |  | No |
| created_at | timestamp |  | No |
### CHARGE_SHARE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| charge_share_id | int | PK | No |
| charge_id | int | FK -> CHARGE | No |
| billing_account_id | int | FK -> BILLING_ACCOUNT | No |
| billing_rule_id | int | FK -> BILLING_RULE | Yes |
| allocated_amount | decimal |  | No |
### INVOICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| invoice_id | int | PK | No |
| billing_account_id | int | FK -> BILLING_ACCOUNT | No |
| issued_at | timestamp |  | No |
| due_at | timestamp |  | No |
| status | text |  | No |
### INVOICE_LINE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| charge_share_id | int | PK; FK -> CHARGE_SHARE | No |
| invoice_id | int | FK -> INVOICE | No |
