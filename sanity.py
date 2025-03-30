import requests
import yaml
import pandas as pd
import smtplib
import json
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os 
import time

def load_yaml(file_path):
    """ Load YAML file and handle errors """
    try:
        file = Path(file_path)
        if not file.exists():
            print(f"Error: YAML file not found -> {file_path}")
            return {}
        with open(file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        return {}

def load_payload(file_path):
    """ Load JSON payload from file and handle errors """
    try:
        file = Path(file_path)
        if not file.exists():
            print(f"Error: Payload file not found -> {file_path}")
            return {}
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading payload file {file_path}: {e}")
        return {}


def fetch_api_data(api, env_vars):
    """ Execute API request, log response, and update environment variables """
    LOG_FILE_NAME = "api_res_fle.log"

    try:
        url = api['url']
        params = api.get('params', {})
        headers = api.get('headers', {})
        payload = None

        # Replace placeholders with environment variables
        params = {k: str(v).replace("{{lat}}", str(env_vars.get("lat", "")))
                         .replace("{{lon}}", str(env_vars.get("lon", ""))) 
                  for k, v in params.items()}

        # Load payload if it's a POST request
        if api['method'].upper() == 'POST' and 'payload_file' in api:
            payload_path = os.path.join(os.path.dirname(__file__), env_vars['payload_dir'],api['payload_file'])
            payload = load_payload(payload_path)

        response = requests.request(api['method'], url, params=params, json=payload, headers=headers)
   
        # Update environment variables from response
        if 'set_env' in api:
            response_json = response.json()
            for key, value in api['set_env'].items():
                keys = value.split('.')
                env_vars[key] = response_json.get(keys[-1], '') if keys else ''

        return {
            "API Name": api['name'],
            "Status": "PASS" if response.status_code == 200 else "FAIL",
            "Response Code": response.status_code,
            "Response": response.json()
        }
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return {
            "API Name": api['name'],
            "Status": "ERROR",
            "Response Code": "N/A",
            "Response": str(e)
        }

def generate_report(results):
    """ Generate an HTML report """
    try:
        df = pd.DataFrame(results)
        return df.to_html(classes="styled-table", index=False)

    except Exception as e:
        print(f"Error generating report: {e}")
        return "<p>Error generating report</p>"

def send_email(report_html, env_vars):
    """ Send email with report """
    try:
        sender_email = env_vars['email']['sender']
        recipient_email = env_vars['email']['recipient']
        subject = "API Validation Report"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(report_html, 'html'))

        with smtplib.SMTP(env_vars['email']['smtp_server'], env_vars['email']['smtp_port']) as server:
            server.starttls()
            server.login(sender_email, env_vars['email']['password'])
            server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    """ Main execution flow """

    CONFIG_FILE_NAME = "config.yaml"
    ENV_FILE_NAME = "env.yaml"
    HTML_REPORT_FILE_NAME = f"Sanity_Report__{int(time.time()*1000)}.html"

    try:
        api_config = load_yaml(os.path.join(os.path.dirname(__file__), CONFIG_FILE_NAME))
        env_vars = load_yaml(os.path.join(os.path.dirname(__file__), ENV_FILE_NAME))

        if not api_config or not env_vars:
            print("Error: Required YAML files missing. Exiting.")
            return
        
        results = []

        for api in api_config.get("apis", []):
            result = fetch_api_data(api, env_vars)
            results.append(result)

        report_html = generate_report(results)
        HTML_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), env_vars["result_dir"], env_vars["HTML_TEMPLATE_FILE"])
        report_path = os.path.join(os.path.dirname(__file__), env_vars["result_dir"], HTML_REPORT_FILE_NAME)
        
        with open(HTML_TEMPLATE_FILE, 'r') as f :
            HTML_TEMPLATE = f.read() 

        with open(report_path, "w", encoding='utf-8') as f:
            f.write(HTML_TEMPLATE.replace('{{ TABLE_CONTENT }}', report_html))

        print(f"Report saved: {report_path}")
        send_email(report_html, env_vars)

    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()