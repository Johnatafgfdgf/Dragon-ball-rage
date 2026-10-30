#!/usr/bin/env python3
"""Inspect opt6 per-image evidence, also inside an exported Android log.
Usage: python3 scripts/analyze_fg_trace.py DragonRage-log-....txt [--json]
Missing ring history/driver feedback is unknown, not evidence of a dropped image.
"""
from pathlib import Path
import json,re,sys
text=Path(sys.argv[1]).read_text(errors='replace')
pattern=re.compile(r'^(FG_[A-Z_]+) t_ns=(\d+) id=(\d+) prev=(\d+) source=(\d+) epoch=(\d+) due_ns=(\d+) value=(-?\d+) detail=(\d+)(?: thread=(\d+))?$',re.M)
frames={};roll=[]
for m in pattern.finditer(text):
 stage=m[1];v=list(map(int,m.groups()[1:9]));t,i,previous,source,epoch,due,value,detail=v
 if stage=='FG_ROLLBACK':roll.append((t,epoch));continue
 if not i:continue
 f=frames.setdefault(i,{'id':i,'source':source,'previous':previous,'epoch':epoch,'events':[]})
 f['events'].append({'stage':stage,'t_ns':t,'due_ns':due,'value':value,'detail':detail})
def has(f,stage,predicate=lambda e:True):return any(e['stage']==stage and predicate(e) for e in f['events'])
def generated(f):return has(f,'FG_HISTORY',lambda e:e['value']==2) or has(f,'FG_COMPLETE',lambda e:e['detail']==2)
def complete(f):return has(f,'FG_COMPLETE',lambda e:e['value']>=-1)
def accepted(f):return has(f,'FG_PRESENT',lambda e:e['value'] in (0,1000001003))
def proof(f):return next((e['value'] for e in f['events'] if e['stage']=='FG_PROOF'),-1)
fs=list(frames.values());gs=[f for f in fs if generated(f)]
valid=[f for f in gs if complete(f) and proof(f)>=0 and not (proof(f)&2)]
presented=[f for f in valid if accepted(f) and (proof(f)&1)]
stale=[]
for f in gs:
 for e in f['events']:
  if e['stage']=='FG_SUBMIT' and any(t<e['t_ns'] and epoch>f['epoch'] for t,epoch in roll):stale.append(f['id'])
report={
 'scope':'Only retained bounded trace events; cumulative header covers the full run. Driver feedback is optional.',
 'retained_image_ids':len(fs),'generated_ids':len(gs),
 'generated_dispatches':sum(has(f,'FG_DISPATCH') for f in gs),
 'generated_gpu_complete_valid':len(valid),
 'generated_unique_present_success':len(presented),
 'all_image_present_success':sum(accepted(f) for f in fs),
 'driver_display_positive':sum(has(f,'FG_DISPLAY',lambda e:e['value']>0) for f in fs),
 'driver_display_explicit_zero':sum(has(f,'FG_DISPLAY',lambda e:e['value']==0) for f in fs),
 'completed_generated_without_present_success':sum(not accepted(f) for f in valid),
 'generated_plans_canceled_before_dispatch':sum(has(f,'FG_DROP') and not has(f,'FG_DISPATCH') for f in gs),
 'completed_endpoint_copies':sum(complete(f) and proof(f)>=0 and (proof(f)&2)!=0 for f in gs),
 'proof_unknown':sum(proof(f)<0 for f in fs if complete(f)),
 'rollback_epochs':len(roll),'generated_submits_after_epoch_invalidated':sorted(set(stale)),
 'verified_generated_present_ids':[f['id'] for f in presented],
 'limits':'A 256-sample GPU difference is evidence of different source content, not proof of scanout or all-pixel quality. A missing display report stays unknown.'}
print(json.dumps(report,indent=2,ensure_ascii=False))
