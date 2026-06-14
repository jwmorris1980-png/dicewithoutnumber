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
