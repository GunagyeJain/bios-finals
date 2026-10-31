# Eval labels

Hand labels for the metrics (A5). Coordinates only, never images. Format: `docs/05-solution/data-schema.md` §2.

- `<clip>__<labeller>.json`: one file per clip and labeller, written by the label tool.
- `shared/<clip>.json`: frame list of the common 30-frame set (`--shared`), so every labeller gets the same frames.

Label: `python -m egovision.eval.label_tool --clip <clip> --labeller <firstname> --n 40`
(how-to at the top of `src/egovision/eval/label_tool.py`). Window ignores keys or clicks? Add `--web` and open http://localhost:8765. Frame images go to `eval/frames/`, which is git-ignored.
