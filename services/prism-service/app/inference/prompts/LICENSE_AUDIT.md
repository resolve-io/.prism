# License Audit — Understand-Anything Port

**PRISM task:** [5.1-T1] License audit on UA prompts before porting
**Story:** `docs/stories/5.1.understand-anything-integration.md`
**Auditor:** claude-opus-4-7
**Audit date:** 2026-05-20

## Upstream

- **Repository:** [Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything)
- **Pinned commit:** `57a25ed4aaca8a116a6f6e011a578985c18e78c6`
- **Default branch:** `main`
- **License SPDX:** `MIT`
- **License blob SHA:** `87c7ab246cd64adb13e92db3a80cefebfdee298a`

## License (verbatim)

```
MIT License

Copyright (c) 2026 Yuxiang Lin

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject
to the following conditions:
```

```
The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Verdict

**PASS** — MIT is permissive, compatible with PRISM's distribution
model, and explicitly allows verbatim derivative work with
attribution.

## Per-analyzer decision

| Analyzer                | UA source path                                              | Decision        |
|-------------------------|-------------------------------------------------------------|-----------------|
| `tour_builder`          | `understand-anything-plugin/agents/tour-builder.md`         | verbatim-port   |
| `architecture_analyzer` | `understand-anything-plugin/agents/architecture-analyzer.md`| verbatim-port   |
| `domain_analyzer`       | `understand-anything-plugin/agents/domain-analyzer.md`      | verbatim-port   |
| `onboarding_writer`     | *no UA counterpart*                                         | PRISM-original  |

## Attribution requirements

For each ported prompt file (`tour_builder.md`,
`architecture_analyzer.md`, `domain_analyzer.md`), the YAML
frontmatter MUST include:

```yaml
source:
  upstream: Lum1104/Understand-Anything
  upstream_path: understand-anything-plugin/agents/<name>.md
  upstream_sha: 57a25ed4aaca8a116a6f6e011a578985c18e78c6
  license: MIT
  copyright: Copyright (c) 2026 Yuxiang Lin
```

The `onboarding_writer.md` prompt is a PRISM-original; it carries
no upstream attribution. Its frontmatter sets `source: prism-original`.

A copy of the upstream MIT text is reproduced verbatim above in
this audit file; the audit itself satisfies the MIT requirement
that "the above copyright notice and this permission notice shall
be included" in copies of substantial portions.

## Gate status

✅ T1 PASS — T7 (port prompts) is unblocked.
