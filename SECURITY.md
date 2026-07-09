# Security Policy

## Supported versions

Airflow Observer is currently pre-1.0. Security fixes are applied to the main branch.

## Reporting a vulnerability

Please do not open public issues for vulnerabilities that expose credentials, allow unauthorized ingestion, or leak Airflow metadata.

Report privately by contacting the repository maintainers through GitHub security advisories once the repository is published.

Include:

- affected commit or version;
- reproduction steps;
- impact;
- suggested mitigation, if known.

## Deployment guidance

- Generate a strong `DEFAULT_API_KEY` per deployment.
- Keep `DEMO_MODE=false` outside local demos.
- Use HTTPS in front of the frontend and backend.
- Restrict backend ingress so only trusted agents and the frontend can reach it.
- Rotate Observer and Airflow credentials when staff or infrastructure changes.
- Never commit `.env`, Slack webhook URLs, Airflow tokens, or database backups.
