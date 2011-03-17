# initial port of a Javascript CSS-to-XPath converter found here:
#  http://code.google.com/p/css2xpath/source/browse/trunk/src/css2xpath.js
# originally written by Andrea Giammarchi
# some tweaks have been applied, and not all properties have been ported

import re

replacements = [
    # add @ for attribs
    (re.compile("\[([^\]~\$\*\^\|\!]+)(=[^\]]+)?\]"), "[@\\1\\2]"),
    # multiple queries
    (re.compile("\s*,\s*"), "|"),
    # , + ~ >
    (re.compile("\s*(\+|~|>)\s*"), "\\1"),
    #* ~ + >
    (re.compile("([a-zA-Z0-9\_\-\*\.#])~([a-zA-Z0-9\_\-\*\.#])"), "\\1/following-sibling::\\2"),
    (re.compile("([a-zA-Z0-9\_\-\*\.#])\+([a-zA-Z0-9\_\-\*\.#])"), "\\1/following-sibling::*[1]/self::\\2"),
    (re.compile("([a-zA-Z0-9\_\-\*\.#])>([a-zA-Z0-9\_\-\*\.#])"), "\\1/\\2"),
    # all unescaped stuff escaped
    (re.compile("\[([^=]+)=([^'|\"][^\]]*)\]"), "[\\1='\\2']"),
    # all descendant or self to #
    (re.compile("(^|[^a-zA-Z0-9\_\-\*])(#|\.)([a-zA-Z0-9\_\-]+)"), "\\1*\\2\\3"),
    (re.compile("([\>\+\|\~\,\s])([a-zA-Z\*]+)"), '\\1//\\2'),
    (re.compile("\s+\/\/"), '//'),
    # :first-child
    (re.compile("([a-zA-Z0-9\_\-\*\.#]+):first-child"), "*[1]/self::\\1"),
    # :last-child
    (re.compile("([a-zA-Z0-9\_\-\*\.#]+):last-child"), "\\1[not(following-sibling::*)]"),
    # :only-child
    (re.compile("([a-zA-Z0-9\_\-\*\.#]+):only-child"), "*[last()=1]/self::\\1"),
    # :empty
    (re.compile("([a-zA-Z0-9\_\-\*\.#]+):empty"), "\\1[not(*) and not(normalize-space())]"),
    # :not
#        (re.compile("([a-zA-Z0-9\_\-\*]+):not\(([^\)]*)\)"), function(s, a, b){return a.concat("[not(", css2xpath(b).replace(/^[^\[]+\[([^\]]*)\].*$"), "\\1"), ")]");}),
    # :nth-child
#        (re.compile("([a-zA-Z0-9\_\-\*]+):nth-child\(([^\)]*)\)"), function(s, a, b){
#        switch(b){
#            case    "n":
#                return a;
#            case    "even":
#                return "*[position() mod 2=0 and position()>=0]/self::" + a;
#            case    "odd":
#                return a + "[(count(preceding-sibling::*) + 1) mod 2=1]";
#            default:
#                b = (b || "0").replace(/^([0-9]*)n.*?([0-9]*)$/, "\\1+\\2").split("+");
#                b[1] = b[1] || "0";
#                return "*[(position()-".concat(b[1], ") mod ", b[0], "=0 and position()>=", b[1], "]/self::", a);
#            }
#        }),
    # :contains(selectors)
#        (re.compile(":contains\(([^\)]*)\)"), function(s, a){
#            # return "[contains(css:lower-case(string(.)),'" + a.toLowerCase() + "')]" # it does not work in firefox 3*/
#            return "[contains(string(.),'" + a + "')]";
#        }),
    # |= attrib
    (re.compile("\[([a-zA-Z0-9\_\-]+)\|=([^\]]+)\]"), "[@\\1=\\2 or starts-with(@\\1,concat(\\2,'-'))]"),
    # *= attrib
    (re.compile("\[([a-zA-Z0-9\_\-]+)\*=([^\]]+)\]"), "[contains(@\\1,\\2)]"),
    # ~= attrib
    (re.compile("\[([a-zA-Z0-9\_\-]+)~=([^\]]+)\]"), "[contains(concat(' ',normalize-space(@\\1),' '),concat(' ',\\2,' '))]"),
    # ^= attrib
    (re.compile("\[([a-zA-Z0-9\_\-]+)\^=([^\]]+)\]"), "[starts-with(@\\1,\\2)]"),
    # $= attrib
#        (re.compile("\[([a-zA-Z0-9\_\-]+)\$=([^\]]+)\]"), function(s, a, b){return "[substring(@".concat(a, ",string-length(@", a, ")-", b.length - 3, ")=", b, "]");}),
    # != attrib
    (re.compile("\[([a-zA-Z0-9\_\-]+)\!=([^\]]+)\]"), "[not(@\\1) or @\\1!=\\2]"),
    # ids and classes
    (re.compile("#([a-zA-Z0-9\_\-]+)"), "[@id='\\1']"),
    (re.compile("\.([a-zA-Z0-9\_\-]+)"), "[contains(concat(' ',normalize-space(@class),' '),' \\1 ')]"),
    # normalize multiple filters
    (re.compile("\]\[([^\]]+)"), " and (\\1)"),
]

def css2xpath(s):
    for pair in replacements:
        s = pair[0].sub(pair[1], s)
    return "//" + s