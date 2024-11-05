from __future__ import annotations

import os
import subprocess
import threading
import json
from collections import OrderedDict
from datetime import datetime
import time
import re
from io import StringIO, BytesIO

from Bio.Graphics import GenomeDiagram
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from reportlab.lib.colors import black
import lxml.etree as le
import cairosvg
import numpy as np
from PIL import Image

# Constants ------------------------------------------------------------------------------------------------------------
_LOCUS_REGEX = re.compile(r'(?<=locus:)\w+|(?<=locus: ).*')


# Functions ------------------------------------------------------------------------------------------------------------
def add_job_to_queue(job_queue_path, job_uuid, no_of_fastas, retry=0):
    queue_lock.acquire()
    logger.debug(f'[{job_uuid}] Queue lock acquire')
    backup_file(job_queue_path, (job_queue_path + '.bak'))
    try:
        with open(job_queue_path, 'r+') as queue_file:
            queue_data = json.load(queue_file, object_pairs_hook=OrderedDict)
            logger.debug(f'[{job_uuid}] Read job queue file.')
            job_queue = queue_data['Job queue']
            job_queue.insert(len(job_queue), [job_uuid, no_of_fastas])
            queue_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
            queue_file.seek(0)
            json.dump(queue_data, queue_file, indent=4)
            queue_file.truncate()
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{job_uuid}] Queue lock release')
            logger.debug(f'[{job_uuid}] Added job ' + job_uuid + ' to job queue.')
    except ValueError as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job queue file: ' + str(e) + ' Try again in 2 seconds')
            time.sleep(2)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{job_uuid}] Queue lock release')
            retry += 1
            add_job_to_queue(job_queue_path, job_uuid, retry)
    except (IOError, OSError) as e:
        logger.error(f'[{job_uuid}] Error reading job queue file: {e}; Restore backup and try again')
        if retry <= 10:
            backup_file((job_queue_path + '.bak'), job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{job_uuid}] Queue lock release')
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
        logger.debug(f'[{uuid}] Queue lock acquire')
        backup_file(job_queue_path, (job_queue_path + '.bak'))
        try:
            with open(job_queue_path, 'r+') as queue_file:
                queue_data = json.load(queue_file, object_pairs_hook=OrderedDict)
                logger.debug(f'[{uuid}] Read from job queue file')
                total_worker = queue_data['Total worker']
                logger.debug(f'Available workers: {queue_data["Available worker"]}')

                # Get total number of pending jobs
                pending_jobs = 0
                if len(queue_data['Job queue']) > 0:
                    for i in queue_data['Job queue']:
                        pending_jobs = pending_jobs + i[1]
                if len(queue_data['Processing queue']) > 0:
                    for i in queue_data['Processing queue']:
                        pending_jobs = pending_jobs + i[1]
                logger.debug(f'[{uuid}] Pending jobs in the queue: {pending_jobs}')

                if queue_data['Available worker'] > 0 and pending_jobs > 0:
                    logger.debug(f'[{uuid}] Available worker: {queue_data["Available worker"]}; '
                                 f'Pending jobs in the queue: {pending_jobs}')
                    for i in range(min(queue_data['Available worker'], pending_jobs)):
                        # Get job ID from queue
                        if len(queue_data['Job queue']) > 0:
                            logger.debug(f'[{uuid}] Get job from the job queue.')
                            job_in_queue = queue_data['Job queue'][0]
                            job_uuid = job_in_queue[0]
                            queue_data['Job queue'].remove(job_in_queue)
                            if job_in_queue[1] > 1:
                                job_in_queue = [(job_in_queue[0]), (job_in_queue[1] - 1)]
                                queue_data['Processing queue'].insert(len(queue_data['Processing queue']), job_in_queue)
                                logger.debug(
                                    f'[{uuid}] Moved first job in job queue to the tail of processing queue: {job_uuid}')
                            queue_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_data['Available worker'] -= 1
                            queue_data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_file.seek(0)
                            json.dump(queue_data, queue_file, indent=4)
                            queue_file.truncate()
                            logger.debug(f'[{uuid}] Updated job queue file for job: {job_uuid}')
                            background_thread = threading.Thread(target=run_kaptive,
                                                                 args=(job_queue_path, upload_path, job_uuid,))
                            background_thread.start()
                        else:
                            logger.debug(f'[{uuid}] Get job from the processing queue.')
                            job_in_queue = queue_data['Processing queue'][0]
                            job_uuid = job_in_queue[0]
                            queue_data['Processing queue'].remove(job_in_queue)
                            if job_in_queue[1] > 1:
                                job_in_queue = [(job_in_queue[0]), (job_in_queue[1] - 1)]
                                queue_data['Processing queue'].insert(len(queue_data['Processing queue']), job_in_queue)
                                logger.debug(f'[{uuid}] Moved first job in processing try to the tail: {job_uuid}')
                            queue_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_data['Available worker'] -= 1
                            queue_data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                            queue_file.seek(0)
                            json.dump(queue_data, queue_file, indent=4)
                            queue_file.truncate()
                            logger.debug(f'[{uuid}] Updated job queue file for job: {job_uuid}')
                            background_thread = threading.Thread(target=run_kaptive,
                                                                 args=(job_queue_path, upload_path, job_uuid,))
                            background_thread.start()
                    if queue_lock.locked():
                        queue_lock.release()
                    logger.debug(f'[{uuid}] Queue lock release')
                    break
                elif pending_jobs == 0:
                    if queue_lock.locked():
                        queue_lock.release()
                    logger.debug(f'[{uuid}] Queue lock release')
                    logger.debug(f'[{uuid}] No job in the queue.')
                    break
                else:
                    if queue_lock.locked():
                        queue_lock.release()
                    logger.debug(f'[{uuid}] Queue lock release')
                    logger.debug(f'[{uuid}] No available worker to process this job. Try again in {job_waiting_time}s')
                    time.sleep(int(job_waiting_time))
                    continue
        except ValueError as e:
            if retry <= 10:
                logger.error(f'[{uuid}] Error reading job queue file: {e} Try again in 2s')
                if queue_lock.locked():
                    queue_lock.release()
                logger.debug(f'[{uuid}]  Queue lock release')
                time.sleep(2)
                retry += 1
                consume_worker(job_queue_path, upload_path, retry)
                break
        except (IOError, OSError) as e:
            if retry <= 10:
                logger.error(f'[{uuid}] Error reading job queue file: {e}; Restore backup and try again.')
                backup_file((job_queue_path + '.bak'), job_queue_path)
                if queue_lock.locked():
                    queue_lock.release()
                logger.debug(f'[{uuid}] Queue lock release')
                retry += 1
                consume_worker(job_queue_path, upload_path, retry)
                break
        break


def run_kaptive(job_queue_path, upload_path, job_uuid, retry=0):
    job_file_path = os.path.join(upload_path, job_uuid, 'job_list.json')
    job_list_lock.acquire()
    logger.debug(f'[{job_uuid}] File list lock acquire')
    backup_file(job_file_path, (job_file_path + '.bak'))
    try:
        with open(job_file_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug(f'[{job_uuid}] Read job list file for job: {job_uuid}')
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
                        logger.debug(f'[{job_uuid}] File list lock release')
                        if job_data['Jobs pending'] == 0 and job_data['Jobs running'] == 0:  # This is the last job
                            release_job(job_queue_path, job_uuid)

                        logger.debug(
                            f'[{job_uuid}] [{seq_no}] Job finished: {fastafile}; Pending: {job_data["Jobs pending"]}; '
                            f'Running: {job_data["Jobs running"]};  Finished: {job_data["Jobs succeeded"]}; '
                            f'Error: {job_data["Jobs failed"]}'
                        )

                        json_path = os.path.join(upload_path, job_uuid, 'kaptive_results.json')
                        table_path = os.path.join(upload_path, job_uuid, 'kaptive_results_table.txt')

                        if not os.path.exists(cwd := os.path.join(upload_path, job_uuid, str(seq_no))):
                            os.makedirs(cwd)
                        logger.debug(f'[{job_uuid}] [{seq_no}] Current work directory: {cwd}')

                        job_json_path = os.path.join(upload_path, job_uuid, str(seq_no), 'kaptive_results.json')

                        cmd = f'kaptive assembly {reference_db} ../{fastafile} --no-header -j -f'
                        logger.debug(f'[{job_uuid}] [{seq_no}] {cmd=}')
                        out, err = subprocess.Popen(
                            cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, universal_newlines=True,
                            stderr=subprocess.PIPE).communicate()
                        process_result(job_file_path, job_queue_path, upload_path, job_json_path, table_path,
                                       json_path, out, err, seq_no, job_uuid, fastafile, reference_db)
                        break

            else:
                if job_list_lock.locked():
                    job_list_lock.release()
                logger.debug(f'[{job_uuid}] File list lock release')
                release_job(job_queue_path, job_uuid)
                logger.debug(f'[{job_uuid}] Releasing worker')
                release_worker(job_queue_path)
                queue_lock.acquire()
                job_data = read_json_from_file(job_queue_path)
                if (len(job_data['Job queue']) > 0 or len(job_data['Processing queue']) > 0) \
                        and job_data['Available worker'] > 0:
                    logger.debug(f'[{job_uuid}] Found jobs in the queue file')
                    logger.debug(f'[{job_uuid}] Start a new session')
                    t = threading.Thread(target=consume_worker, args=(job_queue_path, upload_path,))
                    t.start()
                if queue_lock.locked():
                    queue_lock.release()
    except ValueError as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job list file: {e}. Try again in 2s')
            if job_list_lock.locked():
                job_list_lock.release()
            logger.debug(f'[{job_uuid}] File list lock release')
            time.sleep(2)
            retry += 1
            run_kaptive(job_queue_path, upload_path, job_uuid, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job list file: {e}. Restore backup and try again.')
            backup_file((job_file_path + '.bak'), job_file_path)
            if job_list_lock.locked():
                job_list_lock.release()
            logger.debug(f'[{job_uuid}] File list lock release')
            time.sleep(2)
            retry += 1
            run_kaptive(job_queue_path, upload_path, job_uuid, retry)


def release_worker(job_queue_path, retry=0):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
        ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid
    queue_lock.acquire()
    logger.debug(f'[{uuid}] Queue lock acquire')
    backup_file(job_queue_path, (job_queue_path + '.bak'))
    try:
        with open(job_queue_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug(f'[{uuid}] Read job queue file')
            available_worker = job_data['Available worker']
            job_data['Available worker'] = available_worker + 1
            job_data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
            job_file.seek(0)
            json.dump(job_data, job_file, indent=4)
            job_file.truncate()
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{uuid}] Queue lock release')
            logger.error(f'[{uuid}] Worker is released. Available workers: {available_worker + 1}')
    except ValueError as e:
        if retry <= 10:
            logger.error(f'[{uuid}] Error reading job queue file: {e}. Try again in 2s')
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{uuid}] Queue lock release')
            time.sleep(2)
            retry += 1
            release_worker(job_queue_path, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error(f'[{uuid}] Error reading job queue file: {e}. Restore backup and try again.')
            backup_file((job_queue_path + '.bak'), job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{uuid}] Queue lock release')
            time.sleep(2)
            retry += 1
            release_worker(job_queue_path, retry)


def release_job(job_queue_path, job_uuid, retry=0):
    queue_lock.acquire()
    logger.debug(f'[{job_uuid}] Queue lock acquire')
    backup_file(job_queue_path, (job_queue_path + '.bak'))
    try:
        with open(job_queue_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug(f'[{job_uuid}] Read job queue file.')
            for i in job_data['Processing queue']:
                if job_uuid in i[0]:
                    job_data['Processing queue'].remove(i)
                    job_data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
                    job_file.seek(0)
                    json.dump(job_data, job_file, indent=4)
                    job_file.truncate()
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{job_uuid}] Queue lock release')
            logger.debug(f'[{job_uuid}] Removed job from processing queue: {job_uuid}')
    except ValueError as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job queue file: {e}. Try again in 2s')
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{job_uuid}] Queue lock release')
            time.sleep(2)
            retry += 1
            release_job(job_queue_path, job_uuid, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job queue file: {e}. Restore backup and try again.')
            backup_file((job_queue_path + '.bak'), job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            logger.debug(f'[{job_uuid}] Queue lock release')
            time.sleep(2)
            retry += 1
            release_job(job_queue_path, job_uuid, retry)


def process_result(job_file_path, job_queue_path, upload_path, job_json_path, job_table_path, json_path,
                   out, err, seq_no, job_uuid, fastafile, reference_db, retry=0):
    job_list_lock.acquire()
    logger.debug(f'[{job_uuid}] File list lock acquire')
    backup_file(job_file_path, (job_file_path + '.bak'))
    try:
        with open(job_file_path, 'r+') as job_file:
            job_data = json.load(job_file, object_pairs_hook=OrderedDict)
            logger.debug(f'[{job_uuid}] Read job list file.')
            job_data['Job list'][seq_no]['Standard out'] = out
            job_data['Job list'][seq_no]['Standard error'] = err
            job_data['Jobs running'] -= 1
            job_data['Job list'][seq_no]['Finish time'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))

            if out and os.stat(job_json_path).st_size > 0:  # Job finished
                logger.debug(f'[{job_uuid}] [{seq_no}] Standard Out: Yes')
                job_data['Job list'][seq_no]['Job status'] = 2  # Change status to job finished.
                os.remove(os.path.join(upload_path, job_uuid, fastafile))  # Remove the fasta file
                job_data['Jobs succeeded'] += 1
                job_file.seek(0)
                json.dump(job_data, job_file, indent=4)
                job_file.truncate()
                if job_list_lock.locked():
                    job_list_lock.release()
                logger.debug(f'[{job_uuid}] File list lock release')

                # Write result to the table
                job_table_lock.acquire()
                backup_file(job_table_path, (job_table_path + '.bak'))
                with open(job_table_path, 'at') as table:
                    table.write(out)
                    logger.debug(f'[{job_uuid}] [{seq_no}] Wrote to TXT result file.')
                job_table_lock.release()

                # Write to JSON result file
                job_json_lock.acquire()
                logger.debug(f'[{job_uuid}] JSON lock acquire')
                if os.path.exists(json_path):
                    backup_file(json_path, (json_path + '.bak'))
                if job_json_lock.locked():
                    job_json_lock.release()
                logger.debug(f'[{job_uuid}] JSON lock release')
                write_to_result_json(job_json_path, json_path, seq_no)
                # Draw locus image
                draw_locus_image(reference_db, job_json_path, upload_path, job_uuid)
                os.remove(job_json_path)  # Remove the individual JSON file
            else:  # Job failed
                # Write to job list file
                job_data['Job list'][seq_no]['Job status'] = 3  # Change status to job failed.
                job_data['Jobs failed'] += 1
                job_file.seek(0)
                json.dump(job_data, job_file, indent=4)
                job_file.truncate()
                if job_list_lock.locked():
                    job_list_lock.release()
                logger.debug(f'[{job_uuid}] File list lock release')

            logger.debug(
                f'[{job_uuid}] [{seq_no}]' f'Job finished: {fastafile}; Pending: {job_data["Jobs pending"]}; '
                f'Running: {job_data["Jobs running"]};  Finished: {job_data["Jobs succeeded"]}; Error: {job_data["Jobs failed"]}'
            )
            logger.debug(f'[{job_uuid}] Releasing worker')
            release_worker(job_queue_path)
            job_list_lock.acquire()
            job_data = read_json_from_file(job_file_path)
            if job_list_lock.locked():
                job_list_lock.release()
            if job_data['Jobs pending'] == 0 and job_data['Jobs running'] == 0:  # This is the last job
                # logger.debug(f'[{job_uuid}] Fasta file(s) are removed.')
                logger.debug(f'[{job_uuid}] All files has been processed.')
                release_job(job_queue_path, job_uuid)
            logger.debug(f'[{job_uuid}] Reading queue file for new jobs.')
            queue_lock.acquire()
            queue_data = read_json_from_file(job_queue_path)
            if queue_lock.locked():
                queue_lock.release()
            if len(queue_data['Job queue']) > 0 or len(queue_data['Processing queue']) > 0:
                logger.debug(f'[{job_uuid}] Found jobs in the queue file.')
                t = threading.Thread(target=consume_worker, args=(job_queue_path, upload_path,))
                t.start()
    except ValueError as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job list file: {e}; Try again in 2s')
            if job_list_lock.locked():
                job_list_lock.release()
            logger.debug(f'[{job_uuid}] File list lock release')
            time.sleep(2)
            retry += 1
            process_result(job_file_path, job_queue_path, upload_path, job_json_path, job_table_path,
                           json_path, out, err, seq_no, job_uuid, fastafile, reference_db, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error(f'[{job_uuid}] Error reading job list file: {e}; Restore backup and try again.')
            backup_file((job_file_path + '.bak'), job_file_path)
            logger.debug(f'[{job_uuid}] File list lock release')
            if job_list_lock.locked():
                job_list_lock.release()
            time.sleep(2)
            retry += 1
            process_result(job_file_path, job_queue_path, upload_path, job_json_path, job_table_path,
                           json_path, out, err, seq_no, job_uuid, fastafile, reference_db, retry)


def draw_locus_image(reference_db, job_json_path, upload_path, job_uuid):
    if not os.path.exists(job_json_path):
        return

    job_result_data = read_json_from_file(job_json_path, json_lines=True)[0]

    locus_image_folder_path = os.path.join(upload_path, job_uuid, 'locus_image')
    if not os.path.exists(locus_image_folder_path):
        os.makedirs(locus_image_folder_path)

    png_path = os.path.join(locus_image_folder_path, job_result_data["sample_name"] + '.png')
    locus_record = get_locus_record(locus := job_result_data["best_match"], reference_db)

    genes_in_locus = {
        i['gene']: (float(i['percent_identity']), float(i['percent_coverage']), i['partial'] == 'True',
                    i['phenotype'] == 'truncated', i['below_threshold'] == 'True')
        for i in job_result_data["expected_genes_inside_locus"]
    }
    gd = GenomeDiagram.Diagram(name=locus)
    gd_feature_set = gd.new_track(
        1, name=locus, greytrack=False, start=0, end=len(locus_record), scale_ticks=0).new_set()

    for n, gene in enumerate(filter(lambda i: i.type == 'CDS', locus_record.features), start=1):
        gene_name = f"{locus}_{str(n).zfill(2)}" + (f"_{x}" if (x := gene.qualifiers.get('gene', [''])[0]) else '')
        if gene_result := genes_in_locus.get(gene_name):
            gene_colour = get_gene_colour(*gene_result[0:2])
            gene_name = f'{gene_name} {gene_result[0]:.2f}% {gene_result[1]:.2f}%'
            if gene_result[2]:
                gene_name += ' partial'
            elif gene_result[3]:
                gene_name += ' truncated'
            elif gene_result[4]:
                gene_name += ' below threshold'
        else:
            gene_colour = '#E5E5E5'

        gd_feature_set.add_feature(
            gene, sigil="BIGARROW", border=black, color=gene_colour, arrowshaft_height=1.0, label=True,
            name=gene_name, label_position="middle", label_angle=20, label_strand=1, label_size=20)

    gd.draw(format="linear", pagesize=(1800, 100), x=0, yt=0, yb=0, y=0, fragments=1, start=0, end=len(locus_record))

    with StringIO() as f:  # Use StringIO to write GenomeDiagram SVG to a string
        gd.write(f, "SVG")  # No intermediate files are needed here
        svg = process_svg(f.getvalue())  # Then trim the SVG with the process_svg function

    with BytesIO() as png:  # Use BytesIO to write PNG to byte string
        cairosvg.svg2png(svg, write_to=png)
        img = np.array(Image.open(png))  # Load PNG into numpy

    idx = np.where(img[:, :, 3] > 0)  # Trim whitespace with numpy
    x0, y0, x1, y1 = idx[1].min(), idx[0].min(), idx[1].max(), idx[0].max()
    out = Image.fromarray(img[y0:y1 + 1, x0:x1 + 1, :])  # Convert array back to image
    out.save(png_path)  # Save the image


def get_locus_record(locus, gbk_file) -> SeqRecord | None:
    """Returns the requested locus from the reference genbank"""
    for record in SeqIO.parse(gbk_file, 'genbank'):
        if source := next(filter(lambda i: i.type == 'source' and i.qualifiers.get('note'), record.features)):
            for note in source.qualifiers['note']:
                if (m := _LOCUS_REGEX.search(note)) and m.group(0) == locus:
                    return record
    return None


def get_gene_colour(cov: float, ident: float) -> str:
    """Taken from Kaptive 2, we no longer give genes confidence"""
    if cov >= 100.0 and ident >= 99.0:
        return '#7F407F'  # Very high
    elif cov >= 99.0 and ident >= 95.0:
        return '#995C99'  # High
    elif cov >= 97.0 and ident >= 95.0:
        return '#B27DB2'  # Good
    elif cov >= 95.0 and ident >= 85.0:
        return '#CCA3CC'  # Low
    else:
        return '#D9C3D9'  # None


def process_svg(svg_string: str) -> str:
    """
    Parses an SVG string as an element tree and removes unwanted layers
    """
    svg_elements = le.fromstring(svg_string.encode())
    count_a = 0
    count_b = 0
    for elem in svg_elements.xpath('//*[attribute::style]'):
        if elem.attrib['style'] == "stroke-linecap: butt; stroke-width: 1; stroke: rgb(0%,0%,0%);":
            count_a += 1
        elif elem.attrib['style'] == "stroke-width: 1; stroke-linecap: butt; stroke: rgb(0%,0%,0%);":
            count_b += 1
    if count_a == 2:
        for elem in svg_elements.xpath('//*[attribute::style]'):
            if elem.attrib['style'] == "stroke-linecap: butt; stroke-width: 1; stroke: rgb(0%,0%,0%);":
                parent = elem.getparent()
                parent.remove(elem)
            elif elem.attrib['style'] == "stroke-width: 1; stroke-linecap: butt; stroke: rgb(0%,0%,0%);":
                for elem_g in svg_elements.xpath('//*[attribute::transform]'):
                    if elem_g.attrib['transform'] == "":
                        elem_g.insert(0, elem)
    elif count_b == 2:
        for elem in svg_elements.xpath('//*[attribute::style]'):
            if elem.attrib['style'] == "stroke-width: 1; stroke-linecap: butt; stroke: rgb(0%,0%,0%);":
                parent = elem.getparent()
                parent.remove(elem)
            elif elem.attrib['style'] == "stroke-linecap: butt; stroke-width: 1; stroke: rgb(0%,0%,0%);":
                for elem_g in svg_elements.xpath('//*[attribute::transform]'):
                    if elem_g.attrib['transform'] == "":
                        elem_g.insert(0, elem)
    rect = svg_elements.xpath('//svg:rect', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    rect[0].set('y', '-100')
    for elem in svg_elements.xpath('//*[attribute::height]'):
        if elem.attrib['height'] == "100":
            elem.attrib['height'] = "800"
    for elem in svg_elements.xpath('//*[attribute::width]'):
        if elem.attrib['width'] == "1800":
            elem.attrib['width'] = "2500"
    for elem in svg_elements.xpath('//*[attribute::viewBox]'):
        if elem.attrib['viewBox'] == "0 0 1800 100":
            elem.attrib['viewBox'] = "0 0 2500 100"
    for elem in svg_elements.xpath('//*[attribute::transform]'):
        if elem.attrib['transform'] == "scale(1,-1) translate(0,-100)":
            elem.attrib['transform'] = "scale(1,-1) translate(0,-300)"

    for elem in svg_elements.xpath('//*[attribute::style]'):  # Removes the black lines and background
        if not elem.text and 'path' in elem.tag:  # Tom Stanton 03.10.2022
            parent = elem.getparent()
            parent.remove(elem)
    return le.tostring(svg_elements, pretty_print=True, encoding="utf-8")
