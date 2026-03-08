#!/bin/bash
pkill -f "streamlit run app.py" 2>/dev/null
sleep 1
source .venv/bin/activate
streamlit run app.py
