Blocked: 2026-09-19
Missing: a write-scoped HF_TOKEN in .env (currently role:"read", verified via a live
  GET /api/whoami-v2 call, not assumed) — needed for `--push` to upload the merged
  model to the Hub, which is what OUTCOME requires (EXPORT.json naming a Hub repo and
  commit).
Done before stopping: training/export.py written and working (fp16 merge, per-prompt
  self-check, reverse control run and kept red in NOTES.md); real run against
  training/output completed locally — self-check passed (max|adapter-merged|=0.039062
  < 0.05), model saved to /home/alter/qwen/models-new/merged_v1/ (16 GB, fp16),
  tasks/10-serving/01-merged-export/EXPORT.json written with adapter/base/self-check/
  file hashes and versions (hub_repo_id and hub_commit are null, pending push). Project
  gate green (208 tests, coverage 100%).
What can be done without it: nothing more on this task — OUTCOME is specifically the
  Hub repo+commit. The next step the moment a write-scoped token exists: re-run
  `python3 training/export.py --adapter training/output --out /home/alter/qwen/models-new/merged_v1
  --manifest tasks/10-serving/01-merged-export/EXPORT.json --push <hf-user>/tonofdevelopervoice-qwen3-8b-v1-merged`
  (the local artifact is already correct, so this only needs to redo the ~16 GB upload,
  not the merge) and hand the resulting EXPORT.json to the verifier for VERIFY items
  2-3.
