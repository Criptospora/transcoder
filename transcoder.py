#! Python3
# This script transcodes files passed as arguments into OPUS
# KNOWN BUGS: The parent directory path must NOT contain FLAC or WAV in it.
# Also, if 

import os, sys, logging, multiprocessing, time, shutil, re

logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
logging.disable(logging.DEBUG)
#logging.disable(logging.CRITICAL)

def renamedirs(directory, formatRegex, tgtformat): # Renames folders accordingly
    for path, subfolders, files in os.walk(directory):
        newpath = re.sub(r'\s*(\d\d-\d\d\d?)\s*', '', path) # Deletes bitdepth and sample rate (POSSIBLE BUGS if album or band contain numbers!)
        newpath = formatRegex.sub(tgtformat, newpath) # Changes format name
        if newpath != path:
            logging.debug('Moving %s to %s' % (path, newpath))
            shutil.move(path, newpath) # Renames. BUG: If parent path has FLAC in it, it will mess up

def cleanup(directory): # Deletes empty folders and renames the others
    for path, subfolders, files in os.walk(directory, topdown=False):
        if subfolders == [] and files == []: #folder is empty
            os.rmdir(path)
            logging.debug(path + ' was deleted')
                

# Argument parser
def get_filequeue():
    filequeue = []
    
    for i in range(1, len(sys.argv)):
        this_argv = sys.argv[i]
        if os.path.isfile(this_argv):
            if this_argv.endswith('.flac') or this_argv.endswith('.wav'):
                filequeue.append(this_argv)
                logging.debug(this_argv + ' added to filequeue')
        elif os.path.isdir(this_argv):
            parentdir = os.path.dirname(this_argv)
            basedirname = os.path.basename(this_argv)
            workingdir = get_targetdir(parentdir)
            # Copy directory tree
            logging.info('Creating the folder tree structure...')
            shutil.copytree(this_argv, os.path.join(workingdir, basedirname), copy_function=copydir)
            # Walk the directory to find flac files and append them to filequeue
            for path, dirs, files in os.walk(this_argv):
                logging.debug('walking in: %s' % (path))
                for file in files:
                    if file.endswith('.flac') or file.endswith('.wav'):
                        filequeue.append((os.path.join(path, file), workingdir)) #appends tuple: (filepath, targetdir)
                        logging.debug(os.path.join(path, file) + ' will be transcoded to: ' + workingdir)
        
    return filequeue # list of tuples

# Target directory generator
# TODO: Add customization
def get_targetdir(dirname):
    path = os.path.join(dirname, 'transcoded')
    return path


# OPUS encoding function
def opusenc(sourcefilepath, workingdir):
    logging.debug('sourcefilepath is: ' + sourcefilepath)
    
    # Parse encode settings
    # TODO: Increase customization
    sourcefilename = os.path.basename(sourcefilepath)    
    targetfilename = os.path.splitext(sourcefilename)[0] + '.opus'

    sourcereldir = os.path.dirname(os.path.relpath(sourcefilepath))
    logging.debug('sourcereldir is: ' + sourcereldir)
    
    targetfilepath = os.path.join(workingdir, sourcereldir, targetfilename)
    logging.debug('targetfilepath is: ' + targetfilepath)
    os.makedirs(os.path.dirname(targetfilepath), exist_ok=True) #skips if it exists
            
    encodesettings = 'opusenc --quiet --bitrate 128 "%s" "%s"' % (sourcefilepath, targetfilepath)

    # Encode file with Opus to the destination
    logging.info('Transcoding: %s' % sourcefilepath)
    os.system(encodesettings)
    logging.debug('Transcode finished: %s' % targetfilepath)


# Blank copy function to pass to shutil.copytree.
# This way copytree just copies the tree structure, no files in them
def copydir(src, dst, *, follow_symlinks=True):
    return None

# Main process
if __name__ == '__main__':
    logging.info('Getting files to transcode...')
    files = get_filequeue()
    
    # iterate the queue and encode each file
    logging.info('Passing orders to the transcoding workers...')
    pool = multiprocessing.Pool() # create a pool of workers
    t0 = time.perf_counter()
    pool.starmap(opusenc, files) # iterate 'files' and use the pool to encode them
    pool.close() # closes the pool once all tasks finish (required for .join)
    pool.join() # waits for the workers to finish before continuing
    t1 = time.perf_counter()
    logging.info('Transcoding took %f seconds', t1-t0)

    logging.info('Cleaning up...')
    formatRegex = re.compile(r'FLAC|flac|Flac|WAV|wav|Wav')
    dirtyfolders = []
    for f, tgtdir in files: 
        if tgtdir not in dirtyfolders:
            dirtyfolders.append(tgtdir)
    for dirtyfolder in dirtyfolders:
        #TODO: potential for optimization. Calling them both walks the folder twice
        cleanup(dirtyfolder)
        renamedirs(dirtyfolder, formatRegex, 'Opus 128')
    logging.info('DONE!')
