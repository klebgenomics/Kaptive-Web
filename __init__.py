import configparser
import os
import json
import multiprocessing
import sys
from datetime import datetime
from collections import OrderedDict

Config = configparser.ConfigParser()
Config.read('applications/kaptive_web/settings.ini')
queue_path = Config.get('Path', 'queue_path')
upload_path = Config.get('Path', 'upload_path')


# Save JSON Object to a file
def save_json_to_file(f, json_string):
    try:
        with open(f, 'wt+') as file:
            json.dump(json_string, file, indent=4)
            print("Wrote to file: " + f, file=sys.stderr)
    except (IOError, OSError) as e:
        print("Error writing file: " + f + "; " + str(e), file=sys.stderr)


# Read JSON Object from a file
def read_json_from_file(f):
    data = OrderedDict()
    try:
        with open(f, 'r') as file:
            data = json.load(file, object_pairs_hook=OrderedDict)
    except ValueError as e:
        print("Error parsing file " + f + ": " + str(e), file=sys.stderr)
        if not f.endswith('.bak'):
            os.remove(f)
            data = read_json_from_file((f + '.bak'))
            save_json_to_file(f, data)
    except (IOError, OSError) as e:
        print("Error reading file " + f + ": " + str(e), file=sys.stderr)
        if not f.endswith('.bak'):
            os.remove(f)
            data = read_json_from_file((f + '.bak'))
            save_json_to_file(f, data)
    return data


job_queue_path = os.path.join(queue_path, 'queue')
available_worker = multiprocessing.cpu_count() - 1
if os.path.exists(
        job_queue_path):  # and os.path.getsize(job_queue_path) > 2: catches empty queue (i.e. if file contains {})
    data = OrderedDict()  # read_json_from_file returns an OrderedDict even if empty, no need to declare here.
    # Put the jobs in processing back to the job queue
    data = read_json_from_file(job_queue_path)
    job_queue = data['Job queue']
    processing_queue = data['Processing queue']
    data['Job queue'] = data['Processing queue'] + data['Job queue']
    data['Processing queue'] = []
    data['Last update (queue)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
    data['Total worker'] = available_worker
    data['Available worker'] = available_worker
    data['Last update (worker)'] = str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
    save_json_to_file(job_queue_path, data)
    print("Queue file updated.", file=sys.stderr)

    for i in data['Job queue']:
        job_list_path = os.path.join(upload_path, i[0], 'job_list.json')
        job_data = read_json_from_file(job_list_path)

        # Check and fix the job list
        for j in job_data['Job list']:
            if (j['Job status']) == 1 and (j['Finish time'] == ''):
                j['Job status'] = 0
                j['Standard out'] = ''
                j['Standard error'] = ''
                job_data['Jobs pending'] += 1
                job_data['Jobs running'] -= 1
                job_name = j['Fasta file']
                job_seq = j['Job seq']
                save_json_to_file(job_list_path, job_data)
                print("Fixed corrupted data in job list.", file=sys.stderr)
                break
else:
    data = OrderedDict({
        'Job queue': [],
        'Processing queue': [],
        'Last update (queue)': str(datetime.now().strftime('%d %b %Y %H:%M:%S')),
        'Total worker': available_worker,
        'Available worker': available_worker,
        'Last update (worker)': str(datetime.now().strftime('%d %b %Y %H:%M:%S'))
    })
    save_json_to_file(job_queue_path, data)
    print("Queue file created.", file=sys.stderr)
