// Test the published CLI against disposable Git tags and project-local installs.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { access, mkdtemp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const cli = join(root, 'node_modules/skills/bin/cli.mjs');
const temporary = await mkdtemp(join(tmpdir(), 'agent-harness-cli-'));
const source = join(temporary, 'source.git');
const project = join(temporary, 'project');
const skill = 'harness-cli-fixture';
const sourceUrl = 'https://fixture.invalid/harness/skills.git';
// Exercise the normal HTTPS/ref parser while keeping all Git traffic local.
const environment = {
  ...process.env, DISABLE_TELEMETRY: '1', DO_NOT_TRACK: '1', CI: 'true',
  GIT_CONFIG_COUNT: '1',
  GIT_CONFIG_KEY_0: `url.${pathToFileURL(source).href}.insteadOf`,
  GIT_CONFIG_VALUE_0: sourceUrl,
};

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, env: environment, encoding: 'utf8', timeout: 60000 });
  assert.equal(result.status, 0, `${command} ${args.join(' ')}\n${result.error ?? ''}\n${result.stdout}\n${result.stderr}`);
  return result.stdout;
}

async function writeSkill(version) {
  await writeFile(join(source, 'skills', skill, 'SKILL.md'),
    `---\nname: ${skill}\ndescription: "Used only for a disposable installation test."\n---\n# Fixture\nReport fixture version ${version}.\n`);
}

async function installedVersion(version) {
  const installed = join(project, '.agents', 'skills', skill);
  assert.match(await readFile(join(installed, 'SKILL.md'), 'utf8'), new RegExp(`fixture version ${version}\\.`));
  assert.deepEqual((await readdir(installed)).sort(), ['SKILL.md', 'scripts']);
  assert.equal(await readFile(join(installed, 'scripts/helper.txt'), 'utf8'), 'runtime-resource\n');
  const lock = JSON.parse(await readFile(join(project, 'skills-lock.json'), 'utf8'));
  assert.equal(lock.skills[skill].ref, `v0.${version}.0`);
  assert.equal(lock.skills[skill].skillPath, `skills/${skill}/SKILL.md`);
}

async function skillFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      files.push(...(await skillFiles(join(directory, entry.name)))
        .map(file => join(entry.name, file)));
    } else {
      files.push(entry.name);
    }
  }
  return files.sort();
}

try {
  await mkdir(join(source, 'skills', skill, 'scripts'), { recursive: true });
  await mkdir(join(source, 'registry'));
  await mkdir(join(source, 'reviews'));
  await mkdir(project);
  await writeFile(join(source, 'registry/skills.json'), '{"maintenance-only":true}\n');
  await writeFile(join(source, 'reviews/decision.md'), 'maintenance-only\n');
  await writeFile(join(source, 'AGENTS.md'), 'Harness maintenance instructions only.\n');
  await writeFile(join(source, 'skills', skill, 'scripts/helper.txt'), 'runtime-resource\n');
  await writeSkill(1);
  run('git', ['init', '-b', 'main'], source);
  run('git', ['add', '.'], source);
  const commit = ['-c', 'user.name=Harness fixture', '-c', 'user.email=fixture@example.invalid', 'commit'];
  run('git', [...commit, '-m', 'Fixture version one'], source);
  run('git', ['tag', 'v0.1.0'], source);
  await writeSkill(2);
  run('git', ['add', '.'], source);
  run('git', [...commit, '-m', 'Fixture version two'], source);
  run('git', ['tag', 'v0.2.0'], source);

  const options = ['--skill', skill, '--agent', 'codex', '--copy', '--yes'];
  run(process.execPath, [cli, 'add', `${sourceUrl}#v0.1.0`, ...options], project);
  await installedVersion(1);
  run(process.execPath, [cli, 'update', skill, '--project', '--yes'], project);
  await installedVersion(1);
  run(process.execPath, [cli, 'add', `${sourceUrl}#v0.2.0`, ...options], project);
  await installedVersion(2);
  const projectFiles = await readdir(project);
  for (const excluded of ['registry', 'reviews', 'AGENTS.md']) {
    assert.ok(!projectFiles.includes(excluded), `${excluded} leaked into the project`);
  }
  console.log('OK: tagged install, pinned update, explicit upgrade, resources, and maintenance exclusion');

  const index = JSON.parse(await readFile(join(root, 'registry/skills.json'), 'utf8'));
  const owned = Object.keys(index.skills);
  if (owned.length) {
    const ownedProject = join(temporary, 'owned-project');
    await mkdir(ownedProject);
    run(process.execPath, [cli, 'add', root, '--skill', '*', '--agent', 'codex', '--copy', '--yes'], ownedProject);
    const installedRoot = join(ownedProject, '.agents/skills');
    assert.deepEqual((await readdir(installedRoot)).sort(), owned.sort());
    for (const name of owned) {
      const runtime = join(root, 'skills', name);
      const installed = join(installedRoot, name);
      const files = await skillFiles(runtime);
      assert.deepEqual(await skillFiles(installed), files, `${name} includes every runtime resource`);
      for (const file of files) {
        assert.deepEqual(await readFile(join(installed, file)),
          await readFile(join(runtime, file)), `${name}/${file} installs unchanged`);
      }
      for (const reserved of ['provenance.json', 'registry', 'reviews']) {
        assert.ok(!(await readdir(join(installedRoot, name))).includes(reserved));
      }
    }
    for (const name of ['harness', 'unslop', 'technical-writing', 'deslop', 'no-comments', 'interrogate', 'show-me-your-work', 'figure-it-out', 'benchmark-checklist', 'how', 'why', 'architect', 'arena', 'swarm', 'control-ui', 'control-cli', 'principle-laziness-protocol', 'principle-foundational-thinking', 'principle-redesign-from-first-principles', 'principle-attack-the-premise', 'principle-subtract-before-you-add', 'principle-minimize-reader-load', 'principle-outcome-oriented-execution', 'principle-experience-first', 'principle-exhaust-the-design-space', 'principle-build-the-lever', 'principle-model-the-domain', 'principle-boundary-discipline', 'principle-type-system-discipline', 'principle-make-operations-idempotent', 'principle-migrate-callers-then-delete-legacy-apis', 'principle-separate-before-serializing-shared-state', 'principle-prove-it-works', 'principle-fix-root-causes', 'principle-sequence-verifiable-units', 'principle-test-behavior-not-implementation', 'principle-explain-the-number', 'principle-guard-the-context-window', 'principle-never-block-on-the-human', 'principle-encode-lessons-in-structure']) {
      const expected = name === 'harness'
        ? /allow_implicit_invocation: false/
        : /allow_implicit_invocation: true/;
      assert.match(await readFile(join(installedRoot, name, 'agents/openai.yaml'), 'utf8'),
        expected, `${name} has the intended Codex invocation policy`);
    }
    const standaloneProject = join(temporary, 'standalone-project');
    await mkdir(standaloneProject);
    run(process.execPath, [cli, 'add', root, '--skill', 'harness', '--agent', 'codex', '--copy', '--yes'], standaloneProject);
    const standaloneRoot = join(standaloneProject, '.agents/skills');
    assert.deepEqual(await readdir(standaloneRoot), ['harness']);
    const mode = join(standaloneRoot, 'harness');
    assert.equal(await readFile(join(mode, 'SKILL.md'), 'utf8'),
      await readFile(join(root, 'skills/harness/SKILL.md'), 'utf8'));
    assert.match(await readFile(join(mode, 'agents/openai.yaml'), 'utf8'),
      /allow_implicit_invocation: false/);
    const modeFiles = (await skillFiles(mode))
      .filter(name => name.endsWith('.md'))
      .map(name => join(mode, name));
    for (const file of modeFiles) {
      const content = await readFile(file, 'utf8');
      for (const match of content.matchAll(/\(`([^`]+\.md)`\)|\]\(([^)]+\.md)\)/g)) {
        const target = resolve(dirname(file), match[1] ?? match[2]);
        assert.ok(target.startsWith(`${mode}${sep}`), `${file} refers outside the Harness package`);
        await access(target);
      }
    }
    const laneRoot = join(temporary, 'installed-lanes');
    await mkdir(laneRoot);
    const sourceHead = run('git', ['rev-parse', 'HEAD'], source).trim();
    const laneProcess = spawnSync('python3', [join(mode, 'scripts/run_lane.py'),
      '--checkout', source, '--head', sourceHead, '--temp-root', laneRoot,
      '--deadline', '15', '--', 'python', '-c', 'import sys; print(sys.prefix)'],
    { cwd: standaloneProject, env: environment, encoding: 'utf8', timeout: 30000 });
    const laneResult = JSON.parse(laneProcess.stdout);
    const laneReceipt = JSON.parse(await readFile(laneResult.receipt, 'utf8'));
    if (process.platform === 'linux') {
      assert.equal(laneProcess.status, 0, `${laneProcess.stdout}\n${laneProcess.stderr}`);
      assert.equal(laneResult.outcome, 'passed');
      assert.equal(laneResult.cleanup, 'complete');
      assert.equal(laneReceipt.source.source_after, sourceHead);
      assert.equal((await readFile(join(laneReceipt.run_directory, 'execution.stdout'), 'utf8')).trim(),
        laneReceipt.environment_paths.VIRTUAL_ENV);
      assert.equal(laneReceipt.command[0], join(laneReceipt.environment_paths.VIRTUAL_ENV, 'bin/python'));
    } else {
      assert.notEqual(laneProcess.status, 0);
      assert.equal(laneResult.outcome, 'unsupported');
      assert.equal(laneResult.cleanup, 'not_started');
    }

    const store = join(temporary, 'installed-orchestration-store');
    const helper = join(mode, 'scripts/orch.py');
    run('python3', [helper, '--store', store, 'init'], standaloneProject);
    const inbox = JSON.parse(run('python3', [helper, '--store', store, 'inbox', 'drain', '--json'], standaloneProject));
    assert.deepEqual(inbox, { batch: null, pointers: [] });
    run('python3', [helper, '--store', store, 'unit', 'add', 'installed-recovery', '--track', 'build'], standaloneProject);
    const queueInput = join(temporary, 'queue-checkpoint-input.json');
    await writeFile(queueInput, JSON.stringify({ schema_version: 1, program: 'installed-recovery',
      repository: { name: 'fixture/repo', path: standaloneProject }, authorization: 'Run the disposable fixture.',
      units: [{ id: 'installed-recovery', owner_id: 'fixture-owner', work_scope: ['fixture-checkout'],
        brief: 'Continue the disposable fixture.', findings: ['Retain the original report.'], evidence: [],
        next_actions: [{ id: 'verify', kind: 'local', status: 'planned', receipt: null }] }] }));
    const queueCheckpoint = JSON.parse(run('python3', [helper, '--store', store, 'checkpoint',
      '--input', queueInput, '--json'], standaloneProject));
    assert.equal(queueCheckpoint.units[0].owner_id, 'fixture-owner');
    const hostState = join(temporary, 'queue-host-state.json');
    await writeFile(hostState, JSON.stringify({ schema_version: 1, observed_at: new Date().toISOString(),
      owners: [{ id: 'fixture-owner', state: 'stopped', writer_stopped: true }] }));
    const storeBefore = await Promise.all((await skillFiles(store)).map(async file =>
      [file, await readFile(join(store, file))]));
    const pickupArgs = [helper, '--store', store, 'pickup', '--host-state', hostState, '--json'];
    const recovered = JSON.parse(run('python3', pickupArgs, standaloneProject));
    assert.equal(recovered.units[0].same_scope_replacement_allowed, true);
    assert.equal(recovered.units[0].replacement_packet.authorization, 'Run the disposable fixture.');
    assert.deepEqual(JSON.parse(run('python3', pickupArgs, standaloneProject)), recovered);
    const unavailableHost = JSON.parse(run('python3', [helper, '--store', store, 'pickup', '--json'], standaloneProject));
    assert.equal(unavailableHost.units[0].owner_classification, 'unknown');
    assert.equal(unavailableHost.units[0].same_scope_replacement_allowed, false);
    assert.deepEqual(await skillFiles(store), storeBefore.map(([file]) => file));
    for (const [file, content] of storeBefore) assert.deepEqual(await readFile(join(store, file)), content);
    const checkpoint = join(temporary, 'audit-checkpoint.json');
    await writeFile(checkpoint, JSON.stringify({ schema_version: 1, program: 'installed-fixture', repo: standaloneProject,
      authorization: 'Run the disposable local fixture.', resume: 'Read the saved queue and gates.',
      units: [], owners: [], published_heads: [], findings: [], evidence: [], next_actions: [], unresolved_gates: [] }));
    const registrationHelper = join(mode, 'scripts/audit.py');
    const unsupported = JSON.parse(run('python3', [registrationHelper, '--store', store,
      'ensure', '--checkpoint', checkpoint], standaloneProject));
    assert.equal(unsupported.registration_status, 'unavailable');
    assert.equal(unsupported.checkpoint.metadata.authorization, 'Run the disposable local fixture.');
    const registration = JSON.parse(run('python3', [registrationHelper, '--store', store, 'status'], standaloneProject));
    assert.equal(registration.registration_id, null);
    await access(join(mode, 'references/audit-registration.md'));
    const audit = JSON.parse(run('python3', [join(mode, 'scripts/worktree-audit.py'), '--repo', source, '--base', 'main'], standaloneProject));
    assert.equal(audit.worktrees.length, 1);
    assert.ok(audit.worktrees[0].reasons.includes('primary-worktree'));
    const emptyPlan = join(temporary, 'empty-plan.md');
    await writeFile(emptyPlan, '');
    const planResult = spawnSync(process.execPath, [join(mode, 'scripts/check-plan.mjs'), emptyPlan],
      { cwd: standaloneProject, env: environment, encoding: 'utf8', timeout: 60000 });
    assert.equal(planResult.status, 1, planResult.stderr);
    assert.match(planResult.stderr, /no H1 title/, `${planResult.stdout}\n${planResult.stderr}\n${planResult.error ?? ''}`);

    for (const excluded of ['registry', 'reviews', 'AGENTS.md']) {
      assert.ok(!(await readdir(ownedProject)).includes(excluded));
    }
    console.log(`OK: ${owned.length} owned skill(s) install without maintenance records; standalone Harness includes its playbooks and policy without installing routed skills`);
  }
} finally {
  await rm(temporary, { recursive: true, force: true });
}
