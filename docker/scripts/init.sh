
echo "Initializing Healthcare System Deception Framework..."

echo "Waiting for Elasticsearch..."
until curl -s http://elasticsearch:9200 >/dev/null; do
    sleep 1
done
echo "Elasticsearch is up!"

echo "Waiting for Kibana..."
until curl -s http://kibana:5601 >/dev/null; do
    sleep 1
done
echo "Kibana is up!"

echo "Setting up monitoring dashboards..."

echo "Starting Healthcare Deception Framework..."
python /app/simple_server.py
