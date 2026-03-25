# Contributing to ExamCraft AI

> **Note:** This repository is automatically mirrored from our private
> development monorepo. It contains the open-source core of ExamCraft AI
> (MIT License). Pull requests opened here cannot be merged directly.

## How to Contribute

1. **Open an issue** describing your proposed change
2. Our team will review and, if approved, implement it in our internal repo
3. The change will appear in this mirror on the next release

For bug reports, please use the bug report issue template.

## Quick Start for Local Development

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   `git clone https://github.com/yourusername/examcraft.git`
3. **Setup** environment variables: `cp backend/.env.example backend/.env`
4. **Start** development stack: `docker compose up`
5. **Create** a feature branch: `git checkout -b feature/amazing-feature`
6. **Make** your changes and **test** thoroughly
7. **Commit** using conventional commits:
   `git commit -m 'feat: Add amazing feature'`
8. **Push** to your fork: `git push origin feature/amazing-feature`
9. **Create** a Pull Request with a clear description

## Development Environment

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.13+ (for local development)
- Node.js 18+ (for frontend development)
- Claude API Key (optional, for testing KI features)

### Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/examcraft-ai.git
cd examcraft-ai

# Start development stack
./start-dev.sh

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Code Standards

### Python (Backend & Utils)

- **Style**: PEP 8 compliance required
- **Type Hints**: All functions must include type hints
- **Documentation**: Docstrings for all public functions
- **Testing**: Unit tests with pytest
- **Formatting**: Use `ruff format` before committing

```bash
# Code quality checks
ruff check backend/ utils/
ruff format backend/ utils/
pytest backend/tests/
```

### TypeScript (Frontend)

- **Style**: ESLint + Prettier configuration
- **Types**: Strict TypeScript, no `any` types
- **Components**: Functional components with hooks
- **Testing**: React Testing Library + Jest
- **UI**: Use shadcn/ui components consistently

```bash
# Frontend checks
cd frontend
bun run lint
bun run type-check
bun test
```

## Types of Contributions

### Bug Reports

- Use GitHub Issues with the "bug" label
- Include steps to reproduce, expected vs actual behavior
- Provide system information (OS, Docker version, etc.)
- Screenshots/logs are highly appreciated

### Feature Requests

- Use GitHub Issues with the "enhancement" label
- Clearly describe the use case and proposed solution
- Consider educational impact and user experience
- Check existing issues to avoid duplicates

### Documentation

- README improvements, code comments, API documentation
- Tutorial content, examples, educational materials
- Translations (currently German/English)

### Testing

- Unit tests for backend services
- Integration tests for API endpoints
- Frontend component tests
- E2E testing scenarios

## Architecture Overview

### Backend (`backend/`)

- **FastAPI** REST API server
- **SQLAlchemy** ORM with PostgreSQL
- **Pydantic** data validation and serialization
- **Claude API** integration via PydanticAI

### Document Processing (`utils/`)

- **Docling** for PDF text extraction
- **ChromaDB** for vector storage and semantic search
- **sentence-transformers** for embeddings

### Frontend (`frontend/`)

- **React 18** with TypeScript
- **TanStack Query** for API state management
- **Tailwind CSS** + shadcn/ui for styling
- **React Router** for navigation

## Security Guidelines

- **Never commit** API keys or sensitive data
- **Use environment variables** for configuration
- **Sanitize user inputs** in all API endpoints
- **Validate file uploads** to prevent malicious content
- **Follow OWASP** best practices for web security

## Pull Request Process

1. **Branch Naming**: Use descriptive names
   (`feature/add-export-format`, `fix/pdf-parsing-bug`)

2. **Commit Messages**: Follow
   [Conventional Commits](https://conventionalcommits.org/)

   ```text
   feat: add new question type for multiple choice
   fix: resolve PDF parsing issue with special characters
   docs: update API documentation for question generation
   test: add unit tests for RAG system
   ```

3. **PR Description Template**:
   - **What**: Brief description of changes
   - **Why**: Motivation and context
   - **How**: Technical approach
   - **Testing**: How you tested the changes
   - **Screenshots**: For UI changes

4. **Review Process**:
   - All PRs require at least one review
   - CI/CD checks must pass
   - Code coverage should not decrease
   - Documentation must be updated if needed

## Educational Impact

When contributing, consider:

- **Pedagogical Value**: How does this improve education?
- **Accessibility**: Can all users benefit from this feature?
- **Internationalization**: Consider multi-language support
- **Performance**: Impact on user experience and system resources

## Debugging & Development

### Backend Development

```bash
# Run backend locally for debugging
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Database operations
docker-compose exec postgres psql -U examcraft -d examcraft

# View logs
docker-compose logs -f backend
```

### Frontend Development

```bash
# Run frontend with hot reload
cd frontend
bun start

# Debug build issues
bun run build
bun run type-check
```

## Testing Guidelines

### Backend Testing

```bash
# Run all backend tests
pytest backend/tests/

# Test specific modules
pytest backend/tests/test_document_processing.py -v

# Coverage report
pytest --cov=backend backend/tests/
```

### Frontend Testing

```bash
# Run frontend tests
bun test

# Coverage report
bun run test:coverage

# E2E tests (if implemented)
bun run test:e2e
```

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and community support
- **Documentation**: Check `/docs` folder and API documentation at
  `/docs` endpoint
- **Code Review**: Request reviews from maintainers in PRs

## Recognition

All contributors will be recognized in our README.md and release notes.
We appreciate every contribution, whether it's code, documentation, bug
reports, or community support!

## License

By contributing to ExamCraft AI, you agree that your contributions will be
licensed under the MIT License.

---

**Happy Contributing!** Let's build amazing educational technology together!
