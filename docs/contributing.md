# Contributing

Thank you for your interest in improving the Meeting Transcription Tool!  
This guide sets expectations for code quality, testing, documentation, and workflow.

## Development Workflow
1. Fork & clone the repository.
2. Create a feature branch: `git checkout -b feature/my-change`.
3. Install runtime + docs tooling: `pip install -r requirements.txt -r docs/requirements.txt`.
4. Add or update tests alongside your code changes.
5. Run linting & tests before opening a PR.

## Coding Standards
- Prefer explicit type hints and dataclasses for structured data.
- Keep modules small and composable; reuse helpers like `format_segments_for_prompt`.
- Capture API calls with sanitized metadata for observability.
- Fail gracefully with informative messages; never swallow exceptions silently.

## Testing
- Run `pytest` locally.
- Use mocks to isolate external services (OpenAI, Google Generative AI).
- Add regression tests when fixing bugs to prevent re-introduction.

## Documentation
- Update the Markdown files under `docs/`—they are the single source of truth.
- Keep the README concise; link back to relevant docs for detail.
- When adding new features, include a short note in the relevant page (e.g., `speaker-identification.md`).

## GitHub Pages
- Documentation is published automatically from `docs/` using MkDocs Material.
- Changes merged into `main` trigger the CI workflow (`publish-docs.yml`) that builds and deploys the site.
- To preview locally:
  ```bash
  mkdocs serve
  ```

## Pull Request Checklist
- [ ] Tests cover new functionality.
- [ ] `pytest` passes locally.
- [ ] Docs updated (or confirmed not needed).
- [ ] Lint warnings addressed.
- [ ] Squash commits into logical units (optional but encouraged).

## Community Guidelines
- Be respectful and constructive.
- Prefer asynchronous communication via GitHub issues/PRs.
- Clearly document assumptions and limitations in your PR description.

Ready to contribute? Open an issue to discuss larger ideas or jump straight into a pull request for focused fixes.  
We appreciate your support!

