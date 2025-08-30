# YouTube Archiver - Requirements

## Functional Requirements

### Core Features
1. **Video Discovery**
   - Scan specified YouTube channels for live stream videos
   - Identify videos that are currently public
   - Filter for videos older than 24 hours
   - Focus on live streams (sacrament meetings are typically the only live content)

2. **Visibility Management**
   - Change video visibility from "public" to "unlisted"
   - Preserve video content and metadata
   - Maintain access for ward members via direct links
   - No deletion of video content

3. **Channel Management**
   - Support for multiple ward YouTube channels (scalable design)
   - Configurable channel list (IDs or URLs)
   - Batch processing across all channels
   - Individual channel error handling
   - Easy setup for different stakes/wards

4. **Scheduling**
   - Manual execution capability (local script)
   - Automated execution via GitHub Actions
   - Monday evening scheduling (configurable time)
   - Timezone awareness for different ward locations

### Authentication & Authorization
1. **YouTube API Setup**
   - Google Cloud project configuration
   - YouTube Data API v3 enablement
   - OAuth2 credentials for channel management
   - Secure credential storage and rotation

2. **Permissions**
   - Channel manager permissions for stake tech specialist account
   - Appropriate API scopes for video management
   - Secure authentication flow for both local and CI environments

### Safety & Reliability
1. **Error Handling**
   - Graceful handling of API rate limits
   - Network connectivity issues
   - Invalid channel access
   - Individual video processing failures

2. **Validation**
   - Verify channel access before processing
   - Confirm video age before visibility changes
   - Validate API responses
   - Dry-run mode for testing

3. **Logging**
   - Record all actions taken
   - Track processing statistics
   - Error logging and reporting
   - Optional summary reports

## Technical Requirements

### Local Execution
- **Language**: Python 3.9+ (for enhanced type hints support)
- **Type Safety**: Full type annotations with mypy static type checking
- **Dependencies**: Google API client libraries, configuration management, dependency injection framework
- **Architecture**: Clean architecture with dependency injection and abstract base classes
- **Configuration**: YAML or JSON config file with Pydantic models for validation
- **Credentials**: Local OAuth2 token storage
- **Output**: Console logging with optional file output
- **Testing**: Comprehensive unit and integration tests with coverage reporting

### GitHub Actions Workflow
- **Trigger**: Scheduled cron job (Monday evenings)
- **Environment**: Ubuntu latest runner
- **Secrets**: Secure storage of API credentials
- **Notifications**: Optional workflow status notifications
- **Artifacts**: Processing logs and reports

### API Integration
- **Service**: YouTube Data API v3
- **Endpoints**: 
  - Channels list
  - Search for channel videos
  - Videos list with statistics
  - Videos update for visibility changes
- **Rate Limiting**: Respect YouTube API quotas and limits
- **Pagination**: Handle large channel video lists

## Configuration Requirements

### Channel Configuration
```yaml
# Example configuration - easily customizable for different stakes
stake_info:
  name: "Example Stake"
  tech_specialist: "your.email@gmail.com"
  
channels:
  - name: "1st Ward"
    channel_id: "UC..."
    timezone: "America/Denver"
  - name: "2nd Ward" 
    channel_id: "UC..."
    timezone: "America/Denver"
  - name: "3rd Ward"
    channel_id: "UC..."
    timezone: "America/Denver"
```

### Processing Settings
```yaml
settings:
  age_threshold_hours: 24
  target_visibility: "unlisted"
  dry_run: false
  max_videos_per_channel: 50
  schedule_time: "20:00"  # 8 PM
```

## Non-Functional Requirements

### Performance
- Process all 7 channels within 5 minutes
- Handle up to 50 videos per channel efficiently
- Minimal API quota usage

### Security
- Secure credential management
- No hardcoded secrets in code
- Audit trail of all changes
- Principle of least privilege for API access

### Maintainability
- Clear documentation and setup instructions
- Modular code structure with SOLID principles
- Configuration-driven behavior
- Easy addition/removal of channels
- Strong type safety with comprehensive type annotations
- Dependency injection for testability and flexibility
- Abstract base classes for extensibility

### Reliability
- 99% success rate for video processing
- Graceful degradation on partial failures
- Retry logic for transient errors
- Monitoring and alerting capabilities

## Code Quality & Architecture Requirements

### Type Safety
1. **Static Type Checking**
   - Full type annotations for all functions, methods, and variables
   - mypy static type checker with strict configuration
   - Type hints for external library interfaces
   - Generic types where appropriate (List[T], Dict[K, V], etc.)
   - Protocol classes for structural typing where needed

2. **Runtime Type Validation**
   - Pydantic models for configuration validation
   - Input validation at API boundaries
   - Type-safe deserialization of API responses
   - Comprehensive error messages for type mismatches

### Dependency Injection
1. **Container-Based DI**
   - Use dependency-injector or similar framework
   - Constructor injection preferred over property injection
   - Interface-based dependencies (ABC classes)
   - Configurable lifetimes (singleton, transient, scoped)

2. **Testability**
   - All external dependencies injected (YouTube API, file system, etc.)
   - Easy mocking and stubbing for unit tests
   - Clear separation of concerns
   - No global state or singletons except where necessary

### Abstract Base Classes (ABC)
1. **Core Interfaces**
   ```python
   # Example interfaces to implement
   class VideoRepository(ABC):
       @abstractmethod
       async def get_channel_videos(self, channel_id: str) -> List[Video]: ...
   
   class VisibilityManager(ABC):
       @abstractmethod
       async def change_visibility(self, video_id: str, visibility: VideoVisibility) -> bool: ...
   
   class ConfigurationProvider(ABC):
       @abstractmethod
       def get_channels(self) -> List[ChannelConfig]: ...
   ```

2. **Implementation Strategy**
   - Abstract base classes for all major components
   - Concrete implementations for YouTube API integration
   - Mock implementations for testing
   - Plugin architecture for future extensions

### Testing Requirements
1. **Test Coverage**
   - Minimum 90% code coverage
   - 100% coverage for critical business logic
   - Coverage reporting with pytest-cov
   - Coverage enforcement in CI/CD pipeline

2. **Test Types**
   - **Unit Tests**: Individual component testing with mocks
   - **Integration Tests**: API integration with test credentials
   - **Contract Tests**: Verify ABC implementations
   - **End-to-End Tests**: Full workflow testing with dry-run mode

3. **Test Framework & Tools**
   - pytest as primary testing framework
   - pytest-asyncio for async test support
   - pytest-mock for mocking capabilities
   - factory-boy or similar for test data generation
   - hypothesis for property-based testing (where applicable)

4. **Test Organization**
   ```
   tests/
   ├── unit/
   │   ├── test_video_repository.py
   │   ├── test_visibility_manager.py
   │   └── test_configuration.py
   ├── integration/
   │   ├── test_youtube_api.py
   │   └── test_workflow.py
   ├── fixtures/
   │   ├── sample_configs.py
   │   └── mock_responses.py
   └── conftest.py
   ```

### Code Quality Tools
1. **Linting & Formatting**
   - black for code formatting
   - isort for import sorting
   - flake8 or ruff for linting
   - pre-commit hooks for automated checks

2. **Static Analysis**
   - mypy for type checking with strict configuration
   - bandit for security analysis
   - pylint for additional code quality checks
   - Documentation string validation

3. **Development Workflow**
   - All checks must pass before merge
   - Automated testing in GitHub Actions
   - Code review requirements
   - Continuous integration with quality gates

### Architecture Patterns
1. **SOLID Principles**
   - Single Responsibility: Each class has one reason to change
   - Open/Closed: Open for extension, closed for modification
   - Liskov Substitution: Subtypes must be substitutable for base types
   - Interface Segregation: Many client-specific interfaces
   - Dependency Inversion: Depend on abstractions, not concretions

2. **Clean Architecture**
   ```
   src/
   ├── domain/          # Business logic and entities
   │   ├── models/      # Domain models (Video, Channel, etc.)
   │   ├── services/    # Business logic interfaces
   │   └── exceptions/  # Domain-specific exceptions
   ├── infrastructure/ # External concerns
   │   ├── youtube/     # YouTube API implementation
   │   ├── config/      # Configuration providers
   │   └── logging/     # Logging implementations
   ├── application/    # Application services
   │   ├── handlers/    # Command/query handlers
   │   └── workflows/   # Business workflows
   └── main.py         # Application entry point
   ```

## Reusability Requirements

### Multi-User Support
1. **Easy Setup Process**
   - Clear documentation for Google API setup
   - Step-by-step configuration guide
   - Template configuration files
   - Minimal technical knowledge required

2. **Flexible Configuration**
   - Support for any number of channels
   - Configurable timezones for different regions
   - Customizable scheduling preferences
   - Optional features (reporting, notifications)

3. **Distribution & Sharing**
   - Open source repository (GitHub)
   - Clear README with setup instructions
   - Example configurations for common scenarios
   - Troubleshooting guide

4. **Security Considerations**
   - Each user manages their own API credentials
   - No shared secrets or centralized authentication
   - Clear guidance on credential security
   - Separate configurations per stake/ward

### Documentation Requirements
1. **Setup Guide**
   - Google Cloud Console setup
   - YouTube API credential creation
   - Local environment configuration
   - GitHub Actions setup (optional)

2. **User Guide**
   - Configuration file customization
   - Running the script locally
   - Monitoring and troubleshooting
   - Common issues and solutions

3. **Technical Documentation**
   - Code structure and architecture
   - API usage and rate limiting
   - Extension points for customization
   - Contributing guidelines
   - Type safety and testing guidelines
   - Development environment setup

## Out of Scope (Phase 1)
- Video deletion functionality
- Advanced video filtering (beyond live streams)
- Real-time monitoring
- Web-based dashboard
- Video content analysis
- Custom notification systems beyond basic logging
- Centralized multi-stake management system
