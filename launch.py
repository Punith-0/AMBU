"""Open the browser only after the local backend is ready."""
import sys,subprocess,time,urllib.request,webbrowser
from pathlib import Path
url='http://127.0.0.1:8877'
def ready():
    try:
        with urllib.request.urlopen(url+'/api/state',timeout=1) as response:return response.status==200
    except Exception:return False
if ready():webbrowser.open(url)
else:
    process=subprocess.Popen([sys.executable,'-X','utf8',str(Path(__file__).with_name('app.py'))],cwd=Path(__file__).parent)
    try:
        for _ in range(60):
            if process.poll() is not None:raise RuntimeError('Server exited. Check the startup error above.')
            if ready():webbrowser.open(url);break
            time.sleep(.5)
        else:print('Server is still loading. Open '+url+' when ready.')
        process.wait()
    except KeyboardInterrupt:process.terminate();process.wait(timeout=10)
