# Biker Relaxed Routing MVP

This project selects the least stressful route using Google Maps traffic data.

## Features

- Uses Google Directions API
- Computes stress score using traffic delay
- Allows acceptable distance increase
- Selects optimal relaxed route

## Setup

1. Install dependencies:

pip install -r requirements.txt

2. Copy .env.example to .env

3. Add your Google Maps API key

4. Run:

### Streamlit UI (recommended)

streamlit run app.py

### CLI (legacy)

python main.py
