import pandas as pd,re
M={'2026-01':('29a2740a-Miles_Driven_Jan.xlsx','Report','Vehicle','Distance'),
'2026-02':('d9d85dd7-February_Miles.xlsx','Report','Vehicle','Distance'),
'2026-03':('49f153a4-Miles_March.xlsx','Report','Vehicle','Distance'),
'2026-04':('595f62d5-April_Miles_sim.xlsx','Sheet1','Vehicle','Miles'),
'2026-05':('707f4e32-May_Miles_Geotab.xlsx','Report','Vehicle','Distance'),
'2026-06':('05bb13b8-June_Company_Miles_by_Asset_June.xlsx','Report','Vehicle','Distance'),
'2026-07':('6ce20970-Miles_Driven_July.xlsx','Report','Asset','Distance driven'),
'2026-08':('5ad0fae8-August_Miles_Driven.xlsx','Report','Vehicle','Distance'),
'2026-09':('17ea817c-Miles_September_2026.xlsx','Report','Vehicle','Distance')}
rows=[]
for m,(f,s,vc,dc) in M.items():
    d=pd.read_excel(f,sheet_name=s,dtype=str); d.columns=[c.strip() for c in d.columns]
    d=d[[vc,dc]].rename(columns={vc:'veh',dc:'mi'})
    d['month']=m; d['file_rows']=len(d)
    rows.append(d)
df=pd.concat(rows)
df['mi']=pd.to_numeric(df['mi'],errors='coerce')
df['veh']=df['veh'].astype(str).str.strip()
def parse(v):
    p=v.split('-')
    return (p[1],p[0],p[2] if len(p)>2 else None) if len(p)>=2 else (None,None,None)
df[['asset','pstore','sfx']]=df['veh'].apply(lambda v:pd.Series(parse(v)))
df.to_pickle('/tmp/claude-0/-home-claude/beabc8da-8639-59c1-85f4-c5bad2fd86c1/scratchpad/miles.pkl')
