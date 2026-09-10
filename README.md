# skills

A Claude Code plugin holding my personal skills.

## Install

```bash
/plugin marketplace add ntotten/skills
```

```bash
/plugin install ntotten-skills@ntotten-skills
```

## Skills

| Skill | What it does |
| ----- | ------------ |
| [`delegate-to-kimi`](skills/delegate-to-kimi/SKILL.md) | Hands a self-contained task to Kimi K3 on Fireworks AI, then applies the result locally. |

### `delegate-to-kimi`

Claude gathers the context and writes the prompt, Kimi K3 does the generation,
Claude reviews and applies the result. Kimi has no filesystem access — it returns
text, it never edits the repo.

Needs a Fireworks API key, either in the environment:

```bash
export FIREWORKS_API_KEY=fw_...
```

…or via the plugin's `FIREWORKS_API_KEY` user config, which Claude Code prompts
for when the plugin is enabled. Get a key at
<https://fireworks.ai/account/api-keys>.

The script is stdlib-only Python 3 and runs standalone:

```bash
python3 skills/delegate-to-kimi/scripts/kimi.py \
  --prompt "Summarize the public API of this module as a markdown table." \
  --file src/parser.py
```

`--help` lists every flag.

## Layout

```
.
├── .claude-plugin/
│   ├── marketplace.json    # so the repo can be added as a marketplace
│   └── plugin.json         # the plugin manifest
├── skills/
│   └── delegate-to-kimi/
│       ├── SKILL.md
│       ├── references/fireworks-api.md
│       └── scripts/kimi.py
└── LICENSE
```

To add a skill, create `skills/<name>/SKILL.md` with `name` and `description`
frontmatter; it is picked up automatically. Bump `version` in both
`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` to release it.

## License

MIT
