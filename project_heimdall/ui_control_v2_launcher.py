#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parent/'ui_control_v2.py'
s=p.read_text(encoding='utf-8')
s=s.replace("return jsonify([] if d.get('_error') if isinstance(d,dict) else d)","return jsonify([] if isinstance(d,dict) and d.get('_error') else d)")
ns={'__name__':'__main__','__file__':str(p)}
exec(compile(s,str(p),'exec'),ns,ns)
