import csv
import requests
import os

# Define constants for API URLs
API_BASE_URL = "yourhaloapiURL"
CATEGORY_URL = f"{API_BASE_URL}/category"
TEMPLATE_URL = f"{API_BASE_URL}/template"
RULE_URL = f"{API_BASE_URL}/ticketrules"
OAUTH2_TOKEN_URL = "youroauth2URL"

# OAuth2 client credentials (replace these with your actual credentials)
CLIENT_ID = "yourclientID"
CLIENT_SECRET = "yourclientsecret"
SCOPE = "all"  # Usually, it's something like 'api' or the specific scope your app needs

# Function to obtain OAuth2 access token using client credentials
def get_oauth_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE
    }
    
    response = requests.post(OAUTH2_TOKEN_URL, data=data)
    auth_token = response.json().get("access_token")
    
    if response.status_code == 200:
        return auth_token
    else:
        raise Exception(f"Failed to obtain OAuth token: {response.text}")

# Function to process CSV file and map tasks
def process_csv(file_path):
    tasks_map = {}

    # Try reading as UTF-8 first, fallback to Windows-1252 if it fails
    try:
        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except UnicodeDecodeError:
        print("⚠️ UTF-8 decoding failed. Retrying with Windows-1252 encoding...")
        with open(file_path, newline='', encoding='cp1252', errors='replace') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

    # Process the rows into tasks_map
    for row in rows:
        try:
            key = f"{row['Type']}>{row['Subtype']}>{row['Item']}"
            task = row.get('Task', '').strip()
            priority = row.get('Priority', '1')

            if task:
                if key not in tasks_map:
                    tasks_map[key] = []
                tasks_map[key].append({"text": task})
        except KeyError as e:
            print(f"⚠️ Missing expected column in CSV: {e}")
        except Exception as e:
            print(f"⚠️ Error processing row: {e}")

    return tasks_map

# Function to create categories in HaloPSA
def create_category(name, token):
    
    category_data = [
        {
            "category_name": name,
            "value": name,
			"type_id": 1
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    category_response = requests.post(CATEGORY_URL, headers=headers, json=category_data)
    if category_response.status_code == 201:
        print(f"✔️ Category '{name}' created successfully!")
    else:
        print(f"❌ Error: {category_response.status_code}, Failed to create category '{name}'")

# Function to create templates in HaloPSA
def create_template(name, tasks, token):

    template_data = [
        {
            "name": name,
            "tickettype_id": 1,
            "todo_list": tasks
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    template_response = requests.post(TEMPLATE_URL, headers=headers, json=template_data)
    if template_response.status_code == 201:
        try:
            response_data = template_response.json()
            template_id = response_data['id']
            print(f"✔️ Template '{name}' created successfully!")
            return template_id
        except (KeyError, IndexError, ValueError) as e:
            print(f"❌ Parsing Error: {e}")
            #print(f"Raw Response: {template_response.status_code} {template_response.text}")
            return None
    else:
        print(f"❌ Error: {template_response.status_code}, Failed to create template '{name}'")
        #print(f"Response Text: {template_response.text}")
        return None

# Function to create ticket rules in HaloPSA
def create_rule(name, template_id, token):

    rule_data = [
        {
            "name": name,
            "use": "0",
            "criteria": [
                {
                    "fieldname": "category2",
                    "value_type": "string",
                    "tablename": "faults",
                    "type": 0,
                    "value_string": name,
                    "value_display": name
                }
            ],
            "new_priority_id": "1",
            "new_template_id": template_id
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    rule_response = requests.post(RULE_URL, headers=headers, json=rule_data)
    if rule_response.status_code == 201:
        print(f"✔️ Rule for '{name}' created successfully!")
    else:
        print(f"❌ Error: {rule_response.status_code}, Failed to create rule for '{name}'")
        #print(f"Response Text: {rule_response.text}")

# Main function
def main():
    try:
        # Step 1: Get OAuth2 token
        token = get_oauth_token()

        # Step 2: Process CSV file
        file_path = os.path.expanduser("~/Downloads/ticket-template.csv")
        tasks_map = process_csv(file_path)
        
        # Step 3: Create categories, templates, and rules
        for name, tasks in tasks_map.items():
            create_category(name, token)    # create category
            template_id = create_template(name, tasks, token)    # create template
            if template_id:
                create_rule(name, template_id, token)    # create rule
            else:
                print(f"⚠️ Skipping rule creation for '{name}' due to missing template ID.")

    except Exception as e:
        print(f"Error: {e}")
        #print(f"Response Text: {e.response.text}")

if __name__ == "__main__":
    main()
def run_halo_upload(csv_path, base_url, oauth_url, client_id, client_secret):
    global API_BASE_URL, CATEGORY_URL, TEMPLATE_URL, RULE_URL, OAUTH2_TOKEN_URL, CLIENT_ID, CLIENT_SECRET

    # Override global config dynamically
    API_BASE_URL = base_url
    CATEGORY_URL = f"{API_BASE_URL}/category"
    TEMPLATE_URL = f"{API_BASE_URL}/template"
    RULE_URL = f"{API_BASE_URL}/ticketrules"
    OAUTH2_TOKEN_URL = oauth_url
    CLIENT_ID = client_id
    CLIENT_SECRET = client_secret

    try:
        token = get_oauth_token()
        tasks_map = process_csv(csv_path)

        for name, tasks in tasks_map.items():
            create_category(name, token)
            template_id = create_template(name, tasks, token)
            if template_id:
                create_rule(name, template_id, token)
            else:
                print(f"⚠️ Skipping rule creation for '{name}' due to missing template ID.")
        return "Upload completed successfully."

    except Exception as e:
        return f"Error: {e}"
