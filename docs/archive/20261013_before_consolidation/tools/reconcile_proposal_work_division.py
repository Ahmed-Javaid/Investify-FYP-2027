"""Carry the preserved proposal's SmartArt assignments into current Mid-1 drafts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/Investify Updated (1).pptx'
OUTPUT = ROOT / 'evidence/proposal_work_division_20261013.json'


def main():
    if OUTPUT.exists():
        raise ValueError('Preserve earlier proposal-assignment receipts')
    ns = {'d': 'http://schemas.openxmlformats.org/drawingml/2006/diagram',
          'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    with ZipFile(SOURCE) as archive:
        diagram_bytes = archive.read('ppt/diagrams/data2.xml')
        diagram = ET.fromstring(diagram_bytes)
        points = {p.get('modelId'): ' '.join(t.text or '' for t in p.findall('.//a:t', ns))
                  for p in diagram.findall('.//d:ptLst/d:pt', ns)}
        owners = ('Ahmed Javaid', 'Rafay Ul Haq', 'Soban Ahmed')
        assigned = {owner: [] for owner in owners}
        for edge in diagram.findall('.//d:cxnLst/d:cxn', ns):
            owner, task = points.get(edge.get('srcId')), points.get(edge.get('destId'))
            if edge.get('type', 'parOf') == 'parOf' and owner in assigned and task:
                assigned[owner].append((int(edge.get('srcOrd')), task))
        rows = [{'source_name': owner, 'member': 'Soban Ahmad' if owner == 'Soban Ahmed' else owner,
                 'planned_tasks': [task for _, task in sorted(assigned[owner])],
                 'actual_completion_or_authorship_established': False} for owner in owners]
        if any(len(row['planned_tasks']) != 5 for row in rows):
            raise ValueError('Unexpected proposal assignment structure')
    receipt = {'schema': 'investify-proposal-work-division-v1',
               'checked_utc': datetime.now(timezone.utc).isoformat(),
               'source': SOURCE.relative_to(ROOT).as_posix(), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               'slide': 13, 'smartart_part': 'ppt/diagrams/data2.xml',
               'smartart_sha256': hashlib.sha256(diagram_bytes).hexdigest(),
               'method': 'Read the original SmartArt parent/child connections and source ordering, not slide-text order alone',
               'assignments': rows,
               'name_reconciliation': 'Slide 13 spells Soban Ahmed. The supplied cover/student record uses Soban Ahmad (22I-2460), retained in the current report.',
               'scope': 'Original planned work division. It does not certify who authored or completed current assistant-supported modules.'}
    OUTPUT.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    md = ['# Proposal-based work division', '',
          'The planned assignments below come from slide 13 of the preserved proposal deck. The current report uses the supplied student-record spelling, Soban Ahmad. The source slide spells Soban Ahmed.', '',
          '| Member | Planned responsibilities from the proposal | Actual completion evidence |', '| --- | --- | --- |']
    tex = [r'\begin{longtable}{p{0.21\textwidth}p{0.48\textwidth}p{0.21\textwidth}}\toprule',
           r'Member & Proposal-assigned responsibilities & Completion evidence\\\midrule']
    for row in rows:
        tasks = '; '.join(row['planned_tasks'])
        md.append(f'| {row["member"]} | {tasks} | Member confirmation and function-level defence still required. |')
        tex.append(row['member'] + ' & ' + tasks + r' & Actual member work and defence to be recorded.\\')
    tex.append(r'\bottomrule\end{longtable}')
    md += ['', '[Byte-bound source receipt](../evidence/proposal_work_division_20261013.json). Original proposal bytes remain unchanged.', '',
           'These allocations organize work and defence preparation. Actual implementation, review, tests understood and assistant-generated contributions must be recorded by each member. Historical repository authorship is preserved. QLoRA is planned later work and remains unexecuted.', '']
    (ROOT / 'deliverables/WORK_DIVISION.md').write_text('\n'.join(md), encoding='utf-8')
    (ROOT / 'report/chapters/proposal_work_division.tex').write_text('\n'.join(tex) + '\n', encoding='utf-8')
    print('Recovered and documented three proposal owners and fifteen exact planned assignments.')


if __name__ == '__main__':
    main()
