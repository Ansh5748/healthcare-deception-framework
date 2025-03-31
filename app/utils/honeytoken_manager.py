import uuid
import redis
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host='redis', port=6379, db=0)

def generate_honeytoken(context):
    """
    Generate a unique honeytoken and store it in Redis
    """
    token_id = str(uuid.uuid4())
    token_data = {
        "context": context,
        "created_at": datetime.now().isoformat(),
        "accessed": False,
        "access_count": 0,
        "access_ips": []
    }
    
    redis_client.set(f"honeytoken:{token_id}", str(token_data))
    
    logger.info(f"Created honeytoken: {token_id} for context: {context}")
    
    return token_id

def check_honeytoken_access(token_id, ip_address):
    """
    Record access to a honeytoken
    """
    token_key = f"honeytoken:{token_id}"
    token_data_str = redis_client.get(token_key)
    
    if not token_data_str:
        logger.warning(f"Access to non-existent honeytoken: {token_id} from IP: {ip_address}")
        return
    
    token_data_str = token_data_str.decode('utf-8')
    token_data = eval(token_data_str)
    
    token_data["accessed"] = True
    token_data["access_count"] += 1
    token_data["last_accessed"] = datetime.now().isoformat()
    if ip_address not in token_data["access_ips"]:
        token_data["access_ips"].append(ip_address)
    
    redis_client.set(token_key, str(token_data))
    
    logger.warning(f"HONEYTOKEN ACCESSED: {token_id} from IP: {ip_address}, context: {token_data['context']}")
    
    alert_data = {
        "event_type": "honeytoken_access",
        "token_id": token_id,
        "ip_address": ip_address,
        "context": token_data["context"],
        "timestamp": datetime.now().isoformat()
    }
    redis_client.publish("security_alerts", str(alert_data))
