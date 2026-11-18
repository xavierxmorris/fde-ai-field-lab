# Breakwater: start here

Start with section 2 of the [field guide](plan.md) for a 45-minute paper exercise. You can also use the [printable PDF](Breakwater-field-guide.pdf) or open [the HTML edition](plan.html) in a browser after cloning. Draft the three incident briefs, then use the [step-by-step solution](SOLUTION.md) to check which evidence supports each claim. The 12-week project is to evaluate and improve a system under realistic evidence and review constraints, not just to reproduce the three briefs.

The starter is local, read-only and dependency-free (Python 3.11+). Run these commands from `labs/breakwater`, the directory containing `desk.py`:

```shell
python desk.py brief 08:25
python desk.py search 08:25 "gateway recovered"
python desk.py brief 08:55
python desk.py brief 09:10
python -m unittest -v test_desk
```

`case.json` is the synthetic manifest. `observed` and `received` are UTC minutes on the single case date. The fixture register contains only approved policies; publication and effective dates have day precision and start at 00:00 UTC. Change a copy for experiments. `search` searches the eligible *archive*, including historical notes: a match is not necessarily the newest version or a verified fact. `brief` resolves eligible authoritative evidence independently of search. It does not write or send anything.

**Starter limitations:** no authentication, ingestion of untrusted data, real signing or source verification, cloud model, append-only store, reviewer UI or reporting integration. Identity, source labels, batch membership and approval are simulated in a trusted, editable file. No enforcement can protect a local file from someone who already has it. Do not feed real incident data into the lab. Bring your own frozen **synthetic** evaluation incidents in week 9; the supplied tests and workshop are not a production benchmark.
