import tensorflow as tf
import numpy as np
from DCM.PDE_utils import PDE_utils


class Poisson(PDE_utils):

    def __init__(self):

        self.sigma = 0.04
        self.epsilon = None
        self.q = None
        super().__init__()

    # Define loss of the PDE
    def residual_loss(self,mesh,model,X):
        x,y,z = X
        r = self.laplacian(mesh,model,X) - self.source(x,y,z)        
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r

    def source(self,x,y,z):
        sum = 0
        for qk,Xk in self.q:
            xk,yk,zk = Xk
            deltak = tf.exp((-1/(2*self.sigma**2))*((x-xk)**2+(y-yk)**2+(z-zk)**2))
            sum += qk*deltak
        normalizer = (1/((2*self.pi)**(3.0/2)*self.sigma**3))
        sum *= normalizer
        return (-1/self.epsilon)*sum
    
    def Fundamental(self,X,Xr):
        x,y,z = X
        xr,yr,zr = Xr
        r = tf.sqrt((x-xr)**2 + (y-yr)**2 + (z-zr)**2)
        G = (1/(4*self.pi))*(1/r)
        return G
    
    def border_value(self,x,y,z,R):
        q = 0
        for qk,Xk in self.q:
            xk,yk,zk = Xk
            #r_1 = 1/((x-xk)**2+(y-yk)**2+(z-zk)**2)
            q += qk
        r = np.sqrt(x**2 + y**2 + z**2)
        return q/(4*self.pi)*(np.exp(-self.kappa*(r-R))/(self.epsilon*(1+self.kappa*R)*r))
    
    def preconditioner(self,mesh,model,X):
        x,y,z = X

        rI = self.problem['rI']
        epsilon_1 = self.problem['epsilon_1']
        epsilon_2 = self.problem['epsilon_2']
        kappa = self.problem['kappa']
        q = self.q[0][0]

        R = mesh.stack_X(x,y,z)
        u = model(R)
        r = tf.sqrt(x**2+y**2+z**2)
        upred = (q/(4*self.pi)) * ( 1/(epsilon_1*r) - 1/(epsilon_1*rI) + 1/(epsilon_2*(1+kappa*rI)*rI) )
        loss = tf.reduce_mean(tf.square(upred-u))

        return loss
    

    def analytic(self,x,y,z):
        rI = self.problem['rI']
        epsilon_1 = self.problem['epsilon_1']
        epsilon_2 = self.problem['epsilon_2']
        kappa = self.problem['kappa']
        q = self.q[0][0]

        r = tf.sqrt(x**2+y**2+z**2)
        upred = (q/(4*self.pi)) * ( 1/(epsilon_1*r) - 1/(epsilon_1*rI) + 1/(epsilon_2*(1+kappa*rI)*rI) )

        return upred



class Helmholtz(PDE_utils):

    def __init__(self):

        self.sigma = 0.04
        self.epsilon = None
        self.q = None
        super().__init__()


    # Define loss of the PDE
    def residual_loss(self,mesh,model,X):
        x,y,z = X
        R = mesh.stack_X(x,y,z)
        u = model(R)
        r = self.laplacian(mesh,model,X) - self.kappa**2*u      
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r
    
    def border_value(self,x,y,z,R):
        q = 0
        for qk,Xk in self.q:
            xk,yk,zk = Xk
            #r_1 = 1/((x-xk)**2+(y-yk)**2+(z-zk)**2)
            q += qk
        r = np.sqrt(x**2 + y**2 + z**2)
        return q/(4*self.pi)*(np.exp(-self.kappa*(r-R))/(self.epsilon*(1+self.kappa*R)*r))

    def Fundamental(self,X,Xr):
        x,y,z = X
        xr,yr,zr = Xr
        r = tf.sqrt((x-xr)**2 + (y-yr)**2 + (z-zr)**2)
        G = (1/(4*self.pi))*(-tf.exp(-self.kappa*r)/r)
        return G

    def preconditioner(self,mesh,model,X):
        x,y,z = X

        rI = self.problem['rI']
        epsilon_1 = self.problem['epsilon_1']
        epsilon_2 = self.problem['epsilon_2']
        kappa = self.problem['kappa']
        q = self.q[0][0]

        R = mesh.stack_X(x,y,z)
        u = model(R)
        r = tf.sqrt(x**2+y**2+z**2)
        upred = (q/(4*self.pi)) * (tf.exp(-kappa*(r-rI))/(epsilon_2*(1+kappa*rI)*r))
        loss = tf.reduce_mean(tf.square(upred-u))

        return loss
    

    def analytic(self,x,y,z):
        rI = self.problem['rI']
        epsilon_1 = self.problem['epsilon_1']
        epsilon_2 = self.problem['epsilon_2']
        kappa = self.problem['kappa']
        q = self.q[0][0]

        r = tf.sqrt(x**2+y**2+z**2)
        upred = (q/(4*self.pi)) * (tf.exp(-kappa*(r-rI))/(epsilon_2*(1+kappa*rI)*r))

        return upred
    



class Non_Linear(PDE_utils):

    def __init__(self):

        self.sigma = 0.04
        self.epsilon = None
        self.q = None
        super().__init__()


    # Define loss of the PDE
    def residual_loss(self,mesh,model,X):
        x,y,z = X
        R = mesh.stack_X(x,y,z)
        u = model(R)
        r = self.laplacian(mesh,model,X) - self.kappa**2*tf.math.sinh(u)      
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r
    


class PBE_Interface(PDE_utils):

    def __init__(self):
        super().__init__()


    def adapt_PDEs(self,PDEs,unions):
        self.PDEs = PDEs
        self.uns = unions

    def loss_I(self,solver,solver_ex):
        loss = 0
        for j in range(len(solver.PDE.XI_data)):
            X = solver.mesh.get_X(solver.PDE.XI_data[j])
            x_i,y_i,z_i = X

            R = solver.mesh.stack_X(x_i,y_i,z_i)
            u_1 = solver.model(R)
            u_2 = solver_ex.model(R)

            n_v = self.normal_vector(X)
            du_1 = self.directional_gradient(solver.mesh,solver.model,X,n_v)
            du_2 = self.directional_gradient(solver_ex.mesh,solver_ex.model,X,n_v)

            u_prom = (u_1+u_2)/2
            
            loss += tf.reduce_mean(tf.square(u_1 - u_prom)) 
            loss += tf.reduce_mean(tf.square(du_1*solver.un - du_2*solver_ex.un))
            
        return loss
    

    def analytic(self,r):
        rI = self.problem['rI']
        epsilon_1 = self.problem['epsilon_1']
        epsilon_2 = self.problem['epsilon_2']
        kappa = self.problem['kappa']
        q = self.q[0][0]

        f_IN = lambda r: (q/(4*self.pi)) * ( 1/(epsilon_1*r) - 1/(epsilon_1*rI) + 1/(epsilon_2*(1+kappa*rI)*rI) )
        f_OUT = lambda r: (q/(4*self.pi)) * (np.exp(-kappa*(r-rI))/(epsilon_2*(1+kappa*rI)*r))

        y = np.piecewise(r, [r<=rI, r>rI], [f_IN, f_OUT])

        return y


    