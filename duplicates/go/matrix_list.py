import random
import sys
import time

def MatrixMin(m):
    min_i = 0
    min_j = 0
    min_v = 1.0
    
    n = len(m)
    
    for i in xrange(n):
        for j in xrange(n):
            if m[i][j] < min_v:
                min_i = i
                min_j = j
                min_v = m[i][j]

    return min_i, min_j


def RandMatrix(n):
    m = []
    
    for i in xrange(n):
        row = []
        for j in xrange(n):
            row.append(random.random())
        m.append(row)
    
    return m


if __name__ == '__main__':
    n = int(sys.argv[1])

    start = time.time()
    m = RandMatrix(n)
    end = time.time()
    print "Creating %d x %d matrix took %fms" % (n, n, (end - start) * 1000.0)

    start = time.time()
    i, j = MatrixMin(m)
    end = time.time()
    print "Finding min in %d x %d matrix took %fms" % (n, n, (end - start) * 1000.0)
    print "Min was %f" % m[i][j]
