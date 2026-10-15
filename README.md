# VerdiDeck

**Your AiiDA workspace, one terminal away.**

Browse processes, inspect results, and check your AiiDA environment without repeatedly rebuilding the same `verdi` commands. VerdiDeck is a keyboard-driven terminal interface that keeps lists, details, and status together in one view.

Built for researchers and developers who already use AiiDA and want a faster way to look around.

## Why try it?

- **Keep context while you explore.** Move between processes, nodes, groups, computers, codes, and profiles without losing the surrounding view.
- **Stay on the keyboard.** Use familiar navigation keys, numbered panels, and quick refresh controls.
- **Keep the interface responsive.** Commands run asynchronously; configurable auto-refresh keeps the view current.
- **Use the environment you already have.** VerdiDeck runs alongside AiiDA and reads its existing profiles and configuration.

## Try it in your AiiDA environment

**Requirements:** Python **3.9+** and AiiDA **1.6.9–2.x** (`aiida-core>=1.6.9,<3.0`). Activate the environment where your AiiDA installation and profile already work.

Install and launch:

```sh
python -m pip install verdideck
verdideck
```

If you have not set up AiiDA yet, configure it first using the [AiiDA documentation](https://aiida.readthedocs.io/projects/aiida-core/en/stable/intro/get_started.html). VerdiDeck does not provision a database or create a profile for you.

To try the latest source instead:

```sh
python -m pip install "git+https://github.com/DeeliN221/verdideck.git"
verdideck
```

## Your first minute

1. Press **2** to focus the process/calculation panel.
2. Move with **j/k** and inspect the selected item in the details panel.
3. Use **[ / ]** to switch tabs, **r** to refresh, and **a** to toggle auto-refresh.
4. Press **?** for shortcuts and **q** to quit.

| Key | Action |
| --- | --- |
| `0` | Focus results/details |
| `1` | Computers, codes, plugins |
| `2` | Processes, CalcJobs |
| `3` | Groups, nodes |
| `4` | Configuration, profiles |
| `5` | Status |

## Scope

VerdiDeck focuses on **query and inspection commands** such as list, show, and status. It does not replace the full `verdi` CLI or support every interactive command. Keep a regular terminal available for workflow submission and administrative tasks.

Compatibility behavior is documented in [docs/compatibility.md](docs/compatibility.md).

## Make it yours

New installations use `~/.config/verdideck/config.yaml`. Set your preferred Textual theme, panel proportions, auto-refresh interval, line numbers, and wrapping. A non-positive refresh interval disables periodic refresh.

```yaml
theme: monokai
auto_refresh_interval: 10
auto_refresh_on_startup: true
left_panel_width_percent: 40
show_line_numbers: false
soft_wrap: true
```

### Coming from lazyverdi?

VerdiDeck is the renamed successor to lazyverdi. If you already have `~/.config/lazyverdi/config.yaml` and no VerdiDeck configuration, that existing file is reused. Your AiiDA data and profiles are not moved or reset. The package, Python module, and command are now **`verdideck`**.

## Development and feedback

```sh
git clone https://github.com/DeeliN221/verdideck.git
cd verdideck
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run mypy src
```

Found a command that does not display correctly? [Open an issue](https://github.com/DeeliN221/verdideck/issues) with your AiiDA version, operating system, and a small example with private data removed. Suggestions from real research workflows are especially welcome.

Inspired by [lazygit](https://github.com/jesseduffield/lazygit) and [lazydocker](https://github.com/jesseduffield/lazydocker). VerdiDeck is an independent project, not an official AiiDA distribution.

Licensed under [MIT](LICENSE).
