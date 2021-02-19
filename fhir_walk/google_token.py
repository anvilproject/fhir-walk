"""Wrapper to generate the authentication token"""

import jwt
import json
import datetime
import subprocess
import requests
from pathlib import Path

""" I'm not having much luck doing it google's way. I'm moving on for the time
being since I am able to get it moving doing things a bit more manually

from google.oauth2 import id_token
from google.oauth2 import service_account as service_auth
import google.auth
import google.auth.transport.requests
from google.auth.transport.requests import AuthorizedSession
"""
import pdb

# these do time-out periodicallly (max lifetime is 1hr)
# So, you may want to keep this around and regenerate your
# bearer token
class GoogleAuth(object):
    def __init__(self, target_service = None, oa2_client=None):
        "Optionally choose between target service or open auth2"
        self.target_service = target_service
        self.oa2_client = oa2_client
        if target_service:
            with open(target_service, 'rt') as f:
                data=f.read()
                data = json.loads(data)
                self.account = data['client_email']
                self.private_key = data['private_key']
                self.algorithm = 'RS256'
                self.token_uri = data['token_uri']
                self.target_data = data
        self.scope = "https://www.googleapis.com/auth/cloud-platform"
        self.credentials = None

        if oa2_client:
            with open(oa2_client, 'rt') as f:
                data = f.read()
                data= json.loads(data)

                self.client_id = data['installed']['client_id']
                self.project_id = data['installed']['project_id']
                self.auth_uri = data['installed']['auth_uri']
                self.token_uri = data['installed']['token_uri']
                self.client_secret = data['installed']['client_secret']
                self.credentials = None

    def access_token(self, lifetime=60):
        #pdb.set_trace()        
        if self.target_service:
            """
            This should work, but obviously the token I'm getting back isn't what I expect it 
            should be. So, rather than continuing to spin my tires on a more elegant solution 
            for something I have working, I'm going to move on for now. 

            creds = service_auth.IDTokenCredentials.from_service_account_file(self.target_service, target_audience=self.token_uri)
            authed_session = AuthorizedSession(creds)
            resp = authed_session.get(self.scope)
            request = google.auth.transport.requests.Request()
            token = creds.token
            print(id_token.verify_token(token, request))
            print("Returning the token from google's stuff")
            return token

            pdb.set_trace()
            from oauth2client import service_account 
            credentials = service_account.ServiceAccountCredentials.from_json_keyfile_name(self.target_service)
            """
            claim_set = {
                "iss": self.account,
                "scope": self.scope,
                "aud": self.token_uri,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=lifetime),
                "iat": datetime.datetime.utcnow()
            }

            signature = jwt.encode(claim_set, self.private_key, algorithm=self.algorithm)
            req = requests.post(self.token_uri, 
                            data={
                                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                                'assertion': signature,
                                'response_type': 'code'
                                }
                            )
            return req.json()['access_token']
        elif self.oa2_client:

            if self.credentials is None or self.credentials.expired:
                #pdb.set_trace()
                from google_auth_oauthlib.flow import InstalledAppFlow

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oa2_client,
                    scopes=[self.scope]) 
                self.credentials = flow.run_console()        
                # The local server only works if you are running with access to the browser, 
                # Which doesn't work right with WSL
                """credentials = flow.run_local_server(host='localhost',
                    port=8080, 
                    authorization_prompt_message='Please visit this URL: {url}', 
                    success_message='The auth flow is complete; you may close this window.',
                    open_browser=True)            """   
                #print(credentials)
            return self.credentials.token
