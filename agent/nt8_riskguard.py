"""
nt8_riskguard.py — the NT8 RiskGuard profile as a consumer of agent-loop.

Usage:
    agent-loop --profile nt8-riskguard --profile-module agent.nt8_riskguard \
        --tickets agent/tickets_p0.json --ticket T1
"""
from __future__ import annotations

from agent_loop.profiles import Profile, register

NT8_RISKGUARD = Profile(
    name="nt8-riskguard",
    language="csharp",
    file_suffixes=(".cs",),
    line_comment="//",
    block_comment=("/*", "*/"),
    block_kind="decl",  # brace-delimited
    preprocessor_directives=("#if", "#endif"),
    # NinjaTrader's log pane mangles non-ASCII, so the static gate rejects it.
    # This is an NT8 constraint, not a universal one -- hence a profile flag.
    ascii_only=True,
    # Build and test
    build_cmd="dotnet build tests/RiskGuardTests.csproj --nologo -v q",
    test_cmd="dotnet run --project tests/RiskGuardTests.csproj --nologo -v q",
    # Lock-scope gate (C# has a lock primitive)
    lock_name="_stateLock",
    risk_calls=(".Flatten", ".Cancel", ".Submit", ".CreateOrder"),
    # File scope (Developer mode)
    file_scope_whitelist=("addons/",),
    # Protected paths
    protected=(
        "*Tests.cs",
        "*.csproj",
        "agent/*",
    ),
    test_sources=("tests/*Tests.cs",),
    # Context and token budgets
    context_token_budget=3000,
    round_input_token_budget=40000,
    # Graph project (codebase-memory-mcp).
    # Deliberately empty after the repo split: the old value pointed at
    # tvDownloadOHLC's graph, which indexed these files under
    # scripts/ninjatrader/addons/ and no longer contains them at all. A stale
    # graph answers with paths that do not exist, which is worse than no graph.
    # Re-enable by indexing THIS repo and putting its project name here.
    graph_project="",
    # Prompts (carried over from the original profiles.py)
    implementer_rules="""\
You are a senior C# engineer hardening a NinjaTrader 8 AddOn that manages
real money on funded futures accounts. You make surgical, minimal, provably-correct edits.

HARD CONSTRAINTS (violating any of these fails review):
1. Target C# 8.0 / .NET Framework 4.8 AND a net8.0 test build. No records, no
   target-typed new, no file-scoped namespaces, no raw string literals, no ranges/indices.
2. The file compiles under BOTH `#if TESTING` (net8.0, NinjaTrader stubs) and the real
   NT8 build. If you touch code inside a `#if`/`#else` block, preserve the structure.
3. NEVER call Account.Flatten / Account.Cancel / Account.Submit / Account.CreateOrder while
   holding the _stateLock. Collect intent under lock, execute after releasing it.
4. ASCII only in string literals and comments. No emoji, no smart quotes, no box drawing.
5. Do not rename existing public/internal members, do not change existing method signatures
   that callers depend on, and do not delete existing behaviour that is not part of the ticket.
6. Preserve the existing brace style, 4-space indentation, and the exact leading indentation
   of the first line of each region you return.
7. Fail closed: if a safety precondition cannot be verified, take the conservative action
   (flatten / block / skip the copy), never the permissive one.
8. Do not weaken, delete, or work around a test in order to pass. If a test is wrong, say so
   in your notes and leave it alone -- you are not given access to test code.""",
    reviewer_priorities="""\
You are an adversarial code reviewer for safety-critical trading software.
You are reviewing a proposed patch to a NinjaTrader 8 risk-guard AddOn that protects real funded
accounts. Assume the implementer is confident and wrong. Your job is to find the case where this
patch loses money or leaves a position unprotected.

Check, in priority order:
1. CORRECTNESS OF THE FIX: does it actually close the described defect, in every path?
2. NEW NAKED-RISK PATHS: any path where a position ends up with no covering stop, or a stop
   larger than the position (which flips the position when it triggers).
3. LOCK DISCIPLINE: any Account.Flatten/Cancel/Submit/CreateOrder reachable while _stateLock
   is held; any new lock ordering.
4. RACE CONDITIONS: state written after an async submit; event handlers that can observe a
   half-updated FSM; timers armed twice or never disposed.
5. TEST ADEQUACY: the suite is a first-class artifact, review it as such.
6. COMPILE BREAKS: C# 8.0 / net48 + net8.0-with-stubs compatibility.
7. REGRESSIONS: existing behaviour or existing tests that this would break.

Be specific. Cite the offending line text. Do not restate the ticket. Do not praise.""",
    # This text used to live in the package as a hardcoded ARBITER_SYSTEM, which
    # meant every consumer -- including the Python profile -- got the NT8 bar for
    # UPHELD ("state the sequence of events that loses money"). It belongs to
    # this profile, where it is true.
    arbiter_rules="""\
You are the arbiter for a patch to a NinjaTrader 8 risk-guard AddOn that
protects real funded futures accounts.

The mechanical gates have already established that it compiles, that the full test suite runs
with no regressions, and that no broker call is reachable while the state lock is held.

An UPHELD finding must state the concrete sequence of events that loses money or leaves a
position unprotected. "Could be clearer", "might be safer", and "consider also handling" are
NOT upheld.

An unsound SHIP here reaches a live trading account, so prefer ESCALATE over a confident wrong
answer. On naked-position risk, a model does not get the last word.""",
    # Settled decisions.
    #
    # These are injected into EVERY review round. The handover's rule is "add to
    # both places, and retire from both places" -- because a settled decision that
    # has since been settled the other way does not merely go stale, it instructs
    # the panel to approve reintroducing a closed defect.
    #
    # Only SIX were carried across the 2026-08-12 repo split, while the handover
    # claimed P0-9's five invariants and P1-56's two were "mirrored verbatim" here.
    # They were not. That is not a bookkeeping slip: P1-56's invariant 1 is exactly
    # the rule the P0-63 candidate broke (it re-drove through SyncFollowerStopOnce,
    # bypassing the in-flight reservation), NO reviewer flagged it, and it was caught
    # by reading. The panel could not have flagged it -- it was never told. Restored
    # and reconciled against handover section 7 on 2026-08-13.
    settled=(
        "CoveredQuantity is the SUM over every live protective stop on the position, and both it "
        "and RecognizedStopOrder are DERIVED from PositionGuardFsm's stop list -- neither is "
        "assignable (P1-36, closed 2026-08-07).",
        "NT8 raises ExecutionUpdate BEFORE PositionUpdate. Code that reads account.Positions "
        "from an execution handler reads a position that does not exist yet on an entry fill "
        "(P0-49, closed 2026-08-07).",
        "The copier FAILS CLOSED ON ENTRIES, NEVER ON EXITS.",
        "Pending copies and recognised stops are keyed by Order OBJECT REFERENCE, never by "
        "Order.OrderId. NT8's OrderId is neither unique nor stable.",
        "The mirrored bracket stop carries the leader's SIGNED offset applied to the FOLLOWER's "
        "own fill. Never Math.Abs, never the leader's stop PRICE.",
        "Simulation accounts are identified by account.Provider == Provider.Simulator, never "
        "by a name prefix (P1-20, closed).",
        # --- P1-56's two invariants (closed 2026-08-10) ---
        "SyncFollowerStop is the RESERVATION HOLDER; SyncFollowerStopOnce does the work and "
        "never touches the flags. StopInFlight is published under _lock before any broker call "
        "and cleared exactly once in a finally that runs AFTER the bounded re-drive loop. Any "
        "new caller that must respect the reservation calls the WRAPPER, never ...Once. Do not "
        "clear it between passes (reopens the window); do not leave it for the re-drive to clear "
        "(leaks forever -- the re-drive backs off before reaching any finally); do not make the "
        "re-drive recursive; and do not let re-drive passes skip the StopAttempts increment "
        "(P1-56, closed 2026-08-10).",
        "bracket.WorkingStop is NEVER cleared before a broker call, nor in OnFollowerOrderUpdate "
        "-- not even on catch or abort paths. An honest WorkingStop is what makes a concurrent "
        "sync MODIFY the existing stop instead of creating a second one (P1-56).",
        # --- P0-9 item (1)'s five invariants (closed 2026-08-10) ---
        "The mirrored stop and target legs are DELIBERATELY ASYMMETRIC. Do not propose unifying "
        "the syncs or sharing StopInFlight/StopAttempts with the target: sharing lets an in-flight "
        "TARGET sync delay the risk leg, and lets target churn spend the stop's budget (P0-9).",
        "A fresh OCO id is minted ONLY on the cancel-then-create path -- not per-generation on "
        "every sync, and not never. Re-using an id whose group may be retired has the broker "
        "reject the new STOP. The rule is about the group's life, not the id's history (P0-9).",
        "A leg terminal while its sibling FILLED was RETIRED, not lost, and must not be "
        "resubmitted. P0-50's live re-read does not catch this because ExecutionUpdate precedes "
        "PositionUpdate (P0-9).",
        "A MULTI-TARGET leader is not mirrored at all -- not nearest, not last-seen. This does "
        "not apply to stops (P0-9).",
        "Leg prices are rounded to tick BEFORE the comparison, never after; after would never "
        "match and would re-drive the leg forever (P0-9).",
        # --- P0-63 (fixed 2026-08-13, remedy 3) ---
        "Account.Change() is a REQUEST, not a setter. The caller's desired values sit on the "
        "Order until the provider settles, and on provider: Simulator the change can be silently "
        "ignored and the order REVERTS to its pre-change values. So a synchronous read-back proves "
        "nothing: detection is 'the SETTLED order is still at its pre-change values', which is "
        "positive evidence and fails safe. Recovery marks the account once and bypasses "
        "modify-in-place thereafter; modify-in-place is preserved for providers that honour it "
        "(P0-63, fixed 2026-08-13 via remedy 3).",
        # --- Lock-scope false positives the panel raises every round ---
        "Orphan cancels are QUEUED, not inline: UpdateFsmOnPosition adds to _pendingCancels under "
        "the lock and DrainPendingCancels sends them after it is released. Do not move the Cancel "
        "back inline, and do not call the drain from inside the lock -- the lock is re-entrant, so "
        "that reads as correct and changes nothing (P1-35, closed 2026-08-07).",
        "ArmGraceTimer under _stateLock is CORRECT and required -- it only schedules a timer "
        "callback and makes no broker call. Reviewers raise it as a lock-scope violation every "
        "round; it is a false positive.",
        "SeedFsmsForExistingPositions needs no lock of its own: every call site already holds "
        "_stateLock and it makes no broker call. Reviewers flag this as a false positive.",
        "Reading account.Positions outside _stateLock is ACCEPTED -- a stale read yields a safe "
        "abort or a harmless spurious grace timer, not naked risk. The TOCTOU window between the "
        "live position read and account.Submit CANNOT be closed without holding a lock across a "
        "broker call, which is forbidden.",
        "ValidateInvariant must NOT reject PlaceStopOrder when action.Quantity > liveQuantity. It "
        "looks like a missing safety check and it leaves the position permanently NAKED; "
        "ExecuteAction re-sizes from the live position.",
        "The lockout sweep's three-phase order is deliberate: cancel risk-increasing orders, "
        "flatten, then cancel reducing orders only for instruments confirmed flat. Cancelling "
        "everything up front and then failing to flatten is the naked-position bug (P1-11).",
        "No new GuardFsmState enum values -- existing tests assert on them.",
        # --- Session 20, 2026-08-13: P0-67, P0-68, P1-69, P1-70, P1-71 ---
        "A cache of broker state is written ONLY from the broker. DynamicAtmManager's "
        "bracket.CurrentStopPrice is assigned in exactly one place -- ReconcileStopFromBroker, from "
        "the live Order -- and NEVER from the value passed to Change(). Do not remove the reconcile "
        "on the grounds that the request usually succeeds: on provider: Simulator it never does "
        "(P0-67, fixed 2026-08-13).",
        "ONE outstanding Change() per order, at EVERY call site. A second change while one is in "
        "flight is dropped AND reverts the order, so it ends at neither request's values (P0-61, "
        "established live). The copier holds this with bracket.StopInFlight; the ATM manager holds "
        "it with bracket.RequestedStopPrice. In ScaledRunner the breakeven and trailing moves can "
        "both fire in one sweep, which is how this was found.",
        "A log line must not claim an outcome it has not observed: ..._REQUESTED before the broker "
        "call, ..._CONFIRMED only on settle, printing the SETTLED values (P1-70). And a message must "
        "not NAME another event type -- it poisons grep on a file whose purpose is post-hoc "
        "grepping, and it broke an absence assertion in the suite.",
        "Every relationship named in COPY_BEGIN emits exactly ONE terminal outcome event, matched by "
        "NAMING CONVENTION (COPY_SUBMITTED / COPY_SKIPPED_* / COPY_BLOCKED_* / COPY_FAILED_*), so a "
        "skip path added later is counted automatically. Corollary, and it is load-bearing: a "
        "NON-terminal event must NOT take a terminal prefix, or one relationship reports two "
        "outcomes while another drops in silence and the totals still look right (P1-71).",
        # --- P2-92, 2026-08-13. The panel upheld this SEVEN times in one round, as seven
        # restatements of one finding, and it is refuted on all three legs. Recorded here so the
        # next round does not spend itself on it again.
        "MarkRuleLockout acquiring _stateLock (via IsActingMode) is CORRECT and cannot deadlock. "
        "Only one lock exists in this file, so there is no ordering cycle; _stateLock is RE-ENTRANT, "
        "so acquiring it on a thread that already holds it cannot block; and NOTHING in the addon "
        "ever waits on another thread while holding it -- there is no Join, Wait, WaitOne or .Result "
        "anywhere (every `Join` in the file is string.Join). ProcessAction already calls "
        "IsActingMode() from inside its own lock(_stateLock) block and has shipped that way. Do not "
        "propose passing the mode in, caching it, or reading _mode unsynchronised (P2-92, closed "
        "2026-08-13).",
        "A shadow-mode breach flattening nothing is the DEFINITION of shadow mode, not a defect of "
        "any patch that leaves it alone. Do not file 'the position is left unprotected while trading "
        "is allowed' against P2-92's fix: the exposure after it is identical to the exposure before "
        "it, minus a lockout that stopped the copier and every strategy while flattening nothing. "
        "And do not propose suppressing IsLockedOut in shadow -- eight tests breach in the default "
        "mode and assert that flag, and the state model is not the defect (P2-92).",
        "A read endpoint must not mutate. /api/copier/config's get action must NEVER call "
        "LoadFromDisk: it replaces the in-memory relationships that ObserveFollowerFill writes its "
        "measurements onto, so reading the config destroyed the thing being read. The metrics are "
        "session-scoped -- a recompile resets them and a zero is not a measurement (P1-69).",
    ),
)

register(NT8_RISKGUARD)