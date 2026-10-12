"""Acquire exact pinned original social classifiers, without inference or labels."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODELS = (
    ('cryptobert','ElKulako/cryptobert','9e37c910fe87727cb842a9ac55c6388256fe0f15',
     'model.safetensors','fe34ba09b3d701ff2b4ee69205e42c8143fcee1f89fe3a0cf10444988634a3c9',
     ('config.json','merges.txt','special_tokens_map.json','tokenizer.json','tokenizer_config.json','vocab.json')),
    ('cardiff','cardiffnlp/twitter-roberta-base-sentiment-latest','3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7',
     'pytorch_model.bin','4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae',
     ('config.json','merges.txt','special_tokens_map.json','vocab.json')),
)


def now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_hash(payload):
    return hashlib.sha1(b'blob '+str(len(payload)).encode('ascii')+b'\0'+payload).hexdigest()


def bounded_get(url, limit):
    with urllib.request.urlopen(url,timeout=30) as response:
        payload = response.read(limit+1)
        if response.status != 200 or len(payload)>limit:
            raise ValueError('Publisher response fails status/size bounds')
    return payload


def inspect_model(spec):
    key,model,revision,weight,weight_hash,small = spec
    base = f'https://huggingface.co/{model}'
    metadata_url = f'https://huggingface.co/api/models/{model}/revision/{revision}?blobs=true'
    raw = bounded_get(metadata_url,2*1024*1024)
    metadata = json.loads(raw)
    if metadata.get('sha') != revision or metadata.get('id') != model:
        raise ValueError('Pinned publisher identity/revision mismatch')
    siblings = {row['rfilename']:row for row in metadata['siblings']}
    files, content = [], {}
    for name in (*small,weight):
        if name not in siblings:
            raise ValueError('Required original publisher file missing: '+name)
        entry = siblings[name]
        if type(entry.get('size')) is not int or entry['size'] <= 0:
            raise ValueError('Exact publisher file size is required')
        source_url = f'{base}/blob/{revision}/{name}'
        if name == weight:
            lfs = entry.get('lfs',{})
            if lfs.get('sha256') != weight_hash or lfs.get('size') != entry['size']:
                raise ValueError('Original publisher weight pointer changed')
            pointer = bounded_get(f'{base}/raw/{revision}/{name}',2048)
            match = re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?',pointer)
            if (match is None or match.group(1).decode()!=weight_hash or int(match.group(2))!=entry['size']
                    or git_blob_hash(pointer)!=entry['blobId']):
                raise ValueError('Primary LFS pointer, API metadata and pinned identity differ')
            sha = weight_hash
        else:
            if entry['size'] > 4*1024*1024 or entry.get('lfs'):
                raise ValueError('Original tokenizer/config metadata exceeds declared small-file policy')
            payload = bounded_get(f'{base}/raw/{revision}/{name}',4*1024*1024)
            if len(payload)!=entry['size'] or git_blob_hash(payload)!=entry['blobId']:
                raise ValueError('Original Git blob bytes differ from pinned metadata: '+name)
            sha = hashlib.sha256(payload).hexdigest()
            content[name] = payload
        files.append({'filename':name,'sha256':sha,'expected_bytes':entry['size'],
                      'source_url':source_url,'publisher_git_blob_sha1':entry['blobId']})
    return {'key':key,'model_id':model,'revision':revision,'weight_filename':weight,
            'files':files,'metadata_url':metadata_url,'metadata_sha256':hashlib.sha256(raw).hexdigest(),
            'primary_metadata':metadata,'status':'pinned_metadata_verified'},content


def save(receipt, report, *, exclusive=False):
    with receipt.open('x' if exclusive else 'w',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
        stream.write('\n')


def download_model(record, content, directory):
    if directory.exists():
        raise ValueError('Original snapshot directory already exists; preserve it and use a new cache root')
    directory.mkdir(parents=True)
    for entry in record['files']:
        name = entry['filename']
        target = directory/name
        if name in content:
            with target.open('xb') as stream:
                stream.write(content[name])
        else:
            partial = directory/(name+'.partial')
            url = f"https://huggingface.co/{record['model_id']}/resolve/{record['revision']}/{name}"
            sha, size = hashlib.sha256(),0
            next_progress = 64*1024*1024
            with urllib.request.urlopen(url,timeout=60) as response,partial.open('xb') as stream:
                if response.status!=200:
                    raise ValueError('Unexpected publisher weight response')
                while True:
                    chunk = response.read(8*1024*1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size>entry['expected_bytes']:
                        raise ValueError('Weight transfer exceeds pinned publisher size')
                    sha.update(chunk)
                    stream.write(chunk)
                    if size>=next_progress:
                        print(f"{record['key']}: {size}/{entry['expected_bytes']} weight bytes",flush=True)
                        next_progress += 64*1024*1024
            if size!=entry['expected_bytes'] or sha.hexdigest()!=entry['sha256']:
                raise ValueError('Downloaded weight bytes differ from original publisher pointer; partial retained')
            partial.rename(target)
        if target.stat().st_size!=entry['expected_bytes'] or file_hash(target)!=entry['sha256']:
            raise ValueError('Actual snapshot file fails final identity check')
    record.update(status='downloaded_original_bytes_verified',snapshot_directory=str(directory))
    print(f"Verified complete original snapshot: {record['model_id']}",flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--download',action='store_true')
    args = parser.parse_args()
    cache,receipt = args.cache_root.resolve(),args.receipt.resolve()
    if not cache.is_relative_to(Path('E:/AI-Tools/Cache').resolve()):
        raise ValueError('Publisher caches belong under E:/AI-Tools/Cache')
    if not receipt.is_relative_to(ROOT/'evidence') or receipt.exists():
        raise ValueError('Use a new project evidence receipt')
    if args.download and cache.exists():
        raise ValueError('Preserve previous caches; choose a new root')
    report = {'schema':'investify-original-social-acquisition-v1','started_utc':now(),
              'status':'started','download_requested':args.download,'models':[],
              'model_inference_calls':0,'labels_modified':False,'fnspid_requests':0,
              'routing_settings_changed':False,'script_sha256':file_hash(Path(__file__))}
    save(receipt,report,exclusive=True)
    try:
        inspected = []
        for spec in MODELS:
            record,content = inspect_model(spec)
            report['models'].append(record)
            inspected.append((record,content))
            save(receipt,report)
        report['status']='all_pinned_metadata_verified'
        save(receipt,report)
        if args.download:
            for record,content in inspected:
                download_model(record,content,cache/record['key']/record['revision'])
                save(receipt,report)
            report['status']='both_original_snapshots_verified'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        report['completed_utc']=now()
        save(receipt,report)
    print(report['status'],flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
