import unittest
import datetime
import xml.etree.ElementTree as ET
from update_stats import USER, PROFILE, public_projects, activity_data, radar, activity, render

def repo(name, private=False, fork=False):
    return {'name':name,'full_name':USER+'/'+name,'private':private,'fork':fork,'owner':{'login':USER},'language':'Python','pushed_at':'2026-11-27T00:00:00Z'}

class TelemetryTest(unittest.TestCase):
    def setUp(self):
        self.today=datetime.date(2026,11,27)
        self.repos=[repo(USER),repo('public<&>'),repo('PRIVATE_SENTINEL',True),repo('FORK_SENTINEL',fork=True)]
    def test_privacy(self):
        self.assertEqual(len(public_projects(self.repos)),2)
        xml=radar(self.repos,self.today)
        self.assertNotIn('PRIVATE_SENTINEL',xml)
        self.assertNotIn('FORK_SENTINEL',xml)
        self.assertNotIn(PROFILE,xml)
        self.assertIn('public&lt;&amp;&gt;',xml)
    def test_activity(self):
        def e(i,r,public=True,actor=USER,date='2026-11-27'):
            return {'id':i,'public':public,'actor':{'login':actor},'repo':{'name':USER+'/'+r},'created_at':date+'T01:00:00Z','type':'PushEvent'}
        good=e('1','public<&>')
        events=[good,good,e('2','PRIVATE_SENTINEL'),e('3',USER),e('4','public<&>',False),e('5','public<&>',actor='bot'),e('6','public<&>',date='2026-10-01')]
        counts,kinds=activity_data(self.repos,events,self.today)
        self.assertEqual(sum(counts.values()),1)
        self.assertEqual(kinds['PushEvent'],1)
    def test_svg(self):
        for svg in [render(public_projects(self.repos)),radar(self.repos,self.today),activity(self.repos,[],self.today),radar([],self.today)]:
            ET.fromstring(svg)
if __name__=='__main__':
    unittest.main()
