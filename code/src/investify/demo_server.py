"""Local historical-record demo with live verification; standard library only.

This serves saved decisions and calls the real explanation verifier. It does
not train, fetch prices, personalise predictions, or simulate LLM generations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from investify.decision_record import DecisionRecord
from investify.explain.context import build_context
from investify.explain.pipeline import emit
from investify.explain.local_llm import ExplainerConfig, LocalExplainer, PROMPT_VERSION
from investify.explain.template import Explanation, render
from investify.explain.verifier import VERIFIER_CONTRACT_VERSION
from investify.risk_comparator import build_comparator
from investify.risk_profile import CAPACITY_OPTIONS, CAPACITY_WEIGHTS, TOLERANCE_QUESTIONS, PROFILE_VERSION, score_profile

ROOT = Path(__file__).resolve().parents[2]
CORPORA = {
    "alpaca": ("Alpaca / Benzinga", "decision_records_alpaca.json"),
    "fnspid": ("FNSPID", "decision_records.json"),
}
MAX_REQUEST_BYTES = 128 * 1024


class DemoCatalog:
    def __init__(self, artifacts: Path = ROOT / "artifacts"):
        self.records = {}
        self.errors = {}
        self.comparators = {}
        self.comparator_errors = {}
        for corpus, (_, filename) in CORPORA.items():
            try:
                data = json.loads((artifacts / filename).read_text(encoding="utf-8"))
                records = [DecisionRecord.from_dict(p) for p in data["decision_records"]]
                if not records:
                    raise ValueError("the corpus contains no decision records")
                for record in records:
                    # Validate JSON-safe context as well as the frozen schema.
                    json.dumps(build_context(record, corpus=corpus), allow_nan=False)
                by_date = {r.session_date: r for r in records}
                if len(by_date) != len(records):
                    raise ValueError("duplicate session dates in this single-ticker corpus")
                self.records[corpus] = by_date
            except (OSError, KeyError, TypeError, ValueError) as error:
                self.errors[corpus] = f"Historical decisions unavailable: {error}"
            if corpus in self.records:
                try:
                    self.comparators[corpus] = build_comparator(artifacts / filename, corpus=corpus)
                except (OSError, KeyError, TypeError, ValueError, OverflowError) as error:
                    self.comparator_errors[corpus] = f"Separate comparator unavailable: {error}"

    def summary(self) -> dict:
        return {
            "corpora": {
                key: {"label": CORPORA[key][0], "sessions": sorted(records),
                      "decision_counts": dict(Counter(r.decision for r in records.values()))}
                for key, records in self.records.items()
            },
            "unavailable": self.errors,
            "verifier_contract": VERIFIER_CONTRACT_VERSION,
            "risk_comparators": {key: {'fit_end': item.manifest['fit_end'],
                                      'fit_rows': item.manifest['fit_rows'],
                                      'heldout_sessions': item.manifest['heldout_sessions'],
                                      'version': item.manifest['version']}
                                 for key, item in self.comparators.items()},
            "risk_comparator_unavailable": self.comparator_errors,
        }

    def get(self, corpus: str, session: str) -> DecisionRecord:
        if corpus not in CORPORA:
            raise ValueError("Unknown news corpus")
        if corpus not in self.records:
            raise ValueError("Historical decisions for this corpus are unavailable")
        try:
            return self.records[corpus][session]
        except KeyError:
            raise ValueError("No recorded decision for this session") from None


def record_view(catalog: DemoCatalog, corpus: str, session: str) -> dict:
    record = catalog.get(corpus, session)
    template = render(record)
    return {"context": build_context(record, corpus=CORPORA[corpus][0]),
            "template": {"text": template.text, "payload": template.payload}}


def risk_view(catalog: DemoCatalog, request: dict) -> dict:
    if not isinstance(request, dict) or set(request) != {'corpus', 'session', 'capacity', 'tolerance'}:
        raise ValueError('Select a corpus/session and supply exactly capacity and tolerance answers')
    if not isinstance(request['corpus'], str) or not isinstance(request['session'], str):
        raise ValueError('Corpus and session must be text')
    catalog.get(request['corpus'], request['session'])
    profile = score_profile(request['capacity'], request['tolerance'])
    if request['corpus'] not in catalog.comparators:
        raise ValueError('The separate comparator for this corpus is unavailable')
    return catalog.comparators[request['corpus']].score(request['session'], profile)


def _report(result) -> dict:
    return {"passed": result.passed, "failed_metrics": list(result.failed_metrics),
            "numeric_fidelity": result.numeric_fidelity,
            "directional_consistency": result.directional_consistency,
            "claim_recall": result.claim_recall,
            "unverifiable_rate": result.unverifiable_rate,
            "claims": result.as_table()}


def verify_view(catalog: DemoCatalog, request: dict) -> dict:
    if not isinstance(request, dict) or not isinstance(request.get("text"), str):
        raise ValueError("The explanation must include a text field")
    if not isinstance(request.get("corpus"), str) or not isinstance(request.get("session"), str):
        raise ValueError("Select a news corpus and a recorded session")
    strict = request.get("strict_prose", True)
    if type(strict) is not bool:
        raise ValueError("strict_prose must be true or false")
    record = catalog.get(request["corpus"], request["session"])
    emitted = emit(record, Explanation(request["text"], request.get("payload")),
                   strict_prose=strict)
    candidate_result = emitted.rejected_verification or emitted.verification
    return {"text": emitted.text, "replaced_by_template": emitted.replaced_by_template,
            "candidate": _report(candidate_result), "emitted": _report(emitted.verification),
            "verifier_contract": VERIFIER_CONTRACT_VERSION,
            "strict_prose": strict}


def explain_view(catalog: DemoCatalog, request: dict, explainer: LocalExplainer) -> dict:
    if (not isinstance(request, dict) or not isinstance(request.get("corpus"), str) or
            not isinstance(request.get("session"), str)):
        raise ValueError("Select a news corpus and a recorded session")
    record = catalog.get(request["corpus"], request["session"])
    result = explainer.explain(record, corpus=CORPORA[request["corpus"]][0])
    return {"text": result.emitted.text, "status": result.status, "reason": result.reason,
            "used_template": result.used_template, "requested_model": result.requested_model,
            "prompt_version": result.prompt_version,
            "emitted": _report(result.emitted.verification),
            "attempts": [{"number": attempt.number, "served_model": attempt.served_model,
                          "elapsed_seconds": attempt.elapsed_seconds,
                          "error": attempt.error, "raw_output": attempt.raw_output,
                          "finish_reason": attempt.finish_reason,
                          "verification": _report(attempt.verification) if attempt.verification else None}
                         for attempt in result.attempts],
            "verifier_contract": VERIFIER_CONTRACT_VERSION}


def make_server(port: int = 8765, *, catalog: DemoCatalog | None = None,
                explainer: LocalExplainer | None = None) -> ThreadingHTTPServer:
    catalog = catalog if catalog is not None else DemoCatalog()
    explainer = explainer if explainer is not None else LocalExplainer()
    page_html = (ROOT / "app/mideval_demo.html").read_bytes()
    state_js = (ROOT / 'app/demo_state.js').read_bytes()
    sources = [Path(__file__), ROOT / "src/investify/explain/verifier.py",
               ROOT / "src/investify/explain/pipeline.py", ROOT / "app/mideval_demo.html",
               ROOT / "src/investify/explain/local_llm.py", ROOT / "src/investify/explain/template.py",
               ROOT / "src/investify/explain/context.py", ROOT / "src/investify/risk_profile.py",
               ROOT / "src/investify/risk_comparator.py", ROOT / "src/investify/decision_record.py"]
    sources.append(ROOT / 'app/demo_state.js')
    source_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sources}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            # Do not write request data into an application log.
            return

        def send_body(self, status, body, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, value):
            self.send_body(status, json.dumps(value, allow_nan=False).encode("utf-8"))

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path == "/":
                self.send_body(200, page_html,
                               "text/html; charset=utf-8")
            elif path.path == '/static/demo_state.js':
                self.send_body(200, state_js, 'text/javascript; charset=utf-8')
            elif path.path == "/health":
                self.send_json(200, {"ready": bool(catalog.records),
                                    "records": sum(len(rows) for rows in catalog.records.values()),
                                    "source_sha256": source_hashes,
                                    "verifier_contract": VERIFIER_CONTRACT_VERSION})
            elif path.path == "/api/catalog":
                self.send_json(200, catalog.summary())
            elif path.path == "/api/profile-contract":
                self.send_json(200, {'version': PROFILE_VERSION, 'capacity_options': CAPACITY_OPTIONS,
                                    'capacity_weights': CAPACITY_WEIGHTS, 'tolerance_questions': TOLERANCE_QUESTIONS,
                                    'notice': 'Project prototype, not a validated risk instrument. No answers are defaulted.'})
            elif path.path == "/api/explainer-status":
                self.send_json(200, {"configured": explainer.config.model is not None,
                                    "model": explainer.config.model,
                                    "base_url": explainer.config.base_url,
                                    "max_attempts": explainer.config.max_attempts,
                                    "timeout_seconds": explainer.config.timeout_seconds,
                                    "prompt_version": PROMPT_VERSION})
            elif path.path == "/api/record":
                query = parse_qs(path.query)
                try:
                    view = record_view(catalog, query.get("corpus", [""])[0],
                                       query.get("session", [""])[0])
                except ValueError as error:
                    self.send_json(400, {"error": str(error)})
                else:
                    self.send_json(200, view)
            else:
                self.send_json(404, {"error": "Page not found"})

        def do_POST(self):
            route = urlsplit(self.path).path
            if route not in {"/api/verify", "/api/explain", "/api/risk-comparator"}:
                self.send_json(404, {"error": "Page not found"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send_json(415, {"error": "Use a JSON explanation request"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if not 0 < length <= MAX_REQUEST_BYTES:
                self.send_json(413, {"error": "Explanation request is empty or too large"})
                return
            try:
                def invalid_number(value):
                    raise ValueError(f"Non-finite JSON number: {value}")
                request = json.loads(self.rfile.read(length), parse_constant=invalid_number)
                view = (verify_view(catalog, request) if route == "/api/verify" else
                        risk_view(catalog, request) if route == "/api/risk-comparator" else
                        explain_view(catalog, request, explainer))
            except (UnicodeError, ValueError) as error:
                self.send_json(400, {"error": str(error)})
            else:
                self.send_json(200, view)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--llm-model", help="Exact identifier of an already available local model")
    parser.add_argument("--llm-base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--llm-timeout", type=float, default=20)
    args = parser.parse_args()
    explainer = LocalExplainer(ExplainerConfig(model=args.llm_model, base_url=args.llm_base_url,
                                             timeout_seconds=args.llm_timeout,
                                             api_key=os.environ.get("INVESTIFY_LLM_API_KEY") or None))
    with make_server(args.port, explainer=explainer) as server:
        print(f"Investify live verification demo: http://127.0.0.1:{server.server_port}", flush=True)
        print("Historical decisions; no retraining. LLM " +
              (f"configured as {args.llm_model}" if args.llm_model else "unconfigured; verified guide available") +
              ". Ctrl+C stops the server.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
