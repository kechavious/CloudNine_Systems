# Group 4 - Data dictionary
Canonical Milestone 1 schema: 50 tables. PK = primary key; FK = foreign key; UK = additional unique key. All fields required unless marked Yes. All money is USD; decimal amounts use fixed precision. Timestamps are UTC.

## Clients and people
### CLIENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| client_id | int | PK | No |
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
### CLIENT_RELATIONSHIP
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| relationship_id | int | PK | No |
| parent_client_id | int | FK -> CLIENT | No |
| child_client_id | int | FK -> CLIENT | No |
| relationship_type | text |  | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
### STAFF
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| staff_id | int | PK | No |
| user_id | int | UK; FK -> USER_ACCOUNT | No |
| staff_role | text |  | No |
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
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
### METRIC
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| metric_id | int | PK | No |
| name | text | UK | No |
| unit | text |  | No |
### CONFIGURATION_CAPACITY
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| configuration_id | int | PK; FK -> RESOURCE_CONFIGURATION | No |
| metric_id | int | PK; FK -> METRIC | No |
| capacity | decimal |  | No |
### RESOURCE_STATE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| state_id | int | PK | No |
| resource_id | int | FK -> RESOURCE | No |
| status | text |  | No |
| reason | text |  | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
| recorded_by_staff_id | int | FK -> STAFF | Yes |
### RESOURCE_RELATIONSHIP
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| relationship_id | int | PK | No |
| source_resource_id | int | FK -> RESOURCE | No |
| target_resource_id | int | FK -> RESOURCE | No |
| relationship_type | text |  | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
## Reservations and agreements
### CONTRACT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| contract_id | int | PK | No |
| client_id | int | FK -> CLIENT | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
| sla_note | text |  | No |
| priority_note | text |  | No |
### RESERVATION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_id | int | PK | No |
| client_id | int | FK -> CLIENT | No |
| created_at | timestamp |  | No |
| status | text |  | No |
### RESERVATION_CONTRACT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_id | int | PK; FK -> RESERVATION | No |
| contract_id | int | FK -> CONTRACT | No |
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
| approved_by_staff_id | int | FK -> STAFF | Yes |
### RESERVATION_ITEM
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_item_id | int | PK | No |
| revision_id | int | FK -> RESERVATION_REVISION | No |
| resource_type_id | int | FK -> RESOURCE_TYPE | No |
| quantity | int |  | No |
| preferred_region_id | int | FK -> REGION | Yes |
| preferred_zone_id | int | FK -> AVAILABILITY_ZONE | Yes |
| preferred_data_center_id | int | FK -> DATA_CENTER | Yes |
| location_mode | text |  | No |
### REQUIREMENT_CAPACITY
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_item_id | int | PK; FK -> RESERVATION_ITEM | No |
| metric_id | int | PK; FK -> METRIC | No |
| minimum_capacity | decimal |  | No |
### RESERVATION_SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| reservation_item_id | int | PK; FK -> RESERVATION_ITEM | No |
| service_id | int | PK; FK -> SERVICE | No |
| quantity | decimal |  | No |
### COMMITMENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| commitment_id | int | PK | No |
| reservation_id | int | FK -> RESERVATION | No |
| billing_account_id | int | FK -> BILLING_ACCOUNT | No |
| commitment_type | text |  | No |
| required_amount | decimal |  | No |
| status | text |  | No |
| terms_note | text |  | No |
## Deployment and consumption
### DEPLOYMENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| deployment_id | int | PK | No |
| reservation_id | int | FK -> RESERVATION | No |
| project_id | int | FK -> PROJECT | Yes |
| name | text |  | No |
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
### WORKLOAD
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| workload_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| name | text |  | No |
| workload_type | text |  | No |
### RESOURCE_ALLOCATION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| allocation_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| reservation_item_id | int | FK -> RESERVATION_ITEM | No |
| configuration_id | int | FK -> RESOURCE_CONFIGURATION | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
| allocation_status | text |  | No |
| supersedes_allocation_id | int | FK -> RESOURCE_ALLOCATION | Yes |
| change_reason | text |  | No |
| assigned_by_staff_id | int | FK -> STAFF | Yes |
### ALLOCATION_CAPACITY
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| allocation_id | int | PK; FK -> RESOURCE_ALLOCATION | No |
| metric_id | int | PK; FK -> METRIC | No |
| allocated_capacity | decimal |  | No |
### SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| service_id | int | PK | No |
| name | text | UK | No |
| service_type | text |  | No |
### RESOURCE_SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| resource_id | int | PK; FK -> RESOURCE | No |
| service_id | int | PK; FK -> SERVICE | No |
| valid_from | timestamp | PK | No |
| valid_to | timestamp |  | Yes |
### DEPLOYMENT_SERVICE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| deployment_service_id | int | PK | No |
| deployment_id | int | FK -> DEPLOYMENT | No |
| service_id | int | FK -> SERVICE | No |
| starts_at | timestamp |  | No |
| ends_at | timestamp |  | Yes |
### USAGE_RECORD
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| usage_id | int | PK | No |
| allocation_id | int | FK -> RESOURCE_ALLOCATION | Yes |
| deployment_service_id | int | FK -> DEPLOYMENT_SERVICE | Yes |
| metric_id | int | FK -> METRIC | No |
| quantity | decimal |  | No |
| period_start | timestamp |  | No |
| period_end | timestamp |  | No |
| record_type | text |  | No |
| recorded_at | timestamp |  | No |
| supersedes_usage_id | int | FK -> USAGE_RECORD | Yes |
## Pricing and charge allocation
### RATE_PLAN
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| rate_plan_id | int | PK | No |
| name | text | UK | No |
### RATE_RULE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| rate_rule_id | int | PK | No |
| rate_plan_id | int | FK -> RATE_PLAN | No |
| resource_type_id | int | FK -> RESOURCE_TYPE | Yes |
| service_id | int | FK -> SERVICE | Yes |
| region_id | int | FK -> REGION | Yes |
| metric_id | int | FK -> METRIC | No |
| performance_tier | text |  | Yes |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
| hour_start | int |  | Yes |
| hour_end | int |  | Yes |
| duration_min_hours | decimal |  | Yes |
| duration_max_hours | decimal |  | Yes |
| quantity_min | decimal |  | Yes |
| quantity_max | decimal |  | Yes |
| unit_price | decimal |  | No |
| discount_fraction | decimal |  | No |
| precedence | int |  | No |
### CONTRACT_RATE_PLAN
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| contract_id | int | PK; FK -> CONTRACT | No |
| valid_from | timestamp | PK | No |
| rate_plan_id | int | FK -> RATE_PLAN | No |
| valid_to | timestamp |  | Yes |
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
| client_id | int | FK -> CLIENT | Yes |
| project_id | int | FK -> PROJECT | Yes |
| deployment_id | int | FK -> DEPLOYMENT | Yes |
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
| deployment_id | int | FK -> DEPLOYMENT | No |
| adjustment_of_charge_id | int | FK -> CHARGE | Yes |
| authorized_by_staff_id | int | FK -> STAFF | Yes |
| charge_type | text |  | No |
| amount | decimal |  | No |
| status | text |  | No |
| reason | text |  | No |
| created_at | timestamp |  | No |
### CHARGE_USAGE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| charge_id | int | PK; FK -> CHARGE | No |
| usage_id | int | FK -> USAGE_RECORD | No |
| rate_rule_id | int | FK -> RATE_RULE | No |
### CHARGE_SHARE
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| charge_share_id | int | PK | No |
| charge_id | int | FK -> CHARGE | No |
| billing_account_id | int | FK -> BILLING_ACCOUNT | No |
| billing_rule_id | int | FK -> BILLING_RULE | Yes |
| allocated_amount | decimal |  | No |
## Invoices and payments
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
### PAYMENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| payment_id | int | PK | No |
| billing_account_id | int | FK -> BILLING_ACCOUNT | No |
| amount | decimal |  | No |
| payment_type | text |  | No |
| paid_at | timestamp |  | No |
| status | text |  | No |
| external_reference | text | UK | No |
### PAYMENT_APPLICATION
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| application_id | int | PK | No |
| payment_id | int | FK -> PAYMENT | No |
| invoice_id | int | FK -> INVOICE | Yes |
| commitment_id | int | FK -> COMMITMENT | Yes |
| applied_amount | decimal |  | No |
## Access and audit
### CREDENTIAL
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| credential_id | int | PK | No |
| user_id | int | FK -> USER_ACCOUNT | No |
| credential_type | text |  | No |
| credential_reference | text | UK | No |
| expires_at | timestamp |  | Yes |
| revoked_at | timestamp |  | Yes |
### ACCESS_GRANT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| grant_id | int | PK | No |
| user_id | int | FK -> USER_ACCOUNT | No |
| client_id | int | FK -> CLIENT | Yes |
| project_id | int | FK -> PROJECT | Yes |
| deployment_id | int | FK -> DEPLOYMENT | Yes |
| resource_id | int | FK -> RESOURCE | Yes |
| service_id | int | FK -> SERVICE | Yes |
| permission | text |  | No |
| valid_from | timestamp |  | No |
| valid_to | timestamp |  | Yes |
| granted_by_staff_id | int | FK -> STAFF | Yes |
### AUDIT_EVENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| audit_event_id | int | PK | No |
| actor_user_id | int | FK -> USER_ACCOUNT | Yes |
| reservation_id | int | FK -> RESERVATION | Yes |
| deployment_id | int | FK -> DEPLOYMENT | Yes |
| resource_id | int | FK -> RESOURCE | Yes |
| service_id | int | FK -> SERVICE | Yes |
| occurred_at | timestamp |  | No |
| action | text |  | No |
| result | text |  | No |
| details_note | text |  | No |
### AUTHENTICATION_EVENT
| Column | Type | Key / reference | Nullable |
|---|---|---|---|
| authentication_event_id | int | PK | No |
| credential_id | int | FK -> CREDENTIAL | Yes |
| attempted_identifier | text |  | Yes |
| occurred_at | timestamp |  | No |
| result | text |  | No |
