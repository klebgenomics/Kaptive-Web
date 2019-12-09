import os
import subprocess
import time
import threading
import json
from collections import OrderedDict
from datetime import datetime
from Bio import SeqIO
from Bio.Graphics import GenomeDiagram


def add_job_to_queue(job_queue_path, job_uuid, no_of_fastas, retry=0):
    queue_lock.acquire()
    logger.debug('[' + job_uuid + '] ' + 'Queue lock acquire. [12]')
    backup_file(job_queue_path, (job_queue_path + '.bak'))
    try:
        with open(job_queue_path, 'r+') as queue_file:
            queue_data = json.load(queue_file, object_pairs_hook=OrderedDict)
            logger.debug('[' + job_uuid + '] ' + 'Read job queue file.')
            job_queue = queue_data['Job queue']
            job_queue.insert(len(job_queue), [job_uuid, no_of_fastas])
            queue_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
            queue_file.seek(0)
            json.dump(queue_data, queue_file, indent=4)
            queue_file.truncate()
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'Queue lock release. [26]')
            logger.debug('[' + job_uuid + '] ' + 'Added job ' + job_uuid + ' to job queue.')
    except ValueError as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job queue file: ' + str(e) + ' Try again in 2 seconds')
            time.sleep(2)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'Queue lock release. [33]')
            retry += 1
            add_job_to_queue(job_queue_path, job_uuid, retry)
    except (IOError, OSError) as e:
        logger.error('[' + job_uuid + '] ' + 'Error reading job queue file: ' + str(e) +
                     '. Restore backup and try again.')
        if retry <= 10:
            backup_file((job_queue_path + '.bak'), job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'Queue lock release. [41]')
            time.sleep(2)
            retry += 1
            add_job_to_queue(job_queue_path, job_uuid, retry)


def consume_worker(job_queue_path, upload_path, retry=0):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    while True:
        queue_lock.acquire()
        logger.debug('[' + uuid + '] ' + 'Queue lock acquire. [56]')
        backup_file(job_queue_path, (job_queue_path + '.bak'))
        try:
            with open(job_queue_path, 'r+') as queue_file:
                queue_data = json.load(queue_file, object_pairs_hook=OrderedDict)
                logger.debug('[' + uuid + '] ' + 'Read from job queue file.')
                total_worker = queue_data['Total worker']
                logger.debug(' Available workers: ' + str(queue_data['Available worker']))

                # Get total number of pending jobs
                pending_jobs = 0
                if len(queue_data['Job queue']) > 0:
                    for i in queue_data['Job queue']:
                        pending_jobs = pending_jobs + i[1]
                if len(queue_data['Processing queue']) > 0:
                    for i in queue_data['Processing queue']:
                        pending_jobs = pending_jobs + i[1]
                logger.debug('[' + uuid + '] ' + 'Pending jobs in the queue: ' + str(pending_jobs))

                if queue_data['Available worker'] > 0 and pending_jobs > 0:
                    logger.debug('[' + uuid + '] ' + ' * Available worker: ' +
                                 str(queue_data['Available worker']) +
                                 '. Pending jobs in the queue: ' + str(pending_jobs))
                    for i in range(min(queue_data['Available worker'], pending_jobs)):
                        # Get job ID from queue
                        if len(queue_data['Job queue']) > 0:
                            logger.debug('[' + uuid + '] ' + ' * Get job from the job queue.')
                            job_in_queue = queue_data['Job queue'][0]
                            job_uuid = job_in_queue[0]
                            queue_data['Job queue'].remove(job_in_queue)
                            if job_in_queue[1] > 1:
                                job_in_queue = [(job_in_queue[0]), (job_in_queue[1]-1)]
                                queue_data['Processing queue'].insert(len(queue_data['Processing queue']), job_in_queue)
                                logger.debug('[' + uuid + '] ' +
                                             'Moved first job in job queue to the tail of processing queue: ' +
                                             job_uuid)
                            queue_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_data['Available worker'] -= 1
                            queue_data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_file.seek(0)
                            json.dump(queue_data, queue_file, indent=4)
                            queue_file.truncate()
                            logger.debug('[' + uuid + '] ' + 'Updated job queue file for job: ' + job_uuid)
                            background_thread = threading.Thread(target=run_script,
                                                                 args=(job_queue_path, upload_path, job_uuid, ))
                            background_thread.start()
                        else:
                            logger.debug('[' + uuid + '] ' + ' * Get job from the processing queue.')
                            job_in_queue = queue_data['Processing queue'][0]
                            job_uuid = job_in_queue[0]
                            queue_data['Processing queue'].remove(job_in_queue)
                            if job_in_queue[1] > 1:
                                job_in_queue = [(job_in_queue[0]), (job_in_queue[1]-1)]
                                queue_data['Processing queue'].insert(len(queue_data['Processing queue']), job_in_queue)
                                logger.debug('[' + uuid + '] ' +
                                             'Moved first job in proecssing try to the tail: ' +
                                             job_uuid)
                            queue_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_data['Available worker'] -= 1
                            queue_data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_file.seek(0)
                            json.dump(queue_data, queue_file, indent=4)
                            queue_file.truncate()
                            logger.debug('[' + uuid + '] ' + 'Updated job queue file for job: ' + job_uuid)
                            background_thread = threading.Thread(target=run_script,
                                                                 args=(job_queue_path, upload_path, job_uuid, ))
                            background_thread.start()
                    if queue_lock.locked():
                        queue_lock.release()
                    logger.debug('[' + uuid + '] ' + 'Queue lock release. [133]')
                    break
                elif pending_jobs == 0:
                    if queue_lock.locked():
                        queue_lock.release()
                    logger.debug('[' + uuid + '] ' + 'Queue lock release. [125]')
                    logger.debug('[' + uuid + '] ' + 'No job in the queue.')
                    break
                else:
                    if queue_lock.locked():
                        queue_lock.release()
                    logger.debug('[' + uuid + '] ' + 'Queue lock release. [132]')
                    logger.debug('[' + uuid + '] ' + 'No available worker to process this job. Try again in ' +
                                 job_waiting_time + ' seconds.')
                    time.sleep(int(job_waiting_time))
                    continue
        except ValueError as e:
            if retry <= 10:
                logger.error('[' + uuid + '] ' + 'Error reading job queue file: ' + str(e) + ' Try again in 2 seconds')
                if queue_lock.locked():
                    queue_lock.release()
                logger.debug('[' + uuid + '] ' + 'Queue lock release. [141]')
                time.sleep(2)
                retry += 1
                consume_worker(job_queue_path, upload_path, retry)
                break
        except (IOError, OSError) as e:
            if retry <= 10:
                logger.error('[' + uuid + '] ' + 'Error reading job queue file: ' + str(e) +
                             '. Restore backup and try again.')
                backup_file((job_queue_path + '.bak'), job_queue_path)
                if queue_lock.locked():
                    queue_lock.release()
                logger.debug('[' + uuid + '] ' + 'Queue lock release. [150]')
                retry += 1
                consume_worker(job_queue_path, upload_path, retry)
                break
        break


def run_script(job_queue_path, upload_path, job_uuid, retry=0):
    job_file_path = os.path.join(upload_path, job_uuid, 'job_list.json')
    table_path = os.path.join(upload_path, job_uuid, 'kaptive_results_table.txt')
    job_list_lock.acquire()
    logger.debug('[' + job_uuid + '] ' + 'File list lock acquire. [160]')
    backup_file(job_file_path, (job_file_path + '.bak'))
    try:
        with open(job_file_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug('[' + job_uuid + '] ' + 'Read job list file for job: ' + job_uuid)
            if job_data['Jobs pending'] > 0:
                for i in job_data['Job list']:
                    if i['Job status'] == 0:  # Job is pending
                        # Get parameters
                        fastafile = i['Fasta file']
                        reference_db = job_data['Reference database']
                        seq_no = i['Job seq']
                        i['Job status'] = 1  # Change status to job running.
                        job_data['Jobs pending'] -= 1
                        job_data['Jobs running'] += 1
                        i['Start time'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                        job_file.seek(0)
                        json.dump(job_data, job_file, indent=4)
                        job_file.truncate()
                        if job_list_lock.locked():
                            job_list_lock.release()
                        logger.debug('[' + job_uuid + '] ' + 'File list lock release. [182]')
                        if job_data['Jobs pending'] == 0 and job_data['Jobs running'] == 0:  # This is the last job
                            release_job(job_queue_path, job_uuid)

                        logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' +
                                     'Processing job: ' + fastafile +
                                     '. Pending: ' + str(job_data['Jobs pending']) +
                                     '. Running: ' + str(job_data['Jobs running']) +
                                     '. Finished: ' + str(job_data['Jobs succeeded']) +
                                     '. Error: ' + str(job_data['Jobs failed']))

                        job_result_path = os.path.join(upload_path, job_uuid, str(seq_no), 'kaptive_results.json')
                        result_path = os.path.join(upload_path, job_uuid, 'kaptive_results.json')
                        job_table_path = os.path.join(upload_path, job_uuid, str(seq_no), 'kaptive_results_table.txt')
                        out, err = run_kaptive(job_uuid, seq_no, fastafile, reference_db)

                        # Processing standard out and error
                        process_result(job_file_path, job_queue_path, upload_path, job_result_path, job_table_path,
                                       table_path, result_path, out, err, seq_no, job_uuid, fastafile, reference_db)
                        break
            else:
                if job_list_lock.locked():
                    job_list_lock.release()
                logger.debug('[' + job_uuid + '] ' + 'File list lock release. [203]')
                release_job(job_queue_path, job_uuid)
                logger.debug('[' + job_uuid + '] ' + 'Releasing worker. [202]')
                release_worker(job_queue_path)
                queue_lock.acquire()
                job_data = read_json_from_file(job_queue_path)
                if (len(job_data['Job queue']) > 0 or len(job_data['Processing queue']) > 0) \
                        and job_data['Available worker'] > 0:
                    logger.debug('[' + job_uuid + '] ' + 'Found jobs in the queue file. [231]')
                    logger.debug('[' + job_uuid + '] ' + 'Start a new session.')
                    t = threading.Thread(target=consume_worker, args=(job_queue_path, upload_path, ))
                    t.start()
                if queue_lock.locked():
                    queue_lock.release()
    except ValueError as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job list file: ' + str(e) + ' Try again in 2 seconds')
            if job_list_lock.locked():
                job_list_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'File list lock release. [212]')
            time.sleep(2)
            retry += 1
            run_script(job_queue_path, upload_path, job_uuid, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job list file: ' + str(e) +
                         '. Restore backup and try again.')
            backup_file((job_file_path + '.bak'), job_file_path)
            if job_list_lock.locked():
                job_list_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'File list lock release. [221]')
            time.sleep(2)
            retry += 1
            run_script(job_queue_path, upload_path, job_uuid, retry)


def release_worker(job_queue_path, retry=0):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid
    queue_lock.acquire()
    logger.debug('[' + uuid + '] ' + 'Queue lock acquire. [233]')
    backup_file(job_queue_path, (job_queue_path + '.bak'))
    try:
        with open(job_queue_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug('[' + uuid + '] ' + 'Read job queue file.')
            available_worker = job_data['Available worker']
            job_data['Available worker'] = available_worker + 1
            job_data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
            job_file.seek(0)
            json.dump(job_data, job_file, indent=4)
            job_file.truncate()
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + uuid + '] ' + 'Queue lock release. [248]')
            logger.error('[' + uuid + '] ' + 'Worker is released. Available workers: ' + str(available_worker + 1))
    except ValueError as e:
        if retry <= 10:
            logger.error('[' + uuid + '] ' + 'Error reading job queue file: ' + str(e) + ' Try again in 2 seconds')
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + uuid + '] ' + 'Queue lock release. [254]')
            time.sleep(2)
            retry += 1
            release_worker(job_queue_path, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error('[' + uuid + '] ' + 'Error reading job queue file: ' + str(e) +
                         '. Restore backup and try again.')
            backup_file((job_queue_path + '.bak'), job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + uuid + '] ' + 'Queue lock release. [263]')
            time.sleep(2)
            retry += 1
            release_worker(job_queue_path, retry)


def release_job(job_queue_path, job_uuid, retry=0):
    queue_lock.acquire()
    logger.debug('[' + job_uuid + '] ' + 'Queue lock acquire. [271]')
    backup_file(job_queue_path, (job_queue_path + '.bak'))
    try:
        with open(job_queue_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug('[' + job_uuid + '] ' + 'Read job queue file.')
            for i in job_data['Processing queue']:
                if job_uuid in i[0]:
                    job_data['Processing queue'].remove(i)
                    job_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                    job_file.seek(0)
                    json.dump(job_data, job_file, indent=4)
                    job_file.truncate()
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'Queue lock release. [286]')
            logger.debug('[' + job_uuid + '] ' + 'Removed job from processing queue: ' + job_uuid)
    except ValueError as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job queue file: ' + str(e) + ' Try again in 2 seconds')
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'Queue lock release. [293]')
            time.sleep(2)
            retry += 1
            release_job(job_queue_path, job_uuid, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job queue file: ' + str(e) +
                         '. Restore backup and try again.')
            backup_file((job_queue_path + '.bak'), job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'Queue lock release. [301]')
            time.sleep(2)
            retry += 1
            release_job(job_queue_path, job_uuid, retry)


def run_kaptive(job_uuid, seq_no, fastafile, reference_db):
    path = os.path.join(upload_path, job_uuid, str(seq_no))
    if not os.path.exists(path):
        os.makedirs(path)
    # Set parameters for Kaptive Script
    param1 = ' -a ../' + fastafile
    param2 = ' -k ' + reference_database_path + reference_db
    param3 = ' -v'
    if 'Klebsiella_k_locus_' in reference_db:
        param4 = ' -g ' + reference_database_path + 'wzi_wzc_db.fasta'
    else:
        param4 = ''

    # Generate the command line to run the Kaptive Python script
    cmd = 'python ' + base_path + 'kaptive.py' + param1 + param2 + param3 + param4
    logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' + 'Current work directory: ' + path)
    logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' + 'Command to run the job: ' + cmd)
    process_call = subprocess.Popen(cmd, cwd=path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process_call.communicate()
    time.sleep(3)
    return out, err


def process_result(job_file_path, job_queue_path, upload_path, job_result_path, job_table_path, table_path, result_path,
                   out, err, seq_no, job_uuid, fastafile, reference_db, retry=0):
    job_list_lock.acquire()
    logger.debug('[' + job_uuid + '] ' + 'File list lock acquire. [330]')
    backup_file(job_file_path, (job_file_path + '.bak'))
    try:
        with open(job_file_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug('[' + job_uuid + '] ' + 'Read job list file.')
            job_data['Job list'][seq_no]['Standard out'] = out
            job_data['Job list'][seq_no]['Standard error'] = err
            job_data['Jobs running'] -= 1
            job_data['Job list'][seq_no]['Finish time'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
            if out is not None and os.path.exists(job_result_path):  # Job finished
                logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' + 'Standard Out: Yes')
                job_data['Job list'][seq_no]['Job status'] = 2  # Change status to job finished.
                job_data['Jobs succeeded'] += 1
                job_file.seek(0)
                json.dump(job_data, job_file, indent=4)
                job_file.truncate()
                if job_list_lock.locked():
                    job_list_lock.release()
                logger.debug('[' + job_uuid + '] ' + 'File list lock release. [350]')
                # Write to TXT result file
                write_to_result_table(job_table_path, table_path, job_uuid, seq_no)

                # Write to JSON result file
                job_json_lock.acquire()
                logger.debug('[' + job_uuid + '] ' + 'JSON lock acquire. [358]')
                if os.path.exists(result_path):
                    backup_file(result_path, (result_path + '.bak'))
                if job_json_lock.locked():
                    job_json_lock.release()
                logger.debug('[' + job_uuid + '] ' + 'JSON lock release. [362]')
                write_to_result_json(job_result_path, result_path, seq_no)
                # Draw locus image
                draw_locus_image(reference_db, job_result_path, upload_path, job_uuid, seq_no)
            else:  # Job failed
                # Write to job list file
                job_data['Job list'][seq_no]['Job status'] = 3  # Change status to job failed.
                job_data['Jobs failed'] += 1
                job_file.seek(0)
                json.dump(job_data, job_file, indent=4)
                job_file.truncate()
                if job_list_lock.locked():
                    job_list_lock.release()
                logger.debug('[' + job_uuid + '] ' + 'File list lock release. [373]')
            logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' +
                         'Job: ' + fastafile + ' finished' +
                         '. Pending: ' + str(job_data['Jobs pending']) +
                         '. Running: ' + str(job_data['Jobs running']) +
                         '. Finished: ' + str(job_data['Jobs succeeded']) +
                         '. Error: ' + str(job_data['Jobs failed']))
            logger.debug('[' + job_uuid + '] ' + 'Releasing worker. [384]')
            release_worker(job_queue_path)
            job_list_lock.acquire()
            job_data = read_json_from_file(job_file_path)
            if job_list_lock.locked():
                job_list_lock.release()
            if job_data['Jobs pending'] == 0 and job_data['Jobs running'] == 0:  # This is the last job
                # Remove the fasta file
                [os.remove(os.path.join(upload_path, job_uuid, f)) for f in
                 os.listdir(os.path.join(upload_path, job_uuid)) if f.endswith(".fasta")]
                logger.debug('[' + job_uuid + '] ' + 'Fasta file(s) are removed.')
                logger.debug('[' + job_uuid + '] ' + 'All files has been processed.')
                release_job(job_queue_path, job_uuid)
            logger.debug('[' + job_uuid + '] ' + 'Reading queue file for new jobs.')
            queue_lock.acquire()
            queue_data = read_json_from_file(job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            if len(queue_data['Job queue']) > 0 or len(queue_data['Processing queue']) > 0:
                logger.debug('[' + job_uuid + '] ' + 'Found jobs in the queue file.')
                t = threading.Thread(target=consume_worker, args=(job_queue_path, upload_path, ))
                t.start()
    except ValueError as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job list file: ' + str(e) + ' Try again in 2 seconds')
            if job_list_lock.locked():
                job_list_lock.release()
            logger.debug('[' + job_uuid + '] ' + 'File list lock release. [396]')
            time.sleep(2)
            retry += 1
            process_result(job_file_path, job_queue_path, upload_path, job_result_path, job_table_path, table_path,
                           result_path, out, err, seq_no, job_uuid, fastafile, reference_db, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error('[' + job_uuid + '] ' + 'Error reading job list file: ' + str(e) +
                         '. Restore backup and try again.')
            backup_file((job_file_path + '.bak'), job_file_path)
            logger.debug('[' + job_uuid + '] ' + 'File list lock release. [404]')
            if job_list_lock.locked():
                job_list_lock.release()
            time.sleep(2)
            retry += 1
            process_result(job_file_path, job_queue_path, upload_path, job_result_path, job_table_path, table_path,
                           result_path, out, err, seq_no, job_uuid, fastafile, reference_db, retry)


def draw_locus_image(reference_db, job_result_path, upload_path, job_uuid, seq_no):
    from reportlab.lib.colors import black
    import lxml.etree as le


    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    job_result_data = read_json_from_file(job_result_path)
    locus = job_result_data[0]["Best match"]["Locus name"]
    if locus == 'O1v1' or locus == 'O2v1':
        locus = 'O1/O2v1'
    if locus == 'O1v2' or locus == 'O2v2':
        locus = 'O1/O2v2'
    assemble_name = job_result_data[0]["Assembly name"]
    locus_image_folder_path = os.path.join(upload_path, job_uuid, 'locus_image')

    if not os.path.exists(locus_image_folder_path):
        os.makedirs(locus_image_folder_path)

    gbk_file = reference_database_path + reference_db
    gbk_path = os.path.join(upload_path, job_uuid, str(seq_no), locus.replace('/', '_') + '.gbk')
    svg_path = os.path.join(locus_image_folder_path, assemble_name + '.svg')
    svg_temp_path = os.path.join(locus_image_folder_path, assemble_name + '_temp.svg')
    png_path = os.path.join(locus_image_folder_path, assemble_name + '.png')

    for record in SeqIO.parse(gbk_file, 'genbank'):
        for feature in record.features:
            if feature.type == 'source' and 'note' in feature.qualifiers:
                for note in feature.qualifiers['note']:
                    if ':' in note:
                        if note.split(':')[1].strip() == locus:
                            SeqIO.write(record, gbk_path, 'genbank')
                            logger.debug('[' + job_uuid + '] ' + "Locus genbank file created.")
                    elif '=' in note:
                        if note.split('=')[1].strip() == locus:
                            SeqIO.write(record, gbk_path, 'genbank')
                            logger.debug('[' + job_uuid + '] ' + "Locus genbank file created.")

    if os.path.exists(gbk_path):
        A_rec = SeqIO.read(gbk_path, "genbank")

        locus_genes = job_result_data[0]["Locus genes"]

        A_colors = []
        A_cov = []
        A_id = []
        A_name = []

        for genes in locus_genes:
            if genes["Result"] == "Found in locus":
                if genes["Match confidence"] == "Very high":
                    A_colors += ["#7F407F"]
                elif genes["Match confidence"] == "High":
                    A_colors += ["#995C99"]
                elif genes["Match confidence"] == "Good":
                    A_colors += ["#B27DB2"]
                elif genes["Match confidence"] == "Low":
                    A_colors += ["#CCA3CC"]
                elif genes["Match confidence"] == "None":
                    A_colors += ["#D9C3D9"]
                A_cov += [(" Cov: " + genes["tblastn result"]["Coverage"])]
                A_id += [(" ID: " + genes["tblastn result"]["Identity"])]
                if "Gene" not in genes["Reference"]:
                    A_name += [genes["Name"]]
                else:
                    A_name += [genes["Reference"]["Gene"]]
            else:
                A_colors += ["#E5E5E5"]
                A_cov += ['']
                A_id += ['']
                if "Gene" not in genes["Reference"]:
                    A_name += [genes["Name"]]
                else:
                    A_name += [genes["Reference"]["Gene"]]

        name = locus
        gd_diagram = GenomeDiagram.Diagram(name)
        max_len = 0
        for record, gene_colors, gene_cov, gene_id, gene_name in zip([A_rec], [A_colors], [A_cov], [A_id], [A_name]):
            max_len = max(max_len, len(record))
            gd_track_for_features = gd_diagram.new_track(1,
                                                         name=record.name,
                                                         greytrack=False,
                                                         start=0,
                                                         end=len(record),
                                                         scale_ticks=0)
            gd_feature_set = gd_track_for_features.new_set()

            i = 0
            for feature in record.features:
                if feature.type != "CDS":
                    # Exclude this feature
                    continue
                gd_feature_set.add_feature(feature,
                                           sigil="BIGARROW",
                                           border=black,
                                           color=gene_colors[i],
                                           arrowshaft_height=1.0,
                                           label=True,
                                           name=gene_name[i] + gene_cov[i] + gene_id[i],
                                           label_position="middle",
                                           label_size=14,
                                           label_angle=20,
                                           label_strand=1)
                i += 1

        gd_diagram.draw(format="linear",
                        pagesize=(1800, 100),
                        x=0, yt=0, yb=0, y=0,
                        fragments=1,
                        start=0, end=max_len)
        # gd_diagram.write(png_path, "PNG") # Use GenomeDiagram to generate PNG
        gd_diagram.write(svg_path, "SVG")

        with open(svg_path, 'r') as svg_file:
            svg = le.parse(svg_file)
            count_a = 0
            count_b = 0
            for elem in svg.xpath('//*[attribute::style]'):
                if elem.attrib['style'] == "stroke-linecap: butt; stroke-width: 1; stroke: rgb(0%,0%,0%);":
                    count_a += 1
                elif elem.attrib['style'] == "stroke-width: 1; stroke-linecap: butt; stroke: rgb(0%,0%,0%);":
                    count_b += 1
            if count_a == 2:
                for elem in svg.xpath('//*[attribute::style]'):
                    if elem.attrib['style'] == "stroke-linecap: butt; stroke-width: 1; stroke: rgb(0%,0%,0%);":
                        parent=elem.getparent()
                        parent.remove(elem)
                    elif elem.attrib['style'] == "stroke-width: 1; stroke-linecap: butt; stroke: rgb(0%,0%,0%);":
                        for elem_g in svg.xpath('//*[attribute::transform]'):
                            if elem_g.attrib['transform'] == "":
                                elem_g.insert(0, elem)
            elif count_b == 2:
                for elem in svg.xpath('//*[attribute::style]'):
                    if elem.attrib['style'] == "stroke-width: 1; stroke-linecap: butt; stroke: rgb(0%,0%,0%);":
                        parent = elem.getparent()
                        parent.remove(elem)
                    elif elem.attrib['style'] == "stroke-linecap: butt; stroke-width: 1; stroke: rgb(0%,0%,0%);":
                        for elem_g in svg.xpath('//*[attribute::transform]'):
                            if elem_g.attrib['transform'] == "":
                                elem_g.insert(0, elem)
            rect = svg.xpath('//svg:rect', namespaces={'svg': 'http://www.w3.org/2000/svg'})
            rect[0].set('y', '-100')
            for elem in svg.xpath('//*[attribute::height]'):
                if elem.attrib['height'] == "100":
                    elem.attrib['height'] = "800"
            for elem in svg.xpath('//*[attribute::width]'):
                if elem.attrib['width'] == "1800":
                    elem.attrib['width'] = "2500"
            for elem in svg.xpath('//*[attribute::viewBox]'):
                if elem.attrib['viewBox'] == "0 0 1800 100":
                    elem.attrib['viewBox'] = "0 0 2500 100"
            for elem in svg.xpath('//*[attribute::transform]'):
                if elem.attrib['transform'] == "scale(1,-1) translate(0,-100)":
                    elem.attrib['transform'] = "scale(1,-1) translate(0,-300)"

        with open(svg_temp_path, 'w') as f:
            f.write(le.tostring(svg))

        convert_cmd = 'convert ' + svg_temp_path + ' ' + png_path
        subprocess.call(convert_cmd, shell=True)

        trim_cmd = 'convert ' + png_path + ' -trim ' + png_path
        subprocess.call(trim_cmd, shell=True)
    else:
        logger.debug('[' + job_uuid + '] ' + "Failed to create locus image.")
