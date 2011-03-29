from ngrams import jaccard, NGramSpace


class Clustering(object):
    
    def __init__(self, docs):
        self.num_docs = len(docs)
        self.assignments = range(0, self.num_docs)
        
        self.distance = [None for _ in range(0, self.num_docs)]
        for i in range(0, self.num_docs):
            self.distance[i] = [None for _ in range(0, i+1)]
            for j in range(0, i + 1):
                self.distance[i][j] = 1.0 - jaccard(docs[i], docs[j])

    def min_link(self):
        min_i = None
        min_j = None
        min_d = 1.0
        
        for i in range(0, self.num_docs):
            for j in range(0, i):
                if self.distance[i][j] <= min_d and self.assignments[i] != self.assignments[j]:
                    min_i = i
                    min_j = j
                    min_d = self.distance[i][j]
        
        return (min_i, min_j)

    def merge(self, i, j):
        cluster_i = self.assignments[i]
        cluster_j = self.assignments[j]
        
        for x in range(0, self.num_docs):
            if self.assignments[x] == cluster_j:
                self.assignments[x] = cluster_i
                
    def get_clusters(self):
        mapping = dict([(rep, list()) for rep in set(self.assignments)])
        for i in range(0, len(self.assignments)):
            mapping[self.assignments[i]].append(i)

        return mapping


def cluster_loop(clustering, raw_docs):
    while True:
        (i, j) = clustering.min_link()

        if (i, j) == (None, None):
            print "All elements in single cluster."
            break

        print "Potential Clustering (%d, %d):" % (i, j)
        print raw_docs[i]
        print "===================="
        print raw_docs[j]
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
    
    return clustering.assignments
