
import os
from app import app
import ftputil
import credentials
import json
import requests
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['mgf', 'mzxml', 'mzml', 'csv', 'txt'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_single_file(request, group):
    sessionid = request.cookies.get('sessionid')

    filename = ""

    if 'file' not in request.files:
        return "{}"
    request_file = request.files['file']

    return upload_single_file_push(request_file, sessionid, group)

def upload_single_file_push(request_file, uuid_folder, collection_name):
    if request_file.filename == '':
        return "{}"
    if request_file and allowed_file(request_file.filename):
        filename = secure_filename(request_file.filename)
        save_dir = os.path.join(app.config['UPLOAD_FOLDER'], uuid_folder, collection_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        local_filename = os.path.join(save_dir, filename)
        request_file.save(local_filename)

        #Uploading to FTP
        upload_to_gnps(local_filename, uuid_folder, collection_name)

        #Remove local file
        os.remove(local_filename)
    else:
        print("not allowed")
        json.dumps({"status": "Invalid File Type"})

    return json.dumps({"filename": filename})


def check_ftp_folders(username):
    url = "ccms-ftp01.ucsd.edu"
    present_folders = []

    with ftputil.FTPHost(url, credentials.USERNAME, credentials.PASSWORD) as ftp_host:
        names = ftp_host.listdir(ftp_host.curdir)
        if not username in names:
            return present_folders

        ftp_host.chdir(username)

        return ftp_host.listdir(ftp_host.curdir)

    return present_folders


def upload_to_gnps(input_filename, folder_for_spectra, group_name):
    url = "ccms-ftp01.ucsd.edu"

    with ftputil.FTPHost(url, credentials.USERNAME, credentials.PASSWORD) as ftp_host:
        names = ftp_host.listdir(ftp_host.curdir)
        try:
            if not folder_for_spectra in names:
                print("MAKING DIR")
                ftp_host.mkdir(folder_for_spectra)
        except:
            print("Cannot Make Folder", folder_for_spectra)

        ftp_host.chdir(folder_for_spectra)
        try:
            if not group_name in ftp_host.listdir(ftp_host.curdir):
                print("MAKING Group DIR")
                ftp_host.mkdir(group_name)
        except:
            print("Cannot Make Folder", group_name)
        ftp_host.chdir(group_name)

        ftp_host.upload(input_filename, os.path.basename(input_filename))

def get_classic_networking_lowres_parameters():
    invokeParameters = {}
    invokeParameters["workflow"] = "METABOLOMICS-SNETS-V2"
    invokeParameters["protocol"] = "None"
    invokeParameters["library_on_server"] = "d.speclibs;"
    invokeParameters["tolerance.PM_tolerance"] = "2.0"
    invokeParameters["tolerance.Ion_tolerance"] = "0.5"
    invokeParameters["PAIRS_MIN_COSINE"] = "0.70"
    invokeParameters["MIN_MATCHED_PEAKS"] = "6"
    invokeParameters["TOPK"] = "10"
    invokeParameters["CLUSTER_MIN_SIZE"] = "2"
    invokeParameters["RUN_MSCLUSTER"] = "on"
    invokeParameters["MAXIMUM_COMPONENT_SIZE"] = "100"
    invokeParameters["MIN_MATCHED_PEAKS_SEARCH"] = "6"
    invokeParameters["SCORE_THRESHOLD"] = "0.7"
    invokeParameters["ANALOG_SEARCH"] = "0"
    invokeParameters["MAX_SHIFT_MASS"] = "100.0"
    invokeParameters["FILTER_STDDEV_PEAK_datasetsINT"] = "0.0"
    invokeParameters["MIN_PEAK_INT"] = "0.0"
    invokeParameters["FILTER_PRECURSOR_WINDOW"] = "1"
    invokeParameters["FILTER_LIBRARY"] = "1"
    invokeParameters["WINDOW_FILTER"] = "1"
    invokeParameters["CREATE_CLUSTER_BUCKETS"] = "1"
    invokeParameters["CREATE_ILI_OUTPUT"] = "0"

    return invokeParameters

def get_classic_networking_highres_parameters():
    invokeParameters = {}
    invokeParameters["workflow"] = "METABOLOMICS-SNETS-V2"
    invokeParameters["protocol"] = "None"
    invokeParameters["library_on_server"] = "d.speclibs;"
    invokeParameters["tolerance.PM_tolerance"] = "0.05"
    invokeParameters["tolerance.Ion_tolerance"] = "0.05"
    invokeParameters["PAIRS_MIN_COSINE"] = "0.70"
    invokeParameters["MIN_MATCHED_PEAKS"] = "6"
    invokeParameters["TOPK"] = "10"
    invokeParameters["CLUSTER_MIN_SIZE"] = "2"
    invokeParameters["RUN_MSCLUSTER"] = "on"
    invokeParameters["MAXIMUM_COMPONENT_SIZE"] = "100"
    invokeParameters["MIN_MATCHED_PEAKS_SEARCH"] = "6"
    invokeParameters["SCORE_THRESHOLD"] = "0.7"
    invokeParameters["ANALOG_SEARCH"] = "0"
    invokeParameters["MAX_SHIFT_MASS"] = "100.0"
    invokeParameters["FILTER_STDDEV_PEAK_datasetsINT"] = "0.0"
    invokeParameters["MIN_PEAK_INT"] = "0.0"
    invokeParameters["FILTER_PRECURSOR_WINDOW"] = "1"
    invokeParameters["FILTER_LIBRARY"] = "1"
    invokeParameters["WINDOW_FILTER"] = "1"
    invokeParameters["CREATE_CLUSTER_BUCKETS"] = "1"
    invokeParameters["CREATE_ILI_OUTPUT"] = "0"

    return invokeParameters

def launch_GNPS_workflow(ftp_path, job_description, username, password, groups_present, email, preset):
    invokeParameters = {}

    if preset == "LOWRES":
        invokeParameters = get_classic_networking_lowres_parameters()
    elif preset == "HIGHRES":
        invokeParameters = get_classic_networking_highres_parameters()
    else:
        return "Error No Preset"

    invokeParameters["desc"] = job_description
    invokeParameters["spec_on_server"] = "d." + ftp_path + "/G1;"
    if "G2" in groups_present:
        invokeParameters["spec_on_server_group2"] = "d." + ftp_path + "/G2;"
    if "G3" in groups_present:
        invokeParameters["spec_on_server_group3"] = "d." + ftp_path + "/G3;"

    invokeParameters["email"] = email


    task_id = invoke_workflow("gnps.ucsd.edu", invokeParameters, username, password)

    return task_id

def launch_GNPS_featurenetworking_workflow(ftp_path, job_description, username, password, email, featuretool, present_folders, preset):
    invokeParameters = {}

    if preset == "LOWRES":
        invokeParameters = get_featurenetworking_lowres_parameters()
    elif preset == "HIGHRES":
        invokeParameters = get_featurenetworking_highres_parameters()
    else:
        return "Error No Preset"

    #Specific Parameters Update
    invokeParameters["desc"] = job_description

    invokeParameters["quantification_table"] = "d." + ftp_path + "/featurequantification;"
    invokeParameters["spec_on_server"] = "d." + ftp_path + "/featurems2;"
    if "samplemetadata" in present_folders:
        invokeParameters["metadata_table"] = "d." + ftp_path + "/samplemetadata;"

    #Quant
    invokeParameters["QUANT_TABLE_SOURCE"] = featuretool

    #Additional Pairs
    if "additionalpairs" in present_folders:
        invokeParameters["additional_pairs"] = "d." + ftp_path + "/additionalpairs;"

    invokeParameters["email"] = email

    task_id = invoke_workflow("gnps.ucsd.edu", invokeParameters, username, password)

    return task_id

def get_featurenetworking_lowres_parameters():
    invokeParameters = {}
    invokeParameters["workflow"] = "FEATURE-BASED-MOLECULAR-NETWORKING"
    invokeParameters["protocol"] = "None"
    invokeParameters["desc"] = "Job Description"
    invokeParameters["library_on_server"] = "d.speclibs;"

    #Networking
    invokeParameters["tolerance.PM_tolerance"] = "2.0"
    invokeParameters["tolerance.Ion_tolerance"] = "0.5"
    invokeParameters["PAIRS_MIN_COSINE"] = "0.70"
    invokeParameters["MIN_MATCHED_PEAKS"] = "6"
    invokeParameters["TOPK"] = "10"
    invokeParameters["MAX_SHIFT"] = "500"

    #Network Pruning
    invokeParameters["MAXIMUM_COMPONENT_SIZE"] = "100"

    #Library Search
    invokeParameters["MIN_MATCHED_PEAKS_SEARCH"] = "6"
    invokeParameters["SCORE_THRESHOLD"] = "0.7"
    invokeParameters["TOP_K_RESULTS"] = "1"
    invokeParameters["ANALOG_SEARCH"] = "0"
    invokeParameters["MAX_SHIFT_MASS"] = "100.0"
    invokeParameters["FILTER_STDDEV_PEAK_datasetsINT"] = "0.0"
    invokeParameters["MIN_PEAK_INT"] = "0.0"
    invokeParameters["FILTER_PRECURSOR_WINDOW"] = "1"
    invokeParameters["FILTER_LIBRARY"] = "1"
    invokeParameters["WINDOW_FILTER"] = "1"

    #Quant
    invokeParameters["QUANT_TABLE_SOURCE"] = ""
    invokeParameters["GROUP_COUNT_AGGREGATE_METHOD"] = "Mean"
    invokeParameters["QUANT_FILE_NORM"] = "RowSum"

    #External tools
    invokeParameters["RUN_DEREPLICATOR"] = "1"

    invokeParameters["email"] = "ccms.web@gmail.com"
    invokeParameters["uuid"] = "1DCE40F7-1211-0001-979D-15DAB2D0B500"

    return invokeParameters

def get_featurenetworking_highres_parameters():
    invokeParameters = {}
    invokeParameters["workflow"] = "FEATURE-BASED-MOLECULAR-NETWORKING"
    invokeParameters["protocol"] = "None"
    invokeParameters["desc"] = "Job Description"
    invokeParameters["library_on_server"] = "d.speclibs;"

    #Networking
    invokeParameters["tolerance.PM_tolerance"] = "0.05"
    invokeParameters["tolerance.Ion_tolerance"] = "0.05"
    invokeParameters["PAIRS_MIN_COSINE"] = "0.70"
    invokeParameters["MIN_MATCHED_PEAKS"] = "6"
    invokeParameters["TOPK"] = "10"
    invokeParameters["MAX_SHIFT"] = "500"

    #Network Pruning
    invokeParameters["MAXIMUM_COMPONENT_SIZE"] = "100"

    #Library Search
    invokeParameters["MIN_MATCHED_PEAKS_SEARCH"] = "6"
    invokeParameters["SCORE_THRESHOLD"] = "0.7"
    invokeParameters["TOP_K_RESULTS"] = "1"
    invokeParameters["ANALOG_SEARCH"] = "0"
    invokeParameters["MAX_SHIFT_MASS"] = "100.0"
    invokeParameters["FILTER_STDDEV_PEAK_datasetsINT"] = "0.0"
    invokeParameters["MIN_PEAK_INT"] = "0.0"
    invokeParameters["FILTER_PRECURSOR_WINDOW"] = "1"
    invokeParameters["FILTER_LIBRARY"] = "1"
    invokeParameters["WINDOW_FILTER"] = "1"

    #Quant
    invokeParameters["QUANT_TABLE_SOURCE"] = ""
    invokeParameters["GROUP_COUNT_AGGREGATE_METHOD"] = "Mean"
    invokeParameters["QUANT_FILE_NORM"] = "RowSum"

    #External tools
    invokeParameters["RUN_DEREPLICATOR"] = "1"

    invokeParameters["email"] = "ccms.web@gmail.com"
    invokeParameters["uuid"] = "1DCE40F7-1211-0001-979D-15DAB2D0B500"

    return invokeParameters


def invoke_workflow(base_url, parameters, login, password):
    username = login
    password = password

    s = requests.Session()

    payload = {
        'user' : username,
        'password' : password,
        'login' : 'Sign in'
    }

    r = s.post('https://' + base_url + '/ProteoSAFe/user/login.jsp', data=payload, verify=False)
    r = s.post('https://' + base_url + '/ProteoSAFe/InvokeTools', data=parameters, verify=False)
    task_id = r.text

    print(r.text)

    if len(task_id) > 4 and len(task_id) < 60:
        print("Launched Task: : " + r.text)
        return task_id
    else:
        print(task_id)
        return None
