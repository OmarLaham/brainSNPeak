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
		exclude_brain_region = request.POST.get('exclude_brain_region')
		
		if exclude_dev_details == None:
			exclude_dev_details = False
		else:
			exclude_dev_details = True
			
		if exclude_brain_region == None:
			exclude_brain_region = False
		else:
			exclude_brain_region = True
		

		response_status = 200 # unless we have any error
		response_message = ""

		response_snps = []

		# first check that input is correct
		valid_input = True
		snp_ids = snp_ids.split(",")
		for snp_id in snp_ids:
			snp_id = snp_id.strip()
			if snp_id[0:2] != "rs":
				response_status = 500
				response_message = "some SNP ids are invalid"
				valid_input = False
				break
			
			
		# search for results
		if valid_input:
			try:
			
				#first load the df that maps snp_ids to map_ids
				df_gwas_peak = pd.read_csv(path.join(settings.DATA_DIR,"snps_mapped_to_peak_ids.tsv"), sep="\t", index_col=0, keep_default_na=False) # don't convert empty values to NaN
			
				for snp_id in snp_ids:
					snp_id = snp_id.strip()        
					res = df_gwas_peak.loc[snp_id]
					if not len(res):
						response_snps.append({"id": snp_id, "ocrs": "NA"})
					else:
						peak_id = dict(res)["peak_id"]
						peak_info_path = path.join(settings.PEAKS_INFO_DIR, "{0}.tsv".format(peak_id))

						if not path.exists(peak_info_path):
							response_snps.append({"id": snp_id, "ocrs": "NA"})
						else:
							df_peak = pd.read_csv(peak_info_path, sep="\t")
							
							# reorder
							df_peak = df_peak[["specimen", "cell_type", "brain_region"]]
							
							if exclude_dev_details: #give results regardless of development timepoint
								del df_peak["specimen"]
								
							if exclude_brain_region:
								del df_peak["brain_region"]
								
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



