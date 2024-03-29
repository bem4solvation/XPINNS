import tensorflow as tf
import os
import logging
import shutil

from DCM.PDE_Model_Regularized import Poisson
from DCM.PDE_Model_Regularized import Helmholtz
from DCM.PDE_Model_Regularized import PBE_Interface

from Simulation_X import Simulation

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'results')
#if os.path.exists(main_path):
#        shutil.rmtree(main_path)
#os.makedirs(main_path)

folder_name = 'data'
folder_path = os.path.join(main_path,folder_name)
if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
os.makedirs(folder_path)

filename = os.path.join(folder_path,'logfile.log')
LOG_format = '%(levelname)s - %(name)s: %(message)s'
logging.basicConfig(filename=filename, filemode='w', level=logging.INFO, format=LOG_format)
logger = logging.getLogger(__name__)

logger.info('================================================')


# Inputs
###############################################

def main():

    Sim = Simulation(PBE_Interface)

    # PDE
    q_list = [(1,[0,0,0])]

    inputs = {'Problem': 'Main_X_REG',
              'rmin': 0,
              'rI': 1,
              'rB': 10,
              'epsilon_1':1,
              'epsilon_2':80,
              'kappa': 0.125,
              }
    
    Sim.problem = inputs
    Sim.q = q_list
    
    rI = inputs['rI']
    rB = inputs['rB']

    Sim.domain_in = ([-rI,rI],[-rI,rI],[-rI,rI])
    Sim.PDE_in = Poisson()
    Sim.PDE_in.sigma = 0.04
    Sim.PDE_in.epsilon = inputs['epsilon_1']
    Sim.PDE_in.epsilon_G = inputs['epsilon_1']
    Sim.PDE_in.q = q_list
    Sim.PDE_in.problem = inputs

    inner_interface = {'type':'I', 'value':None, 'fun':None, 'dr':None, 'r':rI, 'N': 40}
    Sim.borders_in = {'1':inner_interface}
    Sim.ins_domain_in = {'rmax': rI}


    Sim.domain_out = ([-rB,rB],[-rB,rB],[-rB,rB])
    Sim.PDE_out = Helmholtz()
    Sim.PDE_out.epsilon = inputs['epsilon_2']
    Sim.PDE_out.epsilon_G = inputs['epsilon_1']
    Sim.PDE_out.kappa = inputs['kappa']
    Sim.PDE_out.q = q_list 
    Sim.PDE_out.problem = inputs

    u_an = Sim.PDE_out.border_value(rB,0,0,rI) - Sim.PDE_out.G_Fun(rB,0,0)
    outer_interface = {'type':'I', 'value':None, 'fun':None, 'dr':None, 'r':rI, 'N':50}
    outer_dirichlet = {'type':'D', 'value':u_an, 'fun':None, 'dr':None, 'r':rB, 'N': 50}
    
    Sim.borders_out = {'1':outer_interface,'2':outer_dirichlet}
    Sim.ins_domain_out = {'rmax': rB,'rmin':rI}


    # Mesh
    Sim.mesh = {'N_r': 40,
                'N_r_P': 40}

    # Neural Network
    Sim.weights = {
        'w_r': 1,
        'w_d': 1,
        'w_n': 1,
        'w_i': 1,
        'w_k': 1
    }

    Sim.lr = ([3000,6000],[1e-2,5e-3,5e-4])

    
    Sim.hyperparameters_in = {
                'input_shape': (None,3),
                'num_hidden_layers': 4,
                'num_neurons_per_layer': 12,
                'output_dim': 1,
                'activation': 'tanh',
                'architecture_Net': 'FCNN',
                'kernel_initializer': 'glorot_normal'
        }

    Sim.hyperparameters_out = {
                'input_shape': (None,3),
                'num_hidden_layers': 4,
                'num_neurons_per_layer': 12,
                'output_dim': 1,
                'activation': 'tanh',
                'architecture_Net': 'FCNN',
                'kernel_initializer': 'glorot_normal'
        }


    Sim.N_iters = 2101
    Sim.precondition = True
    Sim.N_precond = 2000
    Sim.N_batches = 50

    Sim.iters_save_model = 100

    Sim.folder_path = folder_path

    Sim.setup_algorithm()

    # Solve
    Sim.solve_algorithm(N_iters=Sim.N_iters, precond=Sim.precondition, N_precond=Sim.N_precond, N_batches=Sim.N_batches, save_model=Sim.iters_save_model)
    
    Sim.postprocessing(folder_path=folder_path)



if __name__=='__main__':
    main()


