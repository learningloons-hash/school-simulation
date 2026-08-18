# MemBench fixture subset (Senna iter-46)

Vendored test fixtures derived from [MemBench](https://github.com/import-myself/Membench) (ACL 2025 Findings).

## Source

| Field | Value |
|-------|--------|
| Repository | https://github.com/import-myself/Membench |
| Pinned commit | `f66d8d1028d3f68627d00f77a967b93fbb8694b6` |
| License | MIT (see below) |

## Subset taken

One trimmed trajectory per MemBench scenario × memory-level cell (four JSON files):

| File | MemBench scenario | Memory level | Source path in upstream repo |
|------|-------------------|--------------|------------------------------|
| `participation_factual.json` | Participation (first-person) | Factual (low-level) | `MemData/FirstAgent/simple.json` |
| `participation_reflective.json` | Participation | Reflective (high-level) | `MemData/FirstAgent/highlevel.json` (movie) |
| `observation_factual.json` | Observation (third-person) | Factual | `MemData/ThirdAgent/simple.json` |
| `observation_reflective.json` | Observation | Reflective | `MemData/ThirdAgent/highlevel.json` (movie) |

Each trajectory retains MemBench `QA` fields (`question`, `choices`, `ground_truth`, `target_step_id`, …) and the first four normalized `message_list` turns for offline CI.

## MIT License Notice

Copyright (c) MemBench authors (see upstream repository for contributor list)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
