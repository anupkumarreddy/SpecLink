# SpecLink

SpecLink is a Django monolith for DV verification closure. It maps specification requirements to tests, checks, simulation evidence, and regression runs so a team can prove which requirements are closed, partial, failed, or still open.

The MVP uses a vendor-agnostic evidence protocol: SpecLink generates a SystemVerilog package with runtime APIs such as `pass_check`, `fail_check`, and `hit_check`. Simulations print a machine-readable summary block, a Python parser converts logs to evidence JSON, and the Django app ingests that evidence to recompute closure.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install django
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_speclink_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

`seed_speclink_demo` creates an AXI demo project with requirements, tests, checks, mappings, a processed regression run, closure evidence, and a generated package. It is safe to rerun.

This first version loads Tailwind CSS and Preline UI from public CDNs in the base template. A local Node/Tailwind build pipeline can be added later when the frontend asset policy is finalized.

## Core Workflow

1. Create a project from the Projects page.
2. Add requirement categories in Django admin.
3. Add requirements from the Requirements page or admin.
4. Add tests from the Tests page.
5. Add checks from the Checks page.
6. Map requirements to tests and checks from the Mappings page.
7. Generate and download the SystemVerilog package from Generate SV.
8. Instantiate `speclink_top` in the testbench.
9. Mark checks from scoreboard, assertions, comparisons, monitors, or callbacks:

```systemverilog
speclink_top slink;

initial begin
  slink = new();
  fork
    slink.run();
  join_none
end

slink.pass_check("AXI-AW-001", "AWADDR_STABLE_CHECK");
slink.fail_check("AXI-AW-001", "AWADDR_STABLE_CHECK", "AWADDR changed while stalled");
slink.hit_check("AXI-AW-001", "AWADDR_STABLE_CHECK");
```

10. Run simulation with either `+SPECLINK_TESTNAME=axi_basic_write_test` or an explicit call to `set_current_test`.
11. Parse the simulation log into evidence JSON:

```bash
python manage.py parse_speclink_log --project axi --run-id nightly_001 path/to/test.log --output evidence.json
```

or:

```bash
python tools/speclink_parse_log.py --project axi --run-id nightly_001 path/to/test.log --output evidence.json
```

12. Upload `evidence.json` from Evidence Upload.
13. View closure on the dashboard, regression run detail, requirement detail, and snapshot pages.

## Example DV Flow

- Requirement: `AXI-AW-001`, "AWADDR must remain stable while AWVALID is high and AWREADY is low."
- Test: `axi_basic_write_test`
- Check: `AWADDR_STABLE_CHECK`
- Mapping: `AXI-AW-001` requires `axi_basic_write_test` and `AWADDR_STABLE_CHECK`
- Generated package expects `AWADDR_STABLE_CHECK` when `axi_basic_write_test` runs
- Scoreboard calls `pass_check` when comparison passes
- End-of-test summary reports the check passed
- Parser extracts evidence
- Django marks `AXI-AW-001` closed for that regression run

## Closure Policy

A requirement is closed for a run only when it is active, all required mapped tests have evidence, all required mapped tests passed, all required mapped checks were observed, all required checks passed, and no required check failed or is missing.

Failed tests or failed checks make the requirement failed. Partial evidence with missing required checks or tests makes it partial. No meaningful evidence leaves it open.

## Tests

```bash
python manage.py test
```
