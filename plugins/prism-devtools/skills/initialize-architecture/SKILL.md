---
name: initialize-architecture
description: Use to create complete architecture documentation structure. Creates all required architecture documents from templates.
version: 1.0.0
---

Creates complete architecture documentation from templates in `docs/architecture/`.

## Steps

1. Load config from `.prism/core-config.yaml`
2. Check existing docs status
3. Choose mode: create missing or recreate all
4. Generate documents from templates
5. Create master `README.md` index
6. Validate files and show next steps

See [instructions.md](./instructions.md) for templates and document details.
