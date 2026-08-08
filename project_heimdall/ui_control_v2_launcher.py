#!/usr/bin/env python3
from pathlib import Path

p=Path(__file__).resolve().parent/'ui_control_v2.py'
s=p.read_text(encoding='utf-8')

# Compatibility fix for the original v2 parser typo.
s=s.replace(
    "return jsonify([] if d.get('_error') if isinstance(d,dict) else d)",
    "return jsonify([] if isinstance(d,dict) and d.get('_error') else d)",
)

# Doctor and Check for Update are read-only actions. They should never require
# the maintenance password. The UI proxy skips login for those actions.
old_proxy="""    login,code=post('/api/maintenance/login',{'password':password})
    if code!=200:return jsonify(login),code
    payload={'password':password} if action in {'reboot','shutdown'} else {}
    if action in {'reboot','shutdown'}:payload['confirm']=action.upper()
    result,code=post('/api/maintenance/action/'+action,payload)
    return jsonify(result),code
"""
new_proxy="""    if action in {'doctor','check-update'}:
        result,code=post('/api/maintenance/action/'+action,{})
        return jsonify(result),code
    login,code=post('/api/maintenance/login',{'password':password})
    if code!=200:return jsonify(login),code
    payload={'password':password} if action in {'reboot','shutdown'} else {}
    if action in {'reboot','shutdown'}:payload['confirm']=action.upper()
    result,code=post('/api/maintenance/action/'+action,payload)
    return jsonify(result),code
"""
s=s.replace(old_proxy,new_proxy)

# Read-only buttons execute immediately instead of opening the password dialog.
s=s.replace("authAction('doctor','Run Doctor')","directAction('doctor','Run Doctor')")
s=s.replace("authAction('check-update','Check for Update')","directAction('check-update','Check for Update')")
s=s.replace(
    'All changes require the local Heimdall maintenance password. Automatic update creates a backup first and refuses to run if tracked local changes exist.',
    'Doctor and Check for Update are read-only and do not require a password. Actions that change Josh require the local Heimdall maintenance password. Automatic update creates a backup first and refuses to run if tracked local changes exist.',
)

# Add a result-only modal path for read-only diagnostics.
needle="function authAction(action,title){pendingAction=action;pendingTitle=title;modalTitle.textContent=title;modalText.textContent='Enter the Heimdall maintenance password to continue.';confirmWrap.style.display='none';password.value='';modalResult.style.display='none';modal.classList.add('show');password.focus()}"
replacement="""async function directAction(action,title){
  pendingAction=action;pendingTitle=title;modalTitle.textContent=title;
  modalText.textContent='Running read-only diagnostic...';confirmWrap.style.display='none';
  password.style.display='none';confirmBtn.style.display='none';modalResult.style.display='block';
  modalResult.textContent='Working...';modal.classList.add('show');
  try{let r=await fetch('/api/maintenance/run/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});let d=await r.json();modalResult.textContent=d.output||d.error||JSON.stringify(d);updateResult.textContent=modalResult.textContent}
  catch(e){modalResult.textContent='Request failed: '+e}
}
function authAction(action,title){pendingAction=action;pendingTitle=title;modalTitle.textContent=title;modalText.textContent='Enter the Heimdall maintenance password to continue.';confirmWrap.style.display='none';password.style.display='block';confirmBtn.style.display='';password.value='';modalResult.style.display='none';modal.classList.add('show');password.focus()}"""
s=s.replace(needle,replacement)

ns={'__name__':'__main__','__file__':str(p)}
exec(compile(s,str(p),'exec'),ns,ns)
