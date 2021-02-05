"""Specimens"""
from re import compile

from pprint import pformat
from fhir_walk.model.variants import Variant

class Specimen:
	sample_id_regex = compile("http://ncpi-api-dataservice.kidsfirstdrc.org/biospecimens\?study_id=(?P<study>[A-Za-z0-9-]+)&external_aliquot_id=")
	def __init__(self, host, data=None, ref=None):
		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		

		if data is None:
			payload = host.get(ref)
			data = payload['resource']
			
		self.id = data['id']
		self.dbgap_id = ""
		self.study = ""
		self.sample_id = ""

		for identifier in data['identifier']:
			g = Specimen.sample_id_regex.search(identifier['system'])

			if g:
				self.study = g.group('study')
				self.sample_id = identifier['value']
			elif identifier['system'] == "https://dbgap-api.ncbi.nlm.nih.gov/specimen":
				self.dbgap_id = identifier['value']

		self.subject_id = None
		self.tissue_affected_status = ""

		if "subject" in data:
			self.subject_id = data['subject']['reference']

		self.body_site = ''
		if 'collection' in data:
			if 'bodySite' in data['collection']:
				site_coding = data['collection']['bodySite']['coding'][0]

				if 'display' not in site_coding:
					self.body_site = (site_coding['code'], '')
				else:
					self.body_site = (site_coding['code'], site_coding['display'])

		# Now for the fun part, let's try and get the tissue_affected_status
		payload = self.host.get(f"Observation?specimen=Specimen/{self.id}")
		for data_chunk in payload.entries:
			if 'resource' in data_chunk:
				coding = data_chunk['resource']['code']['coding'][0]
				self.tissue_affected_status = coding['system']

	def variants(self):
		return Variant.VariantsBySpecimen(self.id, self.host)

	@classmethod
	def SpecimenByPatient(cls, patient_id, host):
		payload = host.get(f"Specimen?subject=Patient/{patient_id}")

		specimens = {}

		for data_chunk in payload.entries:
			if 'resource' in data_chunk:
				specimen = Specimen(host, data_chunk['resource'])
				specimens[specimen.sample_id] = specimen
		return specimens