import requests
import yaml
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def load_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def fetch_api_data(api, env_vars):
    """ Executes API requests and updates environment variables """
    url = api['url']
    params = api.get('params', {})
    
    # Replace placeholders with environment variables
    params = {k: str(v).replace("{{lat}}", str(env_vars.get("lat", ""))).replace("{{lon}}", str(env_vars.get("lon", ""))) for k, v in params.items()}
    response = requests.request(api['method'], url, params=params)
    
    if 'set_env' in api:
        response_json = response.json()
        for key, value in api['set_env'].items():
            env_vars[key] = response_json.get(value.split('.')[1], '')
    
    # Log API response with UTF-8 encoding
    with open("api_responses.log", "a", encoding='utf-8') as log_file:
        log_file.write(f"API: {api['name']}\nResponse: {response.text}\n\n")
    
    return {
        "API Name": api['name'],
        "Status": "PASS" if response.status_code == 200 else "FAIL",
        "Response Code": response.status_code,
        "Response": response.text  # Full response instead of truncated
    }

def generate_report(results):
    """ Generates an HTML report """
    df = pd.DataFrame(results)
    return df.to_html(index=False)

def send_email(report_html):
    """ Sends an email with the report """
    sender_email = "your_email@outlook.com"
    recipient_email = "recipient@company.com"
    subject = "API Validation Report"
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(report_html, 'html'))
    
    with smtplib.SMTP('smtp.office365.com', 587) as server:
        server.starttls()
        server.login(sender_email, "your_password")
        server.sendmail(sender_email, recipient_email, msg.as_string())

def main():
    """ Main execution flow """
    config = load_yaml("python-sanity\config.yaml")
    env_vars = {}
    results = []
    
    for api in config["apis"]:
        result = fetch_api_data(api, env_vars)
        results.append(result)
    
    report_html = generate_report(results)
    
    # Save report locally with UTF-8 encoding
    with open(r"python-sanity\api_validation_report.html", "w", encoding='utf-8') as f:
        f.write(report_html)
    print("Report saved: api_validation_report.html")
    
    # send_email(report_html)

if __name__ == "__main__":
    main()