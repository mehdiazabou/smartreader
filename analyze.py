from math import sqrt
from PIL import Image,ImageDraw

class bicluster:
    def __init__(self, vec, left=None, right=None, distance=0.0, id=None):
        self.left = left
        self.right = right
        self.vec = vec
        self.id = id
        self.distance = distance

class analyze:
    def __init__(self,dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def cleandata(self):
        self.con.execute("")
        self.con.execute("delete from wordList where wordid in (select distinct wordid from wordCount group by wordid HAVING count(*)> %s or count(*)< %s)" %(500,15))
        self.con.execute("delete from wordCount where wordid in (select distinct wordid from wordCount group by wordid HAVING count(*)> %s or count(*)< %s)" %(500,15))
        self.con.commit()

    def readdb(self):
        words_tuple = self.con.execute('select word,wordid from wordList').fetchall()
        words = [t[0] for t in words_tuple]
        wordids = {}
        for i in range(len(words)):
            wordids[words_tuple[i][1]]=i
        articles = [t[0] for t in self.con.execute('select title from articleList').fetchall()]
        data = self.con.execute('select articleid,wordid,wcount from wordCount').fetchall()
        #count = [[0]*len(words)]*len(articles)
        count = [[0]*len(words) for i in range(len(articles))]
        for t in data:
            count[t[0]-1][wordids[t[1]]]=t[2]
        return articles, words, count

    def pearson(v1, v2):
        # Simple sums
        sum1 = sum(v1)
        sum2 = sum(v2)

        # Sums of the squares
        sum1Sq = sum([pow(v, 2) for v in v1])
        sum2Sq = sum([pow(v, 2) for v in v2])

        # Sum of the products
        pSum = sum([v1[i] * v2[i] for i in range(len(v1))])

        # Calculate r (Pearson score)
        num = pSum - (sum1 * sum2 / len(v1))
        den = sqrt((sum1Sq - pow(sum1, 2) / len(v1)) * (sum2Sq - pow(sum2, 2) / len(v1)))
        if den == 0: return 0

        return 1.0 - num / den


    def hcluster(self,rows, distance=pearson):
        distances = {}
        currentclustid = -1
        # Clusters are initially just the rows
        clust = [bicluster(rows[i], id=i) for i in range(len(rows))]
        while len(clust) > 1:
            lowestpair = (0, 1)
            closest = distance(clust[0].vec, clust[1].vec)
            # loop through every pair looking for the smallest distance
            for i in range(len(clust)):
                for j in range(i + 1, len(clust)):
                    # distances is the cache of distance calculations
                    if (clust[i].id, clust[j].id) not in distances:
                        distances[(clust[i].id, clust[j].id)] = distance(clust[i].vec, clust[j].vec)
                    d = distances[(clust[i].id, clust[j].id)]
                    if d < closest:
                        closest = d
                        lowestpair = (i, j)
            # calculate the average of the two clusters
            mergevec = [(clust[lowestpair[0]].vec[i] + clust[lowestpair[1]].vec[i]) / 2.0 for i in
                        range(len(clust[0].vec))]
            # create the new cluster
            newcluster = bicluster(mergevec, left=clust[lowestpair[0]],
                                   right=clust[lowestpair[1]],
                                   distance=closest, id=currentclustid)
            # cluster ids that weren't in the original set are negative
            currentclustid -= 1
            del clust[lowestpair[1]]
            del clust[lowestpair[0]]
            clust.append(newcluster)
        return clust[0]

    # Printing results
    def printclust(self,clust, labels=None, n=0):
        # indent to make a hierarchy layout
        for i in range(n): print ' ',
        if clust.id < 0:
            # negative id means that this is branch
            print('-')
        else:
            # positive id means that this is an endpoint
            if labels == None:
                print(clust.id)
            else:
                print(labels[clust.id])
        # now print the right and left branches
        if clust.left != None: self.printclust(clust.left, labels=labels, n=n + 1)
        if clust.right != None: self.printclust(clust.right, labels=labels, n=n + 1)

    # Drawing the dendogram
    def getheight(self,clust):
        # Is this an endpoint? Then the height is just 1
        if clust.left == None and clust.right == None: return 1
        # Otherwise the height is the same of the heights of
        # each branch
        return self.getheight(clust.left) + self.getheight(clust.right)

    def getdepth(self,clust):
        # The distance of an endpoint is 0.0
        if clust.left == None and clust.right == None: return 0
        # The distance of a branch is the greater of its two sides
        # plus its own distance
        return max(self.getdepth(clust.left), self.getdepth(clust.right)) + clust.distance

    def drawdendrogram(self,clust, labels, jpeg='clusters_01.jpg'):
        # height and width
        h = self.getheight(clust) * 20
        w = 1200
        depth = self.getdepth(clust)
        # width is fixed, so scale distances accordingly
        scaling = float(w - 700) / depth
        # Create a new image with a white background
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.line((0, h / 2, 10, h / 2), fill=(255, 0, 0))
        # Draw the first node
        self.drawnode(draw, clust, 10, (h / 2), scaling, labels)
        img.save(jpeg, 'JPEG')

    def drawnode(self,draw, clust, x, y, scaling, labels):
        if clust.id < 0:
            h1 = self.getheight(clust.left) * 20
            h2 = self.getheight(clust.right) * 20
            top = y - (h1 + h2) / 2
            bottom = y + (h1 + h2) / 2
            # Line length
            ll = clust.distance * scaling
            # Vertical line from this cluster to children
            draw.line((x, top + h1 / 2, x, bottom - h2 / 2), fill=(255, 0, 0))
            # Horizontal line to left item
            draw.line((x, top + h1 / 2, x + ll, top + h1 / 2), fill=(255, 0, 0))
            # Horizontal line to right item
            draw.line((x, bottom - h2 / 2, x + ll, bottom - h2 / 2), fill=(255, 0, 0))
            # Call the function to draw the left and right nodes
            self.drawnode(draw, clust.left, x + ll, top + h1 / 2, scaling, labels)
            self.drawnode(draw, clust.right, x + ll, bottom - h2 / 2, scaling, labels)
        else:
            # If this is an endpoint, draw the item label
            draw.text((x + 5, y - 7), labels[clust.id].encode('latin-1','ignore'), (0, 0, 0))