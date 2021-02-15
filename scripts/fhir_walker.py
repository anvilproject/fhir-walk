#!/usr/bin/env python

"""Rudimentary tool for exploring an NCPI fhir resource's contents"""

"""This script can be used to interactively explore data in a fhir server, as long as it conforms to the current NCPI FHIR model. Users can choose a study to inspect and iteratively look at subjects and their related Disease/Phenotype/Variant information"""

"""More useful, perhaps, is that it provides an example of using the OO wrapper library I wrote for using with unit tests for my ingestion scripts

Currently, the "display" assumes a fairly wide terminal (probably 100 characters or so)

The philosophy behind the walker library is largely to pull only what is needed. So, if you get all studies, you really only get the information required to query the server for the relevant subjects. For intermediate objects, like ResearchSubject, that information gets absorbed into the Patient objects, rather than being captured as standalone objects. 

"""

import sys
from argparse import ArgumentParser, FileType
from urllib.parse import urlparse

from ncpi_fhir_utility.client import FhirApiClient

from fhir_walk.config import DataConfig 
from fhir_walk.fhir_host import FhirHost

from fhir_walk.model.research_study import ResearchStudy
from fhir_walk.model.sequencing_data import SequencingData
from fhir_walk.model.variants import Variant, CODES

import random

from shutil import get_terminal_size

from argparse import ArgumentParser, FileType
from colorama import init,Fore,Back,Style
init()

# Simple wrappers to help format printed output for easier reading
def PrintWithColor(txt, color, width=None):
    text_block = txt
    if width:
        text_block = str(txt).ljust(width, ' ')
    return f"{color}{text_block}{Fore.RESET}"

def Yellow(txt, width=None):
    return PrintWithColor(txt, Fore.YELLOW, width)

def Cyan(txt, width=None):
    return PrintWithColor(txt, Fore.CYAN, width)

def Blue(txt, width=None):
    return PrintWithColor(txt, Fore.BLUE, width)

def Green(txt, width=None):
    return PrintWithColor(txt, Fore.GREEN, width)

def Magenta(txt, width=None):
    return PrintWithColor(txt, Fore.MAGENTA, width)

def Red(txt, width=None):
    return PrintWithColor(txt, Fore.RED, width)

# Print the specimen summary
def PrintSpecimen(specimen, dbgap_study_id):
    print(f"""\n{Cyan(specimen.id, 8)} ID: {Magenta(specimen.sample_id, 10)} Tissue Affected Status: {Yellow(specimen.tissue_affected_status, 8)}""")
    if specimen.dbgap_id != "":
        print(f"""{Green(specimen.dbgap_id)}@{Green(dbgap_study_id)}""")

    body_site = specimen.body_site
    if body_site:
        print(f"""Body Site: {Red(body_site[0])} {Blue(body_site[1])}""")

# Print the disease details
def PrintDisease(disease):
    print(f"""\t{Green(disease.code, 12)} {Magenta(disease.status, 12)} {Blue(disease.text)}""")

# Print the Phenotype
def PrintPhenotype(pheno, trait_status):
    print(f"""\t{trait_status} {Yellow(pheno.code, 8)} {Magenta(pheno.status, 8)} {Magenta(pheno.name)}""")

# Print the variants
def PrintVariant(variant):
    print(f"""\t{Green(variant.id, 10)} {Magenta(variant.identifier.value)}""")

    if len(variant.components) > 0:
        chrom = variant.chrom
        pos = variant.pos
        if pos:
            pos = pos.to_str()
        alleles = f"{variant.ref_allele}/{variant.alt_allele}"
        gene = variant.gene
        if chrom:
            loc = f"{chrom.text}:{pos}"
            print(f"""\t\tPos:                 {Green(loc, 20)} {Magenta(alleles)} Gene: {Blue(gene.text)}""")

    zyg = variant.zygosity
    if zyg:
        print(f"""\t\tZygosity:            {Blue(zyg.text)}""")
    ref_seq = variant.ref_seq
    if ref_seq: 
        print(f"""\t\tRef Seq:             {Green(ref_seq)}""")

    trnscpt = variant.transcript
    if trnscpt:
        hgvsc = variant.hgvsc
        if hgvsc:
            hgvsc = hgvsc.to_str()

        hgvsp = variant.hgvsp
        if hgvsp:
            hgvsp = hgvsp.to_str()
        print(f"""\t\tTranscript:          {Red(trnscpt.to_str(), 20)} HGSVC {Magenta(hgvsc, 12)} HGSVP {Yellow(hgvsp)}""")

    inh = variant.inheritance
    if inh:
        print(f"""\t\tMode of Inheritance: {Magenta(inh.coding.code, 8)} """)
    sig = variant.significance
    if sig:
        print(f"""\t\tSignificance:        {Magenta(sig.coding.code, 8)}""")

# The Patient acts as the mastermind for the print statements and will
# call on any relevant prints required
def PrintPatient(patient):
    print(f"""{Cyan(patient.id, 8)} ID: {Magenta(patient.subject_id, 10)} Sex: {Yellow(patient.sex, 8)} Race:Ethnicity {Red(patient.race + ":" + patient.eth)}""")
    print(f"""dbGaP: {Green(patient.dbgap_study_id)}@{Blue(patient.dbgap_study_id)}""")

    relatives = patient.parents()
    if len(relatives) > 0:
        print(f"\nWe found {len(relatives)} relatives.")
        for relation in relatives.keys():
            fam_member = relatives[relation]
            print(f"""{Magenta(relation, 6)} {Blue(fam_member.subject_id, 10)} {Yellow(patient.sex, 8)} {Red(patient.race + ":" + patient.eth)}""")

    specimens = patient.specimens()
    if len(specimens) > 0:
        print(f"\nSpecimen: ")
        for spec in specimens:
            PrintSpecimen(specimens[spec], patient.dbgap_study_id)

    diseases = patient.diseases()
    if len(diseases) > 0:
        print("\nDisease Details: ")
        for d in diseases:
            PrintDisease(diseases[d])
    present_pheno, absent_pheno = patient.phenotypes()
    if (len(present_pheno) + len(absent_pheno)) > 0:
        print("\nPhenotypic Features Present")
        if len(present_pheno) == 0:
            print("\tNo phenotypic features were found")
        for p in present_pheno:
            PrintPhenotype(present_pheno[p], Green("Present", 10))

        print("\nPhenotypic Features ")
        if len(absent_pheno) == 0:
            print("\tNo phenotypic features were found")

        for p in absent_pheno:
            PrintPhenotype(absent_pheno[p], Red("Absent", 10))         

    if len(specimens) > 0:
        for spec in specimens:
            specimen = specimens[spec]
            variants = specimen.variants()

            if len(variants) > 0:
                print(f"\nVariants associated with specimen: {specimen.sample_id}")
                for var in variants:
                    PrintVariant(variants[var])

# Simple wrapper around listing N subjects and letting the user choose
# one (or exit)
def ChoosePatient(patients, max_shown=25):
    patient_idx = 0
    patient_count = len(patients)

    print(f"There are {Fore.MAGENTA}{len(patients)}{Fore.RESET} patients in this study.")
    patient_ids = sorted(patients.keys())
    idx = 0
    for subject_id in patient_ids:
        idx += 1
        p = patients[subject_id]
        print(f"\t{Cyan(idx, 8)} {Yellow(p.subject_id, 12)} - {Green(p.sex, 8)} {Red(p.race + ' ' + p.eth, 24)}")
        if idx == len(patients) or (idx % max_shown == 0):

            selected = input("Select an index above, 'X' to quit otherwise, we'll show next few: ")

            if selected.upper() == 'X':
                sys.exit(1)
            try:
                idx = int(selected) - 1

                if idx < len(patients):
                    return patients[patient_ids[idx]]
            except:
                pass

    print("You didn't choose one, Dave. I choose for you:")
    p = patients[patient_ids[random.randrange(len(patients))]]

    return p

if __name__=='__main__':
    # For now, this assumes you have the hosts listed in a 
    # dot rc file, ~/.ncpi_fhir_rc
    # TODO Write a quick description on how to create that
    # This config is used to establish the host and configure
    # the relevant authentication components for it. 
    config = DataConfig.config(hosts_only=True)

    # Just capture the available environments to let the user
    # make the selection at runtime
    env_options = config.list_environments()

    parser = ArgumentParser()
    parser.add_argument("-e", 
                "--env", 
                choices=env_options, 
                default='dev', 
                help=f"Remote configuration to be used")

    args = parser.parse_args()

    # The host's details are a part of that configured environment
    fhir_host = config.set_host(args.env)

    # Get a list of each of the research study objects
    studies = ResearchStudy.Studies(fhir_host)
    study_list = sorted(studies.keys())
    print(f"The following studies were found: ")

    # Iterate over them so the user can see what to choose from
    for study_name in sorted(study_list):
        print(f"\t{Fore.CYAN}{study_name}{Fore.RESET}")

    # Exit if there isn't any data in the server
    if len(study_list) == 0:
        sys.stderr(f"{Fore.RED}There are no studies to look over at the host {args.env}{Fore.RESET}\n")
        sys.exit(1)

    # No need to get anything from the user if there is only one to 
    # choose from
    if len(study_list) == 1:
        study = studies[study_list[0]]
    else:
        study = None
    
    # We'll default to whatever is the first in the list
    default = study_list[0]
    while study is None:
        study = input(f"Please Select a Study To View [{default}]: ").strip()

        if study == '':
            study = default
        
        if study in studies:
            study = studies[study]
        else:
            study = None

    print(f"Moving forward with the study: {Fore.YELLOW}{study.id}{Fore.RESET}")

    # Use the study object to pull each of the patients
    # TODO: I could certainly make life better by pulling them in 
    # chunks...
    patients = study.Patients()

    # Loop until the user is done, letting them choose a patient to 
    # review
    selected_patient = None
    while selected_patient == None:
        selected_patient = ChoosePatient(patients)
        PrintPatient(selected_patient)

        response = input("\nDo you want to look at someone else?[Y/n] ")
        if response.lower()[0] == 'y':
            selected_patient = None



