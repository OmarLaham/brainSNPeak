from django.conf import settings
from os import path
from django.http import JsonResponse
from django import template
from django.views import View

import pandas as pd
import numpy as np

import os
from os import path
import json 


def query_snp_ids_api(request):


	# accept only POST since snp_ids field value could be very long and that wouldn't fit a GET form straightforward
	if request.method != 'POST':
		response = {
			"status" : 500,
			"message" : "Please use POST method only",
			"snps" : []
		}
		return JsonResponse(response)
		
	else:
		snp_ids = request.POST.get('snp_ids')
		exclude_dev_details = request.POST.get('exclude_dev_details')
		brain_region = request.POST.get('brain_region')
		
		if exclude_dev_details == None:
			exclude_dev_details = False
		else:
			exclude_dev_details = True
		

		response_status = 200 # unless we have any error
		response_message = ""

		response_snps = []

		# first check that input is correct
		valid_input = True
		
		#if snps are separated
		snp_ids = snp_ids.split("\n")
		for snp_id in snp_ids:
			snp_id = snp_id.strip() # remove spaces
			snp_id = snp_id.rstrip() #remove \r
			if snp_id[0:2] != "rs":
				response_status = 500
				response_message = "some SNP ids are invalid"
				valid_input = False
				break
				
		# validate brain region input
		if not brain_region in ["NA", "exclude", "Cortex", "Insula", "M1", "MGE", "Parietal", "PFC", "Somato", "Temporal", "V1"]:
			response_status = 500
			response_message = "invalid brain region"
			valid_input = False
			
			
		# search for results
		if valid_input:
			try:
			
				#first load the df that maps snp_ids to map_ids
				df_gwas_peak = pd.read_csv(path.join(settings.DATA_DIR,"snps_mapped_to_peak_ids.tsv"), sep="\t", keep_default_na=False) # don't convert empty values to NaN
			
				for snp_id in snp_ids:
					snp_id = snp_id.strip()  
					res = df_gwas_peak.query("id=='{0}'".format(snp_id))
					if not len(res):
						response_snps.append({"id": snp_id, "ocrs": "NA"})
					else:
						peak_id = res.reset_index().loc[0, "peak_id"]
						peak_info_path = path.join(settings.PEAKS_INFO_DIR, "{0}.tsv".format(peak_id))

						if not path.exists(peak_info_path):
							response_snps.append({"id": snp_id, "ocrs": "NA2"})
						else:
							df_peak = pd.read_csv(peak_info_path, sep="\t")
							
							# reorder
							df_peak = df_peak[["specimen", "cell_type", "brain_region"]]
							
							if exclude_dev_details: #give results regardless of development timepoint
								del df_peak["specimen"]
								
							if brain_region == "exclude":
								del df_peak["brain_region"]
							elif brain_region != "NA": # if not all regions are selected (no filter)
								df_peak = df_peak.query("brain_region=='{0}'".format(brain_region))
								
							df_peak = df_peak.drop_duplicates()
							df_peak = df_peak.sort_values(list(df_peak.columns), ascending=True) # sort by all remaining cols asc
							
							dict_ocrs = {
								"colnames": " - ".join(list(df_peak.columns)),
								"n_entries": len(df_peak),
								"values": df_peak.values.tolist()
							}
							
							response_snps.append({"id": snp_id, "ocrs": dict_ocrs})

				response_message = "query_result"
			
			except Exception as ex:
				print("> error:", ex)
				response_status = 500
				response_message = "unknown error"

		response = {
			"status" : response_status,
			"message" : response_message,
			"snps" : response_snps
		}

		return JsonResponse(response, json_dumps_params={'indent': 2}) 



