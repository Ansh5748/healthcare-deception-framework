from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import uuid
import time
from urllib.parse import parse_qs, urlparse
import logging
import redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

USERS = {
    "admin": "password123",
    "doctor": "medical",
    "nurse": "nurse123"
}


PATIENTS = {
    "P12345": {
        "id": "P12345",
        "name": "John Smith",
        "dob": "1975-05-15",
        "ssn": "123-45-6789", 
        "diagnosis": "Hypertension",
        "medications": ["Lisinopril", "Hydrochlorothiazide"],
        "doctor": "Dr. Sarah Johnson",
        "last_visit": "2023-03-15"
    },
    "P67890": {
        "id": "P67890",
        "name": "Emily Davis",
        "dob": "1988-11-23",
        "ssn": "987-65-4321",
        "diagnosis": "Type 2 Diabetes",
        "medications": ["Metformin", "Glipizide"],
        "doctor": "Dr. Michael Chen",
        "last_visit": "2023-03-20"
    },
    "P24680": {
        "id": "P24680",
        "name": "Michael Johnson",
        "dob": "1965-08-12",
        "ssn": "456-78-9012",
        "diagnosis": "Asthma",
        "medications": ["Albuterol", "Fluticasone"],
        "doctor": "Dr. Lisa Wong",
        "last_visit": "2023-03-22"
    },
    "P13579": {
        "id": "P13579",
        "name": "Sarah Williams",
        "dob": "1982-02-28",
        "ssn": "789-01-2345",
        "diagnosis": "Arthritis",
        "medications": ["Ibuprofen", "Prednisone"],
        "doctor": "Dr. Robert Brown",
        "last_visit": "2023-03-25"
    }
}


APPOINTMENTS = [
    {"id": "A1001", "patient_id": "P12345", "patient_name": "John Smith", "date": "2023-03-30", "time": "09:00", "doctor": "Dr. Sarah Johnson", "reason": "Follow-up"},
    {"id": "A1002", "patient_id": "P67890", "patient_name": "Emily Davis", "date": "2023-03-30", "time": "10:30", "doctor": "Dr. Michael Chen", "reason": "Medication review"},
    {"id": "A1003", "patient_id": "P24680", "patient_name": "Michael Johnson", "date": "2023-03-30", "time": "13:15", "doctor": "Dr. Lisa Wong", "reason": "Annual checkup"},
    {"id": "A1004", "patient_id": "P13579", "patient_name": "Sarah Williams", "date": "2023-03-30", "time": "15:45", "doctor": "Dr. Robert Brown", "reason": "Pain management"},
    {"id": "A1005", "patient_id": "P12345", "patient_name": "John Smith", "date": "2023-04-15", "time": "11:00", "doctor": "Dr. Sarah Johnson", "reason": "Blood pressure check"}
]


PRESCRIPTIONS = [
    {"id": "RX1001", "patient_id": "P12345", "patient_name": "John Smith", "medication": "Lisinopril", "dosage": "10mg", "frequency": "Once daily", "prescribed_date": "2023-02-15", "refills": 3},
    {"id": "RX1002", "patient_id": "P12345", "patient_name": "John Smith", "medication": "Hydrochlorothiazide", "dosage": "25mg", "frequency": "Once daily", "prescribed_date": "2023-02-15", "refills": 3},
    {"id": "RX1003", "patient_id": "P67890", "patient_name": "Emily Davis", "medication": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "prescribed_date": "2023-03-01", "refills": 5},
    {"id": "RX1004", "patient_id": "P67890", "patient_name": "Emily Davis", "medication": "Glipizide", "dosage": "5mg", "frequency": "Once daily", "prescribed_date": "2023-03-01", "refills": 5},
    {"id": "RX1005", "patient_id": "P24680", "patient_name": "Michael Johnson", "medication": "Albuterol", "dosage": "90mcg", "frequency": "As needed", "prescribed_date": "2023-02-20", "refills": 2},
    {"id": "RX1006", "patient_id": "P24680", "patient_name": "Michael Johnson", "medication": "Fluticasone", "dosage": "110mcg", "frequency": "Twice daily", "prescribed_date": "2023-02-20", "refills": 2},
    {"id": "RX1007", "patient_id": "P13579", "patient_name": "Sarah Williams", "medication": "Ibuprofen", "dosage": "600mg", "frequency": "Every 6 hours as needed", "prescribed_date": "2023-03-10", "refills": 1},
    {"id": "RX1008", "patient_id": "P13579", "patient_name": "Sarah Williams", "medication": "Prednisone", "dosage": "10mg", "frequency": "Once daily", "prescribed_date": "2023-03-10", "refills": 0}
]

# Track honeytokens
HONEYTOKENS = {}

try:
    redis_client = redis.Redis(host='redis', port=6379, db=0)
    redis_client.ping()  # Test connection
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None
    
def generate_honeytoken(context):
    """Generate a unique honeytoken and log it"""
    token_id = str(uuid.uuid4())
    HONEYTOKENS[token_id] = {
        "context": context,
        "created_at": time.time(),
        "accessed": False,
        "access_count": 0,
        "access_ips": []
    }
    logger.info(f"Created honeytoken: {token_id} for context: {context}")
    return token_id

def check_honeytoken_access(token_id, ip_address):
    """Record access to a honeytoken"""
    if token_id not in HONEYTOKENS:
        logger.warning(f"Access to non-existent honeytoken: {token_id} from IP: {ip_address}")
        return
    
    token_data = HONEYTOKENS[token_id]
    token_data["accessed"] = True
    token_data["access_count"] += 1
    token_data["last_accessed"] = time.time()
    if ip_address not in token_data["access_ips"]:
        token_data["access_ips"].append(ip_address)
    
    logger.warning(f"HONEYTOKEN ACCESSED: {token_id} from IP: {ip_address}, context: {token_data['context']}")

    # Publish to Redis for real-time monitoring
    if redis_client:
        try:
            alert_data = {
                "event_type": "honeytoken_access",
                "token_id": token_id,
                "ip_address": ip_address,
                "context": token_data['context'],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "access_count": token_data["access_count"]
            }
            redis_client.publish("security_alerts", json.dumps(alert_data))
            logger.info(f"Published honeytoken access to Redis: {token_id}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

class HealthcareHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query) if parsed_url.query else {}
        
        # Generate a honeytoken for this request
        honeytoken = generate_honeytoken(f"page_visit:{path}")
        
        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_homepage(honeytoken).encode())
        elif path == '/login':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_message = ""
            if query and 'error' in query:
                error_message = '<div class="error">Invalid username or password. Please try again.</div>'
            
            self.wfile.write(self.render_login_page(honeytoken, error_message).encode())
        elif path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_dashboard(honeytoken).encode())
        elif path == '/patients':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_patients_page(honeytoken).encode())
        elif path.startswith('/patient/'):
            patient_id = path.split('/')[2]
            if patient_id in PATIENTS:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(self.render_patient_details(patient_id, honeytoken).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(self.render_404_page().encode())
        elif path == '/appointments':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_appointments_page(honeytoken).encode())
        elif path == '/prescriptions':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_prescriptions_page(honeytoken).encode())
        elif path == '/admin':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_admin_page(honeytoken).encode())
        elif path == '/backup':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_backup_page(honeytoken).encode())
        elif path == '/honeytoken' and query and 'token' in query:
            token = query['token'][0]
            client_ip = self.client_address[0]
            check_honeytoken_access(token, client_ip)
            
            # Redirect to homepage to make it less obvious
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
        elif path == '/api/patients':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(list(PATIENTS.values())).encode())
        elif path.startswith('/api/patients/'):
            patient_id = path.split('/')[3]
            if patient_id in PATIENTS:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(PATIENTS[patient_id]).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Patient not found"}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_404_page().encode())
    
    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parse form data
            form_data = {}
            for item in post_data.split('&'):
                key, value = item.split('=')
                form_data[key] = value
            
            username = form_data.get('username', '')
            password = form_data.get('password', '')
            
            # Log login attempts
            logger.info(f"Login attempt: username={username}, password={password}")
            
            # Publish login attempt to Redis
            if redis_client:
                try:
                    client_ip = self.client_address[0]
                    login_data = {
                        "event_type": "login_attempt",
                        "username": username,
                        "password": password,
                        "ip_address": client_ip,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "success": username in USERS and USERS[username] == password
                    }
                    redis_client.publish("security_alerts", json.dumps(login_data))
                except Exception as e:
                    logger.error(f"Failed to publish login attempt to Redis: {e}")

            # Check credentials
            if username in USERS and USERS[username] == password:
                # Successful login
                self.send_response(302)
                self.send_header('Location', '/dashboard')
                self.end_headers()
            else:
                # Failed login
                self.send_response(302)
                self.send_header('Location', '/login?error=1')
                self.end_headers()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.render_404_page().encode())
    
    def render_homepage(self, honeytoken):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                .login-box {{ max-width: 400px; margin: 20px auto; padding: 20px; background-color: #f0f0f0; border-radius: 5px; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Deception Framework</h1>
            <p>This is a simple test page for the Healthcare System Deception Framework.</p>
            
            <div class="login-box">
                <h2>Login</h2>
                <p>Use these credentials:</p>
                <ul>
                    <li>Username: admin, Password: password123</li>
                    <li>Username: doctor, Password: medical</li>
                    <li>Username: nurse, Password: nurse123</li>
                </ul>
                <a href="/login" class="btn">Go to Login</a>
            </div>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_login_page(self, honeytoken, error_message=""):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                .login-form {{ max-width: 400px; margin: 0 auto; padding: 20px; background-color: #f0f0f0; border-radius: 5px; }}
                .form-group {{ margin-bottom: 15px; }}
                label {{ display: block; margin-bottom: 5px; }}
                input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; }}
                .error {{ color: red; margin-bottom: 15px; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <div class="login-form">
                <h2>Login</h2>
                {error_message}
                <form method="post" action="/login">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    
                    <button type="submit" class="btn">Login</button>
                </form>
            </div>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_dashboard(self, honeytoken):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                .dashboard {{ padding: 20px; background-color: #f0f0f0; border-radius: 5px; }}
                .stats {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
                .stat-card {{ flex: 1; margin: 10px; padding: 15px; background-color: white; border-radius: 5px; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #0056b3; }}
                .patient-list {{ background-color: white; padding: 15px; border-radius: 5px; }}
                .patient-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <div class="dashboard">
                <h2>Dashboard</h2>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">42</div>
                        <div>Patients</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">12</div>
                        <div>Appointments Today</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">8</div>
                        <div>New Prescriptions</div>
                    </div>
                </div>
                
                <h3>Recent Patients</h3>
                <div class="patient-list">
                    <div class="patient-item">
                        <strong>John Smith</strong> - Hypertension - Last Visit: 2023-03-15
                    </div>
                    <div class="patient-item">
                        <strong>Emily Davis</strong> - Type 2 Diabetes - Last Visit: 2023-03-20
                    </div>
                    <div class="patient-item">
                        <strong>Michael Johnson</strong> - Asthma - Last Visit: 2023-03-22
                    </div>
                    <div class="patient-item">
                        <strong>Sarah Williams</strong> - Arthritis - Last Visit: 2023-03-25
                    </div>
                </div>
            </div>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_patients_page(self, honeytoken):
        patients_html = ""
        for patient_id, patient in PATIENTS.items():
            patients_html += f"""
            <tr>
                <td>{patient_id}</td>
                <td>{patient['name']}</td>
                <td>{patient['dob']}</td>
                <td>{patient['diagnosis']}</td>
                <td>{patient['doctor']}</td>
                <td>
                    <a href="/patient/{patient_id}" class="btn-small">View Details</a>
                </td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Patients - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .btn-small {{ background-color: #0056b3; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <h2>Patient Records</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Date of Birth</th>
                        <th>Diagnosis</th>
                        <th>Doctor</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {patients_html}
                </tbody>
            </table>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_patient_details(self, patient_id, honeytoken):
        patient = PATIENTS[patient_id]
        medications_html = ""
        for medication in patient['medications']:
            medications_html += f"<li>{medication}</li>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Patient Details - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                .patient-info {{ margin-bottom: 20px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; }}
                .info-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
                .info-item {{ margin-bottom: 10px; }}
                label {{ font-weight: bold; display: block; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <h2>Patient Details: {patient['name']}</h2>
            <p><a href="/patients">&larr; Back to Patient List</a></p>
            
            <div class="patient-info">
                <h3>Personal Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Patient ID:</label>
                        <span>{patient_id}</span>
                    </div>
                    <div class="info-item">
                        <label>Name:</label>
                        <span>{patient['name']}</span>
                    </div>
                    <div class="info-item">
                        <label>Date of Birth:</label>
                        <span>{patient['dob']}</span>
                    </div>
                    <div class="info-item">
                        <label>SSN:</label>
                        <span>{patient['ssn']}</span>
                    </div>
                </div>
            </div>
            
            <div class="patient-info">
                <h3>Medical Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Diagnosis:</label>
                        <span>{patient['diagnosis']}</span>
                    </div>
                    <div class="info-item">
                        <label>Primary Doctor:</label>
                        <span>{patient['doctor']}</span>
                    </div>
                </div>
            </div>
            
            <div class="patient-info">
                <h3>Medications</h3>
                <ul>
                    {medications_html}
                </ul>
            </div>
            
            <div class="patient-info">
                <h3>Notes</h3>
                <div id="patient-notes">
                    <p>No notes available for this patient.</p>
                </div>
                <button class="btn" onclick="showPatientNotes('{patient_id}', 'Patient reports feeling better after medication change.')">Show Notes</button>
            </div>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
            
            <script>
                // Deliberately vulnerable inline script
                function showPatientNotes(patientId, notes) {{
                    document.getElementById('patient-notes').innerHTML = '<p>' + notes + '</p>';
                    
                    // Store sensitive data in localStorage (deliberately insecure)
                    const patientData = {{
                        id: "{patient_id}",
                        name: "{patient['name']}",
                        ssn: "{patient['ssn']}"
                    }};
                    
                    localStorage.setItem("currentPatient", JSON.stringify(patientData));
                }}
            </script>
        </body>
        </html>
        """
    
    def render_appointments_page(self, honeytoken):
        appointments_html = ""
        for appointment in APPOINTMENTS:
            appointments_html += f"""
            <tr>
                <td>{appointment['id']}</td>
                <td>{appointment['patient_name']}</td>
                <td>{appointment['date']}</td>
                <td>{appointment['time']}</td>
                <td>{appointment['doctor']}</td>
                <td>{appointment['reason']}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Appointments - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <h2>Appointments</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Patient</th>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Doctor</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
                    {appointments_html}
                </tbody>
            </table>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_prescriptions_page(self, honeytoken):
        prescriptions_html = ""
        for prescription in PRESCRIPTIONS:
            prescriptions_html += f"""
            <tr>
                <td>{prescription['id']}</td>
                <td>{prescription['patient_name']}</td>
                <td>{prescription['medication']}</td>
                <td>{prescription['dosage']}</td>
                <td>{prescription['frequency']}</td>
                <td>{prescription['prescribed_date']}</td>
                <td>{prescription['refills']}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prescriptions - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <h2>Prescriptions</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Patient</th>
                        <th>Medication</th>
                        <th>Dosage</th>
                        <th>Frequency</th>
                        <th>Prescribed Date</th>
                        <th>Refills</th>
                    </tr>
                </thead>
                <tbody>
                    {prescriptions_html}
                </tbody>
            </table>
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_admin_page(self, honeytoken):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Panel - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                .admin-section {{ margin-bottom: 30px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; }}
                .admin-actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .btn-small {{ background-color: #0056b3; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; }}
                .info-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
                .info-item {{ margin-bottom: 10px; }}
                label {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <h2>Admin Control Panel</h2>
            
            <div class="admin-section">
                <h3>System Management</h3>
                <div class="admin-actions">
                    <button class="btn">User Management</button>
                    <button class="btn">System Settings</button>
                    <button class="btn">View Logs</button>
                    <a href="/backup" class="btn">Database Backup</a>
                </div>
            </div>
            
            <div class="admin-section">
                <h3>User Accounts</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Role</th>
                            <th>Last Login</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>admin</td>
                            <td>Administrator</td>
                            <td>2023-10-15 08:45</td>
                            <td>
                                <button class="btn-small">Edit</button>
                                <button class="btn-small">Reset Password</button>
                            </td>
                        </tr>
                        <tr>
                            <td>doctor</td>
                            <td>Physician</td>
                            <td>2023-10-14 14:22</td>
                            <td>
                                <button class="btn-small">Edit</button>
                                <button class="btn-small">Reset Password</button>
                            </td>
                        </tr>
                        <tr>
                            <td>nurse</td>
                            <td>Nurse</td>
                            <td>2023-10-15 09:17</td>
                            <td>
                                <button class="btn-small">Edit</button>
                                <button class="btn-small">Reset Password</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="admin-section">
                <h3>System Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <label>System Version:</label>
                        <span>MediCare Plus v1.2.3</span>
                    </div>
                    <div class="info-item">
                        <label>Database:</label>
                        <span>MySQL 5.6.24</span>
                    </div>
                    <div class="info-item">
                        <label>Server:</label>
                        <span>Apache 2.4.12</span>
                    </div>
                    <div class="info-item">
                        <label>PHP Version:</label>
                        <span>5.6.8</span>
                    </div>
                </div>
            </div>
            
            <!-- Hidden configuration data as a comment -->
            <!-- 
            Database connection:
            host: localhost
            user: dbadmin
            pass: db@dmin123
            name: medicare_db
            -->
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_backup_page(self, honeytoken):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Backup - Healthcare System</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #0056b3; }}
                nav {{ background-color: #0056b3; padding: 10px; margin-bottom: 20px; }}
                nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
                .admin-section {{ margin-bottom: 30px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; }}
                .form-group {{ margin-bottom: 15px; }}
                label {{ display: block; margin-bottom: 5px; }}
                input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
                .checkbox-group {{ margin-bottom: 10px; }}
                .btn {{ background-color: #0056b3; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .btn-small {{ background-color: #0056b3; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Healthcare System Portal</h1>
            
            <nav>
                <a href="/dashboard">Dashboard</a>
                <a href="/patients">Patients</a>
                <a href="/appointments">Appointments</a>
                <a href="/prescriptions">Prescriptions</a>
                <a href="/">Logout</a>
            </nav>
            
            <h2>System Backup</h2>
            
            <div class="admin-section">
                <h3>Database Backup</h3>
                <p>Create a backup of the entire database system.</p>
                
                <form action="#" method="post" class="backup-form">
                    <div class="form-group">
                        <label for="backup-name">Backup Name:</label>
                        <input type="text" id="backup-name" name="backup-name" value="backup_20231015" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Backup Options:</label>
                        <div class="checkbox-group">
                            <input type="checkbox" id="include-patient-data" name="include-patient-data" checked>
                            <label for="include-patient-data">Include Patient Data</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="include-system-config" name="include-system-config" checked>
                            <label for="include-system-config">Include System Configuration</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="include-user-accounts" name="include-user-accounts" checked>
                            <label for="include-user-accounts">Include User Accounts</label>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">Start Backup</button>
                </form>
            </div>
            
            <div class="admin-section">
                <h3>Previous Backups</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Backup Name</th>
                            <th>Date</th>
                            <th>Size</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>backup_20231010</td>
                            <td>2023-10-10 03:00</td>
                            <td>245 MB</td>
                            <td>
                                <a href="#" class="btn-small">Download</a>
                                <a href="#" class="btn-small">Delete</a>
                            </td>
                        </tr>
                        <tr>
                            <td>backup_20231003</td>
                            <td>2023-10-03 03:00</td>
                            <td>242 MB</td>
                            <td>
                                <a href="#" class="btn-small">Download</a>
                                <a href="#" class="btn-small">Delete</a>
                            </td>
                        </tr>
                        <tr>
                            <td>backup_20230926</td>
                            <td>2023-09-26 03:00</td>
                            <td>238 MB</td>
                            <td>
                                <a href="#" class="btn-small">Download</a>
                                <a href="#" class="btn-small">Delete</a>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- Hidden backup path information -->
            <!-- Backup storage path: /var/www/medicare/backups/ -->
            <!-- Backup server credentials: backup_user / B@ckup2023! -->
            
            <!-- Hidden honeytoken -->
            <!-- Honeytoken: {honeytoken} -->
        </body>
        </html>
        """
    
    def render_404_page(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Not Found</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                h1 { color: #0056b3; }
            </style>
        </head>
        <body>
            <h1>404 - Page Not Found</h1>
            <p>The page you requested could not be found.</p>
            <a href="/">Return to Home</a>
        </body>
        </html>
        """

if __name__ == '__main__':
    server_address = ('', 5002)
    httpd = HTTPServer(server_address, HealthcareHandler)
    print(f"Server running at http://localhost:5002")
    httpd.serve_forever()
