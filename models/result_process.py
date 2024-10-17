def write_to_result_json(job_result_path, result_path, seq_no, retry=0):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and (
            'session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    job_json_lock.acquire()
    try:
        with open(result_path, 'at+') as file, open(job_result_path, 'rt') as result_json:
            file.write(result_json.readline())
            job_json_lock.release()
            # unlock_file(file)
            logger.debug(f'[{uuid}] [{seq_no}] Wrote to: {result_path}')
    except ValueError as e:
        if retry <= 0:
            logger.error(f'[{uuid}] [{seq_no}] Error reading {file.name}: {e}\nTry again in 2 seconds')
            time.sleep(2)
            job_json_lock.release()
            retry += 1
            write_to_result_json(job_result_path, result_path, seq_no, retry)
    except (IOError, OSError) as e:
        if retry <= 10:
            logger.error(f'[{uuid}] [{seq_no}] Error accessing {file.name}: {e}')
            backup_file((result_path + '.bak'), result_path)
            job_json_lock.release()
            time.sleep(2)
            retry += 1
            write_to_result_json(job_result_path, result_path, seq_no, retry)
