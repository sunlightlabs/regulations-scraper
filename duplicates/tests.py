
import unittest

from ngrams import Sequencer, NGramSpace, overlap, jaccard
from clustering import Clustering, SymmetricMatrix
from db import extract_comment


# for use in interactive tests
test_docs = [
    "Penguins swim in the waters of antarctica.",
    "In antarctica, penguins swim in the waters.",
    "The waters where penguins swim are in antarctica.",
    
    "Bears eat honey in the forest.",
    "The forest where bears eat has honey.",
    "Honey is eaten bears in the forest.",
    
    "Sea gulls fly on the coast.",
    "Sea gulls fly over the water.",
]



class TestSymmetricMatrix(unittest.TestCase):
    
    def test_basic(self):
        m = SymmetricMatrix(5)
        
        self.assertEqual(5, len(m))
        
        self.assertEqual(0, m[2,3])
        
        m[2,3] = 2.3
        
        self.assertEqual(2.3, m[2, 3])
        self.assertEqual(2.3, m[3, 2])
    
    def test_translate(self):
        m = SymmetricMatrix(5)
        
        for i in range(0, 5):
            for j in range(0, i + 1):
                m[i, j] = i + j * 0.1
        
        self.assertEqual(2.1, m[1,2])
        self.assertEqual(2.1, m[2,1])
        
        s = m.submatrix([0, 3, 4])
        
        self.assertEqual(3, len(s))
        
        self.assertEqual(0.0, s[0,0])
        self.assertEqual(3.3, s[1,1])
        self.assertEqual(4.4, s[2,2])
        
        self.assertEqual(4.3, s[1, 2])
        self.assertEqual(4.3, s[2, 1])        
        


class TestSequencer(unittest.TestCase):
    
    def test_basic(self):
        s = Sequencer()
        a = s.id('a')
        b = s.id('b')
        c = s.id('c')
        
        self.assertEqual(1, a)
        self.assertEqual(2, b)
        self.assertEqual(3, c)
        self.assertEqual(a, s.id('a'))
        self.assertEqual(b, s.id('b'))
        self.assertEqual(c, s.id('c'))
        
    def test_ngram(self):
        s = Sequencer()
        
        abc = s.id(('a', 'b', 'c'))
        bcd = s.id(('b', 'c', 'd'))
        
        self.assertEqual(1, abc)
        self.assertEqual(2, bcd)
        self.assertEqual(abc, s.id(('a', 'b', 'c')))
        self.assertEqual(bcd, s.id(('b', 'c', 'd')))


class TestNGramSpace(unittest.TestCase):
    
    def test_unigram(self):
        unigrams = NGramSpace(1)
        
        x = unigrams.parse('This is a sentence')
        y = unigrams.parse('This is another sentence')
        
        self.assertEqual([1, 2, 3, 4], x)
        self.assertEqual([1, 2, 4, 5], y)
        
        self.assertEqual(3, overlap(x, y))
        self.assertEqual(3, overlap(y, x))
        
        self.assertEqual(3.0/5.0, jaccard(x, y))
        self.assertEqual(3.0/5.0, jaccard(y, x))
   
    def test_bigram(self):
        unigrams = NGramSpace(2)

        x = unigrams.parse('This is a sentence')
        y = unigrams.parse('This is another sentence')

        self.assertEqual([1, 2, 3], x)
        self.assertEqual([1, 4, 5], y)

        self.assertEqual(1, overlap(x, y))
        self.assertEqual(1, overlap(y, x))
        
        self.assertEqual(1.0/5.0, jaccard(x, y))
        self.assertEqual(1.0/5.0, jaccard(y, x))

    def test_trigram(self):
        unigrams = NGramSpace(3)

        x = unigrams.parse('This is a sentence')
        y = unigrams.parse('This is another sentence')

        self.assertEqual([1, 2], x)
        self.assertEqual([3, 4], y)

        self.assertEqual(0, overlap(x, y))
        self.assertEqual(0, overlap(y, x))
        
        self.assertEqual(0, jaccard(x, y))
        self.assertEqual(0, jaccard(y, x))     

class TestClustering(unittest.TestCase):
    
    def test_distance(self):
        raw_docs = ['a b c', 'b c d', 'd e f']
        ngrams = NGramSpace(1)
        docs = [ngrams.parse(raw) for raw in raw_docs]
        
        c = Clustering(docs)
        
        self.assertEqual(0, c.distance[0, 0])
        self.assertEqual(0.5, c.distance[1, 0])
        self.assertEqual(0, c.distance[1, 1])
        self.assertEqual(1.0, c.distance[2, 0])
        self.assertEqual(0.8, c.distance[2, 1])
        self.assertEqual(0, c.distance[2, 2])
        
    def test_clustering(self):
        raw_docs = ['a b c', 'b c d', 'd e f']
        ngrams = NGramSpace(1)
        docs = [ngrams.parse(raw) for raw in raw_docs]
        
        c = Clustering(docs)
        
        self.assertEqual((1, 0), c.min_link())
        
        c.merge(1, 0)
        self.assertEqual([1, 1, 2], c.assignments)
        
        self.assertEqual((2, 1), c.min_link())

        c.merge(2, 0)
        self.assertEqual([2, 2, 2], c.assignments)
        
    def test_nonseeded_clustering(self):
        ngrams = NGramSpace(1)
        docs = [ngrams.parse(raw) for raw in test_docs]
        c = Clustering(docs)
        
        self.assertEqual((1, 0), c.min_link())
        c.merge(1, 0)
        self.assertEqual((2, 1), c.min_link())
        c.merge(2, 1)
        self.assertTrue(c.min_link() in [(4,3), (5,3)])
        c.merge(3,4)
        c.merge(3, 5)
        self.assertEqual((7,6), c.min_link())
                
    def test_seeded_clustering(self):
        ngrams = NGramSpace(1)
        docs = [ngrams.parse(raw) for raw in test_docs]
        c = Clustering(docs)
        
        self.assertEqual((0, 1), c.min_link(0))
        c.merge(0, 1)
        self.assertEqual((0, 2), c.min_link(0))
        c.merge(0, 2)
        self.assertEqual((0, 3), c.min_link(0))
        
        self.assertTrue(c.min_link(3) in [(3, 4), (3, 5)])
        c.merge(3, 4)
        self.assertEqual((3, 5), c.min_link(3))
        
        # merge the rest so we can test single-cluster case
        c.merge(3, 5)
        c.merge(6, 7)
        c.merge(0, 3)
        c.merge(0, 6)
    
        self.assertEqual((None, None), c.min_link(7))
        self.assertEqual((None, None), c.min_link())
    
    def test_pairs(self):
        ngrams = NGramSpace(1)
        docs = [ngrams.parse(raw) for raw in test_docs]
        c = Clustering(docs)
        
        self.assertEqual((1, 0), c.closest_pair([0, 1, 2]))
        self.assertEqual((5, 3), c.closest_pair([3, 4, 5]))
        self.assertEqual((7, 6), c.closest_pair([6, 7]))
        
        self.assertEqual((2, 0), c.farthest_pair([0, 1, 2]))
        self.assertEqual((5, 4), c.farthest_pair([3, 4, 5]))
        self.assertEqual((7, 6), c.farthest_pair([6, 7]))        
        
        
class TextExtractors(unittest.TestCase):
    def test_simple(self):
        self.assertEqual('', extract_comment(''))
        self.assertEqual('no marker', extract_comment('no marker'))
        self.assertEqual('no marker\nnewline', extract_comment('no marker\nnewline'))
        
        self.assertEqual('simple content', extract_comment('first metadata... Comment: simple content'))
        self.assertEqual('newline\ncontent', extract_comment('first metadata... Comment:\nnewline\ncontent\n'))
        
        self.assertEqual('star marker', extract_comment('Comment ****** star marker'))

        self.assertEqual('middle section', extract_comment('*** General Comment *** middle section ==== Attachments'))
        
    def test_real(self):
        simple_from_pdf = 'POST OFFICE BOX 3 18  61 BROADWAY  SARANAC LAKE, NEW YORK  12983-031 8 PHONE: 518-891 -2600  FAX: 51 8-891-2756 Sept. 22, 2005 r; Bureau of  Customs and Border  Protection Office of Regulations  and  Rulings Regulations Branch 1300 Pennsylvania  Ave., NW Washington, D.C. 20229 Re: Federal  rule  proposal,  Regulatory Information Number  165 1 -AA66 To whom it may concern: Please  consider  the  enclosed-editorial column as the official  comment  from the editorial board  of  our  two  newspapers - the Adirondack Daily Enterprise and the Lake Placid News  - on the passport  reqirement  rule proposed by  the U.S. departments of State and Homeland Security. Sincerely, Peter Crowley Managing editor Adirondack Daily Cc:  Plattsburgh-North  Country  Chamber of  Commerce P.O. Box  3 10 Plattsburgh, NY  1290 1'
        self.assertEqual(simple_from_pdf, extract_comment(simple_from_pdf))
        
        complex_from_pdf = "'II-Cl-05  PO1:33  IN Public  Comment  for  Document  Requirement  for Travel  Within  the  Western  Hemisphere Agency:  State Department Docket  ID:  165 1 -AA66 Author:  Judith  Quarles Email:  judyq@verizon.net Organization: Mailing  Address:  10 Park  St.  Oneonta  NY,  13820 Comments:  I  believe  the  requirement  for  a passport  as the  only  form  of  ID  would delay  travellers  unduly.  It  would  also  require  the  passport  office  to  come  up  with  a huge  number  of  passports  in  a short  period  of  time. When  I  was  growing  up  we  were  taught  how  wonderful  it  was  that  our  border  with Canada  was  so  open  and  friendly  and  did  not  require  passports.  I  hate  to  see that change.  Is  it  really  necessary  to  require  passports?"
        comment_from_pdf = "I  believe  the  requirement  for  a passport  as the  only  form  of  ID  would delay  travellers  unduly.  It  would  also  require  the  passport  office  to  come  up  with  a huge  number  of  passports  in  a short  period  of  time. When  I  was  growing  up  we  were  taught  how  wonderful  it  was  that  our  border  with Canada  was  so  open  and  friendly  and  did  not  require  passports.  I  hate  to  see that change.  Is  it  really  necessary  to  require  passports?"
        self.assertEqual(comment_from_pdf, extract_comment(complex_from_pdf))

        complex_from_crtext = '****** PUBLIC SUBMISSION ****** As of:4/4/11 11:02 AM                                Comments Due:October 31, 2005Docket:USCBP-2005-0005Documents Required for Travel Within the Western HemisphereComment On:USCBP-2005-0005-0001Documents Required for Travel Within the Western HemisphereDocument:USCBP-2005-0005-0128Comment submitted by Terri L. Land, Michigan Department of State===============================================================================***** Submitter Information *****===============================================================================***** General Comment *****The Michigan Department of State proposes that the Department of HomelandSecurity and Secretary of State accept a state-issued driver?s license oridentification card that is compliant with the REAL ID Act as an acceptabledocument under section 7209 of the Intelligence Reform and Terrorist PreventionAct of 2004, also known as the Western Hemisphere Travel Initiative.===============================================================================***** Attachments *****USCBP-2005-0005-0128.1 Comment submitted by Terry Lynn Land, Secretary of                       State, State of Michigan'
        comment_from_crtext = 'The Michigan Department of State proposes that the Department of HomelandSecurity and Secretary of State accept a state-issued driver?s license oridentification card that is compliant with the REAL ID Act as an acceptabledocument under section 7209 of the Intelligence Reform and Terrorist PreventionAct of 2004, also known as the Western Hemisphere Travel Initiative.'
        self.assertEqual(comment_from_crtext, extract_comment(complex_from_crtext))

        complex_from_msw = "Title: Documents Required for Travel Within the Western HemisphereFR Document Number: 05-17533Legacy Document ID:RIN:Publish Date: 09/01/2005 00:00:00Submitter Info:First Name: DeborahLast Name: HengstMailing Address: 345 Third Street #605City: Niagara FallsCountry: United StatesState or Province: NYPostal Code: 14303Email Address: dxeychick@verizon.netOrganization Name: Niagara Tourism & Convention CorporationComment Info: =================General Comment:I work for the Niagara Tourism & Convention Corporation,which is the agency responsible for the promotion of all of the NiagaraCounty region.  As a tourism employee and Niagara Falls resident, I feelthat this initiative would not be in the best interest of the localeconomy.  Tourism is one of the largest factors in this area's economy andby instituting mandatory passports, I really feel that the economy wouldsuffer by lagging tourism.  As a Niagara Falls resident who often timesenjoys traveling to Canada for baseball games, I can tell you that myfamily would not purchase passports at $100+ each just to go to a baseballgame.  Therefore, I can see where the economy in Canada would also sufferfrom this initiative as I'm sure mine wouldn't be the only family to stopgoing.I urge the federal government to reconsider this initiative and to listento our local leaders who are pushing for other alternatives to the passportmandate."
        comment_from_msw = "I work for the Niagara Tourism & Convention Corporation,which is the agency responsible for the promotion of all of the NiagaraCounty region.  As a tourism employee and Niagara Falls resident, I feelthat this initiative would not be in the best interest of the localeconomy.  Tourism is one of the largest factors in this area's economy andby instituting mandatory passports, I really feel that the economy wouldsuffer by lagging tourism.  As a Niagara Falls resident who often timesenjoys traveling to Canada for baseball games, I can tell you that myfamily would not purchase passports at $100+ each just to go to a baseballgame.  Therefore, I can see where the economy in Canada would also sufferfrom this initiative as I'm sure mine wouldn't be the only family to stopgoing.I urge the federal government to reconsider this initiative and to listento our local leaders who are pushing for other alternatives to the passportmandate."
        self.assertEqual(comment_from_msw, extract_comment(complex_from_msw))


if __name__ == '__main__':
    unittest.main()