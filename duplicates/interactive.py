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
        
        step_size = 1
                
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
        
        print "\n%s\n" % ('=' * 80)
        print "Potential Clustering: %s with %s\n" % (current_cluster, potential_cluster)
        print "Sample doc to cluster:"
        print raw_docs[potential_reps[-1]]
        print ""
        print "Existing cluster has distances\t\t%s" % format_stats(current_stats)
        print "Combined cluster would have distance\t\t%s" % format_stats(combined_stats)
    
        while True:
            choice = raw_input("Cluster? [Y/n] ").lower()
            if choice in ('', 'y', 'n'):
                break

        if choice == 'n':
            break
        
        for rep in potential_reps:
            clustering.merge(seed, rep)
        
        step_size *= 2
        current_cluster = clustering.get_cluster(seed)
        current_stats = clustering.stats(current_cluster)
        


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


from pprint import PrettyPrinter
pp = PrettyPrinter().pprint