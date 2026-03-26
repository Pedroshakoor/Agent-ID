# Contributing to AgentID

Thank you for your interest in contributing! AgentID is MIT-licensed and welcomes all contributors.

## Getting Started

1. Fork the repo and clone locally
2. Run `make dev` to start the full stack
3. Create a feature branch: `git checkout -b feat/my-feature`
4. Make your changes with tests
5. Run `make test` to ensure everything passes
6. Open a PR against `main`

## Development Setup

```bash
make dev        # Start all services via Docker Compose
make test       # Run all tests (backend + SDKs)
make lint       # Lint everything
make migrate    # Run DB migrations
```

## Code Style

- **Python**: Ruff + Black (enforced via pre-commit)
- **TypeScript**: ESLint + Prettier
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)

## Pull Request Guidelines

- One concern per PR
- Include tests for new features
- Update docs/README if adding new APIs
- All CI checks must pass

## Security Issues

Do **not** open public issues for security vulnerabilities. Email security@agentid.dev instead.

## License

By contributing, you agree your work is licensed under MIT.
