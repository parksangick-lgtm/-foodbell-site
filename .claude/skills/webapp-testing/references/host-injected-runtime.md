# Pages that depend on a host-injected runtime

Load this before testing a page whose behaviour depends on an object the
hosting viewer injects at runtime, for example a claude.ai artifact page
that calls `window.claude.use('db')`. Opened from `file://`, such a page
never runs its save path, so a plain static-HTML test checks nothing that
matters.

## Do not test against the user's real data first

Writing a test document into the real store, reading it back and deleting
it has two problems:

- If the page subscribes live to that data, the test document appears on
  the screen the user may have open at that moment.
- It proves that the server accepted a write. It tests none of the page's
  own logic, which is where race conditions live (an input reopening after
  save, the wrong item selected, a save landing on another item after a tab
  switch).

Use a write to real data only as a last step, and tell the user before
making it.

## Fake the host from its documented contract

1. Read the host's current contract (for claude.ai artifacts, the
   capability's `.d.ts` typings). Build the fake from that document, not
   from what the page happens to call. Re-read the contract each time:
   the example below follows the contract as it stood at last verification.
2. Inject the fake before any page script runs:
   `page.add_init_script(script=mock_source)`.
3. Wrap the page in the same skeleton the host publishes it in (doctype,
   viewport meta, and global rules such as `[hidden]{display:none!important}`),
   write it to a file and open it with `file://`. Without the skeleton,
   visibility bugs pass or fail for the wrong reason.
4. Expose the fake's store on `window` (e.g. `window.__store`) so the test
   can assert on what was written, not only on what is shown.

`examples/mock_claude_runtime.js` is a working fake of the `db` and `user`
capabilities. A write is echoed to listeners at once with
`hasPendingWrites: true`, and its promise resolves after a simulated round
trip. `__MODE__` and `__SEED__` are placeholders: the test replaces them
before injecting.

## Run every event order the contract allows

When behaviour depends on the order of asynchronous events, run the same
scenario once per order the contract permits. In the fake above, `MODE`
selects whether a confirmed snapshot follows the write and whether it comes
before or after the write promise resolves (`none`, `before-resolve`,
`after-resolve`). In the case that produced this file, the original bug
passed under one of the three orders and failed under the other two; a
single order could have shipped it.

The same fake also disproves hypotheses cheaply: a suspected cause that
passes under every order is not the cause, and you can drop the fix for it.
