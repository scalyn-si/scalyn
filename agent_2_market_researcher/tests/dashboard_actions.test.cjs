// Exercise the actual dashboard script with a minimal DOM and API responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const html = fs.readFileSync(path.join(__dirname, '../web/dashboard.html'), 'utf8');
const script = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');

function dashboard(response) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: 'https://example.com', disabled: false, innerHTML: '', textContent: '',
      style: {}, children: [], classList: { add() {}, remove() {} },
      appendChild(child) { this.children.push(child); }, focus() {},
    });
    return elements.get(id);
  }
  const requests = [];
  const context = vm.createContext({
    console, Date, Set, JSON,
    document: { getElementById: element, createElement: () => element(Symbol()) },
    window: { addEventListener() {} }, requestAnimationFrame() {},
    setTimeout() {}, setInterval() { return 1; }, clearInterval() {},
    async fetch(url, options) {
      requests.push({ url, options });
      if (url === '/api/leads') return { ok: true, json: async () => ({ status: 'success', leads: [], total_count: 0 }) };
      if (url === '/api/logs') return { ok: true, json: async () => ({ logs: [] }) };
      return { ok: response.status < 400, json: async () => response.body };
    },
  });
  vm.runInContext(script, context);
  return { context, element, requests };
}

test('crawl displays the extracted business profile and restores the button', async () => {
  const app = dashboard({ status: 200, body: { status: 'success', profile: { startup_name: 'Example', industry: 'Logistics' } } });
  await app.context.inspectUrlLive();
  assert.match(app.element('toast-text').textContent, /Ingested Example/);
  assert.equal(app.element('btn-explore-site').disabled, false);
  assert.equal(JSON.parse(app.requests.find(r => r.url === '/api/analyze-website').options.body).url, 'https://example.com');
});

test('crawl displays backend errors without claiming success', async () => {
  const app = dashboard({ status: 422, body: { status: 'error', message: 'Could not crawl example.com: 403 Forbidden' } });
  await app.context.inspectUrlLive();
  assert.match(app.element('toast-text').textContent, /403 Forbidden/);
  assert.equal(app.element('btn-explore-site').disabled, false);
});

test('scout reads the response and reports the actual count', async () => {
  const app = dashboard({ status: 200, body: { status: 'success', discovered_count: 3 } });
  await app.context.triggerScoutCycle();
  assert.match(app.element('toast-text').textContent, /3 qualified prospects/);
  assert.equal(app.element('btn-run-scout').disabled, false);
});

test('scout reports an empty result truthfully', async () => {
  const app = dashboard({ status: 200, body: { status: 'success', discovered_count: 0 } });
  await app.context.triggerScoutCycle();
  assert.match(app.element('toast-text').textContent, /No qualified prospects/);
});

test('scout displays server failures and restores the button', async () => {
  const app = dashboard({ status: 500, body: { status: 'error', message: 'Research failed' } });
  await app.context.triggerScoutCycle();
  assert.equal(app.element('toast-text').textContent, 'Research failed');
  assert.equal(app.element('btn-run-scout').disabled, false);
  assert.ok(!app.element('stream-terminal').children.some(child => /Successfully synchronized/.test(child.innerHTML)));
});
