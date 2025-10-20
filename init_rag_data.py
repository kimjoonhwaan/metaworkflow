"""Initialize RAG system with sample knowledge base data"""

import asyncio
import json
from datetime import datetime

from src.database.session import get_session
from src.database.models import KnowledgeBase, KnowledgeBaseCategory, DocumentContentType
from src.services.rag_service import get_rag_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def create_sample_knowledge_bases():
    """Create sample knowledge bases with useful content"""
    
    rag_service = get_rag_service()
    
    # Sample knowledge base data
    sample_data = [
        {
            "name": "Workflow Patterns",
            "description": "Common workflow patterns and templates",
            "category": KnowledgeBaseCategory.WORKFLOW_PATTERNS,
            "documents": [
                {
                    "title": "Data Processing Workflow Pattern",
                    "content_type": DocumentContentType.TEMPLATE,
                    "content": """
# Data Processing Workflow Pattern

This is a common pattern for processing data from external sources:

## Steps:
1. **Data Fetching**: Use API_CALL to retrieve data from external APIs
2. **Data Validation**: Use PYTHON_SCRIPT to validate and clean data
3. **Data Transformation**: Use PYTHON_SCRIPT to transform data format
4. **Data Storage**: Use PYTHON_SCRIPT to save processed data
5. **Notification**: Use NOTIFICATION to alert completion

## Best Practices:
- Always include error handling in PYTHON_SCRIPT steps
- Use structured JSON output format
- Include data validation before processing
- Log important operations to stderr

## Example Variables:
- `api_url`: URL of the data source
- `output_format`: Desired output format (JSON, CSV, etc.)
- `notification_channel`: Where to send completion notification
""",
                    "tags": ["data", "processing", "api", "validation"]
                },
                {
                    "title": "Scheduled Report Generation Pattern",
                    "content_type": DocumentContentType.TEMPLATE,
                    "content": """
# Scheduled Report Generation Pattern

Pattern for generating and distributing reports on a schedule:

## Steps:
1. **Data Collection**: Gather data from multiple sources
2. **Report Generation**: Create formatted report using PYTHON_SCRIPT
3. **Approval Check**: Use APPROVAL step for review
4. **Distribution**: Send report via email or other channels
5. **Archive**: Store report for future reference

## Key Considerations:
- Include approval workflow for important reports
- Use conditional logic for different report types
- Implement proper error handling and retry logic
- Consider timezone handling for scheduled reports

## Common Use Cases:
- Daily sales reports
- Weekly performance summaries
- Monthly analytics reports
""",
                    "tags": ["reporting", "scheduled", "approval", "distribution"]
                }
            ]
        },
        {
            "name": "Error Solutions",
            "description": "Common error solutions and debugging guides",
            "category": KnowledgeBaseCategory.ERROR_SOLUTIONS,
            "documents": [
                {
                    "title": "Python Script Execution Errors",
                    "content_type": DocumentContentType.ERROR_SOLUTION,
                    "content": """
# Common Python Script Execution Errors

## 1. SyntaxError: unterminated string literal

**Cause**: F-string quote nesting issues
```python
# ❌ Wrong
print(f'Title: {item['title']}')

# ✅ Correct
title = item.get('title', 'N/A')
print(f'Title: {title}')
```

## 2. KeyError: 'variable_name'

**Cause**: Variable not found in input data
```python
# ❌ Wrong
data = variables['required_field']

# ✅ Correct
data = variables.get('required_field', [])
if not data:
    print("Warning: No data provided", file=sys.stderr)
    sys.exit(1)
```

## 3. FileNotFoundError: filename too long

**Cause**: Windows filename length limits
```python
# ✅ Solution: Sanitize filenames
import re
def sanitize_filename(name):
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Limit length
    return name[:100] if len(name) > 100 else name
```

## 4. JSON Parsing Errors

**Cause**: Invalid JSON output format
```python
# ✅ Always use try-except for JSON operations
try:
    result = {"status": "success", "data": processed_data}
    print(json.dumps(result))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```
""",
                    "tags": ["python", "errors", "debugging", "syntax"]
                },
                {
                    "title": "API Call Failures",
                    "content_type": DocumentContentType.ERROR_SOLUTION,
                    "content": """
# API Call Failure Solutions

## Common Issues and Solutions:

### 1. Connection Timeout
```python
# Add timeout and retry logic
import time
import requests

def api_call_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

### 2. Authentication Errors
- Check API keys and tokens
- Verify authentication headers
- Handle token expiration and refresh

### 3. Rate Limiting
```python
# Implement rate limiting
import time

def rate_limited_request(url, delay=1):
    time.sleep(delay)
    response = requests.get(url)
    if response.status_code == 429:
        time.sleep(5)  # Wait before retry
        return rate_limited_request(url, delay * 2)
    return response
```

### 4. Data Format Issues
- Always validate response format
- Handle different content types
- Implement proper error handling
""",
                    "tags": ["api", "network", "timeout", "authentication"]
                }
            ]
        },
        {
            "name": "Code Templates",
            "description": "Verified Python code templates",
            "category": KnowledgeBaseCategory.CODE_TEMPLATES,
            "documents": [
                {
                    "title": "Safe Python Script Template",
                    "content_type": DocumentContentType.CODE,
                    "content": """#!/usr/bin/env python3
import json
import sys
from datetime import datetime

def main():
    # Parse variables from command line
    variables = {}
    if '--variables-file' in sys.argv:
        idx = sys.argv.index('--variables-file')
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], 'r') as f:
                variables = json.load(f)
    
    # Log to stderr (for debugging)
    print(f"Processing started at {datetime.now()}", file=sys.stderr)
    
    try:
        # Your main logic here
        input_data = variables.get('input_data', [])
        
        if not input_data:
            print("Warning: No input data provided", file=sys.stderr)
            sys.exit(1)
        
        # Process data safely
        processed_data = []
        for item in input_data:
            # Extract fields safely
            title = item.get('title', '') if isinstance(item, dict) else str(item)
            content = item.get('content', '') if isinstance(item, dict) else ''
            
            # Process item
            processed_item = {
                'processed_title': title.strip(),
                'processed_content': content.strip(),
                'processed_at': datetime.now().isoformat()
            }
            processed_data.append(processed_item)
        
        # Output structured JSON to stdout
        result = {
            'status': 'success',
            'processed_count': len(processed_data),
            'processed_data': processed_data,
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(result))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        result = {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()""",
                    "tags": ["template", "python", "safe", "structured"]
                },
                {
                    "title": "Data Validation Template",
                    "content_type": DocumentContentType.CODE,
                    "content": """#!/usr/bin/env python3
import json
import sys
from datetime import datetime

def validate_data(data, schema):
    # Validate data against schema
    errors = []
    
    for field, rules in schema.items():
        if field not in data:
            if rules.get('required', False):
                errors.append(f"Missing required field: {field}")
        else:
            value = data[field]
            
            # Type validation
            expected_type = rules.get('type')
            if expected_type and not isinstance(value, expected_type):
                errors.append(f"Field {field} must be {expected_type.__name__}")
            
            # Length validation
            if 'min_length' in rules and len(str(value)) < rules['min_length']:
                errors.append(f"Field {field} too short (min: {rules['min_length']})")
            
            if 'max_length' in rules and len(str(value)) > rules['max_length']:
                errors.append(f"Field {field} too long (max: {rules['max_length']})")
    
    return errors

def main():
    # Parse variables
    variables = {}
    if '--variables-file' in sys.argv:
        idx = sys.argv.index('--variables-file')
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], 'r') as f:
                variables = json.load(f)
    
    try:
        data_to_validate = variables.get('data', {})
        validation_schema = variables.get('schema', {})
        
        # Perform validation
        errors = validate_data(data_to_validate, validation_schema)
        
        if errors:
            result = {
                'status': 'validation_failed',
                'errors': errors,
                'valid': False
            }
        else:
            result = {
                'status': 'validation_passed',
                'valid': True,
                'validated_data': data_to_validate
            }
        
        print(json.dumps(result))
        
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        result = {
            'status': 'error',
            'error': str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()""",
                    "tags": ["validation", "schema", "data", "template"]
                }
            ]
        },
        {
            "name": "Integration Examples",
            "description": "Examples of integrating with external services",
            "category": KnowledgeBaseCategory.INTEGRATION_EXAMPLES,
            "documents": [
                {
                    "title": "Email Integration Example",
                    "content_type": DocumentContentType.EXAMPLE,
                    "content": """
# Email Integration Example

## SMTP Email Sending
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(smtp_server, port, username, password, to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        return {"status": wasser", "error": str(e)}
```

## Email Template with Variables
```python
def create_email_template(template, variables):
    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template
```

## Common Email Providers Configuration
- Gmail: smtp.gmail.com:587
- Outlook: smtp-mail.outlook.com:587
- Yahoo: smtp.mail.yahoo.com:587
""",
                    "tags": ["email", "smtp", "integration", "notification"]
                },
                {
                    "title": "Slack Integration Example",
                    "content_type": DocumentContentType.EXAMPLE,
                    "content": """
# Slack Integration Example

## Slack Webhook Integration
```python
import requests
import json

def send_slack_message(webhook_url, message, channel=None):
    payload = {
        "text": message
    }
    
    if channel:
        payload["channel"] = channel
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return {"status": "success", "message": "Message sent to Slack"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

## Rich Slack Messages
```python
def send_rich_slack_message(webhook_url, title, message, color="good"):
    payload = {
        "attachments": [{
            "color": color,
            "title": title,
            "text": message,
            "footer": "Workflow System",
            "ts": int(time.time())
        }]
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.json()
```

## Slack App Integration
- Use Slack Apps for more advanced integrations
- Bot tokens for interactive features
- OAuth for user-specific actions
""",
                    "tags": ["slack", "webhook", "notification", "integration"]
                }
            ]
        }
    ]
    
    # Create knowledge bases and documents
    for kb_data in sample_data:
        try:
            logger.info(f"Creating knowledge base: {kb_data['name']}")
            
            # Create knowledge base
            kb_id = await rag_service.create_knowledge_base(
                name=kb_data['name'],
                description=kb_data['description'],
                category=kb_data['category']
            )
            
            # Add documents
            for doc_data in kb_data['documents']:
                logger.info(f"Adding document: {doc_data['title']}")
                
                doc_id = await rag_service.add_document(
                    knowledge_base_id=kb_id,
                    title=doc_data['title'],
                    content=doc_data['content'],
                    content_type=doc_data['content_type'],
                    tags=doc_data.get('tags', [])
                )
                
                logger.info(f"Document {doc_data['title']} added with ID: {doc_id}")
        
        except Exception as e:
            logger.error(f"Failed to create knowledge base {kb_data['name']}: {e}")
    
    logger.info("Sample knowledge bases created successfully!")


async def main():
    """Main function to initialize RAG data"""
    logger.info("Initializing RAG system with sample data...")
    
    try:
        await create_sample_knowledge_bases()
        logger.info("RAG system initialization completed!")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
