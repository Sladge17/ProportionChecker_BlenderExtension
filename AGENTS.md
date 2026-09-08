# AGENTS.md

## Status

This repository is a fresh, empty project ("ProportionChecker") — a greenfield Blender
add-on built with the `bpy` Python library. There is currently:

- No source files, manifests, or configuration of any kind.
- No commits on `master` (the git repo is initialized but has no history).
- No build, test, lint, or CI tooling set up.

## Project intent

- Purpose: a Blender add-on for checking proportions (name suggests checking/
  validating proportions of objects or meshes).
- Stack: Python using the `bpy` library. The add-on will run inside Blender's
  bundled Python interpreter.

## For agents

- Target environment is Blender's embedded Python, not a standalone interpreter —
  `bpy` is only available when the code runs inside Blender (or via
  `blender --background` / `--python`). Do not run add-on code with a plain
  `python` interpreter.
- Before writing code, consider how it will be installed/tested:
  `blender --background --python-expr` for headless scripted testing, or installing
  the add-on via `Edit > Preferences > Add-ons` for interactive use.
- There are no existing conventions to preserve; anything created here is greenfield.
- If the intended layout, add-on registration approach, or target Blender version
  matters, ask the user before proceeding.
