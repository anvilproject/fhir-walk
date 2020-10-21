"""Disease (conditions) associated with a patient"""
from pprint import pformat

class Disease:
	def __init__(self, host, data):
		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		
		self.id = data['id']
		self.status = ""

		if 'verificationStatus' in data:
			self.status = data['verificationStatus']['text']

		self.code = ""
		self.text = ""

		if 'code' in data:
			self.text = data['code']['text']

			# For now, we are looking only at the first code
			if 'coding' in data['code']:
				self.code = data['code']['coding'][0]['code']
				self.text = data['code']['coding'][0]['display']



	@classmethod
	def DiseasesByPatient(cls, patient_id, host):
		payload = host.get(f"Condition?subject=Patient/{patient_id}")

		diseases = {}

		for data_chunk in payload.entries:
			disease = Disease(host, data_chunk['resource'])
			diseases[disease.code] = disease

		return diseases