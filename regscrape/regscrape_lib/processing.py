#!/usr/bin/env python

from bson.code import Code
from pymongo.objectid import ObjectId
import subprocess, os, urlparse, json
from regscrape_lib.util import get_db
from exceptions import DecodeFailed
import os
import re
import cStringIO

MAP = """
function() {
    if (this.Views) {
        for (var i = 0; i < this.Views.length; i++) {
            if (%s) {
                emit(this.Views[i].URL, {doc: this._id, view: this.Views[i]})
            }
        }
    }
}
"""

REDUCE = """
function(key, values) {
    return values[0];
}
"""

DB = get_db()

def find_views(**params):
    rule = " && ".join(['this.Views[i].%s == %s' % (item[0], json.dumps(item[1])) for item in params.items()])
    mapfunc = MAP % rule
    
    results = DB.docs.inline_map_reduce(Code(mapfunc), Code(REDUCE), full_response=True)
    
    return DB[results['result']]

def update_view(id, view):
    oid = ObjectId(id)
    
    # can't figure out a way to do this atomically because of bug SERVER-1050
    DB.docs.update({
        '_id': oid
    },
    {
        '$pull': { "Views": {"URL": view['URL']}}
    }, safe=True)
    DB.docs.update({
        '_id': oid
    },
    {
        '$push': { "Views": view}
    }, safe=True)

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
def binary_decoder(binary, error=None):
    def decoder(filename):
        interpreter = subprocess.Popen([binary, filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, run_error = interpreter.communicate()
        
        if not output.strip() or (error and error in output):
            raise DecodeFailed()
        else:
            return output
    
    decoder.__str__ = lambda: binary
    
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