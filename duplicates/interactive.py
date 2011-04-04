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


def interactive_cluster(raw_docs, ngram = 4):
    ngrams = NGramSpace(ngram)
    docs = [ngrams.parse(raw) for raw in raw_docs]
    clustering = Clustering(docs)

    cluster_loop(clustering, raw_docs)
    
    return clustering