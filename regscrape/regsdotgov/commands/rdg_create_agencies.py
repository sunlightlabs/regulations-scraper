GEVENT = False

def run():
    from regs_models import Agency
    import subprocess, re, urllib2

    BAD_SPACES = re.compile("(\xc2\xa0|\r)")
    AGENCY_LINE = re.compile(r"^[A-Z\s\.\,\&\-\'\(\)\/]*[A-Z]+[A-Z\s\(\)]*$")
    REGULAR_LINE = re.compile(r"^[A-Z]{2,}\s{3,}[A-Z]+.*$")
    AGENCY_ONLY_LINE = re.compile(r"^[A-Z]{2,}\s*$")
    DESCRIPTION_ONLY_LINE = re.compile(r"^\s{3,}[A-Z]+.*$")
    THREE_SPACES = re.compile("\s{3,}")
    SPACES = re.compile(r"\s+")
    AMPERSAND = re.compile(r"(?<=[A-Z])\&")
    
    new = 0
    
    print 'Fetching agencies...'
    agencies = {}

    ml_descs = []
    ml_agency = None

    participating = {}

    for file in ["Participating_Agencies.pdf", "Non_Participating_Agencies.pdf"]:
        data = urllib2.urlopen("http://www.regulations.gov/docs/%s" % file)
        pdftotext = subprocess.Popen(["pdftotext", "-layout", "-", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        text = pdftotext.communicate(data.read())
        
        contents = BAD_SPACES.sub(" ", text[0])
        
        agency_lines = [line for line in contents.split("\n") if AGENCY_LINE.match(line)]
        
        for line in agency_lines:
            if REGULAR_LINE.match(line):
                split = THREE_SPACES.split(line, maxsplit=1)
                a_name = split[0].strip()
                a_desc = split[1].strip()

                agencies[a_name] = a_desc
                participating[a_name] = "Non" not in file
            elif AGENCY_ONLY_LINE.match(line):
                ml_agency = line.strip()
            elif DESCRIPTION_ONLY_LINE.match(line):
                ml_descs.append(line.strip())
                if ml_agency:
                    agencies[ml_agency] = " ".join(ml_descs)
                    participating[ml_agency] = "Non" not in file
                    ml_agency = None
                    ml_descs = []
            else:
                print "Broken line:", line

    # hard-coded SIGAR, because it's messed up in the PDF
    agencies["SIGAR"] = "SPECIAL INSPECTOR GENERAL FOR AFGHANISTAN RECONSTRUCTION"
    participating["SIGAR"] = False

    print 'Saving agencies...'

    stop_words = ['the', 'and', 'of', 'on', 'in', 'for']
    for agency, name in agencies.items():
        # fix ampersand weirdness
        name = AMPERSAND.sub(" & ", name)

        # fix spacing and capitalization
        name_parts = SPACES.split(name)
        capitalized_parts = [name_parts[0].title()] + [word.title() if word.lower() not in stop_words else word.lower() for word in name_parts[1:]]
        name = ' '.join(capitalized_parts)

        new += Agency.objects(id=agency).update(
            set__name=name,
            set__rdg_participating=participating[agency],

            upsert=True,
            safe_update=True
        )
    
    print 'Iterated over %s agencies.' % (len(agencies))
    
    return {'total': len(agencies), 'new': new}
