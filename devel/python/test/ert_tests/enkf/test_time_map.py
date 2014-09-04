import datetime 

from ert.enkf.enums.realization_state_enum import RealizationStateEnum
from ert.enkf import TimeMap
from ert.test import TestAreaContext
from ert.test import ExtendedTestCase


class TimeMapTest(ExtendedTestCase):

    def test_time_map(self):
        with self.assertRaises(IOError):
            TimeMap("Does/not/exist")

    
        tm = TimeMap()
        with self.assertRaises(IndexError):
            t = tm[10]
            
        self.assertTrue( tm.update(0 , datetime.date(2000 , 1, 1)))
        self.assertEqual( tm[0] , datetime.date(2000 , 1, 1))
        
        self.assertTrue( tm.isStrict() )
        with self.assertRaises(Exception):
            tm.update(tm.update(0 , datetime.date(2000 , 1, 2)))

        tm.setStrict( False )
        self.assertFalse(tm.update(0 , datetime.date(2000 , 1, 2)))

        tm.setStrict( True )
        self.assertTrue( tm.update( 1 , datetime.date(2000 , 1, 2)))
        d = tm.dump()
        self.assertEqual( d , [(0 , datetime.date(2000,1,1) , 0),
                               (1 , datetime.date(2000,1,2) , 1)])
        

    def test_fscanf(self):
        tm = TimeMap()
    
        with self.assertRaises(IOError):
            tm.fload( "Does/not/exist" )

        with TestAreaContext("timemap/fload1") as work_area:
            with open("map.txt","w") as fileH:
                fileH.write("10/10/2000\n")
                fileH.write("12/10/2000\n")
                fileH.write("14/10/2000\n")
                fileH.write("16/10/2000\n")
            
            tm.fload("map.txt")
            self.assertEqual( 4 , len(tm) )
            self.assertEqual( datetime.date(2000,10,10) , tm[0])
            self.assertEqual( datetime.date(2000,10,16) , tm[3])

        with TestAreaContext("timemap/fload2") as work_area:
            with open("map.txt","w") as fileH:
                fileH.write("10/10/200X\n")

            with self.assertRaises(Exception):    
                tm.fload("map.txt")

            self.assertEqual( 4 , len(tm) )
            self.assertEqual( datetime.date(2000,10,10) , tm[0])
            self.assertEqual( datetime.date(2000,10,16) , tm[3])


        with TestAreaContext("timemap/fload2") as work_area:
            with open("map.txt","w") as fileH:
                fileH.write("12/10/2000\n")
                fileH.write("10/10/2000\n")

            with self.assertRaises(Exception):    
                tm.fload("map.txt")

            self.assertEqual( 4 , len(tm) )
            self.assertEqual( datetime.date(2000,10,10) , tm[0])
            self.assertEqual( datetime.date(2000,10,16) , tm[3])

                
    def test_setitem(self):
        tm = TimeMap()
        tm[0] = datetime.date(2000,1,1)
        tm[1] = datetime.date(2000,1,2)
        self.assertEqual(2 , len(tm))

        self.assertEqual( tm[0] , datetime.date(2000,1,1) )
        self.assertEqual( tm[1] , datetime.date(2000,1,2) )


