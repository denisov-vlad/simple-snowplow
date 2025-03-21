# Simple Snowplow

Simple Snowplow is a lightweight, self-hosted analytics collector compatible with the Snowplow analytics protocol. It allows you to collect event data from websites and applications while maintaining full control over your data and infrastructure.

## Features

- Compatible with Snowplow JavaScript tracker
- Collects web analytics data including page views, events, and user information
- Stores data in ClickHouse for high-performance analytics queries
- Optional SendGrid event tracking integration
- Configurable data retention and storage settings
- Horizontal scaling capabilities with ClickHouse cluster support
- Built with FastAPI for high performance
- Optional demo mode for easy testing

## Architecture

Simple Snowplow consists of the following components:

1. **FastAPI Backend**: Handles incoming tracking events and forwards them to ClickHouse
2. **ClickHouse Database**: Stores and processes analytics data
3. **JavaScript Tracking Libraries**: Compatible with standard Snowplow js trackers

## Installation

### Local Development

To install Simple Snowplow for local development:

1. Make sure you have Docker and Docker Compose installed
2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/simple-snowplow.git
   cd simple-snowplow
   ```
3. Download the required JavaScript files:
   ```bash
   ./simple_snowplow/utils/download_scripts.sh
   ```
4. Start the application using Docker Compose:
   ```bash
   docker-compose -f docker-compose-dev.yml up
   ```

### Production Deployment

For a production environment:

1. Install ClickHouse version 22.11 or later (follow the [ClickHouse documentation](https://clickhouse.com/docs/en/quick-start))
2. Build the Docker image:
   ```bash
   docker build -t simple-snowplow ./simple_snowplow
   ```
3. Create a custom configuration file (see [Configuration](#configuration))
4. Run the Docker container:
   ```bash
   docker run -d \
     -p 8000:80 \
     -v /path/to/your/config.toml:/app/settings.toml \
     -e SNOWPLOW_ENV=production \
     simple-snowplow
   ```

For Kubernetes deployment, check the example manifests in the `.github/k8s` directory.

## Configuration

Simple Snowplow uses a combined configuration system with Dynaconf for loading settings and Pydantic for type validation. Configuration can be managed through:

1. Default settings from `settings.toml`
2. Secret settings from `.secrets.toml` (if exists)
3. Environment variables with `SNOWPLOW_` prefix
4. Custom settings file specified with `SNOWPLOW_SETTINGS_FILE`

The configuration system prioritizes these sources in the order listed.

### Configuration Structure

The configuration is organized into logical sections:

- `common`: Basic application settings
- `clickhouse`: Database connection and table settings
- `logging`: Log formatting and level
- `security`: Security settings including rate limiting
- `proxy`: Configuration for proxy endpoints
- `performance`: Application performance tuning
- `elastic_apm`: APM monitoring configuration
- `prometheus`: Metrics and monitoring settings

### Main Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `common.service_name` | Application name | `simple-snowplow` |
| `common.debug` | Enable debug mode | `false` |
| `common.demo` | Enable demo mode | `false` |
| `logging.level` | Log level (DEBUG, INFO, WARNING, ERROR) | `WARNING` |
| `logging.json` | Use JSON formatting for logs | `false` |
| `security.rate_limiting.enabled` | Enable request rate limiting | `false` |
| `clickhouse.connection.host` | ClickHouse host | `clickhouse` |
| `clickhouse.connection.port` | ClickHouse port | `8123` |
| `clickhouse.configuration.database` | ClickHouse database | `snowplow` |
| `clickhouse.configuration.cluster_name` | ClickHouse cluster name (if using) | `""` |
| `performance.max_concurrent_connections` | Max concurrent connections | `100` |
| `performance.db_pool_size` | Database connection pool size | `5` |

For a complete list of configuration options, refer to the `settings.toml` file.

### Environment Variables

You can override any configuration setting using environment variables with the `SNOWPLOW_` prefix and double underscores to represent nested keys:

```bash
SNOWPLOW_COMMON__DEMO=true
SNOWPLOW_CLICKHOUSE__CONNECTION__HOST=my-clickhouse-server
SNOWPLOW_SECURITY__RATE_LIMITING__ENABLED=true
```

### Custom Configuration File

To use a custom configuration file:

```bash
export SNOWPLOW_SETTINGS_FILE=/path/to/your/custom.toml
```

The custom file only needs to include settings you want to override.

### Environment-Specific Configuration

Simple Snowplow supports environment-specific settings through the `SNOWPLOW_ENV` variable:

```bash
export SNOWPLOW_ENV=production
```

Settings for specific environments can be defined in the configuration file:

```toml
[development]
logging.level = "DEBUG"

[production]
logging.level = "WARNING"
security.disable_docs = true
```

## Usage

### Web Tracking

To track events from your website:

1. Include the Snowplow tracker in your HTML:
   ```html
   <script type="text/javascript">
   (function(p,l,o,w,i,n,g){if(!p[i]){p.GlobalSnowplowNamespace=p.GlobalSnowplowNamespace||[];
   p.GlobalSnowplowNamespace.push(i);p[i]=function(){(p[i].q=p[i].q||[]).push(arguments)
   };p[i].q=p[i].q||[];n=l.createElement(o);g=l.getElementsByTagName(o)[0];n.async=1;
   n.src=w;g.parentNode.insertBefore(n,g)}}(window,document,"script","//your-server.com/static/sp.js","snowplow"));

   snowplow('newTracker', 'sp', 'your-server.com', {
     appId: 'my-app',
     platform: 'web',
     post: true,
     forceSecureTracker: true
   });

   snowplow('trackPageView');
   </script>
   ```

2. Replace `your-server.com` with your Simple Snowplow server address

### Demo Mode

To test Simple Snowplow with the built-in demo:

1. Set `common.demo = true` in your configuration
2. Access the demo page at `http://your-server.com/demo/`
3. Events will be tracked and stored in your ClickHouse database

### Querying Data

To query the collected data, connect to your ClickHouse instance:

```bash
docker exec -it simple-snowplow-ch clickhouse-client
```

Example queries:

```sql
-- Get page views from the last 24 hours
SELECT time, page, refr, device_id, session_id
FROM snowplow.local
WHERE event_type = 'page_view'
  AND time > now() - INTERVAL 1 DAY
ORDER BY time DESC;

-- Count events by type
SELECT event_type, count() as events
FROM snowplow.local
GROUP BY event_type
ORDER BY events DESC;
```

## Troubleshooting

### Common Issues

1. **Connection refused to ClickHouse**
   - Check that ClickHouse is running and accessible
   - Verify the host and port in your configuration
   - Ensure firewall rules allow connections

2. **No data being collected**
   - Check browser console for JavaScript errors
   - Verify tracking endpoint is correctly configured in your tracker
   - Check server logs for any errors

3. **Missing data in queries**
   - Verify the table name (it may be different if you configured a custom name)
   - Check if data partitioning is working as expected

### Logs

To view application logs:

```bash
docker logs -f simple-snowplow
```

For more verbose logging, set `logging.level = "DEBUG"` in your configuration.

## Development

### Setting Up the Development Environment

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r simple_snowplow/requirements.txt
   ```

3. Install development tools:
   ```bash
   pip install pre-commit pytest black isort mypy
   pre-commit install
   ```

4. Run the application locally:
   ```bash
   cd simple_snowplow
   uvicorn main:app --reload
   ```

### Configuration System

Simple Snowplow uses a dual-layer configuration system:

1. **Dynaconf** - Handles loading settings from files, environment variables, etc.
2. **Pydantic** - Provides type validation and default values with BaseSettings classes

The main configuration is in `simple_snowplow/core/config.py`, with these components:

- `dynaconf_settings` - Raw Dynaconf settings object
- Pydantic model classes (e.g., `SecurityConfig`, `ClickHouseConfig`)
- `settings` - Main Pydantic settings instance that provides typed access

When extending the configuration:

1. Add new settings to `settings.toml` with appropriate defaults
2. Create or update the corresponding Pydantic model in `core/config.py`
3. Add the new settings class to the main `Settings` class

Example of adding a new configuration section:

```python
# In core/config.py
class NewFeatureConfig(BaseSettings):
    """Configuration for new feature."""
    
    enabled: bool = dynaconf_settings.get("new_feature.enabled", False)
    timeout: int = dynaconf_settings.get("new_feature.timeout", 30)

# Update the main Settings class
class Settings(BaseSettings):
    # Existing settings...
    new_feature: NewFeatureConfig = NewFeatureConfig()
```

### Running Tests

```bash
pytest
```

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
