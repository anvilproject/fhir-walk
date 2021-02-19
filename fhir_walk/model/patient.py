"""The patient, pulled by way of a research study (so there will be a ResearchSubject id)

Subject may have the following properties: 
id  		- This is the FHIR unique identifier
subject_id 	- This is the ID from the original dataset
sex
eth
race
study 		- The study "id", which is usually just a short study name
dbgap_study_id
dbgap_id 

"""

# TODO -- Add support for extended family

from re import compile

from fhir_walk.model.disease import Disease
from fhir_walk.model.phenotypes import Phenotype
from fhir_walk.model.specimen import Specimen

from pprint import pformat

import pdb

class Patient:
	study_regex = compile("https://ncpi-api-dataservice.kidsfirstdrc.org/(participants|research_subjects)\?study_id=(?P<study>[A-Za-z0-9-]+)&external_id=")
	dbgap_regex = compile("https://dbgap-api.ncbi.nlm.nih.gov/participants\?study_id=(?P<study>[a-zA-Z0-9-]+)&external_id=")

	def __init__(self, host, data):
		# We can arrive here by one of two ways: 1) ResearchSubject and 2) Patient
		# so we may need to perform an additional pull for the actual patient
		# data

		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		
		self.research_subject_id = None
		
		self._parents = None
		self._specimens = None
		if data['resourceType'] == 'ResearchSubject':
			patient_data = host.get(data['individual']['reference']).entries[0]

			first_value = None
			for identifier in data['identifier']:
				g = Patient.study_regex.search(identifier['system'])

				if first_value is None:
					first_value = identifier['value']

				if g is not None:
					self.research_subject_id = identifier['value']

			if self.research_subject_id is None:
				self.research_subject_id = first_value

		else:
			patient_data = data


		self.id = patient_data['id']
		self.sex = patient_data['gender']
		self.race = ""
		self.eth = ""
		self.study = ""
		self.dbgap_study_id = ""
		self.dbgap_id = ""

		# Subject ID is the actual id from the study, whereas, id is the
		# unique ID associated with the FHIR data store
		self.subject_id = None
		first_value = None
		for identifier in patient_data['identifier']:
			if first_value is None:
				first_value = identifier['value']
			g = Patient.study_regex.search(identifier['system'])

			if g is not None:
				self.study = g.group('study')
				self.subject_id = identifier['value']

			else:
				g = Patient.dbgap_regex.search(identifier['system'])
				if g is not None:
					self.dbgap_study_id = g.group('study')
					self.dbgap_id = identifier['value']
		if self.subject_id is None:
			self.subject_id = first_value
	
		if "extension" in patient_data:
			for ex in patient_data['extension']:
				if ex['url'] == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
					self.race = ex['extension'][0]['valueCoding']['display']
				if ex['url'] == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity":
					self.eth = ex['extension'][0]['valueCoding']['display']

	def parents(self):
		"""Return the parents for a given patient"""
		if self._parents is None:
			self._parents = {}
			qry = f"Observation?code:text=Family&focus=Patient/{self.id}"
			payload = self.host.get(f"Observation?code:text=Family&focus=Patient/{self.id}")

			for data_chunk in payload.entries:
				if 'resource' in data_chunk:
					parent_chunk = data_chunk['resource']
					parent_data = self.host.get(parent_chunk['subject']['reference'])
					patient = Patient(self.host, parent_data.entries[0])

					for codeable in parent_chunk['valueCodeableConcept']['coding']:
						if codeable['code'] in ['FTH', 'MTH']:
							self._parents[codeable['code']] = patient

		return self._parents

	def specimens(self):
		"""Pull specimens for the current patient"""
		if self._specimens is None:
			self._specimens = Specimen.SpecimenByPatient(self.id, self.host)

		return self._specimens

	def diseases(self):
		"""Pull diseases associated with the current patient"""
		return Disease.DiseasesByPatient(self.id, self.host)

	def phenotypes(self):
		"""Returns the list of HPOs present and absent (hpos_present, hpos_absent) tuple"""
		return Phenotype.PhenotypesByPatient(self.id, self.host)

	@classmethod
	def PatientsByStudy(cls, study_id, host):
		#print(f"--> ResearchSubject?study=ResearchStudy/{study_id}")
		payload = host.get(f"ResearchSubject?study=ResearchStudy/{study_id}")

		patients = {}

		for data_chunk in payload.entries:
			# To get the patient, we have to use the research subject's individual
			patient = Patient(host, data_chunk['resource'])
			patients[patient.subject_id] = patient
		return patients

	@classmethod
	def PatientBySubjectID(cls, study_id, subject_id, host):
		payload = host.get(f"Patient?identifier={subject_id}")
		return Patient(host, payload)