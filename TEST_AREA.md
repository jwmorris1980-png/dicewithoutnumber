# Local Test Area

All new features must pass the isolated local test area before production deployment:

```powershell
python scripts/test_area.py
```

The test area:

- disables the Discord production token;
- uses a temporary directory and temporary database path;
- compiles bot, cog, service, and script code;
- runs the complete automated test suite;
- blocks `deploy.py` when any check fails.
- blocks direct Git pushes after running `python scripts/install_test_gate.py`.

Add or update a test for every new feature or bug fix. This is the first testing
layer. Features that require real Discord interaction still need a separate
staging Discord application before they can be live-tested without affecting
production servers.

## Required Release Order

1. Run and pass the isolated local test area.
2. Enable the new feature only in the designated Games Without Number test
   server (`1437247431560400928`) and wait for the owner to verify it.
3. Release the feature to all servers only after the owner explicitly approves
   the global release.

Never treat a successful local test or test-server deployment as approval to
release a feature globally.

## Verified Map Library

Run `python scripts/build_verified_map_library.py` to rebuild the reviewed map
manifest. An accepted map must be a direct bitmap, have a source page and
explicit reusable-license metadata, and identify the requested map subject in
its title. Collection pages and personal-use-only images are excluded.
