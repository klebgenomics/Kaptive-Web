import ConfigParser
import logging
import os
import subprocess
import threading
import time
from collections import OrderedDict
from datetime import datetime

queue_lock = threading.Lock()
job_list_lock = threading.Lock()
job_json_lock = threading.Lock()
job_table_lock = threading.Lock()

# Read config file
Config = ConfigParser.ConfigParser()
Config.read('applications/kaptive/settings.ini')
base_path = Config.get('Path', 'base_path')
reference_database_path = Config.get('Path', 'reference_database_path')
upload_path = Config.get('Path', 'upload_path')
download_path = Config.get('Path', 'download_path')
queue_path = Config.get('Path', 'queue_path')
job_waiting_time = Config.get('General', 'job_waiting_time')
refresh_waiting_time = Config.get('General', 'refresh_waiting_time')
captcha = Config.getboolean('Security', 'captcha')
# Set path
job_queue_path = os.path.join(queue_path, 'queue')

# Setup logger
logger = logging.getLogger("kaptive")
logger.setLevel(logging.DEBUG)

# Get number of tblastn or blastn running (for debug purpose only)
procs = subprocess.check_output(['ps', 'uaxw']).splitlines()
blast_procs = [proc for proc in procs if 'blast' in proc]
blast_count = len(blast_procs)
if blast_count > 0:
    logger.debug(' Blast found: ' + str(blast_count))


def index():
    return dict()


def jobs():
    import uuid
    import fnmatch
    import re

    if request.vars.message is not None:
        response.flash = request.vars.message

    # Generate an UUID for each job submission
    session.uuid = str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # Get a list of reference database files, order by file name.
    #  - Copy the database files to this folder.
    #  - Name the first one (default) 1-xxxx, second one 2-xxxx, so on so forth.
    # -------------------------------------------------------------------------
    filelist = {}
    logger.debug('[' + session.uuid + '] ' + 'Reference database file found:')
    for f in sorted(os.listdir(reference_database_path)):
        if os.path.isfile(os.path.join(reference_database_path, f)) and fnmatch.fnmatch(f, '*.gbk'):
            fname = re.sub('\.gbk$', '', f)
            fname = re.sub('_', ' ', fname)
            fname = re.sub('\d-', '', fname)
            logger.debug('[' + session.uuid + '] ' + 'Database Name: ' + f)
            filelist.update({f: fname.replace(' k ', ' K ').replace(' o ', ' O ')})
    filelist_sorted = sorted(filelist.iteritems(), key=lambda d: d[0])
    if len(filelist) == 0:
        logger.error('[' + session.uuid + '] ' + 'No reference database file found.')
        response.flash = 'Internal error. No reference database file found. Please contact us.'

    # Create the form
    fields = [Field('job_name', label=T('Job name (optional)')),
              Field('assembly','upload', requires=[IS_NOT_EMPTY()], label=T('Assembly file*'), custom_store=upload_file),
              Field('reference', requires=IS_IN_SET(filelist_sorted, zero=None), label=T('Reference database'))
              ]
    if captcha:
        fields.append(captcha_field()) # Google reCaptcha v2

    form = SQLFORM.factory(*fields)

    # Process the form
    if form.accepts(request.vars, session):  # .process().accepted
        submit_time = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
        file_dir = os.path.join(upload_path, session.uuid)
        file_path = os.path.join(file_dir, request.vars.assembly.filename)

        # Unpack, if a zip / tar.gz file is uploaded
        compression = get_compression_type(file_path)
        if compression == 'zip':
            process_zip_file(file_dir, file_path)
            logger.debug('[' + session.uuid + '] ' + 'Zip file uploaded: ' + request.vars.assembly.filename)
        elif compression == 'gz':
            process_gz_file(file_dir, request.vars.assembly.filename)
            logger.debug('[' + session.uuid + '] ' + 'GZip file uploaded: ' + request.vars.assembly.filename)

        # Get a list of fasta files
        fastalist = [f for f in os.listdir(os.path.join(upload_path, session.uuid))
                     if os.path.isfile(os.path.join(upload_path, session.uuid, f))]
        fastafiles = []
        no_of_fastas = 0
        for f in fastalist:
            if is_file_fasta(os.path.join(upload_path, session.uuid, f)):

                # Spaces and hashes cause problems, so rename files to be spaceless and hashless, if needed.
                if ' ' in f:
                    new_f = f.replace(' ', '_')
                    logger.debug('[' + session.uuid + '] ' + 'Renaming file to remove spaces: ' +
                                 f + ' -> ' + new_f)
                    os.rename(os.path.join(upload_path, session.uuid, f),
                              os.path.join(upload_path, session.uuid, new_f))
                    f = new_f
                if '#' in f:
                    new_f = f.replace('#', '_')
                    logger.debug('[' + session.uuid + '] ' + 'Renaming file to remove hashes: ' +
                                 f + ' -> ' + new_f)
                    os.rename(os.path.join(upload_path, session.uuid, f),
                              os.path.join(upload_path, session.uuid, new_f))
                    f = new_f

                logger.debug('[' + session.uuid + '] ' + 'Fasta file(s) uploaded: ' + f)
                fastafiles.append(f)
                no_of_fastas += 1
        if no_of_fastas == 0:
            logger.error('[' + session.uuid + '] ' + 'No fasta file found in uploaded file.')
            redirect(URL(r=request, f='jobs', vars=dict(message=T("No fasta file was found in the uploaded file."))))
        fastafiles_string = ', '.join(fastafiles)
        logger.debug('[' + session.uuid + '] ' + 'Selected reference database: ' + request.vars.reference)

        # Save job details to a JSON file
        build_meta_json(session.uuid, request.vars.job_name, fastafiles_string, no_of_fastas,
                        filelist.get(request.vars.reference, None), submit_time)

        # Create empty result file
        create_table_file(request.vars.reference)

        # Build job list
        build_job_dict(session.uuid, request.vars.reference, submit_time, fastafiles, no_of_fastas, upload_path)

        # Add job to job queue
        add_job_to_queue(job_queue_path, session.uuid, no_of_fastas)

        # Run jobs
        t = threading.Thread(target=consume_worker, args=(job_queue_path, upload_path, ))
        t.start()

        # Set status to 1 (i.e. redirected from job upload page) for result page to display content accordingly
        session.status = 1
        redirect(URL('confirmation'))
    elif form.errors:
        response.flash = 'Error(s) found in the form. Please double check and submit again.'
        logger.error('[' + session.uuid + '] ' + 'Error(s) found in the form.')
    return dict(form=form)


def confirmation():
    import os
    refresh_time = int(refresh_waiting_time)
    if session.status < 1:  # If is redirected from kaptive page or from get result page
        session.flash = T('Please submit a job or use a token to get the result for a previous job.')
        logger.debug(' (Confirmation) Direct visit to confirmation page.')
        redirect(URL('jobs'))

    meta_file = os.path.join(upload_path, session.uuid, 'meta.json')
    job_file_path = os.path.join(upload_path, session.uuid, 'job_list.json')

    if (not os.path.exists(meta_file)) and (not os.path.exists(job_file_path)):  # If files does not exist
        session.flash = T('Internal Error. Job list or meta file not found. Please submit the job again.')
        logger.debug('[' + session.uuid + '] ' + '(Confirmation) Job list or meta file not found.')
        redirect(URL('jobs'))

    meta_data = read_json_from_file(meta_file)
    job_data = read_json_from_file(job_file_path)

    # Load meta file to display
    meta_token = meta_data["Token"]
    meta_job_name = meta_data["Job Name"]
    meta_assembly = meta_data["Assembly File"]
    meta_no_of_assembly = meta_data["No of Assembly File"]
    meta_reference = meta_data["Reference"]
    meta_time_stamp = meta_data["Start Time"]
    total_jobs = job_data['Total jobs']
    pending_jobs = job_data['Jobs pending']
    running_jobs = job_data['Jobs running']
    succeeded_jobs = job_data['Jobs succeeded']
    failed_jobs = job_data['Jobs failed']

    result_path = os.path.join(upload_path, session.uuid, 'kaptive_results_table.txt')
    result_json_path = os.path.join(upload_path, session.uuid, 'kaptive_results.json')

    if os.path.exists(result_json_path) and (succeeded_jobs + failed_jobs == total_jobs):  # If job finished
        content = ''
        result_data = read_json_from_file(result_json_path)
        result_status = 1
    elif pending_jobs == 0 and running_jobs == 0:
        content = ''
        result_status = 1
    else:
        if os.path.exists(result_path):  # If result txt file exists
            if total_jobs == pending_jobs:
                content = 'Job is in the queue. It will be processed when a processor is available.'
                logger.debug('[' + session.uuid + '] ' + 'No available worker. Job is in the queue.')
                result_status = 2
            else:
                content = 'Processing your job, it usually takes 10 minutes for each assembly file to complete. ' \
                          'This page will refresh every ' + str(refresh_time / 1000) + \
                          ' seconds until the process is completed. Please do not close this page or start a new job.'
                if os.path.exists(result_json_path):
                    result_data = read_json_from_file(result_json_path)
                else:
                    logger.debug('[' + session.uuid + '] ' + 'Cannot find final result JSON file.')
                result_status = 2
        else:
            content = 'Job is not running, please submit job again.'
            result_status = 3

    if failed_jobs > 0:
        job_data = read_json_from_file(job_file_path)
        error_dict = []
        for i in job_data['Job list']:
            if i['Job status'] == 3:
                error_data = OrderedDict()
                error_data['Job name'] = i['Fasta file']
                error_data['Error'] = i['Standard error']
                error_dict.append(error_data)
    return locals()


def result():
    fields = [Field('uuid', requires=IS_NOT_EMPTY(), label=T('Token'))]
    if captcha:
        fields.append(captcha_field())
    form = SQLFORM.factory(*fields)

    token_status = 0
    if form.accepts(request.vars, session):
        token_uuid = request.vars.uuid.strip()
        meta_file = os.path.join(upload_path, token_uuid, 'meta.json')
        if os.path.exists(meta_file):  # If the meta file exists
            session.uuid = token_uuid
            session.status = 2
            redirect(URL('confirmation'))
        else:
            token_status = 1
            redirect(URL('result'))
            return locals()
    elif form.errors:
        response.flash = 'Form has errors, please double check.'
    return locals()


def user():
    return dict()


@cache.action()
def download():
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    jid = request.args(0)
    sid = request.args(1)
    fid = request.args(2)
    root_path = os.path.join(download_path, jid)
    if not os.path.exists(root_path) and not os.path.isfile(root_path):
        os.makedirs(root_path)
    job_path = os.path.join(root_path, sid)
    if not os.path.exists(job_path) and not os.path.isfile(job_path):
        os.makedirs(job_path)
    if sid == 'result':
        pathfilename = os.path.join(upload_path, jid, fid)
    else:
        pathfilename = os.path.join(upload_path, jid, sid, fid)
    if os.path.exists(pathfilename):
        subprocess.call(['cp', pathfilename, job_path])
        res = os.path.join(job_path, fid)
    else:
        redirect(URL(r=request, f='jobs', vars=dict(message=T("Result file not found. Please resubmit job."))))
    return response.stream(open(res, 'rb'), chunk_size=4096)


@cache.action()
def get_svg():
    uuid = request.args(0)
    assemble_name = request.args(1)
    path = os.path.join(upload_path, uuid, 'locus_image', assemble_name + '.svg')
    return response.stream(path)


@cache.action()
def get_png():
    uuid = request.args(0)
    assemble_name = request.args(1)
    path = os.path.join(upload_path, uuid, 'locus_image', assemble_name + '.png')
    if os.path.exists(path):
        return response.stream(path)
    else:
        path = os.path.join(upload_path, 'image_not_found.svg')
        return response.stream(path)


def call():
    return service()


# Start the job if there is job in the queue
init_job_data = read_json_from_file(job_queue_path)
if len(init_job_data['Job queue']) > 0:
    logger.debug(' Start job left in the queue.')
    available_worker = init_job_data['Available worker']
    logger.debug(' Available workers: ' + str(available_worker))
    pending_jobs = 0
    if len(init_job_data['Job queue']) > 0:
        for i in init_job_data['Job queue']:
            pending_jobs = pending_jobs + i[1]
    if len(init_job_data['Processing queue']) > 0:
        for i in init_job_data['Processing queue']:
            pending_jobs = pending_jobs + i[1]
    for i in range(min(available_worker, pending_jobs)):
        init_t = threading.Thread(target=consume_worker, args=(job_queue_path, upload_path, ))
        init_t.start()
        time.sleep(2)
        logger.debug(' Start to processing job ' + str(i + 1) + ' left in the queue.')
