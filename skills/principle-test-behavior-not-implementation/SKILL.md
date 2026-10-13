---
name: principle-test-behavior-not-implementation
description: "Apply when you write, change, or keep a test. Call the code the way its users do and assert the result they observe against a literal expected value. Ask whether a plausible defect could still pass the test; strengthen assertions that miss the behavior, or delete tests that observe none."
disable-model-invocation: true
---

# Test Behavior, Not Implementation

A test calls the code as its users do and asserts the result they observe against a literal expected value. Calls alone and restated constants do neither.

Before keeping a test, ask whether a plausible defect could still pass. Name the defect it catches and the observable behavior it checks. Strengthen an assertion that misses that behavior, or delete a test that observes none.

A test that cannot fail for a defect costs CI time and review attention. A constant pin blocks edits to the constant or prompt it restates.

**Five assertion patterns to scrutinize:**

These are warning signs, not automatic deletion rules. `toBeDefined()` fails for `undefined`, and an empty result can be correct behavior. Judge the complete test against a plausible defect.

- **Weak or no assertion.** No `expect`, or only `toBeDefined`, `toBeTruthy`, `not.toThrow`, `toBeInstanceOf`, `toBeGreaterThan(0)`.
- **Call or absence only.** Only `toHaveBeenCalled`, `not.toHaveBeenCalled`, `toBeUndefined`, `toEqual([])`, `toHaveLength(0)`, `not.toBe(wrongValue)`.
- **Self-referential.** The expected value comes from the code under test: `expect(f(a)).toBe(f(a))`, `expect(parsed.url).toBe(buildUrl(...))`.
- **Constant pin.** The assertion restates a hand-maintained constant, config default, table row, or prompt string: `expect(LIMITS.maxTools).toBe(8)`, `expect(PROMPT).toContain("You are")`.
- **Fixture asserts fixture.** Asserts on test-built data or a `beforeEach` value without calling the subject in the body.

**The fix:** call the subject in the test body with one concrete input and assert the literal output or observable effect, `expect(slugify("Hello, World!")).toBe("hello-world")`. If an absence-only assertion could miss a defect, also assert presence on the other input. For a constant, test the mechanism that reads it with one input. For a mock, assert its payload or the state after the call. Delete a test only when it observes no behavior and cannot be strengthened.

Keep relation checks across table rows (a key in two tables, a parent that exists) and `*.test-d.ts` type checks.
