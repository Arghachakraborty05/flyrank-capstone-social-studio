# Acceptance Evidence

This document tracks verification of the Social Media Studio requirements. Results will be recorded from actual implementation and test execution.

**Current status:** Acceptance testing pending; application implementation has not started.

## Acceptance Probes

|   ID  |                                 Requirement                                  |                       Verification evidence                         | Status  |
|-------|------------------------------------------------------------------------------|---------------------------------------------------------------------|---------|
| AP-01 | Ingest a source post and generate valid variants for at least two platforms. | API request/response and stored variant records.                    | Pending |
| AP-02 | Reject invalid content before review and identify the violated constraint.   |Test output showing the validation failure and named rule.           | Pending |
| AP-03 | Prevent scheduling of an unapproved variant.                               |API response showing an appropriate 4xx status and clear error message.| Pending |
| AP-04 | Publish an approved variant through the real Telegram adapter.|Test transcript and Telegram publication identifier or verifiable message reference.| Pending |
| AP-05 | Restart processing and verify recovery and duplicate protection.             |Restart test output and persistent schedule/publication history.     | Pending |
| AP-06 | Switch to the mock X publisher without changing campaign business logic.     |Configuration, test output, and persisted mock publication preview.  | Pending |

## Additional Verification

The following areas will also be verified as the corresponding functionality is implemented:

- Review states and edit, approve, and reject operations.
- Persistent scheduling and publication-attempt history.
- Secret handling and exclusion of credentials from Git.
- Automated tests and reproducible setup instructions.

## Evidence Policy

Only observed results from executed tests or verifiable application behavior will be marked as passed. Untested requirements remain pending. Failed tests and known limitations will be recorded accurately.