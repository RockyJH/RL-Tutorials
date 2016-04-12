import random
import numpy as np
import math
import cPickle
import json
import os
import sys

# Networks
from RLLogisticRegression import RLLogisticRegression
from NeuralNet import NeuralNet 
from RLNeuralNetwork import RLNeuralNetwork
from RLNeuralNetworkDQ import RLNeuralNetworkDQ
from RLDeepNet import RLDeepNet 
from DeepCACLA import DeepCACLA
from DeepDPG import DeepDPG 
from ForwardDynamicsNetwork import ForwardDynamicsNetwork

# Games
from MapGame import Map
from BallGame1D import BallGame1D
from BallGame1DFuture import BallGame1DFuture

from RL_visualizing import *
from RLVisualize import RLVisualize
from NNVisualize import NNVisualize
from ExperienceMemory import ExperienceMemory
from RunGame import *



    
if __name__ == "__main__":
    
    # make a color map of fixed colors
    #try: 
        file = open(sys.argv[1])
        settings = json.load(file)
        file.close()
        map = loadMap()
        # Normalization constants for data
        max_reward = settings['max_reward']
        # max_reward = 1.0
        max_state = settings['max_state']
        
        print "Max Reward: " + str(max_reward)
        print "Max State: " + str(max_state)
        
        
        # game = Map(map)
        game = None
        game_type = settings['game_type']
        if game_type == 'BallGame1DFuture':
            print "Creating Game type: " + str(game_type)
            game = BallGame1DFuture()
        elif game_type == 'BallGame1D':
            print "Creating Game type: " + str(game_type)
            game = BallGame1D()
        else:
            print "Unrecognized game: " + str(game_type)
            sys.exit()
            
        game.enableRender()
        game._simulate=True
        # game._saveVideo=True
        game.setMovieName(str(settings['agent_name']) + "_on_" + str(game_type))
            
        action_bounds = np.array(settings['action_bounds'])
        action_length = len(action_bounds[0])
        data_folder = settings['data_folder']
        states = np.array([max_state])
        state_length = len(max_state)
        action_space_continuous=True
        
        file_name=data_folder+"navigator_agent_"+str(settings['agent_name'])+".pkl"
        model = cPickle.load(open(file_name))
        
        file_name_dynamics=data_folder+"forward_dynamics_"+str(settings['agent_name'])+".pkl"
        forwardDynamicsModel = cPickle.load(open(file_name_dynamics))
        
        if action_space_continuous:
            # X, Y, U, V, Q = get_continuous_policy_visual_data(model, max_state, game)
            X, Y, U, V, Q = get_continuous_policy_visual_data1D(model, max_state, game)
        else:
            X, Y, U, V, Q = get_policy_visual_data(model, max_state, game)
        game.init(U, V, Q)
        game.reset()
        
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        num_actions = 20
        scaling = 1.0
        game._box.state[0][1] = 0.0
        
        actions = (np.random.rand(num_actions,1)-0.5) * 2.0 * scaling
        for action_ in actions:
            # ballGame.resetTarget()
            game.resetTarget()
            game.resetHeight()
            game._box.state[0][1] = 0.0
            state = game.getState()
            print "State: " + str(state)
            # reward = game.actContinuous(action_)
            # print "Action: " + str(action_)
            # print "Verify State: " + str(state) + " with " + str(scale_state(norm_state(state, max_state=max_state), max_state=max_state))

            pa = model.predict([norm_state(state, max_state)])
            if action_space_continuous:
                action = scale_action(pa, action_bounds)
                print "Action: " + str(action)
                prediction = scale_state(forwardDynamicsModel.predict(state=norm_state(state, max_state), action=norm_action(action, action_bounds)), max_state)
                print "Next State Prediction: " + str(prediction)
                predicted_height = game._computeHeight(prediction[1]) # This is dependent on the network shape
                game.setPrediction([2,predicted_height])
                # print "Next Height Prediction: " + str(predicted_height)
                reward = game.actContinuous(action)
                print "Height difference: " + str(math.fabs(predicted_height - game._max_y))
            elif not action_space_continuous:
                # print "Action: " + str(pa)
                reward = game.act(action)
                
            # print "Reward: " + str(reward)
            
            

    #except Exception, e:
    #    print "Error: " + str(e)
    #    raise e
