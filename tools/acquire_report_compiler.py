"""Fetch the official pinned portable Tectonic Windows release onto E:."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('E:/AI-Tools/Cache/tectonic-0.17.0')
RECEIPT=ROOT/'evidence/report_compiler_acquisition_20261013.json'
NAME='tectonic-0.17.0-x86_64-pc-windows-msvc.zip'
SHA='f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f'
SIZE=21060223

def main():
    if CACHE.exists() or RECEIPT.exists():
        raise ValueError('Preserve earlier compiler acquisition; choose a new versioned identity')
    url='https://api.github.com/repos/tectonic-typesetting/tectonic/releases/tags/tectonic%400.17.0'
    request=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'Investify-mid-eval-build'})
    with urllib.request.urlopen(request,timeout=30) as response:
        metadata=json.loads(response.read(2*1024*1024))
    matches=[item for item in metadata['assets'] if item['name']==NAME]
    if metadata['tag_name']!='tectonic@0.17.0' or len(matches)!=1:
        raise ValueError('Require the exact official release asset')
    asset=matches[0]
    if asset['size']!=SIZE or asset.get('digest')!='sha256:'+SHA:
        raise ValueError('Official release size/digest differ from reviewed metadata')
    CACHE.mkdir(parents=True)
    archive=CACHE/NAME
    with urllib.request.urlopen(asset['browser_download_url'],timeout=60) as response:
        payload=response.read(SIZE+1)
    if len(payload)!=SIZE or hashlib.sha256(payload).hexdigest()!=SHA:
        raise ValueError('Compiler archive fails official byte identity')
    with archive.open('xb') as stream:
        stream.write(payload)
    files={}
    with zipfile.ZipFile(archive) as bundle:
        if sum(info.file_size for info in bundle.infolist())>120*1024*1024:
            raise ValueError('Compiler archive exceeds extraction bound')
        for info in bundle.infolist():
            target=(CACHE/info.filename).resolve()
            if not target.is_relative_to(CACHE.resolve()):
                raise ValueError('Compiler archive path escapes E: cache')
            if info.is_dir():
                target.mkdir(parents=True,exist_ok=True)
                continue
            target.parent.mkdir(parents=True,exist_ok=True)
            data=bundle.read(info)
            with target.open('xb') as stream:
                stream.write(data)
            files[info.filename]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    executables=list(CACHE.rglob('tectonic.exe'))
    if len(executables)!=1:
        raise ValueError('Require one extracted compiler executable')
    env=dict(os.environ,TEMP='E:/AI-Tools/Temp',TMP='E:/AI-Tools/Temp',
             TECTONIC_CACHE_DIR='E:/AI-Tools/Cache/tectonic-data',
             XDG_CACHE_HOME='E:/AI-Tools/Cache',XDG_CONFIG_HOME='E:/AI-Tools/Work/tectonic-config')
    result=subprocess.run([str(executables[0]),'--version'],capture_output=True,text=True,env=env,timeout=30)
    if result.returncode:
        raise RuntimeError('Verified compiler failed version check: '+result.stderr)
    report={'schema':'investify-official-report-compiler-v1','checked_utc':datetime.now(timezone.utc).isoformat(),
            'status':'downloaded_verified_version_checked','release_url':metadata['html_url'],
            'archive_sha256':SHA,'archive_bytes':SIZE,'extracted_files':files,
            'executable':str(executables[0]),'version_output':result.stdout.strip(),
            'cache_directory':env['TECTONIC_CACHE_DIR'],'system_installation':False,'report_compiled':False,
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with RECEIPT.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2)
        stream.write('\n')
    print(result.stdout.strip())
    print('Portable compiler verified:',executables[0])

if __name__=='__main__':
    main()
