# Biker Relaxed Routing MVP

This project selects the least stressful route using Google Maps traffic data.

## Features

- Uses Google Directions API (driving mode for traffic-aware stress)
- Computes stress score using traffic delay
- Allows acceptable distance increase
- Selects optimal relaxed route

## Setup

1. Install dependencies:

pip install -r requirements.txt

2. Add your Google Maps API key (recommended: Streamlit secrets)

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_MAPS_API_KEY = "PASTE_KEY_HERE"
```

Alternatively, you can set an environment variable:

```bash
export GOOGLE_MAPS_API_KEY="PASTE_KEY_HERE"
```

## Logging

This project uses Python's built-in `logging`.

- Default log level: `INFO`
- Enable debug logs:

```bash
export LOG_LEVEL=DEBUG
```

The log file captures DEBUG by default. You can change file verbosity separately:

```bash
export LOG_FILE_LEVEL=INFO
```

By default, the log file is **overwritten on each run** (fresh log). To append across runs:

```bash
export LOG_APPEND=1
```

Logs are written to both:
- console (stdout)
- a rotating log file (default: `logs/bikers_map.log`)

You can override the log file path and rotation limits:

```bash
export LOG_FILE="logs/bikers_map.log"
export LOG_MAX_BYTES=2000000
export LOG_BACKUP_COUNT=3
```

If you see noisy Streamlit/watchdog entries, you can quiet specific loggers:

```bash
export LOG_QUIET_LOGGERS="watchdog,streamlit,urllib3"
```

4. Run:

### Streamlit UI (recommended)

streamlit run app.py

### CLI (legacy)

python main.py
