import os
import csv

def write_to_result_table(result_path, final_result_path, job_uuid, seq_no):
    job_table_lock.acquire()
    with open(result_path) as f:
        no_of_lines = sum(1 for _ in f)
    if no_of_lines == 2:
        raw_result = list(csv.reader(open(result_path, 'rb'), delimiter='\t'))
        line = raw_result[1]
        backup_file(final_result_path, (final_result_path + '.bak'))
        with open(final_result_path, 'at') as table:
            # lock_file(table)
            table.write('\t'.join(line))
            table.write('\n')
            job_table_lock.release()
            # unlock_file(table)
            logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' + 'Wrote to TXT result file.')
    else:
        logger.debug('[' + job_uuid + '] [' + str(seq_no) + '] ' + 'Empty TXT result file.')


def write_to_result_json(job_result_path, result_path, seq_no, retry = 0):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and ('session.uuid' not in vars())) or session.uuid == None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    job_result_data = {}
    final_result_data = {}

    job_result_data = read_json_from_file(job_result_path)

    if os.path.exists(result_path):
        job_json_lock.acquire()
        try:
            with open(result_path, 'r+') as file:
                # lock_file(file)
                final_result_data = json.load(file, object_pairs_hook=OrderedDict)
                logger.debug('[' + uuid + '] [' + str(seq_no) + '] ' + 'Read from file: ' + result_path)
                final_result_data.append(job_result_data[0])
                final_result_data = sorted(final_result_data, key=lambda k: k['Assembly name'])
                file.seek(0)
                json.dump(final_result_data, file, indent=4)
                file.truncate()
                job_json_lock.release()
                # unlock_file(file)
                logger.debug('[' + uuid + '] [' + str(seq_no) + '] ' + 'Wrote to file: ' + result_path)
        except ValueError as e:
            if retry <= 0:
                logger.error('[' + uuid + '] [' + str(seq_no) + '] ' + 'Error reading file ' + file.name + ': ' + str(e) + ' Try again in 2 seconds')
                time.sleep(2)
                job_json_lock.release()
                retry = retry + 1
                write_to_result_json(job_result_path, result_path, seq_no, retry)
        except (IOError, OSError) as e:
            if retry <= 10:
                logger.error('[' + uuid + '] [' + str(seq_no) + '] ' + 'Error accessing file ' + file.name + ': ' + str(e))
                backup_file((result_path + '.bak'), result_path)
                job_json_lock.release()
                time.sleep(2)
                retry = retry + 1
                write_to_result_json(job_result_path, result_path, seq_no, retry)
    else:
        job_json_lock.acquire()
        try:
            with open(result_path, 'wb') as result_file:
                json.dump(job_result_data, result_file, indent=4)
                job_json_lock.release()
                # unlock_file(result_file)
                logger.debug('[' + uuid + '] [' + str(seq_no) + '] ' + 'Wrote to file: ' + result_path)
        except (IOError, OSError) as e:
            logger.error('[' + uuid + '] [' + str(seq_no) + '] ' + 'Error writing file: \n' + result_path + '; ' + str(e))
