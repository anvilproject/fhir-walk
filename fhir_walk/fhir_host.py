"""Some helper classes for working with NCPI FHIR resources

Clients can instantiate a FhirHost explicitly with: 
        username, password, cookie and target_service_url
or passing as key/value pairs in a dict. This should allow clients 
to bypass using the config class which is largely designed for ingestion
and testing. 

Dependencies: ncpi_fhir_utility
"""
from ncpi_fhir_utility.client import FhirApiClient
import subprocess
from pprint import pformat
import pdb

class FhirResult:
    """Wrap the return value a bit to make interacting with it a bit more smoother"""
    def __init__(self, payload):
        self.response = payload['response']

        # Always return an array, even if it was a single entry
        if 'entry' in self.response:
            self.entries = self.response['entry']
        else:
            self.entries = [self.response]

        # If there is pagination, this will capture the "next" url to traverse 
        # large returns
        self.next = None

        self.entry_count = len(self.entries)

        if "link" in self.response:
            for ref in self.response['link']:
                if ref['relation'] == 'next':
                    self.next = ref['url']       

    def append(self, payload):
        """Extend our entry data by following pagination links"""
        self.response = payload['response']
        self.next = None

        for ref in self.response['link']:
            if ref['relation'] == 'next':
                self.next = ref['url']   

        self.entries += self.response['entry']
        self.entry_count = len(self.entries)   


# TODO: This is just a hasty solution, but if there is real interest, this should be turned into
# an iterable class rather than bulk capture of entire list of data
class FhirHost:
    # Singleton. For use with kf ingestion, we can configure this prior to passing control to 
    # load function. 
    _fhir_host = None    

    def __init__(self, cfg=None, **kwargs):
        """For controlled dev server, our security is cookie based, however, some servers will rely on username/password"""
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.cookie = kwargs.get('cookie')
        self.service_token = kwargs.get('service_account_token')

        # URL associated with the host. If it's a non-standard port, use appropriate URL:XXXXX format
        self.target_service_url = kwargs.get('target_service_url')

        self.is_valid = False
        self.google_identity = False
        self._client = None         # Cache the client so we don't have to rebuild it between calls

        if cfg is not None:
            if 'username' in cfg:
                self.username = cfg['username']
                self.password = cfg['password']

            if 'cookie' in cfg:
                self.cookie = cfg['cookie']

            if 'service_account_token' in cfg:
                self.service_token = cfg['service_account_token']
                print("We are using a service account token (or pretending to)")

            if 'target_service_url' in cfg:
                self.target_service_url = cfg['target_service_url']

        self.is_valid = self.target_service_url is not None and (
                (self.username is not None and self.password is not None)  or
                (self.cookie is not None) or
                (self.target_service_url is not None) )

        # Deal with google's service account authentication
        if self.service_token is not None:
            self.google_identity = True

            #from google.cloud import storage
            #self.storage_client = storage.Client.from_service_account_json(self.service_token)

    def auth(self):
        """Return basic authorization tuple. Currently assumes cookie means no username/password"""
        if self.cookie is None and not self.google_identity:
            return (self.username, self.password)

    def client(self):
        """Return cached client object, creating it if necessary"""
        if self._client is None:
            self._client = FhirApiClient(
                base_url=self.target_service_url, auth=self.auth()
            )
        return self._client

    def put(self, resource, data, validate_only=False):
        """validate_only will append the $validate to the end of the final url"""
        objs = data

        if not isinstance(objs, list):
            objs = [data]

        for obj in objs:
            cheaders = self.client()._fhir_version_headers()

            # Deal with the cookie stuff, if it's appropriate
            if self.cookie:
                cheaders['cookie'] = self.cookie

            url = f"{self.target_service_url}/"


    def get_google_identity(self):
        #pdb.set_trace()
        token = subprocess.check_output(['gcloud','auth','application-default', 'print-access-token'])
        token = token.decode('utf8').strip()
        return "Bearer " + token

    def get(self, resource, recurse=True):
        """Default to recurse down the chain of 'next' links

        Please note that this is currently not very robust and works with our CMG data. 
        """
        cheaders = self.client()._fhir_version_headers()
        if self.cookie:
            cheaders['cookie'] = self.cookie

        #print(self.google_identity)
        if self.google_identity:
            cheaders['Authorization'] = self.get_google_identity()
            print("Doin' the holka polkey")

        count = "?_count=250"

        if "?" in resource:
            count = "&_count=250"

        url = f"{self.target_service_url}/{resource}{count}"
        success, result = self.client().send_request("GET", f"{url}", headers=cheaders)
       
        if not success:
            print("There was a problem with the request for the GET")
            print(pformat(result))

        # For now, let's just give up if there was a problem
        assert(success)
        content = FhirResult(result)

        # Follow paginated results if so desired
        while recurse and content.next is not None:
            params = content.next.split("?")[1]

            success, result = self.client().send_request("GET", f"{self.target_service_url}?{params}", headers=cheaders)
            assert(success)
            content.append(result)
        return content

    @classmethod
    def host(cls, cfg=None, **kwargs):
        """Build new or retrieve preconfigured host object"""
        if cls._fhir_host is None:
            cls._fhir_host = FhirHost(cfg=cfg, **kwargs)
        return cls._fhir_host

