"""Build editable project-specific TikZ and SVG design diagrams from one specification."""
from pathlib import Path
import json
import textwrap
from xml.sax.saxutils import escape
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'report/figures'
ASSETS = ROOT / 'code/app/assets'

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((text.rstrip()+'\n').replace('\n','\r\n').encode('utf-8'))

def tex_escape(text):
    for a,b in (('&',r'\&'),('_',r'\_'),('%',r'\%'),('#',r'\#')):
        text=text.replace(a,b)
    return text

def diagram(name,title,nodes,edges):
    """Coordinates are authored design geometry, not computed experimental outcomes."""
    by_id={n[0]:n for n in nodes}
    lines=[r'\begin{tikzpicture}[x=1mm,y=1mm,box/.style={draw=blue!45!black,fill=blue!2,rounded corners=1mm,align=center,text width=39mm,minimum height=22mm,inner sep=2mm,font=\sffamily\footnotesize},link/.style={->,>=stealth,draw=blue!50!black,thick}]']
    max_y=max(n[2] for n in nodes)
    width,height=900,int((max_y+16-min(n[2] for n in nodes))*6+122)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">', '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8Z" fill="#426c85"/></marker></defs>',f'<rect width="900" height="{height}" fill="#fff"/>',f'<text x="20" y="27" fill="#172b43" font-family="Arial" font-size="21" font-weight="bold">{escape(title)}</text>']
    def point(x,y):return x*6,(max_y+16-y)*6+32
    for ident,x,y,heading,body in nodes:
        label=r'\textbf{'+tex_escape(heading)+'}'+r'\\[1mm]'+r'\\'.join(tex_escape(v) for v in body)
        lines.append(f'\\node[box] ({ident}) at ({x},{y}) '+'{'+label+'};')
        sx,sy=point(x,y);svg.append(f'<rect x="{sx-129}" y="{sy-70}" width="258" height="140" rx="7" fill="#f3f7fa" stroke="#426c85" stroke-width="1.5"/>')
        content=[(heading,17,True)] + [(line,14,False) for b in body for line in textwrap.wrap(b,30)]
        top=sy-(len(content)*20)/2+14
        for i,(text,size,bold) in enumerate(content):svg.append(f'<text x="{sx}" y="{top+i*20}" text-anchor="middle" fill="#172b43" font-family="Arial" font-size="{size}" font-weight="{"bold" if bold else "normal"}">{escape(text)}</text>')
    for source,target,label in edges:
        a,b=by_id[source],by_id[target]
        if a[2]==b[2]:
            first,last=('east','west') if a[1]<b[1] else ('west','east')
            path=f'({source}.{first}) -- ({target}.{last})'
            x1,y1=point(a[1]+(21.5 if first=='east' else -21.5),a[2]);x2,y2=point(b[1]+(-21.5 if last=='west' else 21.5),b[2]);route=f'M{x1},{y1} L{x2},{y2}'
        else:
            first,last=('south','north') if a[2]>b[2] else ('north','south')
            dy=-6 if first=='south' else 6
            path=f'({source}.{first}) -- ++(0,{dy}) -| ({target}.{last})'
            x1,y1=point(a[1],a[2]+(-11.7 if first=='south' else 11.7));x2,y2=point(b[1],b[2]+(11.7 if last=='north' else -11.7));middle=y1+(36 if first=='south' else -36);route=f'M{x1},{y1} L{x1},{middle} L{x2},{middle} L{x2},{y2}'
        lines.append(r'\draw[link] '+path+(r' node[pos=.5,above,fill=white,inner sep=.5mm,font=\scriptsize]{'+tex_escape(label)+'}' if label else '')+';')
        svg.append(f'<path d="{route}" fill="none" stroke="#426c85" stroke-width="1.8" marker-end="url(#arrow)"/>')
    lines.append(r'\end{tikzpicture}');svg.append('</svg>')
    write(OUT/f'mid1_{name}.tex','\n'.join(lines));write(ASSETS/f'{name}.svg','\n'.join(svg))
    return {'name':name,'title':title,'nodes':[{'id':n[0],'x_mm':n[1],'y_mm':n[2],'heading':n[3],'fields':n[4]} for n in nodes],'edges':edges}

SPECS=[]
SPECS.append(diagram('domain','Implemented domain objects',[
 ('collection',23,100,'CaseCollection',['source, artifact SHA256','records by session']),
 ('record',75,100,'DecisionRecord',['ticker, session, horizon','class, probabilities','features and SHAP']),
 ('contrib',127,100,'FeatureContribution',['name, value, SHAP','rank and direction']),
 ('explanation',23,59,'Explanation',['visible candidate text','optional claim payload']),
 ('verification',75,59,'VerificationResult',['claim checks, hard gates','four quality metrics']),
 ('emission',127,59,'EmittedExplanation',['accepted or fallback text','retained rejected report']),
 ('profile',23,18,'RiskProfile',['capacity and tolerance','reconciled score R']),
 ('comparison',75,18,'Comparator result',['scaling provenance','fixed and profile scores']),
 ('study',127,18,'Study evidence',['frozen plan and run hashes','separate recorded study']),
 ],[('collection','record','1..n'),('record','contrib','0..k'),('record','verification','facts'),('explanation','verification','checks'),('verification','emission','result'),('profile','comparison','R')]))
SPECS.append(diagram('components','Implemented components and interfaces',[
 ('browser',75,140,'Browser',['localhost interface','selection and user actions']),
 ('presenter',75,105,'Presentation controller',['streamlit_app.py','presenter.py active page']),
 ('loader',23,70,'Recorded-data adapter',['presenter_data.load_cases','schema and identity checks']),
 ('checking',75,70,'Explanation checking',['verifier.verify','pipeline.emit']),
 ('risk',127,70,'Profile comparison',['score_profile','comparator.score']),
 ('artifacts',23,35,'Stored evidence',['decision JSON and receipts','original run identities']),
 ('context',75,35,'Evidence context',['build_context','maintained definitions']),
 ('result',127,35,'Comparison output',['fixed and profile scores','classifier remains unchanged']),
 ],[('browser','presenter',''),('presenter','loader',''),('presenter','checking',''),('presenter','risk',''),('loader','artifacts','read'),('checking','context','facts'),('risk','result','score')]))
SPECS.append(diagram('layers','Layer responsibilities',[
 ('ui',75,135,'Presentation',['focused Streamlit workspace','portable historical HTTP interface']),
 ('application',75,98,'Application services',['case selection, context, emission','prototype profile and recorded studies']),
 ('domain',75,61,'Domain contracts',['DecisionRecord and claim verification','profile rules and comparison invariants']),
 ('storage',75,24,'Artifact boundary',['JSON receipts and model records','Parquet feature store; E: model caches']),
 ],[('ui','application','calls'),('application','domain','validates'),('domain','storage','recorded evidence')]))
SPECS.append(diagram('dataflow','Data flow through the live module',[
 ('reviewer',75,143,'Reviewer',['session and source choice','candidate text; profile answers']),
 ('load',75,108,'P1 Validate case',['record schema and hash','one available recorded session']),
 ('store',23,108,'D1 Recorded decisions',['classifier probabilities','raw features and attributions']),
 ('context',23,67,'P2 Build context',['feature meanings and units','explicit absent inputs']),
 ('verify',75,67,'P3 Check explanation',['visible prose and JSON','against the selected record']),
 ('blend',127,67,'P4 Compare profile',['earlier scaling rows only','separate fixed/profile blend']),
 ('output',75,26,'Reviewed output',['class and source evidence','checked text or verified fallback']),
 ],[('reviewer','load','choice'),('store','load','read'),('load','context',''),('load','verify',''),('load','blend',''),('context','output',''),('verify','output',''),('blend','output','')]))
SPECS.append(diagram('state','Explanation UI state transitions',[
 ('selected',75,135,'Case selected',['candidate initialized','case and artifact identity']),
 ('edited',75,99,'Text edited',['verification becomes stale','no accepted result displayed']),
 ('checking',75,63,'Checking',['strict supported-claim gates','current case and text hash']),
 ('accepted',23,27,'Candidate accepted',['current verified text','retained metrics']),
 ('fallback',75,27,'Fallback verified',['rejected candidate retained','replacement checked separately']),
 ('error',127,27,'Unavailable or failed',['no verified output claimed','explicit retry or selection']),
 ],[('selected','edited','edit'),('edited','checking','check'),('checking','accepted','pass'),('checking','fallback','reject'),('checking','error','error')]))
SPECS.append(diagram('deployment','Local deployment topology',[
 ('browser',75,135,'User browser',['127.0.0.1:8507','Streamlit websocket and UI']),
 ('viewer',75,97,'Viewer Python 3.11',['isolated E: environment','no import-time model training']),
 ('project',23,59,'Project artifacts',['Investify/code and receipts','read recorded JSON evidence']),
 ('core',75,59,'Core modules',['context, verifier, pipeline','profile and comparator']),
 ('optional',127,59,'Optional local LLM',['explicit configured request','verified original checkpoint']),
 ('science',23,21,'Scientific environment',['separate offline/recovery run','verified prices/news/model cache']),
 ('cache',127,21,'E: caches and scratch',['original publisher weights','temporary builds and QA']),
 ],[('browser','viewer',''),('viewer','project',''),('viewer','core',''),('viewer','optional','optional'),('science','project','new outputs'),('optional','cache','weights')]))
SPECS.append(diagram('schema','Artifact schema and digest relationships',[
 ('manifest',23,105,'Corpus manifest',['raw-subset and vendor hashes','calendar and source metadata']),
 ('run',75,105,'Scientific run',['source/config/runtime identity','frozen and refit traces']),
 ('records',127,105,'Decision records',['session-keyed JSON array','model and data provenance']),
 ('benchmark',23,64,'Social benchmark',['post ID, text and AI reference','declared exclusions']),
 ('plan',75,64,'Selection plan',['benchmark digest, split','pinned candidate revisions']),
 ('bundle',127,64,'Model run bundle',['raw logits, probabilities','execution and byte receipts']),
 ('packet',23,23,'Teacher packet',['record and split identity','facts, patterns, definitions']),
 ('teacher',75,23,'Verified teacher result',['raw prose batch digest','independent verifier outcome']),
 ('exports',127,23,'Training exports',['accepted train/validation','test dates excluded']),
 ],[('manifest','run','hash'),('run','records','writes'),('benchmark','plan','hash'),('plan','bundle','binds'),('packet','teacher','binds'),('teacher','exports','filters')]))
SPECS.append(diagram('pipeline','Scientific pipeline and live explanation module',[
 ('inputs',23,135,'Verified snapshots',['NVDA daily prices/news','receipt and calendar admission']),
 ('sentiment',75,135,'Original FinBERT',['headline polarity scores','5,748 unique headlines']),
 ('features',127,135,'Session features',['technical and news features','strict-prior join and lags']),
 ('labels',23,94,'Observed labels',['one/five-session endpoints','availability-safe purge']),
 ('harness',75,94,'Leakage harness',['six folds and six arms','same rows and fixed seed']),
 ('engine',127,94,'Model and explanation data',['XGBoost and calibration','native TreeSHAP traces']),
 ('records',23,53,'Retained run artifacts',['186 decisions per mode','source/config/runtime hashes']),
 ('live',75,53,'Live review module',['context and claim checking','separate prototype risk blend']),
 ('studies',127,53,'Separate recorded studies',['original social classifiers','assistant teacher pilot']),
 ],[('inputs','sentiment','news'),('sentiment','features','text'),('inputs','labels','price'),('labels','harness','rows'),('features','engine',''),('harness','engine','eval'),('engine','records',''),('records','live','read'),('studies','live','view')]))
SPECS.append(diagram('equity_domain','Conceptual equity-to-explanation domain',[
 ('equity',30,115,'Equity',['ticker and study scope','NVDA or separate MSFT cohort']),
 ('observations',105,115,'Market observations',['dated prices and headlines','declared vendor/source vintage']),
 ('features',30,74,'Feature evidence',['technical and news values','session availability and units']),
 ('model',105,74,'Model run',['model/calibration identity','raw scores and attributions']),
 ('decision',30,33,'Recorded decision case',['class, probabilities, horizon','bound to source/session']),
 ('explanation',105,33,'Explanation and check',['candidate, factual claims','accepted or verified fallback']),
 ],[('equity','observations','1..n'),('observations','features',''),('features','model','input'),('model','decision',''),('decision','explanation','facts')]))
# Native lifelines and numbered messages: current local checking operation.
sequence=r'''\begin{tikzpicture}[x=.985mm,y=1mm,font=\sffamily\footnotesize,>=stealth]
\foreach \x/\n in {12/Reviewer,53/Streamlit UI,94/Record service,135/Verify and emit}{
\node[draw,fill=blue!3,text width=25mm,align=center,minimum height=10mm] at (\x,122){\n};
\draw[dashed,gray] (\x,116)--(\x,8);}
\draw[->] (12,105)--node[above]{1. Select case}(53,105);
\draw[->] (53,93)--node[above]{2. Load and validate}(94,93);
\draw[->,dashed] (94,81)--node[above]{3. Record and context}(53,81);
\draw[->] (12,69)--node[above]{4. Edit candidate}(53,69);
\draw[->] (53,57)--node[above]{5. Record, visible text and JSON}(135,57);
\node[align=left,text width=65mm,fill=blue!2,draw] at (100,39){6. Check both representations.\\If rejected, retain its report and independently verify the template.};
\draw[->,dashed] (135,21)--node[above]{7. Accepted text or verified fallback}(53,21);
\draw[->,dashed] (53,10)--node[above]{8. Show current result}(12,10);
\end{tikzpicture}'''
write(OUT/'mid1_sequence.tex',sequence)
activity=r'''\begin{tikzpicture}[x=1mm,y=1mm,box/.style={draw,rounded corners,text width=43mm,align=center,minimum height=12mm,font=\sffamily\footnotesize},>=stealth]
\node[box] (load) at (75,155){Load and validate the selected record};
\node[box] (candidate) at (75,131){Read current text and record-bound payload};
\node[box] (check) at (75,107){Verify visible claims and JSON independently};
\node[draw,diamond,aspect=2,align=center,font=\sffamily\footnotesize] (pass) at (75,80){Pass?};
\node[box] (accept) at (27,52){Emit accepted candidate and its report};
\node[box] (reject) at (123,52){Retain failure; render and verify fallback};
\node[box] (show) at (75,21){Display verified output; checking failure emits no success};
\draw[->](load)--(candidate);\draw[->](candidate)--(check);\draw[->](check)--(pass);
\draw[->](pass.west)-|node[pos=.25,above]{yes}(accept.north);
\draw[->](pass.east)-|node[pos=.25,above]{no}(reject.north);
\draw[->](accept.south)|-(show.west);\draw[->](reject.south)|-(show.east);
\end{tikzpicture}'''
write(OUT/'mid1_activity.tex',activity)
wireframe=r'''\begin{tikzpicture}[x=1mm,y=1mm,font=\sffamily\footnotesize]
\draw[gray] (0,0) rectangle (150,103);
\node[anchor=west,font=\sffamily\bfseries\small] at (5,96){Investify};
\node[anchor=east] at (145,96){Overview / Walkthrough / Experiments / Design};
\draw[gray!45] (5,89)--(145,89);
\node[anchor=west] at (5,82){Case selection (collapsed): experiment and recorded session};
\node[anchor=west] at (5,72){Decision / Evidence / Risk profile / Explanation check};
\draw[draw=gray!50,fill=blue!2] (5,17) rectangle (72,62);
\draw[draw=gray!50,fill=blue!2] (78,17) rectangle (145,62);
\node[align=left,text width=58mm] at (38,43){Editable candidate\\Displayed probability and claims\\[2mm]Inject error / restore facts\\Check explanation};
\node[align=left,text width=58mm] at (112,43){Checked output\\Accepted or rejected status\\[2mm]Verified fallback when needed\\Details stay collapsed};
\node[anchor=west] at (5,9){Previous};\node at (75,9){One active step};\node[anchor=east] at (145,9){Next};
\end{tikzpicture}'''
write(OUT/'mid1_wireframe.tex',wireframe)
write(OUT/'mid1_design_spec.json',json.dumps({'status':'assistant-drafted project-specific design; student/supervisor review pending','scope':'Diagrams describe implemented artifacts and interfaces; no relational database or trained student is invented','diagrams':SPECS},indent=2))
print('Built seven shared TikZ/SVG diagrams plus sequence, activity and UI wireframe sources.')
