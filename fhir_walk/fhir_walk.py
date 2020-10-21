#!/usr/bin/env python

"""Rudimentary tool for exploring an NCPI fhir resource's contents"""

from argparse import ArgumentParser, FileType
from urllib.parse import urlparse
from ncpi_fhir_utility.client import FhirApiClient

from ncpi_fhir_plugin.ncpi_config import Config

from ncpi_fhir_plugin.model.research_study import ResearchStudy
from ncpi_fhir_plugin.model.sequencing_data import SequencingData

if __name__=='__main__':
    config = Config.config()
    fhir_host = config.set_host('dev')

    studies = ResearchStudy.Studies(fhir_host)
    print(f"The following studies were found: {', '.join(sorted(studies.keys()))}")

    study = studies['CMG-UW']
    print(f"Shall we pull the patients for study...let's say {study.id}")
    patients = study.Patients()

    if len(patients) > 100:
        print(f"Phew! That's a bunch. We have {len(patients)} in there! Let's print out some information about them")
        for pid in list(patients.keys())[0:150]:
            p = patients[pid]
            print(f"\t{p.id} - {p.sex} - {p.race}:{p.eth}")
            diseases = p.diseases()
            for d in diseases.keys():
                print(f"\t\tDisease:\t{diseases[d].code} {diseases[d].text} - {diseases[d].status}")

            hpos_present, hpos_absent = p.hpos()
            for hpo in hpos_present:
                print(f"\t\tHPO Present:\t{hpo.name} {hpo.code}")
            for hpo in hpos_absent:
                print(f"\t\tHPO Absent:\t{hpo.name} {hpo.code}")

            parents = []

            for rel in p.parents():
                parents.append(f"\t\t\t{rel}: {p.parents[rel].id} {p.parents[rel].sex}")
            if len(parents) > 0:
                parents = "\n".join(parents)
                print(f"\t\tParents: {parents}")

            specimens = p.specimens()
            for spec in specimens:
                print(f"\t\tSpecimen {spec.id} - {spec.tissue_affected_status} from {spec.body_site}")

                seq_data = SequencingData.SequencingDataBySpecimen(spec.id, fhir_host)
                print(f"Total number of data? {len(seq_data)}")
                for seq in seq_data:
                    files = seq.sequencing_files
                    print(files)
                    for file in files:
                        info = file.get_infos()[0]

                        print(f"\t\t\t{file.filename} - {info.reference_genome} - {info.data_processing_pipeline} {seq.analyte_type} {seq.capture_region_bed_file}")

