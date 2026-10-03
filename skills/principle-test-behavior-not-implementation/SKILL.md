---
name: principle-test-behavior-not-implementation
description: "Apply when you write, change, or keep a test. Call the code the way its users do and assert the result they observe against a literal expected value. Ask whether a plausible defect could still pass the test; strengthen assertions that miss the behavior, or delete tests that observe none."
disable-model-invocation: true
---

# Test Behavior, Not Implementation

A test calls the code the way its users do and asserts the result they observe against a literal expected value. A test that asserts which calls the code made, or restates a constant the code contains, does neither.

The check: before you keep a test, ask whether a plausible defect could still pass it. Name the defect the assertion would catch and the observable behavior it checks. Strengthen an assertion that misses that behavior, or delete a test that observes none.

**Why:** A test that cannot fail for a defect costs CI time and review attention and catches nothing. A constant pin also fails when someone edits the constant or the prompt it restates, so it prevents that edit.

**Five assertion patterns to scrutinize:**

These patterns are warning signs, not automatic reasons to delete a test. For example, `toBeDefined()` fails for `undefined`, and an empty result can be correct behavior. Judge whether the complete test distinguishes correct behavior from a plausible defect.

- **Weak or no assertion.** No `expect`, or only `toBeDefined`, `toBeTruthy`, `not.toThrow`, `toBeInstanceOf`, `toBeGreaterThan(0)`.
- **Mock or absence only.** Only `toHaveBeenCalled`, `not.toHaveBeenCalled`, `toBeUndefined`, `toEqual([])`, `toHaveLength(0)`, `not.toBe(wrongValue)`.
- **Self-referential.** The expected value comes from the code under test: `expect(f(a)).toBe(f(a))`, `expect(parsed.url).toBe(buildUrl(...))`.
- **Constant pin.** The assertion restates a hand-maintained constant, config default, table row, or prompt string: `expect(LIMITS.maxTools).toBe(8)`, `expect(PROMPT).toContain("You are")`.
- **Fixture asserts fixture.** The assertion reads data the test built or a value computed in `beforeEach`, and the subject never runs inside the body.

**The fix:** call the subject inside the test body with one concrete input and assert the literal output or the observable effect, `expect(slugify("Hello, World!")).toBe("hello-world")`. When an absence-only assertion could miss a defect, also assert the presence on the other input. For a constant, test the mechanism that reads it with one input instead of restating the value. For a mock, assert the payload it received or the state after the call, not that it was called. When a test observes no behavior and cannot be strengthened to do so, delete it.

**Keep** a test of a relation across a table's rows (a key present in two tables, a parent that exists), and a compile-time check in a `*.test-d.ts` file.
