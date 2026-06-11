# Next Steps: Integration Testing

This document records the proposed integration-testing approach for the CAGED
check-availability Lambda. It is intentionally a future plan. Implementation
should begin after the complete workflow for discovering, downloading, and
storing CAGED files in Amazon S3 is available.

## Goal

Add automated tests that verify the application against real AWS services and
deployed configuration, while keeping production resources and data isolated.

The existing tests should remain the primary unit-test suite. Integration tests
will complement them by detecting problems that fakes cannot expose, including:

- Incorrect resource configuration.
- Missing IAM permissions.
- Invalid Lambda environment variables.
- Deployment-package or handler configuration errors.
- Differences between fake and real AWS API behavior.
- Incorrect event-source connections.
- Timeout, memory, and runtime issues in the deployed Lambda environment.

## Current Constraint

`CheckAvailabilityService.execute()` connects to the external FTP server before
loading the DynamoDB registry. Therefore, invoking the deployed Lambda currently
also invokes the FTP integration.

Until FTP testing is intentionally included, the first integration-test phase
should call the registry-loading behavior with a real DynamoDB table rather than
invoke the full handler. This verifies the application-to-DynamoDB boundary but
does not verify the deployed Lambda execution role.

Do not describe this first phase as a complete Lambda integration test.

## Required AWS Environment

Use an environment that is completely separate from production.

Preferred isolation:

- A dedicated non-production AWS account for development and integration tests.
- A separate deployment stack, such as `caged-check-availability-integration`.
- Test-specific IAM roles with no access to production resources.
- Test-specific resource names and tags.
- Cost budgets and alerts for the test account or environment.

If a separate AWS account is not initially available, use a dedicated stack and
strict IAM resource boundaries in the shared account. Never point integration
tests at production tables, buckets, queues, event buses, or Lambda functions.

## Resources

### Initial DynamoDB Integration

The first phase requires:

- One dedicated DynamoDB table with the same key schema as production.
- Partition key: `registry_id` of type String.
- A test runner IAM role that can read and write only the test table.
- Infrastructure as Code that creates the table consistently.
- A unique `registry_id` for each test run to support parallel execution.

Example test identifier:

```text
integration-<pipeline-run-id>
```

### Deployed Lambda Integration

The later cloud integration environment will require:

- A separately deployed check-availability Lambda.
- A dedicated Lambda execution role.
- Test-specific environment variables.
- The integration DynamoDB registry table.
- A CloudWatch log group with an explicit retention period.
- A test runner role allowed to invoke only the integration Lambda.
- Stack outputs containing the Lambda name or ARN and relevant resource names.

### Full Download Workflow

After the download and S3 workflow is implemented, the test environment may
also require:

- A dedicated S3 bucket for downloaded test files.
- A separate downloader Lambda and execution role, if it is a separate function.
- Test-specific EventBridge rules, SQS queues, Step Functions workflows, or
  other orchestration resources introduced by the final architecture.
- Dead-letter queues or failure destinations where applicable.
- Encryption keys only if the production architecture uses customer-managed
  keys and that behavior must be validated.
- Lifecycle rules to remove old integration-test objects automatically.

All resources must be separate from production and created from the same type of
Infrastructure as Code definition used by production.

## Proposed Directory and Test Separation

Keep cloud integration tests separate from the fast unit tests:

```text
tests/
  integration/
```

The exact commands can be finalized during implementation, but unit and
integration tests should remain independently selectable. Integration tests
must fail clearly when required AWS configuration is absent rather than silently
running against a developer's default resources.

## Phase 1: Real DynamoDB Boundary

1. Define the integration DynamoDB table through Infrastructure as Code.
2. Deploy it in the isolated integration environment.
3. Create a least-privilege IAM role for the local or CI test runner.
4. Configure the test run with an explicit AWS account, region, and table name.
5. Generate a unique `registry_id` for the test run.
6. Seed a known registry item in the real DynamoDB table.
7. Construct `CheckAvailabilityService` with the real boto3 table resource.
8. Call `load_registry_tree()` without calling `execute()`.
9. Assert that the real DynamoDB item is deserialized and returned correctly.
10. Delete only the item created by that test run in teardown.

Initial scenarios:

- A valid registry tree is returned.
- An empty registry tree is accepted.
- A missing item raises `RegistryItemNotFoundError`.
- An invalid tree value raises `InvalidRegistryTreeError`.

Do not repeat every business-rule unit test in this suite. Its purpose is to
verify the AWS boundary and real service behavior.

## Phase 2: Deployed Lambda and DynamoDB

Begin this phase when the Lambda can be exercised without depending on the live
FTP server, or when controlled FTP testing is intentionally introduced.

1. Package the Lambda using the production packaging process.
2. Deploy the Lambda and DynamoDB table to an isolated integration stack.
3. Configure the Lambda with test-specific environment variables.
4. Seed the test registry item.
5. Invoke the deployed Lambda through the AWS Lambda API.
6. Assert that the invocation has no function error.
7. Decode and validate the Lambda response contract.
8. Verify the Lambda execution role can read the integration table.
9. Verify expected structured logs are written to CloudWatch.
10. Remove test data and destroy ephemeral stacks when applicable.

This phase validates packaging, handler configuration, environment variables,
runtime compatibility, IAM permissions, timeout, memory, logging, and DynamoDB
access from the real Lambda environment.

## Phase 3: Full Workflow Integration

Implement this phase after file downloading and S3 persistence are complete.

1. Deploy the complete workflow into the isolated integration environment.
2. Seed controlled registry state and controlled input data.
3. Trigger the workflow through its real entry point.
4. Wait for asynchronous processing with bounded polling and a clear timeout.
5. Verify the expected S3 object exists in the integration bucket.
6. Verify its key, metadata, and relevant content properties.
7. Verify the DynamoDB registry reaches the expected final status.
8. Verify duplicate delivery or retry behavior is idempotent.
9. Verify failure handling, including retry and dead-letter behavior.
10. Delete created objects and test records after each run.

Avoid relying on the mutable public FTP server for deterministic assertions. A
controlled source or fixture will be needed before this phase can be a reliable
CI quality gate.

## CI/CD Sequence

A future delivery pipeline should run checks in this order:

1. Lint and formatting checks.
2. Unit tests with fakes.
3. Build and package validation.
4. Deploy or update the isolated integration stack.
5. Seed integration-test data.
6. Run cloud integration tests.
7. Clean up test data or ephemeral resources.
8. Promote the same tested artifact to the next environment only after all
   required checks pass.

Use short-lived credentials through CI identity federation, such as GitHub
Actions OpenID Connect, instead of permanent AWS access keys.

## Test Isolation and Cleanup

- Use unique identifiers for each pipeline or branch.
- Never clear an entire shared table or bucket during teardown.
- Delete only resources and records owned by the current test run.
- Apply ownership tags to stacks and resources.
- Set CloudWatch log retention rather than retaining logs indefinitely.
- Apply S3 lifecycle expiration to integration-test objects.
- Run cleanup in a final pipeline step even when tests fail.
- Periodically detect and remove abandoned test stacks and data.

## Do

- Keep unit tests fast and run them before cloud tests.
- Test against real AWS services for IAM and configuration confidence.
- Use the same Infrastructure as Code patterns as production.
- Make account, region, stack, and resource names explicit.
- Keep integration scenarios small and focused on component boundaries.
- Validate observable outcomes instead of internal implementation details.
- Set bounded timeouts for asynchronous assertions.

## Do Not

- Use production resources or production data.
- Depend on a developer's implicit default AWS profile.
- Store long-lived AWS credentials in repository or CI configuration.
- Treat DynamoDB Local, mocks, or emulators as proof that IAM is correct.
- Assert exact results from a mutable external FTP server.
- make cloud tests responsible for all business-rule combinations.
- Hide intermittent failures with unlimited retries.
- Promote an artifact different from the one exercised by integration tests.

## Implementation Decision Checklist

Before beginning implementation, decide:

- Which AWS account and region will host integration tests.
- Which Infrastructure as Code project owns the test stack.
- Whether the stack is persistent or created per branch/pipeline.
- How CI obtains short-lived AWS credentials.
- How the application avoids or controls FTP access during deterministic tests.
- Which service is the real entry point for the completed download workflow.
- Which observable state proves successful completion.
- How test data and abandoned resources are cleaned up.

## Recommended Starting Point

When work resumes, implement only Phase 1 first:

```text
pytest -> real isolated DynamoDB table -> load_registry_tree()
```

After the complete download-to-S3 cycle exists, revisit the architecture and
expand the suite to cover the deployed Lambda and the full asynchronous workflow.
