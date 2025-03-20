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

Simple Snowplow can be configured via a TOML configuration file and environment variables. The application uses the following configuration hierarchy:

1. Default settings from `settings.toml`
2. Environment variables with `SNOWPLOW_` prefix
3. Custom settings file specified with `SNOWPLOW_SETTINGS_FILE`

### Main Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `common.service_name` | Application name | `simple-snowplow` |
| `common.demo` | Enable demo mode | `false` |
| `logging.level` | Log level (DEBUG, INFO, WARNING, ERROR) | `WARNING` |
| `clickhouse.connection.host` | ClickHouse host | `clickhouse` |
| `clickhouse.connection.port` | ClickHouse port | `8123` |
| `clickhouse.configuration.database` | ClickHouse database | `snowplow` |
| `clickhouse.configuration.cluster_name` | ClickHouse cluster name (if using) | `""` |

For a complete list of configuration options, refer to the `settings.toml` file.

### Environment Variables

You can override any configuration setting using environment variables with the `SNOWPLOW_` prefix. For example:

```bash
SNOWPLOW_COMMON__DEMO=true
SNOWPLOW_CLICKHOUSE__CONNECTION__HOST=my-clickhouse-server
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

### Running Tests

```bash
pytest
```

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
