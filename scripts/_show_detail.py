import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print("KEYS:", list(d.keys()))
# Try to extract relevant sections
for k in ['match','detail','events','statistics','odds','status','minute','score','home','away','league']:
    if k in d:
        v = d[k]
        if isinstance(v,(dict,list)):
            print(f"\n--- {k} ---")
            print(json.dumps(v, ensure_ascii=False, indent=2)[:3000])
        else:
            print(f"{k}: {v}")
