"""Prepare a new complete V4 catalog/plan from verified original snapshots."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code/src'))


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition',type=Path,required=True)
    parser.add_argument('--converted-directory',type=Path,required=True)
    parser.add_argument('--output-directory',type=Path,required=True)
    args=parser.parse_args()
    output=args.output_directory.resolve()
    converted=args.converted_directory.resolve()
    if not output.is_relative_to(ROOT/'code/artifacts/mid_eval') or output.exists():
        raise ValueError('Preserve study outputs; use a new project study directory')
    if not converted.is_relative_to(Path('E:/AI-Tools/Cache').resolve()) or converted.exists():
        raise ValueError('Use a new conversion cache under E:/AI-Tools/Cache')
    os.environ.update(TEMP='E:/AI-Tools/Temp',TMP='E:/AI-Tools/Temp',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                      HF_HOME='E:/AI-Tools/Cache/huggingface',PYTHONDONTWRITEBYTECODE='1')
    from investify.sentiment_receipts import model_manifest,verify_local_files,freeze_receipt_plan
    from investify.sentiment_selection import digest
    from investify.model_conversion import convert_original
    acquisition=json.loads(args.acquisition.read_text(encoding='utf-8'))
    if acquisition['status']!='both_original_snapshots_verified' or acquisition['model_inference_calls']!=0:
        raise ValueError('Require both complete original acquisition receipts before this preparation')
    parent=json.loads((ROOT/'code/artifacts/mid_eval/social_selection_plan.json').read_text(encoding='utf-8'))
    benchmark=json.loads((ROOT/'code/artifacts/mid_eval/social_benchmark.json').read_text(encoding='utf-8'))
    catalog={'schema':'investify-classifier-publisher-catalog-v1','status':'complete_original_file_metadata',
             'acquisition_receipt_sha256':digest_file(args.acquisition),'models':[],
             'scope':'New complete pinned publisher-byte catalog; original V3 candidates, reference labels and chronology unchanged. Cardiff has disclosed lossless serialization only.'}
    for checkpoint in parent['candidate_checkpoints']:
        records=[row for row in acquisition['models'] if row['model_id']==checkpoint['model_id'] and row['revision']==checkpoint['revision']]
        if len(records)!=1:
            raise ValueError('Acquisition identities differ from original candidate declarations')
        record=records[0]
        original=Path(record['snapshot_directory'])
        for entry in record['files']:
            path=original/entry['filename']
            if path.stat().st_size!=entry['expected_bytes'] or digest_file(path)!=entry['sha256']:
                raise ValueError('Original snapshot changed after acquisition')
        files=[dict(entry) for entry in record['files']]
        manifest={'model_id':checkpoint['model_id'],'revision':checkpoint['revision'],
                  'status':'complete_original_file_metadata','files':files,
                  'publisher_metadata_url':record['metadata_url'],'publisher_metadata_sha256':record['metadata_sha256'],
                  'serialization':'original_publisher_safetensors','snapshot_directory':str(original)}
        if record['key']=='cardiff':
            import torch
            torch.set_num_threads(4)
            conversion=convert_original(original/'pytorch_model.bin',converted)
            for entry in record['files']:
                if entry['filename']!='pytorch_model.bin':
                    shutil.copyfile(original/entry['filename'],converted/entry['filename'])
            files=[entry for entry in files if entry['filename']!='pytorch_model.bin']
            files.append({'filename':'model.safetensors','sha256':conversion['converted_sha256'],
                          'expected_bytes':conversion['converted_bytes'],
                          'source_url':f"https://huggingface.co/{checkpoint['model_id']}/blob/{checkpoint['revision']}/pytorch_model.bin"})
            manifest.update(files=files,serialization='verified_lossless_project_conversion',
                snapshot_directory=str(converted),conversion={
                    'source_bin_sha256':conversion['source_bin_sha256'],
                    'original_bin_path':str(original/'pytorch_model.bin'),
                    'receipt_path':str(converted/'conversion_receipt.json'),
                    'receipt_sha256':digest_file(converted/'conversion_receipt.json')})
            print(f"Original Cardiff conversion verified: {conversion['state_dict_keys']} tensor keys, all dtype/shape/raw bytes equal",flush=True)
        catalog['models'].append(manifest)
    for checkpoint in parent['candidate_checkpoints']:
        manifest=model_manifest(catalog,checkpoint)
        verify_local_files(Path(manifest['snapshot_directory']),manifest)
    plan=freeze_receipt_plan(benchmark,parent,catalog)
    output.mkdir(parents=True)
    save(output/'publisher_catalog.json',catalog)
    save(output/'plan.json',plan)
    receipt={'schema':'investify-complete-original-social-preparation-v1','checked_utc':datetime.now(timezone.utc).isoformat(),
             'status':'catalog_and_plan_frozen','catalog_sha256':digest(catalog),'plan_sha256':digest(plan),
             'parent_plan_sha256':digest(parent),'benchmark_sha256':plan['benchmark_sha256'],
             'candidate_checkpoints':plan['candidate_checkpoints'],'heldout_post_ids':plan['heldout_post_ids'],
             'model_inference_calls':0,'output_directory':str(output),'script_sha256':digest_file(Path(__file__)),
             'scope':'Original candidate weights/config/tokenizers and verified lossless Cardiff serialization. No candidate predictions or deployment decision.'}
    save(output/'preparation_receipt.json',receipt)
    print('Complete original catalog and new receipt-bound plan frozen:',output,flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
