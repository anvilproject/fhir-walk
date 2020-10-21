"""Parse research study objects"""

from fhir_walk.model.patient import Patient
from pprint import pformat

class ResearchStudy:
	def __init__(self, host, data):
		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		
		self.raw = data
		self.id = data['resource']['id']
		self.identifiers = data['resource']['identifier']
		self.title = data['resource']['title']

	@classmethod
	def Studies(cls, host):
		"""Return all research studies found at a given host"""
		data = host.get("ResearchStudy")

		studies = {}
		for data_chunk in data.entries:
			study = ResearchStudy(host, data_chunk)
			studies[study.id] = study
		return studies

	def Patients(self):
		"""Pull all of the patients associated with a given study"""
		return Patient.PatientsByStudy(self.id, self.host)