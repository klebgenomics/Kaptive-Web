from shutil import copyfile


# Validate and process zip file
def process_zip_file(filename):
    import zipfile
    zip_file = open(filename, 'r')
    if zipfile.is_zipfile(zip_file):
        zip_file.close()
        zip_ref = zipfile.ZipFile(filename, 'r')
        if zip_ref.testzip() is not None:
            zip_ref.close()
            session.flash = "Invalid zip file."
            redirect(URL('kaptive'))
        else:
            try:
                zip_ref.extractall("/opt/kaptive/uploads/" + session.uuid + "/")
            except:
                session.flash = "Error occurs when try to unzip file. Please double check the zip file and try again."
                redirect(URL('kaptive'))
            finally:
                zip_ref.close()
    else:
        session.flash = "Invalid zip file."
        redirect(URL('kaptive'))


# Process tar.gz file
def process_gz_file(filename):
    import subprocess
    try:
        subprocess.call(['tar', 'xzf', filename], cwd=("/opt/kaptive/uploads/" + session.uuid + "/"))
    except:
        session.flash = "Error occurs when try to unzip file. Please double check the zip file and try again."
        redirect(URL('kaptive'))


# Read JSON Object from a file without blocking
def read_json_from_file(f):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    data = OrderedDict()
    t = 0
    while t <= 10:
        try:
            with open(f, 'r') as file:
                data = json.load(file, object_pairs_hook=OrderedDict)
                logger.debug('[' + uuid + '] ' + 'Read from file: ' + f)
        except ValueError as e:
            logger.error('[' + uuid + '] ' + 'Error reading file ' + f + ': ' + str(e) + ' Try again in 2 seconds')
            time.sleep(2)
            t += 1
            if (t == 10) and (not f.endswith('.bak')):
                backup_file((f + '.bak'), f)
                time.sleep(2)
                data = read_json_from_file(f)
                break
            continue
        except (IOError, OSError) as e:
            logger.error('[' + uuid + '] ' + 'Error reading file ' + f + ': ' + str(e))
            if not f.endswith('.bak'):
                backup_file((f + '.bak'), f)
                time.sleep(2)
                data = read_json_from_file(f)
        break
    return data


# Save JSON Object to a file without blocking
def save_json_to_file(f, json_string):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    try:
        with open(f, 'wb+') as file:
            json.dump(json_string, file, indent=4)
            logger.debug('[' + uuid + '] ' + 'Wrote to file: ' + f)
    except (IOError, OSError) as e:
        logger.error('[' + uuid + '] ' + 'Error writing file: \n' + f + '; ' + str(e))


def create_table_file():
    table_path = os.path.join(upload_path, session.uuid, 'kaptive_results_table.txt')

    if os.path.isfile(table_path):
        with open(table_path, 'r') as existing_table:
            first_line = existing_table.readline().strip()
            if first_line.startswith('Assembly\tBest match locus'):
                return

    headers = ['Assembly',
               'Best match locus',
               'Match confidence',
               'Problems',
               'Coverage',
               'Identity',
               'Length discrepancy',
               'Expected genes in locus',
               'Expected genes in locus, details',
               'Missing expected genes',
               'Other genes in locus',
               'Other genes in locus, details',
               'Expected genes outside locus',
               'Expected genes outside locus, details',
               'Other genes outside locus',
               'Other genes outside locus, details',
               'wzc',
               'wzi']

    with open(table_path, 'w') as table:
        table.write('\t'.join(headers))
        table.write('\n')


# Append a line to result table
def append_to_table(f, line):
    table = open(f, 'at')
    job_table_lock.acquire()
    # lock_file(table)
    table.write('\t'.join(line))
    table.write('\n')
    # unlock_file(table)
    job_table_lock.release()


def build_meta_json(uuid, job_name, fastafiles, no_of_fastas, reference, submit_time):
    meta_dict = OrderedDict()
    meta_dict['Token'] = uuid
    meta_dict['Job Name'] = job_name
    meta_dict['Assembly File'] = fastafiles
    meta_dict['No of Assembly File'] = no_of_fastas
    meta_dict['Reference'] = reference
    meta_dict['Start Time'] = submit_time
    meta_dict_file = os.path.join(upload_path, uuid, 'meta.json')
    save_json_to_file(meta_dict_file, meta_dict)
    logger.debug('[' + uuid + '] ' + 'Metadata file created.')


def build_job_list(job_list, fastafile, seq):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    job_detail = OrderedDict()
    job_detail['Fasta file'] = fastafile
    job_detail['Job status'] = 0
    job_detail['Job seq'] = seq
    job_detail['Standard out'] = ''
    job_detail['Standard error'] = ''
    job_detail['Start time'] = ''
    job_detail['Finish time'] = ''
    job_list.append(job_detail)
    logger.debug('[' + uuid + '] [' + str(seq) + '] ' + 'Job added: ' + fastafile)


def build_job_dict(uuid, reference, submit_time, fastafiles, no_of_fastas, upload_path):
    job_dict = OrderedDict()
    job_list = []
    seq = 0
    seq_no = 0
    job_dict['Token'] = uuid
    job_dict['Reference database'] = reference
    job_dict['Fasta files'] = ''
    job_dict['Start time'] = submit_time
    job_dict['Total jobs'] = 0
    job_dict['Jobs pending'] = 0
    job_dict['Jobs running'] = 0
    job_dict['Jobs succeeded'] = 0
    job_dict['Jobs failed'] = 0
    job_dict['Last job submitted'] = None
    for f in fastafiles:
        build_job_list(job_list, f, seq)
        seq += 1
    job_dict['Job list'] = job_list
    job_dict['Fasta files'] = fastafiles
    job_dict['Total jobs'] = no_of_fastas
    job_dict['Jobs pending'] = no_of_fastas
    job_file_path = os.path.join(upload_path, uuid, 'job_list.json')
    save_json_to_file(job_file_path, job_dict)
    logger.debug('[' + uuid + '] ' + 'Wrote job list to file: ' + job_file_path)


def upload_file(file, filename=None, path=None):
    import shutil
    path = os.path.join(upload_path, session.uuid)
    if not os.path.exists(path):
        os.makedirs(path)
    pathfilename = os.path.join(path, filename)
    dest_file = open(pathfilename, 'wb')
    try:
            shutil.copyfileobj(file, dest_file)
    finally:
            dest_file.close()
    return filename


def backup_file(src, dst):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    try:
        with open(src, 'r') as file:
            lock_file(file)
            copyfile(src, dst)
            unlock_file(file)
        logger.debug('[' + uuid + '] ' + 'File backed up: ' + dst)
    except (IOError, OSError) as e:
        logger.error('[' + uuid + '] ' + 'Error backing up file: ' + src + ': ' + str(e))
