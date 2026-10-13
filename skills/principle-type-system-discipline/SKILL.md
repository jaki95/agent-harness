---
name: principle-type-system-discipline
description: "Apply when designing types, reviewing a function signature, or writing code in any statically-typed language. Make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, refuse to lie to the compiler, exhaust variants, derive from authoritative schemas."
disable-model-invocation: true
---

# Type System Discipline

Make the compiler reject impossible states, mismatched primitives, and unhandled variants. Prefer defining errors and special cases out of existence over proliferating handlers.

Applies to any typed language. Skills like `typescript-best-practices` ground it in specific syntax.

- **Make illegal states unrepresentable.** Model variants as sum types: discriminated unions in TypeScript, enums with payloads in Rust/Swift/Kotlin, sealed classes in Scala, ADTs in Haskell/OCaml. Avoid bags of optional fields where contradictory combinations compile. `{ completed: boolean; completedAt?: Date }` admits `completed: true; completedAt: undefined`. Derive the boolean from `completedAt !== null`, or model `{ kind: 'open' } | { kind: 'done'; at: Date }`. If a bug makes you question a field combination, the type is too loose. If a comment must explain when the combination is valid, split it into a sum type.
- **Types are constructions, not restrictions.** Build the type from the values you want instead of carving them out of a looser type with checks. A non-empty list is a head plus a rest. A valid time range is a start plus a duration. An even-length list can be a list of pairs. Choose the shape that cannot build the illegal value and expose the interface callers need.
- **Brand semantic primitives.** `UserId` and `OrderId` are strings underneath but should not be interchangeable. Use newtypes in Rust, opaque types in Swift, value classes in Kotlin, phantom types in Haskell, or branded intersections in TypeScript. Validate once at creation, trust the type downstream. If two arguments share a primitive type but mean different things, brand them.
- **External data is untyped until parsed.** RPC payloads, JSON, IPC messages, CLI args, config files, environment variables, database rows. Have a parse function at every boundary that turns unstructured input into the typed model. See the **principle-boundary-discipline** skill for where to put validation.
- **Don't lie to the type system.** Casts, unsafe coercions, and assertion functions that bypass the compiler are latent runtime crashes. If the compiler can't prove a fact, prove it (validate, narrow, refine the model) or accept that the cast is a hazard. Trace each `any`, `as`, or `assertNotNull` to the boundary and validate there.
- **Exhaustive matching is the compiler's job.** A match on a sum type must fail compilation when a new variant is added without handling, so the compiler tells the next agent where to add a case. Use your language's idiom: a `never`-typed binding in TypeScript, unannotated `match` in Rust, `-Wincomplete-patterns` in Haskell, sealed-class match exhaustiveness in Kotlin.
- **Derive types from authoritative schemas.** When a protocol buffer, OpenAPI spec, GraphQL schema, database migration, design-system token file, or another file owns a shape, derive from it instead of hand-rolling a parallel type. See the **principle-encode-lessons-in-structure** skill.
- **Strengthen a type only where partiality appears.** A runtime assertion, null check, or "this should never happen" throw marks a type that is too weak. Push that check into the type, then stop. Track the cases each use site must handle, not every detail of the data. Prefer total functions. `sum` of an empty list is 0, so it takes the plain list. `head` of an empty list has no answer, so it demands the non-empty one. If nothing would otherwise panic, keep the plain type.
