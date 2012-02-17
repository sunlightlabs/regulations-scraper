#!/usr/bin/env python

from bson.code import Code
from pymongo.objectid import ObjectId
from pymongo.binary import Binary
from pymongo.errors import OperationFailure, InvalidDocument
import subprocess, os, urlparse, json
import gevsubprocess
from gevent import Timeout
from regscrape_lib.util import get_db
from exceptions import DecodeFailed, ChildTimeout
import os
import re
import cStringIO
import time
import itertools
import sys
import regscrape_lib
import operator
import zlib

def find_views(**params):
    db = get_db()
    
    # allow for using a pre-filter to speed up execution
    kwargs = {}
    query = {}
    if 'query' in params:
        query = params['query']
        del params['query']
    
    # create the actual map function
    conditions = dict([('views.%s' % item[0], item[1]) for item in params.items()])
    conditions.update(query)
    
    results = itertools.chain.from_iterable(
        itertools.imap(
            lambda doc: [{'view': view, 'doc': doc['_id']} for view in doc['views'] if all(item[0] in view and view[item[0]] == item[1] for item in params.items())],
            db.docs.find(conditions)
        )
    )
    
    return results

def find_attachment_views(**params):
    db = get_db()

    # allow for using a pre-filter to speed up execution
    kwargs = {}
    query = {}
    if 'query' in params:
        query = params['query']
        del params['query']

    # create the actual map function
    conditions = dict([('attachments.views.%s' % item[0], item[1]) for item in params.items()])
    conditions.update(query)

    results = itertools.chain.from_iterable(
        itertools.imap(
            lambda doc: reduce(operator.add, [
                [
                    {'view': view, 'doc': doc['_id'], 'attachment': attachment['object_id']}
                    for view in attachment['views'] if all(item[0] in view and view[item[0]] == item[1] for item in params.items())
                ] for attachment in doc['attachments']
            ] if 'attachments' in doc else [], []),
            db.docs.find(conditions)
        )
    )

    return results

def update_view(doc, view, try_compression=True):
    oid = ObjectId(doc)
    
    # use db object from thread pool
    db = get_db()
    
    # can't figure out a way to do this atomically because of bug SERVER-1050
    # remove the old version of the view
    db.docs.update({
        '_id': oid
    },
    {
        '$pull': {"views": {"url": view['url']}}
    }, safe=True)

    # add the new one back
    try:
        db.docs.update({
            '_id': oid
        },
        {
            '$push': {"views": view}
        }, safe=True)
    except (OperationFailure, InvalidDocument):
        # apparently whatever we changed made the document too big
        # so as long as we haven't already tried, let's first compress
        # all the other views on the document
        if try_compression:
            compress_all(doc)

            # then, since saving this view failed, before, add back a compressed version
            db.docs.update({
                '_id': oid
            },
            {
                '$push': {"views": compress_view(view)}
            }, safe=True)
        else:
            raise
    
    # return it to the pool
    del db

def update_attachment_view(doc, attachment, view, try_compression=True):
    oid = ObjectId(doc)
    
    db = get_db()
    
    # two-stage push/pull as above
    db.docs.update({
        '_id': oid,
        'attachments.object_id': attachment
    },
    {
        '$pull': {'attachments.$.views': {'url': view['url']}}
    }, safe=True)

    try:
        db.docs.update({
            '_id': oid,
            'attachments.object_id': attachment
        },
        {
            '$push': {'attachments.$.views': view}
        }, safe=True)
    except (OperationFailure, InvalidDocument):
        # apparently whatever we changed made the document too big
        # same strategy as above
        if try_compression:
            compress_all(doc)

            # then, since saving this view failed, before, add back a compressed version
            db.docs.update({
                '_id': oid,
                'attachments.object_id': attachment
            },
            {
                '$push': {'attachments.$.views': compress_view(view)}
            }, safe=True)
        else:
            raise
    
    del db

def compress_all(doc):
    # grab the original document and run compression on everything that isn't compressed
    # but save via pull/push, since there are other workers potentially making simultaneous saves
    oid = ObjectId(doc)

    db = get_db()

    full_doc = db.docs.find({'_id': oid})[0]

    # regular views first
    for view in full_doc['views']:
        if not view_is_compressed(view):
            update_view(doc, compress_view(view), try_compression=False)
    
    # then attachments
    for attachment in full_doc.get('attachments', []):
        for view in attachment['views']:
            if not view_is_compressed(view):
                update_attachment_view(doc, attachment['object_id'], compress_view(view), try_compression=False)

def view_is_compressed(view):
    if 'text' not in view or not view['text']:
        # the only compression strategy we have operates on the text, so if there's no text, it's as compressed
        # as it's going to get
        return True
    elif type(view['text']) == dict and 'compressed' in view['text']:
        # already compressed
        return True
    else:
        return False

def compress_view(view):
    text = view.get('text', '')
    if type(text) == unicode:
        text = text.encode('utf-8')
    
    if type(text) == str:
        text = {'compressed': Binary(zlib.compress(text))}
    
    out = view.copy()
    out['text'] = text

    return out


# the following is from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    import os
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

# the following is from http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
import unicodedata, re

control_chars = ''.join(map(unichr, range(0,10) + range(11,13) + range(14,32) + range(127,160)))

control_char_re = re.compile('[%s]' % re.escape(control_chars))

def remove_control_chars(s):
    return control_char_re.sub('', s)

# decoders
def binary_decoder(binary, error=None, append=[]):
    if not type(binary) == list:
        binary = [binary]
    def decoder(filename):
        interpreter = gevsubprocess.GPopen(binary + [filename] + append, stdin=gevsubprocess.PIPE, stdout=gevsubprocess.PIPE, stderr=gevsubprocess.STDOUT)
        
        timeout = Timeout(getattr(settings, 'EXTRACTION_TIMEOUT', 120), ChildTimeout)
        timeout.start()
        try:
            output, run_error = interpreter.communicate('')
            timeout.cancel()
        except ChildTimeout:
            interpreter.kill()
            raise
        
        if not output.strip() or (error and error in output):
            raise DecodeFailed()
        else:
            return output
    
    decoder.__str__ = lambda: binary[0]
    
    return decoder

def script_decoder(script, error=None):
    script_path = os.path.join(os.path.dirname(os.path.abspath(regscrape_lib.__file__)), 'scripts', script)
    
    decoder = binary_decoder([sys.executable, script_path], error=error)
    decoder.__str__ = lambda: script
    
    return decoder

def ocr_scrub(text):
    lines = re.split(r'\n', text)
    garbage = re.compile(r'[^a-zA-Z\s]')
    
    def is_real_line(word):
        letter_length = len(garbage.sub('', word))
        return letter_length and len(word) and letter_length/float(len(word)) >= 0.5
    
    filtered_lines = [line.strip() for line in lines if line and is_real_line(line)]
    filtered_text = '\n'.join(filtered_lines)
    
    if len(filtered_text) / float(len(text)) < 0.5:
        raise DecodeFailed('This is does not appear to be text.')
    
    return filtered_text

def pdf_ocr(filename):
    basename = os.path.basename(filename).split('.')[0]
    working = '/tmp/%s' % basename
    if not os.path.exists(working):
        os.mkdir(working)
    os.chdir(working)
    
    def cleanup():
        if working and working != '/tmp/':
            os.chdir('..')
            subprocess.Popen(['rm', '-rf', working], stdout=subprocess.PIPE).communicate()
    
    extractor = subprocess.Popen(['pdfimages', filename, basename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    extractor_output, extractor_error = extractor.communicate()
    if extractor_error:
        cleanup()
        raise DecodeFailed("Failed to extract image data from PDF.")
    
    pnm_match = re.compile(r"[a-zA-Z0-9]+-[0-9]+\.p.m")
    pnms = [file for file in os.listdir(working) if pnm_match.match(file)]
    if not pnms:
        cleanup()
        raise DecodeFailed("No images found in PDF.")
    
    converter = subprocess.Popen(['gm', 'mogrify', '-format', 'tiff', '-type', 'Grayscale'] + pnms, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    converter_output, converter_error = converter.communicate()
    if converter_error:
        cleanup()
        raise DecodeFailed("Failed to convert images to tiff.")
    
    tiff_match = re.compile(r"[a-zA-Z0-9]+-[0-9]+\.tiff")
    tiffs = [file for file in os.listdir(working) if tiff_match.match(file)]
    if not tiffs:
        cleanup()
        raise DecodeFailed("Converted tiffs not found.")
    
    out = cStringIO.StringIO()
    for tiff in tiffs:
        tiff_base = tiff.split('.')[0]
        ocr = subprocess.Popen(['tesseract', tiff, tiff_base], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ocr_output, ocr_error = ocr.communicate()
        
    txt_match = re.compile(r"[a-zA-Z0-9]+-[0-9]+\.txt")
    txts = [file for file in os.listdir(working) if txt_match.match(file)]
    if not txts:
        cleanup()
        raise DecodeFailed("OCR failed to find any text.")
    
    for txt in txts:
        ocr_file = open(txt, 'r')
        out.write(ocr_file.read())
        out.write('\n')
    
    return ocr_scrub(out.getvalue())
pdf_ocr.__str__ = lambda: 'tesseract'
pdf_ocr.ocr = True
