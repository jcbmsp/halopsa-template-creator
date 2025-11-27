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
    SCOPE = "all"  # Usually something like 'api'

    # -------------------------------------------
    # OAuth2 Token Function
    # -------------------------------------------
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


    # -------------------------------------------
    # TicketType → ID Mapping
    # -------------------------------------------
    def resolve_type_id(tickettype, token):
        if not tickettype:
            print("⚠ No ticket type provided. Defaulting to Incident (ID=1)")
            return 1

        tickettype_clean = tickettype.strip().lower()

        url = f"{API_BASE_URL}/TicketType"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            tickettypes = resp.json()

            for t in tickettypes:
                print(t.get("id"), t.get("name"))

            # ---- 1. Exact match ----
            for t in tickettypes:
                if t.get("name", "").strip().lower() == tickettype_clean:
                    print(f"✔ Exact match → {t['name']} (ID={t['id']})")
                    return t["id"]

            # ---- 2. Partial match ----
            for t in tickettypes:
                api_name = t.get("name", "").strip().lower()
                if tickettype_clean in api_name or api_name in tickettype_clean:
                    print(f"✔ Partial match → {t['name']} (ID={t['id']})")
                    return t["id"]

            print("❌ No match found. Using fallback ID=1")
            return 1

        except Exception as e:
            print(f"⚠ Error retrieving ticket types: {e}")
            return 1
    # -------------------------------------------
    # Process CSV
    # -------------------------------------------
    def process_csv(file_path):
        tasks_map = {}

        # Try UTF-8, fallback to cp1252
        try:
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
        except UnicodeDecodeError:
            print("⚠️ UTF-8 decoding failed. Retrying with Windows-1252 encoding...")
            with open(file_path, newline='', encoding='cp1252', errors='replace') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

        # Process rows
        for row in rows:
            try:
                key = f"{row['Type']}>{row['Subtype']}>{row['Item']}"
                task = row.get('Task', '').strip()
                ticket_type = row.get('TicketType', '').strip()

                if key not in tasks_map:
                    tasks_map[key] = {
                        "tasks": [],
                        "tickettype": ticket_type
                    }

                if task:
                    tasks_map[key]["tasks"].append({"text": task})

            except Exception as e:
                print(f"⚠️ Error processing row: {e}")

        return tasks_map


    # -------------------------------------------
    # Create Category
    # -------------------------------------------
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

        category_resp = requests.post(CATEGORY_URL, headers=headers, json=category_data)

        if category_resp.status_code == 201:
            print(f"✔️ Category '{name}' created successfully!")
        else:
            print(f"❌ Failed to create category '{name}' → {category_resp.text}")


    # -------------------------------------------
    # Create Template
    # -------------------------------------------
    def create_template(name, tasks, ticket_type, token):

        tickettype_id = resolve_type_id(ticket_type, token)

        template_data = [
            {
                "name": name,
                "tickettype_id": tickettype_id,
                "todo_list": tasks
            }
        ]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        template_resp = requests.post(TEMPLATE_URL, headers=headers, json=template_data)

        if template_resp.status_code == 201:
            try:
                template_id = template_resp.json().get("id")
                print(f"✔️ Template '{name}' created successfully!")
                return template_id
            except:
                print("❌ Error parsing template response")
                return None
        else:
            print(f"❌ Failed to create template '{name}' → {template_resp.text}")
            return None


    # -------------------------------------------
    # Create Rule
    # -------------------------------------------
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

        rule_resp = requests.post(RULE_URL, headers=headers, json=rule_data)

        if rule_resp.status_code == 201:
            print(f"✔️ Rule for '{name}' created successfully!")
        else:
            print(f"❌ Failed to create rule for '{name}' → {rule_resp.text}")


    # -------------------------------------------
    # Main Script
    # -------------------------------------------
    def main():
        try:
            token = get_oauth_token()
            file_path = os.path.expanduser("~/Downloads/ticket-template.csv")
            tasks_map = process_csv(file_path)

            for name, data in tasks_map.items():
                ticket_type = data["tickettype"]
                tasks = data["tasks"]

                create_category(name, token)
                template_id = create_template(name, tasks, ticket_type, token)

                if template_id:
                    create_rule(name, template_id, token)
                else:
                    print(f"⚠️ Skipping rule creation for '{name}' (no template ID)")

        except Exception as e:
            print(f"Error: {e}")


    # -------------------------------------------
    # Streamlit Callable Function
    # -------------------------------------------
    def run_halo_upload(csv_path, base_url, oauth_url, client_id, client_secret):
        global API_BASE_URL, CATEGORY_URL, TEMPLATE_URL, RULE_URL, OAUTH2_TOKEN_URL, CLIENT_ID, CLIENT_SECRET

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

            for name, data in tasks_map.items():
                ticket_type = data["tickettype"]
                tasks = data["tasks"]

                create_category(name, token)
                template_id = create_template(name, tasks, ticket_type, token)

                if template_id:
                    create_rule(name, template_id, token)
                else:
                    print(f"⚠️ Skipping rule creation for '{name}' due to missing template ID.")

            return "Upload completed successfully."

        except Exception as e:
            return f"Error: {e}"


    # Run if standalone
    if __name__ == "__main__":
        main()