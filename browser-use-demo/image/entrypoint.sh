#!/bin/bash
set -e

# Validate environment configuration
echo "Validating environment configuration..."
python validate_env.py
if [ $? -ne 0 ]; then
    echo "Environment validation failed. Exiting."
    exit 1
fi

./start_all.sh
./novnc_startup.sh

python http_server.py > /tmp/server_logs.txt 2>&1 &

STREAMLIT_SERVER_PORT=8501 python -m streamlit run browser_use_demo/streamlit.py > /tmp/streamlit_stdout.log &

# Hosted mode: one password-protected port (8000) in front of Streamlit and noVNC.
if [ "$DEMO_HOSTED" = "1" ]; then
    if [ -z "$DEMO_PASSWORD" ]; then
        echo "DEMO_HOSTED=1 needs DEMO_PASSWORD, since the public demo spends your API key. Exiting."
        exit 1
    fi
    printf 'demo:%s\n' "$(openssl passwd -apr1 "$DEMO_PASSWORD")" > /tmp/demo.htpasswd
    nginx -c "$HOME/nginx.conf" -g 'daemon off;' &
    echo "🔒 Hosted demo on port 8000 (user: demo)"
fi

echo "✨ Browser Use Demo is ready!"
echo "➡️  Open http://localhost:8080 in your browser to begin"

# Keep the container running
tail -f /dev/null
