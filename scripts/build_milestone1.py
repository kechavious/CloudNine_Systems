from pathlib import Path
import re, html, subprocess
import xml.etree.ElementTree as ET
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
raw={'Clients and people': {'client': 'clientId:int '
                                  'PK;parentClientId:int->client?;name:text;clientType:text;contactEmail:text;qualificationNote:text?',
                        'user_account': 'userId:int PK;name:text;email:text '
                                        ';accountKind:text;staffRole:text?;status:text',
                        'client_membership': 'membershipId:int '
                                             'PK;clientId:int->client;userId:int->user_account;role:text;validFrom:timestamp;validTo:timestamp?',
                        'project': 'projectId:int PK;clientId:int->client;name:text'},
 'Infrastructure and availability': {'region': 'regionId:int PK;name:text;regulatoryNote:text',
                                     'availability_zone': 'zoneId:int '
                                                          'PK;regionId:int->region;name:text;redundancyNote:text;connectivityNote:text',
                                     'data_center': 'dataCenterId:int '
                                                    'PK;zoneId:int->availability_zone;name:text;location:text',
                                     'resource_type': 'resourceTypeId:int PK;name:text '
                                                      ';intendedWorkload:text',
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
 'Services, rates and metering': {'service': 'serviceId:int PK;name:text;serviceType:text;billingUnit:text',
                                  'service_rate': 'serviceRateId:int '
                                                  'PK;serviceId:int->service;validFrom:timestamp;validTo:timestamp?;unitPrice:decimal',
                                  'usage_record': 'usageId:int '
                                                  'PK;deploymentServiceId:int->deployment_service;allocationId:int->resource_allocation?;quantity:decimal;periodStart:timestamp;periodEnd:timestamp;recordType:text;recordedAt:timestamp;supersedesUsageId:int->usage_record '
                                                  '?'},
 'Billing and invoices': {'billing_account': 'billingAccountId:int '
                                             'PK;responsibleClientId:int->client;name:text;billingContactUserId:int->user_account?',
                          'charge': 'chargeId:int PK;usageId:int->usage_record '
                                    '?;deploymentServiceId:int->deployment_service?;serviceRateId:int->service_rate?;adjustmentOfChargeId:int->charge?;authorizedByUserId:int->user_account?;chargeType:text;amount:decimal;status:text;reason:text;createdAt:timestamp',
                          'charge_share': 'chargeShareId:int '
                                          'PK;chargeId:int->charge;billingAccountId:int->billing_account;allocatedAmount:decimal',
                          'invoice': 'invoiceId:int '
                                     'PK;billingAccountId:int->billing_account;issuedAt:timestamp;dueAt:timestamp;status:text',
                          'invoice_line': 'chargeShareId:int PK->charge_share;invoiceId:int->invoice'}}
# Additional identity rules are documented in analysis R9, not drawn as key markers.
unique_attributes={('user_account','email'),('region','name'),('resource_type','name'),
                   ('service','name'),('usage_record','supersedesUsageId'),('charge','usageId')}
schema={}; modules={}
for module,tables in raw.items():
 modules[module]=list(tables)
 for name,fields in tables.items():
  schema[name]=[]
  for f in fields.split(';'):
   field,desc=f.split(':'); target=None
   if '->' in desc:
    desc,target=desc.split('->'); target=target.rstrip('?').strip()
   schema[name].append(dict(name=field,type=desc.split()[0].rstrip('?'),pk='PK' in desc,fk=target,nullable='?' in f,unique=(name,field) in unique_attributes))
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
def endpoints(name,f):
 return ('0..1' if f['nullable'] else '1', '0..1' if f['unique'] or (f['pk'] and sum(x['pk'] for x in schema[name])==1) else '0..*')
def graph(names,overview=False):
 external=[] if overview else sorted({f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names})
 dot=['digraph G {','graph [rankdir=TB, bgcolor="white", nodesep=0.8, ranksep=1.15, splines=polyline, pad=0.25, outputorder=edgesfirst];','node [shape=plain, fontname="Helvetica"];','edge [fontname="Helvetica", fontsize=11, color="#333333", arrowsize=0.6, labeldistance=2.0];']
 for name in names+external:
  ext=name in external; fs=[f for f in schema[name] if f['pk']] if ext else schema[name]
  color='#e9e9e9' if ext else '#ffffff'
  label=name+(' (ref)' if ext else '')
  rows=[f'<TR><TD COLSPAN="3" BGCOLOR="{color}"><FONT COLOR="black" POINT-SIZE="13"><B>{label}</B></FONT></TD></TR>']
  for field in fs:
   key='/'.join(k for k,b in [('PK',field['pk']),('FK',bool(field['fk']))] if b)
   rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="11">{key or "&#160;"}</FONT></TD><TD PORT="{field["name"]}" ALIGN="LEFT"><FONT POINT-SIZE="11">{field["name"]}</FONT></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="11">{field["type"]}{" ?" if field["nullable"] else ""}</FONT></TD></TR>')
  dot.append(f'{name} [label=<<TABLE BORDER="1" COLOR="#333333" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6">'+''.join(rows)+'</TABLE>>];')
 for name in names:
  for field in schema[name]:
   target=field['fk']
   if not target: continue
   parent,child=endpoints(name,field)
   targetpk=next(x['name'] for x in schema[target] if x['pk'])
   destination=name
   source=target
   if target==name and name=='client':
    source=target+':n';destination=name+':n'
   if not overview and name=='client_membership':
    destination=name+(':e' if target=='user_account' else ':w')
   attrs=f'label="{relationship_label(field)}",dir=none,taillabel="{parent}",headlabel="{child}",style="{"dashed" if target in external else "solid"}"'

   dot.append(f'{source} -> {destination} [{attrs}];')
 if not overview and 'client_membership' in names:
  dot.append('user_account -> client [style=invis, weight=20];')
 dot.append('}')
 return '\n'.join(dot)
for member,(_,names) in views.items():
 (TMP/f'owner_{member}.dot').write_text(graph(names))
node="""const fs=require('fs'); const {instance}=require('/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@viz-js/viz'); (async()=>{const v=await instance();for(const file of ['owner_A','owner_B','owner_C','owner_D']){const p=process.argv[1]+'/'+file;fs.writeFileSync(p+'.svg',v.renderString(fs.readFileSync(p+'.dot','utf8'),{format:'svg'}));}})();"""
subprocess.run(['/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','-e',node,str(TMP)],check=True)
# Fail if Graphviz omitted a label or relationship instead of producing a full diagram.
for member,(_,names) in views.items():
 external={f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names}
 svg=(TMP/f'owner_{member}.svg').read_text()
 assert svg.count('class="node"')==len(names)+len(external),member
 assert svg.count('class="edge"')==sum(bool(f['fk']) for name in names for f in schema[name]),member
svgout=ROOT/'output/svg';svgout.mkdir(parents=True,exist_ok=True)
# Compose the four final diagrams into a readable two-by-two overview.
ET.register_namespace('', 'http://www.w3.org/2000/svg')
overview=ET.Element('{http://www.w3.org/2000/svg}svg',width='1800',height='2500',viewBox='0 0 1800 2500')
title=ET.SubElement(overview,'{http://www.w3.org/2000/svg}title')
title.text='CloudNine Systems - four ERD domains, 23 tables'
for i,(member,(title,names)) in enumerate(views.items()):
 x=30+(i%2)*900;y=55+(i//2)*1240
 heading=ET.SubElement(overview,'{http://www.w3.org/2000/svg}text',x=str(x),y=str(y),attrib={'font-family':'Helvetica, Arial, sans-serif','font-size':'22','font-weight':'bold'})
 heading.text=f'{member} | {title}'
 panel=ET.fromstring((TMP/f'owner_{member}.svg').read_text())
 _,_,pw,ph=map(float,panel.attrib['viewBox'].split())
 scale=min(840/pw,1150/ph)
 panel.set('x',str(x+(840-pw*scale)/2));panel.set('y',str(y+20))
 panel.set('width',str(pw*scale));panel.set('height',str(ph*scale))
 panel.set('preserveAspectRatio','xMidYMin meet');overview.append(panel)
(svgout/'Group4_ERD_Overview.svg').write_text(ET.tostring(overview,encoding='unicode')+'\n')
# Editable owner views render directly on GitHub; each repeats only necessary
# external keys. The .mmd file remains the full schema with all FK relationships.
parts=['# Group 4 - ERD ownership views','23 tables; one primary owner per table. Names will be mapped to A-D later.', '![All 23 entities and relationships](../../output/svg/Group4_ERD_Overview.svg)','[Submission PDF](../../output/pdf/Group4_ERD.pdf) | [Analysis and constraints](Group4_Analysis_Draft.md)','']
for member,(title,names) in views.items():
 parts += [f'## Member {member}: {title}',f'{len(names)} owned tables. Shaded boxes show primary keys of entities owned by another member.',f'![Member {member} ERD](../../output/svg/Group4_ERD_{member}.svg)','', '<details>', '<summary>Editable Mermaid source</summary>', '', '```mermaid','erDiagram','    direction LR']
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
 parts += ['```','</details>','']
(DOC/'Group4_ERD_Views.md').write_text('\n'.join(parts).rstrip()+'\n')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=10,leading=13,spaceAfter=7,textColor=colors.black))
styles.add(ParagraphStyle(name='TitleCustom',fontName='Helvetica-Bold',fontSize=23,leading=28,spaceAfter=16,textColor=colors.black))
styles.add(ParagraphStyle(name='SubCustom',fontName='Helvetica-Bold',fontSize=13,leading=17,spaceBefore=14,spaceAfter=7,textColor=colors.black))
def footer(c,d):
 c.setFont('Helvetica',8); c.setFillColor(colors.HexColor('#555555')); c.drawString(48,28,'GROUP 4 | CLOUDNINE SYSTEMS | MILESTONE 1'); c.drawRightString(letter[0]-48,28,str(d.page))
def pdf_text(md,path):
 story=[]
 body_style=ParagraphStyle(name='CompactTeamBody',parent=styles['BodyCustom'],leading=12,spaceAfter=6) if path.name=='Group4_Team_Statement.pdf' else styles['BodyCustom']
 for line in md.splitlines():
  if not line.strip(): continue
  if line.startswith('# '): style='TitleCustom'; line=line[2:]
  elif line.startswith('## '): style='SubCustom'; line=line[3:]
  else: style='BodyCustom'
  line=html.escape(line)
  line=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',line)
  story.append(Paragraph(line,body_style if style=='BodyCustom' else styles[style]))
 grouped=[]
 i=0
 while i<len(story):
  if story[i].style.name=='SubCustom' and i+1<len(story):
   grouped.append(KeepTogether([story[i],story[i+1]]));i+=2
  else: grouped.append(story[i]);i+=1
 story=grouped
 SimpleDocTemplate(str(path),pagesize=letter,invariant=1,allowSplitting=1,rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=48).build(story,onFirstPage=footer,onLaterPages=footer)
# Assignment-style diagrams: four readable domain views.
c=canvas.Canvas(str(OUT/'Group4_ERD.pdf'),invariant=1)
c.setTitle('Group 4 - CloudNine Systems - ER diagram')
pages=[(f'owner_{member}',title+' - ER diagram',f'Member {member}: {len(names)} tables; shaded boxes reference another domain') for member,(title,names) in views.items()]
for page,(file,title,subtitle) in enumerate(pages,1):
 d=svg2rlg(str(TMP/f'{file}.svg'))
 w=max(900,d.width+100);h=d.height+245
 c.setPageSize((w,h));c.setFillColor(colors.black)
 c.setFont('Helvetica-Bold',24);c.drawCentredString(w/2,h-38,title)
 c.setFont('Helvetica',11);c.drawCentredString(w/2,h-59,subtitle)
 renderPDF.draw(d,c,(w-d.width)/2,152)
 c.setFont('Helvetica-Bold',11);c.drawString(50,128,'Assumptions and notation')
 notes=['PK = primary key; FK = foreign key; ? = nullable. Unmarked attributes are required.',
 'Endpoint cardinalities: 1 = exactly one; 0..1 = zero or one; 0..* = zero or more.',
 'Each labelled line represents its child foreign key. Reference boxes repeat existing entities.',
 'Uniqueness, time intervals, allocation limits and billing rules: analysis report R1-R9.']
 domain_notes={
  'owner_A':['A client has at most one parent; client hierarchy cycles are prohibited.', 'An item selects at most one preferred location level; approved reservations must contain items.'],
  'owner_B':['Each data center belongs to one zone, and each zone belongs to one region.', 'Resource-state intervals for the same resource cannot overlap; resource capacities are scalar.'],
  'owner_C':['Allocations must match the reservation item and deployment; overlapping fractions total at most one.', 'Replacement allocations retain the predecessor; rates for the same service cannot overlap.'],
  'owner_D':['Each charge has exactly one context: usage, direct service, or adjustment of an earlier charge.', 'Final payer shares sum to the charge; an invoiced share belongs to the invoice account and is billed once.'],
 }
 notes+=domain_notes[file]
 for i,note in enumerate(notes):c.setFont('Helvetica',10);c.drawString(50,111-i*15,note)
 c.setFont('Helvetica',9);c.drawRightString(w-50,20,f'Group 4 | {page} / {len(pages)}');c.showPage()
c.save()
for member in views:
 (svgout/f'Group4_ERD_{member}.svg').write_text((TMP/f'owner_{member}.svg').read_text())
report=(DOC/'Group4_Analysis_Draft.md').read_text()
team=(DOC/'Group4_Team_Statement.md').read_text()
(DOC/'Group4_Analysis_Draft.md').write_text(report)
(DOC/'Group4_Team_Statement.md').write_text(team)
pdf_text(report,OUT/'Group4_Analysis_Draft.pdf');pdf_text(team,OUT/'Group4_Team_Statement.pdf')
print(f'Created {N}-table schema, four owner views, four-page ERD, analysis and team statement.')
