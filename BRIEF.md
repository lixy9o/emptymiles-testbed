# EmptyMiles Matching Testbed - a pitch

## The idea

You can't safely A/B-test a matching algorithm on live operations, and as an outsider I don't
have your production order logs to replay. So how do you measure whether a change to the
matcher actually helps - before it touches real cargo?

My answer: an **offline testbed**. A sandbox that generates a logistics world you control
(orders, planned routes, demand clustering, time windows), runs *any* matching strategy through
it behind one simple interface, and reports the metrics that matter - fill rate, empty-mile %,
**CO₂ vs. baseline**, cost, and compute latency - on identical, reproducible accounting.

The clever part: *not* having your data stops being a weakness. **Generating the data is the
point.** And the day you're willing to share real logs, the same harness replays them unchanged.

## I didn't just sketch this - I built a working prototype

To be clear, this isn't a slide deck. It's a runnable system, and it already produces real
findings (synthetic, but the emission/cost physics are grounded in published DEFRA/GLEC figures):

- **A pluggable matcher interface** - drop your real matcher in and benchmark it against a
  baseline, a greedy piggyback matcher, and an exact OR-Tools optimum (a ceiling to measure against).
- **Explainable match scoring** - every match carries reason codes (CO₂ saved, detour, fill,
  time slack). It caught a *carbon-losing* match on its first run, which I then guarded against -
  the kind of bug a black-box matcher hides.
- **Empty-leg forecasting** - learns where spare capacity reliably appears and predicts it on a
  held-out day with measurable skill, so matching could go proactive rather than reactive.
- **A liquidity analysis** showing match rate *falls* as order volume outpaces available routes -
  i.e. matching is capacity-constrained, not free.
- All of it **seeded, reproducible, and covered by ~25 passing tests.**

One headline from the default run: a simple greedy matcher already cuts **~5% CO₂** vs. giving
every order its own dedicated trip - and the testbed is built precisely to find the strategies
that beat that.

## Want to see it run?

If any of this is useful to you, **reply and I'll email you the full prototype** - the complete
build, the demos, and the test suite - so you can run it and poke at the assumptions yourself.
I'd genuinely value your read on three things: whether the scenario assumptions match real ops,
the insertion-cost model, and whether plugging the real matcher behind the interface is realistic.

No pressure either way - but if it's interesting, the working version is one email away.
