from pathlib import Path
import json, re, html, subprocess
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/milestone1'; OUT=ROOT/'output/pdf'; TMP=ROOT/'tmp/pdfs'
for p in (DOC,OUT,TMP): p.mkdir(parents=True,exist_ok=True)
# field:type; arrows identify the referenced PK; ? means nullable.
raw={
'Clients and people':{
'CLIENT':'client_id:int PK;name:text;client_type:text;contact_email:text;qualification_note:text?',
'USER_ACCOUNT':'user_id:int PK;name:text;email:text UK;status:text',
'CLIENT_MEMBERSHIP':'membership_id:int PK;client_id:int->CLIENT;user_id:int->USER_ACCOUNT;role:text;valid_from:timestamp;valid_to:timestamp?',
'CLIENT_RELATIONSHIP':'relationship_id:int PK;parent_client_id:int->CLIENT;child_client_id:int->CLIENT;relationship_type:text;valid_from:timestamp;valid_to:timestamp?',
'STAFF':'staff_id:int PK;user_id:int->USER_ACCOUNT UK;staff_role:text',
'PROJECT':'project_id:int PK;client_id:int->CLIENT;name:text',
},
'Infrastructure and history':{
'REGION':'region_id:int PK;name:text UK;regulatory_note:text',
'AVAILABILITY_ZONE':'zone_id:int PK;region_id:int->REGION;name:text;redundancy_note:text;connectivity_note:text',
'DATA_CENTER':'data_center_id:int PK;zone_id:int->AVAILABILITY_ZONE;name:text;location:text',
'RESOURCE_TYPE':'resource_type_id:int PK;name:text UK;intended_workload:text',
'RESOURCE':'resource_id:int PK;resource_type_id:int->RESOURCE_TYPE;data_center_id:int->DATA_CENTER;local_identifier:text;is_logical:boolean',
'RESOURCE_CONFIGURATION':'configuration_id:int PK;resource_id:int->RESOURCE;performance_tier:text;valid_from:timestamp;valid_to:timestamp?',
'METRIC':'metric_id:int PK;name:text UK;unit:text',
'CONFIGURATION_CAPACITY':'configuration_id:int PK->RESOURCE_CONFIGURATION;metric_id:int PK->METRIC;capacity:decimal',
'RESOURCE_STATE':'state_id:int PK;resource_id:int->RESOURCE;status:text;reason:text;starts_at:timestamp;ends_at:timestamp?;recorded_by_staff_id:int->STAFF?',
'RESOURCE_RELATIONSHIP':'relationship_id:int PK;source_resource_id:int->RESOURCE;target_resource_id:int->RESOURCE;relationship_type:text;valid_from:timestamp;valid_to:timestamp?',
},
'Reservations and agreements':{
'CONTRACT':'contract_id:int PK;client_id:int->CLIENT;starts_at:timestamp;ends_at:timestamp?;sla_note:text;priority_note:text',
'RESERVATION':'reservation_id:int PK;client_id:int->CLIENT;created_at:timestamp;status:text',
'RESERVATION_CONTRACT':'reservation_id:int PK->RESERVATION;contract_id:int->CONTRACT',
'RESERVATION_REVISION':'revision_id:int PK;reservation_id:int->RESERVATION;revision_number:int;start_time:timestamp;end_time:timestamp;change_reason:text;created_at:timestamp;changed_by_user_id:int->USER_ACCOUNT;approved_by_staff_id:int->STAFF?',
'RESERVATION_ITEM':'reservation_item_id:int PK;revision_id:int->RESERVATION_REVISION;resource_type_id:int->RESOURCE_TYPE;quantity:int;preferred_region_id:int->REGION?;preferred_zone_id:int->AVAILABILITY_ZONE?;preferred_data_center_id:int->DATA_CENTER?;location_mode:text',
'REQUIREMENT_CAPACITY':'reservation_item_id:int PK->RESERVATION_ITEM;metric_id:int PK->METRIC;minimum_capacity:decimal',
'RESERVATION_SERVICE':'reservation_item_id:int PK->RESERVATION_ITEM;service_id:int PK->SERVICE;quantity:decimal',
'COMMITMENT':'commitment_id:int PK;reservation_id:int->RESERVATION;billing_account_id:int->BILLING_ACCOUNT;commitment_type:text;required_amount:decimal;status:text;terms_note:text',
},
'Deployment and consumption':{
'DEPLOYMENT':'deployment_id:int PK;reservation_id:int->RESERVATION;project_id:int->PROJECT?;name:text;started_at:timestamp?;ended_at:timestamp?;confidentiality_level:text',
'DEPLOYMENT_EVENT':'event_id:int PK;deployment_id:int->DEPLOYMENT;event_type:text;priority_after:int?;scaling_mode_after:text?;event_time:timestamp;reason:text;actor_user_id:int->USER_ACCOUNT?',
'WORKLOAD':'workload_id:int PK;deployment_id:int->DEPLOYMENT;name:text;workload_type:text',
'RESOURCE_ALLOCATION':'allocation_id:int PK;deployment_id:int->DEPLOYMENT;reservation_item_id:int->RESERVATION_ITEM;configuration_id:int->RESOURCE_CONFIGURATION;starts_at:timestamp;ends_at:timestamp?;allocation_status:text;supersedes_allocation_id:int->RESOURCE_ALLOCATION?;change_reason:text;assigned_by_staff_id:int->STAFF?',
'ALLOCATION_CAPACITY':'allocation_id:int PK->RESOURCE_ALLOCATION;metric_id:int PK->METRIC;allocated_capacity:decimal',
'SERVICE':'service_id:int PK;name:text UK;service_type:text',
'RESOURCE_SERVICE':'resource_id:int PK->RESOURCE;service_id:int PK->SERVICE;valid_from:timestamp PK;valid_to:timestamp?',
'DEPLOYMENT_SERVICE':'deployment_service_id:int PK;deployment_id:int->DEPLOYMENT;service_id:int->SERVICE;starts_at:timestamp;ends_at:timestamp?',
'USAGE_RECORD':'usage_id:int PK;allocation_id:int->RESOURCE_ALLOCATION?;deployment_service_id:int->DEPLOYMENT_SERVICE?;metric_id:int->METRIC;quantity:decimal;period_start:timestamp;period_end:timestamp;record_type:text;recorded_at:timestamp;supersedes_usage_id:int->USAGE_RECORD?',
},
'Pricing and charge allocation':{
'RATE_PLAN':'rate_plan_id:int PK;name:text UK',
'RATE_RULE':'rate_rule_id:int PK;rate_plan_id:int->RATE_PLAN;resource_type_id:int->RESOURCE_TYPE?;service_id:int->SERVICE?;region_id:int->REGION?;metric_id:int->METRIC;performance_tier:text?;valid_from:timestamp;valid_to:timestamp?;hour_start:int?;hour_end:int?;duration_min_hours:decimal?;duration_max_hours:decimal?;quantity_min:decimal?;quantity_max:decimal?;unit_price:decimal;discount_fraction:decimal;precedence:int',
'CONTRACT_RATE_PLAN':'contract_id:int PK->CONTRACT;valid_from:timestamp PK;rate_plan_id:int->RATE_PLAN;valid_to:timestamp?',
'BILLING_ACCOUNT':'billing_account_id:int PK;responsible_client_id:int->CLIENT;name:text;billing_contact_user_id:int->USER_ACCOUNT?',
'BILLING_RULE':'billing_rule_id:int PK;client_id:int->CLIENT?;project_id:int->PROJECT?;deployment_id:int->DEPLOYMENT?;valid_from:timestamp;valid_to:timestamp?;rule_note:text',
'BILLING_RULE_SHARE':'billing_rule_id:int PK->BILLING_RULE;billing_account_id:int PK->BILLING_ACCOUNT;share_fraction:decimal',
'CHARGE':'charge_id:int PK;deployment_id:int->DEPLOYMENT;adjustment_of_charge_id:int->CHARGE?;authorized_by_staff_id:int->STAFF?;charge_type:text;amount:decimal;status:text;reason:text;created_at:timestamp',
'CHARGE_USAGE':'charge_id:int PK->CHARGE;usage_id:int->USAGE_RECORD;rate_rule_id:int->RATE_RULE',
'CHARGE_SHARE':'charge_share_id:int PK;charge_id:int->CHARGE;billing_account_id:int->BILLING_ACCOUNT;billing_rule_id:int->BILLING_RULE?;allocated_amount:decimal',
},
'Invoices and payments':{
'INVOICE':'invoice_id:int PK;billing_account_id:int->BILLING_ACCOUNT;issued_at:timestamp;due_at:timestamp;status:text',
'INVOICE_LINE':'charge_share_id:int PK->CHARGE_SHARE;invoice_id:int->INVOICE',
'PAYMENT':'payment_id:int PK;billing_account_id:int->BILLING_ACCOUNT;amount:decimal;payment_type:text;paid_at:timestamp;status:text;external_reference:text UK',
'PAYMENT_APPLICATION':'application_id:int PK;payment_id:int->PAYMENT;invoice_id:int->INVOICE?;commitment_id:int->COMMITMENT?;applied_amount:decimal',
},
'Access and audit':{
'CREDENTIAL':'credential_id:int PK;user_id:int->USER_ACCOUNT;credential_type:text;credential_reference:text UK;expires_at:timestamp?;revoked_at:timestamp?',
'ACCESS_GRANT':'grant_id:int PK;user_id:int->USER_ACCOUNT;client_id:int->CLIENT?;project_id:int->PROJECT?;deployment_id:int->DEPLOYMENT?;resource_id:int->RESOURCE?;service_id:int->SERVICE?;permission:text;valid_from:timestamp;valid_to:timestamp?;granted_by_staff_id:int->STAFF?',
'AUDIT_EVENT':'audit_event_id:int PK;actor_user_id:int->USER_ACCOUNT?;reservation_id:int->RESERVATION?;deployment_id:int->DEPLOYMENT?;resource_id:int->RESOURCE?;service_id:int->SERVICE?;occurred_at:timestamp;action:text;result:text;details_note:text',
'AUTHENTICATION_EVENT':'authentication_event_id:int PK;credential_id:int->CREDENTIAL?;attempted_identifier:text?;occurred_at:timestamp;result:text',
}}
schema={}; modules={}
for module,tables in raw.items():
 modules[module]=list(tables)
 for name,fields in tables.items():
  schema[name]=[]
  for f in fields.split(';'):
   field,desc=f.split(':'); target=None
   if '->' in desc:
    desc,target=desc.split('->'); target=target.replace(' UK',''); target=target.rstrip('?')
   schema[name].append(dict(name=field,type=desc.split()[0].rstrip('?'),pk='PK' in desc,fk=target,nullable='?' in f,unique='UK' in f))
for name,fs in schema.items():
 assert any(f['pk'] for f in fs),name
 for f in fs:
  assert not f['fk'] or f['fk'] in schema,(name,f)
  assert not (f['pk'] and f['nullable'])
N=len(schema)
(DOC/'Group4_Schema.json').write_text(json.dumps(dict(modules=modules,tables=schema),indent=2)+'\n')
lines=['erDiagram','    direction LR']
for name,fs in schema.items():
 for f in fs:
  if f['fk']:
   left='o|' if f['nullable'] else '||'
   right='o|' if f['unique'] or (f['pk'] and sum(x['pk'] for x in fs)==1) else 'o{'
   lines.append(f'    {f["fk"]} {left}--{right} {name} : {f["name"]}')
for name,fs in schema.items():
 lines.append(f'    {name} {{')
 for f in fs:
  flags=', '.join(x for x,b in [('PK',f['pk']),('FK',bool(f['fk'])),('UK',f['unique'])] if b)
  lines.append(f'        {f["type"]} {f["name"]}'+(' '+flags if flags else '')+(' "nullable"' if f['nullable'] else ''))
 lines.append('    }')
(DOC/'Group4_ERD.mmd').write_text('\n'.join(lines)+'\n')
dictlines=['# Group 4 - Data dictionary',f'Canonical Milestone 1 schema: {N} tables. PK = primary key; FK = foreign key; UK = additional unique key. All fields required unless marked Yes. All money is USD; decimal amounts use fixed precision. Timestamps are UTC.\n']
for module,names in modules.items():
 dictlines.append('## '+module)
 for name in names:
  dictlines.extend(['### '+name,'| Column | Type | Key / reference | Nullable |','|---|---|---|---|'])
  for f in schema[name]:
   flags=[]
   if f['pk']: flags.append('PK')
   if f['unique']: flags.append('UK')
   if f['fk']: flags.append('FK -> '+f['fk'])
   dictlines.append(f'| {f["name"]} | {f["type"]} | {"; ".join(flags)} | {"Yes" if f["nullable"] else "No"} |')
(DOC/'Group4_Data_Dictionary.md').write_text('\n'.join(dictlines)+'\n')
# Render module diagrams with real entity fields, FK relationships, and multiplicities.
for i,(module,names) in enumerate(modules.items(),1):
 external=sorted({f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names})
 dot=['digraph G {','graph [rankdir=LR, bgcolor="white", nodesep=0.4, ranksep=1.0, splines=polyline, pad=0.2];','node [shape=plain, fontname="Helvetica"];','edge [fontname="Helvetica", fontsize=8, color="#64748b", arrowsize=0.7];']
 for name in names+external:
  ext=name in external; fs=[f for f in schema[name] if f['pk']] if ext else schema[name]
  title=name+(' (reference)' if ext else '')
  rows=[f'<TR><TD COLSPAN="2" BGCOLOR="{"#64748b" if ext else "#16324f"}"><FONT COLOR="white"><B>{title}</B></FONT></TD></TR>']
  for f in fs:
   key='/'.join(k for k,b in [('PK',f['pk']),('FK',bool(f['fk'])),('UK',f['unique'])] if b)
   rows.append(f'<TR><TD ALIGN="LEFT">{key}</TD><TD ALIGN="LEFT">{f["name"]}: {f["type"]}{" ?" if f["nullable"] else ""}</TD></TR>')
  dot.append(f'{name} [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5">'+''.join(rows)+'</TABLE>>];')
 for name in names:
  for f in schema[name]:
   if f['fk']:
    child='0..1' if f['unique'] or (f['pk'] and sum(x['pk'] for x in schema[name])==1) else '0..*'
    parent='0..1' if f['nullable'] else '1'
    dot.append(f'{f["fk"]} -> {name} [dir=none, taillabel="{parent}", headlabel="{child}", label="{f["name"]}", style="{"dashed" if f["fk"] in external else "solid"}"];')
 dot.append('}')
 (TMP/f'module{i}.dot').write_text('\n'.join(dot))
node='''const fs=require('fs'); const {instance}=require('/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@viz-js/viz'); (async()=>{const v=await instance();for(let i=1;i<=7;i++){const p=process.argv[1]+'/module'+i;fs.writeFileSync(p+'.svg',v.renderString(fs.readFileSync(p+'.dot','utf8'),{format:'svg'}));}})();'''
subprocess.run(['/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','-e',node,str(TMP)],check=True)
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=8,textColor=colors.HexColor('#243247')))
styles.add(ParagraphStyle(name='TitleCustom',fontName='Helvetica-Bold',fontSize=23,leading=28,spaceAfter=16,textColor=colors.HexColor('#16324f')))
styles.add(ParagraphStyle(name='SubCustom',fontName='Helvetica-Bold',fontSize=13,leading=17,spaceBefore=14,spaceAfter=7,textColor=colors.HexColor('#16324f')))
def footer(c,d):
 c.setFont('Helvetica',8); c.setFillColor(colors.HexColor('#64748b')); c.drawString(48,28,'GROUP 4 | CLOUDNINE SYSTEMS | MILESTONE 1'); c.drawRightString(letter[0]-48,28,str(d.page))
def pdf_text(md,path):
 story=[]
 for line in md.splitlines():
  if not line.strip(): continue
  if line.startswith('# '): style='TitleCustom'; line=line[2:]
  elif line.startswith('## '): style='SubCustom'; line=line[3:]
  else: style='BodyCustom'
  line=html.escape(line)
  line=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',line)
  story.append(Paragraph(line,styles[style]))
 SimpleDocTemplate(str(path),pagesize=letter,rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=48).build(story,onFirstPage=footer,onLaterPages=footer)
# ERD: cover + seven detailed, vector module pages. Page dimensions preserve legibility.
c=canvas.Canvas(str(OUT/'Group4_ERD.pdf'),pagesize=letter)
c.setTitle('Group 4 - CloudNine Systems - 3NF ERD')
c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',26);c.drawString(48,710,'CloudNine Systems');c.setFont('Helvetica-Bold',18);c.drawString(48,680,'Group 4 | Milestone 1 ERD')
intro=[f'{N} tables organized into seven connected modules.','Logical relational design in Third Normal Form (3NF).','Each module page shows all owned attributes and incoming FK relationships.','Gray entities are references to tables fully defined on another module page.','Relationship ends: 1 = required parent; 0..1 = optional parent;','0..* = zero or more children; 0..1 child = unique foreign key.','PK = primary key; FK = foreign key; UK = additional unique key.','? means nullable. Composite PKs are marked on every participating column.','Minimum child counts are enforced by lifecycle rules, not by ordinary FKs.','XOR, time interval, capacity and accounting rules appear in the analysis report.','All monetary values are USD. All timestamps are UTC.','The editable Mermaid and JSON sources accompany this PDF.']
y=640
for line in intro:
 c.setFont('Helvetica',10);c.drawString(48,y,line);y-=21
for i,module in enumerate(modules,1):
 c.setFont('Helvetica',11);c.drawString(48,y,f'{i+1}. {module}');y-=22
c.setFont('Helvetica',8);c.drawString(48,30,'GROUP 4 | DESIGN DRAFT | Team roster and adoption pending');c.showPage()
for i,module in enumerate(modules,1):
 d=svg2rlg(str(TMP/f'module{i}.svg'))
 w=max(792,d.width+72);h=max(612,d.height+120)
 c.setPageSize((w,h));c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',20);c.drawString(36,h-35,f'{i}. {module}')
 c.setFont('Helvetica',10);c.drawString(36,h-55,'PK / FK / UK | ? nullable | Gray = external reference | Edge labels give multiplicity at each end')
 renderPDF.draw(d,c,(w-d.width)/2,45)
 c.setFont('Helvetica',9);c.drawString(36,22,f'Group 4 | CloudNine Systems | ERD page {i+1} of 8');c.showPage()
c.save()
report=f'''# Group 4 - CloudNine Systems
## Milestone 1: Draft Analysis Report
Status: proposed design for team review. Prepared October 10, 2026. The team statement contains role slots because the confirmed roster has not been supplied.
## 1. Speculative scenario and organizational problem
CloudNine Systems is a fictional cloud infrastructure provider serving individuals, teams, and organizations. It operates resources in multiple facilities and geographic regions. Clients reserve capacity in advance, run deployments, change their workloads, and pay for compute and ancillary services. Staff coordinate availability, substitutions, support, and billing.
The proposed information system connects requests, actual assignments, measured consumption, and financial responsibility. It should answer who is using a resource at a given time, whether future commitments can be met, how changes affected consumption, and why each account was charged. The project uses synthetic records, not real customer or credential data.
## 2. Scope and organizational schema
The canonical design has {N} tables across seven modules. The ERD PDF, Mermaid source, JSON schema, and data dictionary describe the same design. Earlier ERD files in docs/ are retained as historical proposals and are not the Milestone 1 submission.
Clients and people: CLIENT represents an individual, team, or organization; USER_ACCOUNT represents a person. CLIENT_MEMBERSHIP stores a person's role over time, while CLIENT_RELATIONSHIP represents organizational and departmental relationships. STAFF extends a user with an operations role. PROJECT groups a client's work. Resource users and the parties responsible for payment are separate concepts.
Infrastructure and history: REGION, AVAILABILITY_ZONE, and DATA_CENTER form a geographic hierarchy. RESOURCE_TYPE describes intended use; RESOURCE identifies independently managed physical or logical assets. RESOURCE_CONFIGURATION and CONFIGURATION_CAPACITY retain changing tiers and numeric capacities. METRIC defines canonical measurement units. RESOURCE_STATE records operational availability, and RESOURCE_RELATIONSHIP records components and dependencies with validity intervals.
Reservations and agreements: RESERVATION identifies the requesting client. RESERVATION_REVISION preserves complete successive request versions. Each version contains RESERVATION_ITEM records, numeric REQUIREMENT_CAPACITY values, and requested RESERVATION_SERVICE records. CONTRACT records agreement terms; RESERVATION_CONTRACT links the applicable agreement without duplicating the agreement's client in the reservation row. COMMITMENT represents deposits and advance commitments.
Deployment and consumption: DEPLOYMENT represents actual activity associated with a reservation and optionally a project. WORKLOAD describes its workloads. RESOURCE_ALLOCATION assigns a specific configuration over an interval; its resource is obtained through that configuration. ALLOCATION_CAPACITY records reserved numeric capacity. DEPLOYMENT_EVENT captures start, stop, pause, resume, scaling, migration, priority and mode changes. SERVICE, RESOURCE_SERVICE and DEPLOYMENT_SERVICE describe ancillary offerings and provisioning. USAGE_RECORD distinguishes estimated from actual metering and retains corrections.
Pricing and charge allocation: RATE_PLAN and effective-dated RATE_RULE records represent resource or service prices, metric units, geographic and tier restrictions, time windows, duration and quantity brackets, and fixed fractional discounts. CONTRACT_RATE_PLAN records which plan applies to an agreement over time. BILLING_ACCOUNT identifies the payer and contact. BILLING_RULE and BILLING_RULE_SHARE define effective sharing agreements. CHARGE records a deployment's monetary obligation or adjustment. CHARGE_USAGE links a metered charge to its measurement and rate. CHARGE_SHARE preserves the actual allocation to payers.
Invoices and payments: INVOICE groups finalized allocated charges for one billing account. INVOICE_LINE associates each charge share with at most one invoice. PAYMENT records receipts or refunds, and PAYMENT_APPLICATION applies a receipt to invoices or deposits. Totals and outstanding balances are derived rather than copied into parent tables.
Access and audit: CREDENTIAL stores only a secure reference or password hash. ACCESS_GRANT defines time-limited permissions on one scope. AUDIT_EVENT captures operational actions and their affected objects. AUTHENTICATION_EVENT separately records successful or failed credential attempts; the credential's owner is derived rather than redundantly stored as an actor.
## 3. Principal design decisions
Reservation is distinct from allocation: a client can reserve a type and capacity without choosing a physical resource. An unassigned request remains a reservation item. Once a specific configuration is chosen, a planned allocation can be created. Several deployments can draw on one reservation, and each deployment can use resources across zones.
History is retained: a reservation change creates a new revision; reconfiguration creates a new configuration interval; migration closes an allocation and creates a replacement. Changes carry reasons and actors where applicable. This supports later explanations of substitutions and billing disputes.
A logical cluster is a RESOURCE with component relationships. Its administrative data center does not imply that every component occupies that center. Allocation checks expand active component relationships so that allocating a cluster and one of its dedicated components cannot consume the same capacity twice. Shared service capacity may be divided explicitly across allocations.
Operational state is separate from occupancy. A resource may be operational while reserved for tomorrow or in use today. Occupancy is derived from allocation intervals; maintenance and failure are represented in RESOURCE_STATE. Forecasts combine unassigned reservation requirements, planned allocations and operational intervals without counting an assigned requirement twice.
Financial records are historical facts. Rate and sharing changes create new effective versions. Finalized charges and their account shares are immutable; corrections use separately authorized adjustments. A final monetary amount is retained as a posted accounting fact, not treated as a continuously recalculated copy of a formula.
## 4. Assumptions and integrity constraints
A1. Each facility belongs to one zone and each zone to one region. A resource has one administrative home. Individual users, teams and organizations are client categories; roles and qualifications are assessed manually and documented rather than generated by a scoring engine.
A2. All money is USD and all timestamps are UTC. Effective intervals are half-open [start, end); null end means open-ended. End must exceed start. No real credentials, secrets or personal records are included in example data.
A3. Every published reservation revision has at least one item. Revision numbers are unique within a reservation. Approval determines which revision is operational; the highest approved revision is current, with cancellation handled by reservation status. Items from earlier revisions remain for historical allocations. Staff must explicitly resolve affected future allocations after a revision is approved.
A4. A reservation item may specify at most one location level: region, zone, or data center. Broader locations are derived from the selected level. location_mode is required or preferred; substitutions outside mandatory constraints require a newly approved revision. This avoids redundant stored region and zone identifiers.
A5. Every allocation references exactly one configuration, including planned assignments. The configuration determines the resource, so RESOURCE_ALLOCATION does not repeat resource_id. Its configuration interval must cover the allocation interval. Allocations must satisfy their reservation's approved requirements; their item's reservation must equal the deployment's reservation.
A6. Current configuration and operational-state intervals must not overlap for a resource. Overlapping allocations cannot exceed each capacity metric, and exclusive resources cannot overlap at all. Maintenance and failure intervals block affected capacity. Dependencies and component relationships prohibit self-links and cycles where the relationship semantics require an acyclic graph.
A7. Each usage row references exactly one of allocation_id and deployment_service_id. The metric defines its unit. Quantities are nonnegative; intervals must fall within the referenced allocation or service interval. Corrections create new records linked by supersedes_usage_id and cannot form cycles. Only the latest actual record in a correction chain contributes to finalized usage billing; estimates are displayed separately.
A8. Each rate rule targets exactly one resource type or service. Optional region, tier, hour window, duration bracket and quantity bracket constrain its applicability. Hours use UTC and range from 0 through 23; overnight windows are split into two rules. Numeric bounds are inclusive at the lower end and exclusive at the upper end. Discount fractions lie between 0 and 1. More specific rules receive a higher explicit precedence; equal-precedence competing matches are rejected. Time or threshold crossings are split into separate priced usage slices. Complex bundle eligibility is reviewed manually; its approved discount is represented by an applicable contract plan or an authorized credit.
A9. Each billing rule has exactly one populated scope: client, project or deployment. Effective rules at the same scope cannot overlap. Precedence is deployment, then project, then client. Shares must be positive and total 1. A missing rule requires an explicitly assigned responsible account before a charge is finalized. Cross-organization payment is allowed when authorized, while the project's owning client must match the reservation client.
A10. Ordinary usage charges have exactly one CHARGE_USAGE link; the associated usage must belong to the charge's deployment, and its rate must match the metric and context. Final usage charges require actual records. Provisional charges do not enter invoices. Surcharges and credits require a staff authorizer and a reason. Credits have negative amounts, reference the original charge where applicable, and affect the same deployment. Account shares sum exactly to the posted amount; any rounding residual is assigned deterministically to the largest share.
A11. Invoice lines may reference only final charge shares for the invoice's account. A share appears on at most one invoice. PAYMENT stores a positive amount and payment_type distinguishes receipt from refund. PAYMENT_APPLICATION references exactly one invoice or commitment, matches the payment account, and has a positive amount. Posted applications cannot exceed the payment amount or the target balance. A refund reverses settlement through an audited transaction. Using a funded deposit on an invoice transfers its application atomically instead of counting it twice.
A12. ACCESS_GRANT populates exactly one scope FK. Access is deny-by-default; explicit user permissions are checked at query boundaries. Credentials contain secure references or password hashes, never raw passwords, tokens or private keys. Human operational events require an actor; automated events may omit one. Authentication failures may have no recognized credential.
A13. Alternate keys include USER_ACCOUNT.email; STAFF.user_id; REGION.name; RESOURCE_TYPE.name; METRIC.name; SERVICE.name; RATE_PLAN.name; CREDENTIAL.credential_reference; PAYMENT.external_reference; RESOURCE(data_center_id, local_identifier); AVAILABILITY_ZONE(region_id, name); DATA_CENTER(zone_id, name); RESERVATION_REVISION(reservation_id, revision_number); CHARGE_SHARE(charge_id, billing_account_id); and CONFIGURATION_CAPACITY(configuration_id, metric_id). Composite primary keys shown in the ERD also enforce uniqueness. Membership and relationship intervals for the same pair and role/type cannot overlap.
A14. Each metric name includes its measurement basis, such as vCPU count, memory capacity in GiB, compute consumption in vCPU-hours or storage consumption in GiB-hours. Unit is a property of the metric. Capacity and consumption metrics are distinct; no implicit unit conversions occur. Metering-to-capacity conversion rules will be documented with the synthetic dataset.
Ordinary PK, FK, UNIQUE and row CHECK constraints enforce local rules. Interval overlap, capacity sums, share totals, mandatory child counts, ownership consistency and lifecycle changes require transactional application checks or database triggers. These are implementation requirements, not claims that a diagram alone enforces them.
## 5. Third Normal Form rationale
The declared dependencies are the primary or alternate keys determining the remaining attributes of each relation. No other non-key determinants are assumed unless explicitly described below. Scalar notes record one explanatory fact; they are not substitutes for lists of resources, capacities, members or prices.
1NF: every column contains one value. Repeating capacities are separated into CONFIGURATION_CAPACITY, REQUIREMENT_CAPACITY and ALLOCATION_CAPACITY. Members, dependencies, services and billing recipients occupy separate rows rather than arrays or comma-separated lists.
2NF: tables with composite keys store attributes of the entire association. For example, (configuration_id, metric_id) determines capacity; neither identifier alone does. (billing_rule_id, billing_account_id) determines share_fraction. RESOURCE_SERVICE's validity interval belongs to the resource-service-start association. There are no attributes depending only on part of a composite primary key.
3NF: geographical names and parents are stored once in REGION, AVAILABILITY_ZONE and DATA_CENTER. RESOURCE stores only its facility FK. METRIC stores unit; measurements and capacities do not repeat it. An allocation stores configuration_id without resource_id, avoiding configuration_id determining resource_id within the allocation relation. Reservation location columns are mutually exclusive, avoiding a stored facility-to-zone-to-region chain.
RESERVATION_CONTRACT separates agreement selection from the reservation's client. INVOICE_LINE separates invoice membership from CHARGE_SHARE, avoiding invoice_id determining a repeated billing_account_id in that relation. AUTHENTICATION_EVENT derives the owner from CREDENTIAL rather than storing both credential and owner. BILLING_RULE has one scope, so it does not copy client identifiers derivable from project or deployment scope.
CHARGE_USAGE is separated from CHARGE so the charge row does not copy the deployment derivable from a usage reference. A rate rule does not uniquely determine a charge amount: actual posted amounts can reflect authorized adjustments and rounding. Charge amounts and allocated amounts are immutable financial facts. Recalculated totals, availability flags, current priority and account balances are views, not independently maintained columns.
Under these declared dependencies and XOR rules, the proposed relations satisfy 3NF. Adding new business dependencies during implementation requires repeating the normalization review; introducing surrogate IDs alone would not establish 3NF.
## 6. Requirements coverage and limitations
Resource types, capacity, tiers and geography map to infrastructure tables. Reconfiguration, dependencies, clustered units, shared services and operational availability map to effective histories and relationships. Advance requests, modifications, delayed assignments and substitutions map to reservation revisions and allocation history. Workloads, scaling, migration, priority and pause/resume map to deployment events, allocations and usage records.
Responsible parties, cost centers, split bills, changing rates, deposits, provisional estimates, surcharges, credits, payments and refunds map to the billing modules and associated integrity rules. Staff contacts, memberships, confidential deployments and operational accountability map to people, access grants and event logs.
The system will support a resource dependency view from RESOURCE_RELATIONSHIP; an interactive zoomable topology is deferred. Allocation optimization, automatic scaling, contractual interpretation, fairness scoring and live metering collection are outside the course implementation. The database retains their decisions and results. SLA and qualification notes are explanatory text; automated evaluation of those terms is not claimed. Service options requiring distinct rates will be modeled as distinct SERVICE offerings; arbitrary nested option documents are excluded.
The web interface can display one or two read-only pages. Authentication infrastructure is not required for this milestone; access metadata remains in the schema because the organizational scenario includes confidentiality. Later work will use at least one quarter of synthetic activity and target eight meaningful aggregate or multi-table queries, covering capacity forecasts, utilization, migration frequency, estimate-versus-actual differences, spending, credits, cost sharing, and outstanding balances. These are plans, not implemented deliverables.
## 7. Team planning and next steps
The accompanying team statement defines role slots, rotating reviews, workload tracking and support procedures. Actual names, availability and acceptance are pending team confirmation. Before submission, each member should explain one end-to-end example from reservation through deployment and billing, review the assumptions, and confirm repository access. Next, the team will select the course DBMS, translate the logical schema into DDL, validate constraints, generate a realistic dataset and implement queries.
## Source basis
Course handouts: Group Project - DB.pdf, seven pages; Group Project_ CloudNine Systems.pdf, five pages. The handouts define the organizational scenario and project expectations. Table names, dependencies, assumptions and scope decisions in this report are this proposed design's interpretation. Milestone 1 follows the three deliverables supplied in the assignment prompt.
'''
team='''# Group 4 - Team Statement
## Milestone 1: Shared understanding and work plan
Status: proposed agreement for member review. Roster, assignments and adoption have not yet been confirmed. This document records the intended process; it does not claim that meetings, reviews or equal contributions have already occurred.
## Shared understanding
We propose to build a database-backed information system for CloudNine Systems. Its purpose is to connect client requests, infrastructure availability, deployment changes, measured usage and financial responsibility. We distinguish requested capacity from actual assignment, resource users from payers, and estimates from finalized charges. We will prioritize a coherent 3NF schema and explain assumptions and limitations.
For Milestone 1, our shared repository will contain the ERD PDF, draft analysis report and this team statement. Each member will review the full design and be able to explain a reservation-to-invoice example, rather than understanding only an assigned section.
## Roster and equitable division
The following four slots are provisional work packages, not a confirmed member count. Replace them with actual names and redistribute if the group has a different size.
Member A: [name pending]. Lead clients, memberships, projects, credentials and access; draft the corresponding report sections. Review Member C's reservation and deployment work.
Member B: [name pending]. Lead geography, resources, configurations, capacities, dependencies and availability. Review Member D's billing and normalization work.
Member C: [name pending]. Lead reservations, revisions, deployments, allocations and metering. Review Member A's people and access work.
Member D: [name pending]. Lead pricing, cost sharing, invoices and payments. Review Member B's resource and history work. Because this package is broad, split pricing and payments into separate issues and transfer one to another member if estimates exceed the group's target workload.
All members: review cross-module relationships and 3NF reasoning; contribute to the analysis; verify the final PDFs. Integration and repository administration rotate between milestones and count as assigned work. No person is permanently responsible for all documentation, testing or cleanup.
## Accountability and visibility
Use one GitHub Issue per concrete task, with an owner, reviewer, acceptance criteria, estimated effort and due date. Agree on actual due dates after confirming the course deadline. The board will use To do, In progress, Review and Done. A task is complete when its artifact is linked and its reviewer has checked it.
Use a feature branch and pull request for changes. The author summarizes the change and affected assumptions; another member reviews keys, relationships, constraints and document consistency. Every member confirms collaborator access and makes a small identifiable contribution. Commit counts are supporting evidence, not a measure of equal effort.
Hold two short check-ins each week at times agreed by the group. Each member reports completed work, next work and blockers. Record decisions, scope changes and reassigned issues in the repository. Notify the group promptly if a task is at risk; do not wait until the deadline.
## Support and prevention of uneven workload
Compare estimated remaining hours and task difficulty at each check-in. Start with comparable total effort per person, including reviews and integration, then rebalance when estimates change. If a member's remaining load materially exceeds others' or a task is blocked for a day, split or transfer work and update the issue owner and reviewer.
A blocked member first describes what they tried and the specific obstacle. A teammate pairs with them to resolve it; ownership can transfer if needed. This is a shared responsibility, not a penalty for asking for help. Availability changes should trigger a new plan agreed by the group.
Keep a brief contribution log covering design, coding, writing, review, debugging and coordination. Discuss imbalances using that evidence and remaining work, rather than counting commits. Set an internal review target at least 48 hours before the course deadline where scheduling permits, leaving time for corrections and avoiding last-minute rescue work by one person.
## Review gates
Gate 1 - Scope: all members confirm the scenario, assumptions and requirements coverage.
Gate 2 - Design: each module receives a peer review; the group checks cross-module foreign keys, cardinalities, candidate keys and 3NF dependencies.
Gate 3 - Submission: verify that the three deliverables exist, diagrams are readable, document links work and the instructor can access the repository. Confirm all members have access before describing it as a shared repository.
## Adoption record - complete before submission
Confirmed member names and GitHub usernames: [pending].
Final work package owners and reviewers: [pending].
Communication channel and check-in schedule: [pending].
Course deadline and internal review date: [pending].
Agreement: each member records their acceptance through a roster pull request review or an individual acknowledgment in the repository. This statement becomes the group's adopted plan only after those confirmations.
'''
(DOC/'Group4_Analysis_Draft.md').write_text(report)
(DOC/'Group4_Team_Statement.md').write_text(team)
pdf_text(report,OUT/'Group4_Analysis_Draft.pdf');pdf_text(team,OUT/'Group4_Team_Statement.pdf')
print(f'Created {N}-table schema, seven ERD modules, analysis and team statement.')
