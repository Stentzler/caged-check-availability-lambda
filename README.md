# CAGED Check Availability Lambda

AWS Lambda function that scans the Novo CAGED FTP tree, compares it with the
DynamoDB downloaded-file registry, and returns new files that still
need downstream processing.

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

Run the handler locally with the default event. This performs a real FTP scan
and reads the registry from DynamoDB:

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

## Environment variables

```env
REGISTRY_TABLE_NAME=downloaded_files_registry
REGISTRY_ID=ftp_tree
REGISTRY_SOURCE=caged_ftp
```

For local DynamoDB:

```env
DYNAMODB_ENDPOINT_URL=http://127.0.0.1:8000
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
```

`debug_handler.py` and the VS Code local launch configuration provide these
defaults before importing `src/handler.py`. Run the Lambda locally with:

```bash
uv run python debug_handler.py
```

To run with an explicit one-command override instead:

```bash
DYNAMODB_ENDPOINT_URL=http://127.0.0.1:8000 \
AWS_DEFAULT_REGION=us-east-1 \
AWS_ACCESS_KEY_ID=dummy \
AWS_SECRET_ACCESS_KEY=dummy \
uv run python debug_handler.py
```

Do not set `DYNAMODB_ENDPOINT_URL` in AWS Lambda unless you intentionally need a
custom endpoint. In AWS, the SDK uses the configured region and Lambda execution
role.

## Lambda response

```json
{
  "new_files": [
    {
      "filename": "CAGEDMOV202605.7z",
      "ftp_url": "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/2026/202605/CAGEDMOV202605.7z",
      "reference_month": "202605",
      "reference_year": "2026",
      "s3_key": "raw/caged/year=2026/month=05/file_type=movement/CAGEDMOV202605.7z"
    }
  ]
}
```

The `file_type` partition identifies the CAGED archive category without requiring
consumers to parse the filename: `movement` for `CAGEDMOV`, `exclusion` for
`CAGEDEXC`, and `late_movement` for `CAGEDFOR`. Unrecognized files use `other`.

## Local event file

`events/check-availability.json` contains a sample Lambda event for local
experiments.

```bash
uv run python -m src.handler events/check-availability.json
```

## Local registry sample

`sample/downloaded_files_registry.json` contains the complete DynamoDB registry
fixture generated from `sample/caged_data.json`. All files are marked as
`downloaded` and use fake S3 URLs.
