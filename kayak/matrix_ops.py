# Author: Ryan P. Adams <rpa@seas.harvard.edu>
# Copyright 2014, The President and Fellows of Harvard University

import numpy as np

from .        import Differentiable
from util     import broadcast

class MatMult(Differentiable):

    def __init__(self, A, B, *args):
        super(MatMult, self).__init__()

        # Recurse to handle lists of arguments.
        if len(args) > 0:
            B = MatMult(B, *args)

        if A.shape()[1] != B.shape()[0]:
            raise Exception("Cannot multiply %s by %s matrices." % (A.shape(), B.shape()))

        self.A = A
        self.B = B

    def compute_value(self, reset, rng, inputs):
        return np.dot( self.A.value(reset, rng, inputs), self.B.value(reset, rng, inputs) )

    def local_grad_A(self, outgrad):
        return np.dot(outgrad, self.B.value().T)

    def local_grad_B(self, outgrad):
        return np.dot(self.A.value().T, outgrad)

    def compute_grad(self, other, outgrad):
        gradient = np.zeros(other.shape())

        if other == self.A:
            gradient += self.local_grad_A(outgrad)
        elif self.A.depends(other):
            gradient += self.A.grad(other, self.local_grad_A(outgrad))

        if other == self.B:
            gradient += self.local_grad_B(outgrad)
        elif self.B.depends(other):
            gradient += self.B.grad(other, self.local_grad_B(outgrad))

        return gradient

    def depends(self, other):
        return other == self.A or other == self.B or self.A.depends(other) or self.B.depends(other)

    def shape(self, inputs=None):
        if len(self.B.shape(inputs)) == 1:
            return (self.A.shape(inputs)[0],)
        else:
            return (self.A.shape(inputs)[0], self.B.shape(inputs)[1],)

class MatSum(Differentiable):
     
    def __init__(self, A, axis=None):
        super(MatSum, self).__init__()

        if axis is not None and type(axis) != int:
            raise Exception("Can only sum over one axis at a time.")

        self.A    = A
        self.axis = axis

    def compute_value(self, reset, rng, inputs):
        if self.axis is None:
            # Handle the sum over all elements.
            A_val = self.A.value(reset, rng, inputs)
            return np.sum(A_val).reshape([1] * len(A_val.shape))
        else:
            # Handle a sum and reexpansion over one dimension.
            return np.expand_dims(np.sum(self.A.value(reset, rng, inputs), axis=self.axis), axis=self.axis)

    def local_grad(self, outgrad):
        return outgrad * np.ones(self.A.shape())

    def compute_grad(self, other, outgrad):
        if other == self.A:
            return self.local_grad(outgrad)
        elif self.A.depends(other):
            return self.A.grad(other, self.local_grad(outgrad))
        else:
            return np.zeros(other.shape())
    
    def shape(self, inputs=None):
        if self.axis is None:
            return tuple( [1] * len(self.A.shape(inputs)) )
        else:
            A_shape = list(self.A.shape(inputs))
            A_shape[self.axis] = 1
            return tuple(A_shape)

    def depends(self, other):
        return self.A == other or self.A.depends(other)

class MatAdd(Differentiable):

    def __init__(self, A, B, *args):
        super(MatAdd, self).__init__()

        # Recurse to handle lists of arguments.
        if len(args) > 0:
            B = MatAdd(B, *args)
        
        if broadcast(A.shape(), B.shape()) is None:
            raise Exception("Matrices are not broadcastable: %s vs %s" % (A.shape(), B.shape()))

        self.A = A
        self.B = B

    def compute_value(self, reset, rng, inputs):
        return self.A.value(reset, rng, inputs) + self.B.value(reset, rng, inputs)

    def local_grad_A(self, outgrad):
        if np.atleast_1d(outgrad).shape == self.A.shape():
            return outgrad
        else:
            broadcast_axes = tuple(np.nonzero(np.array(self.A.shape())==1)[0])
            return np.sum(outgrad, axis=broadcast_axes).reshape(self.A.shape())

    def local_grad_B(self, outgrad):
        if np.atleast_1d(outgrad).shape == self.B.shape():
            return outgrad
        else:
            broadcast_axes = tuple(np.nonzero(np.array(self.B.shape())==1)[0])
            return np.sum(outgrad, axis=broadcast_axes).reshape(self.B.shape())

    def compute_grad(self, other, outgrad):
        if outgrad is None:
            outgrad = np.ones(broadcast(self.A.shape(), self.B.shape()))

        gradient = np.zeros(other.shape())

        if other == self.A:
            gradient += self.local_grad_A(outgrad)
        elif self.A.depends(other):
            gradient += self.A.grad(other, self.local_grad_A(outgrad))

        if other == self.B:
            gradient += self.local_grad_B(outgrad)
        elif self.B.depends(other):
            gradient += self.B.grad(other, self.local_grad_B(outgrad))

        return gradient

    def depends(self, other):
        return other == self.A or other == self.B or self.A.depends(other) or self.B.depends(other)

    def shape(self, inputs=None):
        return broadcast(self.A.shape(inputs), self.B.shape(inputs))

class MatDet(Differentiable):
    pass

class MatLogDet(Differentiable):
    pass

class MatTrace(Differentiable):
    pass

class Transpose(Differentiable):

    def __init__(self, A, axes=None):
        super(Transpose, self).__init__()

        self.A    = A
        self.axes = axes

    def compute_value(self, reset, rng, inputs):
        return np.transpose(self.A.value(reset, rng, inputs), axes=self.axes)

    def local_grad(self, outgrad):
        if self.axes is None:
            return np.transpose(outgrad)
        else:
            return np.transpose(outgrad, axes=np.argsort(self.axes))

    def compute_grad(self, other, outgrad):
        if other == self.A:
            return self.local_grad(outgrad)
        elif self.A.depends(other):
            return self.A.grad(other, self.local_grad(outgrad))
        else:
            return np.zeros(self.A.shape())

    def depends(self, other):
        return other == self.A or self.A.depends(other)

    def shape(self):
        if self.axes is None:
            return self.A.shape()[::-1]
        else:
            return tuple([self.A.shape[ii] for ii in self.axes])

class Reshape(Differentiable):

    def __init__(self, A, new_shape):
        super(Reshape, self).__init__()

        self.A         = A
        self.new_shape = new_shape

    def compute_value(self, reset, rng, inputs):
        return np.reshape(self.A.value(reset, rng, inputs), self.new_shape)

    def local_grad(self, outgrad):
        return np.reshape(outgrad, self.A.shape())

    def compute_grad(self, other, outgrad):
        if other == self.A:
            return self.local_grad(outgrad)
        elif self.A.depends(other):
            return self.A.grad(other, self.local_grad(outgrad))
        else:
            return np.zeros(self.A.shape())

    def depends(self, other):
        return other == self.A or self.A.depends(other)

    def shape(self, inputs=None):
        return self.new_shape

class TensorMult(Differentiable):
    pass
       