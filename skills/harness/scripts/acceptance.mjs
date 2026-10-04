import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { isDeepStrictEqual } from "node:util";

const hash = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const nonempty = (value) => typeof value === "string" && Boolean(value.trim());
const ids = (values) => values.map((value) => value.id);
const within = (root, target) => target === root || target.startsWith(root + path.sep);
const same = isDeepStrictEqual;
const requireInput = (condition, message) => { if (!condition) throw new Error(message); };

function parseJSON(raw) {
	const value = JSON.parse(raw);
	const tokens = raw.toString().match(/"(?:\\.|[^"\\])*"|[{}\[\]:,]|[^{}\[\]:,\s]+/g);
	let cursor = 0;
	function scan() {
		const token = tokens[cursor++];
		if (token === "{") {
			const keys = new Set();
			while (tokens[cursor] !== "}") {
				const key = JSON.parse(tokens[cursor++]);
				requireInput(!keys.has(key), `duplicate JSON key ${key}`);
				keys.add(key);
				cursor++;
				scan();
				if (tokens[cursor] === ",") cursor++;
			}
			cursor++;
		} else if (token === "[") {
			while (tokens[cursor] !== "]") {
				scan();
				if (tokens[cursor] === ",") cursor++;
			}
			cursor++;
		}
	}
	scan();
	return value;
}

function fields(value, allowed, label) {
	requireInput(object(value), `${label} must be an object`);
	for (const key of Object.keys(value)) requireInput(allowed.includes(key), `${label} has unknown field ${key}`);
}

function strings(value, label, empty = false) {
	requireInput(Array.isArray(value) && (empty || value.length > 0) && value.every(nonempty), `${label} must be a string array`);
}

function command(value, label) {
	requireInput(Array.isArray(value) && nonempty(value[0]) && value.every((argument) => typeof argument === "string"), `${label} needs an executable and string arguments`);
}

function records(value, label, empty = false) {
	requireInput(Array.isArray(value) && (empty || value.length > 0), `${label} must be an array`);
	for (const record of value) requireInput(object(record) && nonempty(record.id) && /^[a-z0-9][a-z0-9-]*$/.test(record.id), `${label} needs valid IDs`);
	requireInput(new Set(ids(value)).size === value.length, `${label} has duplicate IDs`);
}

function references(values, targets, label) {
	strings(values, label);
	requireInput(new Set(values).size === values.length, `${label} has duplicate references`);
	for (const id of values) requireInput(targets.includes(id), `${label} references missing ${id}`);
}

function validate(manifest) {
	fields(manifest, ["version", "repoRoot", "outcomes", "scenarios", "gates", "findings", "projectRules"], "manifest");
	requireInput(manifest.version === 1 && nonempty(manifest.repoRoot), "manifest needs version 1 and explicit repoRoot");
	for (const name of ["outcomes", "scenarios", "gates", "findings"]) records(manifest[name], name, name === "findings" || name === "gates");
	const scenarioIds = ids(manifest.scenarios);
	const gateIds = ids(manifest.gates);
	for (const outcome of manifest.outcomes) {
		fields(outcome, ["id", "description", "scenarioIds"], outcome.id);
		requireInput(nonempty(outcome.description), `${outcome.id} needs a description`);
		references(outcome.scenarioIds, scenarioIds, outcome.id);
	}
	for (const scenario of manifest.scenarios) {
		fields(scenario, ["id", "setup", "pass", "verification"], scenario.id);
		requireInput(nonempty(scenario.setup) && nonempty(scenario.pass), `${scenario.id} needs setup and pass predicate`);
		fields(scenario.verification, ["gateIds", "nonapplicable"], `${scenario.id} verification`);
		const verification = scenario.verification;
		requireInput(Object.keys(verification).length === 1, `${scenario.id} needs gates or nonapplicability`);
		if (verification.gateIds) references(verification.gateIds, gateIds, scenario.id);
		else requireInput(nonempty(verification.nonapplicable) && verification.nonapplicable.trim().split(/\s+/).length >= 4
			&& !/\b(?:unavailable|missing|unfinished|inconclusive|not installed|not available)\b/i.test(verification.nonapplicable), `${scenario.id} needs substantive nonapplicability, never a missing-tool or unfinished-check excuse`);
	}
	for (const gate of manifest.gates) {
		fields(gate, ["id", "argv", "cwd", "timeoutMs", "predicate", "artifacts", "environment", "measurement"], gate.id);
		command(gate.argv, `${gate.id} argv`);
		requireInput(Number.isSafeInteger(gate.timeoutMs) && gate.timeoutMs > 0 && gate.timeoutMs <= 3_600_000, `${gate.id} timeoutMs must be 1 to 3600000`);
		requireInput(gate.cwd === undefined || nonempty(gate.cwd), `${gate.id} cwd must be a path`);
		fields(gate.predicate, ["exitCode", "jsonEquals"], `${gate.id} predicate`);
		requireInput(gate.predicate.exitCode === 0, `${gate.id} predicate requires exitCode 0`);
		requireInput(gate.predicate.jsonEquals === undefined || object(gate.predicate.jsonEquals), `${gate.id} jsonEquals must be an object`);
		strings(gate.artifacts, `${gate.id} artifacts`, true);
		requireInput(new Set(gate.artifacts).size === gate.artifacts.length, `${gate.id} has duplicate artifact paths`);
		requireInput(gate.measurement === undefined || typeof gate.measurement === "boolean", `${gate.id} measurement must be boolean`);
		if (gate.environment !== undefined) {
			fields(gate.environment, ["probeArgv", "required"], `${gate.id} environment`);
			command(gate.environment.probeArgv, `${gate.id} probeArgv`);
			requireInput(object(gate.environment.required) && Object.keys(gate.environment.required).length > 0, `${gate.id} needs required environment properties`);
		}
		requireInput(!gate.measurement || gate.environment, `${gate.id} measurement needs an environment probe`);
	}
	for (const finding of manifest.findings) {
		fields(finding, ["id", "class", "premise", "failedAttempts", "focusedScenarioId", "affectedScenarioIds", "coverageReason", "investigations"], finding.id);
		for (const name of ["class", "premise", "coverageReason"]) requireInput(nonempty(finding[name]), `${finding.id} needs ${name}`);
		references([finding.focusedScenarioId], scenarioIds, finding.id);
		references(finding.affectedScenarioIds, scenarioIds, finding.id);
		for (const id of [finding.focusedScenarioId, ...finding.affectedScenarioIds]) {
			requireInput(manifest.scenarios.find((scenario) => scenario.id === id).verification.gateIds, `${finding.id} needs executable focused and affected checks`);
		}
		requireInput(Array.isArray(finding.failedAttempts) && finding.failedAttempts.length > 0, `${finding.id} needs historical repro evidence`);
		for (const attempt of finding.failedAttempts) {
			fields(attempt, ["head", "premise", "gateId", "reproRunId"], `${finding.id} attempt`);
			requireInput(/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(attempt.head) && nonempty(attempt.premise), `${finding.id} attempt needs head and premise`);
			references([attempt.gateId], gateIds, finding.id);
			requireInput(/^[0-9a-f-]+$/.test(attempt.reproRunId), `${finding.id} attempt needs reproRunId`);
		}
		requireInput(Array.isArray(finding.investigations), `${finding.id} needs investigations array`);
		for (const investigation of finding.investigations) {
			fields(investigation, ["premise", "gateId", "evidenceScenarioIds", "conclusion"], `${finding.id} investigation`);
			requireInput(nonempty(investigation.premise) && nonempty(investigation.conclusion), `${finding.id} investigation needs premise and conclusion`);
			references([investigation.gateId], gateIds, finding.id);
			references(investigation.evidenceScenarioIds, scenarioIds, finding.id);
			for (const id of investigation.evidenceScenarioIds) requireInput(manifest.scenarios.find((scenario) => scenario.id === id).verification.gateIds, `${finding.id} investigation needs executable evidence`);
		}
	}
	if (manifest.projectRules !== undefined) {
		fields(manifest.projectRules, ["changedFileLimit", "canonicalSource"], "projectRules");
		const limit = manifest.projectRules.changedFileLimit;
		if (limit !== undefined) {
			fields(limit, ["base", "maximum"], "changedFileLimit");
			requireInput(nonempty(limit.base) && Number.isSafeInteger(limit.maximum) && limit.maximum >= 0, "changedFileLimit needs base and nonnegative maximum");
		}
		const canonical = manifest.projectRules.canonicalSource;
		if (canonical !== undefined) {
			fields(canonical, ["gateIds", "properties"], "canonicalSource");
			references(canonical.gateIds, gateIds, "canonicalSource");
			requireInput(object(canonical.properties) && Object.keys(canonical.properties).length > 0, "canonicalSource needs properties");
			for (const id of canonical.gateIds) {
				const gate = manifest.gates.find((gate) => gate.id === id);
				requireInput(gate.measurement && gate.environment, `${id} canonical source needs a measurement environment probe`);
				for (const [key, value] of Object.entries(canonical.properties)) {
					requireInput(!Object.hasOwn(gate.environment.required, key) || same(value, gate.environment.required[key]), `${id} canonical source contradicts environment requirement ${key}`);
				}
			}
		}
	}
}

function git(root, args, trim = true) {
	const result = spawnSync("git", ["-C", root, ...args], { encoding: "utf8", timeout: 30_000, maxBuffer: 8 * 1024 * 1024 });
	if (result.error || result.status !== 0) throw new Error(`Git failed for ${args[0]}: ${result.error?.message || result.stderr.trim()}`);
	return trim ? result.stdout.trimEnd() : result.stdout;
}

function realTarget(target) {
	if (fs.existsSync(target)) return fs.realpathSync(target);
	return path.join(realTarget(path.dirname(target)), path.basename(target));
}

function context(file, storeOption) {
	const manifestPath = fs.realpathSync(file);
	const rawManifest = fs.readFileSync(manifestPath, "utf8");
	const manifest = parseJSON(rawManifest);
	validate(manifest);
	const root = fs.realpathSync(path.resolve(path.dirname(manifestPath), manifest.repoRoot));
	requireInput(fs.realpathSync(git(root, ["rev-parse", "--show-toplevel"])) === root, "repoRoot must be the actual repository root");
	requireInput(within(root, manifestPath), "manifest must be inside repoRoot");
	const relativeManifest = path.relative(root, manifestPath).split(path.sep).join("/");
	git(root, ["ls-files", "--error-unmatch", "--", relativeManifest]);
	const gitDirectory = fs.realpathSync(git(root, ["rev-parse", "--absolute-git-dir"]));
	const baseStore = realTarget(storeOption ? path.resolve(storeOption) : path.join(gitDirectory, "harness-acceptance"));
	requireInput(!within(root, baseStore) || within(gitDirectory, baseStore), "receipt store must be outside the source tree or in Git metadata");
	const store = path.join(baseStore, hash(`${root}\0${relativeManifest}`));
	return { root, manifestPath, relativeManifest, rawManifest, manifest, manifestSha256: hash(rawManifest), store };
}

function atomicJSON(file, value) {
	const temp = `${file}.${crypto.randomUUID()}.tmp`;
	fs.writeFileSync(temp, JSON.stringify(value, null, "\t") + "\n", { flag: "wx" });
	fs.renameSync(temp, file);
}

function locked(ctx, action) {
	fs.mkdirSync(ctx.store, { recursive: true });
	const file = path.join(ctx.store, "owner.lock");
	const fd = fs.openSync(file, "wx");
	fs.writeFileSync(fd, String(process.pid) + "\n");
	try { return action(); }
	finally { fs.closeSync(fd); fs.unlinkSync(file); }
}

function currentHead(ctx) { return git(ctx.root, ["rev-parse", "HEAD"]); }

function clean(ctx, head) {
	if (currentHead(ctx) !== head) throw new Error("actual HEAD changed during execution");
	if (git(ctx.root, ["status", "--porcelain=v1", "--untracked-files=all"])) throw new Error("actual worktree is dirty");
	if (hash(fs.readFileSync(ctx.manifestPath)) !== ctx.manifestSha256) throw new Error("manifest changed during execution");
}

function preserve(previous, next) {
	for (const earlier of previous.findings) {
		const later = next.findings.find((finding) => finding.id === earlier.id);
		requireInput(later && later.class === earlier.class, `finding history removed or rewritten for ${earlier.id}`);
		for (const name of ["failedAttempts", "investigations"]) requireInput(same(earlier[name], later[name].slice(0, earlier[name].length)), `${earlier.id} ${name} history removed or rewritten`);
		for (const id of [earlier.focusedScenarioId, ...earlier.affectedScenarioIds]) requireInput([later.focusedScenarioId, ...later.affectedScenarioIds].includes(id), `${earlier.id} affected-case history removed for ${id}`);
	}
}

function declaration(ctx, id) {
	requireInput(/^[0-9a-f]{64}$/.test(id), "invalid declaration ID");
	const bytes = fs.readFileSync(path.join(ctx.store, "declarations", `${id}.json`));
	requireInput(hash(bytes) === id, "declaration hash mismatch");
	const value = parseJSON(bytes);
	requireInput(value.repoRoot === ctx.root && value.manifestPath === ctx.relativeManifest, "declaration belongs to another repository or manifest");
	requireInput(hash(value.rawManifest) === value.manifestSha256 && same(parseJSON(value.rawManifest), value.manifest), "declaration manifest hash mismatch");
	requireInput(git(ctx.root, ["show", `${value.head}:${value.manifestPath}`], false) === value.rawManifest, "declaration does not match its committed manifest");
	return value;
}

function activeDeclaration(ctx) {
	const { id } = parseJSON(fs.readFileSync(path.join(ctx.store, "declaration.json")));
	const seen = new Set();
	let current = declaration(ctx, id);
	const latest = current;
	while (current.previous) {
		requireInput(!seen.has(current.previous), "declaration history has a cycle");
		seen.add(current.previous);
		const previous = declaration(ctx, current.previous);
		preserve(previous.manifest, current.manifest);
		current = previous;
	}
	return { id, value: latest };
}

function baseCommit(ctx) {
	const rule = ctx.manifest.projectRules?.changedFileLimit;
	return rule ? git(ctx.root, ["rev-parse", "--verify", `${rule.base}^{commit}`]) : null;
}

function bindDeclaration(ctx, head) {
	const active = activeDeclaration(ctx);
	requireInput(active.value.manifestSha256 === ctx.manifestSha256, "manifest changed since declaration");
	git(ctx.root, ["merge-base", "--is-ancestor", active.value.head, head]);
	requireInput(active.value.baseCommit === baseCommit(ctx), "changed-file base drifted since declaration");
	return active;
}

function declare(ctx) {
	const head = currentHead(ctx);
	clean(ctx, head);
	requireInput(git(ctx.root, ["show", `${head}:${ctx.relativeManifest}`], false) === ctx.rawManifest, "declare needs the committed manifest bytes");
	let previous = null;
	if (fs.existsSync(path.join(ctx.store, "declaration.json"))) {
		const active = activeDeclaration(ctx);
		preserve(active.value.manifest, ctx.manifest);
		previous = active.id;
	}
	const value = { version: 1, repoRoot: ctx.root, manifestPath: ctx.relativeManifest, head,
		manifestSha256: ctx.manifestSha256, rawManifest: ctx.rawManifest, manifest: ctx.manifest,
		baseCommit: baseCommit(ctx), previous };
	const bytes = JSON.stringify(value, null, "\t") + "\n";
	const id = hash(bytes);
	fs.mkdirSync(path.join(ctx.store, "declarations"), { recursive: true });
	fs.writeFileSync(path.join(ctx.store, "declarations", `${id}.json`), bytes, { flag: "wx" });
	atomicJSON(path.join(ctx.store, "declaration.json"), { id });
	return { declared: true, head, declarationId: id, store: ctx.store };
}

function evidence(file) { return { path: file, sha256: hash(fs.readFileSync(file)) }; }

function verifyEvidence(item, source = false) {
	requireInput(object(item) && nonempty(item.path) && nonempty(item.sha256), "missing evidence metadata");
	requireInput(hash(fs.readFileSync(item.path)) === item.sha256, `evidence hash mismatch for ${item.path}`);
	if (source && item.sourcePath) requireInput(hash(fs.readFileSync(item.sourcePath)) === item.sha256, `artifact hash mismatch for ${item.sourcePath}`);
}

function observed(stdout, required, label) {
	const value = parseJSON(stdout);
	requireInput(object(value), `${label} must emit a JSON object`);
	for (const [key, expected] of Object.entries(required)) requireInput(same(value[key], expected), `${label} contradicts ${key}`);
	return value;
}

function execute(ctx, head, dir, label, argv, cwd, timeoutMs) {
	clean(ctx, head);
	const result = spawnSync(argv[0], argv.slice(1), { cwd, encoding: "utf8", timeout: timeoutMs,
		maxBuffer: 8 * 1024 * 1024, killSignal: "SIGKILL", env: { ...process.env, HARNESS_ACCEPTANCE_RUN_DIR: path.dirname(dir), HARNESS_ACCEPTANCE_REPO_ROOT: ctx.root } });
	const receipt = capture(dir, label, argv, cwd, timeoutMs, result);
	try { clean(ctx, head); } catch (error) { receipt.error = error.message; }
	return receipt;
}

function capture(dir, label, argv, cwd, timeoutMs, result) {
	const stdout = path.join(dir, `${label}-stdout.txt`);
	const stderr = path.join(dir, `${label}-stderr.txt`);
	fs.writeFileSync(stdout, result.stdout || "");
	fs.writeFileSync(stderr, result.stderr || "");
	return { argv, cwd, timeoutMs, exitCode: result.status, signal: result.signal || null,
		stdout: evidence(stdout), stderr: evidence(stderr), error: result.error?.message || null };
}

function commandProblem(receipt, label) {
	return receipt.error || receipt.exitCode !== 0 ? `${label} command failed: ${receipt.error || `exit ${receipt.exitCode}`}` : null;
}

function environmentRequired(gate, manifest) {
	const canonical = manifest.projectRules?.canonicalSource;
	return { ...gate.environment.required, ...(canonical?.gateIds.includes(gate.id) ? canonical.properties : {}) };
}

function gateProblems(gate, receipt, manifest) {
	const problems = [];
	const problem = commandProblem(receipt, gate.id);
	if (problem) problems.push(problem);
	if (!problem && gate.predicate.jsonEquals) {
		try { observed(fs.readFileSync(receipt.stdout.path, "utf8"), gate.predicate.jsonEquals, `${gate.id} predicate`); }
		catch (error) { problems.push(error.message); }
	}
	if (gate.environment) {
		const required = environmentRequired(gate, manifest);
		for (const phase of gate.measurement ? ["before", "after"] : ["before"]) {
			const probe = receipt.environment?.[phase];
			if (!probe) { problems.push(`${gate.id} missing ${phase} environment evidence`); continue; }
			const failed = commandProblem(probe, `${gate.id} ${phase} environment`);
			if (failed) { problems.push(failed); continue; }
			try {
				const value = observed(fs.readFileSync(probe.stdout.path, "utf8"), required, `${gate.id} ${phase} environment`);
				requireInput(same(value, probe.observed), `${gate.id} ${phase} observed environment mismatch`);
			} catch (error) { problems.push(`${gate.id} environment: ${error.message}`); }
		}
	}
	return problems;
}

function readRun(ctx, id, source = false) {
	requireInput(/^[0-9a-f-]+$/.test(id), "invalid run ID");
	const dir = path.join(ctx.store, "runs", id);
	const bytes = fs.readFileSync(path.join(dir, "receipt.json"));
	requireInput(hash(bytes) === fs.readFileSync(path.join(dir, "receipt.sha256"), "utf8").trim(), "run receipt hash mismatch");
	const run = parseJSON(bytes);
	requireInput(run.version === 1 && run.runId === id && run.repoRoot === ctx.root && run.manifestPath === ctx.relativeManifest, "run identity mismatch");
	const declared = declaration(ctx, run.declarationId);
	requireInput(run.manifestSha256 === declared.manifestSha256, "run manifest and declaration disagree");
	git(ctx.root, ["merge-base", "--is-ancestor", declared.head, run.head]);
	for (const gate of run.gates) {
		const configured = declared.manifest.gates.find((item) => item.id === gate.id);
		const replace = (value) => value.replaceAll("{run}", dir);
		const gateDir = path.join(dir, gate.id);
		requireInput(configured && same(gate.argv, configured.argv.map(replace)) && gate.timeoutMs === configured.timeoutMs
			&& gate.declaredCwd === path.resolve(ctx.root, configured.cwd || ".") && within(ctx.root, gate.cwd), `${gate.id} command identity differs from declaration`);
		verifyEvidence(gate.stdout);
		verifyEvidence(gate.stderr);
		requireInput(gate.stdout.path === path.join(gateDir, "command-stdout.txt") && gate.stderr.path === path.join(gateDir, "command-stderr.txt"), `${gate.id} evidence path differs from run directory`);
		requireInput(gate.artifacts.length === configured.artifacts.length, `${gate.id} missing artifact receipts`);
		for (const [index, artifact] of gate.artifacts.entries()) {
			requireInput(index < configured.artifacts.length && artifact.sourcePath === path.resolve(ctx.root, replace(configured.artifacts[index]))
				&& artifact.path === path.join(gateDir, `artifact-${index}`), `${gate.id} artifact path differs from declaration`);
			verifyEvidence(artifact, source);
		}
		for (const [phase, probe] of Object.entries(gate.environment || {})) {
			requireInput(["before", "after"].includes(phase) && probe.stdout.path === path.join(gateDir, `${phase}-stdout.txt`)
				&& probe.stderr.path === path.join(gateDir, `${phase}-stderr.txt`), `${gate.id} environment evidence path differs from run directory`);
			requireInput(configured.environment && same(probe.argv, configured.environment.probeArgv.map(replace))
				&& probe.cwd === gate.cwd && probe.timeoutMs === gate.timeoutMs, `${gate.id} historical environment command differs from declaration`);
			verifyEvidence(probe.stdout);
			verifyEvidence(probe.stderr);
		}
	}
	return { run, manifest: declared.manifest };
}

function findingsProblems(ctx) {
	const problems = [];
	const counts = new Map();
	for (const finding of ctx.manifest.findings) {
		for (const attempt of finding.failedAttempts) {
			const key = JSON.stringify([attempt.premise, attempt.gateId]);
			if (!counts.has(key)) counts.set(key, new Set());
			counts.get(key).add(attempt.head);
			try {
				const { run, manifest } = readRun(ctx, attempt.reproRunId);
				requireInput(run.head === attempt.head, `${finding.id} historical repro HEAD mismatch`);
				const gate = manifest.gates.find((gate) => gate.id === attempt.gateId);
				const receipt = run.gates.find((receipt) => receipt.id === attempt.gateId);
				requireInput(gate && receipt && !receipt.error && Number.isInteger(receipt.exitCode)
					&& gateProblems(gate, receipt, manifest).length > 0, `${finding.id} historical repro must show an executed failing gate`);
			} catch (error) { problems.push(`${finding.id} historical evidence: ${error.message}`); }
		}
	}
	for (const [key, heads] of counts) {
		const [premise, gateId] = JSON.parse(key);
		const investigations = ctx.manifest.findings.flatMap((finding) => finding.investigations);
		if (heads.size >= 2 && !investigations.some((item) => item.premise === premise && item.gateId === gateId)) {
			problems.push(`requires Attack the Premise evidence for ${gateId} under ${premise}`);
		}
	}
	return problems;
}

function projectRule(ctx, head, declarationValue) {
	const rule = ctx.manifest.projectRules?.changedFileLimit;
	if (!rule) return null;
	const base = baseCommit(ctx);
	requireInput(base === declarationValue.baseCommit, "changed-file base drifted since declaration");
	const mergeBase = git(ctx.root, ["merge-base", base, head]);
	const paths = git(ctx.root, ["diff", "--name-only", "-z", mergeBase, head]).split("\0").filter(Boolean);
	return { baseCommit: base, mergeBase, count: paths.length, maximum: rule.maximum };
}

function check(ctx) {
	const head = currentHead(ctx);
	const report = { ready: false, head, problems: [], runId: null, store: ctx.store };
	try {
		clean(ctx, head);
		const active = bindDeclaration(ctx, head);
		const { id, receiptSha256 } = parseJSON(fs.readFileSync(path.join(ctx.store, "run.json")));
		report.runId = id;
		requireInput(nonempty(receiptSha256) && hash(fs.readFileSync(path.join(ctx.store, "runs", id, "receipt.json"))) === receiptSha256, "latest run is incomplete or its receipt hash changed");
		const { run } = readRun(ctx, id, true);
		requireInput(run.head === head, "run evidence is stale for actual HEAD");
		requireInput(run.manifestSha256 === ctx.manifestSha256 && run.declarationId === active.id, "run evidence is stale for declaration");
		report.problems.push(...run.problems);
		requireInput(run.gates.length === ctx.manifest.gates.length && new Set(ids(run.gates)).size === run.gates.length, "run has missing or duplicate gate receipts");
		for (const gate of ctx.manifest.gates) {
			const receipt = run.gates.find((receipt) => receipt.id === gate.id);
			const replace = (value) => value.replaceAll("{run}", path.join(ctx.store, "runs", id));
			requireInput(receipt && same(receipt.argv, gate.argv.map(replace)) && receipt.timeoutMs === gate.timeoutMs
				&& receipt.cwd === fs.realpathSync(path.resolve(ctx.root, gate.cwd || ".")), `${gate.id} command receipt differs from declaration`);
			requireInput(receipt.artifacts.length === gate.artifacts.length, `${gate.id} missing artifact receipts`);
			for (const phase of gate.measurement ? ["before", "after"] : ["before"]) {
				if (!gate.environment) continue;
				const probe = receipt.environment?.[phase];
				if (!probe) continue;
				requireInput(same(probe.argv, gate.environment.probeArgv.map(replace)) && probe.cwd === receipt.cwd && probe.timeoutMs === gate.timeoutMs, `${gate.id} ${phase} environment command differs from declaration`);
			}
			report.problems.push(...gateProblems(gate, receipt, ctx.manifest));
		}
		const rule = projectRule(ctx, head, active.value);
		requireInput(same(rule, run.projectRule), "changed-file rule receipt mismatch or base drift");
		if (rule && rule.count > rule.maximum) report.problems.push(`changed-file count ${rule.count} exceeds project maximum ${rule.maximum}`);
		report.problems.push(...findingsProblems(ctx));
		clean(ctx, head);
	} catch (error) { report.problems.push(error.message); }
	report.problems = [...new Set(report.problems)];
	report.ready = report.problems.length === 0;
	return report;
}

function run(ctx) {
	const head = currentHead(ctx);
	const id = crypto.randomUUID();
	const dir = path.join(ctx.store, "runs", id);
	fs.mkdirSync(dir, { recursive: true });
	atomicJSON(path.join(ctx.store, "run.json"), { id });
	const receipt = { version: 1, runId: id, repoRoot: ctx.root, manifestPath: ctx.relativeManifest, head,
		manifestSha256: ctx.manifestSha256, declarationId: null, startedAt: new Date().toISOString(), gates: [], problems: [], projectRule: null };
	try {
		clean(ctx, head);
		const active = bindDeclaration(ctx, head);
		receipt.declarationId = active.id;
		receipt.projectRule = projectRule(ctx, head, active.value);
		for (const gate of ctx.manifest.gates) {
			const replace = (value) => value.replaceAll("{run}", dir);
			const gateDir = path.join(dir, gate.id);
			fs.mkdirSync(gateDir);
			const cwd = fs.realpathSync(path.resolve(ctx.root, gate.cwd || "."));
			requireInput(within(ctx.root, cwd), `${gate.id} cwd must be within repoRoot`);
			const environment = {};
			const probe = (phase) => {
				const result = execute(ctx, head, gateDir, phase, gate.environment.probeArgv.map(replace), cwd, gate.timeoutMs);
				if (!result.error && result.exitCode === 0) {
					try { result.observed = parseJSON(fs.readFileSync(result.stdout.path, "utf8")); }
					catch (error) { result.error = `environment JSON: ${error.message}`; }
				}
				environment[phase] = result;
			};
			if (gate.environment) probe("before");
			let setupProblem = gate.environment ? commandProblem(environment.before, `${gate.id} before environment`) : null;
			if (gate.environment && !setupProblem) {
				try { observed(fs.readFileSync(environment.before.stdout.path, "utf8"), environmentRequired(gate, ctx.manifest), `${gate.id} before environment`); }
				catch (error) { setupProblem = error.message; }
			}
			const argv = gate.argv.map(replace);
			const result = setupProblem ? capture(gateDir, "command", argv, cwd, gate.timeoutMs, { status: null, error: new Error(`environment setup failed, gate skipped: ${setupProblem}`) })
				: execute(ctx, head, gateDir, "command", argv, cwd, gate.timeoutMs);
			if (gate.measurement && !setupProblem) probe("after");
			const artifacts = [];
			for (const [index, artifact] of gate.artifacts.entries()) {
				const sourcePath = path.resolve(ctx.root, replace(artifact));
				const captured = path.join(gateDir, `artifact-${index}`);
				try { fs.copyFileSync(sourcePath, captured); artifacts.push({ ...evidence(captured), sourcePath }); }
				catch (error) { receipt.problems.push(`${gate.id} artifact evidence: ${error.message}`); }
			}
			receipt.gates.push({ id: gate.id, declaredCwd: path.resolve(ctx.root, gate.cwd || "."), ...result, environment, artifacts });
		}
		clean(ctx, head);
	} catch (error) { receipt.problems.push(error.message); }
	receipt.finishedAt = new Date().toISOString();
	atomicJSON(path.join(dir, "receipt.json"), receipt);
	const receiptSha256 = hash(fs.readFileSync(path.join(dir, "receipt.json")));
	fs.writeFileSync(path.join(dir, "receipt.sha256"), receiptSha256 + "\n", { flag: "wx" });
	atomicJSON(path.join(ctx.store, "run.json"), { id, receiptSha256 });
	return check(ctx);
}

export function acceptanceCLI(args) {
	try {
		const [action, file, option, store] = args;
		requireInput(["declare", "run", "check"].includes(action) && nonempty(file)
			&& (args.length === 2 || args.length === 4 && option === "--store" && nonempty(store)),
			"Usage: node check-plan.mjs acceptance <declare|run|check> <acceptance.json> [--store <directory>]");
		const ctx = context(file, store);
		const report = action === "check" ? check(ctx) : locked(ctx, () => action === "declare" ? declare(ctx) : run(ctx));
		console.log(JSON.stringify(report, null, "\t"));
		return report.ready === false ? 1 : 0;
	} catch (error) {
		console.error(error.message);
		return 2;
	}
}
