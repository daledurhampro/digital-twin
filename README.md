# Digital Twin

An AI "digital twin" of Dale Durham. It's a chat interface that answers questions
about my career, skills and experience, in my own voice. It's built for recruiters
and prospective employers.

## How it works

| Layer | Tech | Where it runs |
|---|---|---|
| Frontend | Next.js (static export), React, Tailwind | S3 static website behind CloudFront (optional custom domain via Route 53 + ACM) |
| API | FastAPI wrapped for Lambda (`lambda_handler.py`) | AWS Lambda behind API Gateway (HTTP API): `GET /`, `GET /health`, `POST /chat` |
| Model | Amazon Bedrock (Nova) via the Converse API | Bedrock runtime |
| Memory | Per-session conversation history as JSON | Private S3 bucket in AWS; the local `memory/` folder in dev |
| Infra | Terraform, one workspace per environment (`dev`, `test`, `prod`) | Remote state in S3 with DynamoDB locking |

The twin's persona is built at request time in `backend/context.py`. It draws on the
source material in `backend/data/`: résumé and LinkedIn PDFs, `facts.json`,
`summary.txt` and `style.txt`.

## Repository layout

- `frontend/`: Next.js app (`app/`, `components/twin.tsx`) and its Vitest tests (`__tests__/`)
- `backend/`: FastAPI server, prompt/context builder, Lambda packaging (`deploy.py`) and pytest tests (`tests/`)
- `terraform/`: all AWS infrastructure; `prod.tfvars` holds the production overrides
- `scripts/`: `deploy.sh` and `destroy.sh`, used by CI and locally
- `.github/workflows/`: CI/CD pipelines

## Workflows

**Deploy Digital Twin** (`deploy.yml`) runs on every push and pull request to `main`,
and can also be started manually with an environment choice:

1. **Unit tests**: backend `pytest` (via `uv`) and frontend `vitest`. Every run does this step.
2. **Deploy** (pushes and manual runs only, and only if the tests pass): assumes an AWS
   role via GitHub OIDC, then runs `scripts/deploy.sh <env>`, which:
   - builds the Lambda zip,
   - runs `terraform apply` in the matching workspace,
   - builds the frontend with the new API URL and syncs it to S3.

   The job then invalidates CloudFront and prints the site and API URLs.

Pull requests run the tests only and never deploy. Pushes to `main` deploy to `dev`.

**Destroy Environment** (`destroy.yml`) is manual only. It tears down a chosen
environment with `scripts/destroy.sh`, and only runs if you type the environment name
again to confirm.

## Running tests locally

```bash
cd backend  && uv run pytest
cd frontend && npm test
```

> [!WARNING]
> **Private repository: personal data. Do not clone, fork, or reuse.**
>
> This repository is a personal digital twin of me. It includes real
> career data, which an LLM needs as context for the twin to work. That data is
> here on purpose and is not sample data. It is intended for recruiters and prospective employers.
>
> - **Do not** clone, fork, copy, or redistribute this repository.
> - **Do not** use its contents to train, fine-tune, or provide context to any AI system.
> - **Do not** run it as-is. It would present you, or your LLM, as well - ME and I doubt it would even run without my secrets.
>
> If you can see this, you have access only for the purpose you were given it.
> If you think you have access by mistake, please contact me and
> delete any local copies.

Copyright © 2026 Dale Durham. All rights reserved. No license is granted.
