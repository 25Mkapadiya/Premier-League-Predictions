#!/usr/bin/env python3
"""Run the no-key refresh and always write a machine-readable diagnostic."""
from __future__ import annotations
import contextlib,io,json,traceback
from datetime import datetime,timezone
from prediction_core import ROOT
import refresh_snapshot
STATUS=ROOT/'data'/'refresh_status.json'

def main():
    buf=io.StringIO();success=True;error=None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code=refresh_snapshot.main()
        success=(code==0)
        if not success:error=f'refresh_snapshot returned {code}'
    except Exception as exc:
        success=False;error=f'{type(exc).__name__}: {exc}';buf.write('\n'+traceback.format_exc())
    payload={'updated':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'success':success,'error':error,'logTail':buf.getvalue()[-6000:]}
    STATUS.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(payload['logTail'])
    print('Refresh success:',success,'error:',error)
    return 0
if __name__=='__main__':raise SystemExit(main())
