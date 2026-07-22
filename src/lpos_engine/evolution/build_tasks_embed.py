"""Generate the reviewed CS-001 task file. Ground truth (`expected`) is computed
by the shipped scorer, so the tasks can never drift from the rules they test.
Run once from the repo root: python src/lpos_engine/evolution/build_tasks_embed.py
"""
import json, pathlib
from lpos_engine.evolution.scorer import real_violations

TEXTS = [
    "Our platform is fast and clear — you will notice the difference immediately.",
    "We ship weekly — every release is reviewed before it goes out.",
    "Try it today and see the results!",
    "This is the best launch we have ever done!",
    "A seamless, effortless way to unlock your team's potential.",
    "Supercharge your workflow and elevate every result.",
    "We empower operators with robust, cutting-edge tooling.",
    "1 coordinator, 32 specialists, 37 guilds, 21 operations.",
    "3 plans, 4 tiers, 12 integrations, 99 happy teams.",
    "This is not just a tool, it's a whole operating system.",
    "It is not just faster but smarter in every way.",
    "Faster, smarter, and cleaner than anything you have used.",
    "Simple, reliable, and honest software for real teams.",
    "Not just seamless — it's revolutionary!",
    "Unlock 3 new tiers, 5 workflows, and 9 templates today!",
    "We built this because our own assistant kept shipping work nobody had checked.",
    "Now every piece of work gets a second set of eyes before you see it.",
    "You get one short email when something needs your decision.",
    "Reply by email, on desktop, or in chat, whichever is easiest.",
    "The system keeps a record of what it did and why.",
    "Pricing stays the same on your existing plan.",
    "Ask us anything and a person will get back to you within a day.",
    "It runs quietly and stays out of your way until it matters.",
    "Delve into the data and unlock hidden value.",
    "A game-changing, cutting-edge approach to operations!",
    "10 reasons, 5 benefits, 3 guarantees, 1 decision.",
    "Not just a dashboard, it's mission control for your day.",
    "Bold, clear, and confident writing that sounds human.",
    "Effortless onboarding — supercharge day one!",
    "We measure outcomes, not activity, on every engagement.",
]
tasks = [{"id": f"CS001-{i:03d}", "text": t, "expected": sorted(real_violations(t))}
         for i, t in enumerate(TEXTS)]
out = pathlib.Path(__file__).resolve().parent / "data" / "cs001_tasks.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(tasks, indent=1))
print(f"wrote {len(tasks)} tasks to {out}")
