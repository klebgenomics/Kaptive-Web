from fcntl import flock, LOCK_EX, LOCK_UN, LOCK_NB
import errno


def lock_file(file):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    while True:
        try:
            flock(file, LOCK_EX | LOCK_NB)
            logger.debug('[' + uuid + '] ' + 'File ' + file.name + ' locked.')
            break
            return True
        except IOError as e:
            if e.errno != errno.EAGAIN:
                logger.error('[' + uuid + '] ' + 'Error in locking file: ' + file.name)
                raise
                return False
            else:
                time.sleep(0.2)


def unlock_file(file):
    if (('session.uuid' not in locals()) and ('session.uuid' not in globals()) and
            ('session.uuid' not in vars())) or session.uuid is None:
        uuid = 'No Session ID'
    else:
        uuid = session.uuid

    flock(file, LOCK_UN)
    logger.debug('[' + uuid + '] ' + 'File ' + file.name + ' unlocked.')
    return True
