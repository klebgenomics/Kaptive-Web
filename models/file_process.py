from __future__ import annotations

import zipfile
import subprocess
import shutil
import os
import tarfile
from collections import OrderedDict

# Constants ------------------------------------------------------------------------------------------------------------
_KAPTIVE_HEADER = (
    'Assembly\tBest match locus\tBest match type\tMatch confidence\tProblems\tIdentity\tCoverage\t'
    'Length discrepancy\tExpected genes in locus\tExpected genes in locus, details\tMissing expected genes\t'
    'Other genes in locus\tOther genes in locus, details\tExpected genes outside locus\t'
    'Expected genes outside locus, details\tOther genes outside locus\tOther genes outside locus, details\t'
    'Truncated genes, details\tExtra genes, details\n'
)


# Functions ------------------------------------------------------------------------------------------------------------
def get_compression_type(filename):
    """
    Attempts to guess the compression (if any) on a file using the first few bytes.
    http://stackoverflow.com/questions/13044562
    """
    magic_dict = {'gz': (b'\x1f', b'\x8b', b'\x08'),
                  'bz2': (b'\x42', b'\x5a', b'\x68'),
                  'zip': (b'\x50', b'\x4b', b'\x03', b'\x04')}
    max_len = max(len(x) for x in magic_dict)

    with open(filename, 'rb') as unknown_file:
        file_start = unknown_file.read(max_len)
    compression_type = 'plain'
    for file_type, magic_bytes in magic_dict.items():
        if file_start.startswith(magic_bytes):
            compression_type = file_type
    return compression_type


def is_file_fasta(filename):
    """
    Returns whether or not the file appears to be a fasta file
    """
    try:
        with open(filename, 'rt') as fasta_file:
            try:
                line1, line2 = [next(fasta_file) for x in range(2)]
                if not line1 or not line2:
                    return False
                elif line1[0] != '>' or line2[0] not in {'A', 'C', 'G', 'T', 'a', 'c', 'g', 't'}:
                    return False
                else:
                    return True
            except Exception as ee:
                logger.debug(f'Could not read {filename}: {ee}')
                return False
    except Exception as e:
        logger.debug(f'Could not open {filename}: {e}')
        return False


# Validate and process zip file
def process_zip_file(file_dir, filename):
    if zipfile.is_zipfile(
            filename):  # https://docs.python.org/3/library/zipfile.html#zipfile.is_zipfile (Changed in version 3.1: Support for file and file-like objects.)
        zip_ref = zipfile.ZipFile(filename, 'r')
        if zip_ref.testzip() is not None:
            zip_ref.close()
            session.flash = "Invalid zip file."
            redirect(URL('kaptive'))
        else:
            try:
                zip_ref.extractall(file_dir)
            except:
                session.flash = ("An error occurred when trying to unzip file.\n"
                                 "Please double check the zip file and try again.")
                redirect(URL('kaptive'))
            finally:
                zip_ref.close()
    else:
        session.flash = "Invalid zip file."
        redirect(URL('kaptive'))


def process_gz_file(file_dir, filename):
    # First, unzip the file.
    try:
        subprocess.call(['gunzip', filename], cwd=(file_dir))
    except:
        session.flash = ("An error occurred when trying to gunzip the file\n"
                         "Please double check the file and try again.")
        redirect(URL('kaptive'))

    # Then we check to see if it's a tar. If so, untar it.
    unzipped_files = [f for f in os.listdir(file_dir) if os.path.isfile(os.path.join(file_dir, f))]
    for f in unzipped_files:
        try:
            with tarfile.open(os.path.join(file_dir, f), 'r') as potential_tar:
                tar_contents = potential_tar.getnames()
        except tarfile.ReadError:
            tar_contents = []
        if len(tar_contents) > 0:
            try:
                subprocess.call(['tar', 'xf', f], cwd=(file_dir))
            except:
                session.flash = ("An error occurred when trying to untar the file.\n"
                                 "Please double check the file and try again.")
                redirect(URL('kaptive'))


def read_json_from_file(f, json_lines: bool = False, n_tries: int = 10) -> OrderedDict | list[dict]:
    """
    Read from a JSON file without blocking.
    """
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
        ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    data = [] if json_lines else OrderedDict()
    while (n_try := 0) <= n_tries:  # TODO: Figure out this while loop logic, it feels broken
        try:
            with open(f, 'rt') as file:
                logger.debug(f'[{uuid}] Read from file: {f}')
                data = list(map(json.loads, file.readlines())) if json_lines else json.load(file, object_pairs_hook=OrderedDict)
        except ValueError as e:
            logger.error(f'[{uuid}] Error reading file {f}: {e}; Try again in 2s')
            time.sleep(2)
            n_try += 1
            if (n_try == n_tries) and (not f.endswith('.bak')):
                backup_file((f + '.bak'), f)
                time.sleep(2)
                data = read_json_from_file(f, json_lines)  # TODO: Understand why this function calls itself
                break
            continue
        except (IOError, OSError) as e:
            logger.error(f'[{uuid}] Error reading file {f}: {e}')
            if not f.endswith('.bak'):
                backup_file((f + '.bak'), f)
                time.sleep(2)
                data = read_json_from_file(f, json_lines)  # TODO: Understand why this function calls itself
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
        with open(f, 'wt+') as file:
            json.dump(json_string, file, indent=4)
            logger.debug(f'[{uuid}] Wrote to file {f}')
    except (IOError, OSError) as e:
        logger.error(f'[{uuid}] Error writing file {f}: {e}')


def create_table_file(filename: str = 'kaptive_results_table.txt') -> int:
    """
    Creates a Kaptive result TSV file with headers if it doesn't already exist.
    Returns the number of bytes written.
    """
    if os.path.isfile(table_path := os.path.join(upload_path, session.uuid, filename)):
        with open(table_path, 'rt') as existing_table:
            if existing_table.readline() == _KAPTIVE_HEADER:
                return 0
    with open(table_path, 'wt') as table:
        return table.write(_KAPTIVE_HEADER)


# Append a line to result table
def append_to_table(f, line):
    table = open(f, 'at')
    job_table_lock.acquire()
    # lock_file(table)
    table.write('\t'.join(line))
    table.write('\n')
    # unlock_file(table)
    job_table_lock.release()


def build_meta_json(uuid, job_name, fasta_files: list[str], reference, submit_time):
    meta_dict = OrderedDict({
        'Token': uuid,
        'Job Name': job_name,
        'Assembly File': ', '.join(fasta_files),
        'No of Assembly File': len(fasta_files),
        'Reference': reference,
        'Start Time': submit_time
    })
    meta_dict_file = os.path.join(upload_path, uuid, 'meta.json')
    save_json_to_file(meta_dict_file, meta_dict)
    logger.debug(f'[{uuid}] Metadata file created.')


def build_job_dict(uuid: str, reference: str, submit_time: str, fasta_files: list[str], upload_path: str):
    job_dict = OrderedDict({
        'Token': uuid,
        'Reference database': reference,
        'Fasta files': fasta_files,
        'Start time': submit_time,
        'Total jobs': len(fasta_files),
        'Jobs pending': len(fasta_files),
        'Jobs running': 0,
        'Jobs succeeded': 0,
        'Jobs failed': 0,
        'Last job submitted': None,
        'Job list': [OrderedDict({
            'Fasta file': f, 'Job status': 0, 'Job seq': n, 'Standard out': '', 'Standard error': '', 'Start time': '',
            'Finish time': ''}) for n, f in enumerate(fasta_files)]
    })
    job_file_path = os.path.join(upload_path, uuid, 'job_list.json')
    save_json_to_file(job_file_path, job_dict)
    logger.debug(f'[{uuid}] Wrote job list to file: {job_file_path}')


def upload_file(file, filename=None, path=None):
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
            shutil.copyfile(src, dst)
            unlock_file(file)
        logger.debug(f'[{uuid}] File backed up: {dst}')
    except (IOError, OSError) as e:
        logger.error(f'[{uuid}] Error backing up file {src}: {e}')
