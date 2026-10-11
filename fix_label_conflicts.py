#!/usr/bin/env python3
"""Conservatively resolve duplicate 30/31 source-label conflicts in Chandamama Phase-2 outputs.

No replacement plot numbers are invented. The visually-transcribed conflicts P108/P120
are kept searchable by their source transcription but have a blank assigned plot_number
until a human checks the approved plan.
"""
from pathlib import Path
import csv, json, re, zipfile, shutil

ROOT = Path(__file__).resolve().parent
HTML = ROOT / 'chandamama_phase2_interactive_v5.html'
CSV = ROOT / 'plot_candidates_with_plot_numbers.csv'
GEO = ROOT / 'plot_candidates_with_plot_numbers.geojson'
SVG = ROOT / 'plot_number_review_overlay.svg'
DIAG = ROOT / 'label_alignment_diagnostics.json'

# Canonical, PDF-text-matched records remain plot 30=P152 and 31=P151.
# P108 and P120 had only a visual reading which conflicts with those canonical labels.
conflicts = {'P108': '31', 'P120': '30'}
canon = {'P151': '31', 'P152': '30'}

# ---------------- HTML ----------------
s = HTML.read_text(encoding='utf-8')
# Alter the embedded plot JSON rather than doing brittle edits within a minified object.
start = s.index('const plotShapes=') + len('const plotShapes=')
end = s.index(';\nconst ids=', start)
plots = json.loads(s[start:end])
for p in plots:
    pid = p['id']
    if pid in conflicts:
        p['officialNumber'] = ''
        p['sourceLabel'] = conflicts[pid]
        p['numberSource'] = 'visual transcription only; conflicts with PDF-text-matched label — needs confirmation'
        p['textMatched'] = False
        p['duplicateNumber'] = False
        p['labelConflict'] = True
    elif pid in canon:
        p['officialNumber'] = canon[pid]
        p['sourceLabel'] = canon[pid]
        p['duplicateNumber'] = False
        p['labelConflict'] = False
    else:
        p.setdefault('sourceLabel', p.get('officialNumber', ''))
        p['labelConflict'] = False
s = s[:start] + json.dumps(plots, separators=(',', ':')) + s[end:]

# Correct static SVG labels and ARIA labels on the initial display.
for pid, raw in conflicts.items():
    # Replace the path aria-label and label styling/text for each candidate.
    pat = re.compile(r'(<path class="plot" id="shape-' + pid + r'".*?aria-label=")[^"]*("/><text class=")[^"]*(" id="label-' + pid + r'"[^>]*>)[^<]*(</text>)')
    s, n = pat.subn(lambda m: m.group(1) + f'Candidate {pid}; source label {raw} needs review' + m.group(2) + 'plot-label needs-review-label' + m.group(3) + f'{pid}?' + m.group(4), s, count=1)
    if n != 1:
        raise RuntimeError(f'Could not patch static SVG label for {pid}: {n}')
for pid, raw in canon.items():
    pat = re.compile(r'(<path class="plot" id="shape-' + pid + r'".*?aria-label=")[^"]*("/><text class=")[^"]*(" id="label-' + pid + r'"[^>]*>)[^<]*(</text>)')
    s, n = pat.subn(lambda m: m.group(1) + f'Plot {raw}; candidate {pid}' + m.group(2) + 'plot-label text-matched-label' + m.group(3) + raw + m.group(4), s, count=1)
    if n != 1:
        raise RuntimeError(f'Could not patch static canonical label for {pid}: {n}')

# UI headings and explanation: two unassigned source label conflicts, not four duplicate IDs.
s = s.replace('Detected plot polygons · 155 plot candidates · all labels transcribed · 106 matched to PDF text · duplicate labels flagged',
              'Detected plot polygons · 155 candidates · 106 labels matched to PDF text · 2 source-label conflicts held for review')
s = s.replace('<div class="stat"><b>153</b><span>Distinct labels</span></div><div class="stat"><b>4</b><span>Entries with duplicate IDs</span></div>',
              '<div class="stat"><b>153</b><span>Assigned unique labels</span></div><div class="stat"><b>2</b><span>Labels to confirm</span></div>')
s = s.replace('Labels were transcribed from the 155 oval markers. 106 also matched selectable PDF text. The source plan repeats plot labels 30 and 31 (four polygons are marked with *); resolve those before sale records. All boundaries are CAD-derived candidates and need visual confirmation; drawing-unit areas are not official sale areas.',
              'Labels were transcribed from 155 oval markers; 106 also matched selectable PDF text. Two visual readings conflict with text-matched labels: P108 was read as 31 and P120 as 30. Their official plot-number fields are intentionally blank until checked against the approved plan; raw readings remain searchable. All boundaries are CAD-derived candidates and still need visual confirmation.')
s = s.replace('Local-only review prototype: this browser stores data locally, with no staff sync or login. Export backups regularly. Confirm all polygon boundaries against the approved plan and resolve the duplicate plot labels marked with * before recording sales.',
              'Local-only review prototype: this browser stores data locally, with no staff sync or login. Export backups regularly. Confirm all polygon boundaries against the approved plan. Do not enter sales under P108/P120 until their official numbers are confirmed.')
s = s.replace("const storageKey='chandamama-phase2-inventory-v3-verified-labels';", "const storageKey='chandamama-phase2-inventory-v4-label-conflict-review';\nconst legacyStorageKey='chandamama-phase2-inventory-v3-verified-labels';")
s = s.replace("const defaults=(id)=>({plotNumber:(plotShapes.find(p=>p.id===id)?.officialNumber||''),status:'Available',buyer:'',phone:'',plotSize:'',price:'',paid:'',notes:''});\nlet records={};\ntry{records=JSON.parse(localStorage.getItem(storageKey)||'{}')||{}}catch(e){records={}}\nfor(const id of ids) records[id]={...defaults(id),...(records[id]||{})};",
"const defaults=(id)=>({plotNumber:(plotShapes.find(p=>p.id===id)?.officialNumber||''),status:'Available',buyer:'',phone:'',plotSize:'',price:'',paid:'',notes:''});\nlet records={};\ntry{records=JSON.parse(localStorage.getItem(storageKey)||'{}')||{};if(!Object.keys(records).length){records=JSON.parse(localStorage.getItem(legacyStorageKey)||'{}')||{};for(const [id,raw] of [['P108','31'],['P120','30']]){const r=records[id];if(r&&String(r.plotNumber||'')===raw&&!r.buyer&&!r.phone&&!r.plotSize&&!r.price&&!r.paid&&!r.notes)r.plotNumber='';}}}catch(e){records={}}\nfor(const id of ids) records[id]={...defaults(id),...(records[id]||{})};")
# Search by candidate ID, assigned number, source reading, buyer and phone.
s = s.replace("return [p.id,r.plotNumber,r.buyer,r.phone,r.status].some(v=>String(v||'').toLowerCase().includes(q))",
              "return [p.id,r.plotNumber,p.sourceLabel,p.officialNumber,r.buyer,r.phone,r.status].some(v=>String(v||'').toLowerCase().includes(q))")
# Show candidates and source label in list instead of falsely suggesting an official number.
s = s.replace("left.textContent=(r.plotNumber?`Plot ${r.plotNumber} · `:'')+p.id;", "left.textContent=(r.plotNumber?`Plot ${r.plotNumber} · `:(p.labelConflict?`VERIFY label ${p.sourceLabel} · `:p.officialNumber?`Plot ${p.officialNumber} · `:''))+p.id;")
# Map labels respond to the official editable input. Conflicting candidates get P108?/P120? until user enters a number.
s = s.replace("const display=(r.plotNumber||p.officialNumber||id)+ (p.duplicateNumber?'*':'');label.textContent=display;label.style.fontSize=display.length>4?'0.8px':'1.15px';label.classList.toggle('duplicate-label',p.duplicateNumber);label.classList.toggle('text-matched-label',p.textMatched&&!p.duplicateNumber);label.classList.toggle('visually-transcribed-label',!p.textMatched&&!p.duplicateNumber);",
"const display=r.plotNumber||(p.labelConflict?`${p.id}?`:p.officialNumber||id);label.textContent=display;label.style.fontSize=display.length>4?'0.8px':'1.15px';label.classList.toggle('duplicate-label',false);label.classList.toggle('needs-review-label',p.labelConflict&&!r.plotNumber);label.classList.toggle('text-matched-label',p.textMatched&&!p.labelConflict);label.classList.toggle('visually-transcribed-label',!p.textMatched&&!p.labelConflict);")
# Selected title and description make the conflict explicit.
s = s.replace("document.getElementById('selectedTitle').textContent=(r.plotNumber?`Plot ${r.plotNumber}`:(p.officialNumber?`Plot ${p.officialNumber}${p.duplicateNumber?'*':''}`:id));document.getElementById('selectedMeta').textContent=`${id} · ${p.numberSource}${p.duplicateNumber?' · DUPLICATE LABEL IN SOURCE PLAN':''} · geometry area ${p.area.toFixed(2)} drawing units²`;",
"document.getElementById('selectedTitle').textContent=r.plotNumber?`Plot ${r.plotNumber}`:(p.labelConflict?`Candidate ${id} — confirm plot number`:(p.officialNumber?`Plot ${p.officialNumber}`:id));document.getElementById('selectedMeta').textContent=`${id} · ${p.labelConflict?`SOURCE LABEL CONFLICT: visually read as ${p.sourceLabel}; official plot number left blank pending confirmation`:p.numberSource} · geometry area ${p.area.toFixed(2)} drawing units²`;")
# Other title update sites in buyer/status/field handlers.
s = s.replace("document.getElementById('selectedTitle').textContent=(records[selectedId].plotNumber?`Plot ${records[selectedId].plotNumber}`:(p.officialNumber?`Plot ${p.officialNumber}${p.duplicateNumber?'*':''}`:selectedId));",
"document.getElementById('selectedTitle').textContent=records[selectedId].plotNumber?`Plot ${records[selectedId].plotNumber}`:(p.labelConflict?`Candidate ${selectedId} — confirm plot number`:(p.officialNumber?`Plot ${p.officialNumber}`:selectedId));")
s = s.replace("document.getElementById('selectedTitle').textContent=r.plotNumber?`Plot ${r.plotNumber}`:(p.officialNumber?`Plot ${p.officialNumber}${p.duplicateNumber?'*':''}`:selectedId);",
"document.getElementById('selectedTitle').textContent=r.plotNumber?`Plot ${r.plotNumber}`:(p.labelConflict?`Candidate ${selectedId} — confirm plot number`:(p.officialNumber?`Plot ${p.officialNumber}`:selectedId));")
# Add metadata to exported CSV and JSON.
s = s.replace("pdfTextMatchedPlotNumbers:106,visuallyTranscribedPlotNumbers:49,duplicatePlotLabels:['30','31'],warning:'All boundaries are CAD-derived candidates and require plan review. Source plan repeats the labels 30 and 31; confirm them before sales/payment records.'",
              "pdfTextMatchedPlotNumbers:106,visuallyTranscribedPlotNumbers:49,labelConflicts:[{candidateId:'P108',sourceLabel:'31',officialPlotNumber:''},{candidateId:'P120',sourceLabel:'30',officialPlotNumber:''}],warning:'P108 and P120 have visually transcribed source-label conflicts. Official plot numbers are blank pending confirmation; do not treat their source readings as assigned plot numbers.'")
s = s.replace("const keys=['candidateId','plotNumber','plotNumberSource','duplicatePlotNumberInSource','status','buyer','phone','plotSize','price','paid','balance','geometryAreaDrawingUnits2','notes'];",
              "const keys=['candidateId','plotNumber','sourceLabelTranscription','labelReviewRequired','plotNumberSource','status','buyer','phone','plotSize','price','paid','balance','geometryAreaDrawingUnits2','notes'];")
s = s.replace("const vals=[p.id,r.plotNumber,p.numberSource,p.duplicateNumber?'Yes':'No',r.status,r.buyer,r.phone,r.plotSize,r.price,r.paid,Math.max(0,Number(r.price||0)-Number(r.paid||0)).toFixed(2),p.area,r.notes]",
              "const vals=[p.id,r.plotNumber,p.sourceLabel||p.officialNumber||'',p.labelConflict?'Yes':'No',p.numberSource,r.status,r.buyer,r.phone,r.plotSize,r.price,r.paid,Math.max(0,Number(r.price||0)-Number(r.paid||0)).toFixed(2),p.area,r.notes]")
s = s.replace("records[id]={...defaults()};", "records[id]=defaults(id);")
HTML.write_text(s, encoding='utf-8')

# ---------------- CSV ----------------
with CSV.open(newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
    old_fields = list(rows[0].keys()) if rows else []
new_fields = ['candidate_id','plot_number','source_label_transcription','label_review_required','plot_number_source','pdf_text_matched','duplicate_plot_number_in_source','area_drawing_units2','width','height','vertices','marker_x','marker_y','boundary_review_required']
for r in rows:
    pid = r['candidate_id']
    raw = r.get('plot_number','')
    r['source_label_transcription'] = raw
    r['label_review_required'] = 'True' if pid in conflicts else 'False'
    if pid in conflicts:
        r['plot_number'] = ''
        r['plot_number_source'] = 'visual transcription only; conflicts with PDF-text-matched label — needs confirmation'
        r['pdf_text_matched'] = 'False'
        r['duplicate_plot_number_in_source'] = 'False'
    elif pid in canon:
        r['plot_number'] = canon[pid]
        r['duplicate_plot_number_in_source'] = 'False'
with CSV.open('w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=new_fields); w.writeheader(); w.writerows(rows)

# ---------------- GeoJSON ----------------
geo = json.loads(GEO.read_text(encoding='utf-8'))
for feat in geo.get('features', []):
    p = feat.get('properties', {})
    pid = p.get('candidate_id')
    p['source_label_transcription'] = p.get('plot_number','')
    p['label_review_required'] = pid in conflicts
    if pid in conflicts:
        p['plot_number'] = ''
        p['plot_number_source'] = 'visual transcription only; conflicts with PDF-text-matched label — needs confirmation'
        p['plot_number_text_matched'] = False
        p['duplicate_plot_number_in_source'] = False
    elif pid in canon:
        p['plot_number'] = canon[pid]
        p['duplicate_plot_number_in_source'] = False
GEO.write_text(json.dumps(geo, indent=2), encoding='utf-8')

# ---------------- SVG review overlay ----------------
svg = SVG.read_text(encoding='utf-8')
# SVG entries are in candidate order: P108 precedes P120, P151 and P152.
def replace_first_label(s, old, new, color):
    pattern = r'(fill=")[^"]*(">)' + re.escape(old) + r'(</text>)'
    s2,n = re.subn(pattern, lambda m: m.group(1)+color+m.group(2)+new+m.group(3), s, count=1)
    if n != 1: raise RuntimeError(f'Overlay did not contain expected label {old!r}')
    return s2
# Current order by candidate id: P108 (31*), P120 (30*), P151 (31*), P152 (30*).
svg = replace_first_label(svg, '31*', 'P108?', '#9a3412')
svg = replace_first_label(svg, '30*', 'P120?', '#9a3412')
# Canonical PDF text matches are shown without stars and in their normal matched color.
svg = replace_first_label(svg, '31*', '31', '#153b6c')
svg = replace_first_label(svg, '30*', '30', '#153b6c')
SVG.write_text(svg, encoding='utf-8')

# Render SVG overlay PNG; use CairoSVG if available, otherwise matplotlib screenshot is optional.
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(ROOT/'plot_number_review_overlay.png'), output_width=2400)
except Exception as e:
    print('Could not regenerate PNG from SVG:', e)

# ---------------- Diagnostics ----------------
diag = {
 'polygon_candidates': 155,
 'pdf_text_matched_labels': 106,
 'visually_transcribed_labels': 49,
 'assigned_unique_plot_numbers': 153,
 'unassigned_label_conflicts': [
  {'candidate_id':'P108','source_label_transcription':'31','reason':'Visual transcription conflicts with a PDF-text-matched 31 at P151.'},
  {'candidate_id':'P120','source_label_transcription':'30','reason':'Visual transcription conflicts with a PDF-text-matched 30 at P152.'}
 ],
 'canonical_labels_retained': {'P151':'31','P152':'30'},
 'policy': 'No replacement plot numbers invented. Conflicting visual readings are kept in source_label_transcription and left blank in plot_number pending human confirmation.',
 'boundary_warning': 'Label conflict correction does not itself certify polygon boundaries. Review boundaries against the approved plan.'
}
DIAG.write_text(json.dumps(diag, indent=2), encoding='utf-8')

print(json.dumps({'html':str(HTML),'csv':str(CSV),'geojson':str(GEO),'review_svg':str(SVG),'diagnostics':str(DIAG),'conflicts_cleared':['P108','P120']},indent=2))
