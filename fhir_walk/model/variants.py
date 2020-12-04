"""Capture the phenotypes for a given individual

When pulling Phenotypes for an individual patient, we'll return two dictionaries, 
present and absent (in that order). The key in each of those dicts is the 
HP Code. 
"""
import sys

from pprint import pformat
from fhirwood.identifier import Identifier
from fhirwood.reference import Reference
from fhirwood.codeable_concept import CodeableConcept
from fhirwood.coding import Coding
from fhirwood.range import Range

class CODES:
	gene = "48018-6"
	chrom = "48001-2"
	pos = "exact-start-end"
	ref_allele = "69547-8"
	alt_allele = "69551-0"
	zygosity = "53034-5"
	ref_seq = "62374-4"
	transcript = "51958-7"
	hgvsc = "48004-6"
	hgvsp = "48005-3"
	sv_type = "48006-1"
	inheritance = "mode-of-inheritance"
	significance = "53037-8"

class VariantReport:
	def __init__(self, host, data):
		self.host = host
		self.id = data['id']
		self.identifier = Identifier(block=data['identifier'])

		self.result = []

		self.patient_url = Reference(data['subject'])

		for result in data['result']:
			ref = Reference(block=result)
			payload = host.get(ref.ref)
			for data_chunk in payload.entries:

				coding = Coding(block=data_chunk['code']['coding'])

				# There will also be diagnostic implications, but those are 
				# merged into the actual variants themselves
				if coding == "69548-6":
					self.result.append(Variant(host, data_chunk))


	@classmethod
	def VariantReportsBySubject(cls, subject_id, host):
		payload = host.get(f"DiagnosticReport?subject=Patient/{subject_id}")

		reports = []
		for data_chunk in payload.entries:
			if 'resource' in data_chunk:
				variant_report = VariantReport(host, data_chunk['resource'])
				reports.append(variant_report)
		return reports

class Variant:
	def __init__(self, host, data):
		# this is the fhir_server object, which will be used to pull related entities
		self.host = host		
		self.id = data['id']
		self.identifier = Identifier(block=data['identifier'])

		self.specimen = None
		if "specimen" in data:
			self.specimen = Reference(block=data['specimen'])

		# We'll map the code:coding:code as key and the value as the value
		self.components = {}

		for component in data['component']:
			coding = Coding(block=component['code']['coding'])
			if "valueCodeableConcept" in component:
				self.components[coding.code] = CodeableConcept(block=component['valueCodeableConcept'])
			elif "valueRange" in component:
				self.components[coding.code] = Range(block=component['valueRange'])
			elif "valueString" in component:
				self.components[coding.code] = component['valueString']
			else:
				print(f"I'm not sure what to do with this component: {component.keys()}")
				sys.exit(1)

		# Now let's pull together any diagnostic implications, should there be any
		payload = host.get(f"Observation?code=diagnostic-implication")
		self.implications = {}

		# We can't query for these implications directly, so we have to filter 
		# the right ones out of the list by considering the derivedFrom property
		id_ref = f"Observation/{self.id}"

		#print(payload.entries)
		for data_chunk in payload.entries:
			#print(data_chunk)
			if 'resource' in data_chunk:
				data_chunk = data_chunk['resource']
				ref = Reference(block=data_chunk['derivedFrom'])
				if ref == id_ref:
					for component_block in data_chunk['component']:
						coding = Coding(block=component_block['code']['coding'])
						valuecc = CodeableConcept(block=component_block['valueCodeableConcept'])
						self.implications[coding.code] = valuecc


	@property
	def hgvsc(self):
		return self.components.get(CODES.hgvsc)
	
	@property
	def hgvsp(self):
		return self.components.get(CODES.hgvsp)
	
	@property
	def sv_type(self):
		return self.components.get(CODES.sv_type)
	
	@property
	def pos(self):
		return self.components.get(CODES.pos)

	@property
	def ref_allele(self):
		return self.components.get(CODES.ref_allele)

	@property
	def alt_allele(self):
		return self.components.get(CODES.alt_allele)

	@property
	def zygosity(self):
		return self.components.get(CODES.zygosity)

	@property
	def ref_seq(self):
		return self.components.get(CODES.ref_seq)

	@property
	def transcript(self):
		return self.components.get(CODES.transcript)

	@property
	def chrom(self):
		return self.components.get(CODES.chrom)
	
	@property
	def inheritance(self):
		return self.implications.get(CODES.inheritance)

	@property
	def significance(self):
		return self.implications.get(CODES.significance)		
	

	@property
	def gene(self):
		return self.components.get(CODES.gene)

	@classmethod
	def VariantsBySpecimen(cls, specimen_id, host):
		payload = host.get(f"Observation?specimen=Specimen/{specimen_id}")
		variants = {}
		for data_chunk in payload.entries:
			if 'resource' in data_chunk:
				variant = Variant(host, data_chunk['resource'])
				variants[variant.identifier.value] = variant

		return variants