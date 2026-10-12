/* Controlled DOM/fetch fixtures execute the real inline handlers in Node.
 * No browser, navigation, live service, saved research data or model is used.
 */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const htmlPath = new URL('../app/mideval_demo.html', import.meta.url);
const statePath = new URL('../app/demo_state.js', import.meta.url);
const html = fs.readFileSync(htmlPath, 'utf8');
const stateSource = fs.readFileSync(statePath, 'utf8');
const inline = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).filter(source => source.trim()).join('\n');
const drain = () => new Promise(resolve => setImmediate(resolve));

function harness() {
  const elements = new Map();
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase(); this.children = []; this.listeners = new Map();
      this._value = ''; this._text = ''; this._selected = -1;
      this.hidden = false; this.disabled = false; this.checked = false;
    }
    set id(value) { this._id = value; elements.set(value, this); }
    get id() { return this._id; }
    get options() { return this.children.filter(child => child.tagName === 'OPTION'); }
    get selectedIndex() { return this._selected; }
    set selectedIndex(value) { this._selected = value; }
    get value() {
      return this.tagName === 'SELECT' ? (this.options[this._selected]?.value ?? '') : this._value;
    }
    set value(value) {
      if (this.tagName === 'SELECT') this._selected = this.options.findIndex(option => option.value === String(value));
      else this._value = String(value);
    }
    get textContent() { return this._text; }
    set textContent(value) { this._text = String(value); }
    append(...children) {
      this.children.push(...children);
      if (this.tagName === 'SELECT' && this._selected < 0 && this.options.length) this._selected = 0;
    }
    removeIds() {
      if (this.id && elements.get(this.id) === this) elements.delete(this.id);
      for (const child of this.children) if (child instanceof Element) child.removeIds();
    }
    replaceChildren(...children) {
      for (const child of this.children) if (child instanceof Element) child.removeIds();
      this.children = []; this._selected = -1; this.append(...children);
    }
    querySelectorAll(selector) {
      const result = [];
      for (const child of this.children) if (child instanceof Element) {
        if (child.tagName === selector.toUpperCase()) result.push(child);
        result.push(...child.querySelectorAll(selector));
      }
      return result;
    }
    addEventListener(type, listener, capture = false) {
      const list = this.listeners.get(type) ?? []; list.push({listener, capture}); this.listeners.set(type, list);
    }
    async fire(type) {
      const event = {defaultPrevented: false, stopped: false,
        preventDefault() { this.defaultPrevented = true; },
        stopImmediatePropagation() { this.stopped = true; }};
      for (const {listener} of [...(this.listeners.get(type) ?? [])].sort((a, b) => Number(b.capture) - Number(a.capture))) {
        await listener(event); if (event.stopped) break;
      }
    }
  }
  for (const match of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const element = new Element(match[1]); element.id = match[2];
    element.hidden = /\bhidden\b/.test(match[0]); element.checked = /\bchecked\b/.test(match[0]);
  }
  const requests = [];
  function fetch(url, options = {}) {
    return new Promise((resolve, reject) => requests.push({
      url: String(url), body: options.body ? JSON.parse(options.body) : undefined,
      resolve, reject, settled: false
    }));
  }
  const context = {
    document: {getElementById: id => elements.get(id), createElement: tag => new Element(tag),
      createTextNode: text => { const node = new Element('#text'); node.textContent = text; return node; }},
    fetch, URLSearchParams
  };
  vm.createContext(context); vm.runInContext(stateSource, context); vm.runInContext(inline, context);
  return {
    get: id => elements.get(id), state: expression => vm.runInContext(expression, context),
    fire: (id, type = 'click') => elements.get(id).fire(type),
    request: prefix => {
      const request = requests.find(item => !item.settled && item.url.startsWith(prefix));
      assert.ok(request, 'Expected pending fixture request ' + prefix); return request;
    },
    pending: prefix => requests.filter(item => !item.settled && item.url.startsWith(prefix)),
    async respond(request, data, status = 200) {
      request.settled = true; request.resolve({ok: status >= 200 && status < 300, json: async () => data}); await drain(); await drain();
    },
    async fail(request, reason = 'LABELLED fixture connection failure') {
      request.settled = true; request.reject(new Error(reason)); await drain(); await drain();
    }
  };
}

const sessions = ['2023-01-02', '2023-01-03'];
const catalogue = () => ({
  corpora: {alpaca: {label: 'LABELLED Alpaca fixture', sessions}, fnspid: {label: 'LABELLED FNSPID fixture', sessions}},
  unavailable: {missing_fixture: 'LABELLED unavailable source'}, risk_comparator_unavailable: {}
});
const profile = () => ({
  capacity_options: {horizon: {'5+ years': 1}, buffer: {'6+ months': 1}, stability: {'Salaried and stable': 1}, dependants: {'0': 1}, age: {'18-30': 1}},
  tolerance_questions: [['LABELLED question 1', ['0', '1', '2']], ['LABELLED question 2', ['0', '1', '2']], ['LABELLED question 3', ['0', '1', '2']]]
});
function record(session = sessions[1]) {
  return {
    context: {decision: 'Buy', horizon_days: 5, probabilities: {Buy: .7, Hold: .2, Sell: .1},
      interpretation: 'LABELLED fixture only', features: [],
      coverage: {social_sentiment: 'LABELLED no social feature', risk_conditioning: 'LABELLED separate comparator'},
      data_status: 'LABELLED historical fixture', session_date: session, notice: 'LABELLED non-advice notice', model_version: 'LABELLED fixture model'},
    template: {text: 'LABELLED template ' + session, payload: {confidence: .7, contributions: []}}
  };
}
const report = () => ({passed: true, failed_metrics: [], numeric_fidelity: 1, directional_consistency: 1, claim_recall: 1, unverifiable_rate: 0, claims: []});
const verified = () => ({text: 'LABELLED accepted text', replaced_by_template: false, candidate: report(), emitted: report(), verifier_contract: 'LABELLED fixture contract'});
const guided = text => ({used_template: true, reason: 'LABELLED unconfigured fixture', text, attempts: []});
function comparator(score) {
  return {
    profile: {tier: 'LABELLED prototype', binding_axis: 'tolerance', score, capacity_raw: 1, capacity_score: 1, tolerance_score: score, matched_caps: [], cap_binding: false},
    scaling_fit_end: '2022-12-30', reference: {decision: 'Hold', score: .2},
    profile_conditioned: {decision: 'Hold', score}, sentiment_signal: .1, technical_signal: .3,
    missing_sentiment: false, scaled_inputs: {}, limitation: 'LABELLED no suitability or prediction outcome'
  };
}
async function boot({profileFailure = false, recordPending = false} = {}) {
  const h = harness();
  const initialProfile = h.request('/api/profile-contract');
  if (profileFailure) await h.fail(initialProfile); else await h.respond(initialProfile, profile());
  await h.respond(h.request('/api/explainer-status'), {configured: false});
  await h.respond(h.request('/api/catalog'), catalogue());
  if (!recordPending) await h.respond(h.request('/api/record'), record());
  return h;
}
async function answerProfile(h, tolerance = '1') {
  for (const name of Object.keys(profile().capacity_options)) h.get('profile-' + name).selectedIndex = 1;
  for (let i = 0; i < 3; i++) h.get('tolerance-' + i).value = tolerance;
}
const cases = [];
async function check(name, action) { await action(); cases.push({case: name, passed: true}); }

await check('late_catalogue_empty_cannot_replace_newer_source_selection', async () => {
  const h = harness(), old = h.request('/api/catalog');
  void h.fire('refresh-catalog'); const fresh = h.pending('/api/catalog').at(-1);
  await h.respond(fresh, catalogue()); await h.respond(h.request('/api/record'), record());
  h.get('corpus').value = 'fnspid'; void h.fire('corpus', 'change');
  await h.respond(h.request('/api/record'), record());
  await h.respond(old, {corpora: {}, unavailable: {old: 'LABELLED old failure'}});
  assert.equal(h.get('corpus').value, 'fnspid'); assert.equal(h.get('workspace').hidden, false);
  assert.equal(h.get('status').textContent, 'Historical record loaded. Verification runs locally when requested.');
});
await check('late_catalogue_failure_does_not_overwrite_newer_success', async () => {
  const h = harness(), old = h.request('/api/catalog');
  void h.fire('refresh-catalog'); await h.respond(h.pending('/api/catalog').at(-1), catalogue());
  await h.respond(h.request('/api/record'), record()); await h.fail(old);
  assert.equal(h.get('workspace').hidden, false); assert.match(h.get('status').textContent, /record loaded/);
});
await check('accepted_empty_catalogue_invalidates_loaded_record_and_reports', async () => {
  const h = await boot();
  void h.fire('verify'); await h.respond(h.request('/api/verify'), verified());
  assert.equal(h.get('reports').hidden, false);
  void h.fire('refresh-catalog'); await h.respond(h.request('/api/catalog'), {corpora: {}, unavailable: {alpaca: 'LABELLED missing bytes'}});
  assert.equal(h.state('current'), null); assert.equal(h.get('workspace').hidden, true);
  assert.equal(h.get('reports').hidden, true); assert.equal(h.get('result').hidden, true);
  assert.equal(h.get('corpus').options.length, 0); assert.equal(h.get('session').options.length, 0);
  assert.match(h.get('catalog-limitations').textContent, /missing bytes/); assert.equal(h.get('compare-risk').disabled, true);
});
await check('source_refresh_preserves_available_selected_session_and_exposes_degradation', async () => {
  const h = await boot(); h.get('corpus').value = 'fnspid'; void h.fire('corpus', 'change');
  await h.respond(h.request('/api/record'), record()); h.get('session').value = sessions[0]; void h.fire('session', 'change');
  await h.respond(h.request('/api/record'), record(sessions[0]));
  void h.fire('refresh-catalog'); const data = catalogue(); data.risk_comparator_unavailable.fnspid = 'LABELLED missing comparator';
  await h.respond(h.request('/api/catalog'), data);
  assert.equal(h.get('corpus').value, 'fnspid'); assert.equal(h.get('session').value, sessions[0]);
  await h.respond(h.request('/api/record'), record(sessions[0])); assert.match(h.get('catalog-limitations').textContent, /missing comparator/);
});
await check('record_responses_are_bound_to_the_latest_session', async () => {
  const h = await boot({recordPending: true}), old = h.request('/api/record');
  h.get('session').value = sessions[0]; void h.fire('session', 'change'); const fresh = h.pending('/api/record').at(-1);
  await h.respond(fresh, record(sessions[0])); await h.respond(old, record(sessions[1]));
  assert.equal(h.get('session').value, sessions[0]); assert.match(h.get('data').textContent, /2023-01-02/);
});
await check('record_failure_retains_selection_and_retry_recovery', async () => {
  const h = await boot({recordPending: true}); await h.fail(h.request('/api/record'));
  assert.equal(h.get('workspace').hidden, true); assert.equal(h.get('corpus').options.length, 2);
  assert.equal(h.get('retry-record').disabled, false); void h.fire('retry-record');
  await h.respond(h.request('/api/record'), record()); assert.equal(h.get('workspace').hidden, false);
});
await check('profile_retry_recovers_without_defaults_or_duplicate_fields', async () => {
  const h = await boot({profileFailure: true}); assert.equal(h.get('compare-risk').disabled, true);
  void h.fire('retry-profile'); const old = h.request('/api/profile-contract');
  void h.fire('retry-profile'); const fresh = h.pending('/api/profile-contract').at(-1);
  await h.respond(fresh, profile()); await h.respond(old, profile());
  const fields = h.get('profile-fields').querySelectorAll('select');
  assert.equal(fields.length, 8); assert.ok(fields.every(field => field.value === ''));
  assert.equal(h.get('compare-risk').disabled, false);
  await h.fire('risk-form', 'submit'); assert.equal(h.pending('/api/risk-comparator').length, 0);
});
await check('profile_retry_invalidates_pending_comparator_and_late_contract_failure', async () => {
  const h = await boot(); await answerProfile(h); void h.fire('risk-form', 'submit'); await drain();
  const oldRisk = h.request('/api/risk-comparator'); void h.fire('retry-profile'); const oldProfile = h.request('/api/profile-contract');
  void h.fire('retry-profile'); await h.respond(h.pending('/api/profile-contract').at(-1), profile());
  await h.fail(oldProfile); await h.respond(oldRisk, comparator(.9));
  assert.equal(h.get('risk-result').hidden, true); assert.equal(h.get('profile-fields').querySelectorAll('select').length, 8);
  assert.match(h.get('risk-status').textContent, /no defaults/);
});
await check('obsolete_comparator_cannot_publish_or_release_a_newer_request', async () => {
  const h = await boot(); await answerProfile(h); void h.fire('risk-form', 'submit'); await drain();
  const old = h.request('/api/risk-comparator');
  h.get('tolerance-0').value = '2'; await h.fire('tolerance-0', 'change');
  assert.equal(h.get('compare-risk').disabled, false); void h.fire('risk-form', 'submit'); await drain();
  const fresh = h.pending('/api/risk-comparator').at(-1); await h.respond(old, comparator(.1));
  assert.equal(h.get('compare-risk').disabled, true); assert.equal(h.get('risk-result').hidden, true);
  await h.respond(fresh, comparator(.8)); assert.equal(h.get('compare-risk').disabled, false);
  assert.equal(h.get('risk-result').hidden, false); assert.match(h.get('risk-conditioned-score').textContent, /0.800/);
});
await check('guided_response_and_cleanup_cannot_cross_record_selection', async () => {
  const h = await boot(); void h.fire('explain'); const old = h.request('/api/explain');
  h.get('session').value = sessions[0]; void h.fire('session', 'change'); await h.respond(h.request('/api/record'), record(sessions[0]));
  void h.fire('explain'); const fresh = h.pending('/api/explain').at(-1); await h.respond(old, guided('LABELLED obsolete guide'));
  assert.equal(h.get('generation-result').hidden, true); assert.equal(h.get('verify').disabled, true);
  await h.respond(fresh, guided('LABELLED current guide')); assert.equal(h.get('generated').textContent, 'LABELLED current guide');
  assert.equal(h.get('verify').disabled, false);
});
await check('verification_edits_invalidate_report_and_preserve_independent_outputs', async () => {
  const h = await boot(); void h.fire('explain'); await h.respond(h.request('/api/explain'), guided('LABELLED independent guide'));
  await answerProfile(h); void h.fire('risk-form', 'submit'); await drain(); await h.respond(h.request('/api/risk-comparator'), comparator(.5));
  void h.fire('verify'); await h.respond(h.request('/api/verify'), verified());
  h.get('candidate').value += ' LABELLED edited'; await h.fire('candidate', 'input');
  assert.equal(h.get('reports').hidden, true); assert.equal(h.get('result').hidden, true);
  assert.equal(h.get('generation-result').hidden, false); assert.equal(h.get('risk-result').hidden, false);
  void h.fire('verify'); const pending = h.request('/api/verify'); h.get('strict').checked = false; await h.fire('strict', 'change');
  await h.respond(pending, verified()); assert.equal(h.get('reports').hidden, true);
});
await check('latest_guided_request_owns_output_and_busy_cleanup', async () => {
  const h = await boot(); void h.fire('explain'); const old = h.request('/api/explain');
  // Direct event delivery is a controlled fixture, not browser interaction.
  void h.fire('explain'); const fresh = h.pending('/api/explain').at(-1);
  await h.respond(old, guided('LABELLED old guide')); assert.equal(h.get('verify').disabled, true);
  await h.respond(fresh, guided('LABELLED latest guide')); assert.equal(h.get('generated').textContent, 'LABELLED latest guide');
  assert.equal(h.get('verify').disabled, false);
});

const receipt = {
  schema: 'investify-controlled-node-handler-tests-v1', checked_utc: new Date().toISOString(),
  execution_kind: 'controlled_dom_and_deferred_fetch_fixtures_node_only',
  cases_passed: cases.length, cases, all_checks_passed: true,
  browser_navigation: false, browser_visual_qa: false, live_server_requests: false,
  model_inference: false, source_sha256: {
    'app/mideval_demo.html': crypto.createHash('sha256').update(fs.readFileSync(htmlPath)).digest('hex'),
    'app/demo_state.js': crypto.createHash('sha256').update(fs.readFileSync(statePath)).digest('hex'),
    'tests/test_demo_handlers.mjs': crypto.createHash('sha256').update(fs.readFileSync(new URL(import.meta.url))).digest('hex')
  }
};
const index = process.argv.indexOf('--receipt');
if (index >= 0) {
  const destination = path.resolve(process.argv[index + 1] ?? '');
  const evidence = fileURLToPath(new URL('../../evidence/', import.meta.url));
  if (path.dirname(destination) !== path.resolve(evidence) || path.extname(destination) !== '.json') throw new Error('Receipt must be a new JSON file in this project evidence directory');
  fs.writeFileSync(destination, JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
}
console.log(JSON.stringify(receipt, null, 2));
