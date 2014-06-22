
class Targets(object):

    def __init__(self, Y, batcher=None):
        self.data = Y # Assume NxP
        self.batcher = batcher

    def value(self, reset=False):
        if self.batcher is None:
            return self.data
        else:
            return self.data[self.batcher.indices(),:]

    def shape(self):
        if self.batcher is None:
            return self.data.shape
        else:
            return self.data[self.batcher.indices(),:].shape

    def grad(self, other):
        raise Exception("Not sensible to take gradient in terms of targets.")

    def depends(self, other):
        return False