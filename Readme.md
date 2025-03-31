# Healthcare System Deception Framework

A deliberately vulnerable healthcare system honeypot designed to attract, monitor, and analyze attacker behavior. This project creates a fake healthcare portal with embedded honeytokens and comprehensive monitoring.

## 🚨 Security Warning

⚠️ **IMPORTANT**: This system is deliberately vulnerable and should only be deployed in isolated environments for educational or research purposes. Never expose this system to the internet or use it in a production environment.

## 🌟 Features

- 🏥 Fake healthcare web portal with realistic patient data
- 🍯 Honeytokens embedded throughout the system
- 🔍 Comprehensive monitoring of all system interactions
- 📊 ELK Stack integration for log analysis and visualization
- 🚨 Real-time alerts for honeytoken access
- 🔓 Deliberately vulnerable authentication and API endpoints

## 📋 Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Ansh5748/healthcare-deception-framework.git
cd healthcare-deception-framework

# Build and start the containers
docker-compose build
docker-compose up
```

## 🖥️ Access Points

Once the containers are running, you can access:

- **Web Application**: http://localhost:5002
- **Kibana Dashboard**: http://localhost:5602
- **Elasticsearch API**: http://localhost:9201

## 🔑 Test Credentials

Use these deliberately weak credentials to test the system:

| Username | Password    | Role          |
|----------|-------------|---------------|
| admin    | password123 | Administrator |
| doctor   | medical     | Physician     |
| nurse    | nurse123    | Nurse         |

## 📊 Monitoring

The system logs all interactions and specifically tracks honeytoken access:

- **View logs in Kibana**: http://localhost:5602
  - Create an index pattern for "healthcare-deception-*"
  - Build visualizations for security events

- **Check Redis for honeytoken access**:
  ```bash
  docker exec -it healthcare-deception-framework-redis-1 redis-cli
  SUBSCRIBE security_alerts
  ```

## 📁 Project Structure

```
healthcare-deception-framework/
├── app/                      # Web application
│   ├── simple_server.py      # Main application file
│   └── requirements.txt      # Python dependencies
├── monitoring/               # ELK Stack configuration
│   ├── elasticsearch/        # Elasticsearch config
│   ├── kibana/               # Kibana config
│   └── logstash/             # Logstash config & pipelines
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker build instructions
└── README.md                 # This file
```

## 🔧 Configuration

### Modifying Ports

If you encounter port conflicts, modify the port mappings in `docker-compose.yml`:

```yaml
services:
  web:
    ports:
      - "5002:5002"  # Change the first number to use a different port
  
  redis:
    ports:
      - "6380:6379"  # Redis port
  
  elasticsearch:
    ports:
      - "9201:9200"  # Elasticsearch port
  
  kibana:
    ports:
      - "5602:5601"  # Kibana port
```

## 🛠️ Troubleshooting

### Redis Connection Issues

If the application can't connect to Redis:

```bash
# Check if Redis is running
docker-compose ps redis

# Restart Redis if needed
docker-compose restart redis
```

### Elasticsearch Issues

Elasticsearch requires adequate system resources. If it fails to start:

- Increase Docker's memory allocation in Docker Desktop settings
- Modify the ES_JAVA_OPTS in docker-compose.yml:
  ```yaml
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms256m -Xmx256m"  # Reduce memory usage
  ```

## ⏹️ Stopping the Application

```bash
# Stop the containers
docker-compose down

# Remove all data and volumes
docker-compose down -v
```

## 🧪 Testing Honeytokens

1. Log in using one of the provided credentials
2. Navigate to the patient records section
3. View the page source to find honeytokens
4. Access a honeytoken URL to trigger an alert
5. Check the logs in Kibana to see the alert

## 📚 Educational Resources

This project demonstrates several cybersecurity concepts:

- Honeypots and deception technology
- Web application security vulnerabilities
- Security monitoring and alerting
- Log analysis and visualization

## 👥 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

