from pathlib import Path
import re, html, subprocess
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.graphics import renderPDF
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/milestone1'; OUT=ROOT/'output/pdf'; TMP=ROOT/'tmp/pdfs'
for p in (DOC,OUT,TMP): p.mkdir(parents=True,exist_ok=True)
# field:type; arrows identify the referenced PK; ? means nullable.
raw={'Clients and people': {'client': 'clientId:int '
                                  'PK;parentClientId:int->client?;name:text;clientType:text;contactEmail:text;qualificationNote:text?',
                        'user_account': 'userId:int PK;name:text;email:text '
                                        'UK;accountKind:text;staffRole:text?;status:text',
                        'client_membership': 'membershipId:int '
                                             'PK;clientId:int->client;userId:int->user_account;role:text;validFrom:timestamp;validTo:timestamp?',
                        'project': 'projectId:int PK;clientId:int->client;name:text'},
 'Infrastructure and availability': {'region': 'regionId:int PK;name:text UK;regulatoryNote:text',
                                     'availability_zone': 'zoneId:int '
                                                          'PK;regionId:int->region;name:text;redundancyNote:text;connectivityNote:text',
                                     'data_center': 'dataCenterId:int '
                                                    'PK;zoneId:int->availability_zone;name:text;location:text',
                                     'resource_type': 'resourceTypeId:int PK;name:text '
                                                      'UK;intendedWorkload:text',
                                     'resource': 'resourceId:int '
                                                 'PK;resourceTypeId:int->resource_type;dataCenterId:int->data_center;localIdentifier:text;performanceTier:text;vcpuCount:int;memoryGib:decimal;storageGib:decimal;networkGbps:decimal',
                                     'resource_state': 'stateId:int '
                                                       'PK;resourceId:int->resource;status:text;reason:text;startsAt:timestamp;endsAt:timestamp?;recordedByUserId:int->user_account?'},
 'Reservations and requests': {'reservation': 'reservationId:int '
                                              'PK;clientId:int->client;createdAt:timestamp;startTime:timestamp;endTime:timestamp;status:text;agreementNote:text?;approvedByUserId:int->user_account?',
                               'reservation_item': 'reservationItemId:int '
                                                   'PK;reservationId:int->reservation;resourceTypeId:int->resource_type;quantity:int;minVcpu:int;minMemoryGib:decimal;minStorageGib:decimal;minNetworkGbps:decimal;preferredRegionId:int->region?;preferredZoneId:int->availability_zone?;preferredDataCenterId:int->data_center?;locationMode:text'},
 'Deployments and assignments': {'deployment': 'deploymentId:int '
                                               'PK;reservationId:int->reservation;projectId:int->project?;name:text;workloadNote:text;startedAt:timestamp?;endedAt:timestamp?;confidentialityLevel:text;status:text;priority:int;scalingMode:text',
                                 'resource_allocation': 'allocationId:int '
                                                        'PK;deploymentId:int->deployment;reservationItemId:int->reservation_item;resourceId:int->resource;capacityFraction:decimal;startsAt:timestamp;endsAt:timestamp?;allocationStatus:text;supersedesAllocationId:int->resource_allocation?;changeReason:text;assignedByUserId:int->user_account?',
                                 'deployment_service': 'deploymentServiceId:int '
                                                       'PK;deploymentId:int->deployment;serviceId:int->service;startsAt:timestamp;endsAt:timestamp?'},
 'Services, rates and metering': {'service': 'serviceId:int PK;name:text UK;serviceType:text;billingUnit:text',
                                  'service_rate': 'serviceRateId:int '
                                                  'PK;serviceId:int->service;validFrom:timestamp;validTo:timestamp?;unitPrice:decimal',
                                  'usage_record': 'usageId:int '
                                                  'PK;deploymentServiceId:int->deployment_service;allocationId:int->resource_allocation?;quantity:decimal;periodStart:timestamp;periodEnd:timestamp;recordType:text;recordedAt:timestamp;supersedesUsageId:int->usage_record '
                                                  'UK?'},
 'Billing and invoices': {'billing_account': 'billingAccountId:int '
                                             'PK;responsibleClientId:int->client;name:text;billingContactUserId:int->user_account?',
                          'charge': 'chargeId:int PK;usageId:int->usage_record '
                                    'UK?;deploymentServiceId:int->deployment_service?;serviceRateId:int->service_rate?;adjustmentOfChargeId:int->charge?;authorizedByUserId:int->user_account?;chargeType:text;amount:decimal;status:text;reason:text;createdAt:timestamp',
                          'charge_share': 'chargeShareId:int '
                                          'PK;chargeId:int->charge;billingAccountId:int->billing_account;allocatedAmount:decimal',
                          'invoice': 'invoiceId:int '
                                     'PK;billingAccountId:int->billing_account;issuedAt:timestamp;dueAt:timestamp;status:text',
                          'invoice_line': 'chargeShareId:int PK->charge_share;invoiceId:int->invoice'}}
schema={}; modules={}
for module,tables in raw.items():
 modules[module]=list(tables)
 for name,fields in tables.items():
  schema[name]=[]
  for f in fields.split(';'):
   field,desc=f.split(':'); target=None
   if '->' in desc:
    desc,target=desc.split('->'); target=target.replace(' UK','').rstrip('?').strip()
   schema[name].append(dict(name=field,type=desc.split()[0].rstrip('?'),pk='PK' in desc,fk=target,nullable='?' in f,unique='UK' in f))
for name,fs in schema.items():
 assert any(f['pk'] for f in fs),name
 for f in fs:
  assert not f['fk'] or f['fk'] in schema,(name,f)
  assert not (f['pk'] and f['nullable'])
N=len(schema)
# Portable field inventory for external diagram authoring (no alternate-key markers).
import csv
with (DOC/'Group4_ERD_Fields.csv').open('w',newline='') as inventory:
 writer=csv.writer(inventory)
 writer.writerow(['table','attribute','type','key','nullable','referencesTable','referencesAttribute'])
 for name,fs in schema.items():
  for f in fs:
   target=f['fk']
   writer.writerow([name,f['name'],f['type'],'/'.join(k for k,b in [('PK',f['pk']),('FK',bool(target))] if b),f['nullable'],target or '',next((x['name'] for x in schema[target] if x['pk']),'') if target else ''])


def relationship_label(field):
 name=field['name']
 special={
  'parentClientId':'has child client', 'approvedByUserId':'approves reservation',
  'recordedByUserId':'records resource state', 'assignedByUserId':'assigns allocation',
  'authorizedByUserId':'authorizes charge', 'billingContactUserId':'is contact for',
  'responsibleClientId':'is responsible for', 'supersedesAllocationId':'is replaced by',
  'supersedesUsageId':'is corrected by', 'adjustmentOfChargeId':'has adjustment',
  'preferredRegionId':'is preferred by', 'preferredZoneId':'is preferred by',
  'preferredDataCenterId':'is preferred by',
 }
 if name in special: return special[name]
 return {'client':'has', 'user_account':'has membership', 'region':'contains',
  'availability_zone':'contains', 'data_center':'hosts', 'resource_type':'classifies',
  'resource':'has', 'reservation':'has', 'reservation_item':'is fulfilled by',
  'project':'groups', 'deployment':'has', 'resource_allocation':'supports',
  'service':'has', 'service_rate':'prices', 'deployment_service':'generates',
  'usage_record':'produces', 'charge':'is split into', 'billing_account':'has',
  'charge_share':'appears on', 'invoice':'contains'}[field['fk']]

lines=['erDiagram','    direction LR']
for name,fs in schema.items():
 for f in fs:
  if f['fk']:
   left='o|' if f['nullable'] else '||'
   right='o|' if f['unique'] or (f['pk'] and sum(x['pk'] for x in fs)==1) else 'o{'
   lines.append(f'    {f["fk"]} {left}--{right} {name} : {relationship_label(f)}')
for name,fs in schema.items():
 lines.append(f'    {name} {{')
 for f in fs:
  flags=', '.join(x for x,b in [('PK',f['pk']),('FK',bool(f['fk']))] if b)
  lines.append(f'        {f["type"]} {f["name"]}'+(' '+flags if flags else '')+(' "nullable"' if f['nullable'] else ''))
 lines.append('    }')
(DOC/'Group4_ERD.mmd').write_text('\n'.join(lines)+'\n')
# Views follow the same A-D ownership as the Team Statement.
views={
 'A': ('Clients and reservations', ['client','user_account','client_membership','project','reservation','reservation_item']),
 'B': ('Infrastructure and availability', ['region','availability_zone','data_center','resource_type','resource','resource_state']),
 'C': ('Deployments and services', ['deployment','resource_allocation','deployment_service','service','service_rate']),
 'D': ('Metering and billing', ['usage_record','billing_account','charge','charge_share','invoice','invoice_line']),
}
owner={name:member for member,(_,names) in views.items() for name in names}
assert set(owner)==set(schema) and sum(len(v[1]) for v in views.values())==N
palette={'A':'#245f9c','B':'#267361','C':'#855a9e','D':'#ad6625'}
unique_groups={
 'availability_zone':'UNIQUE(regionId, name)',
 'data_center':'UNIQUE(zoneId, name)',
 'resource':'UNIQUE(dataCenterId, localIdentifier)',
 'service_rate':'UNIQUE(serviceId, validFrom)',
 'charge_share':'UNIQUE(chargeId, billingAccountId)',
}
def endpoints(name,f):
 return ('0..1' if f['nullable'] else '1', '0..1' if f['unique'] or (f['pk'] and sum(x['pk'] for x in schema[name])==1) else '0..*')
def graph(names,overview=False):
 external=[] if overview else sorted({f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names})
 dot=['digraph G {','graph [rankdir=LR, bgcolor="white", nodesep=0.55, ranksep=0.9, splines=spline, pad=0.25, outputorder=edgesfirst];','node [shape=plain, fontname="Helvetica"];','edge [fontname="Helvetica", fontsize=9, color="#61738b", arrowsize=0.6, labeldistance=2.2];']
 for name in names+external:
  ext=name in external; fs=[f for f in schema[name] if f['pk']] if ext or overview else schema[name]
  color='#718096' if ext else palette[owner[name]]
  label=f'{owner[name]} / {name}'+(' (reference)' if ext else '')
  rows=[f'<TR><TD COLSPAN="2" BGCOLOR="{color}"><FONT COLOR="white" POINT-SIZE="11"><B>{label}</B></FONT></TD></TR>']
  for field in fs:
   key='/'.join(k for k,b in [('PK',field['pk']),('FK',bool(field['fk']))] if b)
   rows.append(f'<TR><TD PORT="{field["name"]}" ALIGN="LEFT"><FONT POINT-SIZE="10">{key or "&#160;"}</FONT></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="10">{field["name"]}: {field["type"]}{" ?" if field["nullable"] else ""}</FONT></TD></TR>')
  dot.append(f'{name} [label=<<TABLE BORDER="1" COLOR="#c6d0dc" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6">'+''.join(rows)+'</TABLE>>];')
 for name in names:
  for field in schema[name]:
   target=field['fk']
   if not target: continue
   # The overview is an entity inventory; all relationships are in detail views.
   if overview:
    continue
   parent,child=endpoints(name,field)
   targetpk=next(x['name'] for x in schema[target] if x['pk'])
   destination=name if overview else name+':'+field['name']+':w'
   source=target
   attrs=f'dir=none,taillabel="{parent}",headlabel="{child}",style="{"dashed" if target in external else "solid"}"'
   if overview: attrs+=f',color="{palette[owner[name]]}88"'
   dot.append(f'{source} -> {destination} [{attrs}];')
 dot.append('}')
 return '\n'.join(dot)
(TMP/'overview.dot').write_text(graph(list(schema),True))
for member,(_,names) in views.items():
 (TMP/f'owner_{member}.dot').write_text(graph(names))
node="""const fs=require('fs'); const {instance}=require('/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@viz-js/viz'); (async()=>{const v=await instance();for(const file of ['overview','owner_A','owner_B','owner_C','owner_D']){const p=process.argv[1]+'/'+file;fs.writeFileSync(p+'.svg',v.renderString(fs.readFileSync(p+'.dot','utf8'),{format:'svg'}));}})();"""
subprocess.run(['/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','-e',node,str(TMP)],check=True)
# Fail if Graphviz omitted a label or relationship instead of producing a full diagram.
for member,(_,names) in views.items():
 external={f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names}
 svg=(TMP/f'owner_{member}.svg').read_text()
 assert svg.count('class="node"')==len(names)+len(external),member
 assert svg.count('class="edge"')==sum(bool(f['fk']) for name in names for f in schema[name]),member
assert (TMP/'overview.svg').read_text().count('class="node"')==N
svgout=ROOT/'output/svg';svgout.mkdir(parents=True,exist_ok=True)
(svgout/'Group4_ERD_Overview.svg').write_text((TMP/'overview.svg').read_text())
# Editable owner views render directly on GitHub; each repeats only necessary
# external keys. The .mmd file remains the full schema with all FK relationships.
parts=['# Group 4 - ERD ownership views','23 tables; one primary owner per table. Names will be mapped to A-D later.', '![All 23 entities, color-coded by owner](../../output/svg/Group4_ERD_Overview.svg)','[Submission PDF](../../output/pdf/Group4_ERD.pdf) | [Analysis and constraints](Group4_Analysis_Draft.md)','']
for member,(title,names) in views.items():
 parts += [f'## Member {member}: {title}',f'{len(names)} owned tables. Gray-reference styling is used in the PDF; referenced entities below show only their primary keys.','', '```mermaid','erDiagram','    direction LR']
 external=sorted({x['fk'] for name in names for x in schema[name] if x['fk'] and x['fk'] not in names})
 for name in names:
  for field in schema[name]:
   if field['fk']:
    left='o|' if field['nullable'] else '||'
    _,right=endpoints(name,field)
    right='o|' if right=='0..1' else 'o{'
    parts.append(f'    {field["fk"]} {left}--{right} {name} : {relationship_label(field)}')
 for name in names+external:
  parts.append(f'    {name} {{')
  for field in schema[name]:
   if name in external and not field['pk']:continue
   flags=', '.join(k for k,b in [('PK',field['pk']),('FK',bool(field['fk']))] if b)
   parts.append(f'        {field["type"]} {field["name"]}'+(' '+flags if flags else '')+(' "nullable"' if field['nullable'] else ''))
  parts.append('    }')
 parts += ['```','']
(DOC/'Group4_ERD_Views.md').write_text('\n'.join(parts).rstrip()+'\n')
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
 grouped=[]
 i=0
 while i<len(story):
  if story[i].style.name=='SubCustom' and i+1<len(story):
   grouped.append(KeepTogether([story[i],story[i+1]]));i+=2
  else: grouped.append(story[i]);i+=1
 story=grouped
 SimpleDocTemplate(str(path),pagesize=letter,allowSplitting=1,rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=48).build(story,onFirstPage=footer,onLaterPages=footer)
# Crossing-free atlas: each FK has its own horizontal relationship lane.
c=canvas.Canvas(str(OUT/'Group4_ERD.pdf'),pagesize=letter)
c.setTitle('Group 4 - CloudNine Systems - ERD')
total=N+1
c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',24)
c.drawString(40,742,'CloudNine Systems | ERD')
c.setFont('Helvetica',11)
intro=['23 tables in 3NF. Table names: singular lower_case; attributes: camelCase.',
 'PK = primary key; FK = foreign key. No alternate-key markers are shown.',
 'Each detail page lists every attribute and every outgoing foreign key.',
 'Relationship lanes are independent: lines never cross.',
 'Endpoint numbers give the number of records at that end per opposite record.',
 '1 = exactly one; 0..1 = zero or one; 0..* = zero or more.',
 'Nullable attributes say "optional". All other attributes are required.',
 'Uniqueness and other business rules: analysis report, section 4 (R1-R9).',
 'Tool: generated PDF; not a Lucidchart-authored submission.',
 'Assignment 3 is a formatting reference; the domain remains CloudNine.']
for i,t in enumerate(intro):c.drawString(40,710-i*20,t)
for index,(member,(title,names)) in enumerate(views.items()):
 x=40+(index%2)*280;y=478-(index//2)*190
 c.setFillColor(colors.HexColor(palette[member]));c.setFont('Helvetica-Bold',12)
 c.drawString(x,y,f'Member {member}')
 c.setFont('Helvetica',10);c.drawString(x,y-16,title);y-=16;y-=22
 c.setFillColor(colors.HexColor('#243247'));c.setFont('Helvetica',10)
 for name in names:
  c.drawString(x+4,y,f'{name}  -  page {list(schema).index(name)+2}');y-=17
 y-=12
c.setFont('Helvetica',8);c.drawString(40,24,f'Group 4 | Entity index | 1 / {total}')
c.showPage()
for page,(name,fs) in enumerate(schema.items(),2):
 relations=[f for f in fs if f['fk']]
 w=1200;h=max(800,130+len(relations)*105,150+len(fs)*30)
 c.setPageSize((w,h));c.setFillColor(colors.HexColor(palette[owner[name]]))
 c.setFont('Helvetica-Bold',24);c.drawString(40,h-42,f'{name} | Member {owner[name]}')
 c.setFont('Helvetica',11);c.drawString(40,h-66,'Attributes and labelled relationships | One independent lane per foreign key')
 c.setFont('Helvetica-Bold',12);c.drawString(40,h-101,'Key');c.drawString(95,h-101,'Attribute');c.drawString(320,h-101,'Type / optionality')
 for i,f in enumerate(fs):
  y=h-131-i*30
  c.setFillColor(colors.HexColor('#f1f5f9') if i%2==0 else colors.white);c.rect(35,y-9,470,28,fill=1,stroke=0)
  c.setFillColor(colors.HexColor('#243247'));c.setFont('Helvetica-Bold' if f['pk'] else 'Helvetica',11)
  key='/'.join(k for k,b in [('PK',f['pk']),('FK',bool(f['fk']))] if b)
  c.drawString(40,y,key);c.drawString(95,y,f['name']);c.drawString(320,y,f['type']+(' (optional)' if f['nullable'] else ''))
 c.setFont('Helvetica-Bold',12);c.drawString(550,h-101,'Relationships (parent to child)')
 if not relations:
  c.setFont('Helvetica',11);c.drawString(550,h-135,'No outgoing foreign keys; incoming links appear on child pages.')
 for i,f in enumerate(relations):
  y=h-160-i*105;target=f['fk'];pk=next(x['name'] for x in schema[target] if x['pk'])
  parent,child=endpoints(name,f)
  c.setFillColor(colors.HexColor('#f1f5f9'));c.setStrokeColor(colors.HexColor('#c6d0dc'))
  c.roundRect(550,y-20,220,48,4,fill=1,stroke=1);c.roundRect(955,y-20,220,48,4,fill=1,stroke=1)
  c.setFillColor(colors.HexColor('#243247'));c.setFont('Helvetica-Bold',10)
  c.drawString(560,y+10,target);c.drawString(965,y+10,name)
  c.setFont('Helvetica',10);c.drawString(560,y-7,'PK '+pk);c.drawString(965,y-7,'FK '+f['name'])
  c.setStrokeColor(colors.HexColor('#61738b'));c.line(770,y,955,y)
  c.setFont('Helvetica-Bold',10);c.drawString(777,y-15,parent);c.drawRightString(948,y-15,child)
  c.setFont('Helvetica',10);c.drawCentredString(862,y+12,relationship_label(f))
 c.setFillColor(colors.HexColor('#475569'));c.setFont('Helvetica',9)
 c.drawString(40,25,'Group 4 | 1 = exactly one | 0..1 = optional one | 0..* = zero or more | Assumptions: analysis R1-R9')
 c.drawRightString(w-40,25,f'{page} / {total}');c.showPage()
c.save()
report=(DOC/'Group4_Analysis_Draft.md').read_text()
team=(DOC/'Group4_Team_Statement.md').read_text()
(DOC/'Group4_Analysis_Draft.md').write_text(report)
(DOC/'Group4_Team_Statement.md').write_text(team)
pdf_text(report,OUT/'Group4_Analysis_Draft.pdf');pdf_text(team,OUT/'Group4_Team_Statement.pdf')
print(f'Created {N}-table schema, four owner views, crossing-free ERD atlas, analysis and team statement.')
