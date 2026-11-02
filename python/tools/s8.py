"""S8: 5,000 dives, each simulated directly, replayed from its log, and again in a separate worker process.

    python tools/s8.py --n 5000 --out ../docs/spike-results/S8.json
"""
import argparse
import json
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from depthcharge.bots import ScriptedDiver  # noqa: E402
from depthcharge.dive import Scenario, replay, run  # noqa: E402


def spec(i):
    r = random.Random(900000 + i)
    arch = r.choice(["novice", "trained", "elite"])
    depth = r.uniform(8, 30 if arch == "novice" else 40)
    return dict(seed=r.randrange(1 << 30), archetype=arch, announced_depth_m=round(depth, 1), lead_kg=round(r.uniform(0.0, 3.0), 2),
                dt=r.choice([0.05, 0.05, 0.02]), bot=dict(descent_mps=round(r.uniform(0.4, 1.1), 2), ascent_mps=round(r.uniform(0.4, 1.1), 2)))


def play(i):
    s = spec(i)
    sc = Scenario(**{k: v for k, v in s.items() if k != "bot"})
    d = run(sc, ScriptedDiver(sc.announced_depth_m, **s["bot"]))
    return i, d.digest(), d.outcome, d.log


def direct_and_replay(i):
    i, dig, out, log = play(i)
    sc = Scenario(**{k: v for k, v in spec(i).items() if k != "bot"})
    return i, dig, out, replay(sc, log).digest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="../docs/spike-results/S8.json")
    a = ap.parse_args()
    t0 = time.time()
    ids = list(range(a.n))
    with ProcessPoolExecutor(a.workers) as ex:
        main_rows = [direct_and_replay(i) for i in ids[:50]]           # this process
        worker_rows = list(ex.map(direct_and_replay, ids, chunksize=25))  # other processes
        again = {r[0]: r[1] for r in ex.map(play, ids, chunksize=25)}   # a second worker pass of the direct run
    by_main = {r[0]: r for r in main_rows}
    bad_replay = sum(1 for _, dig, _, rep in worker_rows if dig != rep)
    bad_proc = sum(1 for i, dig, _, _ in worker_rows if again[i] != dig) + sum(1 for i, r in by_main.items() if r[1] != worker_rows[i][1])
    outcomes = {}
    for _, _, o, _ in worker_rows:
        outcomes[o] = outcomes.get(o, 0) + 1
    res = {"dives": a.n, "replay_mismatches": bad_replay, "cross_process_mismatches": bad_proc, "outcomes": outcomes,
           "python": sys.version.split()[0], "seconds": round(time.time() - t0, 1)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res)


if __name__ == "__main__":
    main()
