---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# A small reproducible exercise

Read the [relative asset](asset.txt). Café, λ and 東京 survive conversion.

```python tags=["exercise"]
from pathlib import Path
assert Path("asset.txt").read_text().strip() == "fixture input"
values = [2, 3, 5]
assert sum(values) == 10
print("total=10")
```

```python .noeval
raise RuntimeError("illustration only; never execute")
```

```python tags=["solution-only"]
assert sum([7, 11]) == 18
```

<!-- #region purpose="reflection" -->
Predict what changes when a new value is added, then explain the observed total.
<!-- #endregion -->
