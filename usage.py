"""Best-effort, bounded, asynchronous usage logging; never required for serving requests."""
import json
import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LOG_DIR=ROOT/'logs'
QUEUE=queue.Queue(maxsize=8192)
_worker=None
_stopping=threading.Event()
_dropped=0

def _warn(message):
    # Only the writer thread emits warnings, never the request thread.
    try:
        import sys
        print('nexGJB usage: '+message,file=sys.stderr,flush=True)
    except Exception:
        pass

def _submit(kind,event):
    global _dropped
    try:
        if _stopping.is_set() or _worker is None or not _worker.is_alive():
            return
        now=datetime.now().astimezone()
        QUEUE.put_nowait((kind,now.strftime('%Y-%m'),dict(event,time=now.isoformat(timespec='milliseconds'))))
    except queue.Full:
        _dropped+=1
    except Exception:
        pass

def _client(request):
    # Use ASGI's client address; do not parse arbitrary forwarded headers.
    return request.client.host if request.client else None

def visit(request):
    try:
        _submit('visits',{'ip':_client(request),'user_agent':request.headers.get('user-agent','')[:512],'path':'/'})
    except Exception:
        pass

def download(request,r,features,count,size,status,http_status):
    try:
        selected=[]
        for key in dict.fromkeys(r.ids):
            feature=features.get((r.level,key))
            if feature:
                p=feature['properties']
                selected.append({'id':key,'province':p.get('province'),'city':p.get('city'),'county':p.get('county'),'name':p.get(r.level)})
        _submit('downloads',{'ip':_client(request),'mode':r.mode,'level':r.level,'target':r.target,
            'selected':selected,'count':count,'format':r.format,'crs':r.crs,'bytes':size,
            'status':status,'http_status':http_status})
    except Exception:
        pass

def _append(kind,month,event):
    directory=LOG_DIR/kind
    LOG_DIR.mkdir(mode=0o700,exist_ok=True)
    directory.mkdir(mode=0o700,exist_ok=True)
    path=directory/(month+'.jsonl')
    line=(json.dumps(event,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')
    # Single writer in the default one-worker deployment. Append mode avoids truncation.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    try:
        view=memoryview(line)
        while view:
            n=os.write(fd,view)
            if n<=0: raise OSError('short log write')
            view=view[n:]
    finally:
        os.close(fd)

def _run():
    last_warning=0.0
    last_dropped=0
    while not _stopping.is_set() or not QUEUE.empty():
        try:
            kind,month,event=QUEUE.get(timeout=0.25)
        except queue.Empty:
            continue
        try:
            _append(kind,month,event)
        except Exception as exc:
            if time.monotonic()-last_warning>=30:
                _warn('write failed: '+str(exc))
                last_warning=time.monotonic()
        finally:
            QUEUE.task_done()
        if _dropped!=last_dropped and time.monotonic()-last_warning>=30:
            _warn(f'queue overflow; dropped approximately {_dropped} events')
            last_dropped=_dropped
            last_warning=time.monotonic()

def start():
    global _worker
    try:
        if _worker is not None and _worker.is_alive(): return
        _stopping.clear()
        _worker=threading.Thread(target=_run,name='nexgjb-usage',daemon=True)
        _worker.start()
    except Exception:
        pass

def stop():
    # Bounded shutdown drain. No request waits for disk I/O.
    try:
        _stopping.set()
        if _worker is not None: _worker.join(timeout=3)
    except Exception:
        pass
