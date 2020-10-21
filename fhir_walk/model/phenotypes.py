"""Capture the phenotypes for a given individual

When pulling Phenotypes for an individual patient, we'll return two dictionaries, 
present and absent (in that order). The key in each of those dicts is the 
HP Code. 
"""

from pprint import pformat

class Phenotype:
	def __init__(self, host, data):
		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		

		self.id = data['id']
		self.code = data['code']['coding'][0]['code']
		self.name = data['code']['coding'][0]['display']
		self.status = data['interpretation'][0]['coding'][0]['display']

	@classmethod
	def PhenotypesByPatient(cls, patient_id, host):
		payload = host.get(f"Observation?subject=Patient/{patient_id}")

		phenotypes_present = {}
		phenotypes_absent = {}


		for data_chunk in payload.entries:
			# There will be a lot of observations, and currently, I'm not seeing a way
			# to filter on the types we want for Phenotypes. So, we'll do that here

			if 'resource' in data_chunk:
				resource = data_chunk['resource']

				if 'interpretation' in resource:
					if resource['interpretation'][0]['coding'][0]['code'] =="POS": 
						pheno = Phenotype(host, data_chunk['resource'])
						phenotypes_present[pheno.code] = pheno
					elif resource['interpretation'][0]['coding'][0]['code'] == "NEG":
						pheno = Phenotype(host, data_chunk['resource'])
						phenotypes_absent[pheno.code] = pheno

		return phenotypes_present, phenotypes_absent