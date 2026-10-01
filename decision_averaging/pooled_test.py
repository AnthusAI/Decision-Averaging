import asyncio

import pytest

from decision_averaging.harness.base import EngineAnswer
from decision_averaging.harness.record import read_record
from decision_averaging.harness.tasks import Task

from decision_averaging import analysis
from decision_averaging.pooled import PooledEngine, arm_k, make_engine, pool, rotations

OPTIONS = ["true", "false", "unknown"]


def slot(choice, **p):
    return {"type": "choice", "choice": choice, "probabilities": p}


def test_vote_and_mean_can_disagree():
    answers = [slot("false", true=0.1, false=0.5, unknown=0.4), slot("false", true=0.1, false=0.5, unknown=0.4),
               slot("unknown", true=0.0, false=0.1, unknown=0.9)]
    assert pool(answers, OPTIONS, "vote") == "false"
    assert pool(answers, OPTIONS, "mean") == "unknown"


def test_vote_tie_goes_to_higher_mean_probability_then_option_order():
    answers = [slot("true", true=0.5, false=0.1, unknown=0.4), slot("unknown", true=0.3, false=0.1, unknown=0.6)]
    assert pool(answers, OPTIONS, "vote") == "unknown"
    even = [slot("true", true=0.5, false=0.0, unknown=0.5), slot("unknown", true=0.5, false=0.0, unknown=0.5)]
    assert pool(even, OPTIONS, "vote") == "true"


def test_single_slot_is_its_own_answer():
    one = [slot("false", true=0.4, false=0.35, unknown=0.25)]
    assert pool(one, OPTIONS, "vote") == "false"      # the engine's own choice, even against its argmax
    assert pool([slot(None)], OPTIONS, "vote") is None


class Echo:
    name = "echo"

    def __init__(self):
        self.seen = []

    async def answer(self, text, questions):
        self.seen.append(dict(questions))
        return EngineAnswer(answers={n: slot("true", true=0.9, false=0.05, unknown=0.05) for n in questions},
                            model="echo-1", usage={"input_tokens": 100 * len(questions)})


def test_pooled_engine_sends_k_identical_copies():
    inner = Echo()
    result = asyncio.run(PooledEngine(inner, 3, "echo-k3").answer("t", {"Decision": {"type": "choice"}}))
    assert list(inner.seen[0]) == ["Decision_0", "Decision_1", "Decision_2"]
    assert len({str(q) for q in inner.seen[0].values()}) == 1
    assert len(result.answers) == 3


def test_end_to_end_scoring(tmp_path):
    import shutil
    shutil.copytree(analysis.ROOT / "tasks" / "proofwriter-cwa", tmp_path / "tasks" / "proofwriter-cwa")
    task = Task.load("proofwriter-cwa", root=tmp_path)
    items = task.load_items()[:20]
    from decision_averaging.harness import answering
    for k in (1, 3):
        for run in (1, 2):
            asyncio.run(answering.run(PooledEngine(Echo(), k, f"echo-k{k}"), task, items,
                                      analysis.record_path(f"echo-k{k}", run, task.slug, root=tmp_path)))
    assert len(read_record(analysis.record_path("echo-k3", 1, task.slug, root=tmp_path))) == 20
    rows = analysis.analyse(task, root=tmp_path)
    kinds = {r["kind"] for r in rows}
    assert {"accuracy", "paired", "retest", "slots", "cost"} <= kinds
    retest = next(r for r in rows if r["kind"] == "retest" and r["arm"] == "echo-k3")
    assert retest["agreement"] == 1.0
    paired = next(r for r in rows if r["kind"] == "paired" and r["axis"] == "overall")
    assert paired["diff"] == 0.0


QUESTION = {"type": "choice", "instructions": "Q?", "criteria": {"a": "A", "b": "B", "c": "C", "d": "D",
                                                                  "e": "E", "f": "F"}}


def test_rotations_space_shifts_evenly_and_keep_descriptions():
    versions = rotations(3)(QUESTION)
    assert [list(v["criteria"])[0] for v in versions] == ["a", "c", "e"]
    assert all(v["criteria"] == QUESTION["criteria"] for v in versions)   # same option -> description pairs
    three = {**QUESTION, "criteria": {"t": 1, "f": 2, "u": 3}}
    assert [list(v["criteria"]) for v in rotations(3)(three)] == [["t", "f", "u"], ["f", "u", "t"], ["u", "t", "f"]]


def test_paraphrase_arm_sends_each_wording_once_in_one_request():
    inner = Echo()
    engine = make_engine("echo-para3", inner, ["one", "two", "three", "unused"])
    asyncio.run(engine.answer("t", {"Decision": QUESTION}))
    assert len(inner.seen) == 1
    assert [q["instructions"] for q in inner.seen[0].values()] == ["one", "two", "three"]


def test_arm_names():
    assert arm_k("jev-k10") == 10 and arm_k("jev-perm3") == 3
    for bad in ("jev-3", "jev-vote3", "jev-sep3", "k3"):
        with pytest.raises(ValueError):
            arm_k(bad)
    with pytest.raises(ValueError):
        make_engine("jev-para3", Echo(), ["only one"])


def test_multi_rater_ac1_matches_two_rater_ac1_and_rewards_agreement():
    from decision_averaging.harness.agreement import coefficients
    from decision_averaging.stability import multi_rater
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("c", "c"), ("a", "a")]
    two = coefficients(pairs, ["a", "b", "c"])
    multi = multi_rater([list(p) for p in pairs], ["a", "b", "c"])
    assert abs(multi["agreement"] - two["agreement"]) < 1e-12 and abs(multi["ac1"] - two["ac1"]) < 1e-12
    assert multi_rater([["a"] * 5, ["b"] * 5], ["a", "b"])["ac1"] == 1.0
    assert multi_rater([["a", "a", "a", "a", "b"]], ["a", "b"])["agreement"] == 0.6   # 12 of 20 ordered pairs


def test_stability_scores_runs_three_to_seven_only(tmp_path):
    import shutil
    from decision_averaging import stability
    shutil.copytree(analysis.ROOT / "tasks" / "proofwriter-cwa", tmp_path / "tasks" / "proofwriter-cwa")
    task = Task.load("proofwriter-cwa", root=tmp_path)
    items = task.load_items()[:10]
    from decision_averaging.harness import answering
    for k in (1, 2):
        for run in (1, 3, 4):
            asyncio.run(answering.run(PooledEngine(Echo(), k, f"jev-k{k}"), task, items,
                                      analysis.record_path(f"jev-k{k}", run, task.slug, root=tmp_path)))
    rows = stability.analyse(task, root=tmp_path)
    main = [r for r in rows if r["kind"] == "stability"]
    assert {r["arm"] for r in main} == {"jev-k1", "jev-k2"} and all(r["runs"] == [3, 4] for r in main)
    assert all(r["ac1"] == 1.0 and r["changed"] == 0 for r in main)
    assert any(r["kind"] == "stability_paired" and r["ac1_diff"] == 0.0 for r in rows)
