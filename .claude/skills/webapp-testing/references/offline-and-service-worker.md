# Offline and service-worker testing

Load this before writing any test that calls `context.set_offline(...)`,
waits on `navigator.serviceWorker`, or asserts an "offline" banner or
offline fallback.

Serve the page from `http://localhost` (or https). `navigator.serviceWorker`
does not exist on `file://` or `data:` pages, so a service-worker test there
fails with `Cannot read properties of undefined` before it tests anything.

## Three traps, each of which cost a full run

1. **A promise that never settles hangs `evaluate` with no timeout.**
   `page.evaluate('navigator.serviceWorker.ready')` on a page that never
   registered a worker does not fail; it waits forever. Never `evaluate` a
   promise that may not settle. Race it against a timer, or poll:

   ```python
   active = page.evaluate("""() => Promise.race([
       navigator.serviceWorker.getRegistration().then(r => !!(r && r.active)),
       new Promise(res => setTimeout(() => res('timeout'), 3000)),
   ])""")
   ```

2. **`wait_for_function` over a service-worker promise can time out while
   the worker is already active.** Poll with `page.evaluate(...)` plus
   `page.wait_for_timeout(...)` in a bounded loop instead.

3. **`navigator.onLine` lies on pages opened while offline.** After
   `context.set_offline(True)`, the page that was already open reports
   `false`. A page navigated to *while offline* and served by the service
   worker reports **`true`**. Weak mobile signal behaves the same way on real
   phones. So an offline banner keyed only on `navigator.onLine` never shows
   in exactly the case that matters.

## What to test instead

- Navigate **after** `set_offline(True)` when asserting offline UI, and
  expect `navigator.onLine` to be wrong. The app needs a second signal of
  disconnection: a failed fetch, or the data layer reporting that it is
  serving from cache (e.g. a Firestore snapshot with `fromCache` for more
  than a couple of seconds).
- Look for app code that waits on the server inside `if (navigator.onLine)`
  (for example, awaiting a write before navigating). On a page opened while
  offline that wait never ends. The fix is a bounded wait
  (`Promise.race([write, timer])`); a write queued in a persistent cache
  still goes out later. An offline test that navigates after going offline
  finds this class of bug on its first run.
- Give every wait in an offline test a bound. A missing precondition should
  fail fast with a message, not hang the run.
