from clustering import *

def cluster_loop(clustering, raw_docs):
    while True:
        (i, j) = clustering.min_link()

        if (i, j) == (None, None):
            print "All elements in single cluster."
            break

        if clustering.distance[i, j] != 0.0:
            print "Potential Clustering (%d, %d):" % (i, j)
            clustering.pp_distance(clustering.get_cluster(i))
            print raw_docs[i]
            print "\n========================================\n"
            clustering.pp_distance(clustering.get_cluster(j))
            print raw_docs[j]
            print "\n========================================\n"
            print "Would create:"
            clustering.pp_distance(clustering.get_cluster(i) + clustering.get_cluster(j))
            print '\n'
            while True:
                choice = raw_input("Cluster? [Y/n] ").lower()
                if choice in ('', 'y', 'n'):
                    break

            if choice == 'n':
                break

        clustering.merge(i, j)
        

def format_stats(stats):
    (min, avg, max) = ['{0:.3}'.format(s) for s in stats]
    return "min/avg/max = %s / %s / %s" % (min, avg, max)
    
        
def seeded_cluster_loop(clustering, raw_docs):
    
    while True:
        (seed, _) = clustering.min_link()

        if seed is None:
            print "All elements in single cluster."
            break
                
        while True:
            (i, j) = clustering.min_link(seed)
            cluster_i = clustering.get_cluster(i)
            cluster_j = clustering.get_cluster(j)
            stats_i = clustering.stats(cluster_i)
            stats_j = clustering.stats(cluster_j)
            stats_ij = clustering.stats(cluster_i + cluster_j)

            print "\n%s\n" % ('=' * 80)
            print "Potential Clustering: %s with %s\n" % (cluster_i, cluster_j)
            print "Closest existing doc:\n"
            print raw_docs[i]
            print "\n%s\n" % ('-' * 40)
            print "Closest new doc:\n"
            print raw_docs[j]
            print ""
            print "First cluster has distances\t\t" + format_stats(stats_i)
            print "Second cluster has distances\t\t" + format_stats(stats_j)
            print "Combined cluster would have distances\t" + format_stats(stats_ij)
            print ""
            
            avg_sim_before = 1 - stats_i[1]
            avg_sim_after = 1 - stats_ij[1]
            if avg_sim_after < .5 * avg_sim_before:
                print "*** Average distance increased too much. Stopping clustering automatically. ***"
                break
            
            while True:
                choice = raw_input("Cluster? [Y/n/b] ").lower()
                if choice in ('', 'y', 'n', 'b'):
                    break

            if choice == 'n':
                break
            
            if choice == 'b':
                return

            clustering.merge(i, j)


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
        new_reps += next
        new_cluster += clustering.get_cluster(next)
        
    return new_reps
    
    
    
def interactive_cluster(raw_docs, ngram = 4):
    ngrams = NGramSpace(ngram)
    docs = [ngrams.parse(raw) for raw in raw_docs]
    clustering = Clustering(docs)

    cluster_loop(clustering, raw_docs)
    
    return clustering


from pprint import PrettyPrinter
pp = PrettyPrinter().pprint