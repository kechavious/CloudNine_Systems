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
                        'user_account': 'userId:int PK;clientId:int->client?;name:text;email:text '
                                        ';accountKind:text;staffRole:text?;status:text'},
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
                                               'PK;reservationId:int->reservation;name:text;workloadNote:text;startedAt:timestamp?;endedAt:timestamp?;confidentialityLevel:text;status:text;priority:int;scalingMode:text',
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
                                          'PK;chargeId:int->charge;invoiceId:int->invoice;allocatedAmount:decimal',
                          'invoice': 'invoiceId:int '
                                     'PK;billingAccountId:int->billing_account;issuedAt:timestamp;dueAt:timestamp;status:text'}}
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
 writer=csv.writer(inventory,lineterminator='\n')
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
 return {'client':'has', 'user_account':'acts for', 'region':'contains',
  'availability_zone':'contains', 'data_center':'hosts', 'resource_type':'classifies',
  'resource':'has', 'reservation':'has', 'reservation_item':'is fulfilled by',
  'deployment':'has', 'resource_allocation':'supports',
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
 'A': ('Clients and reservations', ['client','user_account','reservation','reservation_item','billing_account']),
 'B': ('Infrastructure', ['region','availability_zone','data_center','resource_type','resource']),
 'C': ('Deployments and usage', ['deployment','resource_allocation','resource_state','deployment_service','usage_record']),
 'D': ('Services and billing', ['service','service_rate','charge','charge_share','invoice']),
}
owner={name:member for member,(_,names) in views.items() for name in names}
assert set(owner)==set(schema) and sum(len(v[1]) for v in views.values())==N
def endpoints(name,f):
 return ('0..1' if f['nullable'] else '1', '0..1' if f['unique'] or (f['pk'] and sum(x['pk'] for x in schema[name])==1) else '0..*')
def graph(names,overview=False):
 external=[] if overview else sorted({f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names})
 aliases={'state_actor_ref':'user_account','state_resource_ref':'resource'} if 'resource_state' in names and not overview else {}
 external+=list(aliases)
 dot=['digraph G {','graph [rankdir=TB, bgcolor="white", nodesep=1.0, ranksep=1.15, splines=ortho, pad=0.25, outputorder=edgesfirst];','node [shape=plain, fontname="Helvetica"];','edge [fontname="Helvetica", fontsize=11, color="#333333", arrowsize=0.85, labeldistance=2.0];']
 if overview:
  dot[1]=dot[1].replace('rankdir=TB','rankdir=LR').replace('ranksep=1.15','ranksep=1.6')
  dot.append('graph [label="CloudNine Systems - connected ERD overview\\n20 entities | 37 relationships | A: clients | B: infrastructure | C: deployments and usage | D: billing", labelloc=t, fontsize=24, fontname="Helvetica"];')
 for name in names+external:
  ext=name in external; canonical=aliases.get(name,name)
  fs=[f for f in schema[canonical] if f['pk']] if ext else schema[canonical]
  color='#e9e9e9' if ext else '#ffffff'
  label=(f'{owner[canonical]} / ' if overview else '')+canonical+(' (ref)' if ext else '')
  rows=[f'<TR><TD COLSPAN="3" BGCOLOR="{color}" BORDER="1" SIDES="B"><FONT COLOR="black" POINT-SIZE="13"><B>{label}</B></FONT></TD></TR>']
  for field in fs:
   key='/'.join(k for k,b in [('PK',field['pk']),('FK',bool(field['fk']))] if b)
   rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="11">{key or "&#160;"}</FONT></TD><TD PORT="{field["name"]}" ALIGN="LEFT" BORDER="1" SIDES="L"><FONT POINT-SIZE="11">{field["name"]}</FONT></TD><TD ALIGN="LEFT" BORDER="1" SIDES="L"><FONT POINT-SIZE="11">{field["type"]}{" ?" if field["nullable"] else ""}</FONT></TD></TR>')
  dot.append(f'{name} [label=<<TABLE STYLE="ROUNDED" BORDER="1" COLOR="#333333" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6">'+''.join(rows)+'</TABLE>>];')
 for name in names:
  for field in schema[name]:
   target=field['fk']
   if not target: continue
   parent,child=endpoints(name,field)
   targetpk=next(x['name'] for x in schema[target] if x['pk'])
   destination=name
   source=target
   if name=='resource_state' and not overview:
    source='state_actor_ref' if target=='user_account' else 'state_resource_ref'
   tail='teeodot' if parent=='0..1' else 'teetee'
   head='teeodot' if child=='0..1' else 'crowodot'
   attrs=f'label="{relationship_label(field)}",dir=both,arrowtail="{tail}",arrowhead="{head}",style=solid'

   dot.append(f'{source} -> {destination} [{attrs}];')
 dot.append('}')
 return '\n'.join(dot)
(TMP/'overview.dot').write_text(graph(list(schema),True))
for member,(_,names) in views.items():
 (TMP/f'owner_{member}.dot').write_text(graph(names))
node="""const fs=require('fs'); const {instance}=require('/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@viz-js/viz'); (async()=>{const v=await instance();for(const file of ['overview','owner_A','owner_B','owner_C','owner_D']){const p=process.argv[1]+'/'+file;fs.writeFileSync(p+'.svg',v.renderString(fs.readFileSync(p+'.dot','utf8'),{format:'svg'}));}})();"""
subprocess.run(['/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','-e',node,str(TMP)],check=True)
# Place labels on the actual orthogonal routes, including recursive relationships.
# Graphviz's default ortho label coordinates can float away from the line.
from reportlab.pdfbase.pdfmetrics import stringWidth
SVG_NS='http://www.w3.org/2000/svg'
ET.register_namespace('',SVG_NS)
def svg_points(value):
 numbers=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',value)))
 return list(zip(numbers[::2],numbers[1::2]))
def overlaps(a,b):
 return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def position_labels(file,names):
 path=TMP/f'{file}.svg';root=ET.fromstring(path.read_text());ns={'s':SVG_NS}
 fields=[(name,f) for name in names for f in schema[name] if f['fk']]
 labels=[relationship_label(f) for name,f in fields]
 boxes=[];node_boxes={}
 for node in root.findall('.//s:g[@class="node"]',ns):
  points=[]
  for item in node:
   if item.tag.endswith('polygon') or item.tag.endswith('polyline'):points+=svg_points(item.get('points',''))
   elif item.tag.endswith('path'):points+=svg_points(item.get('d',''))
  xs,ys=zip(*points);box=(min(xs)-3,min(ys)-3,max(xs)+3,max(ys)+3);boxes.append(box)
  node_boxes[node.find('s:title',ns).text]=box
 placed=[];label_layers=[]
 for edge in root.findall('.//s:g[@class="edge"]',ns):
  number=int(edge.get('id').replace('edge',''))-1;label=labels[number]
  name,field=fields[number]
  if field['fk']==name:
   left,top,right,bottom=node_boxes[name];x=right-3
   y1=top+(bottom-top)*.14;y2=top+(bottom-top)*.34;outer=x+80
   for item in list(edge):
    if not item.tag.endswith('title'):edge.remove(item)
   ET.SubElement(edge,f'{{{SVG_NS}}}path',d=f'M{x+20},{y1} L{outer},{y1} L{outer},{y2} L{x+20},{y2}',fill='none',stroke='#333333')
   # Optional parent (circle/bar), and optional child (circle/bar or circle/fork).
   for y,many in [(y1,False),(y2,endpoints(name,field)[1]=='0..*')]:
    ET.SubElement(edge,f'{{{SVG_NS}}}line',x1=str(x),y1=str(y),x2=str(x+20),y2=str(y),stroke='#333333')
    if many:
     for delta in [-4,4]:ET.SubElement(edge,f'{{{SVG_NS}}}line',x1=str(x+8),y1=str(y),x2=str(x),y2=str(y+delta),stroke='#333333')
    else:
     ET.SubElement(edge,f'{{{SVG_NS}}}line',x1=str(x+3),y1=str(y-4),x2=str(x+3),y2=str(y+4),stroke='#333333')
    ET.SubElement(edge,f'{{{SVG_NS}}}circle',cx=str(x+14),cy=str(y),r='3.4',fill='white',stroke='#333333')
  route=edge.find('s:path',ns);points=svg_points(route.get('d'))
  segments=[]
  for a,b in zip(points,points[1:]):
   length=abs(a[0]-b[0])+abs(a[1]-b[1])
   if length>24:segments.append((length,a,b))
  width=stringWidth(label,'Helvetica',11)+10;candidates=[]
  for length,a,b in segments:
   for fraction in [.5,.4,.6,.3,.7,.2,.8,.1,.9,.05,.95]:
    x=a[0]+fraction*(b[0]-a[0]);y=a[1]+fraction*(b[1]-a[1])
    box=(x-width/2,y-8,x+width/2,y+8)
    penalty=100000*sum(overlaps(box,n) for n in boxes)+10000*sum(overlaps(box,n) for n in placed)
    candidates.append((penalty+abs(fraction-.5)*20-length*.01,x,y,box))
  assert candidates,(file,label)
  _,x,y,box=min(candidates)
  assert not any(overlaps(box,n) for n in boxes),(file,label,'label overlaps table')
  placed.append(box)
  for old in list(edge.findall('s:text',ns)):edge.remove(old)
  layer=ET.Element(f'{{{SVG_NS}}}g',attrib={'class':'relationship-label','data-edge':edge.get('id')});label_layers.append(layer)
  ET.SubElement(layer,f'{{{SVG_NS}}}rect',x=str(box[0]),y=str(box[1]),width=str(width),height='16',fill='white',stroke='none')
  text=ET.SubElement(layer,f'{{{SVG_NS}}}text',x=str(x),y=str(y+3.5),attrib={'text-anchor':'middle','font-family':'Helvetica, Arial, sans-serif','font-size':'11'})
  text.text=label
 graph_group=root.find('s:g',ns)
 for layer in label_layers:graph_group.append(layer)
 vx,vy,vw,vh=map(float,root.attrib['viewBox'].split())
 root.set('viewBox',f'{vx} {vy} {vw+160} {vh}');root.set('width',f'{vw+160}pt')
 path.write_text(ET.tostring(root,encoding='unicode')+'\n')
position_labels('overview',list(schema))
for member,(_,names) in views.items():position_labels(f'owner_{member}',names)
# Fail if Graphviz omitted a label or relationship instead of producing a full diagram.
for member,(_,names) in views.items():
 external={f['fk'] for name in names for f in schema[name] if f['fk'] and f['fk'] not in names}
 svg=(TMP/f'owner_{member}.svg').read_text()
 assert svg.count('class="node"')==len(names)+len(external)+(2 if 'resource_state' in names else 0),member
 assert svg.count('class="edge"')==sum(bool(f['fk']) for name in names for f in schema[name]),member
svgout=ROOT/'output/svg';svgout.mkdir(parents=True,exist_ok=True)
# The overview contains one node per entity and every FK, including cross-domain links.
overview=(TMP/'overview.svg').read_text()
assert overview.count('class="node"')==N
assert overview.count('class="edge"')==sum(bool(f['fk']) for fs in schema.values() for f in fs)
(svgout/'Group4_ERD_Overview.svg').write_text(overview)
# A standalone vector PDF makes the large overview easy to zoom and share.
overview_drawing=svg2rlg(str(TMP/'overview.svg'))
overview_pdf=canvas.Canvas(str(OUT/'Group4_ERD_Overview.pdf'),pagesize=(overview_drawing.width+60,overview_drawing.height+85),invariant=1)
overview_pdf.setTitle('CloudNine Systems - connected ERD overview')
renderPDF.draw(overview_drawing,overview_pdf,30,55)
overview_pdf.setFont('Helvetica',10)
overview_pdf.drawString(30,30,'PK = primary key | FK = foreign key | ? = nullable | Crow-foot notation: double bar = one, circle/bar = zero or one, circle/fork = zero or many')
overview_pdf.save()
# Editable owner views render directly on GitHub; each repeats only necessary
# external keys. The .mmd file remains the full schema with all FK relationships.
parts=['# Group 4 - ERD ownership views',f'{N} tables; five tables per owner. Names will be mapped to A-D later.', 'Connected overview: every entity appears once, and all cross-domain foreign keys are connected.', '![All 20 entities and relationships](../../output/svg/Group4_ERD_Overview.svg)', '[Zoomable overview PDF](../../output/pdf/Group4_ERD_Overview.pdf)','[Submission PDF](../../output/pdf/Group4_ERD.pdf) | [Analysis and constraints](Group4_Analysis_Draft.md)','']
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
styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=10,leading=13,spaceAfter=7,allowWidows=0,allowOrphans=0,textColor=colors.black))
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
 'Crow-foot cardinalities: double bar = one; circle/bar = zero or one; circle/fork = zero or many.',
 'Each labelled line represents its child foreign key. Reference boxes repeat existing entities.',
 'Uniqueness, time intervals, allocation limits and billing rules: analysis report R1-R9.']
 domain_notes={
  'owner_A':['A client has at most one parent; client hierarchy cycles are prohibited.', 'An item selects at most one preferred location level; approved reservations must contain items.'],
  'owner_B':['Each data center belongs to one zone, and each zone belongs to one region.', 'Resources store capacity; occupancy is derived from allocations, not duplicated as a status.'],
  'owner_C':['Allocations must match the reservation item and deployment; overlapping fractions total at most one.', 'Replacement and state intervals retain history; actual usage and estimates are reported separately.'],
  'owner_D':['Each charge has exactly one context: usage, direct service, or adjustment of an earlier charge.', 'Shares belong to draft invoices; the payer is derived from the invoice. Issued invoices are immutable.'],
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
