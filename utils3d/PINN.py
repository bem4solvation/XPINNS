import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import os
from time import time
from tqdm import tqdm as log_progress

class PINN():
    
    def __init__(self):

        self.DTYPE='float32'
       
        self.loss_hist = list()
        self.loss_r = list()
        self.loss_bD = list()
        self.loss_bN = list()
        self.loss_P = list()
        self.loss_bI = list()
        self.iter = 0
        self.lr = None

    def adapt_mesh(self, mesh,
        w_r=1,
        w_d=1,
        w_n=1,
        w_i=1):
        
        self.mesh = mesh
        self.lb = mesh.lb
        self.ub = mesh.ub

        self.X_r = self.mesh.data_mesh['residual']
        self.w_r = w_r
        self.XD_data,self.UD_data = self.mesh.data_mesh['dirichlet']
        self.w_d = w_d
        self.XN_data,self.UN_data,self.derN = self.mesh.data_mesh['neumann']
        self.w_n = w_n
        self.XI_data,self.derI = self.mesh.data_mesh['interface']
        self.w_i = w_i

        self.x,self.y,self.z = self.mesh.get_X(self.X_r)
        

    def create_NeuralNet(self,NN_class,lr,*args,**kwargs):
        self.model = NN_class(self.mesh.lb, self.mesh.ub,*args,**kwargs)
        self.model.build_Net()
        self.lr = tf.keras.optimizers.schedules.PiecewiseConstantDecay(*lr)


    def adapt_PDE(self,PDE):
        self.PDE = PDE

    def load_NeuralNet(self,directory,name,lr):
        path = os.path.join(os.getcwd(),directory,name)
        NN_model = tf.keras.models.load_model(path, compile=False)
        self.model = NN_model
        self.lr = tf.keras.optimizers.schedules.PiecewiseConstantDecay(*lr)

    def save_model(self,directory,name):
        dir_path = os.path.join(os.getcwd(),directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        self.model.save(os.path.join(dir_path,name))

    def get_r(self):
        with tf.GradientTape(persistent=True) as tape:
           
            tape.watch(self.x)
            tape.watch(self.y)
            tape.watch(self.z)
            R = self.mesh.stack_X(self.x,self.y,self.z)
            u = self.model(R)
            u_x = tape.gradient(u, self.x)
            u_y = tape.gradient(u, self.y)
            u_z = tape.gradient(u, self.z)
            
        u_xx = tape.gradient(u_x, self.x)
        u_yy = tape.gradient(u_y, self.y)
        u_zz = tape.gradient(u_z, self.z)

        del tape
        return self.PDE.fun_r(self.x, u_x, u_xx, self.y, u_y, u_yy, self.z, u_z, u_zz)
    

    def loss_fn(self):
        
        L = dict()
        L['r'] = 0
        L['D'] = 0
        L['N'] = 0

        #residual
        r = self.get_r()
        phi_r = tf.reduce_mean(tf.square(r))
        loss = self.w_r*phi_r
        L['r'] += loss/self.w_r

        #dirichlet
        for i in range(len(self.XD_data)):
            u_pred = self.model(self.XD_data[i])
            loss_D = self.w_d*tf.reduce_mean(tf.square(self.UD_data[i] - u_pred)) 
            loss += loss_D
            L['D'] += loss_D/self.w_d

        #neumann
        for i in range(len(self.XN_data)):
            x_n,y_n,z_n = self.mesh.get_X(self.XN_data[i])
            if self.derN[i]=='x':
                with tf.GradientTape(watch_accessed_variables=False) as tapex:
                    tapex.watch(x_n)
                    R = self.mesh.stack_X(x_n,y_n,z_n)
                    u_pred = self.model(R)
                ux_pred = tapex.gradient(u_pred,x_n)
                del tapex

                loss_N = self.w_n*tf.reduce_mean(tf.square(self.UN_data[i] - ux_pred)) 
            
            elif self.derN[i]=='y':
                with tf.GradientTape(watch_accessed_variables=False) as tapey:
                    tapey.watch(y_n)
                    R = self.mesh.stack_X(x_n,y_n,z_n)
                    u_pred = self.model(R)
                uy_pred = tapey.gradient(u_pred,y_n)
                del tapey

                loss_N = self.w_n*tf.reduce_mean(tf.square(self.UN_data[i] - uy_pred)) 

            elif self.derN[i]=='z':
                with tf.GradientTape(watch_accessed_variables=False) as tapez:
                    tapez.watch(z_n)
                    R = self.mesh.stack_X(x_n,y_n,z_n)
                    u_pred = self.model(R)
                uz_pred = tapez.gradient(u_pred,z_n)
                del tapez

                loss_N = self.w_n*tf.reduce_mean(tf.square(self.UN_data[i] - uz_pred)) 
            
            elif self.derN[i]=='r':
                with tf.GradientTape(persistent=True, watch_accessed_variables=False) as taper:
                    taper.watch(x_n)
                    taper.watch(y_n)
                    taper.watch(z_n)
                    R = self.mesh.stack_X(x_n,y_n,z_n)
                    u_pred = self.model(R)
                ux_pred = taper.gradient(u_pred,x_n)
                uy_pred = taper.gradient(u_pred,y_n)
                uz_pred = taper.gradient(u_pred,z_n)
                del taper
                
                norm_vn = tf.sqrt(x_n**2+y_n**2+z_n**2)
                un_pred = (x_n*ux_pred + y_n*uy_pred + z_n*uz_pred)/norm_vn

                loss_N = self.w_n*tf.reduce_mean(tf.square(self.UN_data[i] - un_pred)) 

            loss += loss_N
            L['N'] += loss_N/self.w_n    

        return loss,L
    
    def get_grad(self):
        with tf.GradientTape(persistent=True) as tape:
            tape.watch(self.model.trainable_variables)
            loss,L = self.loss_fn()
        g = tape.gradient(loss, self.model.trainable_variables)
        del tape
        return loss, L, g
    
    def solve_with_TFoptimizer(self, optimizer, N=1001):
        @tf.function
        def train_step():
            loss, L_loss, grad_theta = self.get_grad()
            optimizer.apply_gradients(zip(grad_theta, self.model.trainable_variables))
            return loss, L_loss
        
        pbar = log_progress(range(N))
        pbar.set_description("Loss: %s " % 100)
        for i in pbar:
            loss,L_loss = train_step()
            self.callback(loss,L_loss)
            if self.iter % 10 == 0:
                pbar.set_description("Loss: {:6.4e}".format(self.current_loss))

    def callback(self,loss,L_loss):
        self.loss_r.append(L_loss['r'])
        self.loss_bD.append(L_loss['D'])
        self.loss_bN.append(L_loss['N'])
        self.current_loss = loss.numpy()
        self.loss_hist.append(self.current_loss)
        self.iter+=1

    def solve(self,N=1000,flag_time=True):
        self.flag_time = flag_time
        optim = tf.keras.optimizers.Adam(learning_rate=self.lr)
 
        t0 = time()
        self.solve_with_TFoptimizer(optim, N)
        print('\nComputation time: {} seconds'.format(time()-t0))



class PINN_Precond(PINN):

    def __init__(self):
        super().__init__()

    def load_preconditioner(self,precond):
        self.precond = precond
        self.precond.X_r = self.X_r
        self.precond.x = self.x
        self.precond.y = self.y
        self.precond.z = self.z

    def get_precond_grad(self):
        with tf.GradientTape(persistent=True) as tape:
            tape.watch(self.model.trainable_variables)
            loss = self.precond.loss_fn(self.model,self.mesh)
        g = tape.gradient(loss, self.model.trainable_variables)
        del tape
        return loss, g

    def precond_with_TFoptimizer(self, optimizer, N=1001):
        @tf.function
        def train_step_precond():
            loss, grad_theta = self.get_precond_grad()
            optimizer.apply_gradients(zip(grad_theta, self.model.trainable_variables))
            return loss

        pbar = log_progress(range(N))
        pbar.set_description("Loss: %s " % 100)
        for i in pbar:
            loss = train_step_precond()
            self.callback(loss)

            if self.iter % 10 == 0:
                pbar.set_description("Loss: %s" % self.current_loss)

    def callback(self,loss):
        self.current_loss = loss.numpy()
        self.loss_hist.append(self.current_loss)
        self.iter+=1

    def preconditionate(self,N=2000):
        optim = tf.keras.optimizers.Adam(learning_rate=self.lr)

        t0 = time()
        self.precond_with_TFoptimizer(optim, N)
        print('\nComputation time: {} seconds'.format(time()-t0))


