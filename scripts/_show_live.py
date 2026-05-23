import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
print(f"source={d.get('source')} fetched={d.get('fetched_at')} stale={d.get('stale')} total={len(d.get('items',[]))}")
print('-'*100)
by_league = {}
for i in d.get('items', []):
    by_league.setdefault(i.get('league','?'), []).append(i)
for lg, items in by_league.items():
    print(f"\n=== {lg} ({len(items)}) ===")
    for i in items:
        sc = i.get('score', {})
        h = sc.get('home'); a = sc.get('away')
        mn = i.get('minute') or i.get('status') or ''
        print(f"  [{mn:>8}] {i.get('home')} {h}-{a} {i.get('away')}")
