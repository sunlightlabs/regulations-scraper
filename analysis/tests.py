
import unittest

from analysis.export import deep_get


class TestDeepGet(unittest.TestCase):
    
    def test_deep_get(self):
        self.assertEqual(None, deep_get('foo', {}))

        self.assertEqual(7, deep_get('foo', {'foo': 7}))
        self.assertEqual(None, deep_get('bar', {'foo': 7}))
        
        self.assertEqual(7, deep_get('foo.bar.spaz', {'foo': {'bar': {'spaz': 7}}}))
        self.assertEqual({'spaz': 7}, deep_get('foo.bar', {'foo': {'bar': {'spaz': 7}}}))
        self.assertEqual(None, deep_get('foo.more.less', {'foo': {'bar': {'spaz': 7}}}))
        self.assertEqual(None, deep_get('spaz.more.less', {'foo': {'bar': {'spaz': 7}}}))
    
    
if __name__ == '__main__':
    unittest.main()