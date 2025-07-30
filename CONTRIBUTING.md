# Contributing to Mipal Analytics

We love your input! We want to make contributing to Mipal Analytics as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. **Fork the repo** and create your branch from `main`.
2. **Make your changes** following our coding standards.
3. **Add tests** if you've added code that should be tested.
4. **Ensure the test suite passes**.
5. **Make sure your code lints** following our style guidelines.
6. **Update documentation** if needed.
7. **Issue that pull request**!

## Coding Standards

### Backend (Python)

- **Type Hints**: Always use Python type definitions as specified in project rules
- **Code Style**: Follow PEP 8 guidelines
- **Docstrings**: Use Google-style docstrings for functions and classes
- **Testing**: Write unit tests for new functionality
- **Dependencies**: Use `uv` for dependency management

Example:
```python
from typing import List, Optional

def process_data(items: List[str], filter_empty: bool = True) -> Optional[List[str]]:
    """Process a list of items with optional filtering.
    
    Args:
        items: List of string items to process
        filter_empty: Whether to filter out empty strings
        
    Returns:
        Processed list of items, or None if input is invalid
    """
    if not items:
        return None
    
    if filter_empty:
        return [item for item in items if item.strip()]
    return items
```

### Frontend

- **Code Style**: Follow established JavaScript/TypeScript conventions
- **Components**: Use functional components with hooks
- **Testing**: Write component tests for new UI features
- **Accessibility**: Ensure components are accessible (WCAG guidelines)

## Project Structure

```
mipal-analytics/
├── backend/          # Python FastAPI backend
│   ├── app/          # Main application code
│   ├── tests/        # Backend tests
│   └── ...
├── frontend/         # Frontend application
│   ├── src/          # Source code
│   ├── tests/        # Frontend tests
│   └── ...
└── docs/             # Documentation
```

## Development Setup

### Backend Development

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Install dependencies using uv**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the development server**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. **Run tests**:
   ```bash
   uv run pytest
   ```

### Frontend Development

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the development server**:
   ```bash
   npm start
   ```

4. **Run tests**:
   ```bash
   npm test
   ```

## Testing Guidelines

### Backend Testing

- Write unit tests for business logic
- Use pytest fixtures for common test data
- Mock external dependencies
- Aim for >80% code coverage

### Frontend Testing

- Write component tests using Jest and React Testing Library
- Test user interactions and component behavior
- Mock API calls in tests

## Submitting Issues

### Bug Reports

When filing an issue, make sure to answer these questions:

1. **What version** of the software are you using?
2. **What operating system** and processor architecture are you using?
3. **What did you do?**
4. **What did you expect to see?**
5. **What did you see instead?**

### Feature Requests

We welcome feature requests! Please provide:

1. **Clear description** of the feature
2. **Use case** - why is this feature needed?
3. **Proposed implementation** (if you have ideas)
4. **Alternative solutions** you've considered

## Code Review Process

1. **All submissions** require review before merging
2. **Maintainers** will review your pull request
3. **Address feedback** promptly and professionally
4. **Tests must pass** before merging
5. **Documentation** must be updated if needed

## Community Guidelines

### Be Respectful

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community

### Be Collaborative

- Help others learn and grow
- Share knowledge and resources
- Ask questions when you need help
- Offer help to others when you can

## Getting Help

- **Documentation**: Check the README and docs/ directory first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Discord/Slack**: [Add your community chat links if available]

## Recognition

Contributors will be recognized in:
- README.md contributor section
- Release notes for significant contributions
- Special recognition for major features or improvements

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## References

This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/master/CONTRIBUTING.md) and other best practices from the open-source community.

---

Thank you for contributing to Mipal Analytics! 🚀 