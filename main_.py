import os
import requests
import shlex
import logging
from google.cloud import secretmanager
from flask import jsonify, request, make_response

logging.basicConfig(level=logging.DEBUG)

def get_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv('GCP_PROJECT')
    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    secret_response = client.access_secret_version(request={"name": secret_path})
    secret_string = secret_response.payload.data.decode("UTF-8")
    return secret_string

def parse_keywords(input_keywords):
    return shlex.split(input_keywords)

def get_jobs(api_key, keywords, location='United States', who_may_apply='public'):
    url = "https://data.usajobs.gov/api/search"
    all_jobs = []
    headers = {
        "Authorization-Key": api_key,
        "User-Agent": "JobSearchApp/1.0"
    }

    for keyword in keywords:
        params = {
            "Keyword": keyword,
            "LocationName": location,
            "WhoMayApply": who_may_apply
        }
        response = requests.get(url, headers=headers, params=params)
        logging.debug(f'Requesting {url} with params {params}')  # Debug output
        logging.debug(f'Response status: {response.status_code}')  # Debug output
        logging.debug(f'Response content: {response.text}')  # Debug output
        if response.status_code == 200:
            all_jobs.extend(response.json()['SearchResult']['SearchResultItems'])
        else:
            logging.error(f"Failed to retrieve data for {keyword}: {response.status_code}")

    return all_jobs

def handle_request(request):
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        request_json = request.get_json(silent=True)
        if not request_json or 'keywords' not in request_json:
            response = jsonify({'error': 'No keywords provided or incorrect format'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400

        input_keywords = request_json['keywords']
        keywords = parse_keywords(input_keywords)
        api_key = get_secret('USAJOBS_API_KEY')
        if not api_key:
            response = jsonify({'error': 'API Key not configured'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500

        jobs = get_jobs(api_key, keywords)
        response = jsonify({'jobs': jobs})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        response = jsonify({'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
