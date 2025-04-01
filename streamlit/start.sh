#!/bin/bash

# Start Streamlit in the background
streamlit run /app/app.py --server.port=8501 --server.address=0.0.0.0 &

# Start Nginx in the foreground
nginx -g "daemon off;"