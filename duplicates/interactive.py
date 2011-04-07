import sys
import os
import cPickle

from clustering import *
from db import setup


def format_stats(stats):
    (min, avg, max) = ['{0:.3}'.format(s) for s in stats]
    return "min/avg/max = %s / %s / %s" % (min, avg, max)
    

def cluster_loop(clustering, raw_docs):
    while True:
        (seed, _) = clustering.min_link()

        if seed is None:
            print "All elements in single cluster."
            break
        
        print "\n%s\n" % ('=' * 80)
        print "Initial document:\n"
        print raw_docs[seed]     
        
        exponential_loop(clustering, seed, raw_docs)
        

def exponential_loop(clustering, seed, raw_docs):
    step_size = 1
    current_cluster = clustering.get_cluster(seed)
    current_stats = clustering.stats(current_cluster)
    
    while True:
        potential_reps = merge_multiple(clustering, current_cluster, step_size)
        potential_cluster = reduce(lambda x, y: x + y, map(clustering.get_cluster, potential_reps))
        combined_stats = clustering.stats(current_cluster + potential_cluster)
        
        avg_sim_before = 1 - current_stats[1]
        avg_sim_after = 1 - combined_stats[1]
        if avg_sim_after < .5 * avg_sim_before:
            print "*** Average distance increased too much. Stopping clustering automatically. ***"
            break        
        
        print "\n%s\n" % ('-' * 80)
        print "Potential Clustering: %s with %s\n" % (current_cluster, potential_cluster)
        print "Sample doc to cluster:"
        print raw_docs[potential_reps[-1]]
        print ""
        print "Existing cluster has distances\t\t%s" % format_stats(current_stats)
        print "Combined cluster would have distance\t%s" % format_stats(combined_stats)
    
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
                

def automatic_merges(clustering, cluster, max_similarity_drop):
    (_, avg_distance, _) = clustering.stats(cluster)
    
    new_cluster = list(cluster)
    orig_similarity = 1 - avg_distance
    new_similarity = orig_similarity
    
    while True:
        (orig, next) = clustering.closest_neighbor(new_cluster)
        next_cluster = clustering.get_cluster(next)
        (_, next_avg_distance, _) = clustering.stats(new_cluster + next_cluster)
        new_similarity = 1 - next_avg_distance
        
        if new_similarity / orig_similarity > max_similarity_drop:
            new_cluster += next_cluster
        else:
            break
    
    return new_cluster
    
    
def merge_multiple(clustering, cluster, n):
    new_cluster = list(cluster)
    new_reps = list()
    
    for _ in range(0, n):
        (orig, next) = clustering.closest_neighbor(new_cluster)
        new_reps.append(next)
        new_cluster += clustering.get_cluster(next)
        
    return new_reps
    
    
def interactive_cluster(raw_docs, ngram = 4):
    ngrams = NGramSpace(ngram)
    docs = [ngrams.parse(raw) for raw in raw_docs]
    clustering = Clustering(docs)

    cluster_loop(clustering, raw_docs)
    
    return clustering


def main(filename):
    if os.path.exists(filename):
        print "Reading existing clustering from %s..." % filename 
        (texts, parsed, ngrams, clustering) = cPickle.load(open(filename, 'rb'), cPickle.HIGHEST_PROTOCOL)
    else:
        print "Loading new clustering from database..."
        (texts, parsed, ngrams, clustering) = setup()
    
    try:
        cluster_loop(clustering, texts)
    except KeyboardInterrupt:
        pass
    
    print "\nWriting clustering to %s..." % filename
    cPickle.dump((texts, parsed, ngrams, clustering), open(filename, 'wb'), cPickle.HIGHEST_PROTOCOL)
    

if __name__ == '__main__':
    main(sys.argv[1])

