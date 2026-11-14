const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');

function loadProductionController() {
  const startMarker = '  // PD-ELU-GIT-ARCH-01 A1 controller begin';
  const endMarker = '  // PD-ELU-GIT-ARCH-01 A1 controller end';
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, 'production A1 controller must be present in app.js');
  const block = source.slice(start + startMarker.length, end);
  assert.match(block, /function createGitIndexCommitUiController\s*\(/);
  const context = {};
  vm.runInNewContext(`${block}\nglobalThis.factory = createGitIndexCommitUiController;`, context, {
    filename: 'ui/app.js#git-index-commit-controller',
  });
  const mountStart = source.indexOf('  function mountGitIndexCommitUi(options) {', start);
  assert.ok(mountStart > start, 'production A1 DOM mounting function must be present');
  vm.runInNewContext(`${source.slice(mountStart, source.indexOf('  // PD-ELU-GIT-ARCH-01 A1 controller end', mountStart))}\nglobalThis.mount = mountGitIndexCommitUi;`, context, {
    filename: 'ui/app.js#git-index-commit-mount',
  });
  return { factory: context.factory, mount: context.mount };
}

function createHarness(replies) {
  const calls = [];
  const statuses = [];
  let currentRoot = 'C:\\repo\\project';
  let refreshes = 0;
  const { factory } = loadProductionController();
  const controller = factory({
    getProjectRoot: () => currentRoot,
    invoke: async (command, args) => {
      calls.push({ command, args });
      const next = replies.shift();
      if (next instanceof Error) throw next;
      return next;
    },
    onStatus: (status) => statuses.push(status),
    onRefresh: async () => { refreshes += 1; },
  });
  return {
    controller,
    calls,
    statuses,
    setRoot: (root) => { currentRoot = root; },
    refreshCount: () => refreshes,
  };
}

class FakeElement {
  constructor(tag) { this.tagName = tag; this.children = []; this.listeners = {}; this.attributes = {}; this.textContent = ''; this.value = ''; this.disabled = false; this.checked = false; }
  setAttribute(name, value) { this.attributes[name] = value; }
  appendChild(node) { this.children.push(node); return node; }
  append(...nodes) { nodes.forEach((node) => this.appendChild(node)); }
  replaceChildren(...nodes) { this.children = [...nodes]; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  async fire(name, event = {}) { if (this.listeners[name]) await this.listeners[name]({ target: this, ...event }); }
}

function createFakeDocument() {
  const nodes = [];
  return {
    nodes,
    createElement(tag) { const node = new FakeElement(tag); nodes.push(node); return node; },
    createTextNode(text) { const node = new FakeElement('#text'); node.textContent = text; return node; },
    byId(id) { return nodes.find((node) => node.id === id); },
  };
}

const preview = (id, generation, paths = ['app/src/main.rs']) => ({
  preview_id: id,
  generation,
  fingerprint: {
    repo_root: 'C:\\repo',
    project_root: 'C:\\repo\\project',
    head_oid: 'a'.repeat(40),
    index_tree_oid: 'b'.repeat(40),
    staged_paths: paths,
  },
  display_paths: paths,
  message_required: true,
});

test('preview shows the read-only staged snapshot and explicit confirmation is bound to its generation', async () => {
  const h = createHarness([
    preview('token-1', 1),
    {
      preview_id: 'token-1', state: 'Committed',
      before: { head_oid: 'a'.repeat(40) }, after: { head_oid: 'c'.repeat(40) },
      created_commit_oid: 'c'.repeat(40), retry_requires_new_preview: true,
    },
  ]);
  await h.controller.preview();
  let view = h.controller.getView();
  assert.equal(view.preview.preview_id, 'token-1');
  assert.equal(view.preview.generation, 1);
  assert.equal(view.preview.head_oid, 'a'.repeat(40));
  assert.equal(view.preview.index_tree_oid, 'b'.repeat(40));
  assert.deepEqual(Array.from(view.preview.paths), ['app/src/main.rs']);
  assert.equal(view.confirmed, false);
  assert.equal(view.canConfirm, false);

  h.controller.setMessage('commit staged file');
  h.controller.setConfirmed(true, 1);
  assert.equal(h.controller.getView().canConfirm, true);
  await h.controller.confirm();
  assert.deepEqual(h.calls.map((call) => call.command), [
    'git_index_commit_preview', 'git_index_commit_confirm',
  ]);
  assert.equal(h.calls[0].args.repo, 'C:\\repo\\project');
  assert.equal(h.calls[1].args.request.preview_id, 'token-1');
  assert.equal(h.calls[1].args.request.generation, 1);
  assert.equal(h.calls[1].args.request.confirmed, true);
  assert.equal(h.calls[1].args.request.message, 'commit staged file');
  assert.equal(h.controller.getView().preview, null);
  assert.equal(h.controller.getView().message, 'commit staged file');
  assert.equal(h.refreshCount(), 1);
});

test('repreview and project-root changes clear the old generation and confirmation', async () => {
  const h = createHarness([preview('token-1', 1), preview('token-2', 2), preview('token-3', 3)]);
  await h.controller.preview();
  h.controller.setMessage('keep draft');
  h.controller.setConfirmed(true, 1);
  await h.controller.preview();
  assert.equal(h.controller.getView().preview.preview_id, 'token-2');
  assert.equal(h.controller.getView().confirmed, false);
  assert.equal(h.controller.getView().message, 'keep draft');
  await h.controller.confirm();
  assert.equal(h.calls.length, 2, 'old checkbox state cannot authorize a re-previewed token');

  h.setRoot('C:\\repo-two\\project');
  h.controller.syncProjectRoot('C:\\repo-two\\project');
  assert.equal(h.controller.getView().preview, null);
  assert.equal(h.controller.getView().confirmed, false);
  await h.controller.confirm();
  assert.equal(h.calls.length, 2, 'root change invalidates the old preview before any invoke');
});

test('an explicit unbound toolbar projection invalidates the preview and disables confirmation', async () => {
  const h = createHarness([preview('token-1', 1)]);
  await h.controller.preview();
  h.controller.setMessage('message');
  h.controller.setConfirmed(true, 1);
  assert.equal(h.controller.getView().canConfirm, true);
  h.controller.syncProjectRoot('');
  assert.equal(h.controller.getView().root, '', 'the empty toolbar projection remains authoritative');
  assert.equal(h.controller.getView().preview, null);
  assert.equal(h.controller.getView().confirmed, false);
  await h.controller.confirm();
  assert.equal(h.calls.length, 1, 'unbinding cannot reuse the former project preview');
  assert.equal(h.controller.getView().canPreview, false);
  await h.controller.preview();
  assert.equal(h.calls.length, 1, 'unbinding cannot silently rehydrate the stale root for a new preview');
});

test('typed pre-invocation errors retain the message and preview while showing the server diagnostic', async () => {
  const typed = Object.assign(new Error('index is busy'), {
    code: 'Busy', diagnostic: 'another A1 commit is active',
    mutation_started: false, requires_new_preview: false,
  });
  const h = createHarness([preview('token-1', 1), typed]);
  await h.controller.preview();
  h.controller.setMessage('retain this');
  h.controller.setConfirmed(true, 1);
  await h.controller.confirm();
  const view = h.controller.getView();
  assert.equal(view.message, 'retain this');
  assert.equal(view.preview.preview_id, 'token-1');
  assert.equal(view.confirmed, true);
  assert.match(view.status, /Busy.*another A1 commit is active/);
  assert.equal(h.calls.length, 2);
});

test('backend canonical project-root spelling does not disable the request-bound preview generation', async () => {
  const dto = preview('token-canonical', 12);
  dto.fingerprint.project_root = '\\\\?\\C:\\repo\\project';
  const h = createHarness([dto]);
  await h.controller.preview();
  h.controller.setMessage('canonical path');
  h.controller.setConfirmed(true, 12);
  assert.equal(h.controller.getView().canConfirm, true);
});

test('attempted and unknown outcomes require a fresh preview without erasing the message', async () => {
  const h = createHarness([preview('token-1', 1), {
    preview_id: 'token-1', state: 'OutcomeUnknown', diagnostic: 'postcondition read failed',
    retry_requires_new_preview: true,
  }]);
  await h.controller.preview();
  h.controller.setMessage('keep after uncertainty');
  h.controller.setConfirmed(true, 1);
  await h.controller.confirm();
  assert.equal(h.controller.getView().preview, null);
  assert.equal(h.controller.getView().confirmed, false);
  assert.equal(h.controller.getView().message, 'keep after uncertainty');
  assert.match(h.controller.getView().status, /OutcomeUnknown.*postcondition read failed/);
  await h.controller.confirm();
  assert.equal(h.calls.length, 2, 'the consumed token cannot be resent');
});

test('missing root, blank message, and mismatched generation never reach a Git command', async () => {
  const h = createHarness([preview('token-1', 4)]);
  h.setRoot('');
  h.controller.syncProjectRoot('');
  await h.controller.preview();
  assert.equal(h.calls.length, 0);
  h.setRoot('C:\\repo\\project');
  h.controller.syncProjectRoot('C:\\repo\\project');
  await h.controller.preview();
  h.controller.setConfirmed(true, 3);
  h.controller.setMessage('');
  await h.controller.confirm();
  assert.equal(h.calls.length, 1, 'only the preview was invoked');
});

test('mounted production controls bind preview, message and generation checkbox to the A1 commands', async () => {
  const { mount } = loadProductionController();
  const document = createFakeDocument();
  const parent = new FakeElement('section');
  const calls = [];
  const controller = mount({
    document,
    parent,
    getProjectRoot: () => 'C:\\repo\\project',
    invoke: async (command, args) => {
      calls.push({ command, args });
      if (command === 'git_index_commit_preview') return preview('token-ui', 8);
      return { preview_id: 'token-ui', state: 'OutcomeUnknown', retry_requires_new_preview: true, diagnostic: 'postcondition not observed' };
    },
    onRefresh: async () => {},
  });
  const previewButton = document.byId('git-index-commit-preview');
  const message = document.byId('git-index-commit-message');
  const checkbox = document.byId('git-index-commit-confirmed');
  const confirmButton = document.byId('git-index-commit-submit');
  await previewButton.fire('click');
  assert.equal(calls[0].command, 'git_index_commit_preview');
  assert.equal(document.byId('git-index-commit-head').textContent, 'a'.repeat(40));
  assert.equal(document.byId('git-index-commit-paths').children[0].textContent, 'app/src/main.rs');
  assert.match(document.byId('git-index-commit-title').textContent, /Index/);
  assert.match(document.nodes.find((node) => node.tagName === 'span' && node.textContent.includes('第 '))?.textContent || '', /第 8 代/);
  message.value = 'UI commit message';
  await message.fire('input');
  checkbox.checked = true;
  await checkbox.fire('change');
  assert.equal(confirmButton.disabled, false);
  await confirmButton.fire('click');
  assert.deepEqual(calls.map((call) => call.command), ['git_index_commit_preview', 'git_index_commit_confirm']);
  assert.equal(calls[1].args.request.message, 'UI commit message');
  assert.equal(calls[1].args.request.generation, 8);
  assert.match(document.byId('git-index-commit-status').textContent, /OutcomeUnknown/);
  assert.equal(message.value, 'UI commit message');
  assert.equal(controller.getView().preview, null);
  assert.equal(confirmButton.disabled, true);
});

test('the application boot path mounts the tested controls only with Tauri IPC and never uses legacy write commands', () => {
  assert.match(source, /function wireGitIndexCommitUi\(\) \{[\s\S]*?mountGitIndexCommitUi\(/);
  assert.match(source, /gitIndexCommitRootSync\(display\)/);
  assert.match(source, /renderBoard\(null\);\s*wireGitIndexCommitUi\(\);/);
  assert.match(source, /function isGitUxMockMode\(\) \{\s*return !!\([\s\S]*?!invoke/);
  const a1Block = source.slice(source.indexOf('  // PD-ELU-GIT-ARCH-01 A1 controller begin'), source.indexOf('  // PD-ELU-GIT-ARCH-01 A1 controller end'));
  assert.doesNotMatch(a1Block, /git_write_commit|git_write_push|git_index_commit_push/);
  assert.match(a1Block, /git_index_commit_preview/);
  assert.match(a1Block, /git_index_commit_confirm/);
});
