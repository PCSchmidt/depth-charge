"""The playable client: server API, the coach, and that the guided dive is winnable with the client's coarse controls."""
import json
import threading
import urllib.request

import pytest

from depthcharge.play.server import App, serve
from depthcharge.play.session import PRACTICE, new_session


def keyboard_player(st, mem):
    """A proxy for a human on the client's controls: kick / hard kick / nothing, plus the pulse keys."""
    o, sc = st["observation"], st["scenario"]
    z, v, D = o["depth_m"], o["vertical_speed_mps"], sc["announced_depth_m"]
    ch = {}
    if o["surfaced"]:
        ch.update({"breathe": True, "f": 0.0, "a": 0.0})
        nxt = o["protocol_next"]
        if nxt and o["t"] - mem.setdefault("last", o["t"]) >= 2.0:
            ch[nxt] = True
            mem["last"] = o["t"]
        return ch
    if z > 0.5 and 0.04 <= o["ear_excess"] <= 0.11 and not o["turning"]:
        ch["equalize"] = True
    if not o["has_tag"]:
        ch["dir"] = 1
        if z >= D - 0.4:
            ch.update({"grab_tag": True, "f": 0.0, "a": 0.0})
        else:
            err = 0.75 - v
            ch.update({"f": 0.8, "a": 1.0 if err > 0.5 else 0.7} if err > 0.0 else {"f": 0.0, "a": 0.0})
    else:
        ch["dir"] = -1
        err = 0.75 + v
        ch.update({"f": 0.8, "a": 0.7} if err > 0.0 and not o["turning"] else {"f": 0.0, "a": 0.0})
    return ch


def play(app, new_body):
    status, st, _ = app.handle("POST", "/api/new", new_body)
    assert status == 200 and st["ghost"]
    mem, titles = {}, []
    for _ in range(4000):
        if st["observation"]["ended"]:
            break
        if "coach" in st and (not titles or titles[-1] != st["coach"]["title"]):
            titles.append(st["coach"]["title"])
        status, st, _ = app.handle("POST", "/api/step", {"n": 2, "change": keyboard_player(st, mem)})
        assert status == 200
    return st, titles


def test_guided_dive_is_winnable_on_the_clients_controls_and_the_coach_walks_through_every_stage():
    st, titles = play(App(), {"guided": True})
    assert st["debrief"]["outcome"] == "success" and st["debrief"]["verified"]
    for stage in ("1. Dive", "Equalize", "3. Reach the tag", "4. Turn", "Surface protocol"):
        assert stage in titles, titles
    assert titles.index("1. Dive") < titles.index("3. Reach the tag") < titles.index("4. Turn") < titles.index("Surface protocol")


def test_unguided_dive_has_no_coach_and_oxygen_is_hidden_until_the_end():
    app = App()
    status, st, _ = app.handle("POST", "/api/new", {"archetype": "elite", "depth": 25, "lead": 1.2, "seed": 4})
    assert "coach" not in st and "debrief" not in st
    assert not {"o2", "co2", "pao2", "o2_ml", "pao2_atm"} & set(json.dumps(st))
    st, _ = play(app, {"archetype": "elite", "depth": 25, "lead": 1.2, "seed": 4})
    assert "samples" in st["debrief"] and st["debrief"]["samples"]


def test_bad_requests_are_rejected_and_the_replay_is_withheld_until_the_end():
    app = App()
    assert app.handle("POST", "/api/step", {})[0] == 409
    assert app.handle("POST", "/api/new", {"depth": 99})[0] == 400
    app.handle("POST", "/api/new", {"guided": True})
    assert app.handle("POST", "/api/step", {"n": 1, "change": {"warp": 1}})[0] == 400
    assert app.handle("GET", "/api/replay", {})[0] == 403


def test_http_server_serves_the_page_and_a_dive():
    srv = serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    page = urllib.request.urlopen(base + "/").read().decode()
    assert "Guided practice dive" in page
    req = urllib.request.Request(base + "/api/new", data=b'{"guided": true}', method="POST", headers={"Content-Type": "application/json"})
    assert json.loads(urllib.request.urlopen(req).read())["coach"]["title"]
    srv.shutdown()


def test_practice_scenario_is_the_documented_one():
    s = new_session(guided=True)
    assert (s.sc.announced_depth_m, s.sc.archetype) == (PRACTICE["announced_depth_m"], PRACTICE["archetype"]) and s.guided
    assert 9.0 < s.neutral_m < 12.0
