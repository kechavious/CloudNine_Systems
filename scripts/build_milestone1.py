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
# Views follow the same A-D ownership as the Team Statement.
views={
 'A': ('Clients and reservations', ['CLIENT','USER_ACCOUNT','CLIENT_MEMBERSHIP','PROJECT','RESERVATION','RESERVATION_ITEM']),
 'B': ('Infrastructure and availability', ['REGION','AVAILABILITY_ZONE','DATA_CENTER','RESOURCE_TYPE','RESOURCE','RESOURCE_STATE']),
 'C': ('Deployments and services', ['DEPLOYMENT','RESOURCE_ALLOCATION','DEPLOYMENT_SERVICE','SERVICE','SERVICE_RATE']),
 'D': ('Metering and billing', ['USAGE_RECORD','BILLING_ACCOUNT','CHARGE','CHARGE_SHARE','INVOICE','INVOICE_LINE']),
}
owner={name:member for member,(_,names) in views.items() for name in names}
assert set(owner)==set(schema) and sum(len(v[1]) for v in views.values())==N
palette={'A':'#245f9c','B':'#267361','C':'#855a9e','D':'#ad6625'}
unique_groups={
 'AVAILABILITY_ZONE':'UNIQUE(region_id, name)',
 'DATA_CENTER':'UNIQUE(zone_id, name)',
 'RESOURCE':'UNIQUE(data_center_id, local_identifier)',
 'SERVICE_RATE':'UNIQUE(service_id, valid_from)',
 'CHARGE_SHARE':'UNIQUE(charge_id, billing_account_id)',
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
   key='/'.join(k for k,b in [('PK',field['pk']),('FK',bool(field['fk'])),('UK',field['unique'])] if b)
   rows.append(f'<TR><TD PORT="{field["name"]}" ALIGN="LEFT"><FONT POINT-SIZE="10">{key or "&#160;"}</FONT></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="10">{field["name"]}: {field["type"]}{" ?" if field["nullable"] else ""}</FONT></TD></TR>')
  if not ext and not overview and name in unique_groups:
   rows.append(f'<TR><TD COLSPAN="2" ALIGN="LEFT" BGCOLOR="#f1f5f9"><FONT POINT-SIZE="9">{unique_groups[name]}</FONT></TD></TR>')
  dot.append(f'{name} [label=<<TABLE BORDER="1" COLOR="#c6d0dc" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6">'+''.join(rows)+'</TABLE>>];')
 for name in names:
  for field in schema[name]:
   target=field['fk']
   if not target: continue
   # The overview omits audit-actor and recursive links. Every FK, including
   # these omitted links, is present in its owned-table detail view.
   if overview and (target==name or target=='USER_ACCOUNT' and name!='CLIENT_MEMBERSHIP'):
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
    parts.append(f'    {field["fk"]} {left}--{right} {name} : {field["name"]}')
 for name in names+external:
  parts.append(f'    {name} {{')
  for field in schema[name]:
   if name in external and not field['pk']:continue
   flags=', '.join(k for k,b in [('PK',field['pk']),('FK',bool(field['fk'])),('UK',field['unique'])] if b)
   parts.append(f'        {field["type"]} {field["name"]}'+(' '+flags if flags else '')+(' "nullable"' if field['nullable'] else ''))
  parts.append('    }')
 parts += ['```','']
(DOC/'Group4_ERD_Views.md').write_text('\n'.join(parts)+'\n')
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
# ERD submission: guide, all-table overview, four owned-table views, constraints.
c=canvas.Canvas(str(OUT/'Group4_ERD.pdf'),pagesize=letter)
c.setTitle('Group 4 - CloudNine Systems - 23-table ERD')
c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',27);c.drawString(48,714,'CloudNine Systems')
c.setFont('Helvetica-Bold',17);c.drawString(48,684,'Group 4 | Milestone 1 | ERD')
c.setFont('Helvetica',11);c.drawString(48,650,'23 core tables. Four work packages. One connected logical design.')
c.setFont('Helvetica-Bold',12);c.drawString(48,612,'Core workflow')
flow=['Client requests -> reservation and items -> deployment and allocation', 'Provisioned service -> usage -> charge -> payer share -> invoice']
for i,text in enumerate(flow):c.setFont('Helvetica',10);c.drawString(48,588-i*20,text)
y=524
for member,(title,names) in views.items():
 c.setFillColor(colors.HexColor(palette[member]));c.roundRect(48,y-8,30,27,4,fill=1,stroke=0)
 c.setFillColor(colors.white);c.setFont('Helvetica-Bold',12);c.drawString(59,y,member)
 c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',11);c.drawString(90,y+5,f'Member {member}: {title}')
 c.setFont('Helvetica',10);c.drawString(90,y-12,f'{len(names)} tables | Detailed view: page {list(views).index(member)+3}');y-=66
notes=['Page 2: all 23 entities, primary keys and principal domain relationships.',
       'Pages 3-6: every owned attribute and every FK, including actors and self-links.',
       'Page 7: composite uniqueness and important constraints.',
       '1 = exactly one; 0..1 = optional one; 0..* = zero or more.',
       'PK = primary key; FK = foreign key; UK = single-column unique key.',
       '? = nullable; gray boxes = external references, not duplicate tables.',
       'All money is USD; all timestamps are UTC.',
       '3NF reasoning and scope assumptions are in the draft analysis report.']
for text in notes:c.setFillColor(colors.HexColor('#475569'));c.setFont('Helvetica',9);c.drawString(48,y,text);y-=19
c.setFont('Helvetica',8);c.drawString(48,28,'Group 4 | Design draft | Names and member acknowledgment pending');c.drawRightString(564,28,'1 / 7');c.showPage()
def draw_graph(file,title,subtitle,page):
 d=svg2rlg(str(TMP/f'{file}.svg'))
 w=max(792,d.width+80);h=max(612,d.height+145)
 c.setPageSize((w,h));c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',21);c.drawString(40,h-37,title)
 c.setFont('Helvetica',10);c.drawString(40,h-59,subtitle)
 renderPDF.draw(d,c,(w-d.width)/2,48)
 c.setFont('Helvetica',9);c.drawString(40,23,'Group 4 | CloudNine Systems | PK / FK / UK | ? nullable | 1 / 0..1 / 0..* multiplicities')
 c.drawRightString(w-40,23,f'{page} / 7');c.showPage()
draw_graph('overview','All-table overview | 23 entities','A = clients / requests; B = resources; C = deployments / services; D = usage / billing. Actor and recursive FKs appear in detail views.',2)
for i,(member,(title,names)) in enumerate(views.items(),3):
 draw_graph(f'owner_{member}',f'Member {member} | {title}',f'{len(names)} owned tables. Gray boxes reference other owners. Lines connect parent PKs to child FKs.',i)
c.setPageSize(letter)
c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',22);c.drawString(48,714,'Keys and integrity rules')
constraints=[
 ('Composite UNIQUE constraints', [name+': '+rule for name,rule in unique_groups.items()]),
 ('Exclusive choices (XOR)', ['RESERVATION_ITEM: at most one preferred location level.', 'CHARGE: exactly one of usage_id, deployment_service_id,', 'or adjustment_of_charge_id. Metered charges require service_rate_id.']),
 ('Lifecycle and financial rules', ['Approved reservations contain items; issued invoices contain lines.', 'Resource type, minimum capacity, dates and mandatory locations must match.', 'Concurrent assigned fractions cannot exceed one per resource.', 'Concurrent item assignments cannot exceed the requested instance count.', 'State intervals for the same resource cannot overlap.', 'Final shares total the charge; posted charges and shares retain history.', 'An invoice line must reference a final share for the same payer account.', 'A share appears on at most one invoice (INVOICE_LINE PK/FK).']),
 ('History and normalization', ['Allocation, availability, rate and usage-correction history are retained.', 'Configuration lineage, reservation revisions and full event logs are deferred.', 'Do not repeat region or zone in RESOURCE, or deployment in USAGE_RECORD.', 'Do not repeat invoice membership or a billing rule in CHARGE_SHARE.', 'Temporal, cross-table and aggregate rules need transactional checks.', 'See analysis sections 3-5 for dependencies, assumptions and limitations.']),
]
y=673
for heading,items in constraints:
 c.setFillColor(colors.HexColor('#16324f'));c.setFont('Helvetica-Bold',12);c.drawString(48,y,heading);y-=23
 for item in items:
  c.setFillColor(colors.HexColor('#475569'));c.setFont('Helvetica',9);c.drawString(56,y,item);y-=18
 y-=17
c.setFont('Helvetica',8);c.drawString(48,28,'Group 4 | Logical design | All 23 tables have a primary key');c.drawRightString(564,28,'7 / 7');c.showPage();c.save()
report=(DOC/'Group4_Analysis_Draft.md').read_text()
team=(DOC/'Group4_Team_Statement.md').read_text()
(DOC/'Group4_Analysis_Draft.md').write_text(report)
(DOC/'Group4_Team_Statement.md').write_text(team)
pdf_text(report,OUT/'Group4_Analysis_Draft.pdf');pdf_text(team,OUT/'Group4_Team_Statement.pdf')
print(f'Created {N}-table schema, four owner views, seven-page ERD, analysis and team statement.')
