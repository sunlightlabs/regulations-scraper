import sys
import os
import cPickle
import csv

from clustering import *
from cftc import CFTCDocument
from db import RegsDocument


def format_stats(size, stats):
    (min, avg, max) = ['{0:.3}'.format(s) for s in stats]
    return "%s documents: min/avg/max = %s / %s / %s" % (size, min, avg, max)
    

def cluster_loop(clustering, docs):
    while True:
        (seed, _) = clustering.min_link()

        if seed is None:
            print "All elements in single cluster."
            break
        
        print "\n%s\n" % ('=' * 80)
        print "Initial document:\n"
        print docs[seed]     
        
        exponential_loop(clustering, seed, docs)
        

def exponential_loop(clustering, seed, docs):
    step_size = 1
    current_cluster = clustering.get_cluster(seed)
    current_stats = clustering.stats(current_cluster)
    
    while True:
        potential_reps = clustering.closest_neighbors(current_cluster, step_size)
        potential_cluster = list(set(reduce(lambda x, y: x + y, map(clustering.get_cluster, potential_reps))))
        potential_cluster.sort()
        combined_stats = clustering.stats(current_cluster + potential_cluster)
        
        avg_sim_before = 1 - current_stats[1]
        avg_sim_after = 1 - combined_stats[1]
        if avg_sim_after < .5 * avg_sim_before:
            print "*** Average distance increased too much. Stopping clustering automatically. ***"
            break        
        
        print "\n%s\n" % ('-' * 80)
        print "Sample doc to cluster:"
        print docs[potential_reps[-1]]
        print ""
        print "Existing cluster\t%s" % format_stats(len(current_cluster), current_stats)
        print "Combined cluster\t%s" % format_stats(len(current_cluster) + len(potential_cluster), combined_stats)
    
        while True:
            choice = raw_input("Cluster? [Y/n] ").lower()
            if choice in ('', 'y', 'n'):
                break

        if choice in ('', 'y'):
            for rep in potential_reps:
                clustering.merge(seed, rep)

            step_size *= 2
            current_cluster = clustering.get_cluster(seed)
            current_stats = clustering.stats(current_cluster)
        else:
            if step_size == 1:
                break
            else:
                step_size = 1
  

def dump_to_csv(clustering, docs, filename):
    writer = csv.writer(open(filename, 'w'))
    writer.writerow(['cluster number', 'document number'] + docs[0].get_output_headers())
    
    clusters = [c for c in clustering.get_clusters().values() if len(c) > 1]
    clusters.sort(key=len, reverse=True)
    
    for i in range(0, len(clusters)):
        for d in clusters[i]:
            writer.writerow([i, d] + docs[d].get_output_values())
    
    return writer
    

def main(filename):
    print "Reading existing clustering from %s..." % filename 
    (clustering, docs) = cPickle.load(open(filename, 'rb'))
    
    try:
        cluster_loop(clustering, docs)
    except KeyboardInterrupt:
        pass
    
    print "\nWriting clustering to %s..." % filename
    cPickle.dump((clustering, docs), open(filename, 'wb'), cPickle.HIGHEST_PROTOCOL)
    
    dump_to_csv(clustering, docs, filename + '.csv')
    

if __name__ == '__main__':
    main(sys.argv[1])

