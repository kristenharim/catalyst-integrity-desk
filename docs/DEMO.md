# Demo script, three minutes

Runs from a frozen local snapshot. Network off. Backup video recorded.

**Reset before every take**, or the ledger carries decisions from the last one and the
receipt shows a chain you did not just build:

```bash
rm -f data/decisions.jsonl data/review_log.jsonl data/ledger.anchor
python3 -m console.app
```

**Say "registered primary completion" out loud, never "catalyst date" and never
"readout".** They differ by two to four months and the gap is always optimistic. The
distinction is a credibility advantage and the first thing a domain judge tests.

The structure is deliberate: open on a fact nobody in the room knows, show the machine
catching it, hand the decision to a human, then prove the record cannot be quietly
rewritten. The reveal comes before the product, because a product demo that opens on a
dashboard has already lost the room.

Every figure below is in `data/snapshot.json`. If a rebuild moves one, re-read this file
before filming.

---

**0:00 to 0:20, the hook.**

> Every biotech thesis rests on a date. They have cash into Q1 2028, the trial completes in
> Q3 2027, therefore they are funded to their catalyst and do not need to raise.
>
> The left side of that sentence comes from SEC filings. The right side comes from
> ClinicalTrials.gov, where the company sets it, can change it whenever it likes, and
> nothing reconciles that change against the thesis that depended on the old date.

**0:20 to 0:50, the fact.**

The console opens on Rocket. Do not click anything yet.

> Here is a real trial. In April 2024, Rocket filed a protocol revision carrying a primary
> completion date of June 2022. That date had already passed, six hundred and seventy seven
> days earlier, and it sat on the public registry the entire time.
>
> No press release. No 8-K. Nothing in the thesis that depended on it moved.

Then the second red node, on the trial above it:

> And this is not a one-off. The trial that replaced it did the same thing on a smaller
> scale, carrying an expired date for thirty days after moving it out by nine hundred and
> forty three.

**0:50 to 1:25, the contract.**

Scroll to the gap table.

> So we treat the catalyst as a contract: this company has capital to reach this completion
> by this date. Runway comes from XBRL tags, and every figure names the tag it came from.
> The completion date comes from the sponsor's own filing with its full revision history
> attached. Python computes both sides. No model touches a number.

Point at the burn band, then at the flagged row on the contract list.

> Burn is a range, not a point, because a partnership upfront makes one quarter
> unrepresentative. Sarepta is on screen and has no rank, with the reason attached: a
> cash-positive quarter in the trailing window that we do not trust as burn. Rows we cannot
> rank stay visible. A screen that hides its hard cases is worse than one that shows them.

**1:25 to 2:05, the break. This is the centre of the demo.**

Open the pending redline. Read the three columns left to right.

> The thesis was approved against that first trial, completion May 2026, and it gave a
> funding gap of plus eight point four months. Funded to catalyst.
>
> Then nothing happened. Nobody filed an amendment. The date simply arrived, and passed.
>
> A lapsed date is not a catalyst, because you cannot run out of money before an event that
> already happened. So the binding catalyst becomes the next registered completion still in
> the future, April 2028, and against that the same cash gives minus fourteen point five
> months. Financing required.
>
> The company did not change. The filing did not change. The thesis broke because time
> passed and nobody was watching.

Then the memo.

> Granite reads the analyst's own written rationale and reports which stated assumption
> broke. It is given the direction of the move, never the values, so it has nothing to echo
> and nothing to do arithmetic on. Any figure in its output that was not in its input
> discards the whole response.

**2:05 to 2:20, where the belief came from.** Cuttable. See the run-long list.

Open `/belief/new`. Do not fill it in on camera, just show it and move.

> One question this has been begging: judged against what? Against this. A human writes the
> thesis, the trial it depends on, and the funding gap below which they would no longer
> believe it. The desk does not invent beliefs, it monitors the ones someone signed.
>
> The invalidation conditions go in the same field Granite reads, so the challenge is
> judged against the conditions the analyst said would change their mind.

**2:20 to 2:50, the human gate and the record.**

> The analyst accepts or rejects. Nothing is automatic.

Click Accept. The receipt appears.

> The decision hash-chains into the ledger. Who decided, what changed, the resulting thesis
> state, the previous hash and the new one, all read back out of the ledger itself.

Now break it on camera, twice.

> Edit one byte of the ledger file.

Reload. The badge reads tampered.

> Fine, so delete the whole entry instead.

Delete the last line, reload. The badge reads truncated or replaced.

> A hash chain on its own only proves the chain you are looking at is self-consistent. It
> cannot tell you an entry was removed. So the head hash and the entry count are recorded
> outside the chain, and the page checks both. Delete the anchor too and it still refuses
> to say intact.

**2:50 to 3:00, the close.**

> Four contracts monitored. Two active breaches. Three registered completion dates already
> lapsed. This is not a screen that ranks companies, it is a queue of beliefs that need an
> analyst today.
>
> Built with IBM Bob on watsonx and Granite. The registry is not a data source. It is a
> disclosure channel with incentives, and now it has an auditor.

---

## If you run long

Drop in this order:

1. The belief form at 2:05. It answers a question a judge may not have asked yet, and the
   receipt at 2:20 already shows a human in the loop. Cut this first, because it is the only
   beat where nothing is wrong on screen.
2. The second red node at 0:40, the thirty-day one. The 677 carries the point alone.
3. The burn band explanation at 1:10.
4. The second ledger break at 2:30, the deletion. Keep the byte edit.

**Never cut:** the 677 fact, and the lapse at 1:25. Those are the two things the room has
not seen before, and the second one is the only demo where a thesis breaks because nobody
did anything.

## What already exists

Put this in the deck, visible, before Q&A. Naming your own priors reads as confidence.
Having them named for you reads as unaware.

| Layer | Who owns it |
|---|---|
| The screen: rank companies by runway against catalyst | [BiopharmaWatch Catalyst Sync](https://www.biopharmawatch.com/catalyst-sync), 11,000+ readouts filtered by cash runway and burn across 949 companies, including a trial-change field |
| Catalyst calendars and analyst-adjusted dates | [Biomedtracker / Citeline](https://www.evaluate.com/solutions/biomedtracker/), [BioPharmCatalyst](https://www.biopharmcatalyst.com/calendars/fda-calendar) |
| Sector runway aggregates | EY Beyond Borders, 33% of public biotechs under one year of runway at end 2025; Stifel publishes weekly |
| The per-version registry panel | [brbk/clinical_trials_history](https://huggingface.co/datasets/brbk/clinical_trials_history), 4,333,631 rows across ~583,000 trials, `primary_completion_date` per version, CC-BY-NC-4.0 |
| Registry-derived dates used to study firm behaviour | [Guenzel & Liu, *Excess Commitment in R&D*, RFS 39(7) 2026](https://doi.org/10.1093/rfs/hhag026) |
| Trial delay base rates | [Shadbolt et al., *JAMA Netw Open* 2023](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2800488): about 1 in 5 RCTs complete on time, median delay 12.2 months |
| Biotech financing cycles | [Lerner, Shane & Tsai, *JFE* 2003](https://www.sciencedirect.com/science/article/abs/pii/S0304405X02002568) |

Then one line, spoken:

> None of that is what we built. What we built is the monitor: the contract that gets
> recomputed when one of those inputs changes, judged against the rationale someone
> actually wrote down, and changed only by a human whose decision is hash chained.

## Q&A one-liners

Rehearse these. Each is under fifteen seconds.

**"Isn't this BiopharmaWatch?"**
Their screen is better than ours and larger. A screen tells you the gap today. It does not
hold a written thesis, detect when a registry change breaks it, or record who decided what.
That is the difference between a filter and a monitor.

**"Guenzel and Liu already did this."**
They ran the opposite arrow: delay causing firms to keep funding projects, moderated by CEO
pay. Ours is firm liquidity possibly affecting how a date gets disclosed. Their paper is why
we know the measurement works, and we cite it.

**"So what is new?"**
Honestly, the monitor, and one narrow open question about disclosure behaviour that we have
not tested and are not claiming.

**"Isn't primary completion just the readout?"**
No, and that is a systematic bias rather than noise. It is last patient last visit for the
primary endpoint; topline follows by weeks to months. Every gap we show is optimistic by
roughly two to four months, uniformly.

**"Your burn number is wrong for the interesting companies."**
Yes. That is why it is a band and why unrankable rows are shown but never ranked. Sarepta is
on screen doing exactly that.

**"Couldn't you just delete the ledger entry?"**
We tried, and the plain hash chain did not notice. That is why the head hash and entry count
now live outside the chain. It detects deletion and replacement, given the anchor was not
also rewritten. Tamper evident, not immutable, and `docs/LIMITS.md` says so in those words.

**"How do you know Granite actually ran?"**
Point the endpoint at an invalid host and the live test fails rather than passes, because it
asserts the classification came from Granite and not from the stub fallback.

**"Only four companies?"**
Four contracts in the frozen demo snapshot. The engine runs twelve, and the join to SEC
filers is the honest bottleneck: sponsor names are free text with no identifier, so a
universe run needs an alias table and hand review of the largest names.

## Do not

- Do not open on the dashboard.
- Do not claim the causal result.
- Do not say "no tool does this". BiopharmaWatch sells a runway-filtered catalyst screener
  across 949 companies and a judge will find it.
- Do not say "immutable" or "append-only" about the ledger. Say tamper evident.
- Do not rebuild the snapshot before filming. It calls Granite and it can move the figures
  this script quotes.
