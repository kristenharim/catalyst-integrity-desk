# Demo script, three minutes

Runs from a frozen local snapshot. Network off. Backup video recorded.

The structure is deliberate: open on a fact nobody in the room knows, show the machine
catching it, hand the decision to a human, then zoom out to the panel. The reveal comes
before the product, because a product demo that opens on a dashboard has already lost
the room.

---

**0:00 to 0:25, the hook.**

> Every biotech thesis rests on a date. They have cash into Q1 2028, the Phase 3 reads
> out in Q3 2027, therefore they are funded to the catalyst.
>
> The left side of that sentence comes from SEC filings. The right side comes from
> ClinicalTrials.gov, where the company sets it, can change it whenever it likes, and
> nothing reconciles that change against the thesis that depended on the old date.

**0:25 to 0:50, the fact.**

Show the Rocket Pharmaceuticals revision timeline.

> Here is a real trial. Four revisions. In April 2024 they updated a primary completion
> date of June 2022. That date had already passed, six hundred and seventy seven days
> earlier, and it sat on the public registry the entire time.
>
> No press release. No 8-K. Nothing in the thesis that depended on it moved.

**0:50 to 1:20, the contract.**

> So we treat the catalyst as a contract: this company has capital to reach this readout
> by this date. Runway comes from XBRL tags, and every figure names the tag it came
> from. The readout date comes from the sponsor's own filing, with its full revision
> history attached. Python computes both sides. No model touches a number.

Point at the burn band and the flagged rows.

> Burn is a range, not a point, because a partnership upfront makes one quarter
> unrepresentative. Rows we cannot trust stay on screen with the reason attached. They
> just do not get a rank.

**1:20 to 1:55, the break.**

Fire the scripted amendment.

> An amendment lands and pushes primary completion out nine months. Python recomputes.
> The funding gap flips negative.
>
> Granite reads the analyst's own written rationale for this position and reports which
> stated assumption just broke. It is given the direction of the move, never the values,
> so it has nothing to echo and nothing to do arithmetic on. Any figure in its output
> that was not in its input discards the whole response.

**1:55 to 2:20, the human gate.**

> The analyst approves or rejects. The decision hash chains into the ledger.

Edit one byte of the ledger file on camera. Run `verify()`. It returns false.

> The thesis is never trusted. It is reviewable.

**2:20 to 2:50, the panel.**

> Every revision is timestamped, so we joined the revision panel to sponsor cash position
> across the sector. Here is the distribution.
>
> The open question is whether companies that cannot fund their way to a readout hold
> optimistic dates longer than solvent ones. We are not claiming that. Low runway
> correlates with small under resourced companies that slip anyway, and separating those
> needs a within firm design. There is adjacent published work on trial delays and firm
> incentives, and the revision data itself is public. What is ours is the monitor.

**2:50 to 3:00, the close.**

> Built with IBM Bob on watsonx and Granite. The registry is not a data source. It is a
> disclosure channel with incentives, and now it has an auditor.

---

## Cuts, if you run long

Drop in this order: the burn band explanation at 1:20, then the ledger tamper demo. Keep
the Rocket fact and the panel no matter what. Those are the two things the room has not
seen before.

## Do not

- Do not open on the dashboard.
- Do not claim the causal result.
- Do not say "no tool does this". BiopharmaWatch sells a runway filtered catalyst
  screener across 949 companies and a judge will find it. The honest line is that the
  screen is a product and the revision panel is not.
