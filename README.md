# CAGED Check Availability Lambda

AWS Lambda function that checks whether a monthly Novo CAGED `CAGEDMOVYYYYMM.7z`
file is available on the public FTP server.

## Local setup

This project uses `uv`.

```bash
uv sync --dev
```

Run the test suite:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

Run the handler locally with the default event. This performs a real FTP check
for the previous calendar month:

```bash
uv run python -m src.handler
```

## Debugging

VS Code breakpoints only stop execution when the Python process is started by
the debugger or when VS Code attaches to a `debugpy` process. A plain
`python test.py` command runs without a debugger attached.

To debug the currently open Python file, select `Python: Current file` in the
VS Code Run and Debug panel.

To debug a terminal command, start Python with `debugpy`:

```bash
uv run python -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 --wait-for-client test.py
```

Then select `Python: Attach to terminal command` in VS Code and start
debugging. Execution will continue after VS Code attaches, and red breakpoints
in the executed file will be active.

## Lambda event

`year_month` is optional. When omitted, the Lambda checks the previous calendar
month.

```json
{
  "year_month": "202605"
}
```

## Local event file

`events/check-availability.json` contains a sample Lambda event for local
experiments.

```bash
uv run python -m src.handler events/check-availability.json
```
