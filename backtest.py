#!/usr/bin/env python3
"""
backtest.py — comprehensive model backtesting.

P1: 8 baselines | P3: 5-bucket | P4: Poisson ML + MaxEP | P6: Draw specialist | P8: LOO CV

Usage:
    python backtest.py
    python backtest.py --no-loo --no-poisson   # fast mode
"""
from __future__ import annotations
import csv, math, sys, argparse
from pathlib import Path

try:
    from scipy.optimize import minimize as _sp_min
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ── data ─────────────────────────────────────────────────────────

def _norm(h, d, a):
    rh, rd, ra = 1/h, 1/d, 1/a
    s = rh+rd+ra
    return rh/s, rd/s, ra/s

def load(path: str) -> list[dict]:
    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ph, pd, pa = _norm(float(row['B365H']), float(row['B365D']), float(row['B365A']))
            hg, ag = int(row['FTHG']), int(row['FTAG'])
            rows.append(dict(
                home=row['HomeTeam'], away=row['AwayTeam'],
                ph=ph, pd=pd, pa=pa,
                p_fav=max(ph, pa), fav_home=(ph >= pa),
                hg=hg, ag=ag,
            ))
    return rows

# ── scoring ───────────────────────────────────────────────────────

def _out(h, a): return 'H' if h > a else ('A' if h < a else 'D')

def pts(ph, pa, ah, aa):
    if ph == ah and pa == aa: return 3
    return 1 if _out(ph, pa) == _out(ah, aa) else 0

def orient(fg, ug, fav_home):
    return (fg, ug) if fav_home else (ug, fg)

def score_list(matches, preds):
    tot = ex = ok = 0
    for m, (h, a) in zip(matches, preds):
        p = pts(h, a, m['hg'], m['ag'])
        tot += p; ex += (p == 3); ok += (p == 1)
    mi = len(matches) - ex - ok
    return dict(total=tot, exact=ex, outcome=ok, miss=mi,
                avg=round(tot/len(matches), 3) if matches else 0.0, n=len(matches))

def run(matches, fn):
    return score_list(matches, [fn(m) for m in matches])

# ── P1: baselines ─────────────────────────────────────────────────

def _fav(fg, ug):    return lambda m: orient(fg, ug, m['fav_home'])
def _market(m):
    if m['ph'] > m['pd'] and m['ph'] > m['pa']: return (2, 1)
    if m['pa'] > m['pd'] and m['pa'] > m['ph']: return (1, 2)
    return (1, 1)

BASELINES = {
    'always_1-0': _fav(1,0), 'always_2-0': _fav(2,0), 'always_2-1': _fav(2,1),
    'always_3-0': _fav(3,0), 'always_3-1': _fav(3,1),
    'always_1-1': lambda m: (1,1), 'always_0-0': lambda m: (0,0),
    'market_2-1': _market,
}

# ── P3: 5-bucket grid search ──────────────────────────────────────

_CANDS = {
    'balanced': [(0,0),(1,1),(1,0),(2,1)],
    'weak':     [(1,0),(2,1),(1,1)],
    'medium':   [(2,0),(2,1),(3,1),(1,0)],
    'strong':   [(2,0),(3,0),(3,1),(2,1)],
    'huge':     [(3,0),(4,0),(4,1),(3,1)],
}

def _cls5(pf, bw, bm, bs, bh):
    if pf < bw: return 'balanced'
    if pf < bm: return 'weak'
    if pf < bs: return 'medium'
    if pf < bh: return 'strong'
    return 'huge'

def _opt5(matches, bw, bm, bs, bh):
    bkts = {b: [] for b in _CANDS}
    for m in matches:
        bkts[_cls5(m['p_fav'], bw, bm, bs, bh)].append(m)
    sc, tot = {}, 0
    for b, ms in bkts.items():
        best_s, best_p = _CANDS[b][0], -1
        for s in _CANDS[b]:
            p = sum(pts(*orient(s[0],s[1],m['fav_home']),m['hg'],m['ag']) for m in ms)
            if p > best_p: best_p, best_s = p, s
        sc[b] = best_s
        tot += best_p if ms else 0
    return sc, tot

def best5(matches):
    best_t, best_cfg = -1, None
    WB = [round(.52+i*.02,2) for i in range(6)]
    MB = [round(.62+i*.02,2) for i in range(7)]
    SB = [round(.75+i*.02,2) for i in range(6)]
    HB = [.85, .88, .92]
    for bw in WB:
        for bm in MB:
            if bm <= bw: continue
            for bs in SB:
                if bs <= bm: continue
                for bh in HB:
                    if bh <= bs: continue
                    sc, t = _opt5(matches, bw, bm, bs, bh)
                    if t > best_t: best_t, best_cfg = t, (bw, bm, bs, bh, sc, t)
    return best_cfg  # (bw, bm, bs, bh, sc, train_pts)

def make_fn5(bw, bm, bs, bh, sc):
    return lambda m: orient(sc[_cls5(m['p_fav'],bw,bm,bs,bh)][0],
                            sc[_cls5(m['p_fav'],bw,bm,bs,bh)][1],
                            m['fav_home'])

# ── P6: draw specialist ───────────────────────────────────────────

def _draw_pred(m, dt, gt, fs):
    if m['pd'] >= dt and abs(m['ph'] - m['pa']) <= gt:
        return (1, 1)
    return orient(fs[0], fs[1], m['fav_home'])

def best_draw(matches):
    best_t, best_cfg = -1, None
    for dt in [round(.22+i*.01,2) for i in range(14)]:
        for gt in [round(.05+i*.05,2) for i in range(8)]:
            for fs in [(1,0),(2,0),(2,1),(3,1)]:
                t = sum(pts(*_draw_pred(m,dt,gt,fs), m['hg'], m['ag']) for m in matches)
                if t > best_t: best_t, best_cfg = t, dict(dt=dt, gt=gt, fs=fs)
    return best_cfg

def make_draw_fn(cfg):
    return lambda m: _draw_pred(m, cfg['dt'], cfg['gt'], cfg['fs'])

# ── P4: Poisson max-expected-points ──────────────────────────────

def _pois(lam, k): return math.exp(-lam) * lam**k / math.factorial(k)

def _fit_lam(ph, pd, pa):
    if not HAS_SCIPY:
        total = max(1.5, -math.log(max(pd, 0.01)) * 1.8)
        lh = total * ph / (ph+pa+1e-9) * 1.05
        la = total * pa / (ph+pa+1e-9) * 1.05
        return max(.1, lh), max(.1, la)
    def err(x):
        lh, la = max(.05, x[0]), max(.05, x[1])
        N = 9
        mat = [[_pois(lh,i)*_pois(la,j) for j in range(N)] for i in range(N)]
        pw  = sum(mat[i][j] for i in range(N) for j in range(N) if i > j)
        pd_ = sum(mat[i][i] for i in range(N))
        pa_ = 1 - pw - pd_
        return (pw-ph)**2 + (pd_-pd)**2 + (pa_-pa)**2
    r = _sp_min(err, [max(.1,ph*2.2), max(.1,pa*2.2)], method='Nelder-Mead',
                options={'xatol':1e-5,'fatol':1e-5,'maxiter':500,'disp':False})
    return max(.05, r.x[0]), max(.05, r.x[1])

def poisson_both(m):
    """Return (most_likely_score, max_ep_score)."""
    lh, la = _fit_lam(m['ph'], m['pd'], m['pa'])
    N = 9
    mat = [[_pois(lh,i)*_pois(la,j) for j in range(N)] for i in range(N)]
    pw  = sum(mat[i][j] for i in range(N) for j in range(N) if i > j)
    pd_ = sum(mat[i][i] for i in range(N))
    pa_ = 1 - pw - pd_
    bml = bep = (0,0); bpml = bpep = -1
    for i in range(N):
        for j in range(N):
            px = mat[i][j]
            po = pw if i > j else (pa_ if j > i else pd_)
            ep = po + 2*px   # E[pts] = P(outcome) + 2*P(exact)
            if px > bpml: bpml, bml = px, (i,j)
            if ep > bpep: bpep, bep = ep, (i,j)
    return bml, bep

def compute_poisson(matches, label=""):
    ml_preds, ep_preds = [], []
    for i, m in enumerate(matches):
        sys.stdout.write(f"\r  Poisson [{label}]: {i+1}/{len(matches)}  "); sys.stdout.flush()
        ml, ep = poisson_both(m)
        ml_preds.append(ml); ep_preds.append(ep)
    print()
    return ml_preds, ep_preds

# ── P8: LOO cross-validation ──────────────────────────────────────

def loo_3bucket(matches):
    TV = [round(.45+i*.025,3) for i in range(15)]
    C3 = [(1,0),(2,0),(2,1),(3,0),(3,1),(1,1),(0,0),(2,2)]
    CO = C3 + [(0,1),(0,2),(1,2)]
    total = 0
    for hi in range(len(matches)):
        tr = [m for i,m in enumerate(matches) if i != hi]
        best_t, best_cfg = -1, None
        for tl in TV:
            for tu in TV:
                if tu <= tl: continue
                dom = [m for m in tr if m['p_fav'] >= tu]
                con = [m for m in tr if tl <= m['p_fav'] < tu]
                opn = [m for m in tr if m['p_fav'] < tl]
                def bs(ms, cands):
                    bst, bp = cands[0], -1
                    for s in cands:
                        p = sum(pts(*orient(s[0],s[1],m['fav_home']),m['hg'],m['ag']) for m in ms)
                        if p > bp: bp, bst = p, s
                    return bst
                ds = bs(dom,C3); cs = bs(con,C3); os = bs(opn,CO)
                t = (sum(pts(*orient(ds[0],ds[1],m['fav_home']),m['hg'],m['ag']) for m in dom) +
                     sum(pts(*orient(cs[0],cs[1],m['fav_home']),m['hg'],m['ag']) for m in con) +
                     sum(pts(*orient(os[0],os[1],m['fav_home']),m['hg'],m['ag']) for m in opn))
                if t > best_t: best_t, best_cfg = t, (tl,tu,ds,cs,os)
        tl,tu,ds,cs,os = best_cfg
        m = matches[hi]
        s = ds if m['p_fav'] >= tu else (cs if m['p_fav'] >= tl else os)
        total += pts(*orient(s[0],s[1],m['fav_home']), m['hg'], m['ag'])
        sys.stdout.write(f"\r  LOO 3-bucket: {hi+1}/{len(matches)}  "); sys.stdout.flush()
    print()
    return total

def loo_draw(matches):
    total = 0
    for hi in range(len(matches)):
        tr = [m for i,m in enumerate(matches) if i != hi]
        cfg = best_draw(tr)
        fn  = make_draw_fn(cfg)
        total += pts(*fn(matches[hi]), matches[hi]['hg'], matches[hi]['ag'])
        sys.stdout.write(f"\r  LOO draw-spec: {hi+1}/{len(matches)}  "); sys.stdout.flush()
    print()
    return total

# ── main ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train',      default='data/wc2018.csv')
    ap.add_argument('--test',       default='data/wc2022.csv')
    ap.add_argument('--eval',       default='data/wc2026.csv')
    ap.add_argument('--no-loo',     action='store_true')
    ap.add_argument('--no-poisson', action='store_true')
    args = ap.parse_args()

    train = load(args.train)
    test  = load(args.test)
    eval_ = load(args.eval) if Path(args.eval).exists() else []

    print(f"Train: {len(train)} ({args.train})")
    print(f"Test:  {len(test)} ({args.test})")
    if eval_: print(f"Eval:  {len(eval_)} ({args.eval})")

    summary_rows = []   # [model, family, params, tr, te, ex, ok, mi, ev, loo]

    # ── P1 baselines ──────────────────────────────────────────────
    print("\n── P1: Baselines ──────────────────────────────────────────────")
    for name, fn in BASELINES.items():
        tr = run(train, fn); te = run(test, fn); ev = run(eval_, fn)
        ev_s = f"  eval={ev['total']}" if eval_ else ""
        print(f"  {name:<20} train={tr['total']:3d}  test={te['total']:3d}{ev_s}")
        summary_rows.append([name,'P1','-',tr['total'],te['total'],
                              te['exact'],te['outcome'],te['miss'],
                              ev['total'] if eval_ else '','-'])

    # ── P3: 5-bucket ──────────────────────────────────────────────
    print("\n── P3: 5-bucket grid search ──────────────────────────────────")
    bw,bm,bs,bh,sc5,_ = best5(train)
    fn5 = make_fn5(bw,bm,bs,bh,sc5)
    tr5 = run(train,fn5); te5 = run(test,fn5); ev5 = run(eval_,fn5)
    print(f"  Bounds: balanced<{bw}  weak<{bm}  medium<{bs}  strong<{bh}")
    print(f"  Scores: {sc5}")
    ev5_s = f"  eval={ev5['total']}" if eval_ else ""
    print(f"  Train: {tr5['total']}  Test: {te5['total']}{ev5_s}")
    summary_rows.append(['5-bucket','P3',f"<{bw}<{bm}<{bs}<{bh}",
                         tr5['total'],te5['total'],te5['exact'],te5['outcome'],te5['miss'],
                         ev5['total'] if eval_ else '','-'])

    # ── P6: draw specialist ───────────────────────────────────────
    print("\n── P6: Draw specialist ───────────────────────────────────────")
    dcfg = best_draw(train)
    dfn  = make_draw_fn(dcfg)
    trd = run(train,dfn); ted = run(test,dfn); evd = run(eval_,dfn)
    evd_s = f"  eval={evd['total']}" if eval_ else ""
    print(f"  draw_t={dcfg['dt']}  gap_t={dcfg['gt']}  fav_score={dcfg['fs']}")
    print(f"  Train: {trd['total']}  Test: {ted['total']}{evd_s}")
    summary_rows.append(['draw-specialist','P6',
                         f"dt={dcfg['dt']},gt={dcfg['gt']},fs={dcfg['fs']}",
                         trd['total'],ted['total'],ted['exact'],ted['outcome'],ted['miss'],
                         evd['total'] if eval_ else '','-'])

    # ── P4: Poisson ───────────────────────────────────────────────
    if not args.no_poisson:
        print("\n── P4: Poisson models ────────────────────────────────────────")
        if not HAS_SCIPY:
            print("  [scipy not found — using approximate lambda estimation]")
        sets = [('train',train),('test',test)]
        if eval_: sets.append(('eval',eval_))
        pois = {}
        for label, ms in sets:
            ml, ep = compute_poisson(ms, label)
            pois[label] = dict(ml=score_list(ms,ml), ep=score_list(ms,ep))
        tr_ml=pois['train']['ml']; tr_ep=pois['train']['ep']
        te_ml=pois['test']['ml'];  te_ep=pois['test']['ep']
        ev_ml=pois.get('eval',{}).get('ml',{}); ev_ep=pois.get('eval',{}).get('ep',{})
        ev_ml_t = ev_ml.get('total','') if eval_ else ''
        ev_ep_t = ev_ep.get('total','') if eval_ else ''
        print(f"  most-likely:  train={tr_ml['total']}  test={te_ml['total']}  exact={te_ml['exact']}", end="")
        if eval_: print(f"  eval={ev_ml_t}", end="")
        print()
        print(f"  max-exp-pts:  train={tr_ep['total']}  test={te_ep['total']}  exact={te_ep['exact']}", end="")
        if eval_: print(f"  eval={ev_ep_t}", end="")
        print()
        summary_rows.append(['poisson-ml','P4','most-likely',tr_ml['total'],te_ml['total'],
                             te_ml['exact'],te_ml['outcome'],te_ml['miss'],ev_ml_t,'-'])
        summary_rows.append(['poisson-ep','P4','max-exp-pts',tr_ep['total'],te_ep['total'],
                             te_ep['exact'],te_ep['outcome'],te_ep['miss'],ev_ep_t,'-'])

    # ── P8: LOO ───────────────────────────────────────────────────
    if not args.no_loo:
        print("\n── P8: LOO cross-validation (training set) ──────────────────")
        l3  = loo_3bucket(train)
        lds = loo_draw(train)
        print(f"  3-bucket:       {l3}/{len(train)} = {l3/len(train):.3f}/match")
        print(f"  draw-specialist:{lds}/{len(train)} = {lds/len(train):.3f}/match")
        if not args.no_poisson:
            lep = tr_ep['total']
            print(f"  poisson-ep:     {lep}/{len(train)} = {lep/len(train):.3f}/match  [no training → LOO = train]")
        # patch LOO into rows
        for row in summary_rows:
            if row[0] == '3-bucket (LOO)' : row[9] = l3
        # add LOO rows
        summary_rows.append(['3-bucket-LOO','P8','LOO','-','-','-','-','-','-',l3])
        summary_rows.append(['draw-spec-LOO','P8','LOO','-','-','-','-','-','-',lds])

    # ── summary ───────────────────────────────────────────────────
    print("\n══ Summary ═══════════════════════════════════════════════════")
    print(f"{'Model':<22} {'Train':>5} {'Test':>5} {'Ex':>3} {'Ok':>3} {'Miss':>4} {'WC2026':>7} {'LOO':>5}")
    print("─" * 60)
    for r in summary_rows:
        tr=str(r[3]); te=str(r[4]); ex=str(r[5]); ok=str(r[6]); mi=str(r[7])
        ev=str(r[8]); lo=str(r[9])
        print(f"{r[0]:<22} {tr:>5} {te:>5} {ex:>3} {ok:>3} {mi:>4} {ev:>7} {lo:>5}")

    # ── save ──────────────────────────────────────────────────────
    out = Path('docs/backtest_summary.csv')
    out.parent.mkdir(exist_ok=True)
    with open(out,'w',newline='',encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['model','family','params','train_pts','test_pts',
                    'test_exact','test_outcome','test_miss','wc2026_pts','loo_train'])
        w.writerows(summary_rows)
    print(f"\nSaved {out}")

if __name__ == '__main__':
    main()
