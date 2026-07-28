# Security policy

## Supported code

The project has not published a stable release. Security fixes are applied to
the current `main` branch. Older commits and development branches are not
maintained as supported versions.

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue, discussion, or
pull request.

Use GitHub's private vulnerability reporting option on the repository
Security page when it is available. Otherwise, email
`gioia.zheng.stud@gmail.com` with the subject
`[rag-observatory security]` and include:

- the affected command, module, or commit;
- steps to reproduce the problem;
- the likely impact;
- any suggested mitigation;
- whether the report may be acknowledged publicly after a fix.

Remove credentials, personal data, proprietary traces, and unrelated secrets
from the report. A minimal synthetic reproduction is preferred.

Reports will be reviewed before public disclosure. No response-time or
resolution-time guarantee is currently offered.

## Scope

Security concerns include unsafe handling of trace content, path or file
operations, dependency or packaging risks, and cases where the documented
privacy boundary is not respected.

General bugs, feature requests, and questions that do not involve sensitive
details should use the public issue templates.
