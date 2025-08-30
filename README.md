# YouTube Archiver

Automated tool to manage YouTube live stream visibility for LDS ward sacrament meeting recordings.

## Overview

This tool helps LDS stake tech specialists automatically change the visibility of sacrament meeting live streams from public to unlisted after the 24-hour church policy window. It's designed to be reusable across different stakes and wards.

## Features

- ✅ **Automated Processing**: Changes video visibility from public to unlisted after 24 hours
- ✅ **Multi-Ward Support**: Manages multiple ward channels from a single configuration
- ✅ **Type Safety**: Built with comprehensive type annotations and mypy validation
- ✅ **Clean Architecture**: SOLID principles with dependency injection and abstract interfaces
- ✅ **Configurable**: YAML-based configuration with environment variable support
- ✅ **Dry Run Mode**: Test changes without actually modifying videos
- ✅ **Comprehensive Testing**: Unit and integration tests with coverage reporting
- ✅ **CI/CD Ready**: GitHub Actions workflow for quality assurance

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Google Cloud Console project with YouTube Data API v3 enabled
- OAuth2 credentials for YouTube API access
- Manager permissions on ward YouTube channels

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/garthdb/youtube-archiver.git
   cd youtube-archiver
   ```

2. **Set up virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure the application**:
   ```bash
   cp config/example.yml config/config.yml
   # Edit config/config.yml with your stake and channel information
   ```

5. **Set up YouTube API credentials**:
   - Follow the [YouTube API Setup Guide](docs/youtube-api-setup.md)
   - Place your `credentials.json` file in the project root

### Usage

**Run in dry-run mode** (recommended first):
```bash
youtube-archiver --config config/config.yml --dry-run
```

**Process all channels**:
```bash
youtube-archiver --config config/config.yml
```

**Process specific channels**:
```bash
youtube-archiver --config config/config.yml --channels UC_CHANNEL_ID_1 UC_CHANNEL_ID_2
```

## Configuration

The application uses YAML configuration files with Pydantic validation. See [`config/example.yml`](config/example.yml) for a complete example.

### Key Configuration Sections

- **`stake_info`**: Your stake information and contact details
- **`channels`**: List of ward YouTube channels to manage
- **`processing`**: Video processing settings (age threshold, target visibility)
- **`youtube_api`**: YouTube API credentials and settings
- **`logging`**: Logging configuration and output settings

### Environment Variables

Configuration supports environment variable substitution:
```yaml
youtube_api:
  credentials_file: "${YOUTUBE_CREDENTIALS_FILE:credentials.json}"
  token_file: "${YOUTUBE_TOKEN_FILE:token.json}"
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run quality checks
make lint          # Run all linting checks
make type-check    # Run mypy type checking
make test          # Run tests
make test-cov      # Run tests with coverage
```

### Code Quality

This project maintains high code quality standards:

- **Type Safety**: 100% mypy compliance with strict mode
- **Code Formatting**: Black, isort, and ruff for consistent style
- **Testing**: Comprehensive test suite with 90%+ coverage requirement
- **Documentation**: Detailed docstrings and architectural documentation

### Architecture

The project follows clean architecture principles:

```
src/youtube_archiver/
├── domain/          # Business logic and entities
│   ├── models/      # Domain models (Video, Channel, etc.)
│   ├── services/    # Abstract interfaces (ABC classes)
│   └── exceptions/  # Domain-specific exceptions
├── infrastructure/ # External concerns
│   ├── config/      # Configuration providers
│   └── youtube/     # YouTube API implementation
└── application/    # Application services and use cases
```

## Deployment

### Local Execution

Run the tool manually on your local machine:
```bash
youtube-archiver --config config/config.yml
```

### GitHub Actions (Recommended)

Set up automated execution using GitHub Actions:

1. Fork this repository
2. Add your configuration as repository secrets
3. Enable the scheduled workflow
4. The tool will run automatically every Monday evening

See [`.github/workflows/schedule.yml`](.github/workflows/schedule.yml) for details.

## Contributing

We welcome contributions from other LDS tech specialists! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all quality checks pass
5. Submit a pull request

## Security

- **Credentials**: Never commit API credentials to the repository
- **Permissions**: Use principle of least privilege for API access
- **Validation**: All inputs are validated using Pydantic models
- **Logging**: Sensitive information is not logged

## Support

- **Issues**: Report bugs and feature requests via [GitHub Issues](https://github.com/garthdb/youtube-archiver/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/garthdb/youtube-archiver/discussions)
- **Documentation**: See the [`docs/`](docs/) directory for detailed guides

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the LDS tech specialist community
- Inspired by the need to help ward leaders manage digital content responsibly
- Thanks to all contributors who help make this tool better

---

**Note**: This tool is not officially affiliated with The Church of Jesus Christ of Latter-day Saints. It's a community project built by tech specialists to help with common ward technology needs.
