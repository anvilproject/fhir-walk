"""Sequencing Data"""

from pprint import pformat
from fhir_walk.model.specimen import Specimen
import pdb 

class SequencingFile:
	def __init__(self, host, data=None, ref=None):
		self.host = host

		if data is None:
			payload = host.get(ref)
			data = payload.entries[0]

		self.id = data['id']
		self._author = data['author'][0]['reference']
		self._subject = data['subject']['reference']

		self.filename = ""

		for item in data['content']:
			if 'attachment' in item and item['format']['display'] == 'Sequence Filename':
				self.filename = item['attachment']['title']

		self._infos = None

	def get_infos(self):
		if self._infos is None:
			self._infos = []

			payload = self.host.get(f"Observation?focus=DocumentReference/{self.id}")

			for data_chunk in payload.entries:
				if 'resource' in data_chunk:
					info = SequencingFileInfo(self.host, data_chunk['resource'])
					self._infos.append(info)

		return self._infos

class SequencingFileInfo:
	def __init__(self, host, data):
		self.host = host
		self.id = data['id']

		self._subject = data['subject']['reference']
		self._doc = data['focus'][0]['reference']	
		
		self._data = {}

		for component in data['component']:
			# Currently, this is all we have
			if 'valueString' in component:
				self._data[component['code']['text']] = component['valueString']	

	@property
	def reference_genome(self):
		return self._data.get("Reference Genome Build")

	@property
	def alignment_method(self):
		return self._data.get("Alignment Method")

	@property
	def data_processing_pipeline(self):
		return self._data.get("Data Processing Pipeline")
	
	@property
	def functional_equivalence_standard(self):
		return self._data.get("Functional Equivalence Standard")


class SequencingData:
	def __init__(self, host, data):
		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		

		self.id = data['id']
		self._owner = data['owner']['reference']
		#self._input = data['input']['valueReference']['reference']
		self._specimen_id = data['focus']['reference']
		self._docs = []
		self._data = {}

		for outp in data['output']:
			if 'text' in outp['type'] and 'valueReference' in outp:
				if outp['type']['text'] == 'Sequence Data Filename':
					self._docs.append(SequencingFile(self.host, ref=outp['valueReference']['reference']))

		for inp in data['input']:
			if 'text' in inp['type']:
				if 'valueString' in inp:
					self._data[inp['type']['text']] = inp['valueString']

		# Let's treat sample differently. No need to make a call to fhir if 
		# no one needs the object, but we can make it easy to get to if
		# they need it
		self._sample = None
		self.analyte_type = self._data.get('Analyte Type')
		self.lib_prep_kit = self._data.get('Library Prep Kit')
		self.exome_capture_platform = self._data.get('Exome Capture Platform')
		self.capture_region_bed_file = self._data.get('Capture Region Bed File')

	@property
	def sequencing_files(self):
		return self._docs
	
	@property
	def specimen(self):
		if self._specimen is None:
			self._specimen = Specimen(self.host, self._specimen_id)
		return self._specimen

	@property
	def sample_id(self):
		return self._data.get('Specimen')

	@property
	def sample(self):
		if self._sample is None:
			sample_id = self.sample_id

			if sample_id:
				payload = host.get(sample_id)
				self._sample = Specimen(host, payload['resource'])

		return self._sample

	@classmethod
	def SequencingDataBySpecimen(cls, specimen_id, host):
		payload = host.get(f"Task?focus=Specimen/{specimen_id}")
		sequence_data = []

		for data_chunk in payload.entries:
			if 'resource' in data_chunk:
				seq = SequencingData(host, data_chunk['resource'])
				sequence_data.append(seq)
		return sequence_data
