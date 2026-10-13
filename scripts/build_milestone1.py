from pathlib import Path
import re, html, subprocess
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
raw={'Clients and people': {'CLIENT': 'client_id:int '
                                  'PK;parent_client_id:int->CLIENT?;name:text;client_type:text;contact_email:text;qualification_note:text?',
                        'USER_ACCOUNT': 'user_id:int PK;name:text;email:text '
                                        'UK;account_kind:text;staff_role:text?;status:text',
                        'CLIENT_MEMBERSHIP': 'membership_id:int '
                                             'PK;client_id:int->CLIENT;user_id:int->USER_ACCOUNT;role:text;valid_from:timestamp;valid_to:timestamp?',
                        'PROJECT': 'project_id:int PK;client_id:int->CLIENT;name:text'},
 'Infrastructure and availability': {'REGION': 'region_id:int PK;name:text UK;regulatory_note:text',
                                     'AVAILABILITY_ZONE': 'zone_id:int '
                                                          'PK;region_id:int->REGION;name:text;redundancy_note:text;connectivity_note:text',
                                     'DATA_CENTER': 'data_center_id:int '
                                                    'PK;zone_id:int->AVAILABILITY_ZONE;name:text;location:text',
                                     'RESOURCE_TYPE': 'resource_type_id:int PK;name:text '
                                                      'UK;intended_workload:text',
                                     'RESOURCE': 'resource_id:int '
                                                 'PK;resource_type_id:int->RESOURCE_TYPE;data_center_id:int->DATA_CENTER;local_identifier:text;performance_tier:text;vcpu_count:int;memory_gib:decimal;storage_gib:decimal;network_gbps:decimal',
                                     'RESOURCE_STATE': 'state_id:int '
                                                       'PK;resource_id:int->RESOURCE;status:text;reason:text;starts_at:timestamp;ends_at:timestamp?;recorded_by_user_id:int->USER_ACCOUNT?'},
 'Reservations and requests': {'RESERVATION': 'reservation_id:int '
                                              'PK;client_id:int->CLIENT;created_at:timestamp;start_time:timestamp;end_time:timestamp;status:text;agreement_note:text?;approved_by_user_id:int->USER_ACCOUNT?',
                               'RESERVATION_ITEM': 'reservation_item_id:int '
                                                   'PK;reservation_id:int->RESERVATION;resource_type_id:int->RESOURCE_TYPE;quantity:int;min_vcpu:int;min_memory_gib:decimal;min_storage_gib:decimal;min_network_gbps:decimal;preferred_region_id:int->REGION?;preferred_zone_id:int->AVAILABILITY_ZONE?;preferred_data_center_id:int->DATA_CENTER?;location_mode:text'},
 'Deployments and assignments': {'DEPLOYMENT': 'deployment_id:int '
                                               'PK;reservation_id:int->RESERVATION;project_id:int->PROJECT?;name:text;workload_note:text;started_at:timestamp?;ended_at:timestamp?;confidentiality_level:text;status:text;priority:int;scaling_mode:text',
                                 'RESOURCE_ALLOCATION': 'allocation_id:int '
                                                        'PK;deployment_id:int->DEPLOYMENT;reservation_item_id:int->RESERVATION_ITEM;resource_id:int->RESOURCE;capacity_fraction:decimal;starts_at:timestamp;ends_at:timestamp?;allocation_status:text;supersedes_allocation_id:int->RESOURCE_ALLOCATION?;change_reason:text;assigned_by_user_id:int->USER_ACCOUNT?',
                                 'DEPLOYMENT_SERVICE': 'deployment_service_id:int '
                                                       'PK;deployment_id:int->DEPLOYMENT;service_id:int->SERVICE;starts_at:timestamp;ends_at:timestamp?'},
 'Services, rates and metering': {'SERVICE': 'service_id:int PK;name:text UK;service_type:text;billing_unit:text',
                                  'SERVICE_RATE': 'service_rate_id:int '
                                                  'PK;service_id:int->SERVICE;valid_from:timestamp;valid_to:timestamp?;unit_price:decimal',
                                  'USAGE_RECORD': 'usage_id:int '
                                                  'PK;deployment_service_id:int->DEPLOYMENT_SERVICE;allocation_id:int->RESOURCE_ALLOCATION?;quantity:decimal;period_start:timestamp;period_end:timestamp;record_type:text;recorded_at:timestamp;supersedes_usage_id:int->USAGE_RECORD '
                                                  'UK?'},
 'Billing and invoices': {'BILLING_ACCOUNT': 'billing_account_id:int '
                                             'PK;responsible_client_id:int->CLIENT;name:text;billing_contact_user_id:int->USER_ACCOUNT?',
                          'CHARGE': 'charge_id:int PK;usage_id:int->USAGE_RECORD '
                                    'UK?;deployment_service_id:int->DEPLOYMENT_SERVICE?;service_rate_id:int->SERVICE_RATE?;adjustment_of_charge_id:int->CHARGE?;authorized_by_user_id:int->USER_ACCOUNT?;charge_type:text;amount:decimal;status:text;reason:text;created_at:timestamp',
                          'CHARGE_SHARE': 'charge_share_id:int '
                                          'PK;charge_id:int->CHARGE;billing_account_id:int->BILLING_ACCOUNT;allocated_amount:decimal',
                          'INVOICE': 'invoice_id:int '
                                     'PK;billing_account_id:int->BILLING_ACCOUNT;issued_at:timestamp;due_at:timestamp;status:text',
                          'INVOICE_LINE': 'charge_share_id:int PK->CHARGE_SHARE;invoice_id:int->INVOICE'}}
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
node='''const fs=require('fs'); const {instance}=require('/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@viz-js/viz'); (async()=>{const v=await instance();for(let i=1;i<=Number(process.argv[2]);i++){const p=process.argv[1]+'/module'+i;fs.writeFileSync(p+'.svg',v.renderString(fs.readFileSync(p+'.dot','utf8'),{format:'svg'}));}})();'''
subprocess.run(['/Users/kangzhengzou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','-e',node,str(TMP),str(len(modules))],check=True)
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
# ERD: cover + detailed vector module pages. Page dimensions preserve legibility.
c=canvas.Canvas(str(OUT/'Group4_ERD.pdf'),pagesize=letter)
c.setTitle('Group 4 - CloudNine Systems - 3NF ERD')
c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',26);c.drawString(48,710,'CloudNine Systems');c.setFont('Helvetica-Bold',18);c.drawString(48,680,'Group 4 | Milestone 1 ERD')
intro=[f'{N} tables organized into {len(modules)} connected modules.','Logical relational design in Third Normal Form (3NF).','Each module page shows all owned attributes and incoming FK relationships.','Gray entities are references to tables fully defined on another module page.','Relationship ends: 1 = required parent; 0..1 = optional parent;','0..* = zero or more children; 0..1 child = unique foreign key.','PK = primary key; FK = foreign key; UK = additional unique key.','? means nullable. Composite PKs are marked on every participating column.','Minimum child counts are enforced by lifecycle rules, not by ordinary FKs.','Composite unique keys, XOR, time and accounting rules appear in the report.','All monetary values are USD. All timestamps are UTC.','The editable Mermaid and generation script accompany this PDF.']
y=640
for line in intro:
 c.setFont('Helvetica',10);c.drawString(48,y,line);y-=21
for i,module in enumerate(modules,1):
 c.setFont('Helvetica',11);c.drawString(48,y,f'{i+2}. {module}');y-=22
c.setFont('Helvetica',8);c.drawString(48,30,'GROUP 4 | DESIGN DRAFT | Team roster and adoption pending');c.showPage()
# Compact conceptual overview: detailed FK relationships remain on module pages.
c.setPageSize((792,612))
c.setFillColor(colors.HexColor('#16324f')); c.setFont('Helvetica-Bold',22)
c.drawString(36,570,'Core workflow overview')
c.setFont('Helvetica',11); c.drawString(36,548,'Read this first; detailed entities, keys and cardinalities follow on the module pages.')
boxes=[(40,420,'CLIENT','Who requests the work?'),(285,420,'RESERVATION','What capacity is requested?'),(530,420,'DEPLOYMENT','What work is running?'),(530,290,'RESOURCE_ALLOCATION','Which resources are assigned?'),(285,290,'USAGE_RECORD','What was consumed?'),(40,290,'CHARGE','What does it cost?'),(40,160,'CHARGE_SHARE','Which account pays each share?'),(285,160,'INVOICE','What is billed to that account?')]
for x,y,title,subtitle in boxes:
 c.setFillColor(colors.HexColor('#edf3f8')); c.setStrokeColor(colors.HexColor('#16324f')); c.roundRect(x,y,220,72,8,fill=1,stroke=1)
 c.setFillColor(colors.HexColor('#16324f')); c.setFont('Helvetica-Bold',11);c.drawString(x+10,y+45,title)
 c.setFont('Helvetica',9);c.drawString(x+10,y+23,subtitle)
def arrow(x1,y1,x2,y2):
 c.setStrokeColor(colors.HexColor('#64748b')); c.setLineWidth(1.4);c.line(x1,y1,x2,y2)
 import math
 angle=math.atan2(y2-y1,x2-x1)
 for delta in (-0.45,0.45): c.line(x2,y2,x2-8*math.cos(angle+delta),y2-8*math.sin(angle+delta))
for coords in [(260,456,285,456),(505,456,530,456),(640,420,640,362),(530,326,505,326),(285,326,260,326),(150,290,150,232),(260,196,285,196)]: arrow(*coords)
c.setFont('Helvetica',10); c.drawString(40,108,'Conceptual flow only: intermediate service, pricing and invoice-line tables are omitted here.')
c.drawString(40,89,f'The following {len(modules)} module pages define the {N}-table model and FK multiplicities.')
c.setFont('Helvetica',9); c.drawString(36,22,'Group 4 | CloudNine Systems | ERD page 2 of 8'); c.showPage()
for i,module in enumerate(modules,1):
 d=svg2rlg(str(TMP/f'module{i}.svg'))
 w=max(792,d.width+72);h=max(612,d.height+120)
 c.setPageSize((w,h));c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',20);c.drawString(36,h-35,f'{i}. {module}')
 c.setFont('Helvetica',10);c.drawString(36,h-55,'PK / FK / UK | ? nullable | Gray = external reference | Edge labels give multiplicity at each end')
 renderPDF.draw(d,c,(w-d.width)/2,45)
 c.setFont('Helvetica',9);c.drawString(36,22,f'Group 4 | CloudNine Systems | ERD page {i+2} of {len(modules)+2}');c.showPage()
c.save()
report=(DOC/'Group4_Analysis_Draft.md').read_text()
team=(DOC/'Group4_Team_Statement.md').read_text()
(DOC/'Group4_Analysis_Draft.md').write_text(report)
(DOC/'Group4_Team_Statement.md').write_text(team)
pdf_text(report,OUT/'Group4_Analysis_Draft.pdf');pdf_text(team,OUT/'Group4_Team_Statement.pdf')
print(f'Created {N}-table schema, {len(modules)} ERD modules, analysis and team statement.')
