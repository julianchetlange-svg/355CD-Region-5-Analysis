import pandas as pd, numpy as np, json, sys
A = '/mnt/user-data/attachments/beabc8da-8639-59c1-85f4-c5bad2fd86c1/'
S = '/tmp/claude-0/-home-claude/beabc8da-8639-59c1-85f4-c5bad2fd86c1/scratchpad/'
LOCS = ['355CD', '355', '015', '033', '037', '041', '088', '089', '093', '097', '100', '103', '108']
CENTRAL = {'355CD', '355'}
WIN = [f'2025-{m:02d}' for m in (10, 11, 12)] + [f'2026-{m:02d}' for m in range(1, 10)]

# ---------- roster ----------
a = pd.read_excel(A + '76d1ece1-Current_Assets_7.xlsx', header=1, dtype=str)
a = a[a['Store Number'].isin(LOCS)].copy()
# 750049 excluded: being sold (confirmed Oct 29, 2026)
names = a.groupby('Store Number')['Store Name'].first().to_dict()
TRUCK = ['Tractor TA', 'Tractor SA', 'Pickup', "24' TA Flatbed", "20' Slide Flatbed", "12' Slide Flatbed", "24' Conveyor", "16' Conveyor"]
def cls(t):
    if t in TRUCK: return 'Truck'
    if 'Truck Mounted' in t: return 'TMFL'
    if 'Trailer' in t: return 'Trailer'
    return 'Forklift'
a['cls'] = a['Asset Template Name'].map(cls)
a['term'] = a.cls.map({'Truck': 60, 'Trailer': 60, 'Forklift': 84, 'TMFL': 84})
a['isd'] = pd.to_datetime(a['Asset Date of Origination'])

# ---------- depreciation (March file, summed by asset) ----------
dp = pd.read_excel(A + 'f93ae8cd-BA_-_McCoys_Asset_Depreciation_Forecast_Fleet_Detail.xlsx', sheet_name=1, dtype=str)
dp.columns = [c.strip() for c in dp.columns]
dp['id'] = dp['Asset Identifier'].str.strip(); dp['amt'] = dp['Depreciation Amount'].astype(float)
dep = dp.groupby('id').amt.sum().to_dict()
dep.update({'758005': 166407.25 / 60, '758011': 166407.25 / 60, '626005': 71123.99 / 60, '626003': 71123.99 / 60})
dep_src = {k: 'March 2026 file' for k in dp.id.unique()}
for k in ['758005', '758011', '626005', '626003']: dep_src[k] = 'Cost ÷ 60 (provided)'

# ---------- leases ----------
ls = pd.read_excel(A + 'a848caef-Current_Assets_8.xlsx', dtype=str)
lease = pd.to_numeric(ls['Asset Lease Fixed Rate'], errors='coerce')
lease = dict(zip(ls['Asset Name'], lease))
lease_note = {}
for k in ['380030', '380042', '380067', '380068']:
    lease[k] = 447.11; lease_note[k] = 'Rate missing; batch rate $447.11 used'
lease['747104'] = 250.0; lease_note['747104'] = 'Holding rental $250/mo'
lease['747106'] = 150.0; lease_note['747106'] = 'Holding rental $150/mo'

# ---------- flat rates ----------
FLAT = {'10K Yard Forklift': 1305.79, "12' Slide Flatbed": 1192.80, "16' Conveyor": 1841.10, "20' Slide Flatbed": 1216.97,
        "24' Conveyor": 2264.57, "24' TA Flatbed": 1981.47, '6K Yard Forklift': 1007.80, '8K Boxcar Forklift': 1343.23,
        '8K Yard Forklift': 1262.59, 'Flatbed Trailer': 914.99, 'Pickup': 995.46, 'Reach Truck': 1400.63,
        'Tractor SA': 1715.35, 'Tractor TA': 1741.26, 'Truck Mounted Forklift': 1152.43}

# ---------- maintenance (rolling 12: Oct25-Sep26) ----------
def ldm(f):
    d = pd.read_excel(A + f, dtype={'Asset Name': str, 'Subcontractor Invoice Reference Number': str})
    d.columns = [c.strip() for c in d.columns]
    d['dt'] = pd.to_datetime(d['Subcontractor Invoice Transaction Date'], format='ISO8601'); return d
T = 'Subcontractor Invoice Total'
mt = pd.concat([ldm('b4b61a20-Asset_Spend_Data_2025_11.xlsx'), ldm('101fbf67-Asset_Spend_Data_2026_.xlsx')])
mt = mt.drop_duplicates(['Subcontractor Invoice Reference Number', 'Asset Name', 'Work Order ID', T])
mtw = mt[(mt.dt >= '2025-10-01') & (mt.dt < '2026-10-01')]
# registration now comes from the fee file, so registration/inspection work orders leave maintenance
isreg = mtw['Work Order Category Full Path'].fillna('').str.contains('Regist', case=False)
reg_removed = mtw[isreg].groupby('Asset Name')[T].sum().to_dict()
mtw = mtw[~isreg]
maint = mtw.groupby('Asset Name')[T].sum().to_dict()
mt['y'] = mt.dt.dt.year; mt['mo'] = mt.dt.dt.month
yoy = mt[mt.mo <= 10].pivot_table(index='Asset Name', columns='y', values=T, aggfunc='sum')

# ---------- miles ----------
mi = pd.read_pickle(S + 'miles_all.pkl')
POOL = {'761', '762', '763', '764', '765', '766', '767', '768'}
mi['key'] = mi.apply(lambda r: r.sfx if r.asset in POOL else r.asset, axis=1)
mi = mi[mi.month.isin(WIN)]
mpv = mi.pivot_table(index='key', columns='month', values='mi', aggfunc='sum')

# ---------- fuel (WEX, 12 months, gallons) ----------
fu = pd.read_pickle(S + 'fuel_all.pkl')
fu['Units'] = pd.to_numeric(fu.Units, errors='coerce'); fu['asset'] = fu['Custom Vehicle/Asset ID'].str.strip()
p = fu['Product Description'].fillna('')
isfuel = p.str.contains('Diesel|Unleaded|Mid/Plus|Premium/Super|E-15|E-85|Biodiesel|Exhaust', case=False)
fu = fu[isfuel & (fu['Unit of Measure'] == 'GA')]
gal = fu.groupby('asset').Units.sum().to_dict()

# ---------- propane ----------
lp = pd.read_excel(A + 'd30b360a-LP_Gallons_by_Location_2025_2026.xlsx', sheet_name='Monthly Detail', header=4, dtype={'Location': str})
lp.columns = [str(c).strip() for c in lp.columns]
lp = lp.set_index('Location')[WIN].sum(axis=1)

# ---------- assemble ----------
rows = []
for _, r in a.iterrows():
    aid = r['Asset Name']; loc = r['Store Number']; c = r.cls
    owned = r['Asset Ownership'] != 'Operating Lease'
    # depreciation months eligible in 2027 (month1 = in-service month)
    elig = []
    for m in range(1, 13):
        k = (2027 - r.isd.year) * 12 + (m - r.isd.month) + 1
        elig.append(1 if (owned and 1 <= k <= r.term) else 0)
    depm = float(dep.get(aid, 0.0)) if owned else 0.0
    flags = []
    if owned and depm == 0 and any(elig): flags.append('Owned, in term, no depreciation amount')
    if not owned and aid in dep: flags.append('Leased; owned wrap depreciation excluded')
    end = r.isd + pd.DateOffset(months=int(r.term))
    rec = dict(id=aid, loc=loc, type=r['Asset Template Name'], cls=c, make=r['Asset Manufacturer Name'],
               own='Owned' if owned else 'Leased', status=r['Asset Status'], isd=r.isd.strftime('%Y-%m-%d'),
               term=int(r.term), depEnd=(end - pd.DateOffset(days=1)).strftime('%Y-%m'),
               dep=round(depm, 2), depElig=elig, depSrc=dep_src.get(aid, '') if owned and depm else '',
               lease=round(float(lease.get(aid, 0) or 0), 2) if not owned else 0.0, leaseNote=lease_note.get(aid, ''),
               flat=FLAT[r['Asset Template Name']], maint=round(float(maint.get(aid, 0.0)), 2),
               maint25=round(float(yoy.loc[aid, 2025]) if aid in yoy.index and not pd.isna(yoy.loc[aid].get(2025)) else 0, 2),
               maint26=round(float(yoy.loc[aid, 2026]) if aid in yoy.index and not pd.isna(yoy.loc[aid].get(2026)) else 0, 2),
               miles=0.0, gal=0.0, lp=0.0, milesNote='', galNote='')
    if r['Asset Status'] == 'Loaner': flags.append('Loaner unit')
    if c == 'Truck':
        src = aid
        if aid == '626003': src = '692009'; rec['milesNote'] = 'Uses predecessor 692009 history'
        if src in mpv.index:
            s = mpv.loc[src].dropna()
            rec['milesMonths'] = int(len(s))
            rec['miles'] = float(s.mean() * 12) if len(s) else 0.0
            if len(s) < 12 and aid not in ('626003',): rec['milesNote'] = f'{len(s)} of 12 months reported; annualized from average'
        g = gal.get(src, 0.0); rec['gal'] = float(g)
        if aid == '758005':
            s = mpv.loc['758005', ['2026-07', '2026-08', '2026-09']]
            mpg = mpv.loc['758005'].sum() / gal['758005']
            rec['miles'] = float(s.mean() * 12); rec['gal'] = rec['miles'] / mpg
            rec['milesNote'] = 'New Apr 2026; Jul–Sep run rate'; rec['galNote'] = 'Gallons from own MPG'
        rows.append(rec); continue
    if c == 'Forklift':
        rec['lp'] = 0  # set below
    rows.append(rec)

df = pd.DataFrame(rows)
# new-truck proxies at 355CD (same-type 355CD average)
def proxy(aid, like):
    src = df[df.id == like].iloc[0]
    df.loc[df.id == aid, ['miles', 'gal']] = [src.miles, src.gal]
    df.loc[df.id == aid, 'milesNote'] = f'New; uses 355CD {src.type} average ({like})'
    df.loc[df.id == aid, 'galNote'] = 'Estimated'
proxy('758011', '758005'); proxy('626005', '697033')
# 626003 gallons from predecessor scaled already via gal(src)
df.loc[df.id == '626003', 'galNote'] = 'Uses predecessor 692009 gallons'

# propane allocation
fk = df.cls == 'Forklift'
pharr = lp['033']; pharr_n = (fk & df['loc'].isin(['033', '355', '355CD'])).sum()
for loc in LOCS:
    m = fk & (df['loc'] == loc)
    n = m.sum()
    if not n: continue
    tot = pharr * n / pharr_n if loc in ('033', '355', '355CD') else lp.get(loc, 0)
    df.loc[m, 'lp'] = tot / n

# gallons per mile (own if plausible, else type median)
tr = df.cls == 'Truck'
df['gpm'] = np.where((df.miles > 0) & (df.gal > 0), df.gal / df.miles.replace(0, np.nan), np.nan)
med = df[tr].groupby('type').gpm.median()
df['mpg'] = 1 / df.gpm
for i, r in df[tr].iterrows():
    tm = med[r.type]
    if pd.isna(r.gpm) or r.gpm < tm * 0.6 or r.gpm > tm * 1.7:
        df.loc[i, 'gpm'] = tm
        df.loc[i, 'galNote'] = (r.galNote + '; ' if r.galNote else '') + f'MPG outside type range; scenario uses {r.type} median'
df['gpm'] = df.gpm.fillna(0)

# registration, taxes, Geotab, Lytx (monthly)
fee = pd.read_excel(A + '3f23cdde-Reg_Tax_Geo_LYTX.xlsx', sheet_name=0, dtype={'Asset Name': str})
fee.columns = [c.strip() for c in fee.columns]
fee = fee.set_index('Asset Name')
for c in ['Registraiton Fee', 'Monthly Taxes', 'Geotab', 'Lytx']: fee[c] = pd.to_numeric(fee[c]).fillna(0)
df['reg'] = df.id.map(lambda i: round(float(fee.loc[i, 'Registraiton Fee']) + float(fee.loc[i, 'Monthly Taxes']), 4))
df['tel'] = df.id.map(lambda i: float(fee.loc[i, 'Geotab']) + float(fee.loc[i, 'Lytx']))
df['feeDetail'] = df.id.map(lambda i: [round(float(fee.loc[i, c]), 2) for c in ['Registraiton Fee', 'Monthly Taxes', 'Geotab', 'Lytx']])
print('fees monthly all', round(df.reg.sum() + df.tel.sum(), 2), 'central', round(df[df['loc'].isin(CENTRAL)][['reg', 'tel']].sum().sum(), 2), 'reg removed from maint', round(sum(reg_removed.get(i, 0) for i in df.id), 2))

# flags
fl = []
for _, r in df.iterrows():
    f = []
    if r.status == 'Loaner': f.append('Loaner unit')
    if r.own == 'Owned' and r.dep == 0 and any(r.depElig): f.append('In term but no depreciation amount')
    if r.cls == 'Truck' and r.maint == 0: f.append('No maintenance history in window')
    if r.milesNote: f.append(r.milesNote)
    if r.galNote: f.append(r.galNote)
    if r.leaseNote: f.append(r.leaseNote)
    if r.id == '747104': f.append('Owned wrap depreciation ($132.37/mo) excluded')
    fl.append(f)
df['flags'] = fl

# ---------- store metrics ----------
sm = pd.read_excel(A + 'b29d844c-Region05_Store_Metrics_YTD_Sep2026.xlsx', sheet_name='Source Data', dtype={'Store #': str}).iloc[:12]
sm2 = pd.read_excel(A + 'b29d844c-Region05_Store_Metrics_YTD_Sep2026.xlsx', sheet_name='Store Metrics', dtype={'Store #': str})
k = 12 / 9
metrics = {}
for _, r in sm.iterrows():
    s2 = sm2[sm2['Store #'] == r['Store #']].iloc[0]
    metrics[r['Store #']] = dict(
        deliveries=r['Total Deliveries'] * k, trips=r['Total Routes (Trips)'] * k, miles=r['Miles YTD'] * k,
        fleetCharge=r['Fleet Charge YTD ($)'] * k, fuel=r['Fuel Cost YTD ($)'] * k,
        timeAway=float(s2['Avg Time Away Utilization']), weight=float(s2['Avg Weight Utilization YTD']),
        daysActive=float(s2['Avg Asset Days Active']), dailyDel=float(s2['Avg Daily Deliveries']),
        delPerTrip=float(s2['Avg Deliveries per Trip']), mpd=float(s2['Avg Miles per Delivery']),
        cpm=float(s2['Avg Cost per Mile YTD']), cpd=float(s2['Avg Cost per Delivery YTD']))
served = {'033': 2882, '037': 621, '093': 509, '015': 487, '089': 377, '100': 267, '103': 167, '108': 25}
served = {k2: v * k for k2, v in served.items()}

FUEL27 = [5.198, 5.016, 4.834, 4.590, 4.455, 4.320, 4.185, 4.095, 4.005, 3.915, 3.825, 3.735]
LP27 = [1.624, 1.637, 1.626, 1.610, 1.604, 1.585, 1.591, 1.578, 1.567, 1.540, 1.524, 1.525]

out = dict(
    generated='2026-10-29',
    locations=[dict(id=l, name=names[l], kind='Central' if l in CENTRAL else 'Store') for l in LOCS],
    assets=json.loads(df.drop(columns=['mpg']).to_json(orient='records')),
    flat=FLAT, fuelRate=FUEL27, lpRate=LP27, mileRate=0.425,
    metrics=metrics, served=served,
    sources=dict(propaneLoc={l: float(lp.get(l, 0)) for l in ['015', '033', '037', '041', '088', '089', '093', '097', '100', '103', '108']}))
json.dump(out, open(S + 'data.json', 'w'))

# ---------- checks ----------
print(len(df), df.groupby('loc').size().to_dict())
print(df.groupby('cls').size().to_dict())
print('dep monthly sum', df.dep.sum().round(2), 'dep 2027', (df.dep * df.depElig.apply(sum)).sum().round(0))
print('lease central', df[df['loc'].isin(CENTRAL)].lease.sum())
print('maint total', df.maint.sum().round(0), df.groupby(df['loc'].isin(CENTRAL)).maint.sum().round(0).to_dict())
print('truck miles', df.miles.sum().round(0), 'gal', df.gal.sum().round(0), 'lp', df.lp.sum().round(0))
print(df[df['flags'].apply(len) > 0][['id', 'loc', 'type', 'flags']].to_string())
print(df[tr][['id', 'loc', 'type', 'miles', 'gal', 'gpm']].round(3).to_string())

# ---------- forklift utilization ----------
yt = pd.read_excel(A + '30e5d5b2-mccoys_selected_locations_yard_tickets_hpd.xlsx', header=6, dtype={'Location #': str})
yt = yt[yt['Location #'].isin(LOCS)]
hdr = pd.read_excel(A + '30e5d5b2-mccoys_selected_locations_yard_tickets_hpd.xlsx', header=None)
fk = {}
for _, r in yt.iterrows():
    fk[r['Location #']] = dict(n=int(r['Forklifts']), hpd=float(r['Avg Operating Hrs / Day (per unit)']),
                               tickets=None if pd.isna(r['Total Yard Tickets (12 mo)']) else float(r['Total Yard Tickets (12 mo)']),
                               tpd=None if pd.isna(r['Avg Yard Tickets / Day']) else float(r['Avg Yard Tickets / Day']))
out['forklift'] = dict(locs=fk, companyHpd=float(hdr.iloc[3, 1]), bizDays=float(hdr.iloc[4, 1]))
json.dump(out, open(S + 'data.json', 'w'))
cnt = df[df.cls == 'Forklift'].groupby('loc').size().to_dict()
print({k: (v['n'], cnt.get(k)) for k, v in fk.items()}, out['forklift']['companyHpd'], out['forklift']['bizDays'])

# ---------- maintenance seasonality (calendar-month index, mean = 1) ----------
ms = mt[(mt.dt >= '2025-01-01') & (mt.dt < '2026-10-01') & ~mt['Work Order Category Full Path'].fillna('').str.contains('Regist', case=False)]
def season(x):
    m = x.groupby([x.dt.dt.year, x.dt.dt.month])[T].sum().unstack(0)
    i = (m / m.mean()).mean(axis=1).reindex(range(1, 13))
    return [float(v) for v in (i / i.mean())]
out['maintSeason'] = dict(region=season(ms[ms['Asset Name'].isin(set(df.id))]), company=season(ms))
json.dump(out, open(S + 'data.json', 'w'))
print('season', out['maintSeason'])
