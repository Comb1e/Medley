---
name: MATH
description: >
  A paradigm for thinking through mathematical problems rigorously and clearly.
  Use this skill whenever the user presents a math problem, asks for help with
  mathematical reasoning, wants to understand a proof, needs to solve an equation,
  is stuck on a word problem, or asks "how do I approach this?" about anything
  quantitative. Also trigger for physics, statistics, logic puzzles, or any
  problem that involves formal reasoning. Do not wait for the user to say
  "use the math skill" — if numbers or symbols are involved, use this.
---

# Output
The output language should be markdown and suffix should be .md

# Math Problem-Solving Paradigm

A structured way of thinking about mathematical problems — from first contact to verified solution.

---

## The Core Stance

Before doing anything, adopt this posture:

> **"I do not yet understand this problem. My first job is to understand it — not solve it."**

Rushing to computation is the most common error. The paradigm below enforces a deliberate pause before any calculation begins.

---

## Phase 0 — Receive and Restate

**Goal:** Translate the problem from the author's language into your own.

1. **Read once without writing anything.** Let the problem sit.
2. **Identify the ask.** What is the problem actually requesting? A number? A proof? A set? A function?
3. **Restate in plain language.** Write one or two sentences explaining the problem as if describing it to someone who hasn't seen it. If you can't do this, you don't yet understand it.
4. **Note what is given vs. what is unknown.** List them explicitly.

> *Heuristic: If restating feels unnecessary, you're skipping it. Don't.*

---

## Phase 1 — Classify

**Goal:** Know what kind of problem this is before touching it.

Ask yourself:

| Question | Why it matters |
|---|---|
| Is this algebraic, geometric, combinatorial, analytic...? | Determines which tools apply |
| Is this asking for existence, uniqueness, or a value? | Shapes the strategy |
| Is this continuous or discrete? | Governs which theorems and techniques are legal |
| Does this have symmetry, periodicity, or special structure? | Often reveals the solution path |
| Have I seen a structurally similar problem before? | Analogical reasoning is powerful |

Classification is not labeling for its own sake — it activates the right mental toolkit.

---

## Phase 2 — Build Intuition Before Computing

**Goal:** Form a hypothesis about what the answer should look like, and why.

This phase is skipped most often and costs the most.

**Techniques:**
- **Try small / simple cases.** What happens when n=1, n=2? What's the base case?
- **Draw a picture.** Even for algebraic problems, a diagram often reveals structure. Geometry is the native language of the mind.
- **Estimate or bound.** Can you say roughly how large the answer should be? Is it obviously greater than zero? Less than 1?
- **Ask: what would make this easy?** If one variable were fixed, or one constraint removed, or the problem were 1D instead of 3D — what would happen?
- **Check extreme cases.** What happens as a variable goes to 0, ∞, or some critical threshold?

By the end of this phase, you should have a *guess* — even a vague one. This guess serves as a target and a sanity check.

---

## Phase 3 — Choose a Strategy

**Goal:** Select the method before executing it.

Common strategies and when they apply:

| Strategy | When to reach for it |
|---|---|
| **Direct computation** | The path is clear; just carry it out carefully |
| **Reduction / substitution** | Transform the problem into a simpler or known one |
| **Induction** | Problem involves natural numbers or recursive structure |
| **Contradiction** | Easier to assume the opposite and derive impossibility |
| **Contrapositive** | "If P then Q" becomes "If not Q then not P" |
| **Construction** | Existence proof — build the object explicitly |
| **Invariant / monovariant** | Track a quantity that never changes (or always changes monotonically) |
| **Pigeonhole** | Counting objects into containers; one box must overflow |
| **Symmetry / bijection** | Two sets are the same size if you can pair them perfectly |
| **Generating functions** | Encode a sequence as a power series and use algebra |
| **Dimensional analysis** | Check that units / degrees / types are consistent |

> *Rule: Name your strategy out loud before executing. If you can't name it, you haven't chosen one.*

---

## Phase 4 — Execute Carefully

**Goal:** Carry out the chosen strategy without shortcuts.

**Discipline rules during execution:**

1. **Work on one line at a time.** Do not collapse multiple steps into one — that's where errors hide.
2. **Annotate transformations.** Note why each step is valid, even briefly. ("Factor out 2." "Apply AM-GM." "By the chain rule.")
3. **Keep track of assumptions.** If you assumed x > 0, write it down. If a case split was needed, label each branch.
4. **Don't abandon a strategy mid-stream.** If the strategy isn't working, go back to Phase 3. Switching mid-execution creates mess.
5. **Preserve equals signs.** Equations should chain: A = B = C = D. Losing the chain is the source of most algebraic errors.

---

## Phase 5 — Verify

**Goal:** Confirm the answer is correct before declaring victory.

Verification is not optional. It is part of solving the problem.

**Verification checklist:**

- [ ] **Substitute back.** Does the answer satisfy the original equation or conditions?
- [ ] **Check the units / dimensions.** If the answer should be a length, does it have units of length?
- [ ] **Test against known cases.** Does the formula give the right answer for n=1, n=2, or the cases you tried in Phase 2?
- [ ] **Check boundary behavior.** Does the solution behave correctly at the extremes you considered?
- [ ] **Sanity-check the magnitude.** Is the answer in the ballpark of your Phase 2 estimate?
- [ ] **Check for missed cases.** Did you handle all branches, all domains, all edge conditions?

If any check fails, the error is almost always in Phase 4. Retrace from the last verified step.

---

## Phase 6 — Reflect

**Goal:** Extract the lesson, not just the answer.

This phase is what separates problem-solvers from calculators.

Ask:

- **What was the key insight?** The one move that unlocked everything.
- **What would I do differently?** Where did I waste time or go down a wrong path?
- **What is this problem a special case of?** Can I generalize the result?
- **What other problems does this technique solve?** Build your mental library.
- **Is the answer beautiful or ugly?** Ugly answers sometimes signal an error; sometimes they signal a harder problem lurking beneath.

---

## Common Failure Modes (and their fixes)

| Failure | Symptom | Fix |
|---|---|---|
| **Premature computation** | You're three lines of algebra in and don't know why | Return to Phase 0. Restate the problem. |
| **Strategy amnesia** | You're doing things but aren't sure what method you're using | Stop. Name the strategy. |
| **Skipping verification** | You got an answer and moved on | Always substitute back. |
| **Case blindness** | Your argument assumes x > 0 but doesn't address x ≤ 0 | Audit your assumptions. List every case. |
| **Notation abuse** | Variables mean different things in different parts of the solution | Fix notation at the start; never reuse a symbol. |
| **Anchoring on first approach** | You're committed to a method that isn't working | Return to Phase 3. There is always another strategy. |

---

## One-Page Summary

```
0. RECEIVE     → Restate in your own words. List givens and unknowns.
1. CLASSIFY    → What kind of problem? What is it asking for?
2. INTUIT      → Small cases. Draw. Estimate. Form a guess.
3. STRATEGIZE  → Name the method before executing it.
4. EXECUTE     → One step at a time. Annotate. Track assumptions.
5. VERIFY      → Substitute back. Check edge cases. Sanity-check magnitude.
6. REFLECT     → What was the key insight? What generalizes?
```

---

## Applying This Skill

When a user presents a math problem, walk through these phases explicitly — at least internally, and visibly when the problem is complex or the user seems stuck. Don't just produce an answer. Show the reasoning at each phase. If the user is learning, narrate the paradigm as you apply it. If they're advanced, you can compress phases but never skip verification.

The goal is not speed. The goal is *understanding* — and then correctness.
