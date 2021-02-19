"""Use a simple YAML file to manage hosts and dataset configurations

By default, this will create/use a file, .ncpi_fhir_rc in the user's home directory. 
This file is just a plain YAML file that describes:
    * Hosts
    * Datasets
    * Dataroot

For users just trying to attach to a fhir host for reading, this class is probably of little interest. 

Each host can support username, password, cookie as well as the target_service_url to simplify
connection details. 

"""
import os 

from yaml import load, FullLoader, dump, safe_load, safe_dump
from pathlib import Path
from fhir_walk.fhir_host import FhirHost 

home = Path.home()
cwd = Path(os.getcwd())

class DataConfig:
    """Store dataset and host details in home directory to allow users to deploy each dataset to different hosts with minimal effort."""

    _cfg = None     # Cheesy Singleton to allow downstream objects to acquire the preconfigured environment

    def __init__(self, data_config=None, host_config=None, dataroot=None, hosts_only=False ):
        """We'll permit client applications to use an alternate storage mechanism for the configurat details.

        * config_file is the actual yaml config
        * dataroot is the 'root' directory where the datasets can be found
        """
        if host_config is None:
            host_config = home/".ncpi_fhir_rc"

        if data_config is None:
            data_config =  cwd / ".ncpi_fhir_rc"

        self.hosts = {}
        self.datasets = {}
        self.dataroot = None
        self.filenames = [host_config, data_config]
        self.cur_environment = 'dev'
        self.host_cache = None

        use_default = not self._load_cfg(host_config, data_config, hosts_only)

        if len(self.hosts) == 0 or self.dataroot is None:
            with open(host_file, 'wt') as f:
                f.write(f"""hosts:
    dev:
        username: {os.getenv('FHIR_USERNAME', 'admin')}
        password: {os.getenv('FHIR_PASSWORD', 'password')}
        target_service_url: {os.getenv('FHIR_HOST', 'http://localhost:8000')}
dataroot: {Path.cwd()}""")
            print(f"Default hosts file written to '{str(host_file)}'.")
        if len(self.datasets) == 0:
            with open(data_config, 'wt') as f:
                f.write(f"""datasets:
    FAKE-CMG:
        sample: example-cmg/FakeData_CMG_Sample.tsv
        family: example-cmg/FakeData_CMG_Family.tsv
        subject: example-cmg/FakeData_CMG_Subject.tsv
        discovery: example-cmg/FakeData_CMG_Discovery.tsv
        sequencing: example-cmg/FakeData_CMG_Sequencing.tsv
""")
            print(f"A fresh datasets was generated at the path: '{str(data_config)}'.")

    def set_host(self, env='dev'):
        """TODO- Should we support having multiple hosts active at once? Currently, there isn't a clear cut use case for it"""
        self.cur_environment = env
        assert env in self.hosts
        self.host = FhirHost.host(cfg=self.hosts[env])
        return self.host

    def get_dataset(self, dataset):
        """Returns the dataset details (dict) for each of the different purposes: sample, family, subject, etc"""
        return self.datasets[dataset]

    def list_environments(self):
        """List the environment strings for each of the environments that have been configured"""
        return sorted(self.hosts.keys())

    def list_datasets(self):
        """List the 'names' for each of the datasets that have been configured"""
        return sorted(self.datasets.keys())

    def get_host(self):
        """Return the FhirHost object"""
        return self.host

    def _load_cfg(self, host_config=None, data_config=None, hosts_only=False):
        """Loads configuration (filename=None will load the default)"""
        if host_config is None:
            host_config = self.host_config
        if data_config is None:
            data_config = self.data_config

        successes = 0

        config = safe_load(open(host_config, 'rt'))
        if config:
            self.hosts = config['hosts']
            self.dataroot = config['dataroot']
            if 'datasets' in config:
                self.datasets = config['datasets']
            successes += 1
        if not hosts_only:
            config = safe_load(open(data_config, 'rt'))
            if config:
                self.datasets = config['datasets']
                successes += 1
        
        return False

    # TBD Having issues with dumping some things to YAML 
    def save(self, filename=None):
        """TODO...this needs to be implemented"""
        if filename is None:
            filename = self.filename

        with open(filename, 'wt') as f:
            f.write("hosts:")

    @classmethod
    def config(cls, config_file=None, dataroot = None, env=None, hosts_only=False):
        """Return singleton if it hasn't been instantiated. Instantiate if any of the parameters differ from current settings (or default)"""

        if cls._cfg is None or (config_file is not None and cls._cfg.filename != config_file):
            cls._cfg = DataConfig(config_file, dataroot, hosts_only=hosts_only)

        if env is not None:
            cls._cfg.set_host(env)

        return cls._cfg



