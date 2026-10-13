/* Syntax verification only. No browser, navigation, DOM or model calls. */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const checks = [];
for (const relative of ['code/app/mideval_demo.html',
                         'code/app/demo_state.js', 'code/tests/test_demo_state.mjs',
                         'code/tests/test_demo_handlers.mjs']) {
  const file = path.join(root, relative);
  const bytes = fs.readFileSync(file);
  if (relative.endsWith('.html')) {
    const scripts = [...bytes.toString('utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
      .map(match => match[1]).filter(source => source.trim());
    for (const [index, source] of scripts.entries()) new vm.Script(source, {filename: relative + '#' + index});
    checks.push({file: relative, sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
                 syntax: 'passed', inline_scripts_parsed: scripts.length});
  } else {
    if (relative.endsWith('.mjs')) {
      if (typeof vm.SourceTextModule !== 'function') throw new Error('Use node --experimental-vm-modules for in-process ESM parsing');
      new vm.SourceTextModule(bytes.toString('utf8'), {identifier: relative});
    } else {
      new vm.Script(bytes.toString('utf8'), {filename: relative});
    }
    checks.push({file: relative, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), syntax: 'passed'});
  }
}
const receipt = {checked_utc: new Date().toISOString(), node: process.version, checks,
  browser_visual_qa: false, browser_navigation: false, handlers_executed: false,
  scope: 'HTML inline-script and Node source syntax only; controlled handler execution has a separate receipt.'};
const index = process.argv.indexOf('--output');
if (index < 0) throw new Error('Use --output with a new evidence JSON path');
const destination = path.resolve(process.argv[index + 1] ?? '');
if (path.dirname(destination) !== path.resolve(root, 'evidence') || path.extname(destination) !== '.json') {
  throw new Error('Use a new JSON receipt in the project evidence directory');
}
fs.writeFileSync(destination, JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
console.log('JavaScript syntax: ' + checks.length + ' sources passed; no browser QA');
